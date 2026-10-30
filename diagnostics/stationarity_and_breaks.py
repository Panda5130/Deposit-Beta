"""Unit-root (ADF / KPSS) re-specification grid and Zivot-Andrews break tests for every bank.

Usage:
    python diagnostics/stationarity_and_breaks.py [--y rate_pf_clean]

Replaces the Colab notebooks (EDA1_Stationarity_Tests, Flagged Rates Analysis - ADF
respecification, Flagged Rate Analysis - Structural Breaks) for the rebuilt datasets, and
runs every bank, not just the flagged ones. Samples: 2011-2026 and 2008-2026, merger-adjusted.

ADF grid    regression c / n  x  lag selection AIC / BIC / t-stat
KPSS grid   regression c / ct x  bandwidth auto / short (legacy) / long (12*(n/100)^(1/4))
ZA          regression c / t / ct on levels, lag by AIC (max 4); if statsmodels' default
            autolag fails (rank-deficient auxiliary regression), retried with fixed lags 4..0.

Outputs in diagnostics/: unit_root_grid.csv, unit_root_summary.csv, zivot_andrews.csv
"""

import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller, kpss, zivot_andrews

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SAMPLES = {"2011-2026": ROOT / "consolidated_fdic_quarterly_financials_2011-2026_merger_adjusted.csv",
           "2008-2026": ROOT / "consolidated_fdic_quarterly_financials_2008-2026_merger_adjusted.csv"}
ALPHA = 0.05


def kpss_lags(n, bandwidth):
    return {"auto": "auto", "short": "legacy", "long": int(np.ceil(12 * (n / 100) ** 0.25))}[bandwidth]


def unit_root_grid(series):
    rows = []
    for order, s in (("I(0)", series), ("I(1)", series.diff().dropna())):
        for reg in ("c", "n"):
            for ic in ("AIC", "BIC", "t-stat"):
                stat, p, lag, *_ = adfuller(s, regression=reg, autolag=ic, maxlag=4)
                rows.append(["ADF", order, reg, ic, stat, p, lag, p < ALPHA])
        for reg in ("c", "ct"):
            for bw in ("auto", "short", "long"):
                stat, p, lag, _ = kpss(s, regression=reg, nlags=kpss_lags(len(s), bw))
                rows.append(["KPSS", order, reg, bw, stat, p, lag, p >= ALPHA])
    return pd.DataFrame(rows, columns=["test", "order", "regression", "lag_rule", "stat", "p_value", "lags",
                                       "indicates_stationary"])


def zivot(series, index):
    rows = []
    for reg in ("c", "t", "ct"):
        attempts = [("AIC", dict(maxlag=4, autolag="AIC"))] + [(f"fixed {k}", dict(maxlag=k, autolag=None))
                                                               for k in range(4, -1, -1)]
        note = ""
        for label, kw in attempts:
            try:
                stat, p, cv, lag, bp = zivot_andrews(series.values, regression=reg, **kw)
                rows.append([reg, label, stat, p, cv["1%"], cv["5%"], cv["10%"], lag, str(index[bp]), p < ALPHA,
                             note.strip("; ")])
                break
            except Exception as e:  # rank deficiency / shape errors in the auxiliary regression
                note += f"{label} failed ({type(e).__name__}); "
        else:
            rows.append([reg, "none", *[np.nan] * 7, False, note.strip("; ")])
    return pd.DataFrame(rows, columns=["regression", "lag_rule", "stat", "p_value", "cv_1", "cv_5", "cv_10",
                                       "lags", "break_quarter", "rejects_unit_root", "note"])


def summarise(grid):
    """Default-spec classification (ADF c/AIC, KPSS c/auto) plus robustness shares."""
    out = {}
    for order in ("I(0)", "I(1)"):
        g = grid[grid.order == order]
        adf = g[(g.test == "ADF") & (g.regression == "c") & (g.lag_rule == "AIC")].iloc[0]
        kp = g[(g.test == "KPSS") & (g.regression == "c") & (g.lag_rule == "auto")].iloc[0]
        verdict = ("stationary" if adf.indicates_stationary and kp.indicates_stationary else
                   "non-stationary" if not adf.indicates_stationary and not kp.indicates_stationary else
                   "inconclusive")
        out[f"{order} ADF c/AIC p"] = adf.p_value
        out[f"{order} KPSS c/auto p"] = kp.p_value
        out[f"{order} default verdict"] = verdict
        for test in ("ADF", "KPSS"):
            t = g[g.test == test]
            share = t.indicates_stationary.sum() if order == "I(1)" else (~t.indicates_stationary).sum()
            out[f"{order} {test} robustness"] = f"{share}/{len(t)}"
    i0, i1 = out["I(0) default verdict"], out["I(1) default verdict"]
    out["classification"] = "I(1)" if (i0 == "non-stationary" and i1 == "stationary") else (
        "I(0)" if i0 == "stationary" else "flagged")
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description="ADF/KPSS grid and Zivot-Andrews tests for every bank.")
    parser.add_argument("--y", default="rate_pf_clean")
    args = parser.parse_args(argv)
    grids, summaries, breaks = [], [], []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for sample, path in SAMPLES.items():
            data = pd.read_csv(path)
            for bank, g in data.groupby("bank_name"):
                s = g.set_index(pd.PeriodIndex(pd.to_datetime(g.quarter), freq="Q"))[args.y].dropna()
                grid = unit_root_grid(s).assign(sample=sample, bank_name=bank)
                grids.append(grid)
                summaries.append({"sample": sample, "bank_name": bank, **summarise(grid)})
                if sample == "2011-2026":
                    breaks.append(zivot(s, s.index).assign(sample=sample, bank_name=bank))
    front = ["sample", "bank_name"]
    for df, name in ((pd.concat(grids), "unit_root_grid.csv"), (pd.DataFrame(summaries), "unit_root_summary.csv"),
                     (pd.concat(breaks), "zivot_andrews.csv")):
        df[front + [c for c in df.columns if c not in front]].to_csv(HERE / name, index=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
