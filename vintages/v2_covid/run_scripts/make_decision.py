"""Write vintages/v2_covid/covid_dummy_decision.csv: per bank, covid_liq with vs without.

"Without" = the v2 results (v2 folder where it holds a file, else v1 repo root; M&T and Old National are in v2).
"With" = vintages/v2_covid (every surviving spec re-estimated with covid_liq offered as a short-run candidate,
pruned at p >= 0.05; selection, many-origin backtests and theta stability rerun on that candidate set).

Inclusion rule (all three): (1) covid_liq survives pruning in the bank's selected (with-dummy) champion;
(2) the with-dummy champion's OOS mean MAE <= the without champion's OOS mean MAE + its one SE (oos_se);
(3) its theta-stability rating is not worse (Green < Amber < Red). When (1) fails the dummy is not in the
selected model, so coef and p report the champion's own spec with the dummy forced in (full sample, no pruning).
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "MAE_Backtesting"))
import backtest as bt  # noqa: E402
import bank_plots as bp  # noqa: E402

est, asym = bt.est, bt.asym
W, V2 = bp.OUTPUT_ROOT, bp.DATA_ROOT
K = ["test_name", "IC/selected lag", "trend type"]
RANK = {"Green": 0, "Amber": 1, "Red": 2}


def without(rel):
    """v2 file when present, else v1 (a bank's rows are in exactly one of them for per-bank folders)."""
    return pd.read_csv(V2 / rel) if (V2 / rel).is_file() else pd.read_csv(ROOT / rel)


def without_rows(rel):
    a, b = pd.read_csv(ROOT / rel), (pd.read_csv(V2 / rel) if (V2 / rel).is_file() else None)
    return a if b is None else pd.concat([a[~a.bank_name.isin(b.bank_name)], b])


def pick(scores, bank):
    r = scores[(scores.bank_name == bank) & scores["pick"]]
    return r.iloc[0]


def skill(multi, bank):
    t = multi[multi.bank_name == bank]
    return float((t.mae / t.naive_mae).max())


def main():
    sel = "MAE_Backtesting/output/out_of_sample/selection_oos_scores_8Q.csv"
    mul = "MAE_Backtesting/output/out_of_sample/backtest_multiorigin_8Q.csv"
    bet = "Beta_Backtesting/output/out_of_sample/beta_backtest_multiorigin_assessment.csv"
    sw, so = pd.read_csv(W / sel), without_rows(sel)
    mw, mo = pd.read_csv(W / mul), without_rows(mul)
    bw, bo = pd.read_csv(W / bet), without_rows(bet)
    summary, estimates = bt.load_candidates()  # with-dummy candidate files (vintages/v2_covid)
    source = bp.load_source(bp.DEFAULTS["dependents"], bp.DEFAULTS["independents"])
    rows = []
    for bank in sorted(sw.bank_name.unique()):
        cw, co = pick(sw, bank), pick(so, bank)
        model_w, model_o = tuple(cw[K]), tuple(co[K])
        has = "covid_liq" in str(cw["terms"]).split(" + ")
        data = bp.bank_data(source, "bank_name", bank, "rate_pf_clean", "FFT")
        spec_rows = bt.bank_rows(estimates, bank)
        spec_rows = spec_rows[bt.model_mask(spec_rows, model_w)]
        if has:
            r = spec_rows[spec_rows.term == "covid_liq"].iloc[0]
            coef, p, basis = float(r.coef), float(r.p_value), "selected model (survived pruning)"
        else:  # champion spec with the dummy forced in
            t = bt.MAEBacktest(bank, model_w, 8, data, spec_rows)
            sr = t.short_run + [(bp.COVID, 0)]
            res = (asym.fit(data, "rate_pf_clean", t.det, t.levels, sr, t.split_lambda) if t.asymmetric
                   else est.fit_one_step(data, "rate_pf_clean", t.det, t.levels, sr))
            coef, p, basis = float(res.params[bp.COVID]), float(res.pvalues[bp.COVID]), "champion spec, dummy forced in"
        dummy = sw[(sw.bank_name == bank) & sw["terms"].str.contains("covid_liq") & sw.admissible]
        rw, ro = bw[bw.bank_name == bank].iloc[0], bo[bo.bank_name == bank].iloc[0]
        c1 = has
        c2 = bool(cw.oos_mae <= co.oos_mae + co.oos_se + 1e-12)
        c3 = RANK[rw.rating] <= RANK[ro.rating]
        rows.append({
            "bank_name": bank, "covid_coef": coef, "covid_p": p, "coef_basis": basis,
            "champion_without": " | ".join(model_o), "champion_with": " | ".join(model_w),
            "champion_same": model_w == model_o, "dummy_in_champion": has,
            "mean_mae_without": float(co.oos_mae), "mean_mae_with": float(cw.oos_mae), "oos_se_without": float(co.oos_se),
            "worst_skill_without": skill(mo, bank), "worst_skill_with": skill(mw, bank),
            "theta_rating_without": ro.rating, "theta_rating_with": rw.rating,
            "n_dummy_candidates": int(sw[(sw.bank_name == bank)]["terms"].str.contains("covid_liq").sum()),
            "best_dummy_candidate_mae": float(dummy.oos_mae.min()) if len(dummy) else float("nan"),
            "rule1_survives_pruning": c1, "rule2_mae_within_1se": c2, "rule3_theta_not_worse": c3,
            "decision": "include" if (c1 and c2 and c3) else "exclude"})
    out = pd.DataFrame(rows)
    out.to_csv(W / "covid_dummy_decision.csv", index=False)
    show = ["bank_name", "covid_coef", "covid_p", "dummy_in_champion", "mean_mae_without", "mean_mae_with", "worst_skill_with",
            "theta_rating_with", "decision"]
    print(out[show].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
