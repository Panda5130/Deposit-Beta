"""Batch verification: run every registered check and write a short verify_summary.json.

    python tools/verify_batch.py [--only NAME ...] [--skip NAME ...] [-o verify_summary.json]

Each check is a function registered with @check("name") that returns (passed: bool, detail: str),
the detail being one line. A check that raises counts as failed with the exception as detail.
To add a check, define a function below with the decorator; nothing else needs changing.
The exit code is 0 when every check that ran passed, 1 otherwise.
"""

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
CHECKS = {}
AUDIT_DIR = ROOT / "audit" / "2026-11-11_pre_det_pruning"
# Originals the owner protects ("do not delete them no matter what"): must match the audit copy.
PROTECTED = ["Co-integration_results.csv", "co-integration_respecification_results.csv",
             "ECM model selection results.csv", "ECM param selection results.csv",
             "ECM estimation results.csv", "estimation result summary.csv",
             "ECM asymmetric estimation results.csv", "asymmetric estimation result summary.csv",
             "ECM asymmetric tests.csv"]
SPEC = ["bank_name", "test_name", "IC/selected lag", "trend type"]


def check(name):
    def register(fn):
        CHECKS[name] = fn
        return fn
    return register


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def manifest(folder=AUDIT_DIR):
    with open(folder / "MANIFEST.sha256.csv", newline="") as f:
        return {r["path"]: r["sha256"] for r in csv.DictReader(f)}


# Checks ----------------------------------------------------------------------------------------
@check("pytest")
def check_pytest():
    cmd = [sys.executable, "-m", "pytest", "ecm_tests", "projection/test_project.py",
           "data_build/test_build_fft.py", "-q", "--tb=line", "-p", "no:cacheprovider"]
    out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    lines = [l for l in out.stdout.strip().splitlines() if l.strip()]
    last = lines[-1] if lines else out.stderr.strip()[-200:]
    return out.returncode == 0, last.strip("= ")


@check("audit_manifest")
def check_audit_manifest():
    m = manifest()
    bad = [p for p, h in m.items() if sha256(AUDIT_DIR / p) != h]
    return not bad, f"{len(m)} audit copies, {len(bad)} changed" + (f": {bad[:3]}" if bad else "")


@check("protected_originals_unchanged")
def check_protected():
    m = manifest()
    bad = [p for p in PROTECTED if not (ROOT / p).exists() or sha256(ROOT / p) != m[p]]
    return not bad, f"{len(PROTECTED)} originals vs audit copy, {len(bad)} differ/missing" + (f": {bad}" if bad else "")


def _pruned_tables():
    import bank_plots as bp
    return {"symmetric": bp.CANDIDATE_FILES["estimates"], "asymmetric": bp.CANDIDATE_FILES["asym_estimates"]}


@check("det_terms_significant")
def check_det_invariant():
    """Every surviving deterministic term has p < 0.05 (on the row deterministic_pruning tests),
    and no model carries a term its qualifying case does not have."""
    import deterministic_pruning as dp
    bad, n, n_terms = [], 0, 0
    for path in _pruned_tables().values():
        for keys, g in pd.read_csv(path).groupby(SPEC, sort=False):
            n += 1
            p = dict(zip(g["term"], g["p_value"]))
            split = "ect_pos.L1" in p
            det = [d for d in ("const", "trend") if d in p or f"LR: {d}" in p]
            if set(det) - set(dp.det_of(keys[3])):
                bad.append(f"{keys[0][:10]} {keys[1][:25]} has {det} beyond its case")
            for term in det:
                n_terms += 1
                if not p[dp.tested_row(keys[1], keys[3], term, split)] < dp.ALPHA:
                    bad.append(f"{keys[0][:10]} {keys[1][:25]} {keys[2]} {term}")
    return not bad, f"{n} models, {n_terms} deterministic terms, {len(bad)} violate" + (f": {bad[:3]}" if bad else "")


@check("models_kept_and_passed_screen")
def check_screen():
    """Pruning keeps every model: same model keys as the unpruned outputs, all of them screened."""
    import deterministic_pruning as dp
    screen = dp.Screen()
    bad, n = [], 0
    for orig, path in zip(("ECM estimation results.csv", "ECM asymmetric estimation results.csv"),
                          _pruned_tables().values()):
        a = set(map(tuple, pd.read_csv(ROOT / orig, usecols=SPEC).drop_duplicates().to_numpy()))
        b = set(map(tuple, pd.read_csv(path, usecols=SPEC).drop_duplicates().to_numpy()))
        if a != b:
            bad.append(f"{Path(path).name}: {len(a - b)} model(s) lost, {len(b - a)} new")
        keys = pd.read_csv(path, usecols=SPEC).drop_duplicates()
        for k in keys.itertuples(index=False):
            n += 1
            if (k[0], dp.base_test_name(k[1]), k[2], k[3]) not in screen.passed:
                bad.append(" / ".join(map(str, k)))
    return not bad, f"{n} surviving models, {len(bad)} not in the screen" + (f": {bad[:2]}" if bad else "")


@check("unaffected_rows_carried_over")
def check_carry():
    """Models with no term dropped are identical to the unpruned originals."""
    import bank_plots as bp
    import deterministic_pruning as dp
    log = pd.read_csv(ROOT / dp.LOG_NAME)
    pruned = set(map(tuple, log[log["action"].str.startswith("dropped")][SPEC].to_numpy()))
    pairs = [(ROOT / "ECM estimation results.csv", bp.CANDIDATE_FILES["estimates"]),
             (ROOT / "ECM asymmetric estimation results.csv", bp.CANDIDATE_FILES["asym_estimates"])]
    worst, missing = 0.0, 0
    for orig, new in pairs:
        new = pd.read_csv(new)
        new = new[[tuple(r) not in pruned for r in new[SPEC].to_numpy()]]
        m = pd.read_csv(orig).merge(new, on=SPEC + ["term"], how="right", suffixes=("_o", "_n"))
        missing += int(m["coef_o"].isna().sum())
        worst = max(worst, float((m["coef_o"] - m["coef_n"]).abs().max()), float((m["p_value_o"] - m["p_value_n"]).abs().max()))
    return missing == 0 and worst < 1e-9, (f"{len(pruned)} pruned models excluded; unpruned rows absent from "
                                           f"originals: {missing}; max |diff| {worst:.1e}")


@check("pruning_log_complete")
def check_log():
    import deterministic_pruning as dp
    log = pd.read_csv(ROOT / dp.LOG_NAME)
    need = [(ROOT / "estimation result summary.csv", False), (ROOT / "asymmetric estimation result summary.csv", True)]
    missing = 0
    for path, asym in need:
        spec = pd.read_csv(path, usecols=SPEC)
        spec = spec[spec[SPEC[3]].map(lambda t: bool(dp.det_of(t)))]  # models with a deterministic term
        logged = set(map(tuple, log[log["asymmetric"].astype(bool) == asym][SPEC].to_numpy()))
        missing += sum(tuple(r) not in logged for r in spec.to_numpy())
    return missing == 0, f"{len(log)} log rows; original models with deterministic terms not logged: {missing}"


@check("oos_champions_are_candidates")
def check_champions():
    sys.path.insert(0, str(ROOT / "MAE_Backtesting"))
    import backtest as bt
    summary, _ = bt.load_candidates()
    bad = []
    for bank in sorted(summary["bank_name"].unique()):
        try:
            bt.champion_model(summary, bank)
        except Exception as e:  # noqa: BLE001
            bad.append(f"{bank.split()[0]}: {str(e)[:60]}")
    return not bad, f"{summary['bank_name'].nunique()} banks; champion not in candidates: {len(bad)}" + (
        f" ({bad[0]})" if bad else "")


# Runner ----------------------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--skip", nargs="*", default=[])
    ap.add_argument("-o", "--output", default=ROOT / "verify_summary.json")
    args = ap.parse_args(argv)
    names = [n for n in (args.only or CHECKS) if n not in args.skip]
    results = []
    for name in names:
        try:
            ok, detail = CHECKS[name]()
        except Exception as e:  # noqa: BLE001
            ok, detail = False, f"{type(e).__name__}: {str(e)[:150]}"
        results.append({"check": name, "pass": bool(ok), "detail": re.sub(r"\s+", " ", str(detail))})
    summary = {"when": datetime.now().isoformat(timespec="seconds"), "all_pass": all(r["pass"] for r in results),
               "n_checks": len(results), "n_failed": sum(not r["pass"] for r in results), "checks": results}
    Path(args.output).write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(f"{len(results) - summary['n_failed']}/{len(results)} checks passed -> {Path(args.output).name}")
    return 0 if summary["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
