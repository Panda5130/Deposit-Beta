"""Downstream rerun in the scratch copy (v2 data + merged candidate files installed under the usual names)."""
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = sys.executable
STEPS = [
    ("oos_backtest", ["MAE_Backtesting/run_backtest.py", "--bank-name", "All"]),
    ("beta_backtest", ["Beta_Backtesting/run_beta_backtest.py", "--bank-name", "All", "--realized"]),
    ("is_backtest", ["MAE_Backtesting/run_backtest.py", "--horizon", "8Q", "--bank-name", "All",
                     "--select", "in-sample", "--first-origin", "2016Q1"]),
    ("is_beta", ["Beta_Backtesting/run_beta_backtest.py", "--select", "in-sample"]),
    ("compare_sel", ["MAE_Backtesting/compare_selection.py"]),
    ("scenarios", ["projection/run_scenarios.py"]),
    ("model_form", ["model_form/run_model_form.py"]),
]
only = sys.argv[1:]
for name, cmd in STEPS:
    if only and name not in only:
        continue
    t0 = time.time()
    print(f"=== {name}: {' '.join(cmd)}", flush=True)
    code = subprocess.run([PY, *cmd], cwd=HERE).returncode
    print(f"=== {name}: exit {code} in {time.time() - t0:.0f}s", flush=True)
print("=== DOWNSTREAM DONE", flush=True)
