"""Rolling-origin stability backtest of one bank's long-run deposit beta.

For a horizon of N quarters and last observed quarter T, the origins are T-N, ..., T-1.
At each origin the model's specification (the terms in "ECM estimation results.csv") is
re-estimated on data up to and including the origin (expanding window, MAEBacktest.fit),
and the long-run beta theta = -coef(x.L1) / lambda is recovered with
ECM estimation.long_run_rows, so it is the same number as the "LR: <x>" row of the
estimates when fitted on the full sample. lambda is the y.L1 coefficient.

The bar for "kQ" is the mean beta over the k fits at origins T-k, ..., T-1, with their
min and max as whiskers; full_sample_beta (the fit through T) is the reference line and
max_abs_dev is the largest |beta at origin - full_sample_beta| over those k fits.

Many-origin run (OI-23): with a first origin (e.g. 2016Q1), beta is re-estimated at every
origin from there to T-1, with the same origin handling as the MAE backtest
(MAEBacktest.origins) and a per-bank cache (BetaCache, keyed like bt.ErrorCache). Each
origin's deviation from the full-sample beta is reported in pp, as a share of the
full-sample beta and in origin standard errors. Rating (assess_multi), on the origins from
RATED_FROM (2020Q1: earlier samples are mostly at the zero lower bound, where beta is weakly
identified; they are charted but not rated):
    failing origin   |deviation| > 2 origin SEs AND > 20% of the full-sample beta
    extreme origin   |deviation| > 3 origin SEs AND > 20% of the full-sample beta
    Green  no failing origin
    Amber  1 or 2 failing origins, none extreme
    Red    3 or more failing origins, or any extreme origin

The model is the bank's champion (backtest.select_model), as in the MAE backtest.
run_beta_backtest.py is the command-line driver; this module holds the reusable pieces.
"""

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
sys.path.insert(0, str(ROOT / "MAE_Backtesting"))
import backtest as bt  # noqa: E402

bp, est = bt.bp, bt.est
ORIGIN_COLUMNS = ["origin", "n_obs", "beta", "beta_se", "beta_p", "lambda"]
DEVIATION_COLUMNS = ["full_sample_beta", "dev", "abs_dev_share", "abs_dev_se"]
RATED_FROM, SE_LIMIT, SE_EXTREME, SHARE_LIMIT, AMBER_MAX_FAILS = "2020Q1", 2.0, 3.0, 0.20, 2
SUMMARY_COLUMNS = ["horizon_q", "first_origin", "last_origin", "n_fits", "mean_beta", "min_beta", "max_beta",
                   "std_beta", "full_sample_beta", "max_abs_dev"]


@dataclass
class BetaResult:
    bank: str
    model: tuple
    horizon: int
    origins: pd.DataFrame  # ORIGIN_COLUMNS, one row per origin T-N..T-1, oldest first
    full_sample: dict  # ORIGIN_COLUMNS for the fit through T
    multi: pd.DataFrame = None  # ORIGIN_COLUMNS + DEVIATION_COLUMNS per origin from first_origin, if run
    assessment: dict = None  # assess_multi(multi)

    @property
    def summary(self):
        """One row per horizon k = 1..N: beta statistics over the fits at origins T-k..T-1."""
        full = self.full_sample["beta"]
        rows = []
        for k in range(1, self.horizon + 1):
            w = self.origins.iloc[-k:]
            rows.append([f"{k}Q", w.origin.iloc[0], w.origin.iloc[-1], len(w), w.beta.mean(), w.beta.min(),
                         w.beta.max(), w.beta.std(ddof=0), full, float((w.beta - full).abs().max())])
        return pd.DataFrame(rows, columns=SUMMARY_COLUMNS)

    def _labelled(self, table):
        keys = dict(zip(["bank_name"] + bt.SPEC_KEYS, [self.bank, *self.model]))
        return table.assign(**keys)[list(keys) + list(table.columns)]

    def labelled_origins(self):
        return self._labelled(self.origins)

    def labelled_summary(self):
        return self._labelled(self.summary)

    def labelled_multi(self):
        return self._labelled(self.multi)


class BetaBacktest(bt.MAEBacktest):
    """Long-run beta of one bank's model re-estimated at each of the last `horizon` origins."""

    def beta_at(self, origin):
        res = self.fit(origin)
        lr = {name: (theta, t, p) for name, theta, t, p in est.long_run_rows(res, self.y, self.det, self.levels)}
        beta, t, p = lr[f"LR: {self.x}"]
        return dict(zip(ORIGIN_COLUMNS, [str(origin), int(res.nobs), float(beta), float(beta / t), float(p),
                                         float(res.params[f"{self.y}.L1"])]))

    def origin_betas(self, first_origin=None):
        """Beta at each of the last `horizon` origins, or at every origin from first_origin to T-1."""
        index = self.data.index
        origins = index[-self.horizon - 1:-1] if first_origin is None else self.origins(first_origin)
        return pd.DataFrame([self.beta_at(o) for o in origins], columns=ORIGIN_COLUMNS)

    def full_sample_beta(self):
        return self.beta_at(self.data.index[-1])

    def run(self):
        return BetaResult(self.bank, self.model, self.horizon, self.origin_betas(), self.full_sample_beta())


def deviations(betas, full_sample):
    """Per-origin betas with their deviation from the full-sample beta: in pp, as a share of
    the full-sample beta and in origin standard errors."""
    full = full_sample["beta"]
    dev = betas["beta"] - full
    return betas.assign(full_sample_beta=full, dev=dev, abs_dev_share=dev.abs() / abs(full),
                        abs_dev_se=dev.abs() / betas["beta_se"])


def assess_multi(table, rated_from=RATED_FROM):
    """Green / Amber / Red beta-stability rating of one bank's many-origin table (deviations())."""
    t = table[pd.PeriodIndex(table.origin, freq="Q") >= pd.Period(rated_from, "Q")]
    if t.empty:
        raise ValueError(f"no origins on or after {rated_from} to rate")
    big = t.abs_dev_share > SHARE_LIMIT
    failing, extreme = t[big & (t.abs_dev_se > SE_LIMIT)], t[big & (t.abs_dev_se > SE_EXTREME)]
    if len(extreme) or len(failing) > AMBER_MAX_FAILS:
        rating = "Red"
    elif len(failing):
        rating = "Amber"
    else:
        rating = "Green"
    reasons = [f"{len(failing)} origin(s) > {SE_LIMIT:g} SE and > {SHARE_LIMIT:.0%}"] if len(failing) else []
    if len(extreme):
        reasons.append(f"{len(extreme)} beyond {SE_EXTREME:g} SE")
    share, se = t.abs_dev_share.idxmax(), t.abs_dev_se.idxmax()
    return {"rated_from": t.origin.iloc[0], "rated_to": t.origin.iloc[-1], "rated_origins": len(t),
            "full_sample_beta": float(t.full_sample_beta.iloc[0]), "min_beta": float(t.beta.min()),
            "max_beta": float(t.beta.max()), "max_abs_dev_share": float(t.abs_dev_share[share]),
            "max_share_origin": t.origin[share], "max_abs_dev_se": float(t.abs_dev_se[se]),
            "max_se_origin": t.origin[se], "failing_origins": len(failing), "extreme_origins": len(extreme),
            "failing_list": " ".join(failing.origin), "rating": rating, "reason": "; ".join(reasons)}


class BetaCache(bt.ErrorCache):
    """Per-origin betas stored per bank (bt.ErrorCache layout and key: model, first_origin,
    data hash, spec). A beta does not depend on the horizon, so any stored run is reused whole."""

    def load(self, bank, model, first_origin, data_hash, spec):
        e = self.read(bank, model, first_origin, data_hash, spec)
        return None if e is None else e[ORIGIN_COLUMNS]

    def store(self, bank, model, first_origin, data_hash, spec, betas):
        self.write(bank, model, first_origin, data_hash, spec, betas[ORIGIN_COLUMNS])


class BetaPlotter:
    """Bar charts of the mean rolling-origin beta per horizon; beta-by-origin charts for the
    many-origin run."""

    Y_RANGE = (-0.25, 1.25)  # beta axis of the many-origin charts; points outside are drawn at the edge

    def __init__(self, y=bp.DEFAULTS["y"], x=bp.DEFAULTS["x"]):
        self.y, self.x = y, x

    def bars(self, result, path):
        t = result.summary
        labels = [f"{r.horizon_q}\n{r.first_origin}\nto {r.last_origin}" for r in t.itertuples()]
        err = [t["mean_beta"] - t["min_beta"], t["max_beta"] - t["mean_beta"]]
        fig, ax = plt.subplots(figsize=(11, 5))
        bars = ax.bar(labels, t["mean_beta"], color="#1f4e79", yerr=err, capsize=4, ecolor="#555555",
                      label="Mean beta over origins (min-max whiskers)")
        ax.bar_label(bars, fmt="%.3f", fontsize=8, padding=2)
        ax.axhline(result.full_sample["beta"], color="#c62828", linestyle="--", linewidth=1.2,
                   label=f"Full-sample beta ({result.full_sample['origin']}): {result.full_sample['beta']:.3f}")
        ax.set_ylim(0, max(t["max_beta"].max(), result.full_sample["beta"]) * 1.25)
        ax.set_title(f"{result.bank}\n{' | '.join(result.model)}\n"
                     f"Rolling-origin long-run beta of {self.y} on {self.x}, {result.horizon}Q backtest", fontsize=10)
        ax.set_xlabel("Horizon (origins averaged)")
        ax.set_ylabel("Long-run beta")
        ax.legend(fontsize=8, loc="upper left")
        ax.grid(True, axis="y", alpha=0.3)
        ax.set_axisbelow(True)
        fig.savefig(path, dpi=120, bbox_inches="tight")
        plt.close(fig)

    def all_banks(self, results, path):
        """Mean beta by horizon, one line per bank."""
        fig, ax = plt.subplots(figsize=(11, 5))
        for result in results:
            t = result.summary
            ax.plot(t["horizon_q"], t["mean_beta"], marker="o", label=result.bank)
        ax.set_title(f"Rolling-origin mean long-run beta of {self.y} on {self.x} by horizon, all banks", fontsize=10)
        ax.set_xlabel("Horizon (mean over origins T-k to T-1)")
        ax.set_ylabel("Mean long-run beta")
        ax.legend(fontsize=8, loc="center left", bbox_to_anchor=(1.0, 0.5))
        ax.grid(True, alpha=0.3)
        ax.set_axisbelow(True)
        fig.savefig(path, dpi=120, bbox_inches="tight")
        plt.close(fig)

    def _origin_panel(self, ax, table, rated_from=None, se_limit=SE_LIMIT, share_limit=SHARE_LIMIT):
        """beta by origin with +/- se_limit origin SEs, the full-sample beta and its +/- share band."""
        t = table.reset_index(drop=True)
        x = np.arange(len(t))
        full = float(t.full_sample_beta.iloc[0])
        lo, hi = self.Y_RANGE
        ax.axhspan(full * (1 - share_limit), full * (1 + share_limit), color="#c62828", alpha=0.08, linewidth=0,
                   label=f"Full-sample beta +/- {share_limit:.0%}")
        ax.axhline(full, color="#c62828", linestyle="--", linewidth=1.2, label=f"Full-sample beta: {full:.3f}")
        ax.fill_between(x, np.clip(t.beta - se_limit * t.beta_se, lo, hi), np.clip(t.beta + se_limit * t.beta_se, lo, hi),
                        color="#1f4e79", alpha=0.15, linewidth=0, label=f"Origin beta +/- {se_limit:g} SE")
        ax.plot(x, np.clip(t.beta, lo, hi), color="#1f4e79", linewidth=1.5, marker="o", markersize=3,
                label="Beta at origin")
        off = ~t.beta.between(lo, hi)
        for i, b in t.beta[off].items():
            ax.plot(i, hi if b > hi else lo, marker="^" if b > hi else "v", color="#1f4e79", markersize=7)
        if off.any():
            ax.text(0.99, 0.03, f"Off scale (triangles): {int(off.sum())} origin(s), "
                    f"beta {t.beta[off].min():.2f} to {t.beta[off].max():.2f}",
                    transform=ax.transAxes, ha="right", va="bottom", fontsize=7, color="#333333")
        if rated_from is not None:
            unrated = int((pd.PeriodIndex(t.origin, freq="Q") < pd.Period(rated_from, "Q")).sum())
            if unrated:
                ax.axvspan(-0.5, unrated - 0.5, color="#b0b0b0", alpha=0.25, linewidth=0,
                           label=f"Not rated (before {rated_from})")
        ticks = x[::4]
        ax.set_xticks(ticks, t.origin.iloc[ticks], rotation=90, fontsize=7)
        ax.set_xlim(-0.5, len(t) - 0.5)
        ax.set_ylim(lo, hi)
        ax.grid(True, axis="y", alpha=0.3)
        ax.set_axisbelow(True)

    def origins_chart(self, result, path, rated_from=RATED_FROM, rating=None, se_limit=SE_LIMIT,
                      share_limit=SHARE_LIMIT):
        """One bank's beta at every origin of the many-origin run."""
        fig, ax = plt.subplots(figsize=(11, 5))
        self._origin_panel(ax, result.multi, rated_from, se_limit, share_limit)
        t = result.multi
        title = (f"{result.bank}\n{' | '.join(result.model)}\nLong-run beta of {self.y} on {self.x} re-estimated at "
                 f"every origin {t.origin.iloc[0]} to {t.origin.iloc[-1]} (expanding window)")
        ax.set_title(title + (f"; rating: {rating}" if rating else ""), fontsize=10)
        ax.set_xlabel("Origin (last quarter of the estimation sample)")
        ax.set_ylabel("Long-run beta")
        ax.legend(fontsize=8, loc="upper right")
        fig.savefig(path, dpi=120, bbox_inches="tight")
        plt.close(fig)

    def all_banks_origins(self, results, path, rated_from=RATED_FROM, ratings=None, se_limit=SE_LIMIT,
                          share_limit=SHARE_LIMIT):
        """Small multiples of beta by origin, one panel per bank."""
        n = len(results)
        cols = min(4, n)
        rows = -(-n // cols)
        fig, axes = plt.subplots(rows, cols, figsize=(4 * cols, 3.4 * rows), sharey=True, squeeze=False)
        for ax, result in zip(axes.flat, results):
            self._origin_panel(ax, result.multi, rated_from, se_limit, share_limit)
            rating = (ratings or {}).get(result.bank)
            ax.set_title(result.bank + (f"\nrating: {rating}" if rating else ""), fontsize=9)
        for ax in list(axes.flat)[n:]:
            ax.axis("off")
        handles, labels = axes.flat[0].get_legend_handles_labels()
        fig.legend(handles, [lab.split(":")[0] for lab in labels], loc="lower center", ncol=len(labels), fontsize=8,
                   bbox_to_anchor=(0.5, -0.02))
        fig.suptitle(f"Long-run beta of {self.y} on {self.x} re-estimated at every origin, all banks", fontsize=11)
        fig.tight_layout(rect=(0, 0.04, 1, 0.97))
        fig.savefig(path, dpi=120, bbox_inches="tight")
        plt.close(fig)
