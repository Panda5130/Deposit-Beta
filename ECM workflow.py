"""Run the ECM workflow end to end: model selection -> parameter selection -> estimation.

Usage (all arguments optional; defaults point at the files in this folder):
    python "ECM workflow.py" [--cointegration FILE] [--respecification FILE]
        [--dependents FILE] [--independents FILE] [--y COLUMN] [--x COLUMN ...]
        [--alpha 0.05] [--out-dir DIR]

Steps (each a separate script in this folder, run with the same Python interpreter):
    1. ECM model selection.py  -> ECM model selection results.csv   (model p-value < alpha)
    2. ECM Param selection.py  -> ECM param selection results.csv   (coef p-value < alpha)
    3. ECM estimation.py       -> ECM estimation results.csv        (one-step ECM per model)
Stops at the first step that fails and exits with that step's return code.
"""

import argparse
import logging
import subprocess
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
log = logging.getLogger("ecm_workflow")


def run_step(number, script, args, output):
    log.info("[%d/3] %s", number, script)
    result = subprocess.run([sys.executable, str(HERE / script), *map(str, args)])
    if result.returncode != 0:
        log.error("[%d/3] %s failed with exit code %d", number, script, result.returncode)
        return result.returncode
    log.info("[%d/3] wrote %s (%d rows)", number, output, len(pd.read_csv(output)))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Cointegration results -> one-step ECM estimates.")
    parser.add_argument("--cointegration", default=HERE / "Co-integration_results.csv")
    parser.add_argument("--respecification", default=HERE / "co-integration_respecification_results.csv")
    parser.add_argument("--dependents", default=HERE / "consolidated_fdic_quarterly_financials_2011-2026_merger_adjusted.csv")
    parser.add_argument("--independents", default=HERE / "FFT_2011-2026.csv")
    parser.add_argument("--y", default="rate_pf_clean")
    parser.add_argument("--x", nargs="+", default=["FFT"])
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--out-dir", default=HERE)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)

    out = Path(args.out_dir)
    model_sel = out / "ECM model selection results.csv"
    param_sel = out / "ECM param selection results.csv"
    estimates = out / "ECM estimation results.csv"
    steps = [
        ("ECM model selection.py",
         ["--cointegration", args.cointegration, "--respecification", args.respecification,
          "--alpha", args.alpha, "-o", model_sel], model_sel),
        ("ECM Param selection.py", ["-i", model_sel, "--alpha", args.alpha, "-o", param_sel], param_sel),
        ("ECM estimation.py",
         ["-i", param_sel, "--dependents", args.dependents, "--independents", args.independents,
          "--y", args.y, "--x", *args.x, "--alpha", args.alpha, "-o", estimates], estimates),
    ]
    for number, (script, step_args, output) in enumerate(steps, start=1):
        code = run_step(number, script, step_args, output)
        if code:
            return code
    log.info("done: %s", estimates)
    return 0


if __name__ == "__main__":
    sys.exit(main())
