"""Documentation figures from the modeled dataset and the current champion outputs.

Usage:
    python docs/make_figures.py [--out-dir docs/figures]

Writes:
    <bank> - Actual vs Predicted.png                 champion's plot from "Actuals vs Predictions"
    <bank> - MAE Backtest 8Q.png                     many-start-date backtest chart from MAE_Backtesting/output
Run after "ECM workflow.py", plotting_workflow.py and MAE_Backtesting/run_backtest.py --first-origin 2016Q1.
Figure 1 (docs/Historical Deposit Rates vs FFT.png) is produced by EDA1_Stationarity_Tests.ipynb.
"""

import argparse
import shutil
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "MAE_Backtesting"))
import backtest as bt  # noqa: E402

def main(argv=None):
    parser = argparse.ArgumentParser(description="Regenerate the documentation figures.")
    parser.add_argument("--out-dir", default=HERE / "figures")
    args = parser.parse_args(argv)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    summary = pd.read_csv(ROOT / "estimation result summary.csv")
    for bank in summary.bank_name.unique():
        model = bt.select_model(summary, bank)
        name = bt.bp.INVALID_CHARS_RE.sub("-", "+".join(model)) + ".png"
        folder = bt.bp.INVALID_CHARS_RE.sub("-", bank)
        shutil.copy(ROOT / "Actuals vs Predictions" / folder / name, out / f"{bank} - Actual vs Predicted.png")
        shutil.copy(ROOT / "MAE_Backtesting" / "output" / folder / "MAE_backtest_multiorigin_8Q.png",
                    out / f"{bank} - MAE Backtest 8Q.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
