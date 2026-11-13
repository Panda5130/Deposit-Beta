"""Backtest checks for tools/verify_batch.py (issue #8 reference limits, trend freeze).

Each check returns (name, ok, detail); CHECKS lists them for registration. Nothing here writes to the
repo's frozen references or the original estimation outputs: freezing happens in a temp directory.
check_reference_reproduces_limits refits every bank's champion for h up to 12 (minutes); the others
are fast. Rerun per changed bank: python -m pytest MAE_Backtesting/test_backtest_reference.py -q --tb=line
and these checks (CHECKS) after any change to a bank's champion, data or the backtest code.
"""

import json
import sys
import shutil
import tempfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "MAE_Backtesting"))
import backtest as bt  # noqa: E402
import run_backtest as rb  # noqa: E402

NO_TREND_BANK = "Huntington"
OUT_DIR = bt.output_dir(bt.DEFAULT_SELECT)


def check_reference_reproduces_limits(horizon=8):
    """A reference frozen now gives, for N=8, exactly the limits file of today's out-of-sample run."""
    name = "backtest: frozen reference reproduces today's limits"
    today = pd.read_csv(OUT_DIR / f"backtest_multiorigin_limits_{horizon}Q.csv")
    with tempfile.TemporaryDirectory() as tmp:
        # Work on a temp copy of the error cache (overlaid with the active data vintage's entries) so the
        # check never rewrites the output folder's cache (issue #20: a v2 run must not touch v1 outputs).
        work, refdir = Path(tmp) / "out", Path(tmp) / "ref"
        shutil.copytree(OUT_DIR / "cache", work / "cache")
        vcache = bt.bp.DATA_ROOT / OUT_DIR.relative_to(bt.bp.OUTPUT_ROOT) / "cache"
        if vcache.is_dir() and vcache != OUT_DIR / "cache":
            shutil.copytree(vcache, work / "cache", dirs_exist_ok=True)
        refdir.mkdir()
        code = rb.main(["--freeze-reference", "--reference-trigger", "initial", "--reference-dir", str(refdir),
                        "--horizon", f"{horizon}Q", "--out-dir", str(work)])
        if code != 0:
            return name, False, f"freeze exited {code}"
        ref, meta = bt.load_reference(refdir / "reference_v1.csv")
        derived = bt.limits_from_reference(ref, horizon)
    same = derived.reset_index(drop=True).round(10).equals(today[derived.columns].round(10))
    return name, same, f"{len(derived)} bands, {meta['champions'].__len__()} banks" if same else f"derived:\n{derived}\ntoday:\n{today}"


def check_freeze_trend_noop_without_trend():
    """--freeze-trend leaves a no-trend champion's forecasts unchanged (and its cache key)."""
    name = f"backtest: freeze-trend is a no-op for {NO_TREND_BANK}"
    summary, estimates = bt.load_candidates()
    source = bt.bp.load_source(bt.bp.DEFAULTS["dependents"], bt.bp.DEFAULTS["independents"])
    gc = bt.bp.DEFAULTS["group_column"]
    bank = next(b for b in rb.resolve_banks("All", summary, gc) if NO_TREND_BANK.lower() in b.lower())
    cache = bt.ErrorCache(OUT_DIR / "cache", per_model=True)
    data = bt.bp.bank_data(source, gc, bank, bt.bp.DEFAULTS["y"], bt.bp.DEFAULTS["x"])
    args = type("A", (), dict(select=bt.DEFAULT_SELECT, first_origin="2016Q1", y=bt.bp.DEFAULTS["y"],
                              x=bt.bp.DEFAULTS["x"], group_column=gc, min_train=20))
    model, _ = rb.choose_model(args, summary, estimates, data, bank, cache, 8)
    rows = bt.bank_rows(estimates, bank, gc)
    spec = rows[bt.model_mask(rows, model)]
    plain, frozen = (bt.MAEBacktest(bank, model, 8, data, spec, freeze_trend=f) for f in (False, True))
    if "trend" in plain.det:
        return name, False, f"{bank} champion has a trend; pick another no-trend bank"
    origin = data.index[-9]
    a = plain.forecast(plain.fit(origin), origin)[1]
    b = frozen.forecast(frozen.fit(origin), origin)[1]
    ok = bool((a == b).all()) and plain.spec() == frozen.spec()
    return name, ok, f"max abs diff {float((a - b).abs().max()):.2e}"


def check_references_immutable():
    """Existing frozen references still match their hashes; freezing again adds a version, never overwrites."""
    name = "backtest: frozen references are immutable"
    problems = []
    for k in bt.reference_versions(bt.REFERENCE_DIR):
        try:
            bt.load_reference(bt.reference_paths(bt.REFERENCE_DIR, k)[0])
        except Exception as e:  # noqa: BLE001
            problems.append(f"v{k}: {e}")
    import test_backtest_reference as t
    tables = {f"Bank{i}": bt.summarise_errors(t.synthetic_errors(i), bt.REF_HORIZON) for i in range(5)}
    with tempfile.TemporaryDirectory() as tmp:
        first, _ = t.freeze(tables, tmp)
        before = first.read_bytes()
        second, _ = t.freeze(tables, tmp, "annual-review")
        if first.read_bytes() != before or second.name != "reference_v2.csv":
            problems.append("a second freeze changed v1 or did not create v2")
        try:
            with open(first, "x"):
                problems.append("v1 could be re-opened for creation")
        except FileExistsError:
            pass
        meta = json.loads(first.with_suffix(".json").read_text())
        if meta["approved_by"] != "":
            problems.append("a fresh freeze must have empty approved_by")
    return name, not problems, "; ".join(problems) or "ok"


CHECKS = [check_references_immutable, check_freeze_trend_noop_without_trend, check_reference_reproduces_limits]
