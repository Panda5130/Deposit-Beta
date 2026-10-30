"""Batch cointegration / ARDL testing.

Usage:
    python "Co-integration Tests.py" DEPENDENTS_FILE INDEPENDENTS_FILE PARAMS_FILE [-o OUTPUT_CSV]

DEPENDENTS_FILE    CSV or Excel holding the dependent series (y). Wide (one column per
                   series) or long/panel format (pick a panel with group_column/group_value).
INDEPENDENTS_FILE  CSV or Excel holding the regressor series (x), one column per series.
                   Both files are joined on their date column, aligned to --freq periods.
PARAMS_FILE        CSV or Excel, one row per specification. Columns (case-insensitive):
    time_series_name   required  dependent column (y)
    dependents         required  regressor column(s), separated by ';' or ','
    tests              optional  any of eg;johansen;ardl (default: all three)
    group_column       optional  panel filter column (e.g. bank_name)
    group_value        optional  value kept in group_column; '*' runs every group
    trend              optional  EG/ARDL deterministic term: n, c, ct (default c)
    max_lag            optional  max lag for EG ADF/ECM and ARDL selection (default 4)
    det_order          optional  Johansen deterministic order -1/0/1 (default 0)
    k_ar_diff          optional  Johansen lagged differences (default 1)
    ardl_case          optional  ARDL bounds-test case 1-5 (default 3)

Output CSV: one row per (group, test, term), panel style. Columns:
    group           renamed to the params' group_column (e.g. bank_name) when all rows share one
    test_name       test / equation the row belongs to
    term            right-hand-side term of that equation
    coef            estimated coefficient
    coef_stat       t-stat of the coefficient
    coef_p_value    p-value of the coefficient
    model_stat      test statistic of the whole test (repeated on each of its terms)
    model_p_value   p-value of that test statistic

    test_name           model_stat / model_p_value                   terms
    EG_LongRun          ADF t on step-1 residuals, MacKinnon p       step-1 OLS + "ADF:" terms
    EG_ShortRun         t on ect.L1 in the short-run ECM, MacKinnon  ECM terms (ect.L1 = speed of adjustment)
                        p (same trend and N as EG_LongRun)
    Johansen trace      trace stat for each rank r; p bounded from   none
                        critical values (no exact p in statsmodels)
    Johansen VECM       none                                          rank-1 VECM, one block per equation
    ARDL bounds F       PSS bounds F, I(1) upper-bound p             UECM terms
Coefficient t/p-values on levels regressors (EG step 1, VECM beta) do not follow standard
distributions when the series are I(1); read them as descriptive only.
"""

import argparse
import re
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.ardl import ARDL, UECM, ardl_select_order
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.adfvalues import mackinnonp
from statsmodels.tsa.vector_ar.vecm import VECM, coint_johansen

OUTPUT_NAME = "Co-integration_results.csv"
OUTPUT_COLUMNS = ["group", "test_name", "term", "coef", "coef_stat", "coef_p_value",
                  "model_stat", "model_p_value"]
JOHANSEN_DETERMINISTIC = {-1: "n", 0: "co", 1: "colo"}
PERIOD_COL = "_period"
DATE_NAMES = ("date", "quarter", "period", "observation_date", "obs_date", "month", "time")
ALL_TESTS = ("eg", "johansen", "ardl")
TEST_ALIASES = {
    "eg": "eg", "engle-granger": "eg", "engle_granger": "eg", "englegranger": "eg",
    "johansen": "johansen", "jo": "johansen",
    "ardl": "ardl", "bounds": "ardl",
}
PARAM_ALIASES = {
    "time_series_name": ("time_series_name", "series", "target", "y", "dependent"),
    "dependents": ("dependents", "independents", "regressors", "x", "exog"),
}


def err(msg):
    print(f"ERROR: {msg}", file=sys.stderr)


def read_table(path):
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"file not found: {path}")
    ext = path.suffix.lower()
    try:
        if ext in (".xlsx", ".xlsm", ".xls"):
            df = pd.read_excel(path)
        elif ext == ".tsv":
            df = pd.read_csv(path, sep="\t")
        elif ext in (".csv", ".txt", ""):
            # sep=None sniffs the delimiter
            df = pd.read_csv(path, sep=None, engine="python")
        else:
            raise ValueError(f"unsupported file type '{ext}' (use CSV or Excel)")
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"could not parse {path}: {e}") from e
    df.columns = [str(c).strip() for c in df.columns]
    return df


def to_periods(values, freq):
    values = values.astype(str).str.strip()
    try:
        # Handles period labels such as 2011Q1 or 2011-03.
        return pd.PeriodIndex(values, freq=freq)
    except Exception:
        return pd.PeriodIndex(pd.to_datetime(values), freq=freq)


def attach_periods(df, date_col, freq, label):
    if date_col is None:
        named = [c for c in df.columns if c.lower() in DATE_NAMES]
        unnamed = [c for c in df.columns if c == "" or c.lower().startswith("unnamed")]
        candidates = named + unnamed + [df.columns[0]]
        date_col = next((c for c in candidates if c in df.columns), None)
    if date_col not in df.columns:
        raise ValueError(f"date column '{date_col}' not in {label} file")
    try:
        periods = to_periods(df[date_col], freq)
    except Exception as e:
        raise ValueError(f"could not read dates from column '{date_col}' in {label} file: {e}") from e
    return df.assign(**{PERIOD_COL: periods})


def merge_sources(dep, indep, dep_date, indep_date, freq):
    dep = attach_periods(dep, dep_date, freq, "dependents")
    indep = attach_periods(indep, indep_date, freq, "independents")
    if indep[PERIOD_COL].duplicated().any():
        raise ValueError("independents file has more than one row per period")
    # Columns already in the dependents file keep their dependents-file values.
    indep = indep[[PERIOD_COL] + [c for c in indep.columns if c not in dep.columns]]
    return dep.merge(indep, on=PERIOD_COL, how="left").sort_values(PERIOD_COL)


def split_list(value):
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return []
    return [v.strip() for v in re.split(r"[;,]", str(value)) if v.strip()]


def opt(row, key, default, cast=str):
    value = row.get(key)
    if value is None or (isinstance(value, float) and np.isnan(value)) or str(value).strip() == "":
        return default
    return cast(str(value).strip()) if cast is not str else str(value).strip()


def normalize_params(params):
    params = params.rename(columns=lambda c: str(c).strip().lower())
    for canonical, aliases in PARAM_ALIASES.items():
        if canonical not in params.columns:
            found = next((a for a in aliases if a in params.columns), None)
            if found is None:
                raise ValueError(f"params file needs a '{canonical}' column")
            params = params.rename(columns={found: canonical})
    return params


def prepare_data(df, y, xs):
    missing = [c for c in [y] + xs if c not in df.columns]
    if missing:
        raise KeyError(f"columns not in source data: {', '.join(missing)}")
    df = df.sort_values(PERIOD_COL)
    data = df[[y] + xs].apply(pd.to_numeric, errors="coerce").dropna().reset_index(drop=True)
    if len(data) < 10:
        raise ValueError(f"only {len(data)} complete observations")
    return data


def coef_rows(res, names=None, prefix=""):
    """(term, coef, t-stat, p-value) for every regressor of a fitted OLS-type result."""
    names = names or list(res.model.exog_names)
    return [(prefix + n, b, t, p) for n, b, t, p in
            zip(names, np.asarray(res.params), np.asarray(res.tvalues), np.asarray(res.pvalues))]


def engle_granger(data, y, xs, trend, max_lag):
    # Step 1: long-run OLS regression of y on the regressors; ADF on its residuals.
    X = data[xs]
    if trend in ("c", "ct"):
        X = sm.add_constant(X, has_constant="add")
    if trend == "ct":
        X = X.assign(trend=np.arange(1, len(X) + 1))
    long_run = sm.OLS(data[y], X).fit()
    resid = long_run.resid
    lr_stat, _, _, adf = adfuller(resid, maxlag=max_lag, regression="n", autolag="AIC", regresults=True)
    lr_pval = mackinnonp(lr_stat, regression=trend, N=len(xs) + 1)
    adf_names = ["resid.L1"] + [f"D.resid.L{i}" for i in range(1, adf.usedlag + 1)]
    lr_coefs = coef_rows(long_run) + coef_rows(adf.resols, adf_names, prefix="ADF: ")

    # Step 2: short-run ECM
    #   dy_t = a + g*ect_{t-1} + sum_{i=0..p} b_i dx_{t-i} + sum_{j=1..p} f_j dy_{t-j} + u_t
    # with p chosen by AIC on a common sample.
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

    fits = [sm.OLS(frame["dy"], sm.add_constant(frame[ecm_columns(p)], has_constant="add")).fit()
            for p in range(max_lag + 1)]
    ecm = min(fits, key=lambda f: f.aic)
    # Cointegration test on the ECM: t on ect.L1 against MacKinnon (2010) critical values.
    sr_stat = ecm.tvalues["ect.L1"]
    sr_pval = mackinnonp(sr_stat, regression=trend, N=len(xs) + 1)
    return [
        ("EG_LongRun", lr_stat, lr_pval, lr_coefs),
        ("EG_ShortRun", sr_stat, sr_pval, coef_rows(ecm)),
    ]


def johansen_pvalue_bound(stat, crit):
    # crit columns are the 90%, 95%, 99% critical values.
    if stat > crit[2]:
        return "<0.01"
    if stat > crit[1]:
        return "<0.05"
    if stat > crit[0]:
        return "<0.10"
    return ">0.10"


def johansen(data, det_order, k_ar_diff):
    res = coint_johansen(data.values, det_order=det_order, k_ar_diff=k_ar_diff)
    out = [
        (f"Johansen trace (r<={r})", res.lr1[r], johansen_pvalue_bound(res.lr1[r], res.cvt[r]),
         [("", np.nan, np.nan, np.nan)])
        for r in range(len(res.lr1))
    ]

    # Rank-1 VECM: D.Y_t = alpha*beta'Y_{t-1} + sum_{i=1..k} G_i D.Y_{t-i} [+ deterministic terms]
    # One block of terms per equation; beta is normalized on the first series.
    cols = list(data.columns)
    vecm = VECM(data.values, k_ar_diff=k_ar_diff, coint_rank=1,
                deterministic=JOHANSEN_DETERMINISTIC.get(det_order, "co")).fit()
    coefs = [(f"beta: {c}", vecm.beta[j, 0],
              np.nan if j == 0 else vecm.tvalues_beta[j, 0],
              np.nan if j == 0 else vecm.pvalues_beta[j, 0])
             for j, c in enumerate(cols)]
    det_names = ["const", "trend"]
    for k, eq in enumerate(cols):
        eq_name = f"D.{eq}: "
        coefs.append((eq_name + "ec1", vecm.alpha[k, 0], vecm.tvalues_alpha[k, 0], vecm.pvalues_alpha[k, 0]))
        for d in range(vecm.det_coef.shape[1]):
            coefs.append((eq_name + det_names[d], vecm.det_coef[k, d],
                          vecm.tvalues_det_coef[k, d], vecm.pvalues_det_coef[k, d]))
        for i in range(k_ar_diff):
            for j, c in enumerate(cols):
                g = i * len(cols) + j
                coefs.append((eq_name + f"D.{c}.L{i + 1}", vecm.gamma[k, g],
                              vecm.tvalues_gamma[k, g], vecm.pvalues_gamma[k, g]))
    out.append(("Johansen VECM (rank 1)", np.nan, np.nan, coefs))
    return out


def ardl_bounds(data, y, xs, trend, max_lag, case):
    sel = ardl_select_order(data[y], max_lag, data[xs], max_lag, trend=trend, ic="aic")
    ar_lags = max(int(np.max(sel.model.ar_lags)) if sel.model.ar_lags else 0, 1)
    # The error-correction form needs at least one lag of every regressor.
    order = {}
    for x in xs:
        chosen = (sel.dl_lags or {}).get(x)
        order[x] = max(int(np.max(chosen)) if chosen else 0, 1)
    model = ARDL(data[y], ar_lags, data[xs], order, trend=trend)
    uecm = UECM.from_ardl(model).fit()
    bt = uecm.bounds_test(case=case)
    lag_desc = ",".join([str(ar_lags)] + [str(order[x]) for x in xs])
    return [(f"ARDL bounds F (ARDL({lag_desc}), case {case})", bt.stat, bt.p_values["upper"],
             coef_rows(uecm))]


def select_groups(source, row):
    """Yield (label, frame) for each panel this params row asks for."""
    group_col = opt(row, "group_column", None)
    if group_col is None:
        yield None, source
        return
    if group_col not in source.columns:
        raise KeyError(f"group_column '{group_col}' not in source data")
    keys = source[group_col].astype(str).str.strip()
    group_val = opt(row, "group_value", "*")
    values = keys.unique() if group_val in ("*", "all") else [group_val]
    for value in values:
        subset = source[keys == value]
        if subset.empty:
            raise ValueError(f"no rows where {group_col} == {value}")
        yield value, subset


def run_row(source, row):
    y = opt(row, "time_series_name", None)
    xs = split_list(row.get("dependents"))
    if y is None or not xs:
        raise ValueError("time_series_name and dependents are required")

    tests = [TEST_ALIASES.get(t.lower()) for t in split_list(row.get("tests"))] or list(ALL_TESTS)
    if None in tests:
        raise ValueError(f"unknown test in '{row.get('tests')}' (use eg, johansen, ardl)")

    trend = opt(row, "trend", "c").lower()
    if trend not in ("n", "c", "ct"):
        raise ValueError(f"trend must be n, c or ct, got '{trend}'")
    max_lag = opt(row, "max_lag", 4, lambda v: int(float(v)))
    det_order = opt(row, "det_order", 0, lambda v: int(float(v)))
    k_ar_diff = opt(row, "k_ar_diff", 1, lambda v: int(float(v)))
    case = opt(row, "ardl_case", 3, lambda v: int(float(v)))

    out = []
    for label, subset in select_groups(source, row):
        name = f"{y} [{label}]" if label else y
        try:
            data = prepare_data(subset, y, xs)
        except Exception as e:
            err(f"{name}: {e}")
            continue
        runners = {
            "eg": lambda: engle_granger(data, y, xs, trend, max_lag),
            "johansen": lambda: johansen(data, det_order, k_ar_diff),
            "ardl": lambda: ardl_bounds(data, y, xs, trend, max_lag, case),
        }
        for test in dict.fromkeys(tests):
            try:
                for test_name, stat, pval, coefs in runners[test]():
                    for term, coef, t, p in coefs:
                        out.append([label or "", test_name, term, coef, t, p, stat, pval])
            except Exception as e:
                err(f"{name} / {test}: {e}")
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description="Engle-Granger, Johansen and ARDL bounds tests.")
    parser.add_argument("dependents_file", help="file with the dependent series (CSV or Excel)")
    parser.add_argument("independents_file", help="file with the regressor series (CSV or Excel)")
    parser.add_argument("params", help="test parameters file (CSV or Excel)")
    parser.add_argument("-o", "--output", default=None,
                        help=f"output CSV (default: {OUTPUT_NAME} next to the dependents file)")
    parser.add_argument("--dep-date", default=None, help="date column in the dependents file")
    parser.add_argument("--indep-date", default=None, help="date column in the independents file")
    parser.add_argument("--freq", default="Q", help="period frequency used to align the files (default Q)")
    args = parser.parse_args(argv)

    try:
        source = merge_sources(read_table(args.dependents_file), read_table(args.independents_file),
                               args.dep_date, args.indep_date, args.freq)
        params = normalize_params(read_table(args.params))
    except (FileNotFoundError, ValueError) as e:
        err(e)
        return 1

    rows = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i, row in enumerate(params.to_dict("records"), start=1):
            try:
                rows.extend(run_row(source, row))
            except Exception as e:
                err(f"params row {i}: {e}")

    # Name the group column after the params' group_column when every row uses the same one.
    columns = list(OUTPUT_COLUMNS)
    group_cols = params.get("group_column", pd.Series(dtype=object)).dropna().astype(str).str.strip()
    if group_cols.nunique() == 1:
        columns[columns.index("group")] = group_cols.iloc[0]

    output = (Path(args.output) if args.output
              else Path(args.dependents_file).resolve().parent / OUTPUT_NAME)
    try:
        pd.DataFrame(rows, columns=columns).to_csv(output, index=False)
    except OSError as e:
        err(f"could not write {output}: {e}")
        return 1
    return 0 if rows else 2


if __name__ == "__main__":
    sys.exit(main())
