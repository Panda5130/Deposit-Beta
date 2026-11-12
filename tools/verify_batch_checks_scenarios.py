"""Scenario checks for tools/verify_batch.py: CHECKS = [fn, ...], each returns (name, ok, detail).
Runs the champions on the committed scenario CSVs (projection/scenarios/scn_*.csv)."""
import sys
from functools import lru_cache
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "projection"))
import run_scenarios as rs  # noqa: E402

pj, bt = rs.pj, rs.bt
CONV_TOL = 0.05      # |instant - ramp| at h=12 (rate pts); real gap is lambda-driven, observed max 0.023
SYM_TOL = 1e-6       # up/down mirror for symmetric champions
ASYM_MIN = 0.05      # KeyBank |asym| at some horizon must exceed this


@lru_cache(maxsize=1)
def projections():
    return rs.run(["All"], bt.DEFAULT_SELECT)


def _wide(h):
    p = projections()
    p = p[p.h == h]  # h counts from the last actual FFT quarter
    return p.pivot(index="bank", columns="scenario", values="rate")


def check_base_equals_flat():
    summary, estimates = bt.load_candidates()
    source = pj.bp.load_source(pj.DEFAULTS["dependents"], pj.DEFAULTS["independents"])
    q, last = rs.last_fft()  # flat at the last actual FFT (flat_8Q.csv is hard-coded 3.67)
    flat = rs.scenario_path("base", q, last)
    worst = 0.0
    for bank, g in projections()[lambda d: d.scenario == "base"].groupby("bank"):
        p = pj.Projection.champion(bank, estimates, summary, source)
        ref = p.project(flat)["rate_pf_clean"].values
        worst = max(worst, float(abs(g["rate"].values[:len(ref)] - ref).max()))
    return "base == flat projection at last FFT", worst < 1e-9, f"max abs diff {worst:.2e}"


def check_convergence():
    w = _wide(rs.H)
    gaps = pd.concat([(w["up_instant"] - w["up_ramp"]).abs(), (w["down_instant"] - w["down_ramp"]).abs()], axis=1).max(axis=1)
    p = projections()
    eq = p[(p.h == rs.H) & p.scenario.isin(["up_instant", "up_ramp"])]
    eqgap = eq.groupby("bank")["long_run_equilibrium"].apply(lambda s: s.max() - s.min()).max()
    ok = bool((gaps < CONV_TOL).all() and eqgap < 1e-9)
    return "instant/ramp converge by h=12", ok, f"max rate gap {gaps.max():.4f} ({gaps.idxmax()}); equilibrium gap {eqgap:.1e}; tol {CONV_TOL}"


def check_symmetry():
    w = _wide(rs.H)
    all_h = projections().pivot_table(index=["bank", "h"], columns="scenario", values="rate")
    asym = ((all_h["up_instant"] - all_h["base"]) + (all_h["down_instant"] - all_h["base"])).abs()
    non_key = asym[[not b.startswith("KeyBank") for b, _ in asym.index]]
    return "up/down mirror (symmetric champions)", bool(non_key.max() < SYM_TOL), f"max |up+down| {non_key.max():.2e}"


def check_keybank_asymmetry():
    all_h = projections().pivot_table(index=["bank", "h"], columns="scenario", values="rate")
    k = all_h[[b.startswith("KeyBank") for b, _ in all_h.index]]
    a = ((k["up_instant"] - k["base"]) + (k["down_instant"] - k["base"])).abs()
    return "KeyBank asymmetry", bool(a.max() > ASYM_MIN), f"max |up+down| {a.max():.3f} (> {ASYM_MIN})"


CHECKS = [check_base_equals_flat, check_convergence, check_symmetry, check_keybank_asymmetry]

if __name__ == "__main__":
    for f in CHECKS:
        print(f())
