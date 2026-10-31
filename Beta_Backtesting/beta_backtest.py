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
SUMMARY_COLUMNS = ["horizon_q", "first_origin", "last_origin", "n_fits", "mean_beta", "min_beta", "max_beta",
                   "std_beta", "full_sample_beta", "max_abs_dev"]


@dataclass
class BetaResult:
    bank: str
    model: tuple
    horizon: int
    origins: pd.DataFrame  # ORIGIN_COLUMNS, one row per origin T-N..T-1, oldest first
    full_sample: dict  # ORIGIN_COLUMNS for the fit through T

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


class BetaBacktest(bt.MAEBacktest):
    """Long-run beta of one bank's model re-estimated at each of the last `horizon` origins."""

    def beta_at(self, origin):
        res = self.fit(origin)
        lr = {name: (theta, t, p) for name, theta, t, p in est.long_run_rows(res, self.y, self.det, self.levels)}
        beta, t, p = lr[f"LR: {self.x}"]
        return dict(zip(ORIGIN_COLUMNS, [str(origin), int(res.nobs), float(beta), float(beta / t), float(p),
                                         float(res.params[f"{self.y}.L1"])]))

    def origin_betas(self):
        index = self.data.index
        return pd.DataFrame([self.beta_at(o) for o in index[-self.horizon - 1:-1]], columns=ORIGIN_COLUMNS)

    def full_sample_beta(self):
        return self.beta_at(self.data.index[-1])

    def run(self):
        return BetaResult(self.bank, self.model, self.horizon, self.origin_betas(), self.full_sample_beta())


class BetaPlotter:
    """Bar charts of the mean rolling-origin beta per horizon."""

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
