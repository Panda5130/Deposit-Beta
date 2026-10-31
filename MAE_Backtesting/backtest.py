"""Rolling-origin MAE backtest of one bank's one-step ECM.

For a horizon of N quarters and last observed quarter T, the origins are T-N, ..., T-1.
At each origin the model's specification (the terms in "ECM estimation results.csv") is
re-estimated on data up to and including the origin with ECM estimation.fit_one_step, then
forecast dynamically to T: predicted y is fed back in as the lag, the regressor (FFT) takes
its realised values. The bar for "kQ" is the mean absolute error over those k quarters.
naive_mae is the same window's MAE of a no-change forecast (y held at its origin value).

Each kQ bar of run() rests on ONE forecast window (origin T-k). run_multi() is the
many-origin version (OI-22): expanding-window re-estimation at every origin from
first_origin to T-1, dynamic forecast up to N steps ahead, and the h-step absolute error
averaged over every origin with origin + h <= T; n_windows is reported per horizon.

Acceptance thresholds for the single-window table (assess, OI-10), on the N horizons' MAE in pp:
    Green  mean <= 0.15 and mean below the no-change mean
    Amber  mean 0.15-0.25, or the model beats no-change on fewer than 6 of 8 horizons (75%)
    Red    mean > 0.25, or any horizon > 0.50

Horizon-aware thresholds for the many-origin table (assess_multi, OI-22), derived each run:
    bands      1..ceil(N/4), ceil(N/4)+1..ceil(N/2), ceil(N/2)+1..N (empty bands dropped)
    limits     per band across the banks: green = up(P75 of band avg), red = max(up(P75 of
               band max), green + 0.05), with up(v) = v rounded up to the next 0.05
    absolute   Red if band max > red, Amber if band avg > green (worst band counts)
    skill      model / no-change h-step MAE: Red if any >= 1.00, Amber if any > 0.75
    rating     worse of absolute and skill; absolute is skipped with fewer than 4 banks
The limits are relative to the peer group: about a quarter of banks exceed green by construction.

Model choice (select_model): the bank's lowest in-sample MAE in "estimation result
summary.csv", ties broken EG > ARDL > Johansen, then file order; or the model the user names.

run_backtest.py is the command-line driver; this module holds the reusable pieces.
"""

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
import bank_plots as bp  # noqa: E402


def load_module(path, name):
    # The file name has a space, so it can't be imported with a plain import.
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


est = load_module(ROOT / "ECM estimation.py", "ecm_estimation")

SPEC_KEYS = bp.SPEC_KEYS
FAMILY_RANK = {"EG": 0, "ARDL": 1, "Johansen": 2}
TABLE_COLUMNS = ["horizon_q", "origin", "start", "end", "n_obs", "mae", "naive_mae"]
GREEN_MEAN, AMBER_MEAN, RED_ANY, MIN_WIN_SHARE = 0.15, 0.25, 0.50, 0.75
ASSESSMENT_COLUMNS = ["mean_mae", "max_mae", "naive_mean_mae", "horizons_beating_naive", "rating"]
MULTI_COLUMNS = ["horizon_q", "first_origin", "last_origin", "n_windows", "mae", "naive_mae"]
ERROR_COLUMNS = ["h", "origin", "err", "naive"]
STEP, SKILL_AMBER, SKILL_RED, MIN_PEERS = 0.05, 0.75, 1.00, 4
LIMIT_COLUMNS = ["band", "h_from", "h_to", "green", "red", "n_banks"]


def family(test_name):
    return next((r for f, r in FAMILY_RANK.items() if str(test_name).startswith(f)), len(FAMILY_RANK))


def parse_model(text):
    keys = [s.strip() for s in str(text).split("|")]
    if len(keys) != len(SPEC_KEYS) or not all(keys):
        raise ValueError(f'model must look like "test_name | IC/selected lag | trend type", got {text!r}')
    return tuple(keys)


def bank_rows(table, bank, group_column="bank_name"):
    return table[table[group_column].astype(str).str.strip() == bank]


def model_mask(rows, model):
    return (rows[SPEC_KEYS].astype(str).apply(lambda c: c.str.strip()) == list(model)).all(axis=1)


def select_model(summary, bank, model=None, group_column="bank_name"):
    """The model to backtest, as (test_name, IC/selected lag, trend type)."""
    rows = bank_rows(summary, bank, group_column).reset_index(drop=True)
    if rows.empty:
        raise ValueError(f"no models for {bank} in the summary")
    if model is not None:
        model = parse_model(model)
        if not model_mask(rows, model).any():
            available = "\n  ".join(" | ".join(map(str, k)) for k in rows[SPEC_KEYS].itertuples(index=False))
            raise ValueError(f"{bank} has no model {' | '.join(model)}; available:\n  {available}")
        return model
    # Round so floating-point noise between equal fits doesn't defeat the family tie-break.
    ranked = rows.assign(_mae=rows["MAE"].round(12), _rank=rows["test_name"].map(family), _order=rows.index)
    best = ranked.sort_values(["_mae", "_rank", "_order"]).iloc[0]
    return tuple(str(best[k]).strip() for k in SPEC_KEYS)


def spec_from_terms(terms, y, x):
    """Map fitted term names back onto fit_one_step's (det, levels, short_run)."""
    det, levels, short_run = [], [], []
    for term in terms:
        if term in ("const", "trend"):
            det.append(term)
        elif term == f"{y}.L1":
            continue  # always included by fit_one_step
        elif term.endswith(".L1") and term[:-3] == x:
            levels.append(x)
        elif (m := bp.SHORT_RUN_RE.match(term)) and m["var"] in (y, x):
            short_run.append((m["var"], int(m["lag"])))
        else:
            raise ValueError(f"unrecognised term '{term}'")
    if f"{y}.L1" not in terms:
        raise ValueError(f"model has no {y}.L1 (correction) term")
    return det, levels, short_run


@dataclass
class BacktestResult:
    bank: str
    model: tuple
    horizon: int
    table: pd.DataFrame  # TABLE_COLUMNS, one row per horizon k = 1..N

    def labelled(self):
        keys = dict(zip(["bank_name"] + SPEC_KEYS, [self.bank, *self.model]))
        return self.table.assign(**keys)[list(keys) + TABLE_COLUMNS]


class MAEBacktest:
    """Rolling-origin backtest of one bank's model over the last `horizon` quarters."""

    def __init__(self, bank, model, horizon, data, spec_rows, y=bp.DEFAULTS["y"], x=bp.DEFAULTS["x"],
                 min_train=20):
        self.bank, self.model, self.horizon = bank, tuple(model), int(horizon)
        self.data, self.y, self.x, self.min_train = data, y, x, min_train
        terms = [t for t in spec_rows["term"].astype(str) if not t.startswith("LR: ")]
        self.det, self.levels, self.short_run = spec_from_terms(terms, y, x)
        if len(data) - self.horizon < min_train:
            raise ValueError(f"{len(data)} observations leave {len(data) - self.horizon} for training "
                             f"before the first origin; need at least {min_train}")

    def fit(self, origin):
        return est.fit_one_step(self.data.loc[:origin], self.y, self.det, self.levels, self.short_run)

    def forecast(self, res, origin):
        """Actual and dynamically forecast y for every quarter after the origin."""
        path = self.data.copy()
        for t in path.index[path.index > origin]:
            # regressor() rebuilds each term over the whole path; trend keeps counting from the start.
            X = pd.concat({term: bp.regressor(path, term).loc[[t]] for term in res.params.index}, axis=1)
            dy_hat = float(X.iloc[0] @ res.params)
            path.loc[t, self.y] = path[self.y].shift(1).loc[t] + dy_hat
        window = self.data.index > origin
        return self.data.loc[window, self.y], path.loc[window, self.y]

    def run(self):
        index = self.data.index
        rows = []
        for k in range(self.horizon, 0, -1):
            origin = index[-k - 1]
            actual, predicted = self.forecast(self.fit(origin), origin)
            naive = float(np.mean(np.abs(actual - self.data.loc[origin, self.y])))
            rows.append([f"{k}Q", str(origin), str(actual.index[0]), str(actual.index[-1]), len(actual),
                         float(np.mean(np.abs(actual - predicted))), naive])
        table = pd.DataFrame(rows, columns=TABLE_COLUMNS).iloc[::-1].reset_index(drop=True)
        return BacktestResult(self.bank, self.model, self.horizon, table)

    def multi_errors(self, first_origin):
        """|model| and |no-change| errors at every (h <= N, origin) from first_origin to T-1."""
        index = self.data.index
        first_origin = max(pd.Period(first_origin, "Q"), index[self.min_train - 1])
        errors = []
        for origin in index[(index >= first_origin) & (index < index[-1])]:
            actual, predicted = self.forecast(self.fit(origin), origin)
            start = self.data.loc[origin, self.y]
            for h, t in enumerate(actual.index[:self.horizon], start=1):
                errors.append((h, str(origin), abs(actual[t] - predicted[t]), abs(actual[t] - start)))
        return pd.DataFrame(errors, columns=ERROR_COLUMNS)

    def run_multi(self, first_origin):
        """h-step-ahead MAE over every origin from first_origin to T-1 (expanding window)."""
        return summarise_errors(self.multi_errors(first_origin))

    def data_hash(self):
        return f"{int(pd.util.hash_pandas_object(self.data, index=True).sum()) & (2**64 - 1):016x}"

    def mae(self):
        t = self.run().table
        return pd.Series(t["mae"].values, index=[f"{r.horizon_q} ({r.start}-{r.end})" for r in t.itertuples()])


def assess(table):
    """Green / Amber / Red rating of one backtest table against the acceptance thresholds."""
    mae, naive = table["mae"], table["naive_mae"]
    mean, wins = float(mae.mean()), int((mae < naive).sum())
    if mean > AMBER_MEAN or float(mae.max()) > RED_ANY:
        rating = "Red"
    elif mean > GREEN_MEAN or wins < MIN_WIN_SHARE * len(table) or mean >= float(naive.mean()):
        rating = "Amber"
    else:
        rating = "Green"
    return dict(zip(ASSESSMENT_COLUMNS, [mean, float(mae.max()), float(naive.mean()), f"{wins}/{len(table)}", rating]))


def summarise_errors(errors, horizon=None):
    """Per-origin errors -> one row per horizon (MULTI_COLUMNS); h > horizon is dropped."""
    e = errors if horizon is None else errors[errors.h <= horizon]
    rows = [[f"{h}Q", g.origin.min(), g.origin.max(), len(g), g.err.mean(), g.naive.mean()]
            for h, g in e.groupby("h")]
    return pd.DataFrame(rows, columns=MULTI_COLUMNS)


class ErrorCache:
    """Per-origin errors stored per bank, reused by any run with horizon <= the stored one.

    One CSV per bank, tagged with model, first_origin, data hash and run horizon. The h-step
    errors for h <= N do not depend on N, so a longer stored run is sliced, not refit.
    """

    def __init__(self, directory):
        self.dir = Path(directory)

    def path(self, bank):
        return self.dir / f"{bp.INVALID_CHARS_RE.sub('-', bank)}.csv"

    def load(self, bank, model, first_origin, data_hash, horizon):
        """Stored errors for the bank (h <= horizon), or None if missing or stale."""
        path = self.path(bank)
        if not path.exists():
            return None
        e = pd.read_csv(path, dtype={"origin": str, "first_origin": str, "data_hash": str, "model": str})
        key = e.iloc[0]
        if (key.model != " | ".join(model) or key.first_origin != str(pd.Period(first_origin, "Q"))
                or key.data_hash != data_hash or key.run_horizon < horizon):
            return None
        return e[e.h <= horizon].reset_index(drop=True)

    def store(self, bank, model, first_origin, data_hash, horizon, errors):
        self.dir.mkdir(parents=True, exist_ok=True)
        errors.assign(model=" | ".join(model), first_origin=str(pd.Period(first_origin, "Q")),
                      data_hash=data_hash, run_horizon=horizon).to_csv(self.path(bank), index=False)


def up(v):
    """v rounded up to the next STEP (0.05), guarding float noise."""
    return np.ceil(np.round(np.asarray(v, dtype=float) / STEP, 9)) * STEP


def horizon_bands(horizon):
    """[(label, h_from, h_to)]: 1..ceil(N/4), ..ceil(N/2), ..N, empty bands dropped."""
    e1, e2 = -(-horizon // 4), -(-horizon // 2)
    edges = [(1, e1), (e1 + 1, e2), (e2 + 1, horizon)]
    return [(f"{a}Q" if a == b else f"{a}-{b}Q", a, b) for a, b in edges if a <= b]


def assess_multi(tables, horizon):
    """Horizon-aware ratings for {bank: summarise_errors table} -> (limits, assessment).

    The band limits use every bank in `tables` (the peers); with fewer than MIN_PEERS banks
    only the skill-ratio test is applied.
    """
    t = pd.concat([tab.assign(bank_name=bank) for bank, tab in tables.items()], ignore_index=True)
    t["h"] = t["horizon_q"].str.rstrip("Q").astype(int)
    t = t[t.h <= horizon].copy()
    bands = horizon_bands(horizon)
    t["band"] = pd.cut(t.h, [0] + [b for _, _, b in bands], labels=[lab for lab, _, _ in bands]).astype(str)
    t["skill"] = t["mae"] / t["naive_mae"]
    per_band = t.groupby(["band", "bank_name"])["mae"].agg(avg="mean", max="max").reset_index()
    n_banks = t.bank_name.nunique()
    q = per_band.groupby("band")[["avg", "max"]].quantile(0.75)
    green = np.round(up(q["avg"]), 2)
    limits = pd.DataFrame({"band": q.index, "green": green,
                           "red": np.round(np.maximum(up(q["max"]), green + STEP), 2), "n_banks": n_banks})
    limits = pd.DataFrame(bands, columns=["band", "h_from", "h_to"]).merge(limits, on="band")[LIMIT_COLUMNS]
    use_absolute = n_banks >= MIN_PEERS
    lim = limits.set_index("band")
    order = ["Green", "Amber", "Red"]

    rows = []
    for bank, g in per_band.groupby("bank_name"):
        g = g.set_index("band").loc[[b for b, _, _ in bands]]
        reasons, absolute = [], "Green"
        for band, r in g.iterrows():
            if r["max"] > lim.loc[band, "red"] + 1e-12:
                absolute = "Red"
                reasons.append(f"{band} max {r['max']:.3f} > red {lim.loc[band, 'red']:.2f}")
            elif r["avg"] > lim.loc[band, "green"] + 1e-12:
                absolute = max(absolute, "Amber", key=order.index)
                reasons.append(f"{band} avg {r['avg']:.3f} > green {lim.loc[band, 'green']:.2f}")
        skill = t[t.bank_name == bank].set_index("h")["skill"]
        worst, worst_h = float(skill.max()), int(skill.idxmax())
        skill_rating = "Red" if worst >= SKILL_RED else ("Amber" if worst > SKILL_AMBER else "Green")
        if skill_rating != "Green":
            reasons.append(f"skill ratio {worst:.2f} at {worst_h}Q")
        if not use_absolute:
            absolute = "n/a"
            reasons = [x for x in reasons if x.startswith("skill")] + [
                f"absolute test skipped: {n_banks} bank(s) with results, need {MIN_PEERS}"]
        final = max([skill_rating] + ([absolute] if use_absolute else []), key=order.index)
        row = {"bank_name": bank}
        for band, r in g.iterrows():
            row[f"{band} avg"], row[f"{band} max"] = r["avg"], r["max"]
        row.update({"worst_skill_ratio": worst, "worst_skill_h": f"{worst_h}Q", "absolute_rating": absolute,
                    "skill_rating": skill_rating, "rating": final, "reason": "; ".join(reasons)})
        rows.append(row)
    return limits, pd.DataFrame(rows)


def plot_mae_bars(result, path, y=bp.DEFAULTS["y"]):
    t = result.table
    labels = [f"{r.horizon_q}\n{r.start}\nto {r.end}" for r in t.itertuples()]
    fig, ax = plt.subplots(figsize=(11, 5))
    bars = ax.bar(labels, t["mae"], color="#1f4e79")
    ax.bar_label(bars, fmt="%.3f", fontsize=8)
    ax.set_title(f"{result.bank}\n{' | '.join(result.model)}\n"
                 f"Rolling-origin dynamic forecast MAE of {y}, {result.horizon}Q backtest", fontsize=10)
    ax.set_xlabel("Forecast horizon (forecast window)")
    ax.set_ylabel("MAE")
    ax.grid(True, axis="y", alpha=0.3)
    ax.set_axisbelow(True)
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)
