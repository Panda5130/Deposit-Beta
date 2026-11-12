"""One-shot batched update of the WIP doc for integration batch 1.0 (2026-11-11). Run once from the repo root."""
from pathlib import Path

import pandas as pd

DOC = Path("WIP Regional Banking Deposit Beta Analyses.md")
s = DOC.read_text(encoding="utf-8")


def rep(old, new):
    global s
    n = s.count(old)
    assert n == 1, f"{n} matches for: {old[:80]!r}"
    s = s.replace(old, new)


def insert_before(anchor, text):
    rep(anchor, text + anchor)


# 0.1 Revision history: row stays 1.0, add this batch's note -------------------------------------------
rep("The deposit rate keeps the 2-point average; a 4-point trailing average was tested and rejected (§4.2). |",
    "The deposit rate keeps the 2-point average; a 4-point trailing average was tested and rejected (§4.2). "
    "Same date, integration batch: deterministic terms are pruned after the cointegration screen (§3.3, §5.5); "
    "Glacier's champion loses its trend (θ 0.277 → 0.230, still Red) and M&T's is relabelled `c` with unchanged "
    "estimates (§6.2, §6.5, L19); MAE stability is rated against the approved fixed reference v1, which closes #8 "
    "(§5.6, §7.1); the trend-freeze accuracy check (§5.6); and a ±200 bp FFT scenario analysis (§7.9). |")

# 1.3 Champions table and bullets ---------------------------------------------------------------------
rep("| Glacier Bank | Johansen VECM (rank 1), k_ar_diff = 1, det_order 1, BIC | -0.158 | 0.277 | 0.0310 | 0.263 | 1.19 | Red | Red |",
    "| Glacier Bank | Johansen VECM (rank 1), k_ar_diff = 1, det_order 1, BIC; trend pruned | -0.139 | 0.230 | 0.0327 | 0.271 | 1.23 | Red | Red |")
rep("| Manufacturers and Traders Trust Company | EG long run, trend `n`, AIC (ADF lag=1, ECM lag=4) | -0.195 | 0.402 | 0.0499 | 0.275 | 0.74 | Green | Red |",
    "| Manufacturers and Traders Trust Company | EG long run, trend `c`, AIC (ADF lag=1, ECM lag=4); constant pruned | -0.195 | 0.402 | 0.0499 | 0.275 | 0.74 | Green | Red |")
rep("Long-run betas fall between 0.28 (Glacier) and 0.52 (SouthState).",
    "Long-run betas fall between 0.23 (Glacier) and 0.52 (SouthState).")
rep("- **Glacier is Red on MAE:** its new champion loses to the no-change forecast at 5Q (skill ratio 1.19).",
    "- **Glacier is Red on MAE:** after its insignificant trend is pruned (§5.5), its champion loses to the no-change "
    "forecast from 3Q (worst skill ratio 1.23 at 7Q) and its 5–8Q maximum (0.493) exceeds the red limit.")
rep("- MAE ratings use limits set from the new champions as a peer group, which are looser at 1–2Q than version 0.1's (§7.1).",
    "- MAE ratings use the fixed limits of reference v1, frozen from these champions and approved on 2026-11-11 (§5.6, §7.1). "
    "They equal this run's peer-derived limits, so no rating changes. Under a ±200 bp FFT shock, pass-through after "
    "12 quarters is 0.24 (Glacier) to 0.51 (SouthState) (§7.9).")

# 3.3 Pipeline -----------------------------------------------------------------------------------------
rep("| 7 | One-step ECM estimation and lag pruning | `ECM estimation.py` | `ECM estimation results.csv`, `estimation result summary.csv` |",
    "| 7 | One-step ECM estimation, lag pruning and deterministic-term pruning | `ECM estimation.py`, `deterministic_pruning.py` | "
    "`ECM estimation results (det pruned).csv`, `estimation result summary (det pruned).csv`, `deterministic_pruning_log.csv` "
    "(the unpruned `ECM estimation results.csv` and `estimation result summary.csv` are kept unchanged) |")
rep("| 7b | Asymmetric variant of each surviving specification | `ECM asymmetric variants.py` | `ECM asymmetric estimation results.csv`, `asymmetric estimation result summary.csv`, `ECM asymmetric tests.csv` |",
    "| 7b | Asymmetric variant of each surviving specification, with the same deterministic-term pruning | `ECM asymmetric variants.py` | "
    "`ECM asymmetric estimation results (det pruned).csv`, `asymmetric estimation result summary (det pruned).csv`, "
    "`ECM asymmetric tests (det pruned).csv` (unpruned originals kept) |")
rep("| 8 | Out-of-sample champion choice, backtests and ratings | `MAE_Backtesting/run_backtest.py`, `backtest.py` | `MAE_Backtesting/output/out_of_sample/` |",
    "| 8 | Out-of-sample champion choice, backtests and ratings against the approved fixed reference | `MAE_Backtesting/run_backtest.py`, `backtest.py` | "
    "`MAE_Backtesting/output/out_of_sample/`, `MAE_Backtesting/reference/reference_v<k>.csv/.json` |")
rep("| 12 | Scenario projection with trend freeze | `projection/project.py` with a scenario CSV of FFT by quarter | `projection/output/<scenario>_projection.csv` |",
    "| 12 | Scenario projection with trend freeze | `projection/project.py` with a scenario CSV of FFT by quarter | `projection/output/<scenario>_projection.csv` |\n"
    "| 12b | ±200 bp FFT scenarios (instant and 4-quarter ramp) | `projection/run_scenarios.py` | `projection/output/scenarios/`, `docs/figures/scenarios/` |\n"
    "| 13 | Batch rerun and verification | `tools/run_batch.py`, `tools/verify_batch.py` | `verify_summary.json` |")
rep("Steps 5 to 7b are run together by `ECM workflow.py`.",
    "Steps 5 to 7b are run together by `ECM workflow.py`. Downstream steps read the pruned files (`bank_plots.CANDIDATE_FILES`).")

# 5.5 Deterministic pruning step -------------------------------------------------------------------------
rep("4. **Estimation:** one-step OLS ECM (§3.2), with long-run coefficients and delta-method standard errors. Short-run lags with p ≥ 0.05 are then removed one at a time (largest p first) and the model refit. λ, the long-run regressor and the deterministic terms are never removed.",
    "4. **Estimation:** one-step OLS ECM (§3.2), with long-run coefficients and delta-method standard errors. Short-run lags with p ≥ 0.05 are then removed one at a time (largest p first) and the model refit. λ and the long-run regressor are never removed.\n"
    "   - **Deterministic-term pruning (after the screen):** once short-run pruning is done, a trend with p ≥ 0.05 is dropped and the model refit, then a constant the same way (`deterministic_pruning.py`). The cointegration screen of step 1 comes first and is not rerun: a pruned model is kept with its qualifying test, and `deterministic_pruning_log.csv` records the qualifying case, the remaining form and the flag `form_differs_from_qualifying_test` (L19). The model's `trend type` label still names the screened case.\n"
    "   - 20 original and 12 asymmetric models lose a term; none is dropped. Two champions change: Glacier loses its trend (p 0.099; θ 0.277 → 0.230) and M&T's champion becomes the `c` specification, whose constant is pruned, so it is numerically identical to the `n` specification it replaces. SouthState is the only champion that keeps a trend (p 0.002).")
rep("   - Wald tests of λ⁺ = λ⁻, θ⁺ = θ⁻, Σγ⁺ = Σγ⁻ and Σφ⁺ = Σφ⁻ are reported in `ECM asymmetric tests.csv`.",
    "   - Wald tests of λ⁺ = λ⁻, θ⁺ = θ⁻, Σγ⁺ = Σγ⁻ and Σφ⁺ = Σφ⁻ are reported in `ECM asymmetric tests.csv`.\n"
    "   - Deterministic terms are pruned after the pair pruning, as in step 4.")

# 5.6 MAE stability against the fixed reference; trend freeze ----------------------------------------------
rep("- **Band limits, derived each run from the peer group:** green = the 75th percentile of the banks' band-average MAE, rounded up to 0.05; red = the 75th percentile of the banks' band-maximum MAE, rounded up to 0.05, and at least green + 0.05.",
    "- **Band limits, from an approved fixed reference:** green = the 75th percentile of the banks' band-average MAE, rounded up to 0.05; red = the 75th percentile of the banks' band-maximum MAE, rounded up to 0.05, and at least green + 0.05. The percentiles are taken from a frozen reference run, not from each run's peers.\n"
    "  - **Reference v1** (`MAE_Backtesting/reference/reference_v1.csv/.json`) holds each champion's h = 1 to 12 errors from 2016Q1, frozen on 2026-11-11 (trigger `initial`) and approved by the model owner (`approved_by`). Reference files are immutable; a new version is frozen with `run_backtest.py --freeze-reference --reference-trigger <trigger>` when a trigger is met (new champion, data revision, periodic review) and is used only after it is approved.\n"
    "  - `--limits auto` (default) uses the newest approved reference and falls back to peer-derived limits if none exists; `--limits peer` and `--limits-from FILE` force either.\n"
    "  - v1's limits for N = 8 equal this run's peer-derived limits (§7.1), so no rating changes at adoption. From now on, one bank's re-specification no longer moves another bank's limits.\n"
    "  - Beta stability keeps its own rule, judged against each champion's own full-sample θ.")
rep("- The limits are relative to the peer group: by construction, about a quarter of banks exceed the green limit in each band. The skill test is the only absolute standard. Fixing the limits from a reference run is a candidate refinement.",
    "- The reference limits are still set relative to a peer group, the one frozen in the reference. The skill test remains the only absolute standard.\n"
    "- **Trend freeze in the backtest (`--freeze-trend`, `MAE_Backtesting/trend_freeze_comparison.py`):** holding the trend at its start-date value over each forecast, as in projection (§5.7), changes SouthState's (the only champion with a trend) h-step MAE by −0.0003 to −0.012 pp, mean −0.0033 pp, and doesn't change its rating. The freeze slightly helps accuracy, which supports its use in projection.¹\n\n"
    "  ¹ Before deterministic pruning, Glacier's champion also carried a trend; freezing it lowered Glacier's mean h-step MAE by 0.0020 pp (`trend_freeze_comparison_glacier_prepruning.csv`).")

# 6.2 Glacier ---------------------------------------------------------------------------------------------
rep("""Chosen by the parsimony step: 5 parameters, against 7 for the version 0.1 champion (ARDL(3,1), case 4). The constant and trend follow the det_order 1 test. The best-scoring model is still the version 0.1 champion.

| Term | Coefficient | *t* | p-value |
| :--- | :-: | :-: | :-: |
| const | 0.0440 | 2.57 | 0.013 |
| trend | -0.00095 | -1.54 | 0.129 |
| y.L1 (λ) | **-0.1580** | -5.24 | 2.6e-06 |
| FFT.L1 | 0.0437 | 4.13 | 1.2e-04 |
| D.y.L1 | 0.5333 | 5.72 | 4.5e-07 |
| LR: const | 0.2786 | 3.09 | 0.0032 |
| LR: trend | -0.00602 | -1.68 | 0.099 |
| **LR: FFT (θ)** | **0.2769** | 7.44 | 7.3e-10 |""",
    """Chosen by the parsimony step: 4 parameters, against 5 for the version 0.1 champion (ARDL(3,1), case 4, also pruned), which is still the best-scoring model. The det_order 1 test qualifies the model with a constant and trend; the trend (long-run p 0.099) is pruned after the screen (§5.5), so the fitted form has a constant only and differs from its qualifying test (L19). Before pruning, θ was 0.277 and λ −0.158.

| Term | Coefficient | *t* | p-value |
| :--- | :-: | :-: | :-: |
| const | 0.0218 | 2.33 | 0.023 |
| y.L1 (λ) | **-0.1388** | -4.99 | 6.1e-06 |
| FFT.L1 | 0.0319 | 4.32 | 6.5e-05 |
| D.y.L1 | 0.5846 | 6.63 | 1.4e-08 |
| LR: const | 0.1571 | 2.58 | 0.013 |
| **LR: FFT (θ)** | **0.2300** | 8.20 | 3.6e-11 |""")
rep("- **Governing MAE rating (many-start-date backtest, §5.6): Red** (skill ratio 1.19 at 5Q). h-step MAE, 1Q to 8Q, over 34 to 41 start dates: 0.049, 0.111, 0.179, 0.248, 0.313, 0.369, 0.403, 0.434 (mean 0.263). Worst skill ratio against the no-change forecast: 1.19 at 5Q.\n- Single-window 8Q backtest (one start date per horizon, supplementary): 0.102, 0.042, 0.033, 0.102, 0.253, 0.290, 0.146, 0.306; mean 0.159, no-change mean 0.119, beats no-change on 3/8 horizons (Amber).",
    "- **Governing MAE rating (many-start-date backtest, §5.6): Red** (5–8Q maximum 0.493 > red 0.45; skill ratio 1.23 at 7Q). h-step MAE, 1Q to 8Q, over 34 to 41 start dates: 0.043, 0.103, 0.167, 0.234, 0.308, 0.380, 0.440, 0.493 (mean 0.271, 0.263 before pruning). Worst skill ratio against the no-change forecast: 1.23 at 7Q.\n- Single-window 8Q backtest (one start date per horizon, supplementary): 0.087, 0.029, 0.020, 0.050, 0.194, 0.204, 0.069, 0.135; mean 0.099, no-change mean 0.119, beats no-change on 5/8 horizons (Amber).")
rep("- **MAE Red:** the champion loses to the no-change forecast at 5Q (skill ratio 1.19). Glacier's deposit rate moves little, so the no-change forecast is hard to beat; the version 0.1 champion was Amber for the same reason (0.96).",
    "- **MAE Red:** the champion loses to the no-change forecast from 3Q (skill ratios 1.03 to 1.23). Glacier's deposit rate moves little, so the no-change forecast is hard to beat; the version 0.1 champion was Amber for the same reason (0.96). Pruning the trend improves 1Q to 4Q errors and worsens 6Q to 8Q.")
rep("- **Long-run beta stability (§5.6): Red.** From 2020Q1 to 2026Q1, θ ranges from 0.103 to 0.273 against the full-sample 0.277. The largest deviation is 63% (2022Q3) and at most 8.47 origin standard errors (2022Q4). Failing start dates: 15 (2020Q1 2020Q2 2020Q3 2020Q4 2021Q1 2021Q2 2021Q3 2021Q4 2022Q1 2022Q2 2022Q3 2022Q4 2023Q1 2023Q4 2024Q1).",
    "- **Long-run beta stability (§5.6): Red.** From 2020Q1 to 2026Q1, θ ranges from 0.029 to 0.339 against the full-sample 0.230. The largest deviation is 88% (2020Q3) and at most 5.17 origin standard errors (2020Q1). Failing start dates: 12 (2020Q1 to 2022Q4).")
rep("- **Realized beta (§5.6, descriptive):** mean actual beta 1Q to 8Q 0.24, 0.21, 0.21, 0.21, 0.22, 0.09, 0.09, 0.11; model-implied 0.14, 0.17, 0.22, 0.22, 0.15, -0.04, -0.02, -0.02.",
    "- **Realized beta (§5.6, descriptive):** mean actual beta 1Q to 8Q 0.24, 0.21, 0.21, 0.21, 0.22, 0.09, 0.09, 0.11; model-implied 0.16, 0.19, 0.25, 0.26, 0.23, -0.25, -0.19, -0.20.")

# 6.5 M&T ---------------------------------------------------------------------------------------------------
rep("#### 6.5.6 Champion Model: EG long run, trend `n`, AIC (ADF lag=1, ECM lag=4)\nChosen by the parsimony step: 3 parameters, against 6 for the version 0.1 champion (ARDL(2,1), case 4), which is still the best-scoring model. It has no deterministic terms, so no trend is frozen for projection.",
    "#### 6.5.6 Champion Model: EG long run, trend `c`, AIC (ADF lag=1, ECM lag=4); constant pruned\nChosen by the parsimony step: 3 parameters, against 6 for the version 0.1 champion (ARDL(2,1), case 4), which is still the best-scoring model. The `c` specification qualifies with a constant, which is pruned after the screen (§5.5). The fitted model is then identical to the `n` specification chosen before pruning, and the tie-break picks the `c` label; every estimate and backtest result below is unchanged. It has no deterministic terms, so no trend is frozen for projection.")

# 7.1 / 7.2 / 7.3 ---------------------------------------------------------------------------------------------
rep("| Glacier Bank | 0.049 | 0.111 | 0.179 | 0.248 | 0.313 | 0.369 | 0.403 | 0.434 | 0.263 | 0.235 | 1.19 | **Red** |",
    "| Glacier Bank | 0.043 | 0.103 | 0.167 | 0.234 | 0.308 | 0.380 | 0.440 | 0.493 | 0.271 | 0.235 | 1.23 | **Red** |")
rep("Band limits for N = 8, derived from this run (§5.6):",
    "Band limits for N = 8, from the approved fixed reference v1 (§5.6); this run's peer-derived limits are identical:")
rep("The limits come from the new champions as a peer group. The 1–2Q limits are looser than version 0.1's (0.10/0.15), because the simpler champions have higher short-horizon errors. The skill ratio does not depend on the peer group: every champion is below 0.75 except Glacier (1.19 at 5Q). Fixing the limits from a reference run is tracked in [#8](https://github.com/Panda5130/Deposit-Beta/issues/8).",
    "Reference v1 was frozen from these champions. Its 1–2Q limits are looser than version 0.1's (0.10/0.15), because the simpler champions have higher short-horizon errors. The skill ratio does not depend on the limits: every champion is below 0.75 except Glacier (1.23 at 7Q). First Horizon's 5–8Q maximum (0.449) is 0.001 below the red limit, so a small deterioration would turn it Red now that the limits no longer move with the peers. Fixed limits resolve [#8](https://github.com/Panda5130/Deposit-Beta/issues/8).")
rep("| Glacier Bank | 0.102 | 0.042 | 0.033 | 0.102 | 0.253 | 0.290 | 0.146 | 0.306 | 0.159 | 0.119 | Amber |",
    "| Glacier Bank | 0.087 | 0.029 | 0.020 | 0.050 | 0.194 | 0.204 | 0.069 | 0.135 | 0.099 | 0.119 | Amber |")
rep("- Long-run betas range from 0.28 (Glacier) to 0.52 (SouthState).",
    "- Long-run betas range from 0.23 (Glacier) to 0.52 (SouthState).")

# 7.4 / 7.5 / 7.6 / 7.7 Glacier rows (consistency with the pruned champion) -----------------------------------
rep("| Glacier Bank | 0.263 Red | 0.344 Red | 0.305 Red | 0.265 Red | 0.204 Amber | 0.253 Red |",
    "| Glacier Bank | 0.271 Red | 0.311 Red | 0.301 Red | 0.265 Red | 0.204 Amber | 0.277 Red |")
rep("and the cycle betas at Glacier (0.204 vs 0.263).", "and the cycle betas at Glacier (0.204 vs 0.271).")
rep("| Glacier Bank | 0.277 | 0.103 to 0.273 | 63%, 2022Q3 | 8.47, 2022Q4 | 15 | **Red** |",
    "| Glacier Bank | 0.230 | 0.029 to 0.339 | 88%, 2020Q3 | 5.17, 2020Q1 | 12 | **Red** |")
rep("- Glacier's beta is the least stable: about 0.10–0.14 until the 2022–23 hiking cycle enters the sample.",
    "- Glacier's beta is the least stable: well below its full-sample value until the 2022–23 hiking cycle enters the sample.")
rep("| Glacier Bank | Out of sample (default): Johansen VECM (rank 1), k_ar_diff = 1, det_order 1, BIC | 5 | 0.0310 | 0.263 (0.087) | 0.277 | Red | Red |\n| | In sample (optional): ARDL(3,1), case 4, BIC | 7 | 0.0292 | 0.207 (0.079) | 0.346 | Amber | Red |",
    "| Glacier Bank | Out of sample (default): Johansen VECM (rank 1), k_ar_diff = 1, det_order 1, BIC; trend pruned | 4 | 0.0327 | 0.271 (0.127) | 0.230 | Red | Red |\n| | In sample (optional): ARDL(3,1), case 4, BIC; pruned | 5 | 0.0296 | 0.242 (0.097) | 0.310 | Amber | Red |")
rep("| Manufacturers and Traders Trust Company | Out of sample (default): EG long run, trend `n`, AIC (ADF lag=1, ECM lag=4) | 3 |",
    "| Manufacturers and Traders Trust Company | Out of sample (default): EG long run, trend `c`, AIC (ADF lag=1, ECM lag=4); constant pruned | 3 |")
rep("| Glacier Bank | 0.24 / 0.14 | 0.21 / 0.17 | 0.21 / 0.22 | 0.11 / -0.02 |",
    "| Glacier Bank | 0.24 / 0.16 | 0.21 / 0.19 | 0.21 / 0.26 | 0.11 / -0.20 |")
rep("Glacier's implied beta turns slightly negative at 8Q.", "Glacier's implied beta turns negative from 6Q (−0.20 at 8Q).")

# 7.9 Scenario analysis (new) ------------------------------------------------------------------------------------
pt = pd.read_csv("projection/output/scenarios/scenario_passthrough.csv")
w = pt.pivot_table(index="bank", columns=["scenario", "k"], values="passthrough")
rows = []
for bank, r in w.iterrows():
    cells = [f"{r[(sc, k)]:.2f}" for sc in ("up_instant", "up_ramp") for k in (4, 8, 12)]
    if bank.startswith("KeyBank"):
        down = " / ".join(f"{r[('down_instant', k)]:.2f}" for k in (4, 8, 12))
        downr = " / ".join(f"{r[('down_ramp', k)]:.2f}" for k in (4, 8, 12))
        note = f"down: {down} (instant), {downr} (ramp)"
    else:
        note = "same as up"
    rows.append(f"| {bank} | " + " | ".join(cells) + f" | {note} |")
fig = lambda b: f"docs/figures/scenarios/{b.replace(' ', '_')}.png"
sec79 = f"""### 7.9 Scenario Analysis (±200 bp FFT)
Each champion is projected 12 quarters past 2026Q3 under five FFT paths (`projection/run_scenarios.py`, scenario files `projection/scenarios/scn_*.csv`). The deposit data end at 2026Q2 and the FFT file holds the actual 2026Q3 value (3.67%), so every path starts from 2026Q3 at the actual FFT and the shock begins in 2026Q4:

- **base:** FFT flat at 3.67%;
- **up / down instant:** ±200 bp in 2026Q4, then flat;
- **up / down ramp:** ±50 bp a quarter for four quarters (2026Q4 to 2027Q3), then flat.

Projections use the trend freeze (§5.7); after pruning, only SouthState's champion has a trend. Pass-through at k quarters after the shock is (rate under the scenario − base rate) ÷ the full ±2.00 pp shock: the cumulative share of the shock passed to the deposit rate. k = 12 is 2029Q3.

| Bank | Up instant, k = 4 | k = 8 | k = 12 | Up ramp, k = 4 | k = 8 | k = 12 | Down shock |
| :--- | :-: | :-: | :-: | :-: | :-: | :-: | :--- |
{chr(10).join(rows)}

*Source: `projection/output/scenarios/scenario_passthrough.csv`.*

![All banks: cumulative pass-through of a ±200 bp FFT shock](<docs/figures/scenarios/all_banks_passthrough.png>)

*Figure 32: Cumulative pass-through by quarter after the shock, four scenarios, all banks.*

- After 12 quarters, pass-through is 0.24 (Glacier) to 0.51 (SouthState), within about 0.02 of each champion's long-run θ: most of the long-run adjustment is complete by then. Instant and ramp paths converge by k = 12 (largest gap 0.02 pp, M&T).
- The ramp delays pass-through: at k = 4, it is 0.06 to 0.29 against 0.13 to 0.40 under the instant shock.
- Every symmetric champion responds to a cut exactly as to a rise, mirrored. KeyBank's asymmetric champion passes a cut through faster than a rise at short horizons (ramp, k = 4: 0.34 down vs 0.20 up), because its adjustment speed and short-run ΔFFT and Δy terms are split by sign (§6.4.6). Its pass-through is about 0.40 in both directions by k = 12.
- Glacier, with the lowest θ, passes through least and slowest.

![KeyBank National Association: deposit rate under the five FFT scenarios](<{fig('KeyBank National Association')}>)

*Figure 33: KeyBank National Association, projected deposit rate under the five FFT scenarios (FFT dotted, right axis), champion model.*

![Glacier Bank: deposit rate under the five FFT scenarios](<{fig('Glacier Bank')}>)

*Figure 34: Glacier Bank, projected deposit rate under the five FFT scenarios (FFT dotted, right axis), champion model.*

Charts for the other banks are in `docs/figures/scenarios/`.

---

"""
insert_before("## 8. Model Limitations and Assumptions", sec79)
rep("Details are in `docs/resolutions/asymmetry_oos_realized_beta.md`.\n\n---\n\n### 7.9", "Details are in `docs/resolutions/asymmetry_oos_realized_beta.md`.\n\n### 7.9")

# 8 Limitations ---------------------------------------------------------------------------------------------------
rep("| L12 | Glacier's champion keeps an insignificant constant and trend because its case 4 test requires them | Glacier | Low |",
    "| L12 | Resolved 2026-11-11: insignificant deterministic terms are now pruned after the screen (§5.5); see L19. | — | — |")
rep("| L14 | Deterministic trends in the Glacier and SouthState champions are frozen at their 2026Q2 value for projection (`projection/project.py`). The freeze is a judgment overlay, not an estimated feature; projections for these banks depend on that choice. | Glacier, SouthState | Medium |",
    "| L14 | The deterministic trend in SouthState's champion, the only champion that keeps one after pruning, is frozen at its 2026Q2 value for projection (`projection/project.py`). The freeze is a judgment overlay, not an estimated feature; projections for this bank depend on that choice. Freezing in the backtest slightly lowers SouthState's errors (§5.6). | SouthState | Medium |")
rep("| L16 | Backtest limits are percentiles of the peer group, so the absolute test is a relative standard: one bank's re-specification can change another's rating (First Horizon turned Red after the Huntington and Old National re-specification (§5.5) with unchanged errors). The single-window backtest has one start date per horizon. | All | Medium |",
    "| L16 | Backtest limits come from the peer group frozen in reference v1 (§5.6), so the absolute test is still a relative standard, fixed at 2026-11-11 champions; it no longer moves when another bank is re-specified, and needs a governed re-freeze when a trigger is met. The single-window backtest has one start date per horizon. | All | Medium |")
rep("| L18 | The asymmetric fits are fragile: 23 of 78 cycled between regime splits, and several admissible variants forecast explosively. KeyBank's asymmetric champion rests on a λ split estimated from the regimes of one sample. | KeyBank, all asymmetric variants | Medium |",
    "| L18 | The asymmetric fits are fragile: 23 of 78 cycled between regime splits, and several admissible variants forecast explosively. KeyBank's asymmetric champion rests on a λ split estimated from the regimes of one sample. | KeyBank, all asymmetric variants | Medium |\n"
    "| L19 | Deterministic terms are pruned after the cointegration screen without re-testing, so a pruned model's fitted form can differ from the form under which it passed (flag `form_differs_from_qualifying_test` in `deterministic_pruning_log.csv`; 32 models). Its `trend type` label still names the qualifying case. Glacier's champion qualified under det_order 1 (constant and trend) but is fitted with a constant only; M&T's qualified under `c` and is fitted without a constant. | Glacier, M&T, 30 non-champion models | Medium |")

# 9.2 Open issues: #8 resolved -----------------------------------------------------------------------------------
rep("""Open at this version:

| Issue | Topic | Section |
| :-: | :--- | :--- |
| [#8](https://github.com/Panda5130/Deposit-Beta/issues/8) | Fix backtest band limits from an approved reference run instead of deriving them from the peer group each run (on hold) | §5.6, §7.1 |
""",
    """Open at this version: none.

Resolved on 2026-11-11 by the integration batch: [#8](https://github.com/Panda5130/Deposit-Beta/issues/8) (backtest band limits fixed from an approved reference run, reference v1, §5.6, §7.1).
""")

DOC.write_text(s, encoding="utf-8")
print("doc updated")
