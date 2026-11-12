"""Rerun only what the 2026-11-11 batch changed, then verify.

    python tools/run_batch.py [--skip STEP ...] > batch.log 2>&1

Steps (in order; each is a subprocess, a failing step is logged and the rest still run):
  oos_backtest   MAE_Backtesting/run_backtest.py (All banks). The per-model error cache means only
                 models whose coefficients changed (Glacier, M&T after deterministic pruning) are refit;
                 the all-bank run keeps the peer-limit, assessment and summary files consistent.
  beta_backtest  Beta_Backtesting/run_beta_backtest.py --realized (All banks, cached the same way).
  trend_freeze   MAE_Backtesting/trend_freeze_comparison.py --banks SouthState (the only champion that
                 still carries a trend; Glacier's pre-pruning comparison is kept in
                 trend_freeze_comparison_glacier_prepruning.csv as a footnote).
  scenarios      projection/run_scenarios.py (all banks, current champions).
  compare_sel    MAE_Backtesting/compare_selection.py
  figures        docs/make_figures.py
  verify         tools/verify_batch.py -> verify_summary.json
Original cointegration / selection / estimation outputs are never touched.
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
STEPS = [
    ("oos_backtest", ["MAE_Backtesting/run_backtest.py", "--bank-name", "All"]),
    ("beta_backtest", ["Beta_Backtesting/run_beta_backtest.py", "--bank-name", "All", "--realized"]),
    ("trend_freeze", ["MAE_Backtesting/trend_freeze_comparison.py", "--banks", "SouthState"]),
    ("scenarios", ["projection/run_scenarios.py"]),
    ("compare_sel", ["MAE_Backtesting/compare_selection.py"]),
    ("figures", ["docs/make_figures.py"]),
    ("verify", ["tools/verify_batch.py"]),
]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--skip", nargs="*", default=[])
    ap.add_argument("--only", nargs="*")
    args = ap.parse_args(argv)
    failed = []
    for name, cmd in STEPS:
        if name in args.skip or (args.only and name not in args.only):
            continue
        t0 = time.time()
        print(f"=== {name}: {' '.join(cmd)}", flush=True)
        code = subprocess.run([PY, *cmd], cwd=ROOT).returncode
        print(f"=== {name}: exit {code} in {time.time() - t0:.0f}s", flush=True)
        if code != 0:
            failed.append(f"{name}({code})")
    print("=== BATCH DONE; failed: " + (", ".join(failed) or "none"), flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
