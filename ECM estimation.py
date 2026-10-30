"""Step 3 of the ECM workflow: fit a one-step ECM for every model that survived steps 1-2.

Usage (all arguments optional; defaults point at the files in this folder):
    python "ECM estimation.py" [-i INPUT_CSV] [--dependents FILE] [--independents FILE]
        [--y COLUMN] [--x COLUMN ...] [-o OUTPUT_CSV]

One ECM per (bank_name, test_name, IC/selected lag, trend type) group of
"ECM param selection results.csv". The long-run equation y = c + theta*x enters the
short-run equation multiplied by the correction rate lambda, and everything is estimated
in one step:

    dy_t = lambda*(y_{t-1} - c - theta*x_{t-1}) + sum gamma_i dx_{t-i} + sum phi_j dy_{t-j} + e_t

It is fitted by OLS in its linear form (dy on const, y.L1, x.L1 and the short-run terms),
which is the same model: lambda is the y.L1 coefficient, and the long-run coefficients
c = -const/lambda and theta = -(x.L1 coef)/lambda are recovered with delta-method standard
errors and reported as "LR: ..." rows.

Which regressors a group gets comes from the terms that survived step 2:
    const / trend                         deterministic terms (EG, ARDL, VECM "D.y: const")
    D.<v>.L<k>                            short-run lags (VECM "D.y: D.<v>.L<k>" likewise)
    ect.L1, y.L1, "D.y: ec1"              the correction rate: adds y.L1 and every x.L1
    FFT, FFT.L1, "beta: FFT"              long-run regressors: add x.L1
A group needs a surviving correction-rate term (EG_LongRun has none by construction and
only needs a long-run regressor); otherwise there is no error correction and it is
skipped. ADF terms and the other VECM equations (D.<x>: ...) are not part of this equation.

Output columns: bank_name, test_name, IC/selected lag, trend type, term, coef, t_stat, p_value
(trend type is included because IC/selected lag alone does not identify a model).

Also writes "estimation result summary.csv" (--summary): one row per model with
bank_name, test_name, IC/selected lag, trend type, MAE, where MAE is the mean absolute
in-sample residual of dy (equal to the MAE of the implied fitted levels y_{t-1} + dy_hat).
"""

import argparse
import importlib.util
import re
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

HERE = Path(__file__).resolve().parent
INPUT_NAME = "ECM param selection results.csv"
OUTPUT_NAME = "ECM estimation results.csv"
GROUP_KEYS = ["bank_name", "test_name", "IC/selected lag", "trend type"]
OUTPUT_COLUMNS = GROUP_KEYS + ["term", "coef", "t_stat", "p_value"]
SUMMARY_NAME = "estimation result summary.csv"
SUMMARY_COLUMNS = GROUP_KEYS + ["MAE"]
SHORT_RUN_RE = re.compile(r"^D\.(?P<var>.+)\.L(?P<lag>\d+)$")


def load_module(path, name):
    # The file name has a space and a hyphen, so it can't be imported with a plain import.
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ct = load_module(HERE / "Co-integration Tests.py", "cointegration_tests")


def ecm_spec(test_name, terms, y, xs):
    """Map a group's surviving terms onto (deterministic terms, long-run xs, short-run lags)."""
    det, levels, short_run = [], set(), set()
    has_correction = test_name == "EG_LongRun"
    for term in terms:
        if test_name.startswith("Johansen VECM"):
            if term.startswith("beta: "):
                if term[len("beta: "):] in xs:
                    levels.add(term[len("beta: "):])
                continue
            equation, _, term = term.partition(": ")
            if equation != f"D.{y}":
                continue
            if term == "ec1":
                has_correction = True
                levels.update(xs)
                continue
        if term.startswith("ADF: "):
            continue
        if term in ("const", "trend"):
            det.append(term)
        elif term == "ect.L1":
            has_correction = True
            levels.update(xs)
        elif term == f"{y}.L1":
            has_correction = True
        elif (m := SHORT_RUN_RE.match(term)):
            short_run.add((m["var"], int(m["lag"])))
        elif term in xs or term.removesuffix(".L1") in xs:
            levels.add(term.removesuffix(".L1"))
    if not has_correction:
        raise ValueError("no significant error-correction term survived")
    if not levels:
        raise ValueError("no long-run regressor survived")
    unknown = sorted({v for v, _ in short_run} - {y, *xs})
    if unknown:
        raise ValueError(f"short-run terms for unknown series: {', '.join(unknown)}")
    return det, [x for x in xs if x in levels], sorted(short_run, key=lambda t: (t[0] != y, t[0], t[1]))


def fit_one_step(data, y, det, levels, short_run):
    diffs = data.diff()
    X = pd.DataFrame(index=data.index)
    if "const" in det:
        X["const"] = 1.0
    if "trend" in det:
        X["trend"] = np.arange(1, len(data) + 1, dtype=float)
    X[f"{y}.L1"] = data[y].shift(1)
    for x in levels:
        X[f"{x}.L1"] = data[x].shift(1)
    for var, lag in short_run:
        X[f"D.{var}.L{lag}"] = diffs[var].shift(lag)
    frame = pd.concat([diffs[y].rename("dy"), X], axis=1).dropna()
    return sm.OLS(frame["dy"], frame[X.columns]).fit()


def long_run_rows(res, y, det, levels):
    """Long-run coefficients -b/lambda for each deterministic term and x, by the delta method."""
    lam_name = f"{y}.L1"
    lam, cov = res.params[lam_name], res.cov_params()
    rows = []
    for name in det + [f"{x}.L1" for x in levels]:
        b = res.params[name]
        grad = np.array([b / lam ** 2, -1.0 / lam])  # d(-b/lam)/d(lam), d(-b/lam)/d(b)
        sub = cov.loc[[lam_name, name], [lam_name, name]].values
        se = float(np.sqrt(grad @ sub @ grad))
        theta = -b / lam
        t = theta / se
        rows.append((f"LR: {name.removesuffix('.L1')}", theta, t, 2 * stats.t.sf(abs(t), res.df_resid)))
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description="Fit one-step ECMs for the selected models.")
    parser.add_argument("-i", "--input", default=HERE / INPUT_NAME)
    parser.add_argument("--dependents", default=HERE / "consolidated_fdic_quarterly_financials_2011-2026_merger_adjusted.csv")
    parser.add_argument("--independents", default=HERE / "FFT_2011-2026.csv")
    parser.add_argument("--y", default="rate_pf_clean", help="dependent column")
    parser.add_argument("--x", nargs="+", default=["FFT"], help="regressor column(s)")
    parser.add_argument("--group-column", default="bank_name")
    parser.add_argument("-o", "--output", default=HERE / OUTPUT_NAME)
    parser.add_argument("--summary", default=HERE / SUMMARY_NAME, help="per-model MAE CSV")
    args = parser.parse_args(argv)

    try:
        if not Path(args.input).is_file():
            raise FileNotFoundError(f"file not found: {args.input}")
        selected = pd.read_csv(args.input)
        source = ct.merge_sources(ct.read_table(args.dependents), ct.read_table(args.independents),
                                  None, None, "Q")
    except (FileNotFoundError, ValueError) as e:
        ct.err(e)
        return 1
    missing = [c for c in GROUP_KEYS + ["term"] if c not in selected.columns]
    if missing:
        ct.err(f"{args.input} is missing columns: {', '.join(missing)}")
        return 1

    rows, summary, data_cache = [], [], {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for keys, group in selected.groupby(GROUP_KEYS, sort=False):
            bank, test_name = keys[0], keys[1]
            label = " / ".join(map(str, keys))
            try:
                if bank not in data_cache:
                    _, subset = next(ct.select_groups(source, {"group_column": args.group_column,
                                                               "group_value": bank}))
                    data_cache[bank] = ct.prepare_data(subset, args.y, args.x)
                det, levels, short_run = ecm_spec(test_name, group["term"].dropna(), args.y, args.x)
                res = fit_one_step(data_cache[bank], args.y, det, levels, short_run)
            except Exception as e:
                ct.err(f"{label}: {e}")
                continue
            fitted = list(zip(res.params.index, res.params, res.tvalues, res.pvalues))
            for term, coef, t, p in fitted + long_run_rows(res, args.y, det, levels):
                rows.append([*keys, term, coef, t, p])
            summary.append([*keys, float(np.mean(np.abs(res.resid)))])

    try:
        pd.DataFrame(rows, columns=OUTPUT_COLUMNS).to_csv(args.output, index=False)
        pd.DataFrame(summary, columns=SUMMARY_COLUMNS).to_csv(args.summary, index=False)
    except OSError as e:
        ct.err(f"could not write output: {e}")
        return 1
    return 0 if rows else 2


if __name__ == "__main__":
    sys.exit(main())
