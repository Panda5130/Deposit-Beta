"""Amend data vintage v2 after the four NIC-found transfers (owner approved 2026-11-13).

    python vintages/v2/run_scripts/amend_v2.py upstream | merge | downstream | harvest

Runs in a staging output root (DEPOSIT_OUTPUT_VINTAGE=v2_stage, so vintages/v2 and the v1 files are never written
until `harvest`): screen -> respecification -> ECM workflow (pruned) and the unpruned estimates for the affected banks,
merged into the full 7-bank candidate files, then the downstream chain on them. `harvest` copies every staged file that
differs from its v1 file into vintages/v2 (v1 = repo root, never touched) and deletes v2 files that no longer differ.
"""
import hashlib
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
STAGE = ROOT / "vintages" / "v2_stage"
V2 = ROOT / "vintages" / "v2"
BANKS = ["Manufacturers and Traders Trust Company", "Huntington National Bank", "SouthState Bank"]
ENV = {**os.environ, "DEPOSIT_OUTPUT_VINTAGE": "v2_stage"}
PY = sys.executable
UP, UPU = STAGE / "upstream", STAGE / "upstream_unpruned"
FFT = ROOT / "FFT_2011-2026.csv"
DEPS = UP / "deps3.csv"


def run(*cmd):
    print("===", " ".join(str(c) for c in cmd)[:230], flush=True)
    r = subprocess.run([PY, *map(str, cmd)], cwd=ROOT, env=ENV)
    print("=== exit", r.returncode, flush=True)
    if r.returncode:
        sys.exit(r.returncode)


def upstream():
    UP.mkdir(parents=True, exist_ok=True), UPU.mkdir(parents=True, exist_ok=True)
    d = pd.read_csv(ROOT / "consolidated_fdic_quarterly_financials_2011-2026_merger_adjusted_v2.csv")
    d[d.bank_name.isin(BANKS)].to_csv(DEPS, index=False)
    run("Co-integration Tests.py", DEPS, FFT, ROOT / "test_params.csv", "-o", UP / "Co-integration_results.csv")
    run("FlaggedRates_co-integration_respecification.py", "--dependents", DEPS, "--independents", FFT, "--banks", *BANKS,
        "-o", UP / "co-integration_respecification_results.csv")
    run("ECM workflow.py", "--cointegration", UP / "Co-integration_results.csv",
        "--respecification", UP / "co-integration_respecification_results.csv",
        "--dependents", DEPS, "--independents", FFT, "--out-dir", UP)
    run("ECM estimation.py", "-i", UP / "ECM param selection results.csv", "--dependents", DEPS, "--independents", FFT,
        "--no-prune-deterministics", "-o", UPU / "ECM estimation results.csv", "--summary", UPU / "estimation result summary.csv")
    code = ("import importlib.util,sys;s=importlib.util.spec_from_file_location('a','ECM asymmetric variants.py');"
            "m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.PROTECTED=[];"
            f"sys.exit(m.main(['-i',r'{UP / 'ECM model selection results.csv'}','--dependents',r'{DEPS}','--independents',r'{FFT}',"
            f"'--out-dir',r'{UPU}','--no-prune-deterministics','--pruning-log',r'{UPU / 'unused_log.csv'}']))")
    run("-c", code)


def base(name):
    p = V2 / name
    return pd.read_csv(p if p.is_file() else ROOT / name)


def merge():
    n = 0
    for d in (UP, UPU):
        for p in sorted(d.glob("*.csv")):
            if p.name in ("deps3.csv",) or p.name.startswith("unused"):
                continue
            b, new = base(p.name), pd.read_csv(p)
            order = {k: i for i, k in enumerate(dict.fromkeys(b.bank_name))}
            m = pd.concat([b[~b.bank_name.isin(BANKS)], new], ignore_index=True)
            m = m.iloc[m.bank_name.map(order).fillna(99).argsort(kind="stable")]
            m.to_csv(STAGE / p.name, index=False)
            n += 1
    print(n, "merged candidate files ->", STAGE)


STEPS = [
    ("oos_backtest", ["MAE_Backtesting/run_backtest.py", "--bank-name", "All"]),
    ("beta_backtest", ["Beta_Backtesting/run_beta_backtest.py", "--bank-name", "All", "--realized"]),
    ("is_backtest", ["MAE_Backtesting/run_backtest.py", "--horizon", "8Q", "--bank-name", "All", "--select", "in-sample",
                     "--first-origin", "2016Q1"]),
    ("is_beta", ["Beta_Backtesting/run_beta_backtest.py", "--select", "in-sample"]),
    ("compare_sel", ["MAE_Backtesting/compare_selection.py"]),
    ("scenarios", ["projection/run_scenarios.py"]),
    ("model_form", ["model_form/run_model_form.py"]),
]


def downstream(only=()):
    run("vintages/v2_covid/run_scripts/seed_cache.py")
    for name, cmd in STEPS:
        if only and name not in only:
            continue
        t0 = time.time()
        run(*cmd)
        print(f"=== {name} {time.time() - t0:.0f}s", flush=True)


def norm(p):
    return hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def harvest():
    keep = set()
    for p in STAGE.rglob("*"):
        rel = p.relative_to(STAGE)
        if not p.is_file() or rel.parts[0] in ("upstream", "upstream_unpruned") or p.suffix in (".py", ".pyc"):
            continue
        q = ROOT / rel
        if q.is_file() and norm(p) == norm(q):
            continue
        keep.add(rel)
        (V2 / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, V2 / rel)
    gone = [p for p in V2.rglob("*") if p.is_file() and p.relative_to(V2) not in keep
            and p.relative_to(V2).parts[0] != "run_scripts" and p.name != "README.md"]
    for p in gone:
        p.unlink()
    print(len(keep), "files in vintages/v2;", len(gone), "removed (no longer differ from v1)")


if __name__ == "__main__":
    {"upstream": upstream, "merge": merge, "downstream": lambda: downstream(sys.argv[2:]), "harvest": harvest}[sys.argv[1]]()
