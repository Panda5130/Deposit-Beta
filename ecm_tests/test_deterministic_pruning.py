"""Tests for the deterministic-term pruning rule (deterministic_pruning.py) in the symmetric
one-step ECM ("ECM estimation.py") and the asymmetric variants.

Run: python -m pytest ecm_tests
"""

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "Beta_Backtesting"))
import beta_backtest as bb  # noqa: E402

est, asym = bb.est, bb.asym
dp = est.dp
Y, X = "rate_pf_clean", "FFT"
BANK, IC = "Test Bank", "AIC / ADF lag=1, ECM lag=1"
EG = "EG_LongRun"


def series(n=64, const=0.0, trend=0.0, seed=1):
    """(y, FFT) with long run y = const + trend*t + 0.4 FFT and lambda -0.4."""
    rng = np.random.default_rng(seed)
    fft = np.clip(np.cumsum(rng.choice([-0.5, -0.25, 0, 0.25, 0.5], n)) + 2.0, 0, None)
    y = np.empty(n)
    y[0] = const + 0.4 * fft[0]
    for t in range(1, n):
        target = const + trend * (t + 1) + 0.4 * fft[t - 1]
        y[t] = y[t - 1] - 0.4 * (y[t - 1] - target) + rng.normal(0, 0.02)
    idx = pd.period_range("2010Q1", periods=n, freq="Q")
    return pd.DataFrame({Y: y, X: fft}, index=idx)


def fit(data, trend_type):
    keys = (BANK, EG, IC, trend_type)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return est.fit_pruned(data, Y, keys, dp.det_of(trend_type), [X], [], 0.05)


def test_significant_terms_are_kept():
    res, det, _, log = fit(series(const=1.0, trend=0.02), "ct (constant + trend)")
    assert det == ["const", "trend"] and {"const", "trend"} <= set(res.params.index)
    assert [r["action"] for r in log] == ["kept (significant)"] * 2
    assert not any(r["form_differs_from_qualifying_test"] for r in log)


def test_insignificant_term_is_pruned_model_kept_and_flagged():
    res, det, _, log = fit(series(const=1.0), "ct (constant + trend)")
    assert res is not None and det == ["const"] and "trend" not in res.params.index
    assert log[0]["term"] == "trend" and log[0]["p_value"] >= 0.05 and log[0]["action"].startswith("dropped")
    assert log[-1]["term"] == "const" and log[-1]["action"] == "kept (significant)"
    assert all(r["qualifying_case"] == "ct" and r["remaining_form"] == "c" for r in log)
    assert all(r["form_differs_from_qualifying_test"] for r in log)


def test_trend_then_const_both_pruned():
    res, det, _, log = fit(series(), "ct (constant + trend)")
    assert res is not None and det == [] and not {"const", "trend"} & set(res.params.index)
    assert [r["term"] for r in log if r["action"].startswith("dropped")] == ["trend", "const"]
    assert log[-1]["remaining_form"] == "n"


def test_rows_and_forms():
    assert dp.tested_row("ARDL bounds F (ARDL(2,1), case 4)", "x", "trend") == "LR: trend"
    assert dp.tested_row("ARDL bounds F (ARDL(2,1), case 3)", "x", "const") == "const"
    assert dp.tested_row(EG, "c (constant)", "const") == "LR: const"
    assert dp.form_of("ARDL bounds F (ARDL(2,1), case 4)", ["const"]) == "case 3"
    assert dp.form_of("Johansen VECM (rank 1)", ["const"]) == "det_order 0"
    assert dp.form_of(EG, ["trend"]).startswith("trend only")


def test_asymmetric_variant_follows_the_same_rule():
    data = series(const=1.0)
    name = (BANK, EG + asym.ASYM_TAG, IC, "ct (constant + trend)")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        v, log = asym.build_pruned(data, Y, X, name, ["const", "trend"], [])
    assert v is not None and v.det == ["const"]
    assert log[0]["asymmetric"] and log[0]["term"] == "trend" and log[0]["action"].startswith("dropped")
    assert log[0]["form_differs_from_qualifying_test"]
