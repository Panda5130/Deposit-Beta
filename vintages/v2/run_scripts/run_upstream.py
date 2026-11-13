"""Upstream rerun for M&T and Old National only: screen -> respec -> ECM workflow, into up_<tag>/.

tag v1 = original data (reproducibility sanity, scratch only); tag v2 = corrected data.
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = sys.executable
BANKS = ["Manufacturers and Traders Trust Company", "Old National Bank"]
tag = sys.argv[1]
out = HERE / f"up_{tag}"
out.mkdir(exist_ok=True)
deps = HERE / f"deps2_{tag}.csv"
fft = HERE / "FFT_2011-2026.csv"


def run(*cmd):
    print("===", " ".join(map(str, cmd)), flush=True)
    r = subprocess.run([PY, *map(str, cmd)], cwd=HERE)
    print("=== exit", r.returncode, flush=True)
    if r.returncode:
        sys.exit(r.returncode)


run("Co-integration Tests.py", deps, fft, HERE / "test_params.csv", "-o", out / "Co-integration_results.csv")
run("FlaggedRates_co-integration_respecification.py", "--dependents", deps, "--independents", fft,
    "--banks", *BANKS, "-o", out / "co-integration_respecification_results.csv")
run("ECM workflow.py", "--cointegration", out / "Co-integration_results.csv",
    "--respecification", out / "co-integration_respecification_results.csv",
    "--dependents", deps, "--independents", fft, "--out-dir", out)
print("UPSTREAM DONE", tag, flush=True)
