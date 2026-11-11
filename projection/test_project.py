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
    summary, estimates = bt.load_candidates()  # originals + asymmetric variants
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
    return [b for b, p in champions.items() if "trend" in p.det]


def flat_target(p, lr, value=FLAT_FFT):
    """c + delta*T + theta*x for a flat FFT path; for theta+- the partial sums after the one move at T+1."""
    target = lr.get("LR: const", 0.0) + lr.get("LR: trend", 0.0) * p.trend_T
    if "LR: FFT" in lr:
        return target + lr["LR: FFT"] * value
    move = value - p.history["FFT"].iloc[-1]
    pos = bp.partial_sum(p.history["FFT"], bp.POS).iloc[-1] + max(move, 0.0)
    neg = bp.partial_sum(p.history["FFT"], bp.NEG).iloc[-1] + min(move, 0.0)
    return target + lr["LR: FFT_pos"] * pos + lr["LR: FFT_neg"] * neg


def test_trend_champions_follow_their_trend_type(champions):
    # Deterministic pruning can drop an insignificant trend, never add one: a champion carries
    # a trend only if its qualifying trend type has one.
    allowed = {b for b, p in champions.items() if "trend" in bt.est.test_deterministics(p.model[2])}
    assert set(trend_banks(champions)) <= allowed


def test_flat_fft_converges_to_frozen_equilibrium(inputs, champions):
    estimates = inputs[0]
    for bank in trend_banks(champions):
        p = champions[bank]
        out = p.project(flat(p, LONG_H))
        lr = bt.bank_rows(estimates, bank).loc[lambda r: bt.model_mask(r, p.model)].set_index("term")["coef"]
        target = flat_target(p, lr)
        assert np.allclose(out["long_run_equilibrium"], target, atol=1e-12), bank  # equilibrium does not move
        assert (out["trend"] == p.trend_T).all(), bank
        y = out["rate_pf_clean"].to_numpy()
        assert abs(y[-1] - target) < 1e-8, bank  # converges to c + delta*T + theta*x
        assert abs(y[-1] - y[-101]) < 1e-8, bank  # and stops moving: no drift with time


def test_unfrozen_trend_drifts_by_delta(champions):
    # The diagnostic path shows what the freeze removes: delta pp per quarter, forever.
    for bank in trend_banks(champions):
        p = champions[bank]
        delta = p.long_run()["trend"]
        y = p.project(flat(p, LONG_H), freeze_trend=False)["rate_pf_clean"].to_numpy()
        assert abs((y[-1] - y[-101]) - 100 * delta) < 1e-8, bank
        assert abs(delta) > 1e-3, bank


def test_no_trend_champion_unaffected_by_freeze(inputs, champions):
    estimates = inputs[0]
    no_trend = [b for b, p in champions.items() if "trend" not in p.det]
    for bank in no_trend:
        p = champions[bank]
        frozen, free = p.project(flat(p, 40)), p.project(flat(p, 40), freeze_trend=False)
        pd.testing.assert_frame_equal(frozen, free)
        assert p.long_run()["trend"] == 0, bank
        lr = bt.bank_rows(estimates, bank).loc[lambda r: bt.model_mask(r, p.model)].set_index("term")["coef"]
        y = p.project(flat(p, LONG_H))["rate_pf_clean"].iloc[-1]
        assert abs(y - flat_target(p, lr)) < 1e-6, bank


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
        sub = pj.Projection(bank, p.model, p.history.loc[:origin], res.params, lr=getattr(res, "lr", None))
        got = sub.project(p.history["FFT"], freeze_trend=False).set_index("quarter")["rate_pf_clean"]
        assert np.allclose(got.to_numpy(), expected.to_numpy(), atol=1e-12, rtol=0), bank


def test_asymmetric_equilibrium_uses_partial_sums_from_T(champions):
    """theta+ FFT+ + theta- FFT-, with the scenario's partial sums run on from their values at T."""
    for bank, p in champions.items():
        if "FFT_pos" not in p.levels:
            continue
        path = pd.Series([4.0, 3.0, 3.5], index=pd.period_range(p.T + 1, periods=3, freq="Q"), name="FFT")
        out = p.project(path).set_index("quarter")
        lr = p.long_run()
        pos0 = bp.partial_sum(p.history["FFT"], bp.POS).iloc[-1]
        neg0 = bp.partial_sum(p.history["FFT"], bp.NEG).iloc[-1]
        moves = np.diff(np.concatenate([[p.history["FFT"].iloc[-1]], path.to_numpy()]))
        pos, neg = pos0 + np.cumsum(np.clip(moves, 0, None)), neg0 + np.cumsum(np.clip(moves, None, 0))
        assert np.allclose(pos + neg, path.to_numpy(), atol=1e-12)
        trend = p.trend_T if "trend" in p.det else 0.0
        expected = lr["const"] + lr["trend"] * trend + lr["FFT_pos"] * pos + lr["FFT_neg"] * neg
        assert np.allclose(out["long_run_equilibrium"].to_numpy(), expected, atol=1e-12), bank


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
