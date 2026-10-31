"""Model-form diagnostics and challengers for root cause RC1 (issues #2, #4, #5).

Usage:
    python model_form/run_model_form.py [--reps 2000] [--first-origin 2016Q1] [--horizon 8]

Steps and outputs (all under model_form/output/):
    1. Gregory-Hansen tests, 7 banks, 2011Q1-2026Q2 (issue #5)
         gregory_hansen.csv              every (bank, model, statistic): value, break, critical values
         gregory_hansen_summary.csv      ADF* per bank and model, with the Zivot-Andrews breaks
         gregory_hansen_cv_sim.csv       simulated finite-sample critical values (T = 62)
         gregory_hansen_adf_by_break.png ADF t at every candidate break, C and C/S models
    2. Challengers on the many-start-date backtest (issue #2): the champion's identical origins,
       expanding window, h = 1..N, no-change benchmark, horizon-band limits and skill test
         errors/<code>.csv               per-origin errors (h, origin, quarter, actual, predicted, err, naive)
         multiorigin_<N>Q.csv            h-step MAE per bank and model (champion re-run included)
         assessment_fixed_limits_<N>Q.csv  each model rated against the champions' band limits
         assessment_peer_limits_<N>Q.csv   each challenger family rated by assess_multi on its own peers
         comparison_<N>Q.csv             mean MAE, worst skill ratio and rating, champion vs. challengers
         fit_forms.csv                   which form each challenger took at each origin (fallbacks)
         asymmetry_tests.csv             full-sample lambda split and Wald test of equal lambdas
         dummy_ecm.csv                   full-sample 2022 dummy coefficient and long-run shift
         cycle_betas.csv                 full-sample cycle betas per bank
         oi8_origin_2025Q1.csv           the 2025Q1 start date: 5-quarter window MAE per model (OI-8)
         oi8_decomposition_2025Q1.csv    champion forecast change from 2025Q1 by term group
         <bank>/challengers_<N>Q.png     h-step MAE by horizon, champion vs. challengers vs. no-change
         oi8_paths_2025Q1.png            forecast paths from 2025Q1, M&T, SouthState, Old National
    3. Huntington evidence (issue #4)
         huntington_eg_subsamples.csv    EG (no deterministic terms) cointegration p by sample window
         huntington_evidence.csv         one-row-per-item summary used in docs/resolutions/model_form.md
"""

import argparse
import logging
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import coint

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import challengers as ch  # noqa: E402
import gregory_hansen as gh  # noqa: E402

bt, bp = ch.bt, ch.bp
log = logging.getLogger("model_form")
OUT = HERE / "output"
CHAMPION_OUT = bt.HERE / "output"
OI8_BANKS = ["Manufacturers and Traders Trust Company", "SouthState Bank", "Old National Bank"]
HUNTINGTON = "Huntington National Bank"
# Categorical slots 1-6 of the validated reference palette, in fixed order; no-change is gray.
COLORS = {"champion": "#2a78d6", "a1": "#eb6834", "a2": "#1baf7a", "b2": "#eda100", "b3": "#e87ba4",
          "c": "#008300", "no-change": "#8a8a8a"}
MARKERS = {"champion": "o", "a1": "s", "a2": "^", "b2": "D", "b3": "v", "c": "P", "no-change": "x"}
CHART_MODELS = ["champion", "a1", "a2", "b2", "b3", "c"]
ORDER = ["Green", "Amber", "Red"]


def short(bank):
    return {"Manufacturers and Traders Trust Company": "M&T", "KeyBank National Association": "KeyBank",
            "Huntington National Bank": "Huntington"}.get(bank, bank.replace(" Bank", ""))


def load_inputs():
    summary = bp.read_csv(bt.ROOT / "estimation result summary.csv")
    estimates = bp.load_estimates(bp.DEFAULTS["estimates"])
    source = bp.load_source(bp.DEFAULTS["dependents"], bp.DEFAULTS["independents"])
    banks = list(summary["bank_name"].astype(str).str.strip().drop_duplicates())
    specs = {}
    for bank in banks:
        model = bt.select_model(summary, bank)
        rows = bt.bank_rows(estimates, bank)
        specs[bank] = (model, rows[bt.model_mask(rows, model)], bp.bank_data(source, "bank_name", bank,
                                                                              bp.DEFAULTS["y"], bp.DEFAULTS["x"]))
    return banks, specs


# 1. Gregory-Hansen ----------------------------------------------------------------------------
def run_gregory_hansen(banks, specs, reps):
    n = len(next(iter(specs.values()))[2])
    log.info("simulating Gregory-Hansen critical values, T=%d, %d reps per model", n, reps)
    cv_sim = {m: gh.simulate_cv(n, m, reps) for m in gh.MODELS}
    pd.DataFrame([{"model": m, "statistic": f"{k}*", "cv_1": v[0], "cv_5": v[1], "cv_10": v[2], "T": n, "reps": reps}
                  for m, d in cv_sim.items() for k, v in d.items()]).to_csv(OUT / "gregory_hansen_cv_sim.csv",
                                                                            index=False)
    rows = []
    for bank in banks:
        data = specs[bank][2]
        assert len(data) == n, f"{bank} has {len(data)} quarters, simulated for {n}"
        rows += [{"bank_name": bank, **r} for r in gh.run(data, bp.DEFAULTS["y"], bp.DEFAULTS["x"], cv_sim)]
    full = pd.DataFrame(rows)
    full.to_csv(OUT / "gregory_hansen.csv", index=False)

    za = pd.read_csv(bt.ROOT / "diagnostics" / "zivot_andrews.csv")
    za = za[za["sample"] == "2011-2026"].pivot(index="bank_name", columns="regression", values="break_quarter")
    adf = full[full.statistic == "ADF*"].pivot(index="bank_name", columns="model")
    summary = pd.DataFrame(index=banks)
    for m in gh.MODELS:
        summary[f"{m} ADF*"] = adf[("value", m)]
        summary[f"{m} break"] = adf[("break_quarter", m)]
        summary[f"{m} reject 5% (sim)"] = adf[("reject_5_sim", m)]
        summary[f"{m} reject 5% (asy)"] = adf[("reject_5_asy", m)]
    for reg in ("c", "t", "ct"):
        summary[f"ZA {reg} break"] = za[reg]
    summary.index.name = "bank_name"
    summary.reset_index().to_csv(OUT / "gregory_hansen_summary.csv", index=False)
    plot_gh_paths(banks, specs, cv_sim)
    return full, summary, cv_sim


def plot_gh_paths(banks, specs, cv_sim):
    fig, axes = plt.subplots(2, 4, figsize=(15, 7), sharey=True)
    for ax, bank in zip(axes.flat, banks):
        data = specs[bank][2]
        for model, color, marker in (("C", COLORS["champion"], "o"), ("C/S", COLORS["a1"], "s")):
            path = gh.adf_path(data, bp.DEFAULTS["y"], bp.DEFAULTS["x"], model)
            ax.plot(range(len(path)), path.values, color=color, marker=marker, markersize=3, linewidth=1.5,
                    label=f"{model} ADF t")
            ax.axhline(cv_sim[model]["ADF"][1], color=color, linestyle="--", linewidth=1,
                       label=f"{model} 5% cv (T={len(data)})")
        ticks = [i for i, q in enumerate(path.index) if q.endswith("Q1") and int(q[:4]) % 2 == 0]
        ax.set_xticks(ticks, [path.index[i][:4] for i in ticks], fontsize=8)
        ax.set_title(short(bank), fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.set_axisbelow(True)
    axes.flat[-1].axis("off")
    handles, labels = axes.flat[0].get_legend_handles_labels()
    axes.flat[-1].legend(handles, labels, loc="center", fontsize=9, frameon=False)
    fig.suptitle("Gregory-Hansen: ADF t on the cointegrating residuals at each candidate break "
                 "(first quarter of the new regime); reject where the line is below its 5% critical value", fontsize=10)
    fig.supylabel("ADF t")
    fig.tight_layout()
    fig.savefig(OUT / "gregory_hansen_adf_by_break.png", dpi=120, bbox_inches="tight")
    plt.close(fig)


# 2. Challengers -------------------------------------------------------------------------------
def run_paths(backtest, first_origin):
    """Per-origin errors as in MAEBacktest.multi_errors, keeping the forecast and the fit form."""
    index = backtest.data.index
    first = max(pd.Period(first_origin, "Q"), index[backtest.min_train - 1])
    rows, forms = [], []
    for origin in index[(index >= first) & (index < index[-1])]:
        fit = backtest.fit(origin)
        actual, predicted = backtest.forecast(fit, origin)
        start = backtest.data.loc[origin, backtest.y]
        for h, t in enumerate(actual.index[:backtest.horizon], start=1):
            rows.append((h, str(origin), str(t), actual[t], predicted[t], abs(actual[t] - predicted[t]),
                         abs(actual[t] - start)))
        forms.append((str(origin), getattr(fit, "form", "")))
    paths = pd.DataFrame(rows, columns=["h", "origin", "quarter", "actual", "predicted", "err", "naive"])
    return paths, pd.DataFrame(forms, columns=["origin", "form"])


def rate_fixed(table, limits):
    """assess_multi's rule for one bank, against given band limits (the champions')."""
    t = table.assign(h=table.horizon_q.str.rstrip("Q").astype(int))
    reasons, absolute = [], "Green"
    for r in limits.itertuples():
        band = t[(t.h >= r.h_from) & (t.h <= r.h_to)]["mae"]
        if band.max() > r.red + 1e-12:
            absolute = "Red"
            reasons.append(f"{r.band} max {band.max():.3f} > red {r.red:.2f}")
        elif band.mean() > r.green + 1e-12:
            absolute = max(absolute, "Amber", key=ORDER.index)
            reasons.append(f"{r.band} avg {band.mean():.3f} > green {r.green:.2f}")
    skill = (t["mae"] / t["naive_mae"]).set_axis(t.h)
    worst, worst_h = float(skill.max()), int(skill.idxmax())
    skill_rating = "Red" if worst >= bt.SKILL_RED else ("Amber" if worst > bt.SKILL_AMBER else "Green")
    if skill_rating != "Green":
        reasons.append(f"skill ratio {worst:.2f} at {worst_h}Q")
    return {"mean_mae": float(t["mae"].mean()), "naive_mean_mae": float(t["naive_mae"].mean()),
            "worst_skill_ratio": worst, "worst_skill_h": f"{worst_h}Q", "absolute_rating": absolute,
            "skill_rating": skill_rating, "rating": max(absolute, skill_rating, key=ORDER.index),
            "reason": "; ".join(reasons)}


def run_challengers(banks, specs, first_origin, horizon):
    (OUT / "errors").mkdir(parents=True, exist_ok=True)
    models = [("champion", "Champion", bt.MAEBacktest)] + [(c.code, c.label, c) for c in
                                                            ch.CHALLENGERS + ch.SENSITIVITIES]
    paths, forms = {}, []
    for code, label, cls in models:
        frames = []
        for bank in banks:
            model, spec_rows, data = specs[bank]
            backtest = cls(bank, model, horizon, data, spec_rows)
            p, f = run_paths(backtest, first_origin)
            frames.append(p.assign(bank_name=bank))
            forms.append(f.assign(bank_name=bank, model=code))
        paths[code] = pd.concat(frames, ignore_index=True)
        paths[code].to_csv(OUT / "errors" / f"{code.replace(chr(39), 'p')}.csv", index=False)
        log.info("%s: %d forecasts", label, len(paths[code]))
    pd.concat(forms).to_csv(OUT / "fit_forms.csv", index=False)
    labels = {code: label for code, label, _ in models}

    tables = {code: {bank: bt.summarise_errors(p[p.bank_name == bank][bt.ERROR_COLUMNS], horizon)
                     for bank in banks} for code, p in paths.items()}
    check_champion(tables["champion"], horizon)
    multi = pd.concat([t.assign(bank_name=b, model=code, model_label=labels[code])
                       for code, d in tables.items() for b, t in d.items()], ignore_index=True)
    multi.to_csv(OUT / f"multiorigin_{horizon}Q.csv", index=False)

    limits = pd.read_csv(CHAMPION_OUT / f"backtest_multiorigin_limits_{horizon}Q.csv")
    fixed = pd.DataFrame([{"bank_name": b, "model": code, "model_label": labels[code], **rate_fixed(t, limits)}
                          for code, d in tables.items() for b, t in d.items()])
    fixed.to_csv(OUT / f"assessment_fixed_limits_{horizon}Q.csv", index=False)
    peer = []
    for code, d in tables.items():
        lim, assessment = bt.assess_multi(d, horizon)
        peer.append(assessment.assign(model=code, model_label=labels[code],
                                      limits="; ".join(f"{r.band} {r.green:.2f}/{r.red:.2f}" for r in lim.itertuples())))
    pd.concat(peer).to_csv(OUT / f"assessment_peer_limits_{horizon}Q.csv", index=False)
    return paths, tables, fixed, labels


def check_champion(tables, horizon):
    """The re-run champion must match MAE_Backtesting's published many-start-date table."""
    ref = pd.read_csv(CHAMPION_OUT / f"backtest_multiorigin_{horizon}Q.csv")
    for bank, t in tables.items():
        r = ref[ref.bank_name == bank].reset_index(drop=True)
        same = (r[["horizon_q", "first_origin", "last_origin", "n_windows"]].astype(str).values
                == t[["horizon_q", "first_origin", "last_origin", "n_windows"]].astype(str).values).all()
        gap = float(np.max(np.abs(r[["mae", "naive_mae"]].values - t[["mae", "naive_mae"]].values)))
        if not same or gap > 1e-9:
            raise RuntimeError(f"{bank}: re-run champion differs from {CHAMPION_OUT} (max gap {gap:.2e})")
    log.info("champion re-run matches backtest_multiorigin_%dQ.csv for all banks (identical origins)", horizon)


def comparison(fixed, tables, horizon):
    champ = fixed[fixed.model == "champion"].set_index("bank_name")
    rows = []
    for r in fixed.itertuples():
        c = champ.loc[r.bank_name]
        t = tables[r.model][r.bank_name]
        rows.append({"bank_name": r.bank_name, "model": r.model, "model_label": r.model_label,
                     "mean_mae": r.mean_mae, "delta_vs_champion": r.mean_mae - c.mean_mae,
                     "pct_vs_champion": 100 * (r.mean_mae / c.mean_mae - 1),
                     "h1": t.mae.iloc[0], "h4": t.mae.iloc[3], "h8": t.mae.iloc[horizon - 1],
                     "naive_mean_mae": r.naive_mean_mae, "worst_skill_ratio": r.worst_skill_ratio,
                     "rating_fixed_limits": r.rating, "champion_rating": c.rating, "reason": r.reason})
    out = pd.DataFrame(rows)
    out.to_csv(OUT / f"comparison_{horizon}Q.csv", index=False)
    return out


def full_sample_tests(banks, specs, horizon):
    asym, dummy, cycles = [], [], []
    for bank in banks:
        model, spec_rows, data = specs[bank]
        last = data.index[-1]
        for cls in (ch.AsymmetricECM, ch.EasingECM):
            fit = cls(bank, model, horizon, data, spec_rows).fit(last)
            if fit.form != "split":
                raise RuntimeError(f"{bank} {cls.code}: full-sample fit fell back to {fit.form}")
            a, b = fit.params.index[:2]
            restriction = np.zeros((1, len(fit.params)))
            restriction[0, :2] = [1, -1]  # lambda_1 = lambda_2
            w = fit.res.wald_test(restriction, scalar=True)
            asym.append({"bank_name": bank, "model": cls.code, "form": fit.form,
                         "lambda_1_name": a, "lambda_1": fit.params[a], "lambda_1_p": fit.res.pvalues[a],
                         "lambda_2_name": b, "lambda_2": fit.params[b], "lambda_2_p": fit.res.pvalues[b],
                         "wald_F_equal": float(w.statistic), "wald_p_equal": float(w.pvalue),
                         "n_regime_1": int((fit.res.model.exog[:, 0] != 0).sum()),
                         "n_regime_2": int((fit.res.model.exog[:, 1] != 0).sum())})
        bt_c = ch.DummyECM(bank, model, horizon, data, spec_rows)
        fit = bt_c.fit(last)
        lam = fit.params[f"{bp.DEFAULTS['y']}.L1"]
        lr = dict((n, (th, p)) for n, th, _, p in ch.est.long_run_rows(fit.res, bp.DEFAULTS["y"], bt_c.det,
                                                                      bt_c.levels + ["D2022"]))
        dummy.append({"bank_name": bank, "break_quarter": bt_c.break_quarter, "delta": fit.params["D2022.L1"],
                      "delta_p": fit.res.pvalues["D2022.L1"], "lambda": lam, "LR_shift": lr["LR: D2022"][0],
                      "LR_shift_p": lr["LR: D2022"][1], "theta": lr[f"LR: {bp.DEFAULTS['x']}"][0],
                      "theta_champion": float(spec_rows.set_index("term").loc[f"LR: {bp.DEFAULTS['x']}", "coef"]),
                      "in_sample_mae": float(np.mean(np.abs(fit.res.resid)))})
        for name, direction, start, stop, dx, dy, beta in ch.cycle_betas(data, bp.DEFAULTS["y"], bp.DEFAULTS["x"]):
            cycles.append({"bank_name": bank, "cycle": name, "direction": direction, "start": start, "end": stop,
                           "dFFT": dx, "dy": dy, "cycle_beta": beta})
        b = ch.StaticOLS(bank, model, horizon, data, spec_rows).fit(last)
        cycles.append({"bank_name": bank, "cycle": "static OLS (levels, 2011Q1-2026Q2)", "direction": "",
                       "start": str(data.index[0]), "end": str(last), "dFFT": np.nan, "dy": np.nan,
                       "cycle_beta": b.lr["beta"]})
    pd.DataFrame(asym).to_csv(OUT / "asymmetry_tests.csv", index=False)
    pd.DataFrame(dummy).to_csv(OUT / "dummy_ecm.csv", index=False)
    pd.DataFrame(cycles).to_csv(OUT / "cycle_betas.csv", index=False)
    return pd.DataFrame(asym), pd.DataFrame(dummy), pd.DataFrame(cycles)


def oi8(paths, labels, origin="2025Q1"):
    rows = []
    for code, p in paths.items():
        w = p[p.origin == origin]
        for bank, g in w.groupby("bank_name"):
            rows.append({"bank_name": bank, "model": code, "model_label": labels[code], "origin": origin,
                         "n_quarters": len(g), "window_mae": g.err.mean(), "h5_err": g.err.iloc[-1],
                         "naive_window_mae": g.naive.mean(),
                         "mean_signed_err": float((g.actual - g.predicted).mean())})
    out = pd.DataFrame(rows)
    out.to_csv(OUT / f"oi8_origin_{origin}.csv", index=False)
    return out


def oi8_decomposition(specs, horizon, origin="2025Q1", steps=5):
    """Champion forecast from the origin split into term groups, summed over the steps.

    error correction = const, trend, y.L1 and x.L1 (lambda times the disequilibrium); momentum =
    lagged dy terms; FFT dynamics = D.FFT terms. The groups add up to the forecast change in y.
    """
    rows = []
    y, x = bp.DEFAULTS["y"], bp.DEFAULTS["x"]
    o = pd.Period(origin, "Q")
    for bank, (model, spec_rows, data) in specs.items():
        backtest = bt.MAEBacktest(bank, model, horizon, data, spec_rows)
        res = backtest.fit(o)
        path = data.copy()
        total = {"error correction": 0.0, "momentum (lagged dy)": 0.0, "FFT dynamics": 0.0}
        for t in path.index[path.index > o][:steps]:
            X = pd.concat({term: bp.regressor(path, term).loc[[t]] for term in res.params.index}, axis=1).iloc[0]
            contrib = X * res.params
            for term, v in contrib.items():
                group = ("momentum (lagged dy)" if term.startswith(f"D.{y}.") else
                         "FFT dynamics" if term.startswith(f"D.{x}.") else "error correction")
                total[group] += v
            path.loc[t, y] = path[y].shift(1).loc[t] + contrib.sum()
        end = path.index[path.index > o][steps - 1]
        rows.append({"bank_name": bank, "origin": origin, "steps": steps, **total,
                     "forecast_change": path.loc[end, y] - data.loc[o, y],
                     "actual_change": data.loc[end, y] - data.loc[o, y],
                     "last_dy_before_origin": data[y].diff().loc[o]})
    out = pd.DataFrame(rows)
    out.to_csv(OUT / f"oi8_decomposition_{origin}.csv", index=False)
    return out


def plot_bank_mae(banks, tables, labels, horizon):
    for bank in banks:
        fig, ax = plt.subplots(figsize=(10, 5))
        h = np.arange(1, horizon + 1)
        for code in CHART_MODELS:
            t = tables[code][bank]
            ax.plot(h, t.mae, color=COLORS[code], marker=MARKERS[code], linewidth=2, markersize=7,
                    label=f"{labels[code]}" if code != "champion" else "Champion")
        ax.plot(h, tables["champion"][bank].naive_mae, color=COLORS["no-change"], marker="x", linestyle="--",
                linewidth=1.5, label="No-change forecast")
        ax.set_xticks(h, [f"{k}Q\nn={n}" for k, n in zip(h, tables["champion"][bank].n_windows)])
        ax.set_ylim(0, None)
        ax.set_title(f"{bank}: many-start-date h-step MAE of {bp.DEFAULTS['y']}, origins 2016Q1 onward, "
                     "champion vs. challengers", fontsize=10)
        ax.set_xlabel("Steps ahead (n = number of start dates)")
        ax.set_ylabel("MAE (pp)")
        ax.legend(fontsize=8, loc="upper left", frameon=False)
        ax.grid(True, axis="y", alpha=0.3)
        ax.set_axisbelow(True)
        bank_dir = OUT / bp.INVALID_CHARS_RE.sub("-", bank)
        bank_dir.mkdir(parents=True, exist_ok=True)
        fig.savefig(bank_dir / f"challengers_{horizon}Q.png", dpi=120, bbox_inches="tight")
        plt.close(fig)


def plot_oi8(paths, specs, labels, origin="2025Q1"):
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), sharey=False)
    for ax, bank in zip(axes, OI8_BANKS):
        data = specs[bank][2]
        hist = data.loc[pd.Period("2023Q1", "Q"):, bp.DEFAULTS["y"]]
        ax.plot(hist.index.to_timestamp(how="end"), hist.values, color="#222222", linewidth=2.5, label="Actual")
        o = pd.Period(origin, "Q")
        for code in CHART_MODELS:
            w = paths[code][(paths[code].bank_name == bank) & (paths[code].origin == origin)]
            x = [o.to_timestamp(how="end")] + list(pd.PeriodIndex(w.quarter, freq="Q").to_timestamp(how="end"))
            y = [data.loc[o, bp.DEFAULTS["y"]]] + list(w.predicted)
            ax.plot(x, y, color=COLORS[code], marker=MARKERS[code], linewidth=1.8, markersize=6,
                    label=labels[code] if code != "champion" else "Champion")
        ax.axvline(o.to_timestamp(how="end"), color="#8a8a8a", linestyle=":", linewidth=1)
        ax.set_title(f"{short(bank)}: forecasts from {origin}", fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.set_axisbelow(True)
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.tick_params(axis="x", labelsize=8)
    axes[0].set_ylabel(f"{bp.DEFAULTS['y']} (%)")
    handles, lab = axes[0].get_legend_handles_labels()
    fig.legend(handles, lab, loc="lower center", ncol=4, fontsize=8, frameon=False, bbox_to_anchor=(0.5, -0.08))
    fig.suptitle(f"OI-8: dynamic forecasts from the {origin} start date (realised FFT), champion vs. challengers",
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / f"oi8_paths_{origin}.png", dpi=120, bbox_inches="tight")
    plt.close(fig)


# 3. Huntington --------------------------------------------------------------------------------
def huntington(specs, horizon, first_origin, gh_summary, fixed, asym, dummy):
    model, spec_rows, data = specs[HUNTINGTON]
    y, x = bp.DEFAULTS["y"], bp.DEFAULTS["x"]
    rows = []
    for start in ("2011Q1", "2013Q1", "2016Q1"):
        for end in ("2019Q4", "2021Q4", "2024Q2", "2025Q4", "2026Q2"):
            w = data.loc[pd.Period(start, "Q"):pd.Period(end, "Q")]
            if len(w) < 16:
                continue
            stat, p, _ = coint(w[y], w[x], trend="n", maxlag=4, autolag="aic")
            rows.append({"start": start, "end": end, "n_obs": len(w), "eg_t": stat, "eg_p": p, "pass_5": p < 0.05})
    sub = pd.DataFrame(rows)
    sub.to_csv(OUT / "huntington_eg_subsamples.csv", index=False)

    h1 = ch.ContemporaneousECM(HUNTINGTON, model, horizon, data, spec_rows)
    p, _ = run_paths(h1, first_origin)
    table = bt.summarise_errors(p[bt.ERROR_COLUMNS], horizon)
    limits = pd.read_csv(CHAMPION_OUT / f"backtest_multiorigin_limits_{horizon}Q.csv")
    h1_rating = rate_fixed(table, limits)
    full = h1.fit(data.index[-1])
    p.assign(bank_name=HUNTINGTON).to_csv(OUT / "errors" / "h1_huntington.csv", index=False)
    table.assign(bank_name=HUNTINGTON, model="h1").to_csv(OUT / f"huntington_h1_multiorigin_{horizon}Q.csv",
                                                          index=False)

    betas = pd.read_csv(bt.ROOT / "Beta_Backtesting" / "output" / HUNTINGTON / "beta_backtest_origins_8Q.csv")
    g = gh_summary.loc[HUNTINGTON]
    f = fixed[fixed.bank_name == HUNTINGTON].set_index("model")
    a = asym[asym.bank_name == HUNTINGTON].set_index("model")
    dm = dummy.set_index("bank_name").loc[HUNTINGTON]
    items = [
        ("Baseline cointegration", "fails all four at 5% (EG long run p 0.085)", "§6.3.4"),
        ("Re-specification grid", "only EG long run, no deterministic terms (p 0.019)", "§6.3.4"),
        ("EG `n` by sample window", f"{int(sub.pass_5.sum())} of {len(sub)} windows pass at 5%; "
                                    f"p from {sub.eg_p.min():.3f} to {sub.eg_p.max():.3f}", "huntington_eg_subsamples.csv"),
        ("Gregory-Hansen C (level shift)", f"ADF* {g['C ADF*']:.2f}, break {g['C break']}, "
                                           f"reject 5% (T=62 sim): {g['C reject 5% (sim)']}", "gregory_hansen_summary.csv"),
        ("Gregory-Hansen C/S (regime shift)", f"ADF* {g['C/S ADF*']:.2f}, break {g['C/S break']}, "
                                              f"reject 5% (T=62 sim): {g['C/S reject 5% (sim)']}", "gregory_hansen_summary.csv"),
        ("Asymmetry by sign of ect (a1)", f"lambda+ {a.loc['a1', 'lambda_1']:.3f}, lambda- {a.loc['a1', 'lambda_2']:.3f}, "
                                          f"Wald p {a.loc['a1', 'wald_p_equal']:.3f}", "asymmetry_tests.csv"),
        ("Asymmetry easing vs. other (a2)", f"easing {a.loc['a2', 'lambda_1']:.3f}, other {a.loc['a2', 'lambda_2']:.3f}, "
                                            f"Wald p {a.loc['a2', 'wald_p_equal']:.3f}", "asymmetry_tests.csv"),
        ("2022Q3 level dummy (c)", f"delta {dm['delta']:.3f} (p {dm['delta_p']:.3f}), long-run shift {dm['LR_shift']:.3f}, "
                                   f"theta {dm['theta']:.3f} vs. {dm['theta_champion']:.3f}", "dummy_ecm.csv"),
        ("Rolling-origin beta", f"{betas.beta.iloc[0]:.3f} ({betas.origin.iloc[0]}) to {betas.beta.iloc[-1]:.3f} "
                                f"({betas.origin.iloc[-1]}), falling at {int((betas.beta.diff().dropna() < 0).sum())} "
                                f"of {len(betas) - 1} steps", "Beta_Backtesting/output/Huntington National Bank/"),
        ("Champion many-start-date rating", f"{f.loc['champion', 'rating']} ({f.loc['champion', 'reason']})",
         "assessment_fixed_limits_8Q.csv"),
        ("Best challenger rating", "; ".join(f"{m}: {f.loc[m, 'rating']} (mean {f.loc[m, 'mean_mae']:.3f})"
                                             for m in f.index if m != "champion"), "assessment_fixed_limits_8Q.csv"),
        ("Champion + D.FFT.L0 (h1)", f"coef {full.params[f'D.{x}.L0']:.3f} (p {full.res.pvalues[f'D.{x}.L0']:.3f}); "
                                     f"mean h-step MAE {h1_rating['mean_mae']:.3f}, rating {h1_rating['rating']}"
                                     f"{' (' + h1_rating['reason'] + ')' if h1_rating['reason'] else ''}",
         f"huntington_h1_multiorigin_{horizon}Q.csv"),
    ]
    ev = pd.DataFrame(items, columns=["item", "result", "source"])
    ev.to_csv(OUT / "huntington_evidence.csv", index=False)
    return ev, sub, table, h1_rating


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reps", type=int, default=2000, help="Monte Carlo reps for GH critical values")
    parser.add_argument("--first-origin", default="2016Q1")
    parser.add_argument("--horizon", type=int, default=8)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
    OUT.mkdir(parents=True, exist_ok=True)

    banks, specs = load_inputs()
    _, gh_summary, _ = run_gregory_hansen(banks, specs, args.reps)
    paths, tables, fixed, labels = run_challengers(banks, specs, args.first_origin, args.horizon)
    comparison(fixed, tables, args.horizon)
    asym, dummy, _ = full_sample_tests(banks, specs, args.horizon)
    oi8(paths, labels)
    oi8_decomposition(specs, args.horizon)
    plot_bank_mae(banks, tables, labels, args.horizon)
    plot_oi8(paths, specs, labels)
    ev, *_ = huntington(specs, args.horizon, args.first_origin, gh_summary, fixed, asym, dummy)
    log.info("Huntington evidence:\n%s", ev.to_string(index=False))
    log.info("done: outputs in %s", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
