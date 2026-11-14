"""COVID liquidity-injection dummy (covid_liq): calendar step 2020Q2-2021Q4, short-run only, 0 in projections."""
import importlib.util
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "projection"))
import bank_plots as bp  # noqa: E402
import project as pj  # noqa: E402

K = ["bank_name", "test_name", "IC/selected lag", "trend type"]


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / file)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_dummy_is_a_calendar_step():
    q = pd.period_range("2019Q4", "2022Q2", freq="Q")
    d = bp.covid_series(q)
    assert list(d[d == 1].index) == list(pd.period_range("2020Q2", "2021Q4", freq="Q"))
    assert d.sum() == 7 and d.loc[pd.Period("2020Q1", "Q")] == 0 and d.loc[pd.Period("2022Q1", "Q")] == 0
    # a regressor for any quarter depends only on that quarter (no look-ahead): a truncated path agrees
    full = bp.regressor(pd.DataFrame(index=q), bp.COVID)
    assert full.loc[:pd.Period("2020Q3", "Q")].equals(bp.regressor(pd.DataFrame(index=q[:4]), bp.COVID))


def test_dummy_is_zero_in_projection():
    source = bp.load_source(pj.DEFAULTS["dependents"], pj.DEFAULTS["independents"])
    bank = "Glacier Bank"
    hist = bp.bank_data(source, "bank_name", bank, "rate_pf_clean", "FFT")
    params = pd.Series({"const": 0.05, "rate_pf_clean.L1": -0.2, "FFT.L1": 0.1, bp.COVID: 5.0})
    p = pj.Projection(bank, ("m", "1", "n"), hist, params)
    future = pd.Series(3.0, index=pd.period_range(p.T + 1, periods=6, freq="Q"), name="FFT")
    with_dummy = p.project(future)
    p0 = pj.Projection(bank, ("m", "1", "n"), hist, params.drop(bp.COVID))
    assert np.allclose(with_dummy["rate_pf_clean"], p0.project(future)["rate_pf_clean"], atol=0, rtol=0)
    assert (bp.regressor(pd.DataFrame(index=future.index), bp.COVID) == 0).all()
    inside = pd.Series(3.0, index=pd.period_range("2021Q1", periods=3, freq="Q"), name="FFT")
    import pytest
    with pytest.raises(ValueError):
        pj.Projection(bank, ("m", "1", "n"), hist.iloc[:-25], params).project(inside)


def test_specs_without_dummy_reproduce_v2(tmp_path):
    """Without --covid the estimation reproduces the v2 symmetric det-pruned estimates exactly."""
    out, summ, log = tmp_path / "e.csv", tmp_path / "s.csv", tmp_path / "l.csv"
    r = subprocess.run([sys.executable, str(ROOT / "ECM estimation.py"), "-o", str(out), "--summary", str(summ),
                        "--pruning-log", str(log)], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-300:]
    ref = pd.read_csv(bp.DATA_ROOT / "ECM estimation results (det pruned).csv")
    new = pd.read_csv(out)
    m = new.merge(ref, on=K + ["term"], how="outer", suffixes=("_n", "_v2"), indicator=True)
    assert (m["_merge"] == "both").all()
    assert float((m.coef_n - m.coef_v2).abs().max()) < 1e-12  # same arithmetic; rounding noise only


def test_no_write_outside_output_root():
    """Every default output location sits under bank_plots.OUTPUT_ROOT (never the original output/ folders)."""
    root = bp.OUTPUT_ROOT
    import backtest as bt
    assert bt.output_dir("out-of-sample").is_relative_to(root) and bt.output_dir("in-sample", "Beta").is_relative_to(root)
    assert Path(bp.DEFAULTS["out_dir"]).is_relative_to(root) and bp.VINTAGE_DIR.is_relative_to(root)
    rs = load("run_scenarios_t", "projection/run_scenarios.py")
    assert all(p.is_relative_to(root) for p in (rs.OUT_DIR, rs.FIG_DIR, rs.SCEN_DIR))
    src = (ROOT / "model_form" / "run_model_form.py").read_text(encoding="utf-8")
    assert 'OUT = bp.out_path("model_form/output")' in src
