# OI-24: short-run terms for EG long-run specifications, and Huntington's re-specified champion

Resolution notes for OI-24 (provisional number, raised in `docs/resolutions/model_form.md` §4) and for the Huntington re-specification that the user chose on 2026-10-31 (option A, issue [#4](https://github.com/Panda5130/Deposit-Beta/issues/4), OI-19).

- Code: `ECM model selection.py` (new `carry_eg_short_run`). `ECM Param selection.py` and `ECM estimation.py` are unchanged.
- Outputs: the four ECM CSVs in the repo root, `MAE_Backtesting/output/` and `Beta_Backtesting/output/`, regenerated. The backtest modules themselves were run, not edited.
- Status: WIP. Nothing here has been folded into `WIP Regional Banking Deposit Beta Analyses.md`.

```bash
python "ECM workflow.py"
python MAE_Backtesting/run_backtest.py --horizon 8Q --bank-name All --first-origin 2016Q1 --no-cache
python Beta_Backtesting/run_beta_backtest.py
```

`--no-cache` is required for this run. The error cache is keyed on the model label and the data hash, not on the fitted terms. Huntington's label is unchanged, so without the flag the cache would return the old champion's errors (see §5).

---

## 1. Summary

1. **The fix.** Each EG long-run specification that passes the model screen now gets the short-run lags of its own Engle-Granger second-step regression: the `EG_ShortRun` rows with the same bank, IC/selected lag and trend type. These are the D.y and D.FFT lags up to the spec's ECM lag. They go through the same p < 0.05 parameter screen (step 2) and the same one-at-a-time pruning in the one-step ECM (step 3) as every other family.
2. **Three champions change, not one.**
   - **Huntington** keeps its specification label, but the champion now has six short-run terms: D.y L1 to L3 and D.FFT L0 to L2. Its rating moves from **Red to Green**, mean h-step MAE 0.334 → **0.221**. That is better than the single-term variant tested in `model_form` (D.FFT.L0 only, 0.240).
   - **Old National** changes champion, from the Johansen VECM (in-sample MAE 0.0414) to EG long run `n`, BIC (0.0285). It stays **Green**, mean 0.263 → 0.249.
   - **KeyBank** changes label only. EG long run `n`, BIC now gives exactly the same regression as the ARDL(4,4) case 1 champion (identical terms and MAE 0.03167), and the EG > ARDL tie-break (§5.5) picks it. Its coefficients, forecasts and rating are identical.
   - First Horizon, Glacier, M&T and SouthState are unchanged.
3. **Side effect on the peer limits: First Horizon goes Green → Red with no change to its own errors.** Huntington's and Old National's lower short-horizon errors tighten the peer-derived 1–2Q limits from 0.15/0.20 to 0.10/0.15. First Horizon's 2Q MAE of 0.179 now exceeds the red limit. The 5–8Q red limit also falls from 0.50 to 0.45, which leaves KeyBank Red (0.533). This follows from the peer-relative design (§5.6) and belongs to the eval-selection thread (issues [#1](https://github.com/Panda5130/Deposit-Beta/issues/1) and #10). It is flagged here, not resolved.
4. **Trade-offs in the new Huntington and Old National champions.**
   - **Slower error correction.** Huntington's λ falls from −0.313 (p 6e-11) to −0.066 (p 0.016), and Old National's from −0.135 to −0.086. The short-run terms now carry most of the dynamics.
   - **Large lagged-Δy terms.** Huntington: D.y.L1 0.86, L2 −0.90, L3 0.43. These are the momentum terms that OI-8 identified as the cause of the 2025Q1 start-date error at M&T, Old National and SouthState. Huntington's single window from 2025Q1 worsens from 0.094 to 0.187, above the no-change 0.135; this window has not been decomposed.
   - **A long-run beta that swings rather than drifts.** Huntington's θ is 0.463, against 0.469 before. Across origins it now ranges from 0.352 to 0.553 (largest deviation 0.110, 24%, 1.22 origin SEs). Before, it drifted one way from 0.551 to 0.465, with a 2.06-SE deviation. The one-directional drift and the over-2-SE flag are gone, but the range is wider.

---

## 2. The pipeline change

**What was wrong.** The EG test writes two row sets per specification:
- `EG_LongRun`: the levels regression plus the ADF lags of its residual (`ADF: resid.L1`, `ADF: D.resid.L1`);
- `EG_ShortRun`: the second-step ECM (`ect.L1`, D.y and D.FFT lags).

Step 3 treats `EG_LongRun` as error-correcting by construction (§5.5 item 3), but it ignores ADF rows. So an EG long-run ECM reached estimation with λ and the levels term only. Its short-run candidates sat in the `EG_ShortRun` group, which is screened separately and usually fails the model screen on its own `ect.L1` t-test (Huntington: p 0.257).

**Change** (`ECM model selection.py`, `carry_eg_short_run`, applied after the model screen):
- for each kept `EG_LongRun` specification, copy the `D.*` rows of the matching `EG_ShortRun` group, relabelled `EG_LongRun`;
- the copied rows keep their own coefficient p-values, and take the `EG_LongRun` model statistic and p-value (the test that validates the spec);
- the copied rows are placed right after their spec's rows, so the file order (the last tie-break in §5.5) is unchanged;
- `ect.L1` and the second-step constant are not copied. λ comes from y.L1 in the one-step ECM, and deterministic terms follow the trend type.

Steps 2 and 3 need no change. Step 2 drops copied lags with p ≥ 0.05, and step 3 picks up the survivors as `D.<v>.L<k>` and prunes them one at a time. Only `EG_LongRun` groups change. Every other family's output is identical, and the in-sample MAE of every non-EG-long-run specification is unchanged.

**Row counts:** model selection 637 → 762 rows (+125 copied lags); parameter selection 429 → 506. Estimation writes the same 78 models (555 → 629 term rows), with more terms in the EG long-run ones.

**Proposed §5.5 wording (item 3), replacing the last sentence:**

> `EG_LongRun` is treated as error-correcting by construction. Its short-run candidates are the D.y and D.FFT lags of the Engle-Granger second-step regression of the same specification, screened in step 2 like any other short-run term (OI-24).

---

## 3. Champions before and after

| Bank | Champion before | Champion after | In-sample MAE | Mean h-step MAE | Rating |
| :--- | :--- | :--- | :-: | :-: | :-: |
| First Horizon | ARDL(3,4) case 4, AIC | unchanged | 0.0469 | 0.242 | Green → **Red** (peer limits) |
| Glacier | ARDL(3,1) case 4, BIC | unchanged | 0.0292 | 0.207 | Amber |
| **Huntington** | EG long run `n`, AIC (no short-run terms) | EG long run `n`, AIC, with D.y L1–3 and D.FFT L0–2 | 0.0709 → 0.0234 | 0.334 → 0.221 | Red → **Green** |
| KeyBank | ARDL(4,4) case 1, AIC | EG long run `n`, BIC (identical regression) | 0.0317 | 0.280 | Red |
| M&T | ARDL(2,1) case 4, AIC | unchanged | 0.0383 | 0.218 | Green |
| **Old National** | Johansen VECM, det_order −1, k_ar_diff 1 | EG long run `n`, BIC | 0.0414 → 0.0285 | 0.263 → 0.249 | Green |
| SouthState | ARDL(4,3) case 1, AIC | unchanged | 0.0336 | 0.264 | Green |

Huntington's three passing specifications (AIC, BIC, t-stat; ADF lag 1, ECM lag 3) still give one identical ECM, so AIC stays the champion on file order.

---

## 4. Replacement text for `WIP Regional Banking Deposit Beta Analyses.md`

The main session folds these in. OI-24 is a provisional number; renumber it if another thread has used it. The figures referenced in §6.3 and §6.6 (`docs/figures/…`) were **not** regenerated in this branch, to avoid clashing with other threads' work on `docs/figures/`. The new backtest charts are in `MAE_Backtesting/output/<bank>/` and `Beta_Backtesting/output/<bank>/`. The actual-vs-predicted charts need `plotting_workflow.py` to be re-run when the text is folded in.

### §1.3 Summary of Current Results

> Every bank has at least one specification that is cointegrated with the federal funds rate at the 5% level, although for Huntington and Old National only after re-specification. The selected model for each bank is the specification with the lowest in-sample MAE (§5.5). The rating is the governing many-start-date backtest rating (§5.6).
>
> | Bank | Selected specification | Speed of adjustment (λ) | Long-run deposit beta (θ) | In-sample MAE (pp) | Many-start-date mean h-step MAE (pp) | Rating |
> | :--- | :--- | :-: | :-: | :-: | :-: | :-: |
> | First Horizon Bank | ARDL(3,4), case 4, AIC | -0.375 | 0.517 | 0.0469 | 0.242 | Red |
> | Glacier Bank | ARDL(3,1), case 4, BIC | -0.112 | 0.346 | 0.0292 | 0.207 | Amber |
> | Huntington National Bank | EG long run, no deterministic terms, AIC (ADF lag 1, ECM lag 3) | -0.066 | 0.463 | 0.0234 | 0.221 | Green |
> | KeyBank National Association | EG long run, no deterministic terms, BIC (ADF lag 1, ECM lag 3) | -0.110 | 0.398 | 0.0317 | 0.280 | Red |
> | Manufacturers and Traders Trust Company | ARDL(2,1), case 4, AIC | -0.184 | 0.432 | 0.0383 | 0.218 | Green |
> | Old National Bank | EG long run, no deterministic terms, BIC (ADF lag 1, ECM lag 3) | -0.086 | 0.394 | 0.0285 | 0.249 | Green |
> | SouthState Bank | ARDL(4,3), case 1, AIC | -0.082 | 0.443 | 0.0336 | 0.264 | Green |
>
> All λ and θ estimates are significant at the 5% level, all θ at 1%; λ at 1% except KeyBank (p 0.010), Old National (0.010) and Huntington (0.016). KeyBank's EG specification is the same regression as ARDL(4,4) case 1 and is chosen on the EG > ARDL tie-break (§5.5). Long-run betas fall between 0.35 and 0.52. Six series are I(1) under the default unit-root specification; Glacier is flagged (KPSS I(0) p 0.057). Re-estimated at the eight origins 2024Q2 to 2026Q1, each bank's θ deviates from its full-sample value by at most 0.025 (First Horizon) to 0.135 (KeyBank) (§7.5). First Horizon is rated Red only because the peer-derived 1–2Q red limit fell to 0.15 when the Huntington and Old National champions improved; its own errors are unchanged (§7.1).

### §6.3.5 Specifications Estimated

> 3 one-step ECMs (3 EG). In-sample MAE 0.0234 to 0.0234. Long-run beta 0.463 to 0.463.

### §6.3.6 Champion Model: Engle-Granger long run, trend `n`, AIC (ADF lag=1, ECM lag=3)

> All three passing specifications (AIC, BIC, t-stat) give the same one-step ECM. Short-run candidates are the D.y and D.FFT lags of the Engle-Granger second-step regression (§5.5, OI-24): D.y L1–L3 and D.FFT L0–L2 pass the screen and survive pruning; D.FFT.L3 (p 0.61) fails the screen.
>
> | Term | Coefficient | *t* | p-value |
> | :--- | :-: | :-: | :-: |
> | y.L1 (λ) | **-0.0665** | -2.49 | 0.016 |
> | FFT.L1 | 0.0308 | 2.51 | 0.015 |
> | D.y.L1 | 0.8553 | 7.22 | 2.7e-09 |
> | D.y.L2 | -0.8956 | -6.09 | 1.6e-07 |
> | D.y.L3 | 0.4322 | 4.92 | 9.7e-06 |
> | D.FFT.L0 | 0.1738 | 9.75 | 3.7e-13 |
> | D.FFT.L1 | -0.0995 | -3.05 | 0.0036 |
> | D.FFT.L2 | 0.1566 | 4.98 | 8.0e-06 |
> | **LR: FFT (θ)** | **0.4627** | 13.28 | 5.2e-18 |
>
> Before OI-24 the champion had no short-run terms (λ −0.313, θ 0.469, in-sample MAE 0.0709). The contemporaneous ΔFFT term now passes about 17% of a rate change through in the same quarter, and λ falls to −0.066: adjustment runs mainly through the short-run terms rather than through error correction.

### §6.3.7 Outcomes Analysis and Issues

> - **Governing rating (many-start-date backtest, §5.6): Green.** h-step MAE, 1Q to 8Q, over 34 to 41 start dates: 0.042, 0.097, 0.148, 0.199, 0.255, 0.307, 0.339, 0.381 (mean 0.221; previous champion 0.334, Red). Worst skill ratio against the no-change forecast: 0.49 at 6Q.
> - Single-window 8Q backtest (one start date per horizon, supplementary): 0.094, 0.132, 0.069, 0.049, 0.187, 0.287, 0.169, 0.214; mean 0.150, no-change mean 0.231, beats no-change on 4/8 horizons (Amber). The window from 2025Q1 (5Q column) worsens from 0.094 to 0.187, above no-change (0.135). The new champion carries large lagged-Δy terms, which OI-8 identified as the source of the 2025Q1 error at M&T, Old National and SouthState (OI-25).
> - **Scope decision (2026-10-31): Huntington stays in scope with a caveat** (OI-19, L15). Cointegration rests on one specification family (EG long run, no deterministic terms) and is identified mainly by the 2022–24 cycle: the EG test fails in every sample window ending in 2019Q4 and in 2021Q4 windows starting in 2013 or later, and Gregory-Hansen finds no break (`model_form/output/huntington_eg_subsamples.csv`).
> - **Adjustment asymmetry.** Huntington has the strongest asymmetry in the peer set (λ+ −0.118 vs. λ− −0.459, Wald p 1.4e-07, on the previous champion; `docs/resolutions/model_form.md` §3.2). An asymmetric-λ variant of the new champion has not been tested.
> - **Long-run beta stability (§5.6):** re-estimated at the eight origins 2024Q2 to 2026Q1, θ ranges from 0.352 to 0.553 against the full-sample 0.463. The largest deviation is 0.110 (24%) at 2024Q4, 1.22 origin standard errors. The estimates fall from 0.553 (2024Q2) to 0.352 (2024Q4), at the turn of the easing cycle, then recover to 0.42–0.45, the same dip as the other banks (§7.5). The previous champion's one-directional drift (0.551 to 0.465, 2.06 SEs at 2024Q2) is gone, but the range is wider.

### §6.4 KeyBank (consequential, label only)

> **§6.4.6 heading:** Champion Model: Engle-Granger long run, trend `n`, BIC (ADF lag=1, ECM lag=3).
>
> **First paragraph:** With short-run candidates now offered to EG long-run specifications (OI-24), EG long run `n` (BIC and t-stat) gives exactly the regression of ARDL(4,4) case 1, AIC (in-sample MAE 0.0317 for both). The EG > ARDL tie-break (§5.5) selects the EG label. Coefficients, backtests and ratings are unchanged.
>
> **§6.4.5:** 17 one-step ECMs (8 EG, 8 ARDL, 1 Johansen). In-sample MAE 0.0317 to 0.0453. Long-run beta 0.398 to 0.487.
>
> **§6.4.7 first bullet:** red limit 0.50 → 0.45 ("5-8Q max 0.533 > red 0.45").

### §6.6 Old National (consequential, champion change)

> **§6.6.5:** 2 one-step ECMs (1 EG, 1 Johansen). In-sample MAE 0.0285 to 0.0414. Long-run beta 0.394 to 0.419.
>
> **§6.6.6 Champion Model: Engle-Granger long run, trend `n`, BIC (ADF lag=1, ECM lag=3).** EG ADF t −3.43 (p 0.008). Short-run candidates come from the Engle-Granger second-step regression (OI-24). The Johansen VECM (det_order −1, k_ar_diff 1), the champion before OI-24, now has the higher in-sample MAE (0.0414).
>
> | Term | Coefficient | *t* | p-value |
> | :--- | :-: | :-: | :-: |
> | y.L1 (λ) | **-0.0856** | -2.67 | 0.010 |
> | FFT.L1 | 0.0337 | 2.51 | 0.015 |
> | D.y.L1 | 0.7163 | 6.65 | 2.1e-08 |
> | D.y.L2 | -0.7376 | -5.73 | 5.8e-07 |
> | D.y.L3 | 0.4607 | 5.05 | 6.3e-06 |
> | D.FFT.L0 | 0.1388 | 5.99 | 2.3e-07 |
> | D.FFT.L1 | -0.0956 | -2.68 | 0.0099 |
> | D.FFT.L2 | 0.1374 | 4.13 | 1.4e-04 |
> | **LR: FFT (θ)** | **0.3937** | 11.11 | 4.1e-15 |
>
> **§6.6.7:**
> - **Governing rating (many-start-date backtest, §5.6): Green.** h-step MAE, 1Q to 8Q, over 34 to 41 start dates: 0.047, 0.117, 0.179, 0.225, 0.286, 0.349, 0.382, 0.405 (mean 0.249; Johansen champion 0.263). Worst skill ratio against the no-change forecast: 0.65 at 6Q.
> - Single-window 8Q backtest (supplementary): 0.005, 0.082, 0.067, 0.048, 0.363, 0.213, 0.271, 0.149; mean 0.150, no-change mean 0.207, beats no-change on 7/8 horizons (Green).
> - The large single-window error at 5Q (start date 2025Q1, 0.363) is unchanged and remains the shared easing-cycle effect (OI-8).
> - **Long-run beta stability (§5.6):** re-estimated at the eight origins 2024Q2 to 2026Q1, θ ranges from 0.300 to 0.493 against the full-sample 0.394. The largest deviation is 0.099 (25%) at 2024Q3, 0.91 origin standard errors (largest in SEs: 1.24 at 2025Q1). The estimates dip to 0.329 and 0.300 at the 2024Q4 and 2025Q1 origins, then return to 0.38–0.40.

### §7.1 Many-Start-Date Backtest

> Start dates every quarter from 2016Q1, expanding estimation window, dynamic forecasts with realized FFT. Each h-step figure averages 34 (8Q) to 41 (1Q) start dates.
>
> | Bank | 1Q | 2Q | 3Q | 4Q | 5Q | 6Q | 7Q | 8Q | Mean | No-change mean | Worst skill ratio | Rating |
> | :--- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
> | First Horizon Bank | 0.100 | 0.179 | 0.227 | 0.239 | 0.283 | 0.308 | 0.312 | 0.292 | 0.242 | 0.539 | 0.71 | **Red** |
> | Glacier Bank | 0.047 | 0.103 | 0.156 | 0.195 | 0.238 | 0.277 | 0.306 | 0.331 | 0.207 | 0.235 | 0.96 | **Amber** |
> | Huntington National Bank | 0.042 | 0.097 | 0.148 | 0.199 | 0.255 | 0.307 | 0.339 | 0.381 | 0.221 | 0.467 | 0.49 | **Green** |
> | KeyBank National Association | 0.054 | 0.115 | 0.172 | 0.224 | 0.294 | 0.384 | 0.464 | 0.533 | 0.280 | 0.448 | 0.71 | **Red** |
> | Manufacturers and Traders Trust Company | 0.059 | 0.117 | 0.170 | 0.211 | 0.261 | 0.290 | 0.304 | 0.329 | 0.218 | 0.394 | 0.62 | **Green** |
> | Old National Bank | 0.047 | 0.117 | 0.179 | 0.225 | 0.286 | 0.349 | 0.382 | 0.405 | 0.249 | 0.404 | 0.65 | **Green** |
> | SouthState Bank | 0.061 | 0.134 | 0.202 | 0.262 | 0.312 | 0.355 | 0.384 | 0.406 | 0.264 | 0.413 | 0.70 | **Green** |
>
> Band limits for N = 8, derived from this run (§5.6):
>
> | Band | Green limit (band average) | Red limit (band maximum) |
> | :-: | :-: | :-: |
> | 1-2Q | 0.10 | 0.15 |
> | 3-4Q | 0.25 | 0.30 |
> | 5-8Q | 0.40 | 0.45 |
>
> First Horizon is Red on the 1–2Q band (2Q 0.179 > red 0.15), and KeyBank on the 5–8Q band (8Q 0.533 > red 0.45). First Horizon's errors are unchanged from the previous run, where the 1–2Q limits were 0.15/0.20 and it was Green. The limits tightened because the re-specified Huntington and Old National champions have lower short-horizon errors (OI-24). This is the peer-relative effect noted in §5.6.

**Also needed when folding in** (same numbers, no new text required): §7.2 rows for Huntington (0.094, 0.132, 0.069, 0.049, 0.187, 0.287, 0.169, 0.214; mean 0.150; no-change 0.231; Amber) and Old National (0.005, 0.082, 0.067, 0.048, 0.363, 0.213, 0.271, 0.149; mean 0.150; no-change 0.207; Green). §7.3 ratings bullet: First Horizon and KeyBank Red; Huntington, M&T, Old National and SouthState Green; Glacier Amber. §7.5 rows: Huntington 0.463 / 0.449 / 0.352 to 0.553 / 0.110 (24%) / 2024Q4 / 1.22; Old National 0.394 / 0.390 / 0.300 to 0.493 / 0.099 (25%) / 2024Q3 / 0.91. In the §7.5 bullets, drop "Huntington is the only bank whose estimate drifts in one direction…" (no bank now has an origin more than two SEs out), and give Huntington's level as about 0.45.

### §8 Model Limitations: row replaced

| # | Limitation | Affected banks | Impact |
| :-: | :--- | :--- | :--- |
| L15 | Huntington cointegration rests on one specification family (EG long run, no deterministic terms) and on post-2022 data: the test fails in every window ending in 2019Q4 and in 2021Q4 windows starting in 2013 or later. GH finds no break. Kept in scope with this caveat (decision 2026-10-31). The re-specified champion (short-run terms added, OI-24) is Green, but its λ is small (−0.066) and its θ ranges from 0.352 to 0.553 across origins (OI-19) | Huntington | High |

### §9.2 Open Issues Log: rows replaced

| ID | Issue | Bank(s) | Priority | Status |
| :-: | :--- | :--- | :-: | :--- |
| OI-19 | Huntington cointegration rests on a single specification family; assess robustness and whether Huntington stays in scope | Huntington | High | Closed (decision 2026-10-31): kept in scope with a caveat (one specification family; post-2022 identification; L15). The champion is re-specified through OI-24 (D.y L1–3, D.FFT L0–2) and rates Green (mean h-step MAE 0.221 vs. 0.334). Evidence in `docs/resolutions/model_form.md` §4 and `docs/resolutions/oi24_eg_short_run.md`. ([#4](https://github.com/Panda5130/Deposit-Beta/issues/4)) |
| OI-24 | EG long-run specifications entered the one-step ECM with no short-run terms: the step-2 output carried only ADF residual lags, so D.FFT and D.y lags were never screened | Huntington, Old National, KeyBank (all EG long-run specifications) | High | Closed: `ECM model selection.py` gives each passing EG long-run spec the D.* lags of its own EG second-step regression, screened at p < 0.05 and pruned like every other family (§5.5). Champions change for Huntington (Red → Green) and Old National (Johansen → EG, Green); KeyBank's label changes (identical regression). The tighter peer 1–2Q limits turn First Horizon Red (§7.1) |

---

## 5. Notes for other threads

- **eval-selection (issues #1 and #10; owns `MAE_Backtesting/`, `Beta_Backtesting/`):**
  - The error cache (`ErrorCache.load`) is keyed on the model label, `first_origin`, data hash and horizon, not on the fitted terms. When the pipeline changes a spec's terms but not its label (Huntington here), a cached run returns stale errors. This run used `--no-cache`. A fix would add the fitted term list, or a hash of it, to the key. Not changed here, since the module belongs to that thread.
  - First Horizon flips Green → Red with no change to its own errors, purely because of the peer-derived limits. This is a concrete case for fixing the limits from a reference run (§5.6).
- **model_form:** every Huntington and Old National number in `docs/resolutions/model_form.md` §3 (challengers scored against the champion) refers to the old champions. `model_form/run_model_form.py` checks that its re-run champion matches `backtest_multiorigin_8Q.csv`, so it now needs a re-run (about 8 minutes) before its tables are folded in. Not re-run here.
- **data-projection:** the projection reads champions from the CSVs, so Huntington's and Old National's projections change with no code change. The champion selection call is unchanged.
- **OI-8 / OI-25:** both re-specified champions carry large lagged-Δy terms. That makes Huntington a fourth bank exposed to the momentum effect. Its 2025Q1 single window worsens from 0.094 to 0.187.
