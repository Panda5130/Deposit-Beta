"""Deposit-beta backtests of one bank's champion: theta stability and realized beta.

1. Theta stability (OI-23, option C). The model's specification (its terms in the estimates)
   is re-estimated at every origin from a first origin (e.g. 2016Q1) to T-1 with an expanding
   window (MAEBacktest.fit, MAEBacktest.origins), and the long-run beta theta is recovered with
   backtest.long_run, so it is the same number as the "LR: <x>" row of the estimates when
   fitted on the full sample. An asymmetric model has theta+ and theta- (rows "LR: FFT_pos",
   "LR: FFT_neg"); each is tracked and rated, and the worse rating counts. Each origin's
   deviation from the full-sample value is reported in pp, as a share of the full-sample value
   and in origin standard errors. Rating (assess_multi), on the origins from RATED_FROM (2020Q1:
   earlier samples are mostly at the zero lower bound, where beta is weakly identified; they
   are charted but not rated):
       failing origin   |deviation| > 2 origin SEs AND > 20% of the full-sample value
       extreme origin   |deviation| > 3 origin SEs AND > 20% of the full-sample value
       Green  no failing origin
       Amber  1 or 2 failing origins, none extreme
       Red    3 or more failing origins, or any extreme origin
   Per-origin results are cached per bank (BetaCache, keyed like bt.ErrorCache).

2. Realized beta (RealizedBetaBacktest; replaces the 8-start-date beta view). Same start
   dates as the MAE backtest (expanding window from first_origin) and h = 1..N. At start date t
   the model is fitted on data to t and forecast dynamically with realized FFT. For every
   (t, h) with |FFT_{t+h} - FFT_t| >= min_move (0.25 pp, model_form/challengers.EASING_DROP):
       actual beta     (y_{t+h} - y_t) / (FFT_{t+h} - FFT_t)     (at h = 1: dy_t / dFFT_t)
       implied beta    (yhat_{t+h} - y_t) / (FFT_{t+h} - FFT_t)  (the model's pass-through)
   Pairs with a smaller FFT move are listed but not used: with FFT (almost) unchanged the ratio
   is undefined or explodes. Each horizon h is summarised on its own over its start dates (no
   pooling across horizons): mean actual and implied beta, and the mean of theta (theta+-) at
   those start dates, the coefficient-implied long-run beta. This view is descriptive: it is
   charted, not scored or rated.

The model is the bank's champion under the chosen rule (backtest.DEFAULT_SELECT by default).
run_beta_backtest.py is the command-line driver; this module holds the reusable pieces.
"""

import sys
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "MAE_Backtesting"))
sys.path.insert(0, str(ROOT / "model_form"))
import backtest as bt  # noqa: E402
from challengers import EASING_DROP  # noqa: E402

bp, est, asym = bt.bp, bt.est, bt.asym
ORIGIN_COLUMNS = ["origin", "param", "n_obs", "beta", "beta_se", "beta_p", "lambda", "lambda_neg"]
DEVIATION_COLUMNS = ["full_sample_beta", "dev", "abs_dev_share", "abs_dev_se"]
RATED_FROM, SE_LIMIT, SE_EXTREME, SHARE_LIMIT, AMBER_MAX_FAILS = "2020Q1", 2.0, 3.0, 0.20, 2
ORDER = ["Green", "Amber", "Red"]
PAIR_COLUMNS = ["origin", "h", "quarter", "y0", "actual", "predicted", "FFT0", "FFT", "dFFT", "scored",
                "actual_beta", "implied_beta"]
REALIZED_COLUMNS = ["horizon_q", "n_pairs", "n_skipped", "mean_actual_beta",
                    "mean_implied_beta"]  # + mean_theta_ref_<theta|theta_pos|theta_neg>


def param_label(param, x=bp.DEFAULTS["x"]):
    return {x: "theta", f"{x}{bp.POS}": "theta+", f"{x}{bp.NEG}": "theta-"}.get(param, param)


@dataclass
class BetaResult:
    bank: str
    model: tuple
    full_sample: pd.DataFrame  # ORIGIN_COLUMNS for the fit through T, one row per long-run param
    multi: pd.DataFrame = None  # ORIGIN_COLUMNS + DEVIATION_COLUMNS per (origin, param) from first_origin
    assessment: dict = None  # assess_multi(multi)

    def labelled_multi(self):
        keys = dict(zip(["bank_name"] + bt.SPEC_KEYS, [self.bank, *self.model]))
        return self.multi.assign(**keys)[list(keys) + list(self.multi.columns)]


def lambdas(res, y):
    """(lambda+ or lambda, lambda- or lambda) of a fit."""
    if asym.is_tar(res):
        return float(res.params[asym.LAMBDA_POS]), float(res.params[asym.LAMBDA_NEG])
    lam = float(res.params[f"{y}.L1"])
    return lam, lam


class BetaBacktest(bt.MAEBacktest):
    """Long-run beta (theta, or theta+ and theta-) of one bank's model re-estimated at each origin."""

    def beta_at(self, origin):
        res = self.fit(origin)
        lr = {name: (theta, t, p) for name, theta, t, p in bt.long_run(res, self.y, self.det, self.levels)}
        lam_p, lam_n = lambdas(res, self.y)
        rows = []
        for v in self.levels:
            beta, t, p = lr[f"LR: {v}"]
            rows.append(dict(zip(ORIGIN_COLUMNS, [str(origin), v, int(res.nobs), float(beta), float(beta / t),
                                                  float(p), lam_p, lam_n])))
        return rows

    def origin_betas(self, first_origin):
        """Beta(s) at every origin from first_origin to T-1, one row per (origin, long-run param)."""
        return pd.DataFrame([r for o in self.origins(first_origin) for r in self.beta_at(o)], columns=ORIGIN_COLUMNS)

    def full_sample_beta(self):
        return pd.DataFrame(self.beta_at(self.data.index[-1]), columns=ORIGIN_COLUMNS)


def deviations(betas, full_sample):
    """Per-origin betas with their deviation from the full-sample value of the same param:
    in pp, as a share of the full-sample value and in origin standard errors."""
    full = betas["param"].map(full_sample.set_index("param")["beta"])
    dev = betas["beta"] - full
    return betas.assign(full_sample_beta=full, dev=dev, abs_dev_share=dev.abs() / full.abs(),
                        abs_dev_se=dev.abs() / betas["beta_se"])


def assess_param(t):
    big = t.abs_dev_share > SHARE_LIMIT
    failing, extreme = t[big & (t.abs_dev_se > SE_LIMIT)], t[big & (t.abs_dev_se > SE_EXTREME)]
    if len(extreme) or len(failing) > AMBER_MAX_FAILS:
        rating = "Red"
    elif len(failing):
        rating = "Amber"
    else:
        rating = "Green"
    reasons = [f"{len(failing)} origin(s) > {SE_LIMIT:g} SE and > {SHARE_LIMIT:.0%}"] if len(failing) else []
    if len(extreme):
        reasons.append(f"{len(extreme)} beyond {SE_EXTREME:g} SE")
    share, se = t.abs_dev_share.idxmax(), t.abs_dev_se.idxmax()
    return {"rated_from": t.origin.iloc[0], "rated_to": t.origin.iloc[-1], "rated_origins": len(t),
            "full_sample_beta": float(t.full_sample_beta.iloc[0]), "min_beta": float(t.beta.min()),
            "max_beta": float(t.beta.max()), "max_abs_dev_share": float(t.abs_dev_share[share]),
            "max_share_origin": t.origin[share], "max_abs_dev_se": float(t.abs_dev_se[se]),
            "max_se_origin": t.origin[se], "failing_origins": len(failing), "extreme_origins": len(extreme),
            "failing_list": " ".join(failing.origin), "rating": rating, "reason": "; ".join(reasons)}


def assess_multi(table, rated_from=RATED_FROM, x=bp.DEFAULTS["x"]):
    """Green / Amber / Red theta-stability rating of one bank's many-origin table (deviations()).

    Each long-run param (theta, or theta+ and theta-) is rated; the row describes the worst one
    and ratings_by_param lists them all.
    """
    t = table[pd.PeriodIndex(table.origin, freq="Q") >= pd.Period(rated_from, "Q")]
    if t.empty:
        raise ValueError(f"no origins on or after {rated_from} to rate")
    per = {p: assess_param(g) for p, g in t.groupby("param", sort=False)}
    worst = max(per, key=lambda p: (ORDER.index(per[p]["rating"]), per[p]["max_abs_dev_se"]))
    out = {"param": param_label(worst, x), **per[worst]}
    if len(per) > 1:
        out["reason"] = "; ".join(f"{param_label(p, x)}: {a['reason'] or 'none failing'}" for p, a in per.items())
    out["ratings_by_param"] = "; ".join(f"{param_label(p, x)} {a['rating']} (full {a['full_sample_beta']:.3f})"
                                        for p, a in per.items())
    return out


class BetaCache(bt.ErrorCache):
    """Per-origin betas stored per bank (bt.ErrorCache layout and key: model, first_origin,
    data hash, spec). A beta does not depend on the horizon, so any stored run is reused whole."""

    def load(self, bank, model, first_origin, data_hash, spec):
        e = self.read(bank, model, first_origin, data_hash, spec)
        if e is None or not set(ORIGIN_COLUMNS) <= set(e.columns):
            return None  # missing, stale, or written before the per-param layout
        return e[ORIGIN_COLUMNS]

    def store(self, bank, model, first_origin, data_hash, spec, betas):
        self.write(bank, model, first_origin, data_hash, spec, betas[ORIGIN_COLUMNS])


# Realized beta ---------------------------------------------------------------------------------
class RealizedBetaBacktest(bt.MAEBacktest):
    """Actual vs model-implied pass-through (y_{t+h} - y_t) / (FFT_{t+h} - FFT_t) at every start date."""

    def pairs(self, first_origin, min_move=EASING_DROP):
        """One row per (start date, h <= N): PAIR_COLUMNS plus the reference theta(s) at the start date."""
        rows = []
        for origin in self.origins(first_origin):
            res = self.fit(origin)
            actual, predicted = self.forecast(res, origin)
            thetas = {f"theta_ref_{param_label(name[4:], self.x).replace('+', '_pos').replace('-', '_neg')}": th
                      for name, th, _, _ in bt.long_run(res, self.y, self.det, self.levels) if name[4:] in self.levels}
            y0, x0 = self.data.loc[origin, self.y], self.data.loc[origin, self.x]
            for h, t in enumerate(actual.index[:self.horizon], start=1):
                dx = float(self.data.loc[t, self.x] - x0)
                scored = abs(dx) >= min_move - 1e-12
                a_beta = (actual[t] - y0) / dx if scored else np.nan
                i_beta = (predicted[t] - y0) / dx if scored else np.nan
                rows.append({"origin": str(origin), "h": h, "quarter": str(t), "y0": y0, "actual": actual[t],
                             "predicted": predicted[t], "FFT0": x0, "FFT": self.data.loc[t, self.x], "dFFT": dx,
                             "scored": scored, "actual_beta": a_beta, "implied_beta": i_beta, **thetas})
        return pd.DataFrame(rows)


def theta_ref_columns(table):
    return [c for c in table.columns if c.startswith("theta_ref_") or c.startswith("mean_theta_ref_")]


def summarise_realized(pairs, horizon):
    """One row per horizon h over that horizon's scored start dates only (REALIZED_COLUMNS): the
    number of start dates used and skipped, mean actual and implied beta, and mean theta (theta+-)."""
    rows, refs = [], theta_ref_columns(pairs)
    for h in range(1, horizon + 1):
        g = pairs[pairs.h == h]
        s = g[g.scored]
        rows.append([f"{h}Q", len(s), len(g) - len(s), s.actual_beta.mean(), s.implied_beta.mean()]
                    + [s[c].mean() for c in refs])
    return pd.DataFrame(rows, columns=REALIZED_COLUMNS + [f"mean_{c}" for c in refs])


# Charts ----------------------------------------------------------------------------------------
class BetaPlotter:
    """theta-by-origin charts (stability) and realized-beta charts."""

    Y_RANGE = (-0.25, 1.25)  # beta axis of the many-origin charts; points outside are drawn at the edge

    def __init__(self, y=bp.DEFAULTS["y"], x=bp.DEFAULTS["x"]):
        self.y, self.x = y, x

    def _origin_panel(self, ax, table, rated_from=None, se_limit=SE_LIMIT, share_limit=SHARE_LIMIT):
        """beta by origin with +/- se_limit origin SEs, the full-sample beta and its +/- share band."""
        t = table.reset_index(drop=True)
        x = np.arange(len(t))
        full = float(t.full_sample_beta.iloc[0])
        lo, hi = self.Y_RANGE
        ax.axhspan(full * (1 - share_limit), full * (1 + share_limit), color="#c62828", alpha=0.08, linewidth=0,
                   label=f"Full-sample value +/- {share_limit:.0%}")
        ax.axhline(full, color="#c62828", linestyle="--", linewidth=1.2, label=f"Full-sample value: {full:.3f}")
        ax.fill_between(x, np.clip(t.beta - se_limit * t.beta_se, lo, hi), np.clip(t.beta + se_limit * t.beta_se, lo, hi),
                        color="#1f4e79", alpha=0.15, linewidth=0, label=f"Origin value +/- {se_limit:g} SE")
        ax.plot(x, np.clip(t.beta, lo, hi), color="#1f4e79", linewidth=1.5, marker="o", markersize=3,
                label="Value at origin")
        off = ~t.beta.between(lo, hi)
        for i, b in t.beta[off].items():
            ax.plot(i, hi if b > hi else lo, marker="^" if b > hi else "v", color="#1f4e79", markersize=7)
        if off.any():
            ax.text(0.99, 0.03, f"Off scale (triangles): {int(off.sum())} origin(s), "
                    f"{t.beta[off].min():.2f} to {t.beta[off].max():.2f}",
                    transform=ax.transAxes, ha="right", va="bottom", fontsize=7, color="#333333")
        if rated_from is not None:
            unrated = int((pd.PeriodIndex(t.origin, freq="Q") < pd.Period(rated_from, "Q")).sum())
            if unrated:
                ax.axvspan(-0.5, unrated - 0.5, color="#b0b0b0", alpha=0.25, linewidth=0,
                           label=f"Not rated (before {rated_from})")
        ticks = x[::4]
        ax.set_xticks(ticks, t.origin.iloc[ticks], rotation=90, fontsize=7)
        ax.set_xlim(-0.5, len(t) - 0.5)
        ax.set_ylim(lo, hi)
        ax.grid(True, axis="y", alpha=0.3)
        ax.set_axisbelow(True)

    def origins_chart(self, result, path, rated_from=RATED_FROM, rating=None):
        """One bank's theta (or theta+ and theta-) at every origin of the many-origin run."""
        params = list(result.multi.param.drop_duplicates())
        fig, axes = plt.subplots(len(params), 1, figsize=(11, 4.2 * len(params) + 0.8), squeeze=False)
        t = result.multi
        for ax, p in zip(axes[:, 0], params):
            self._origin_panel(ax, t[t.param == p], rated_from)
            ax.set_ylabel(f"Long-run {param_label(p, self.x)}")
            ax.legend(fontsize=8, loc="upper right")
        axes[-1, 0].set_xlabel("Origin (last quarter of the estimation sample)")
        title = (f"{result.bank}\n{' | '.join(result.model)}\nLong-run beta of {self.y} on {self.x} re-estimated at "
                 f"every origin {t.origin.iloc[0]} to {t.origin.iloc[-1]} (expanding window)")
        axes[0, 0].set_title(title + (f"; rating: {rating}" if rating else ""), fontsize=10)
        fig.tight_layout()
        fig.savefig(path, dpi=120, bbox_inches="tight")
        plt.close(fig)

    def all_banks_origins(self, results, path, rated_from=RATED_FROM, ratings=None):
        """Small multiples of beta by origin, one panel per bank and long-run param."""
        panels = [(r, p) for r in results for p in r.multi.param.drop_duplicates()]
        n = len(panels)
        cols = min(4, n)
        rows = -(-n // cols)
        fig, axes = plt.subplots(rows, cols, figsize=(4 * cols, 3.4 * rows), sharey=True, squeeze=False)
        for ax, (result, p) in zip(axes.flat, panels):
            self._origin_panel(ax, result.multi[result.multi.param == p], rated_from)
            rating = (ratings or {}).get(result.bank)
            label = "" if p == self.x else f" ({param_label(p, self.x)})"
            ax.set_title(result.bank + label + (f"\nrating: {rating}" if rating else ""), fontsize=9)
        for ax in list(axes.flat)[n:]:
            ax.axis("off")
        handles, labels = axes.flat[0].get_legend_handles_labels()
        fig.legend(handles, [lab.split(":")[0] for lab in labels], loc="lower center", ncol=len(labels), fontsize=8,
                   bbox_to_anchor=(0.5, -0.02))
        fig.suptitle(f"Long-run beta of {self.y} on {self.x} re-estimated at every origin, all banks", fontsize=11)
        fig.tight_layout(rect=(0, 0.04, 1, 0.97))
        fig.savefig(path, dpi=120, bbox_inches="tight")
        plt.close(fig)

    def _realized_panel(self, ax, table):
        """Bars: mean actual and model-implied beta per h (left axis). Line: mean theta (theta+-) at
        the same start dates, the coefficient-implied long-run beta (right axis)."""
        h = np.arange(1, len(table) + 1)
        ax.bar(h - 0.2, table.mean_actual_beta, width=0.4, color="#b0b0b0", label="Actual beta")
        ax.bar(h + 0.2, table.mean_implied_beta, width=0.4, color="#1f4e79", label="Model-implied beta (forecast)")
        ax.axhline(0, color="black", linewidth=0.6)
        ax.set_xticks(h, [f"{r.horizon_q}\nn={r.n_pairs}" for r in table.itertuples()], fontsize=7)
        ax.set_ylabel("Beta at horizon h (mean over start dates)", fontsize=8)
        ax.grid(True, axis="y", alpha=0.3)
        ax.set_axisbelow(True)
        right = ax.twinx()
        for col, color in zip(theta_ref_columns(table), ["#c62828", "#ef6c00"]):
            name = col.removeprefix("mean_theta_ref_").replace("theta_pos", "theta+").replace("theta_neg", "theta-")
            right.plot(h, table[col], color=color, linestyle="--", marker="o", markersize=3,
                       label=f"Coefficient-implied long-run {name} (right axis)")
        right.set_ylabel("Long-run theta (mean over start dates)", fontsize=8, color="#c62828")
        right.tick_params(axis="y", colors="#c62828")
        return right

    @staticmethod
    def _legend(fig, axes_pairs):
        handles, labels = [], []
        for ax in axes_pairs:
            for hdl, lab in zip(*ax.get_legend_handles_labels()):
                if lab not in labels:
                    handles.append(hdl)
                    labels.append(lab)
        fig.legend(handles, labels, loc="lower center", ncol=len(labels), fontsize=8, bbox_to_anchor=(0.5, -0.02))

    def realized_chart(self, bank, model, table, path, first_origin, min_move=EASING_DROP):
        """One bank's mean actual vs model-implied beta per horizon, theta on a second axis."""
        fig, ax = plt.subplots(figsize=(11, 5))
        right = self._realized_panel(ax, table)
        ax.set_xlabel("Steps ahead h (n = start dates with |dFFT| >= the threshold)")
        ax.set_title(f"{bank}\n{' | '.join(model)}\nRealized vs model-implied beta of {self.y} on {self.x}, start "
                     f"dates {first_origin} onward, |FFT(t+h) - FFT(t)| >= {min_move:.2f} pp", fontsize=10)
        self._legend(fig, [ax, right])
        fig.tight_layout(rect=(0, 0.06, 1, 1))
        fig.savefig(path, dpi=120, bbox_inches="tight")
        plt.close(fig)

    def realized_all_banks(self, tables, path, min_move=EASING_DROP):
        """Small multiples of realized_chart, one panel per bank ({bank: (model, table)})."""
        n = len(tables)
        cols = min(4, n)
        rows = -(-n // cols)
        fig, axes = plt.subplots(rows, cols, figsize=(4.6 * cols, 3.6 * rows), squeeze=False)
        twins = []
        for ax, (bank, (model, table)) in zip(axes.flat, tables.items()):
            twins.append(self._realized_panel(ax, table))
            ax.set_title(bank + (" (asymmetric)" if bt.is_asymmetric_name(model[0]) else ""), fontsize=9)
        for ax in list(axes.flat)[n:]:
            ax.axis("off")
        self._legend(fig, [axes.flat[0]] + twins)
        fig.suptitle(f"Realized vs model-implied beta of {self.y} on {self.x} by horizon, all banks "
                     f"(|FFT(t+h) - FFT(t)| >= {min_move:.2f} pp); long-run theta on the right axis", fontsize=11)
        fig.tight_layout(rect=(0, 0.04, 1, 0.97))
        fig.savefig(path, dpi=120, bbox_inches="tight")
        plt.close(fig)
