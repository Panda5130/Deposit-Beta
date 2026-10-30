"""Retest the flagged rates under every trend / lag-selection combination each test allows.

Usage (all arguments optional; defaults point at the files in this folder):
    python FlaggedRates_co-integration_respecification.py
        [--dependents FILE] [--independents FILE] [--y COLUMN] [--x COLUMN ...]
        [--banks NAME ...] [--max-lag N] [-o OUTPUT_CSV]

Reuses the data loading, VECM and coefficient helpers in "Co-integration Tests.py"
(imported, not modified). The grid per test:

    Engle-Granger  trend   n, c, ct  (long-run regression and short-run ECM)
                   lags    AIC, BIC, t-stat (general-to-specific), fixed (= max lag)
                           for both the residual ADF and the ECM lag length;
                           EG_ShortRun tests t on ect.L1 against MacKinnon critical values
    Johansen       trend   det_order -1 (none), 0 (constant), 1 (linear trend)
                   lags    k_ar_diff chosen by VECM AIC, BIC, HQIC, FPE, or fixed at 1
    ARDL bounds    trend   PSS cases 1-5 (case 1: n; 2-3: c; 4-5: ct)
                   lags    AIC, BIC, HQIC

Output: co-integration_respecification_results.csv, with the Co-integration_results.csv
columns plus "IC/selected lag" and "trend type" right after bank_name.
"""

import argparse
import importlib.util
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.ardl import ARDL, UECM, ardl_select_order
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.vector_ar.vecm import select_order

HERE = Path(__file__).resolve().parent


def load_module(path):
    # The file name has a space and a hyphen, so it can't be imported with a plain import.
    spec = importlib.util.spec_from_file_location("cointegration_tests", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ct = load_module(HERE / "Co-integration Tests.py")

OUTPUT_NAME = "co-integration_respecification_results.csv"
# All seven banks (OI-4): Huntington and Old National were originally left out because they
# passed under the baseline, so their cointegration result had no robustness check.
FLAGGED_BANKS = ["Manufacturers and Traders Trust Company", "Glacier Bank", "First Horizon Bank",
                 "SouthState Bank", "KeyBank National Association", "Huntington National Bank",
                 "Old National Bank"]
GROUP_COLUMN = "bank_name"
EXTRA_COLUMNS = ["IC/selected lag", "trend type"]

EG_TRENDS = {"n": "n (none)", "c": "c (constant)", "ct": "ct (constant + trend)"}
EG_ICS = ["AIC", "BIC", "t-stat", "fixed"]
JOHANSEN_TRENDS = {-1: "det_order -1 (none)", 0: "det_order 0 (constant)", 1: "det_order 1 (linear trend)"}
JOHANSEN_ICS = ["aic", "bic", "hqic", "fpe", "fixed"]
ARDL_CASES = {
    1: ("n", "case 1 (no deterministic terms)"),
    2: ("c", "case 2 (restricted constant)"),
    3: ("c", "case 3 (unrestricted constant)"),
    4: ("ct", "case 4 (unrestricted constant, restricted trend)"),
    5: ("ct", "case 5 (unrestricted constant and trend)"),
}
ARDL_ICS = ["aic", "bic", "hqic"]


def add_deterministic(X, trend):
    if trend in ("c", "ct"):
        X = sm.add_constant(X, has_constant="add")
    if trend == "ct":
        X = X.assign(trend=np.arange(1, len(X) + 1))
    return X


def select_ecm(frame, columns_for, max_lag, trend, ic):
    """Fit the ECM for p = 0..max_lag and keep the one the lag-selection rule picks."""
    fits = [sm.OLS(frame["dy"], add_deterministic(frame[columns_for(p)], trend)).fit()
            for p in range(max_lag + 1)]
    if ic == "AIC":
        return min(fits, key=lambda f: f.aic)
    if ic == "BIC":
        return min(fits, key=lambda f: f.bic)
    if ic == "t-stat":
        # General-to-specific: longest p whose own lag-p terms include one significant at 5%.
        for p in range(max_lag, 0, -1):
            last = [c for c in columns_for(p) if c not in columns_for(p - 1)]
            if (fits[p].pvalues[last] < 0.05).any():
                return fits[p]
        return fits[0]
    return fits[max_lag]


def engle_granger(data, y, xs, trend, ic, max_lag):
    # Step 1: long-run regression and ADF on its residuals.
    long_run = sm.OLS(data[y], add_deterministic(data[xs], trend)).fit()
    resid = long_run.resid
    autolag = None if ic == "fixed" else ic
    lr_stat, _, _, adf = adfuller(resid, maxlag=max_lag, regression="n", autolag=autolag,
                                  regresults=True)
    lr_pval = ct.mackinnonp(lr_stat, regression=trend, N=len(xs) + 1)
    adf_names = ["resid.L1"] + [f"D.resid.L{i}" for i in range(1, adf.usedlag + 1)]
    lr_coefs = ct.coef_rows(long_run) + ct.coef_rows(adf.resols, adf_names, prefix="ADF: ")

    # Step 2: short-run ECM, lag length chosen by the same rule.
    diffs = data.diff()
    frame = pd.DataFrame({"dy": diffs[y], "ect.L1": resid.shift(1)})
    for i in range(max_lag + 1):
        for x in xs:
            frame[f"D.{x}.L{i}"] = diffs[x].shift(i)
        if i:
            frame[f"D.{y}.L{i}"] = diffs[y].shift(i)
    frame = frame.dropna()

    def ecm_columns(p):
        cols = ["ect.L1"] + [f"D.{x}.L{i}" for i in range(p + 1) for x in xs]
        return cols + [f"D.{y}.L{j}" for j in range(1, p + 1)]

    ecm = select_ecm(frame, ecm_columns, max_lag, trend, ic)
    ecm_lag = max([int(c.rsplit(".L", 1)[1]) for c in ecm.model.exog_names if c.startswith(f"D.{y}.L")],
                  default=0)

    # Cointegration test on the ECM: t on ect.L1 against MacKinnon (2010) critical values.
    sr_stat = ecm.tvalues["ect.L1"]
    sr_pval = ct.mackinnonp(sr_stat, regression=trend, N=len(xs) + 1)
    label = f"{ic} / ADF lag={adf.usedlag}, ECM lag={ecm_lag}"
    return [
        (label, "EG_LongRun", lr_stat, lr_pval, lr_coefs),
        (label, "EG_ShortRun", sr_stat, sr_pval, ct.coef_rows(ecm)),
    ]


def johansen(data, det_order, ic, max_lag):
    if ic == "fixed":
        k_ar_diff = 1
    else:
        order = select_order(data.values, max_lag, deterministic=ct.JOHANSEN_DETERMINISTIC[det_order])
        k_ar_diff = int(getattr(order, ic))
    label = f"{ic.upper() if ic != 'fixed' else 'fixed'} / k_ar_diff={k_ar_diff}"
    return [(label, *row) for row in ct.johansen(data, det_order, k_ar_diff)]


def ardl_bounds(data, y, xs, case, ic, max_lag):
    trend = ARDL_CASES[case][0]
    sel = ardl_select_order(data[y], max_lag, data[xs], max_lag, trend=trend, ic=ic)
    ar_lags = max(int(np.max(sel.model.ar_lags)) if sel.model.ar_lags else 0, 1)
    # The error-correction form needs at least one lag of every regressor.
    order = {}
    for x in xs:
        chosen = (sel.dl_lags or {}).get(x)
        order[x] = max(int(np.max(chosen)) if chosen else 0, 1)
    uecm = UECM.from_ardl(ARDL(data[y], ar_lags, data[xs], order, trend=trend)).fit()
    bt = uecm.bounds_test(case=case)
    lag_desc = ",".join([str(ar_lags)] + [str(order[x]) for x in xs])
    return [(f"{ic.upper()} / ARDL({lag_desc})", f"ARDL bounds F (ARDL({lag_desc}), case {case})",
             bt.stat, bt.p_values["upper"], ct.coef_rows(uecm))]


def run_bank(data, bank, y, xs, max_lag):
    specs = (
        [(EG_TRENDS[t], lambda t=t, ic=ic: engle_granger(data, y, xs, t, ic, max_lag))
         for t in EG_TRENDS for ic in EG_ICS]
        + [(JOHANSEN_TRENDS[d], lambda d=d, ic=ic: johansen(data, d, ic, max_lag))
           for d in JOHANSEN_TRENDS for ic in JOHANSEN_ICS]
        + [(f"{ARDL_CASES[c][0]} - {ARDL_CASES[c][1]}", lambda c=c, ic=ic: ardl_bounds(data, y, xs, c, ic, max_lag))
           for c in ARDL_CASES for ic in ARDL_ICS]
    )
    rows = []
    for trend_label, run in specs:
        try:
            for lag_label, test_name, stat, pval, coefs in run():
                for term, coef, t, p in coefs:
                    rows.append([bank, lag_label, trend_label, test_name, term, coef, t, p, stat, pval])
        except Exception as e:
            ct.err(f"{bank} / {trend_label}: {e}")
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description="Respecify co-integration tests for flagged rates.")
    parser.add_argument("--dependents", default=HERE / "consolidated_fdic_quarterly_financials_2011-2026_merger_adjusted.csv")
    parser.add_argument("--independents", default=HERE / "FFT_2011-2026.csv")
    parser.add_argument("--y", default="rate_pf_clean", help="dependent column")
    parser.add_argument("--x", nargs="+", default=["FFT"], help="regressor column(s)")
    parser.add_argument("--banks", nargs="+", default=FLAGGED_BANKS, help="flagged banks to retest")
    parser.add_argument("--max-lag", type=int, default=4)
    parser.add_argument("-o", "--output", default=HERE / OUTPUT_NAME)
    args = parser.parse_args(argv)

    try:
        source = ct.merge_sources(ct.read_table(args.dependents), ct.read_table(args.independents),
                                  None, None, "Q")
    except (FileNotFoundError, ValueError) as e:
        ct.err(e)
        return 1

    rows = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for bank in args.banks:
            try:
                _, subset = next(ct.select_groups(source, {"group_column": GROUP_COLUMN, "group_value": bank}))
                data = ct.prepare_data(subset, args.y, args.x)
            except Exception as e:
                ct.err(f"{bank}: {e}")
                continue
            rows.extend(run_bank(data, bank, args.y, args.x, args.max_lag))

    base = list(ct.OUTPUT_COLUMNS)
    base[base.index("group")] = GROUP_COLUMN
    columns = base[:1] + EXTRA_COLUMNS + base[1:]
    try:
        pd.DataFrame(rows, columns=columns).to_csv(args.output, index=False)
    except OSError as e:
        ct.err(f"could not write {args.output}: {e}")
        return 1
    return 0 if rows else 2


if __name__ == "__main__":
    sys.exit(main())
