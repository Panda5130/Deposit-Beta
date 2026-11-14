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
AUDIT_DIR = ROOT / "audit"
# Pre-change snapshots are kept as manifests (path, sha256 of the git blob content, baseline commit); the
# files themselves live in git history at the baseline commit.
MANIFESTS = {"pre_det_pruning": AUDIT_DIR / "2026-11-11_pre_det_pruning.manifest.csv",
             "pre_transfer_fix": AUDIT_DIR / "2026-11-13_pre_transfer_fix.manifest.csv"}
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


def manifest(path=MANIFESTS["pre_det_pruning"]):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def git_blob(commit, path):
    """Bytes of path at commit, or None when git has no such file."""
    r = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=ROOT, capture_output=True)
    return r.stdout if r.returncode == 0 else None


def blob_id(path=None, commit=None):
    """Git object id of the working-tree file (line endings normalised as git does) or of commit:path."""
    cmd = ["git", "rev-parse", f"{commit}:{path}"] if commit else ["git", "hash-object", "--", str(path)]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


# Checks ----------------------------------------------------------------------------------------
@check("pytest")
def check_pytest():
    cmd = [sys.executable, "-m", "pytest", "ecm_tests", "projection/test_project.py",
           "data_build/test_build_fft.py", "data_build/test_build_dataset.py",
           "projection/test_scenarios.py", "MAE_Backtesting/test_backtest_reference.py", "-q", "--tb=line", "-p", "no:cacheprovider"]
    out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    lines = [l for l in out.stdout.strip().splitlines() if l.strip()]
    last = lines[-1] if lines else out.stderr.strip()[-200:]
    return out.returncode == 0, last.strip("= ")


def _manifest_failures(name):
    rows = manifest(MANIFESTS[name])
    bad = []
    for r in rows:
        blob = git_blob(r["baseline_commit"], r["path"])
        if blob is None or hashlib.sha256(blob).hexdigest() != r["sha256"]:
            bad.append(r["path"])
    return rows, bad


@check("audit_manifest")
def check_audit_manifest():
    """Every pre_det_pruning manifest entry resolves to a file in git at its baseline commit with that sha256."""
    rows, bad = _manifest_failures("pre_det_pruning")
    return not bad, f"{len(rows)} entries in git, {len(bad)} missing/changed" + (f": {bad[:3]}" if bad else "")


@check("protected_originals_unchanged")
def check_protected():
    """The protected originals still equal their baseline blob (same git object id)."""
    m = {r["path"]: r for r in manifest(MANIFESTS["pre_det_pruning"])}
    bad = [p for p in PROTECTED if not (ROOT / p).exists() or blob_id(ROOT / p) != blob_id(p, m[p]["baseline_commit"])]
    return not bad, f"{len(PROTECTED)} originals vs baseline commit, {len(bad)} differ/missing" + (f": {bad}" if bad else "")


def _pruned_tables():
    import bank_plots as bp
    return {"symmetric": bp.CANDIDATE_FILES["estimates"], "asymmetric": bp.CANDIDATE_FILES["asym_estimates"]}


@check("no_outputs_outside_vintages")
def check_no_outputs_outside_vintages():
    """After a run, no tracked data/result file outside vintages/ is modified and none is new (source code is
    excluded: editing a script is not a run output). Runs write only under bank_plots.OUTPUT_ROOT."""
    out = subprocess.run(["git", "status", "--porcelain", "-uall"], cwd=ROOT, capture_output=True, text=True).stdout
    paths = [l[3:].strip().strip('"') for l in out.splitlines()]
    bad = [p for p in paths if not p.startswith("vintages/") and p.endswith((".csv", ".png", ".xlsx", ".json", ".log"))
           and p != "verify_summary.json" and not p.startswith("audit/")]
    return not bad, f"{len(paths)} changed paths, {len(bad)} result files outside vintages/" + (f": {bad[:3]}" if bad else "")


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
    import bank_plots as bp
    import deterministic_pruning as dp
    screen = dp.Screen(bp.vfile(dp.SCREEN_NAME))
    bad, n = [], 0
    for orig, path in zip(("ECM estimation results.csv", "ECM asymmetric estimation results.csv"),
                          _pruned_tables().values()):
        a = set(map(tuple, pd.read_csv(bp.vfile(orig), usecols=SPEC).drop_duplicates().to_numpy()))
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
    # the v2 data vintage's own files (the covid_liq run offers a new candidate, so its pruning path can differ)
    log = pd.read_csv(bp.DATA_ROOT / dp.LOG_NAME)
    pruned = set(map(tuple, log[log["action"].str.startswith("dropped")][SPEC].to_numpy()))
    pairs = [(bp.DATA_ROOT / "ECM estimation results.csv", bp.DATA_ROOT / "ECM estimation results (det pruned).csv"),
             (bp.DATA_ROOT / "ECM asymmetric estimation results.csv", bp.DATA_ROOT / "ECM asymmetric estimation results (det pruned).csv")]
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
    import bank_plots as bp
    import deterministic_pruning as dp
    log = pd.read_csv(bp.vfile(dp.LOG_NAME))
    need = [(bp.vfile("estimation result summary.csv"), False),
            (bp.vfile("asymmetric estimation result summary.csv"), True)]
    missing = 0
    for path, asym in need:
        spec = pd.read_csv(path, usecols=SPEC)
        spec = spec[spec[SPEC[3]].map(lambda t: bool(dp.det_of(t)))]  # models with a deterministic term
        logged = set(map(tuple, log[log["asymmetric"].astype(bool) == asym][SPEC].to_numpy()))
        missing += sum(tuple(r) not in logged for r in spec.to_numpy())
    return missing == 0, f"{len(log)} log rows; original models with deterministic terms not logged: {missing}"


@check("fft_end_equals_bank_end")
def check_fft_end():
    import bank_plots as bp
    bank = bp.to_periods(pd.read_csv(bp.DEPENDENTS["2011"],
                                     usecols=["quarter"])["quarter"]).max()
    bank8 = bp.to_periods(pd.read_csv(bp.DEPENDENTS["2008"],
                                      usecols=["quarter"])["quarter"]).max()
    ends = {n: bp.to_periods(pd.read_csv(ROOT / n).iloc[:, 0]).max() for n in ("FFT_2011-2026.csv", "FFT_2008-2026.csv")}
    try:
        for n, e in ends.items():
            bp.check_series_end(bank if "2011" in n else bank8, e, "bank data", n)
        scen = pd.read_csv(ROOT / "projection" / "scenarios" / "scn_base.csv").iloc[:, 0]
        first = bp.to_periods(scen).min()
        assert first == bank, f"scenarios start from {first}, expected the last actual {bank}"
    except (ValueError, AssertionError) as e:
        return False, str(e)
    return True, f"FFT ends {ends['FFT_2011-2026.csv']} = bank data end {bank}; scenarios start from it"


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


@check("doc_figure_links_resolve")
def check_doc_links():
    from urllib.parse import unquote
    doc = ROOT / "WIP Regional Banking Deposit Beta Analyses.md"
    links = re.findall(r"!\[[^\]]*\]\(<?([^)>]+)>?\)", doc.read_text(encoding="utf-8"))
    missing = [l for l in links if not (ROOT / unquote(l.strip())).is_file()]
    return not missing, f"{len(links)} image links; missing: {len(missing)}" + (f" ({missing[0]})" if missing else "")


# NIC Transformations cross-check (issue #20) ---------------------------------------------------
# FDIC /history logs charter mergers only. Every NIC transformation into a target bank (or into one
# of its Mode A predecessors) whose predecessor has an FDIC cert and RSSD must be covered: by a
# /history or supplementary event in merger_events_used_v2.csv, by the supplementary file, or by an
# explicit waiver. Without a cached NIC file the check is skipped with a warning (it does not fail).
NIC = {"transformations": None, "attributes": None}      # set by --nic-transformations / --nic-attributes
NIC_HOWTO = ("download CSV_TRANSFORMATIONS, CSV_ATTRIBUTES_ACTIVE and _CLOSED (RSSD->FDIC cert) from "
             "https://www.ffiec.gov/npw/FinancialReport/DataDownload, then pass --nic-transformations FILE "
             "[--nic-attributes FILE ...]")
NIC_CACHE = ROOT / "data_build" / "raw" / "nic" / "CSV_TRANSFORMATIONS.CSV"  # git-ignored download cache
NIC_WAIVERS = ROOT / "data_build" / "raw" / "nic_transfer_waivers.csv"
SUPPLEMENTARY = ROOT / "data_build" / "raw" / "supplementary_transfer_events.csv"
EVENTS_V2 = ROOT / "merger_events_used_v2.csv"


def _nic_events(path, attribute_paths):
    """NIC transformations as predecessor/successor RSSD + FDIC cert + date (upper-cased NIC columns)."""
    t = pd.read_csv(path, dtype=str).rename(columns=str.upper)
    t = t.rename(columns={"#ID_RSSD_PREDECESSOR": "ID_RSSD_PREDECESSOR"})
    out = pd.DataFrame({"pred_rssd": pd.to_numeric(t["ID_RSSD_PREDECESSOR"], errors="coerce"),
                        "succ_rssd": pd.to_numeric(t["ID_RSSD_SUCCESSOR"], errors="coerce"),
                        "date": pd.to_datetime(t["D_DT_TRANS"].str[:10].str.replace("-", ""), format="%Y%m%d",
                                               errors="coerce")})
    for side, col in (("pred", "PREDECESSOR_CERT"), ("succ", "SUCCESSOR_CERT")):
        out[f"{side}_cert"] = pd.to_numeric(t[col], errors="coerce") if col in t else float("nan")
    if attribute_paths:
        a = pd.concat([pd.read_csv(p, dtype=str, usecols=lambda c: c.upper().lstrip("#") in ("ID_RSSD", "ID_FDIC_CERT"))
                       .rename(columns=lambda c: c.upper().lstrip("#")) for p in attribute_paths])
        a = a.apply(pd.to_numeric, errors="coerce").dropna()
        a = a[a.ID_FDIC_CERT > 0].drop_duplicates("ID_RSSD").set_index("ID_RSSD").ID_FDIC_CERT
        for side in ("pred", "succ"):
            out[f"{side}_cert"] = out[f"{side}_cert"].fillna(out[f"{side}_rssd"].map(a))
    return out


@check("nic_transfers_covered")
def check_nic_transfers():
    """Every NIC transformation into a survivor in the merger tree is covered, same-charter / non-depository,
    or a deposit transfer the owner has waived. Classification and materiality: tools/nic_crosscheck.py."""
    need = [NIC_CACHE.parent / n for n in ("CSV_TRANSFORMATIONS.CSV", "CSV_ATTRIBUTES_ACTIVE.CSV", "CSV_ATTRIBUTES_CLOSED.CSV")]
    if not all(f.is_file() for f in need):
        print(f"WARNING nic_transfers_covered skipped: no cached NIC files; {NIC_HOWTO}", file=sys.stderr)
        return True, f"SKIPPED (warning): NIC files missing in {NIC_CACHE.parent}; {NIC_HOWTO}"
    import nic_crosscheck as nc
    e, n, _ = nc.classify()
    counts = e["class"].value_counts().to_dict()
    gaps = e[e["class"] == "deposit transfer"]
    detail = (f"{len(e)} NIC events into tree survivors: {counts}; {len(n)} tree members absorbed by a non-tree successor "
              f"(FDIC receiverships)")
    if len(gaps):
        detail += ": unwaived deposit transfers " + "; ".join(
            f"RSSD {int(r.pred_rssd)} (cert {int(r.pred_cert)}) -> {int(r.succ_cert)} {str(r.date)[:10]}" for r in gaps.itertuples())
    return len(gaps) == 0, detail


@check("audit_pre_transfer_fix_manifest")
def check_audit_v2():
    rows, bad = _manifest_failures("pre_transfer_fix")
    return not bad, f"{len(rows)} entries in git, {len(bad)} missing/changed" + (f": {bad[:3]}" if bad else "")


V2_RERUN_BANKS = {"Manufacturers and Traders Trust Company", "Old National Bank", "Huntington National Bank",
                  "SouthState Bank"}  # banks whose rate series differs from v1 (issue #20 plus amendment 1)


@check("v2_other_banks_rate_unchanged")
def check_v2_other_banks():
    """v2 changes rate_pf_clean only for the re-run banks; the other banks are identical (max abs diff 0)."""
    worst, n = 0.0, 0
    for s in ("2008", "2011"):
        a = pd.read_csv(ROOT / f"consolidated_fdic_quarterly_financials_{s}-2026_merger_adjusted.csv")
        b = pd.read_csv(ROOT / f"consolidated_fdic_quarterly_financials_{s}-2026_merger_adjusted_v2.csv")
        m = a.merge(b, on=["bank_name", "quarter"], how="outer", suffixes=("_1", "_2"), indicator=True)
        assert (m["_merge"] == "both").all(), "v1/v2 bank-quarter keys differ"
        m = m[~m.bank_name.isin(V2_RERUN_BANKS)]
        n += m.bank_name.nunique()
        worst = max(worst, float((m.rate_pf_clean_1 - m.rate_pf_clean_2).abs().max()))
    return worst == 0, f"{n // 2} other banks, max |rate_pf_clean v2 - v1| = {worst}"


def _register_module(module_name):
    """Register a sibling check module whose CHECKS entries return (label, ok, detail)."""
    import importlib
    if str(Path(__file__).resolve().parent) not in sys.path:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        mod = importlib.import_module(module_name)
    except Exception as e:  # noqa: BLE001  (an import failure is reported as a failed check)
        CHECKS[f"{module_name}:import"] = lambda e=e: (False, f"{type(e).__name__}: {str(e)[:150]}")
        return
    prefix = module_name.replace("verify_batch_checks_", "")
    for fn in mod.CHECKS:
        def run(fn=fn):
            label, ok, detail = fn()
            return ok, f"{label}: {detail}"
        CHECKS[f"{prefix}:{fn.__name__.removeprefix('check_')}"] = run


_register_module("verify_batch_checks_backtest")    # reference limits, trend freeze (issue #8)
_register_module("verify_batch_checks_scenarios")   # FFT +/-200 bp scenarios


# Runner ----------------------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--skip", nargs="*", default=[])
    ap.add_argument("-o", "--output", default=ROOT / "verify_summary.json")
    ap.add_argument("--nic-transformations", default=None, metavar="CSV",
                    help="cached NIC Transformations CSV for the nic_transfers_covered check (else skipped)")
    ap.add_argument("--nic-attributes", nargs="*", default=[], metavar="CSV",
                    help="NIC attributes CSV(s) mapping ID_RSSD -> ID_FDIC_CERT")
    args = ap.parse_args(argv)
    NIC["transformations"], NIC["attributes"] = args.nic_transformations, args.nic_attributes
    if not NIC["transformations"] and NIC_CACHE.is_file():  # the cached NIC download, when present
        NIC["transformations"] = str(NIC_CACHE)
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
