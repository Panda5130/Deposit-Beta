"""Step 2 of the ECM workflow: keep only the terms whose coefficient p-value is below alpha.

Usage (all arguments optional; defaults point at the files in this folder):
    python "ECM Param selection.py" [-i INPUT_CSV] [--alpha 0.05] [-o OUTPUT_CSV]

Reads "ECM model selection results.csv" and writes "ECM param selection results.csv" with
the same columns. Rows without a coefficient p-value (Johansen trace rows, the normalized
beta) are dropped along with the insignificant ones.
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
INPUT_NAME = "ECM model selection results.csv"
OUTPUT_NAME = "ECM param selection results.csv"


def err(msg):
    print(f"ERROR: {msg}", file=sys.stderr)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Keep terms with coefficient p-value < alpha.")
    parser.add_argument("-i", "--input", default=HERE / INPUT_NAME)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("-o", "--output", default=HERE / OUTPUT_NAME)
    args = parser.parse_args(argv)

    path = Path(args.input)
    if not path.is_file():
        err(f"file not found: {path}")
        return 1
    try:
        df = pd.read_csv(path)
    except Exception as e:
        err(f"could not parse {path}: {e}")
        return 1
    if "coef_p_value" not in df.columns:
        err(f"{path} has no coef_p_value column")
        return 1

    kept = df[pd.to_numeric(df["coef_p_value"], errors="coerce") < args.alpha]
    try:
        kept.to_csv(args.output, index=False)
    except OSError as e:
        err(f"could not write {args.output}: {e}")
        return 1
    return 0 if len(kept) else 2


if __name__ == "__main__":
    sys.exit(main())
