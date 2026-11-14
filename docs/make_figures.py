"""Documentation figures from the modeled dataset and the current champion outputs.

Usage:
    python docs/make_figures.py [--out-dir docs/figures] [--select out-of-sample|in-sample]

The champions follow MAE_Backtesting/backtest.py DEFAULT_SELECT (out-of-sample over the original
and asymmetric candidates) unless --select says otherwise. Writes:
    <bank> - Actual vs Predicted.png                 champion's plot from "Actuals vs Predictions"
    <bank> - MAE Backtest 8Q.png                     many-start-date backtest chart
    <bank> - Beta Backtest.png                       long-run theta (theta+-) at every start date from 2016Q1
    <bank> - Realized Beta 8Q.png                    realized vs model-implied beta by horizon, theta on a second axis
    All Banks - Beta Backtest.png                    theta at every start date, all banks
    All Banks - Realized Beta 8Q.png                 realized vs model-implied beta by horizon, one panel per bank
Run after "ECM workflow.py", plotting_workflow.py, MAE_Backtesting/run_backtest.py and
Beta_Backtesting/run_beta_backtest.py --realized (with the same --select).
Figure 1 (docs/Historical Deposit Rates vs FFT.png) is produced by EDA1_Stationarity_Tests.ipynb.
"""

import argparse
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "MAE_Backtesting"))
import backtest as bt  # noqa: E402


def _src(base, *parts):
    """File under the output vintage, else the same relative path in the next vintage of bank_plots.VINTAGE_CHAIN."""
    p = Path(base).joinpath(*parts)
    rel = p.relative_to(bt.bp.OUTPUT_ROOT)
    return bt.bp.vfile(rel.as_posix())


def main(argv=None):
    parser = argparse.ArgumentParser(description="Regenerate the documentation figures.")
    parser.add_argument("--out-dir", default=HERE / "figures")
    parser.add_argument("--select", choices=bt.SELECT_CHOICES, default=bt.DEFAULT_SELECT)
    args = parser.parse_args(argv)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    mae_dir, beta_dir = bt.output_dir(args.select), bt.output_dir(args.select, "Beta")
    summary, _ = bt.load_candidates()
    for bank in summary.bank_name.unique():
        model = bt.champion_model(summary, bank, select=args.select)
        name = bt.bp.INVALID_CHARS_RE.sub("-", "+".join(model)) + ".png"
        folder = bt.bp.INVALID_CHARS_RE.sub("-", bank)
        shutil.copy(bt.bp.vfile(f"Actuals vs Predictions/{folder}/{name}"), out / f"{bank} - Actual vs Predicted.png")
        shutil.copy(_src(mae_dir, folder, "MAE_backtest_multiorigin_8Q.png"), out / f"{bank} - MAE Backtest 8Q.png")
        shutil.copy(_src(beta_dir, folder, "beta_backtest_multiorigin.png"), out / f"{bank} - Beta Backtest.png")
        shutil.copy(_src(beta_dir, folder, "realized_beta_8Q.png"), out / f"{bank} - Realized Beta 8Q.png")
    shutil.copy(_src(beta_dir, "beta_backtest_multiorigin_all_banks.png"), out / "All Banks - Beta Backtest.png")
    shutil.copy(_src(beta_dir, "realized_beta_all_banks_8Q.png"), out / "All Banks - Realized Beta 8Q.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
