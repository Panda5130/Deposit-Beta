"""Predicted vs. actual plots for every surviving ECM specification of one bank.

Usage (all arguments except the bank optional; defaults point at the files in this folder):
    python bank_plots.py BANK_NAME [--estimates FILE] [--dependents FILE] [--independents FILE]
        [--y COLUMN] [--x COLUMN] [--group-column COLUMN] [--out-dir DIR]

"ECM estimation results.csv" holds coefficients, not fitted values, so each model's
predictions are rebuilt from the source data: the regressors are recreated under the
same term names (const, trend, y.L1, x.L1, D.v.Lk) and multiplied by the coefficients,
giving the one-step-ahead prediction of dy_t. The plot shows it in levels,
predicted y_t = y_{t-1} + predicted dy_t, against the actual y_t; the MAE is the same in
levels and in differences. "LR: ..." rows are derived from the others and are not used.

One PNG per (test_name, IC/selected lag, trend type) is written to
<out-dir>/<bank>/"{test_name}+{IC/selected lag}+{trend type}.png" (out-dir defaults to
"Actuals vs Predictions" in this folder). Characters Windows does not allow in file names
(\\ / : * ? " < > |) are replaced with "-".

plotting_workflow.py imports load_estimates, load_source and plot_bank to run every bank
while reading the input files once.
"""

import argparse
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT_DIR_NAME = "Actuals vs Predictions"
DEFAULTS = {
    "estimates": HERE / "ECM estimation results.csv",
    "dependents": HERE / "consolidated_fdic_quarterly_financials_2011-2026_merger_adjusted.csv",
    "independents": HERE / "FFT_2011-2026.csv",
    "y": "rate_pf_clean",
    "x": "FFT",
    "group_column": "bank_name",
    "out_dir": HERE / OUT_DIR_NAME,
}
SPEC_KEYS = ["test_name", "IC/selected lag", "trend type"]
SHORT_RUN_RE = re.compile(r"^D\.(?P<var>.+)\.L(?P<lag>\d+)$")
INVALID_CHARS_RE = re.compile(r'[\\/:*?"<>|]')


def err(msg):
    print(f"ERROR: {msg}", file=sys.stderr)


def read_csv(path):
    if not Path(path).is_file():
        raise FileNotFoundError(f"file not found: {path}")
    return pd.read_csv(path)


def load_estimates(path, group_column=DEFAULTS["group_column"]):
    estimates = read_csv(path)
    missing = [c for c in [group_column] + SPEC_KEYS + ["term", "coef"] if c not in estimates.columns]
    if missing:
        raise ValueError(f"{path} is missing columns: {', '.join(missing)}")
    return estimates


def to_periods(values):
    values = values.astype(str).str.strip()
    try:
        return pd.PeriodIndex(values, freq="Q")  # labels such as 2011Q1
    except Exception:
        return pd.PeriodIndex(pd.to_datetime(values), freq="Q")  # dates such as 2011-03-31


def load_source(dependents, independents):
    """Dependents (all banks) merged with the independents on the quarter."""
    dep, indep = read_csv(dependents), read_csv(independents)
    date_col = next((c for c in dep.columns if c.lower() in ("quarter", "date", "period")), dep.columns[0])
    dep = dep.assign(period=to_periods(dep[date_col]))
    indep = indep.assign(period=to_periods(indep[indep.columns[0]]))
    indep = indep[["period"] + [c for c in indep.columns if c not in dep.columns]]
    return dep.merge(indep, on="period", how="left").sort_values("period")


def bank_data(source, group_column, bank, y, x):
    """The bank's complete (y, x) observations in time order, indexed by quarter."""
    missing = [c for c in (group_column, y, x) if c not in source.columns]
    if missing:
        raise ValueError(f"source data has no column(s): {', '.join(missing)}")
    rows = source[source[group_column].astype(str).str.strip() == bank]
    if rows.empty:
        raise ValueError(f"no source rows where {group_column} == {bank}")
    data = rows.set_index("period")[[y, x]].apply(pd.to_numeric, errors="coerce").dropna()
    if data.empty:
        raise ValueError(f"{bank} has no complete {y}/{x} observations")
    return data


def regressor(data, term):
    """Rebuild the column that a term of the one-step ECM stands for."""
    if term == "const":
        return pd.Series(1.0, index=data.index)
    if term == "trend":
        return pd.Series(np.arange(1, len(data) + 1, dtype=float), index=data.index)
    if term.endswith(".L1") and term[:-3] in data.columns:
        return data[term[:-3]].shift(1)
    m = SHORT_RUN_RE.match(term)
    if m and m["var"] in data.columns:
        return data[m["var"]].diff().shift(int(m["lag"]))
    raise ValueError(f"unrecognised term '{term}'")


def predict(data, y, spec_rows):
    coefs = spec_rows[~spec_rows["term"].str.startswith("LR: ")].set_index("term")["coef"]
    if coefs.empty:
        raise ValueError("no coefficients to predict with")
    X = pd.concat({term: regressor(data, term) for term in coefs.index}, axis=1)
    frame = pd.concat([data[y].rename("actual"), data[y].shift(1).rename("previous"), X], axis=1).dropna()
    if frame.empty:
        raise ValueError("no observations left after building the lags")
    predicted = frame["previous"] + frame[coefs.index] @ coefs
    return frame["actual"], predicted


def plot_spec(bank, actual, predicted, keys, y, path):
    mae = float(np.mean(np.abs(actual - predicted)))
    dates = actual.index.to_timestamp(how="end")
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(dates, actual.values, color="#1f4e79", linewidth=2, label=f"Actual {y}")
    ax.plot(dates, predicted.values, color="#d9822b", linewidth=1.6, linestyle="--",
            label=f"Predicted {y} (one-step ECM)")
    ax.set_title(f"{bank}\n{keys[0]} | {keys[1]} | {keys[2]}", fontsize=10)
    ax.set_xlabel("Quarter")
    ax.set_ylabel(y)
    ax.grid(True, alpha=0.3)
    ax.text(0.02, 0.95, f"MAE = {mae:.4f}", transform=ax.transAxes, va="top", fontsize=10,
            bbox={"boxstyle": "round", "facecolor": "white", "edgecolor": "0.6"})
    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=False)
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return mae


def plot_bank(bank, estimates, source, out_dir, y=DEFAULTS["y"], x=DEFAULTS["x"],
              group_column=DEFAULTS["group_column"]):
    """Plot every surviving model of one bank into <out_dir>/<bank>/.

    Returns (written, gaps): [(file name, MAE)] and [(model label, reason)] for models
    that could not be plotted. Raises ValueError when the bank has no estimates or data.
    """
    rows = estimates[estimates[group_column].astype(str).str.strip() == bank]
    if rows.empty:
        raise ValueError(f"no surviving models for {bank} in the estimates")
    data = bank_data(source, group_column, bank, y, x)

    bank_dir = Path(out_dir) / bank
    bank_dir.mkdir(parents=True, exist_ok=True)
    written, gaps = [], []
    for keys, spec_rows in rows.groupby(SPEC_KEYS, sort=False):
        name = INVALID_CHARS_RE.sub("-", "+".join(map(str, keys))) + ".png"
        try:
            actual, predicted = predict(data, y, spec_rows)
            written.append((name, plot_spec(bank, actual, predicted, keys, y, bank_dir / name)))
        except Exception as e:
            gaps.append((" / ".join(map(str, keys)), str(e)))
    return written, gaps


def main(argv=None):
    parser = argparse.ArgumentParser(description="Predicted vs. actual ECM plots for one bank.")
    parser.add_argument("bank_name", help="bank to plot, exactly as in the estimates file")
    parser.add_argument("--estimates", default=DEFAULTS["estimates"])
    parser.add_argument("--dependents", default=DEFAULTS["dependents"])
    parser.add_argument("--independents", default=DEFAULTS["independents"])
    parser.add_argument("--y", default=DEFAULTS["y"], help="dependent column")
    parser.add_argument("--x", default=DEFAULTS["x"], help="regressor column")
    parser.add_argument("--group-column", default=DEFAULTS["group_column"])
    parser.add_argument("--out-dir", default=DEFAULTS["out_dir"], help="the bank's folder is created here")
    args = parser.parse_args(argv)

    try:
        estimates = load_estimates(args.estimates, args.group_column)
        source = load_source(args.dependents, args.independents)
        written, gaps = plot_bank(args.bank_name, estimates, source, args.out_dir,
                                  args.y, args.x, args.group_column)
    except (FileNotFoundError, ValueError) as e:
        err(e)
        if "no surviving models" in str(e):
            banks = sorted(estimates[args.group_column].astype(str).str.strip().unique())
            err(f"banks with estimates: {'; '.join(banks)}")
        return 1

    for name, mae in written:
        print(f"{name}  MAE={mae:.4f}")
    for label, reason in gaps:
        err(f"{args.bank_name} / {label}: not plotted ({reason})")
    print(f"{len(written)} plot(s) written to {Path(args.out_dir) / args.bank_name}")
    return 0 if written else 2


if __name__ == "__main__":
    sys.exit(main())
