"""Scenario tests. Run: python -m pytest projection/test_scenarios.py -q --tb=line"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import pytest  # noqa: E402
import verify_batch_checks_scenarios as vc  # noqa: E402


def test_scenario_files_match_last_fft():
    q, last = vc.rs.last_fft()
    for name in vc.rs.SCENARIOS:
        s = vc.pj.read_scenario(vc.rs.SCEN_DIR / f"scn_{name}.csv")
        assert s.index[0] == q and abs(s.iloc[0] - last) < 1e-9
        assert len(s) == vc.rs.H + 1
    assert abs(vc.pj.read_scenario(vc.rs.SCEN_DIR / "scn_up_ramp.csv").iloc[-1] - (last + 2)) < 1e-9


@pytest.mark.parametrize("check", vc.CHECKS, ids=lambda f: f.__name__)
def test_check(check):
    name, ok, detail = check()
    assert ok, f"{name}: {detail}"
