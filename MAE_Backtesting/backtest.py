"""Rolling-origin MAE backtest of one bank's one-step ECM.

For a horizon of N quarters and last observed quarter T, the origins are T-N, ..., T-1.
At each origin the model's specification (the terms in "ECM estimation results.csv") is
re-estimated on data up to and including the origin with ECM estimation.fit_one_step, then
forecast dynamically to T: predicted y is fed back in as the lag, the regressor (FFT) takes
its realised values. The bar for "kQ" is the mean absolute error over those k quarters.

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
TABLE_COLUMNS = ["horizon_q", "origin", "start", "end", "n_obs", "mae"]


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
            rows.append([f"{k}Q", str(origin), str(actual.index[0]), str(actual.index[-1]), len(actual),
                         float(np.mean(np.abs(actual - predicted)))])
        table = pd.DataFrame(rows, columns=TABLE_COLUMNS).iloc[::-1].reset_index(drop=True)
        return BacktestResult(self.bank, self.model, self.horizon, table)

    def mae(self):
        t = self.run().table
        return pd.Series(t["mae"].values, index=[f"{r.horizon_q} ({r.start}-{r.end})" for r in t.itertuples()])


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
