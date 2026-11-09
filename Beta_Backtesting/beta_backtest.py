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
       beta error      implied - actual
   Pairs with a smaller FFT move are listed but not scored (the ratio blows up).
   Rated metric (assess_realized), per horizon band (backtest.horizon_bands), pooling the
   band's scored pairs: mean absolute beta error, bias (mean error), and the skill ratio against
   the no-change benchmark, whose implied beta is 0 (so its error is |actual beta|):
       skill = mean |beta error| / mean |actual beta|
       Red if any rated band >= 1.00, Amber if any > 0.75 (backtest's skill cut-offs), else Green
   A band with fewer than MIN_PAIRS scored pairs is reported but not rated. theta (theta+-)
   at each start date is shown for reference only and not rated: it is a long-run quantity.

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
                "actual_beta", "implied_beta", "beta_error"]
REALIZED_COLUMNS = ["horizon_q", "n_pairs", "n_skipped", "mean_actual_beta", "mean_implied_beta", "mae_beta",
                    "bias", "naive_mae_beta", "skill"]  # + mean_theta_ref_<theta|theta_pos|theta_neg>
MIN_PAIRS = 5


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
                             "scored": scored, "actual_beta": a_beta, "implied_beta": i_beta,
                             "beta_error": i_beta - a_beta, **thetas})
        return pd.DataFrame(rows)


def theta_ref_columns(table):
    return [c for c in table.columns if c.startswith("theta_ref_") or c.startswith("mean_theta_ref_")]


def summarise_realized(pairs, horizon):
    """Per horizon h: scored pairs, mean actual and implied beta, MAE and bias of the implied
    beta, the no-change benchmark's MAE (|actual beta|) and the skill ratio (REALIZED_COLUMNS)."""
    rows, refs = [], theta_ref_columns(pairs)
    for h in range(1, horizon + 1):
        g = pairs[pairs.h == h]
        s = g[g.scored]
        mae, naive = s.beta_error.abs().mean(), s.actual_beta.abs().mean()
        rows.append([f"{h}Q", len(s), len(g) - len(s), s.actual_beta.mean(), s.implied_beta.mean(), mae,
                     s.beta_error.mean(), naive, mae / naive if len(s) else np.nan] + [s[c].mean() for c in refs])
    return pd.DataFrame(rows, columns=REALIZED_COLUMNS + [f"mean_{c}" for c in refs])


def assess_realized(pairs, horizon, min_pairs=MIN_PAIRS):
    """Rating of the implied beta per horizon band (module docstring): worst rated band counts."""
    rows, rating, reasons, worst = {}, "Green", [], (np.nan, "")
    for band, a, b in bt.horizon_bands(horizon):
        s = pairs[pairs.scored & pairs.h.between(a, b)]
        mae, naive = s.beta_error.abs().mean(), s.actual_beta.abs().mean()
        skill = mae / naive if len(s) else np.nan
        rows.update({f"{band} n": len(s), f"{band} mae_beta": mae, f"{band} bias": s.beta_error.mean(),
                     f"{band} naive_mae_beta": naive, f"{band} skill": skill})
        if len(s) < min_pairs:
            reasons.append(f"{band} not rated ({len(s)} pairs < {min_pairs})")
            continue
        if not np.isfinite(worst[0]) or skill > worst[0]:
            worst = (skill, band)
        band_rating = "Red" if skill >= bt.SKILL_RED else ("Amber" if skill > bt.SKILL_AMBER else "Green")
        if band_rating != "Green":
            reasons.append(f"{band} skill {skill:.2f}")
        rating = max(rating, band_rating, key=ORDER.index)
    scored = pairs[pairs.scored]
    return {"n_pairs": int(len(scored)), "n_skipped": int((~pairs.scored).sum()),
            "mae_beta": scored.beta_error.abs().mean(), "bias": scored.beta_error.mean(),
            "naive_mae_beta": scored.actual_beta.abs().mean(), **rows, "worst_skill": worst[0],
            "worst_band": worst[1], "rating": rating if np.isfinite(worst[0]) else "n/a",
            "reason": "; ".join(reasons)}


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

    def realized_chart(self, bank, model, table, assessment, path, horizon, min_move=EASING_DROP):
        """Left: mean actual vs implied beta per h, theta for reference. Right: beta MAE vs no-change."""
        h = np.arange(1, horizon + 1)
        fig, (left, right) = plt.subplots(1, 2, figsize=(14, 5))
        left.bar(h - 0.2, table.mean_actual_beta, width=0.4, color="#b0b0b0", label="Actual beta (mean)")
        left.bar(h + 0.2, table.mean_implied_beta, width=0.4, color="#1f4e79", label="Model-implied beta (mean)")
        for col, color in zip(theta_ref_columns(table), ["#c62828", "#ef6c00"]):
            name = col.removeprefix("mean_theta_ref_").replace("theta_pos", "theta+").replace("theta_neg", "theta-")
            left.plot(h, table[col], color=color, linestyle="--", marker="o", markersize=3,
                      label=f"Long-run {name} at start date (reference, not rated)")
        left.axhline(0, color="black", linewidth=0.6)
        left.set_xticks(h, [f"{r.horizon_q}\nn={r.n_pairs}" for r in table.itertuples()])
        left.set_xlabel("Steps ahead (n = scored start dates)")
        left.set_ylabel("Beta = change in y / change in FFT")
        left.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2)
        left.grid(True, axis="y", alpha=0.3)
        left.set_axisbelow(True)
        bars = right.bar(h - 0.2, table.mae_beta, width=0.4, color="#1f4e79", label="Model: mean |implied - actual|")
        right.bar(h + 0.2, table.naive_mae_beta, width=0.4, color="#b0b0b0", label="No change: mean |actual|")
        right.bar_label(bars, labels=[f"{v:.2f}" if np.isfinite(v) else "" for v in table.skill], fontsize=7)
        right.set_xticks(h, [r.horizon_q for r in table.itertuples()])
        right.set_xlabel("Steps ahead (bar labels: skill ratio)")
        right.set_ylabel("Mean absolute beta error")
        right.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2)
        right.grid(True, axis="y", alpha=0.3)
        right.set_axisbelow(True)
        fig.suptitle(f"{bank}\n{' | '.join(model)}\nRealized vs model-implied beta, start dates "
                     f"{assessment.get('first_origin', '')} onward, |dFFT| >= {min_move:.2f} pp; "
                     f"rating: {assessment['rating']}", fontsize=10)
        fig.tight_layout()
        fig.savefig(path, dpi=120, bbox_inches="tight")
        plt.close(fig)

    def realized_all_banks(self, assessment, horizon, path):
        """Skill ratio per horizon band, one group per bank, with the Amber/Red cut-offs."""
        bands = [b for b, _, _ in bt.horizon_bands(horizon)]
        banks = list(assessment.bank_name)
        x = np.arange(len(banks))
        width = 0.8 / len(bands)
        fig, ax = plt.subplots(figsize=(12, 5))
        for i, band in enumerate(bands):
            ax.bar(x + (i - (len(bands) - 1) / 2) * width, assessment[f"{band} skill"], width=width, label=band)
        ax.axhline(bt.SKILL_AMBER, color="#ef6c00", linestyle="--", linewidth=1.2, label="Amber (> 0.75)")
        ax.axhline(bt.SKILL_RED, color="#c62828", linestyle="--", linewidth=1.2, label="Red (>= 1.00)")
        ax.set_xticks(x, [f"{b}\n{r}" for b, r in zip(banks, assessment.rating)], fontsize=8)
        ax.set_ylabel("Skill ratio: model / no-change mean |beta error|")
        ax.set_title(f"Realized vs model-implied beta of {self.y} on {self.x}: skill ratio by horizon band, all banks",
                     fontsize=10)
        ax.legend(fontsize=8)
        ax.grid(True, axis="y", alpha=0.3)
        ax.set_axisbelow(True)
        fig.savefig(path, dpi=120, bbox_inches="tight")
        plt.close(fig)
