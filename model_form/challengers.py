"""Challenger models for the many-start-date backtest (issue #2, OI-11).

Every challenger subclasses MAE_Backtesting/backtest.py's MAEBacktest, so it is re-estimated
and scored by the same expanding-window loop (multi_errors) as the champions: at every origin
from first_origin to T-1 it is fitted on data up to the origin and forecast dynamically, with
predicted y fed back and realised FFT used. Only fit() and forecast() differ.

Challengers (the champion's own short-run terms are kept wherever an ECM is used):
    a0  TwoStepECM        champion's long run, then dy on ect(t-1) + short run. Symmetric control
                          for a1/a2, so asymmetry is not confused with the two-step estimation.
    a1  AsymmetricECM     separate lambda for positive and negative ect(t-1) (threshold at 0,
                          Enders-Siklos TAR form): y above vs. below its long-run level.
    a2  EasingECM         separate lambda in easing quarters (FFT down more than 0.25 pp over the
                          last 4 quarters) and in all other quarters.
    b1  StaticOLS         y = a + b x in levels; forecast a + b x(t).
    b2  StaticBeta        the same b applied to the FFT change since the origin: y(o) + b (x(t) - x(o)).
    b3  CycleBeta         cumulative cycle betas (change in y / change in FFT over a rate cycle),
                          the latest up- and down-cycle beta seen by the origin applied to each
                          quarter's FFT change by its sign.
    c   DummyECM          the champion's ECM plus a level dummy D(t-1), D = 1 from the break quarter.

Long-run parameters for a0-a2 come from the champion's one-step fit at the same origin
(ECM estimation.long_run_rows), so lambda is the only thing that changes between a0 and a1/a2.
"""

from dataclasses import dataclass, field
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "MAE_Backtesting"))
import backtest as bt  # noqa: E402

bp, est = bt.bp, bt.est
MIN_REGIME = 6  # training quarters needed in each regime before lambda is split
MIN_POST = 4  # post-break training quarters needed before the dummy enters
EASING_DROP = 0.25  # pp fall in FFT over 4 quarters that marks an easing quarter
MIN_CYCLE_MOVE = 0.20  # pp FFT move needed before a cycle beta is used
# Rate cycles, each from the last quarter before the first policy move to the last quarter
# before the first opposite move, so the lagged pass-through is inside the cycle.
CYCLES = [("2015-19 up", "2015Q3", "2019Q2", "up"), ("2019-20 down", "2019Q2", "2021Q4", "down"),
          ("2022-24 up", "2021Q4", "2024Q2", "up"), ("2024-26 down", "2024Q2", "2026Q2", "down")]


@dataclass
class Fit:
    """What a challenger needs to forecast: OLS params plus any fixed long-run pieces."""
    params: pd.Series
    lr: dict = field(default_factory=dict)
    form: str = ""
    res: object = None


class Challenger(bt.MAEBacktest):
    code, label = "", ""

    def forecast(self, fit, origin):
        """Actual and dynamically forecast y for the `horizon` quarters after the origin."""
        path = self.data.copy()
        after = path.index[path.index > origin][:self.horizon]
        for t in after:
            path.loc[t, self.y] = self.predict(fit, path, t, origin)
        return self.data.loc[after, self.y], path.loc[after, self.y]

    def predict(self, fit, path, t, origin):
        X = self.columns(path, fit).loc[[t], fit.params.index]
        return float(path[self.y].shift(1).loc[t] + X.iloc[0] @ fit.params)

    # ECM helpers -----------------------------------------------------------------------------
    def base_columns(self, path):
        """The champion's one-step ECM regressors, rebuilt the way bank_plots.regressor does."""
        terms = self.det + [f"{self.y}.L1"] + [f"{v}.L1" for v in self.levels] + [
            f"D.{v}.L{k}" for v, k in self.short_run]
        return pd.concat({term: bp.regressor(path, term) for term in terms}, axis=1)

    def short_run_columns(self, path):
        return pd.concat({f"D.{v}.L{k}": bp.regressor(path, f"D.{v}.L{k}") for v, k in self.short_run}, axis=1) \
            if self.short_run else pd.DataFrame(index=path.index)

    def ols(self, X, origin):
        train = self.data.loc[:origin]
        frame = pd.concat([train[self.y].diff().rename("dy"), X.loc[train.index]], axis=1).dropna()
        return sm.OLS(frame["dy"], frame[X.columns]).fit()

    def long_run(self, origin):
        """Champion one-step fit at the origin -> {term: theta} for the deterministic terms and x."""
        res = self.fit_champion(origin)
        return res, {name.removeprefix("LR: "): theta for name, theta, _, _ in
                     est.long_run_rows(res, self.y, self.det, self.levels)}

    def fit_champion(self, origin):
        return bt.MAEBacktest.fit(self, origin)

    def ect(self, path, lr):
        """y minus its long-run level: y - sum(theta * term), term = const, trend or x."""
        e = path[self.y].copy()
        for term, theta in lr.items():
            e -= theta * (path[term] if term == self.x else bp.regressor(path, term))
        return e


class TwoStepECM(Challenger):
    code, label = "a0", "Two-step ECM (symmetric control)"

    def regimes(self, path, lr):
        return {"ect.L1": self.ect(path, lr).shift(1)}

    def fit(self, origin):
        _, lr = self.long_run(origin)
        path = self.data.loc[:origin]
        parts = self.regimes(path, lr)
        form = "split"
        counts = {k: int((v.dropna() != 0).sum()) for k, v in parts.items()}
        if len(parts) > 1 and min(counts.values()) < MIN_REGIME:
            parts, form = {"ect.L1": self.ect(path, lr).shift(1)}, "symmetric (fallback)"
        X = pd.concat([pd.DataFrame(parts, index=path.index), self.short_run_columns(path)], axis=1)
        res = self.ols(X, origin)
        return Fit(res.params, {"theta": lr}, form if len(parts) > 1 else "symmetric", res)

    def predict(self, fit, path, t, origin):
        X = self._full(path, fit).loc[[t], fit.params.index]
        return float(path[self.y].shift(1).loc[t] + X.iloc[0] @ fit.params)

    def _full(self, path, fit):
        """Every regime column (including the symmetric one) so a fallback fit can forecast."""
        e = self.ect(path, fit.lr["theta"]).shift(1)
        parts = {"ect.L1": e, **self.regimes(path, fit.lr["theta"])}
        return pd.concat([pd.DataFrame(parts, index=path.index), self.short_run_columns(path)], axis=1)


class AsymmetricECM(TwoStepECM):
    code, label = "a1", "Asymmetric ECM (lambda by sign of ect)"

    def regimes(self, path, lr):
        e = self.ect(path, lr).shift(1)
        return {"ect+.L1": e.clip(lower=0), "ect-.L1": e.clip(upper=0)}


class EasingECM(TwoStepECM):
    code, label = "a2", "Asymmetric ECM (lambda by easing vs. other FFT)"

    def regimes(self, path, lr):
        e = self.ect(path, lr).shift(1)
        easing = (path[self.x].diff(4) < -EASING_DROP).astype(float)
        return {"ect.L1 x easing": e * easing, "ect.L1 x other": e * (1 - easing)}


class StaticOLS(Challenger):
    code, label = "b1", "Static OLS beta (levels)"

    def fit(self, origin):
        train = self.data.loc[:origin]
        res = sm.OLS(train[self.y], sm.add_constant(train[self.x])).fit()
        return Fit(res.params, {"beta": float(res.params[self.x])}, "levels", res)

    def predict(self, fit, path, t, origin):
        return float(fit.params["const"] + fit.params[self.x] * path.loc[t, self.x])


class StaticBeta(StaticOLS):
    code, label = "b2", "Static OLS beta (applied to FFT change)"

    def predict(self, fit, path, t, origin):
        return float(self.data.loc[origin, self.y] + fit.lr["beta"] * (path.loc[t, self.x] - path.loc[origin, self.x]))


def cycle_betas(data, y, x, origin=None):
    """[(cycle, direction, start, end used, dFFT, dy, beta)] using data up to the origin."""
    rows = []
    last = data.index[-1] if origin is None else pd.Period(origin, "Q")
    for name, start, end, direction in CYCLES:
        start, end = pd.Period(start, "Q"), pd.Period(end, "Q")
        if start >= last:
            continue
        stop = min(end, last)
        dx = data.loc[stop, x] - data.loc[start, x]
        dy = data.loc[stop, y] - data.loc[start, y]
        rows.append((name, direction, str(start), str(stop), dx, dy, dy / dx if abs(dx) >= MIN_CYCLE_MOVE else np.nan))
    return rows


class CycleBeta(Challenger):
    code, label = "b3", "Cycle-specific betas"

    def fit(self, origin):
        rows = cycle_betas(self.data, self.y, self.x, origin)
        latest = {}
        for name, direction, *_, beta in rows:
            if np.isfinite(beta):
                latest[direction] = (name, beta)
        if not latest:  # no cycle has moved FFT enough yet: fall back to the static OLS beta
            b = StaticOLS.fit(self, origin).lr["beta"]
            latest = {"up": ("static OLS", b), "down": ("static OLS", b)}
        latest.setdefault("down", latest.get("up"))
        latest.setdefault("up", latest.get("down"))
        form = f"up: {latest['up'][0]}; down: {latest['down'][0]}"
        return Fit(pd.Series(dtype=float), {"up": latest["up"][1], "down": latest["down"][1]}, form)

    def predict(self, fit, path, t, origin):
        dx = path.loc[t, self.x] - path[self.x].shift(1).loc[t]
        beta = fit.lr["up"] if dx >= 0 else fit.lr["down"]
        return float(path[self.y].shift(1).loc[t] + beta * dx)


class DummyECM(Challenger):
    code, label = "c", "Champion ECM + 2022 level dummy"
    break_quarter = "2022Q3"

    def dummy(self, path):
        return pd.Series((path.index >= pd.Period(self.break_quarter, "Q")).astype(float), index=path.index)

    def columns(self, path, fit):
        X = self.base_columns(path)
        X["D2022.L1"] = self.dummy(path).shift(1)
        return X

    def fit(self, origin):
        path = self.data.loc[:origin]
        X = self.columns(path, None)
        post = int((X["D2022.L1"].iloc[1:] == 1).sum())
        if post < MIN_POST:
            X, form = X.drop(columns="D2022.L1"), "champion (too few post-break quarters)"
        else:
            form = "with dummy"
        res = self.ols(X, origin)
        return Fit(res.params, {}, form, res)


class DummyECM2022Q1(DummyECM):
    code, label = "c'", "Champion ECM + level dummy from 2022Q1 (sensitivity)"
    break_quarter = "2022Q1"


class ContemporaneousECM(Challenger):
    """Huntington sensitivity (issue #4): the champion plus D.FFT.L0, refitted with OLS."""
    code, label = "h1", "Champion ECM + D.FFT.L0"

    def columns(self, path, fit):
        X = self.base_columns(path)
        if f"D.{self.x}.L0" not in X:
            X[f"D.{self.x}.L0"] = bp.regressor(path, f"D.{self.x}.L0")
        return X

    def fit(self, origin):
        X = self.columns(self.data.loc[:origin], None)
        res = self.ols(X, origin)
        return Fit(res.params, {}, "", res)


CHALLENGERS = [TwoStepECM, AsymmetricECM, EasingECM, StaticOLS, StaticBeta, CycleBeta, DummyECM]
SENSITIVITIES = [DummyECM2022Q1]
