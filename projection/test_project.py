"""Tests for the projection layer and the trend freeze (issue #7). Run: python -m pytest projection"""

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import project as pj  # noqa: E402

bt, bp = pj.bt, pj.bp
FLAT_FFT, LONG_H = 3.67, 300


@pytest.fixture(scope="module")
def inputs():
    estimates = bp.load_estimates(pj.DEFAULTS["estimates"])
    summary = bp.read_csv(pj.DEFAULTS["summary"])
    source = bp.load_source(pj.DEFAULTS["dependents"], pj.DEFAULTS["independents"])
    return estimates, summary, source


@pytest.fixture(scope="module")
def champions(inputs):
    estimates, summary, source = inputs
    banks = sorted(summary["bank_name"].astype(str).str.strip().unique())
    return {bank: pj.Projection.champion(bank, estimates, summary, source) for bank in banks}


def flat(p, h, value=FLAT_FFT):
    return pd.Series(value, index=pd.period_range(p.T + 1, periods=h, freq="Q"), name="FFT")


def trend_banks(champions):
    return [b for b, p in champions.items() if "trend" in p.params]


def test_trend_champions_are_the_expected_three(champions):
    assert set(trend_banks(champions)) == {"First Horizon Bank", "Glacier Bank",
                                           "Manufacturers and Traders Trust Company"}


def test_flat_fft_converges_to_frozen_equilibrium(inputs, champions):
    estimates = inputs[0]
    for bank in trend_banks(champions):
        p = champions[bank]
        out = p.project(flat(p, LONG_H))
        lr = bt.bank_rows(estimates, bank).loc[lambda r: bt.model_mask(r, p.model)].set_index("term")["coef"]
        target = lr["LR: const"] + lr["LR: trend"] * p.trend_T + lr["LR: FFT"] * FLAT_FFT
        assert np.allclose(out["long_run_equilibrium"], target, atol=1e-12), bank  # equilibrium does not move
        assert (out["trend"] == p.trend_T).all(), bank
        y = out["rate_pf_clean"].to_numpy()
        assert abs(y[-1] - target) < 1e-8, bank  # converges to c + delta*T + theta*x
        assert abs(y[-1] - y[-101]) < 1e-8, bank  # and stops moving: no drift with time


def test_unfrozen_trend_drifts_by_delta(champions):
    # The diagnostic path shows what the freeze removes: delta pp per quarter, forever.
    for bank in trend_banks(champions):
        p = champions[bank]
        _, delta, _ = p.long_run()
        y = p.project(flat(p, LONG_H), freeze_trend=False)["rate_pf_clean"].to_numpy()
        assert abs((y[-1] - y[-101]) - 100 * delta) < 1e-8, bank
        assert abs(delta) > 1e-3, bank


def test_no_trend_champion_unaffected_by_freeze(champions):
    no_trend = [b for b, p in champions.items() if "trend" not in p.params]
    assert len(no_trend) == 4
    for bank in no_trend:
        p = champions[bank]
        frozen, free = p.project(flat(p, 40)), p.project(flat(p, 40), freeze_trend=False)
        pd.testing.assert_frame_equal(frozen, free)
        c, delta, theta = p.long_run()
        assert c == 0 and delta == 0, bank
        assert abs(frozen["rate_pf_clean"].iloc[-1] - theta * FLAT_FFT) < 1e-3, bank


def test_csv_coefficients_equal_full_sample_refit(inputs, champions):
    estimates = inputs[0]
    for bank, p in champions.items():
        spec = bt.bank_rows(estimates, bank).loc[lambda r: bt.model_mask(r, p.model)]
        res = bt.MAEBacktest(bank, p.model, 0, p.history, spec).fit(p.T)
        pd.testing.assert_series_equal(res.params.sort_index(), p.params.sort_index(), check_names=False,
                                       atol=1e-10, rtol=0)


def test_recursion_matches_backtest_forecast(inputs, champions):
    # Without the freeze, projecting from an origin with realised FFT is the backtest's dynamic forecast.
    estimates = inputs[0]
    for bank, p in champions.items():
        spec = bt.bank_rows(estimates, bank).loc[lambda r: bt.model_mask(r, p.model)]
        backtest = bt.MAEBacktest(bank, p.model, 8, p.history, spec)
        origin = p.history.index[-9]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = backtest.fit(origin)
        _, expected = backtest.forecast(res, origin)
        sub = pj.Projection(bank, p.model, p.history.loc[:origin], res.params)
        got = sub.project(p.history["FFT"], freeze_trend=False).set_index("quarter")["rate_pf_clean"]
        assert np.allclose(got.to_numpy(), expected.to_numpy(), atol=1e-12, rtol=0), bank


def test_scenario_quarters_up_to_T_are_ignored(champions):
    p = champions["KeyBank National Association"]
    full = pd.concat([p.history["FFT"], flat(p, 4)])
    pd.testing.assert_frame_equal(p.project(full), p.project(flat(p, 4)))


def test_scenario_with_gap_or_late_start_is_rejected(champions):
    p = champions["Glacier Bank"]
    with pytest.raises(ValueError, match="without gaps"):
        p.project(flat(p, 4).drop(p.T + 2))
    with pytest.raises(ValueError, match="without gaps"):
        p.project(flat(p, 4).iloc[1:])
    with pytest.raises(ValueError, match="no quarter after"):
        p.project(p.history["FFT"])


def test_cli_writes_every_bank(tmp_path):
    out = tmp_path / "flat.csv"
    assert pj.main(["--scenario", str(pj.HERE / "scenarios" / "flat_8Q.csv"), "-o", str(out)]) == 0
    df = pd.read_csv(out)
    assert list(df.columns) == pj.OUTPUT_COLUMNS
    assert df["bank_name"].nunique() == 7 and len(df) == 7 * 8
    assert df["quarter"].iloc[0] == "2026Q3" and df["quarter"].iloc[7] == "2028Q2"
