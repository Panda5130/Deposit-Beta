"""Documentation figures from the modeled dataset and the current champion outputs.

Usage:
    python docs/make_figures.py [--out-dir docs/figures_rebuild]

Writes:
    Historical Deposit Rates vs FFT.png              Figure 1: rate_pf_clean for all banks vs FFT
    <bank> - Actual vs Predicted.png                 champion's plot from "Actuals vs Predictions"
    <bank> - MAE Backtest 8Q.png                     from MAE_Backtesting/output
Run after "ECM workflow.py", plotting_workflow.py and MAE_Backtesting/run_backtest.py.
"""

import argparse
import shutil
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "MAE_Backtesting"))
import backtest as bt  # noqa: E402

DATA = ROOT / "consolidated_fdic_quarterly_financials_2011-2026_merger_adjusted.csv"
FFT = ROOT / "FFT_2011-2026.csv"


def figure_1(path):
    data = pd.read_csv(DATA, parse_dates=["quarter"])
    fft = pd.read_csv(FFT, index_col=0)["FFT"]
    fft.index = pd.PeriodIndex(fft.index, freq="Q").to_timestamp(how="end").normalize()
    fft = fft[fft.index <= data.quarter.max()]
    fig, ax = plt.subplots(figsize=(12, 6))
    for bank, g in data.groupby("bank_name"):
        ax.plot(g.quarter, g.rate_pf_clean, label=bank, linewidth=1.4)
    ax.plot(fft.index, fft.values, color="black", linestyle="--", linewidth=1.8, label="FFT (quarterly average)")
    ax.set_title("Deposit rate (rate_pf_clean, pro forma) vs. federal funds rate, "
                 f"{data.quarter.min():%Y}Q1 to {data.quarter.max().year}Q{data.quarter.max().quarter}")
    ax.set_ylabel("Percent")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8, ncol=2)
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Regenerate the documentation figures.")
    parser.add_argument("--out-dir", default=HERE / "figures_rebuild")
    args = parser.parse_args(argv)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    figure_1(out / "Historical Deposit Rates vs FFT.png")
    summary = pd.read_csv(ROOT / "estimation result summary.csv")
    for bank in summary.bank_name.unique():
        model = bt.select_model(summary, bank)
        name = bt.bp.INVALID_CHARS_RE.sub("-", "+".join(model)) + ".png"
        folder = bt.bp.INVALID_CHARS_RE.sub("-", bank)
        shutil.copy(ROOT / "Actuals vs Predictions" / folder / name, out / f"{bank} - Actual vs Predicted.png")
        shutil.copy(ROOT / "MAE_Backtesting" / "output" / folder / "MAE_backtest_8Q.png",
                    out / f"{bank} - MAE Backtest 8Q.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
