"""Step 1 of the ECM workflow: keep only the models whose test p-value is below alpha.

Usage (all arguments optional; defaults point at the files in this folder):
    python "ECM model selection.py" [--cointegration FILE] [--respecification FILE]
        [--alpha 0.05] [-o OUTPUT_CSV]

Reads Co-integration_results.csv and co-integration_respecification_results.csv and writes
"ECM model selection results.csv" in the respecification layout:
    bank_name, IC/selected lag, trend type, test_name, term, coef, coef_stat, coef_p_value,
    model_stat, model_p_value

- The baseline file has no IC/selected lag or trend type columns, so they are filled in from
  its terms, using the same labels the respecification script writes (baseline settings:
  EG and ARDL lags by AIC, Johansen k_ar_diff fixed). A baseline spec that the
  respecification also ran appears once.
- Johansen VECM (rank 1) rows have no test statistic of their own; they take the
  Johansen trace (r<=0) stat and p-value of the same spec, the test that validates them.
- Johansen p-values are bounds read from critical values ("<0.01", "<0.05", "<0.10",
  ">0.10"); "<x" passes when x <= alpha.
- A model is kept only when its p-value is below alpha; rows without one are dropped.
- A kept EG_LongRun spec also gets the short-run lags (D.<v>.L<k>) of the EG_ShortRun
  regression with the same bank, IC/selected lag and trend type, relabelled EG_LongRun and
  carrying the EG_LongRun model stat and p-value. They are screened in step 2 and pruned in
  step 3 like every other family's short-run lags (OI-24).
"""

import argparse
import importlib.util
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUTPUT_NAME = "ECM model selection results.csv"
SPEC_KEYS = ["bank_name", "IC/selected lag", "trend type", "test_name"]
TRACE_R0 = "Johansen trace (r<=0)"
VECM = "Johansen VECM (rank 1)"
# How Co-integration Tests.py chooses lags (EG and ARDL by AIC, Johansen fixed k_ar_diff).
BASELINE_IC = {"eg": "AIC", "johansen": "fixed", "ardl": "AIC"}
LAG_RE = re.compile(r"\.L(\d+)$")
ARDL_RE = re.compile(r"ARDL\((?P<lags>[\d,]+)\), case (?P<case>\d)")


def err(msg):
    print(f"ERROR: {msg}", file=sys.stderr)


def load_module(path, name):
    # The file names have spaces/hyphens, so they can't be imported with a plain import.
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


respec = load_module(HERE / "FlaggedRates_co-integration_respecification.py", "respecification")


def max_lag(terms, pattern):
    lags = [int(LAG_RE.search(t).group(1)) for t in terms if re.match(pattern, t) and LAG_RE.search(t)]
    return max(lags, default=0)


def label_baseline(base):
    """Add IC/selected lag and trend type to the baseline rows, bank by bank."""
    labels = {}
    for bank, rows in base.groupby("bank_name"):
        terms = {test: set(r["term"].dropna()) for test, r in rows.groupby("test_name")}

        lr, sr = terms.get("EG_LongRun", set()), terms.get("EG_ShortRun", set())
        trend = "ct" if "trend" in lr else ("c" if "const" in lr else "n")
        adf_lag, ecm_lag = max_lag(lr, r"ADF: D\.resid"), max_lag(sr, r"D\.")
        eg = (f"{BASELINE_IC['eg']} / ADF lag={adf_lag}, ECM lag={ecm_lag}", respec.EG_TRENDS[trend])

        vecm = terms.get(VECM, set())
        det = 1 if any(t.endswith(": trend") for t in vecm) else (0 if any(t.endswith(": const") for t in vecm) else -1)
        k_ar_diff = max_lag(vecm, r".+: D\.")
        jo = (f"{BASELINE_IC['johansen']} / k_ar_diff={k_ar_diff}", respec.JOHANSEN_TRENDS[det])

        for test in rows["test_name"].unique():
            if test.startswith("EG_"):
                labels[(bank, test)] = eg
            elif test.startswith("Johansen"):
                labels[(bank, test)] = jo
            elif (m := ARDL_RE.search(test)):
                case = int(m["case"])
                trend_name, desc = respec.ARDL_CASES[case]
                labels[(bank, test)] = (f"{BASELINE_IC['ardl'].upper()} / ARDL({m['lags']})", f"{trend_name} - {desc}")

    keyed = base.apply(lambda r: labels.get((r["bank_name"], r["test_name"]), (np.nan, np.nan)), axis=1)
    base = base.copy()
    base.insert(1, "IC/selected lag", [k[0] for k in keyed])
    base.insert(2, "trend type", [k[1] for k in keyed])
    return base


def attach_trace_to_vecm(df):
    trace = (df[df["test_name"] == TRACE_R0]
             .drop_duplicates(SPEC_KEYS)[SPEC_KEYS[:3] + ["model_stat", "model_p_value"]])
    is_vecm = df["test_name"] == VECM
    filled = df[is_vecm].drop(columns=["model_stat", "model_p_value"]).merge(trace, on=SPEC_KEYS[:3], how="left")
    filled.index = df.index[is_vecm]
    df = df.copy()
    df.loc[is_vecm, ["model_stat", "model_p_value"]] = filled[["model_stat", "model_p_value"]]
    return df


def carry_eg_short_run(kept, combined):
    """Give each kept EG_LongRun spec the short-run lags of its own EG_ShortRun regression.

    EG_LongRun rows are the levels regression and its ADF lags only, so without this an
    EG long-run ECM would never be offered a D.<v>.L<k> term. The carried rows keep their
    EG_ShortRun coefficient p-values (screened in step 2 like any other short-run term) and
    take the EG_LongRun spec's model stat and p-value, the test that validates them.
    """
    is_lr = kept["test_name"] == "EG_LongRun"
    sr = combined[(combined["test_name"] == "EG_ShortRun") & combined["term"].astype(str).str.startswith("D.")]
    model = kept[is_lr].drop_duplicates(SPEC_KEYS[:3])[SPEC_KEYS[:3] + ["model_stat", "model_p_value"]]
    carried = sr.drop(columns=["model_stat", "model_p_value"]).merge(model, on=SPEC_KEYS[:3])
    carried = carried.assign(test_name="EG_LongRun")[kept.columns]
    # Place each spec's carried rows right after its own rows, so file order is unchanged.
    out = pd.concat([kept.assign(_part=0), carried.assign(_part=1)], ignore_index=True)
    first = out.groupby(SPEC_KEYS, sort=False).ngroup()
    return out.assign(_spec=first).sort_values(["_spec", "_part"], kind="stable").drop(columns=["_part", "_spec"])


def passes(p, alpha):
    if isinstance(p, str):
        p = p.strip()
        if p.startswith("<"):
            return float(p[1:]) <= alpha
        if p.startswith(">"):
            return False
    try:
        return float(p) < alpha
    except (TypeError, ValueError):
        return False


def read_csv(path):
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"file not found: {path}")
    try:
        return pd.read_csv(path)
    except Exception as e:
        raise ValueError(f"could not parse {path}: {e}") from e


def main(argv=None):
    parser = argparse.ArgumentParser(description="Keep cointegration models with p-value < alpha.")
    parser.add_argument("--cointegration", default=HERE / "Co-integration_results.csv")
    parser.add_argument("--respecification", default=HERE / "co-integration_respecification_results.csv")
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("-o", "--output", default=HERE / OUTPUT_NAME)
    args = parser.parse_args(argv)

    try:
        base = read_csv(args.cointegration)
        resp = read_csv(args.respecification)
    except (FileNotFoundError, ValueError) as e:
        err(e)
        return 1

    columns = list(resp.columns)
    missing = [c for c in columns if c not in base.columns and c not in ("IC/selected lag", "trend type")]
    if missing:
        err(f"cointegration file is missing columns: {', '.join(missing)}")
        return 1

    combined = pd.concat([label_baseline(base)[columns], resp[columns]], ignore_index=True)
    combined = combined.drop_duplicates(SPEC_KEYS + ["term"]).reset_index(drop=True)
    combined = attach_trace_to_vecm(combined)
    kept = combined[combined["model_p_value"].map(lambda p: passes(p, args.alpha))]
    kept = carry_eg_short_run(kept, combined)

    try:
        kept.to_csv(args.output, index=False)
    except OSError as e:
        err(f"could not write {args.output}: {e}")
        return 1
    return 0 if len(kept) else 2


if __name__ == "__main__":
    sys.exit(main())
