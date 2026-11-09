"""Tests for the asymmetric ECM variants, their forecasts and the realized-beta backtest.

Run: python -m pytest ecm_tests
"""

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "Beta_Backtesting"))
import beta_backtest as bb  # noqa: E402

bt, bp, est, asym = bb.bt, bb.bp, bb.est, bb.asym
Y, X = "rate_pf_clean", "FFT"
POS, NEG = bp.POS, bp.NEG


def synthetic(n=60, seed=0):
    """A quarterly (y, FFT) pair with rises and falls in FFT and a y that error-corrects slowly
    from above (lambda -0.1) and fast from below (lambda -0.6), long run y = 0.1 + 0.4 FFT."""
    rng = np.random.default_rng(seed)
    fft = np.clip(np.cumsum(rng.choice([-0.5, -0.25, 0, 0, 0.25, 0.5], n)) + 2.0, 0, None)
    y = np.empty(n)
    y[0] = 0.4 * fft[0] + 0.1
    for t in range(1, n):
        e = y[t - 1] - 0.1 - 0.4 * fft[t - 1]
        lam = -0.1 if e > 0 else -0.6
        y[t] = y[t - 1] + lam * e + 0.2 * max(fft[t] - fft[t - 1], 0) + rng.normal(0, 0.06)
    index = pd.period_range("2011Q1", periods=n, freq="Q") if n <= 80 else pd.period_range("1911Q1", periods=n, freq="Q")
    return pd.DataFrame({Y: y, X: fft}, index=index)


@pytest.fixture(scope="module")
def data():
    return synthetic()


@pytest.fixture(scope="module")
def candidates():
    summary, estimates = bt.load_candidates()
    source = bp.load_source(bp.DEFAULTS["dependents"], bp.DEFAULTS["independents"])
    return summary, estimates, source


# 1. Identities ---------------------------------------------------------------------------------
def test_partial_sums_add_up_to_the_level(data):
    pos, neg = bp.partial_sum(data[X], POS), bp.partial_sum(data[X], NEG)
    assert np.allclose(pos + neg, data[X], atol=1e-12, rtol=0)
    assert (pos.diff().dropna() >= 0).all() and (neg.diff().dropna() <= 0).all()
    assert neg.iloc[0] == 0 and pos.iloc[0] == data[X].iloc[0]  # the start level is in FFT+
    lagged = bp.regressor(data, f"{X}{POS}.L1") + bp.regressor(data, f"{X}{NEG}.L1")
    assert np.allclose(lagged.dropna(), bp.regressor(data, f"{X}.L1").dropna(), atol=1e-12, rtol=0)


def test_split_differences_add_up(data):
    for var in (Y, X):
        for lag in (0, 1, 3):
            whole = bp.regressor(data, f"D.{var}.L{lag}")
            parts = bp.regressor(data, f"D.{var}{POS}.L{lag}") + bp.regressor(data, f"D.{var}{NEG}.L{lag}")
            assert np.allclose(parts.dropna(), whole.dropna(), atol=1e-12, rtol=0)
            assert (bp.regressor(data, f"D.{var}{POS}.L{lag}").dropna() >= 0).all()


@pytest.mark.parametrize("det", [[], ["const"], ["const", "trend"]])
def test_ect_parts_add_up(data, det):
    """ect+ + ect- = ect, with and without a constant (the no-constant case relies on the anchor)."""
    lr = {"const": 0.1, "trend": 0.002, f"{X}{POS}": 0.45, f"{X}{NEG}": 0.3}
    weights = {f"{Y}.L1": 1.0, **{(k if k in det else f"{k}.L1"): -v for k, v in lr.items()
                                  if k in det or k.startswith(X)}}
    e = bp.regressor(data, "ect.L1", weights)
    parts = bp.regressor(data, "ect_pos.L1", weights) + bp.regressor(data, "ect_neg.L1", weights)
    assert np.allclose(parts.dropna(), e.dropna(), atol=1e-12, rtol=0)
    expected = data[Y].shift(1) - sum(lr[k] * (bp.regressor(data, k) if k in det else bp.level(data, k).shift(1))
                                      for k in lr if k in det or k.startswith(X))
    assert np.allclose(e.dropna(), expected.dropna(), atol=1e-12, rtol=0)


# 2. Nesting (implementation check, not evidence about asymmetry) -------------------------------
@pytest.mark.parametrize("det", [[], ["const"], ["const", "trend"]])
def test_split_design_nests_symmetric_model_by_exact_reparameterization(data, det):
    """IMPLEMENTATION CHECK. Imposing beta+ = beta- = beta assumes away the asymmetry, so this says
    nothing about whether pass-through is asymmetric. It checks that the split design matrix
    nests the symmetric one: by FFT+ + FFT- = FFT and x+ + x- = x, a regression on the summed
    split columns is algebraically the symmetric model, so coefficients and fitted values must
    match the symmetric fit (ECM estimation.fit_one_step) to 1e-10. A mis-anchored partial sum or
    a wrongly signed split would break it."""
    short_run = [(Y, 1), (X, 0), (X, 1)]
    sym = est.fit_one_step(data, Y, det, [X], short_run)
    split_terms = asym.terms_of(Y, det, asym.split_levels([X]), asym.expand_pairs(short_run))
    frame = asym.design(data, Y, split_terms)
    summed = pd.DataFrame(index=frame.index)
    for name in det + [f"{Y}.L1"]:
        summed[name] = frame[name]
    summed[f"{X}.L1"] = frame[f"{X}{POS}.L1"] + frame[f"{X}{NEG}.L1"]
    for v, k in short_run:
        p, n = asym.pair_names(v, k)
        summed[f"D.{v}.L{k}"] = frame[p] + frame[n]
    res = sm.OLS(frame["dy"], summed[sym.params.index]).fit()
    assert np.allclose(res.params, sym.params, atol=1e-10, rtol=0)
    assert np.allclose(res.fittedvalues, sym.fittedvalues, atol=1e-10, rtol=0)
    # The TAR form with lambda+ = lambda- is the linear form: ect+ + ect- = ect.
    lam = sym.params[f"{Y}.L1"]
    lr = {name: -sym.params[name] / lam for name in det}
    lr[f"{X}{POS}"] = lr[f"{X}{NEG}"] = -sym.params[f"{X}.L1"] / lam
    fit = asym.AsymFit(pd.Series(dtype=float), pd.DataFrame(), pd.Series(dtype=float), 0, Y, det,
                       asym.split_levels([X]), lr=lr)
    weights = fit.ect_weights
    tar = lam * (bp.regressor(data, "ect_pos.L1", weights) + bp.regressor(data, "ect_neg.L1", weights))
    tar = tar + sum(sym.params[f"D.{v}.L{k}"] * (bp.regressor(data, asym.pair_names(v, k)[0])
                                                 + bp.regressor(data, asym.pair_names(v, k)[1]))
                    for v, k in short_run)
    assert np.allclose(tar.loc[sym.fittedvalues.index], sym.fittedvalues, atol=1e-10, rtol=0)


# 3. Pair pruning keeps + and - together --------------------------------------------------------
def lone_terms(terms):
    terms = set(terms)
    lone = []
    for t in terms:
        m = bp.SHORT_RUN_RE.match(t)
        if m and (m["var"].endswith(POS) or m["var"].endswith(NEG)):
            base = m["var"][:-4]
            if not {f"D.{base}{POS}.L{m['lag']}", f"D.{base}{NEG}.L{m['lag']}"} <= terms:
                lone.append(t)
    return lone


def test_pair_pruning_never_leaves_a_lone_term(data):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        v = asym.build_variant(data, Y, X, ["const"], [(Y, 1), (Y, 2), (Y, 3), (X, 0), (X, 1), (X, 2)])
    assert not lone_terms(v.res.params.index)
    assert len(v.pairs) < 6  # something was pruned, in pairs
    lam = [n for n in v.res.params.index if n.startswith("ect_")] or [f"{Y}.L1"]
    assert len(lam) in (1, 2)  # lambda+- both or neither


def test_no_published_variant_has_a_lone_term():
    est_rows = pd.read_csv(ROOT / asym.OUTPUT_NAME)
    for keys, g in est_rows.groupby(asym.GROUP_KEYS):
        terms = list(g.term)
        assert not lone_terms(terms), keys
        assert ("ect_pos.L1" in terms) == ("ect_neg.L1" in terms), keys
        assert (f"LR: {X}{POS}" in terms) == (f"LR: {X}{NEG}" in terms), keys


# 4. lambda+- falls back to symmetric when a regime is too small --------------------------------
SPLIT_SR = [(f"{X}{POS}", 0), (f"{X}{NEG}", 0)]


@pytest.mark.parametrize("seed, min_regime", [(1, asym.MIN_REGIME), (0, 40)])
def test_lambda_split_falls_back_when_a_regime_is_too_small(seed, min_regime):
    """seed 1: ect < 0 in only a few of the 59 quarters; seed 0 with min_regime 40: no split possible."""
    d = synthetic(seed=seed)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = asym.fit_tar(d, Y, ["const"], [X], SPLIT_SR, min_regime=min_regime)
    assert not asym.is_tar(res)
    assert res.form.startswith("symmetric lambda") and min(res.n_pos, res.n_neg) < min_regime
    lin = asym.fit_linear(d, Y, ["const"], [X], SPLIT_SR)
    assert list(res.params.index) == list(lin.params.index) and f"{Y}.L1" in res.params.index
    assert np.allclose(res.params, lin.params, atol=1e-12, rtol=0)


def test_lambda_split_recovers_simulated_asymmetry():
    """With both regimes well populated (400 quarters) the TAR fit is used and finds the DGP."""
    d = synthetic(400)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = asym.fit_tar(d, Y, ["const"], [X], SPLIT_SR)
    assert asym.is_tar(res) and min(res.n_pos, res.n_neg) >= asym.MIN_REGIME and res.converged
    assert res.params[asym.LAMBDA_POS] == pytest.approx(-0.1, abs=0.05)
    assert res.params[asym.LAMBDA_NEG] < -0.4
    assert res.lr[X] == pytest.approx(0.4, abs=0.03)
    # At convergence the regime counts are the signs of the fitted ect.
    e = bp.regressor(d, "ect.L1", res.ect_weights).loc[res.resid.index]
    assert int((e > 0).sum()) == res.n_pos


# 5. Dynamic forecast rebuilds dy+- and the ect regime from the predicted path -------------------
def test_dynamic_forecast_uses_the_predicted_path(candidates):
    summary, estimates, source = candidates
    a = estimates[estimates.asymmetric.astype(bool)]
    has = a.groupby(["bank_name"] + bt.SPEC_KEYS).term.apply(
        lambda t: "ect_pos.L1" in set(t) and any(x.startswith(f"D.{Y}{POS}") for x in t))
    bank, *model = has[has].index[0]
    rows = bt.bank_rows(estimates, bank)
    spec = rows[bt.model_mask(rows, tuple(model))]
    data = bp.bank_data(source, "bank_name", bank, Y, X)
    backtest = bt.MAEBacktest(bank, tuple(model), 8, data, spec)
    origin = data.index[-9]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = backtest.fit(origin)
    actual, predicted = backtest.forecast(res, origin)
    path = data.copy()
    path.loc[predicted.index, Y] = predicted
    weights = res.ect_weights
    moved = 0
    for t in predicted.index:
        x_pred = pd.Series({term: bp.regressor(path, term, weights)[t] for term in res.params.index})
        x_act = pd.Series({term: bp.regressor(data, term, weights)[t] for term in res.params.index})
        dy_hat = path.loc[t, Y] - path[Y].shift(1).loc[t]
        assert abs(dy_hat - float(x_pred @ res.params)) < 1e-10
        moved += int(not np.allclose(x_pred, x_act))
    assert moved > 0  # the predicted path differs from the actual one, so the check has teeth
    # The regime used at the first step is the sign of ect from the last observed quarter.
    first = predicted.index[0]
    e = bp.regressor(path, "ect.L1", weights)[first]
    assert (bp.regressor(path, "ect_pos.L1", weights)[first] > 0) == (e > 0)


# 6. Realized beta ------------------------------------------------------------------------------
def test_realized_beta_at_h1_is_dy_over_dfft_and_small_moves_are_skipped(data):
    spec = pd.DataFrame({"term": ["const", f"{Y}.L1", f"{X}.L1", f"D.{X}.L0"], "coef": [0.0] * 4})
    rbt = bb.RealizedBetaBacktest("synthetic", ("t", "ic", "c"), 4, data, spec, Y, X, min_train=20)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pairs = rbt.pairs(str(data.index[30]))
    h1 = pairs[pairs.h == 1].set_index("quarter")
    dy, dx = data[Y].diff(), data[X].diff()
    for q, r in h1.iterrows():
        t = pd.Period(q, "Q")
        assert r.dFFT == pytest.approx(dx[t], abs=1e-12)
        if abs(dx[t]) >= bb.EASING_DROP:
            assert r.scored and r.actual_beta == pytest.approx(dy[t] / dx[t], abs=1e-12)
        else:
            assert not r.scored and np.isnan(r.actual_beta) and np.isnan(r.implied_beta)
    assert pairs.scored.any() and (~pairs.scored).any()
    table = bb.summarise_realized(pairs, 4)
    assert table.n_pairs.sum() == pairs.scored.sum()
    s = pairs[pairs.scored & (pairs.h == 1)]
    assert table.mae_beta.iloc[0] == pytest.approx((s.implied_beta - s.actual_beta).abs().mean())
    assert table.naive_mae_beta.iloc[0] == pytest.approx(s.actual_beta.abs().mean())  # no change: beta 0
    a = bb.assess_realized(pairs, 4, min_pairs=1)
    assert a["rating"] in ("Green", "Amber", "Red")


# Selection -------------------------------------------------------------------------------------
def test_in_sample_rule_ignores_the_asymmetric_variants(candidates):
    summary, _, _ = candidates
    originals = summary[~summary.asymmetric]
    for bank in summary.bank_name.unique():
        assert bt.select_model(summary, bank) == bt.select_model(originals, bank)


def test_asymmetric_names_parse_and_rank_first():
    name = "EG_LongRun | asymmetric | BIC / ADF lag=1, ECM lag=3 | n (none)"
    assert bt.parse_model(name) == ("EG_LongRun | asymmetric", "BIC / ADF lag=1, ECM lag=3", "n (none)")
    ranks = [bt.family(t) for t in ("ARDL bounds F | asymmetric", "EG_LongRun", "ARDL bounds F", "Johansen VECM")]
    assert ranks == sorted(ranks) and len(set(ranks)) == 4
