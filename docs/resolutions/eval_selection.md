# RC2: out-of-sample evaluation and model selection (issues #1 and #10)

Branch `claude/eval-selection-780b4d`, 2026-10-31. Not pushed; nothing posted on GitHub and nothing written to the vault. The WIP doc is not edited; replacement text is in §5 below.

Root cause RC2: out-of-sample evaluation never fed model selection, and the two backtests were uneven. The MAE backtest used every start date from 2016Q1 with Green/Amber/Red limits. The beta backtest used the last eight start dates and had no threshold.

## 1. Summary

- **Beta backtest from 2016Q1 (#10).** `run_beta_backtest.py --first-origin 2016Q1` re-estimates θ at all 41 start dates from 2016Q1 to 2026Q1 (expanding window). It uses the same origin handling as the MAE backtest and a per-bank cache keyed on model, first origin and data hash. The overlapping start dates 2024Q2–2026Q1 reproduce the committed `beta_backtest_origins_8Q.csv` files exactly for all seven banks.
- **Beta-stability rating (#10), option C, chosen by the user on 2026-10-31.** The rating is computed over the start dates from 2020Q1. A start date fails only when θ is more than 2 standard errors **and** more than 20% away from the full-sample θ. Green: no failing start date. Amber: 1–2 failing, none beyond 3 standard errors. Red: 3 or more failing, or any start date beyond 3 standard errors and 20%.
  - Champions: First Horizon, KeyBank and SouthState **Green**; Huntington and Old National **Amber**; Glacier and M&T **Red**.
- **Optional out-of-sample champion rule (#1).** `run_backtest.py --select out-of-sample` (and the same flag on `run_beta_backtest.py`) works as follows:
  - keeps admissible models only (λ in (−1, 0), θ in [0, 1]);
  - ranks them by mean many-start-date h-step MAE (1–8Q, start dates from 2016Q1);
  - picks the most parsimonious model within one standard error of the best.
  - The default is still the in-sample `select_model`; every existing champion and output is unchanged.
- **Outcome of the out-of-sample rule:** it changes the model for 6 of 7 banks (Huntington is unchanged), with mixed effects:
  - KeyBank improves on both tests (MAE Red → Green, beta stays Green).
  - M&T improves on beta (Red → Green).
  - SouthState gains on MAE (0.264 → 0.197) but its beta turns Red.
  - Glacier gets worse (MAE Amber → Red).
  - First Horizon and Old National give up some accuracy for fewer parameters.
  - This supports keeping the switch with the validator, as decided.

## 2. What was built

| File | Change |
| :--- | :--- |
| `MAE_Backtesting/backtest.py` | Changes: <ul><li>`MAEBacktest.origins()`: shared origin handling.</li><li>`ErrorCache` split into `read`/`write`, plus a `per_model` mode (one file per bank and model).</li><li>`model_terms`, `hac_se`, `oos_scores`, `select_model_oos`.</li></ul> `select_model` is unchanged. |
| `MAE_Backtesting/run_backtest.py` | `--select in-sample\|out-of-sample` (default in-sample). The out-of-sample mode: <ul><li>writes to `MAE_Backtesting/output/out_of_sample/`;</li><li>defaults `--first-origin` to 2016Q1;</li><li>adds `selection_oos_scores_8Q.csv` (every model's λ, θ, admissibility, score, SE, one-SE threshold and pick).</li></ul> |
| `MAE_Backtesting/compare_selection.py` | New script. Writes `output/out_of_sample/selection_comparison_8Q.csv` and `.png`: the in-sample champion against the out-of-sample pick. Stops if any input run used a different model. |
| `Beta_Backtesting/beta_backtest.py` | Adds: <ul><li>`origin_betas(first_origin)`;</li><li>`deviations()`: deviation in pp, share and origin SEs;</li><li>`assess_multi()`: option C;</li><li>`BetaCache`;</li><li>θ-by-start-date charts, one per bank and a small-multiples chart of all banks.</li></ul> |
| `Beta_Backtesting/run_beta_backtest.py` | `--first-origin`, `--no-cache` and `--select`. The default run is unchanged. |

New outputs:

| Path | Content |
| :--- | :--- |
| `Beta_Backtesting/output/<bank>/beta_backtest_multiorigin.csv` / `.png` | θ, SE, λ at each start date 2016Q1–2026Q1, with its deviation from the full-sample θ; chart with ±2 SE, ±20% band, unrated window shaded, rating |
| `Beta_Backtesting/output/beta_backtest_multiorigin_all_banks.csv` / `.png` | All banks; small multiples |
| `Beta_Backtesting/output/beta_backtest_multiorigin_assessment.csv` | Per-bank rating (rated window, θ range, largest deviation as a share and in SEs, failing start dates, reason) |
| `Beta_Backtesting/output/cache/` | Per-origin θ, reused while model, fitted terms, first origin and data match |
| `MAE_Backtesting/output/out_of_sample/` | The full MAE backtest of the out-of-sample picks (same layout as `output/`), `selection_oos_scores_8Q.csv`, `selection_comparison_8Q.csv` / `.png`, per-model error cache |
| `Beta_Backtesting/output/out_of_sample/` | The beta backtest of the out-of-sample picks, including its assessment |

Commands (from the project folder):

```bash
python MAE_Backtesting/run_backtest.py --horizon 8Q --bank-name All --first-origin 2016Q1
python Beta_Backtesting/run_beta_backtest.py --first-origin 2016Q1
python MAE_Backtesting/run_backtest.py --horizon 8Q --bank-name All --select out-of-sample
python Beta_Backtesting/run_beta_backtest.py --first-origin 2016Q1 --select out-of-sample
python MAE_Backtesting/compare_selection.py
```

The first out-of-sample run refits every distinct admissible ECM at 41 start dates. It took about 4 minutes; later runs read the cache.

## 3. Results

### 3.1 Long-run beta from 2016Q1, champions (option C)

41 start dates from 2016Q1 to 2026Q1; rated over the 25 start dates from 2020Q1.

| Bank | Full-sample θ | θ range, 2020Q1–2026Q1 | Largest deviation (share), start date | Largest deviation in SEs, start date | Failing start dates (>2 SE and >20%) | Rating |
| :--- | :-: | :-: | :-: | :-: | :--- | :-: |
| First Horizon Bank | 0.517 | 0.437 to 0.596 | 15%, 2023Q3 | 1.57, 2023Q4 | none | **Green** |
| Glacier Bank | 0.346 | 0.110 to 0.383 | 68%, 2020Q1 | 11.37, 2022Q4 | 14: 2020Q1–2023Q1 and 2023Q4 (13 beyond 3 SE) | **Red** |
| Huntington National Bank | 0.469 | 0.410 to 0.599 | 28%, 2023Q3 | 2.08, 2023Q4 | 2: 2023Q4, 2024Q1 | **Amber** |
| KeyBank National Association | 0.398 | 0.275 to 0.532 | 34%, 2024Q3 | 1.29, 2022Q3 | none | **Green** |
| Manufacturers and Traders Trust Company | 0.432 | 0.290 to 1.285 | 198%, 2023Q4 | 3.06, 2022Q3 | 3: 2020Q1, 2022Q3, 2022Q4 (2022Q3 beyond 3 SE) | **Red** |
| Old National Bank | 0.419 | −0.295 to 0.491 | 170%, 2020Q2 | 2.28, 2020Q1 | 1: 2020Q1 | **Amber** |
| SouthState Bank | 0.443 | −0.009 to 0.524 | 102%, 2020Q2 | 1.27, 2025Q1 | none | **Green** |

Observations:
- **Before 2020, θ is poorly identified.** Samples ending 2016Q1–2019Q4 are mostly 2011–2015 zero-lower-bound data, and FFT varies little. θ at those start dates ranges from −1.12 (Glacier, 2016Q1) to 2.50 (SouthState, 2016Q1), with wide standard errors. They are charted but not rated.
- **Glacier is the clearest instability.** θ sits at 0.11–0.14 at every start date from 2020Q1 to 2023Q1, with tight standard errors (0.02–0.04). It reaches the full-sample 0.35 only after the 2022–23 hiking cycle enters the sample. The estimate is almost entirely driven by the last cycle.
- **M&T:**
  - It fails at 2020Q1 (0.321) and at 2022Q3–Q4 (0.29–0.30, about 3 SE below).
  - At 2023Q3–Q4, λ is near zero (−0.03, −0.02), so θ is unidentified (1.14 and 1.29, SE 2.3). Those start dates exceed 20% but not 2 SE, so the joint rule does not count them.
- **Huntington:** θ is flat at 0.41 from 2020Q3 to 2022Q1, rises to 0.60 at 2023Q3, then falls steadily to 0.465. The 2023Q4 and 2024Q1 start dates are just over 2 SE (2.08, 2.03). This is the same one-way drift seen in the 8-start-date run, now placed in the full cycle.
- **Old National:** θ is 0.24 at every start date from 2020Q3 to 2022Q2. That is 43% below the full-sample 0.42, but only about 1.5 SE, because λ is small (−0.07) and the SEs are wide. Only 2020Q1 (0.309, 2.28 SE) fails. This is the case where the joint rule is most lenient (see §6).
- **First Horizon, KeyBank and SouthState:**
  - First Horizon stays within 16% and 1.6 SE throughout.
  - KeyBank's 34% swing at 2024Q3 and SouthState's near-zero θ at 2020Q2 (λ −0.02, SE 0.93) are imprecise single start dates, so they do not fail.
- The 8-start-date figures in the current §7.5 are unchanged; the default run still produces them.

### 3.2 Rating options considered (2016Q1 run, champions)

Shown to the user on 2026-10-31; the user chose C.

| Bank | A: example rule, all 41 start dates | B: example rule, start dates from 2020Q1 | C: joint rule, start dates from 2020Q1 (chosen) |
| :--- | :-: | :-: | :-: |
| First Horizon Bank | Red | Green | Green |
| Glacier Bank | Red | Red | Red |
| Huntington National Bank | Red | Red | Amber |
| KeyBank National Association | Red | Amber | Green |
| Manufacturers and Traders Trust Company | Red | Red | Red |
| Old National Bank | Red | Red | Amber |
| SouthState Bank | Red | Amber | Green |

How the options differ:
- **Example rule:** Green if every start date is within 2 SE and within 20%; Amber if one of those is broken; Red if both are broken, or any start date is beyond 3 SE.
- **Option A** gives all Red, because the pre-2020 fits are unidentified.
- **Option B** penalises imprecise single start dates through the 20% test, for example M&T 2023Q3 and SouthState 2020Q2.

### 3.3 Out-of-sample champion rule (#1)

**Admissibility.** All 78 models in `estimation result summary.csv` are admissible (λ in (−1, 0), θ in [0, 1]). Many specifications are the same ECM (same terms), and each distinct ECM is scored once.

**Score and standard error:**
- The score is the mean over h = 1..8 of the many-start-date h-step MAE (the "Mean" column of §7.1).
- The standard error is the Newey-West (Bartlett, 7 lags) standard error of the mean per-start-date loss, taken over the 34 start dates with all eight steps. The forecast windows overlap, so a plain standard error would be too small.

**Pick.** Among models with score ≤ best + standard error of the best, the rule picks the fewest parameters, then the lowest score, then EG > ARDL > Johansen, then file order.

| Bank | Model | Params | In-sample MAE | Many-start-date mean MAE (SE) | θ | MAE rating | Beta rating |
| :--- | :--- | :-: | :-: | :-: | :-: | :-: | :-: |
| First Horizon Bank | Champion: ARDL(3,4), case 4, AIC | 9 | 0.0469 | 0.242 (0.039) | 0.517 | Green | Green |
| | Pick: Johansen VECM, k_ar_diff = 1, det_order −1, BIC | 3 | 0.0720 | 0.284 (0.059) | 0.477 | Green | Green |
| Glacier Bank | Champion: ARDL(3,1), case 4, BIC | 7 | 0.0292 | 0.207 (0.079) | 0.346 | Amber | Red |
| | Pick: Johansen VECM, k_ar_diff = 1, det_order 1, BIC | 5 | 0.0310 | 0.263 (0.087) | 0.277 | Red | Red |
| Huntington National Bank | Champion = pick: EG long run, `n`, AIC | 2 | 0.0709 | 0.334 (0.071) | 0.469 | Red | Amber |
| KeyBank National Association | Champion: ARDL(4,4), case 1, AIC | 7 | 0.0317 | 0.280 (0.062) | 0.398 | Red | Green |
| | Pick: ARDL(2,1), case 1, BIC | 4 | 0.0343 | 0.189 (0.041) | 0.412 | Green | Green |
| Manufacturers and Traders Trust Company | Champion: ARDL(2,1), case 4, AIC | 6 | 0.0383 | 0.218 (0.068) | 0.432 | Green | Red |
| | Pick: ARDL(2,1), case 1, BIC | 4 | 0.0386 | 0.225 (0.041) | 0.373 | Green | Green |
| Old National Bank | Champion: Johansen VECM, k_ar_diff = 1, det_order −1, fixed | 4 | 0.0414 | 0.263 (0.065) | 0.419 | Green | Amber |
| | Pick: EG long run, `n`, BIC | 2 | 0.0585 | 0.274 (0.071) | 0.429 | Green | Amber |
| SouthState Bank | Champion: ARDL(4,3), case 1, AIC | 8 | 0.0336 | 0.264 (0.039) | 0.443 | Green | Green |
| | Pick: ARDL(3,2), case 4, BIC | 8 | 0.0347 | 0.197 (0.039) | 0.524 | Green | Red |

Source: `MAE_Backtesting/output/out_of_sample/selection_comparison_8Q.csv` (chart: `selection_comparison_8Q.png`).

How the ratings are computed:
- MAE ratings follow §5.6. The picks' band limits come from the picks' own peer group: the 5–8Q red limit is 0.45, against 0.50 for the champions.
- Beta ratings use option C.

Sensitivity without the parsimony step (lowest score):
- **The champion itself scores best** for Glacier, Huntington, M&T and Old National.
- **SouthState and KeyBank:** the best-scoring model is the pick.
- **First Horizon:** the best-scoring model is ARDL(4,2), case 4, BIC (8 parameters, 0.237, θ 0.527).

So the in-sample champion is also the out-of-sample best for 4 of 7 banks. The parsimony step is what moves First Horizon, Glacier, M&T and Old National.

Observations:
- **The one-SE band is wide.** Standard errors of 0.04–0.08 against scores of 0.19–0.33 mean the band holds several models for most banks, so the rule leans heavily on parsimony. For Glacier it picks a model 27% worse on the point score that fails the skill test (ratio 1.19 at 5Q).
- **The pick changes θ materially for four banks:**

  | Bank | Champion θ | Pick θ |
  | :--- | :-: | :-: |
  | First Horizon | 0.517 | 0.477 |
  | Glacier | 0.346 | 0.277 |
  | M&T | 0.432 | 0.373 |
  | SouthState | 0.443 | 0.524 |

  This matters for projection.
- **SouthState's pick has a restricted trend (case 4).** Adopting it would add SouthState to L14 (trend frozen in projection).
- **Selection bias.** Choosing on the many-start-date backtest uses the same errors that the governing backtest reports, so the backtest of a selected model is optimistic. A held-out window, or a nested selection inside each start date, would be needed for an unbiased figure.

## 4. Verification

- **MAE backtest.** `python MAE_Backtesting/run_backtest.py --horizon 8Q --bank-name All --first-origin 2016Q1` reused every bank's cache. It gives the §7.1 ratings (First Horizon, M&T, Old National, SouthState Green; Glacier Amber; Huntington, KeyBank Red), and every committed file under `MAE_Backtesting/output/` (CSV and PNG) is byte-identical (`git status` clean).
- **Default beta backtest.** `python Beta_Backtesting/run_beta_backtest.py` leaves every committed file under `Beta_Backtesting/output/` byte-identical.
- **Overlap check.** With `--first-origin 2016Q1`, the start dates 2024Q2–2026Q1 equal the committed `beta_backtest_origins_8Q.csv` for all seven banks (`DataFrame.equals`, max difference 0).
- **Cache.** The second run of each command reports "reused from cache".
- **Cache key now includes the fitted terms** (added after the OI-24 thread flagged the gap).
  - Every cache (`ErrorCache`, the per-model cache, `BetaCache`) is keyed on model label, first origin, data hash and `spec`: the sorted fitted terms.
  - Before this, a model that kept its label but changed terms (Huntington under OI-24) would silently reuse stale errors.
  - Cache files written before the change have no `spec` column and are treated as stale. All caches were rebuilt once:
    - Every in-sample result CSV and chart came out byte-identical.
    - The out-of-sample outputs differ only in the last one or two of 16 significant digits, from re-reading cached values. Models, ratings and every reported figure are unchanged.

### 4.1 Interaction with OI-24 (branch `claude/pensive-nightingale-b5db07`, not merged here)

OI-24 gives `EG_LongRun` specifications their `EG_ShortRun` lags in `ECM model selection.py`. That changes the estimates the backtests read, and every result in §3 is for the estimates on `main`. If OI-24 is merged, it changes champions:

| Bank | Change under OI-24 | MAE rating (mean MAE) |
| :--- | :--- | :-: |
| Huntington | Same label, new terms | Red → Green (0.334 → 0.221) |
| Old National | Johansen VECM → EG long run, `n`, BIC | |
| KeyBank | Moves to an EG label for the identical regression (EG > ARDL tie-break) | |

After a merge, rerun the five commands in §2. The spec-keyed caches recompute only what changed. Then refresh §3.1–§3.3, the Huntington, Old National and KeyBank bullets in §5, and the draft comments.

The OI-24 run also tightens the peer-derived MAE limits, and First Horizon goes Green → Red with unchanged errors. That is evidence for fixed reference-run limits (#8, on hold), not addressed here.

## 5. Replacement text for the WIP doc

### §5.5 Model and Parameter Selection, step 5 (replace) and new step 6

5. **Champion choice:** lowest in-sample MAE of Δy per bank. Ties are broken EG > ARDL > Johansen, then file order. This is the default and the basis of every result in this document.
6. **Optional out-of-sample rule (OI-9, not adopted; deferred to the validator):** `run_backtest.py --select out-of-sample`.
   - **Admissibility:** keep models with λ in (−1, 0) and θ in [0, 1].
   - **Ranking:** by mean many-start-date h-step MAE (h = 1..N, start dates from 2016Q1, §5.6).
   - **Pick:** the model with the fewest parameters among those within one standard error of the best. The standard error is Newey-West with N−1 lags over the start dates with all N steps.
   - **Effect on 2026Q2 data:** the rule changes the model for six of seven banks (§7.6).

### §5.6 Performance Testing: replace the "Parameter stability test" paragraph

**Parameter stability test: long-run beta from 2016Q1.**
- **Method:** at every start date from 2016Q1 to T−1 (41 at T = 2026Q2), the champion is re-estimated on data up to that start date (expanding window, the same fit and start dates as the many-start-date backtest). θ = −β(FFT.L1)/λ, its delta-method standard error and λ are recorded.
- **Deviation:** each start date's deviation from the full-sample θ is reported in pp, as a share of θ and in origin standard errors.
- **Rating:** on the start dates from 2020Q1. Earlier samples are mostly at the zero lower bound, where θ is weakly identified; they are charted but not rated.
  - A start date fails if its θ is more than 2 origin standard errors **and** more than 20% away from the full-sample θ.
  - Green: no failing start date.
  - Amber: one or two failing start dates, none more than 3 standard errors and 20% away.
  - Red: three or more failing start dates, or any start date more than 3 standard errors and 20% away.
- **Rationale for the joint test:** it counts only deviations that are both statistically and economically large. A large move with a wide standard error (λ near zero) is treated as imprecision, not instability.
- **Supplementary view:** the 8-start-date view (start dates T−8 to T−1, mean θ per horizon) is kept as a supplementary chart.
- **Cache:** per-start-date θ is cached (`Beta_Backtesting/output/cache/`).

### §6.x.7 beta bullet (replace in each bank)

- **6.1.7 First Horizon:** **Long-run beta stability (§5.6): Green.**
  - From 2020Q1 to 2026Q1, θ ranges from 0.437 to 0.596 against the full-sample 0.517.
  - The largest deviation is 15% (2023Q3) and at most 1.57 origin standard errors (2023Q4). No start date fails.
  - Over the last eight start dates the range is 0.494–0.542. It is the most stable beta in the peer set.
- **6.2.7 Glacier:** **Long-run beta stability (§5.6): Red.**
  - θ is 0.11–0.14 at every start date from 2020Q1 to 2023Q1, with standard errors of 0.02–0.04. That is 60–68% and 6–11 standard errors below the full-sample 0.346; 14 of 25 rated start dates fail, 13 beyond 3 standard errors.
  - It reaches 0.29–0.38 only once the 2022–23 hiking cycle is in the sample, so the long-run beta is identified almost entirely by the last cycle.
  - Over the last eight start dates it is stable (0.294–0.383, within one standard error).
- **6.3.7 Huntington:** **Long-run beta stability (§5.6): Amber.**
  - θ is flat at 0.41 from 2020Q3 to 2022Q1, rises to 0.60 at 2023Q3, then falls steadily to 0.465 at 2026Q1.
  - Two start dates fail: 2023Q4 (0.588, 2.08 SE, 25%) and 2024Q1 (0.564, 2.03 SE, 20%).
  - The one-way drift adds to the robustness concern in OI-19.
- **6.4.7 KeyBank:** **Long-run beta stability (§5.6): Green.**
  - From 2020Q1, θ ranges from 0.275 to 0.532 against the full-sample 0.398.
  - The largest deviations are 31% at 2022Q3 and 34% at 2024Q3. Both are within 1.3 origin standard errors, because λ is small (about −0.05) and the estimates are imprecise.
- **6.5.7 M&T:** **Long-run beta stability (§5.6): Red.**
  - Three start dates fail: 2020Q1 (0.321, 2.96 SE), 2022Q3 (0.290, 3.06 SE, 33%) and 2022Q4 (0.300, 2.95 SE).
  - At 2023Q3–Q4, λ is about −0.02 and θ is unidentified (1.14 and 1.29, standard error 2.3). Those start dates are not counted.
  - From 2024Q3, θ is 0.37–0.43.
- **6.6.7 Old National:** **Long-run beta stability (§5.6): Amber.**
  - θ is 0.24 at every start date from 2020Q3 to 2022Q2, about 43% below the full-sample 0.419, but only 1.4–1.6 standard errors, because λ is small (−0.07).
  - Only 2020Q1 (0.309, 2.28 SE, 26%) fails. θ returns to 0.34–0.49 from 2023Q3.
- **6.7.7 SouthState:** **Long-run beta stability (§5.6): Green.**
  - From 2020Q1, θ ranges from −0.01 to 0.52 against the full-sample 0.443.
  - The low values at 2020Q2–Q3 (λ −0.02 to −0.04, standard error up to 0.93) and the 2025Q1 dip (0.330, 1.27 SE) are imprecise rather than significant. No start date fails.

### §7.5 Long-Run Beta Stability (replace)

**7.5 Long-Run Beta Stability (start dates from 2016Q1)**

Each champion is re-estimated at every start date from 2016Q1 to 2026Q1 (expanding window), and θ is compared with the full-sample estimate through 2026Q2 (`Beta_Backtesting/run_beta_backtest.py --first-origin 2016Q1`). Ratings use the start dates from 2020Q1 (§5.6).

| Bank | Full-sample θ | θ range, 2020Q1–2026Q1 | Largest deviation (share), start date | Largest deviation in SEs, start date | Failing start dates | Rating |
| :--- | :-: | :-: | :-: | :-: | :-: | :-: |
| First Horizon Bank | 0.517 | 0.437 to 0.596 | 15%, 2023Q3 | 1.57, 2023Q4 | 0 | **Green** |
| Glacier Bank | 0.346 | 0.110 to 0.383 | 68%, 2020Q1 | 11.37, 2022Q4 | 14 | **Red** |
| Huntington National Bank | 0.469 | 0.410 to 0.599 | 28%, 2023Q3 | 2.08, 2023Q4 | 2 | **Amber** |
| KeyBank National Association | 0.398 | 0.275 to 0.532 | 34%, 2024Q3 | 1.29, 2022Q3 | 0 | **Green** |
| Manufacturers and Traders Trust Company | 0.432 | 0.290 to 1.285 | 198%, 2023Q4 | 3.06, 2022Q3 | 3 | **Red** |
| Old National Bank | 0.419 | −0.295 to 0.491 | 170%, 2020Q2 | 2.28, 2020Q1 | 1 | **Amber** |
| SouthState Bank | 0.443 | −0.009 to 0.524 | 102%, 2020Q2 | 1.27, 2025Q1 | 0 | **Green** |

![All banks: long-run beta re-estimated at every start date](<Beta_Backtesting/output/beta_backtest_multiorigin_all_banks.png>)

*Figure 23: Long-run beta θ re-estimated at every start date from 2016Q1, all banks, with ±2 origin standard errors, the full-sample θ ±20%, and the unrated window before 2020Q1 shaded.*

(Copy the figure to `docs/figures/` with the other figures when the doc is edited.)

- Before 2020, θ is poorly identified for every bank: −1.12 to 2.50, with wide standard errors. Those samples are mostly zero-lower-bound data.
- Glacier's beta is the least stable: 0.11–0.14 with tight standard errors until the 2022–23 hiking cycle enters the sample.
- M&T fails at 2020Q1 and 2022Q3–Q4. Huntington drifts up to 0.60 and back. Old National sits at 0.24 through 2020–2022, which is large but imprecise.
- Over the last eight start dates (2024Q2–2026Q1), the earlier supplementary view still holds:
  - First Horizon (5%) and Glacier (15%) are the most stable.
  - KeyBank (34%) and SouthState (25%) move most, both within 1.3 standard errors.
  - Most banks dip at the 2024Q4 and 2025Q1 start dates (OI-8). The 8-start-date charts are in `Beta_Backtesting/output/<bank>/beta_backtest_8Q.png`.

**New §7.6 Out-of-sample model choice (optional rule, not adopted)**

Insert the champion vs pick table from §3.3 of this note, followed by these bullets:

- The rule (§5.5 step 6) changes the model for six of seven banks; Huntington is unchanged.
- For four banks (Glacier, Huntington, M&T and Old National), the in-sample champion is also the best on the many-start-date MAE. The change comes from the parsimony step, because the one-standard-error band is wide (0.04–0.08).
- The effects are mixed:
  - KeyBank improves on both tests.
  - M&T's beta becomes Green.
  - SouthState gains on MAE but its beta turns Red.
  - Glacier's pick fails the skill test.
- Selecting on the governing backtest makes that backtest optimistic for the selected model. Adoption is deferred to the validator (OI-9).

### §8 Model Limitations (replace L8 and L17)

| # | Limitation | Affected banks | Impact |
| :-: | :--- | :--- | :--- |
| L8 | Champion chosen on in-sample MAE, and several specifications collapse to the same ECM. An optional out-of-sample rule (§5.5 step 6) would change six of seven models with mixed effects. It is not adopted (OI-9), and selecting on the backtest would bias that backtest. | All | Medium |
| L17 | Beta stability is rated only from 2020Q1, because earlier samples are mostly zero-lower-bound data. The joint 2-SE-and-20% test does not flag large moves with wide standard errors (Old National θ about 0.24 through 2020–2022). Glacier and M&T are rated Red. | All, esp. Glacier, M&T | Medium |

### §9.2 Open Issues Log (replace OI-9 and OI-23 rows)

| ID | Issue | Bank(s) | Priority | Status |
| :-: | :--- | :--- | :-: | :--- |
| OI-9 | Select the champion on out-of-sample backtest MAE (or a combination), not in-sample MAE | All | Medium | Partially closed: optional rule implemented (`run_backtest.py --select out-of-sample`; admissible λ and θ, many-start-date MAE, one-standard-error parsimony) with a side-by-side comparison (§7.6). In-sample MAE retained as the default; adoption deferred to the validator ([#1](https://github.com/Panda5130/Deposit-Beta/issues/1)) |
| OI-23 | Set an acceptance threshold for long-run beta stability and extend the start dates back to 2016Q1 | All | Medium | Closed: start dates from 2016Q1; rating on start dates from 2020Q1 (fail = >2 SE and >20%; Amber 1–2, Red 3+ or any >3 SE). Glacier and M&T Red, Huntington and Old National Amber. The validator should confirm the threshold ([#10](https://github.com/Panda5130/Deposit-Beta/issues/10)) |

## 6. Questions for the validator

1. **One-standard-error rule.** Is the standard error of the best model the right width? A paired standard error of each model's loss difference from the best would be much tighter, because the models' errors are highly correlated. It would move the picks toward the best-scoring model.
2. **Lenient case in the joint test.** Should the joint beta test also flag sustained deviations, for example 4 or more consecutive start dates beyond 20%? That would catch Old National's 2020–2022 level of about 0.24, which no single start date flags.
3. **Rated window.** Is 2020Q1 the right start for the rated window? An alternative is an identification screen, for example rating only start dates with origin SE below 0.15.
4. **Unbiased evaluation.** Should out-of-sample selection be nested, or scored on a held-out window, so that the reported backtest of the selected model is not optimistic?

## 7. Draft GitHub comments (not posted)

### Issue #1 (OI-9)

> Implemented as an **optional** rule on branch `claude/eval-selection-780b4d`; the default is unchanged (in-sample `select_model`).
>
> **Rule:** `python MAE_Backtesting/run_backtest.py --select out-of-sample`
> 1. Admissible: λ in (−1, 0), θ in [0, 1] (all 78 current models pass).
> 2. Ranking: mean many-start-date h-step MAE, h = 1..8, start dates from 2016Q1. Each distinct ECM is scored once and its errors cached.
> 3. Pick: fewest parameters within one standard error of the best. The standard error is Newey-West with 7 lags, over the 34 start dates with all eight steps.
>
> **Result** (`MAE_Backtesting/output/out_of_sample/selection_comparison_8Q.csv`): the pick differs from the champion for 6 of 7 banks (Huntington unchanged).
> - KeyBank: ARDL(4,4) → ARDL(2,1) case 1. MAE 0.280 → 0.189; MAE rating Red → Green; beta Green.
> - M&T: case 4 → case 1, θ 0.432 → 0.373. Beta rating Red → Green.
> - SouthState: ARDL(4,3) case 1 → ARDL(3,2) case 4. MAE 0.264 → 0.197, but beta rating Green → Red.
> - Glacier: ARDL(3,1) case 4 → Johansen det_order 1. MAE 0.207 → 0.263; MAE rating Amber → Red (skill ratio 1.19).
> - First Horizon and Old National: sparser models with slightly higher MAE; ratings unchanged.
>
> For 4 of 7 banks the champion is also the best-scoring model; the changes come from the parsimony step. The one-standard-error band is wide (0.04–0.08).
>
> **Open for the validator:**
> - whether the one-standard-error width should be a paired standard error;
> - whether selection should be nested or held out, so the reported backtest is not optimistic.
>
> Steps 1 and 2 of the proposed scheme (AIC/BIC lag choice, LM and CUSUM screens) are not part of this change. Leaving open until the validator decides.

### Issue #10 (OI-23)

> Done on branch `claude/eval-selection-780b4d`.
>
> **Start dates from 2016Q1.** `python Beta_Backtesting/run_beta_backtest.py --first-origin 2016Q1` re-estimates θ at all 41 start dates from 2016Q1 to 2026Q1, using the MAE backtest's origin handling and a cache keyed like `ErrorCache`. The 2024Q2–2026Q1 start dates reproduce the existing 8-start-date files exactly.
>
> **Threshold** (agreed 2026-10-31), applied to start dates from 2020Q1. Earlier fits are mostly zero-lower-bound data and give θ from −1.1 to 2.5; they are charted but not rated.
> - A start date fails if it is more than 2 origin SE **and** more than 20% from the full-sample θ.
> - Green: none fail. Amber: 1–2 fail, none beyond 3 SE. Red: 3 or more fail, or any beyond 3 SE and 20%.
>
> **Ratings** (`Beta_Backtesting/output/beta_backtest_multiorigin_assessment.csv`):
>
> | Bank | Rating | Reason |
> | :--- | :-: | :--- |
> | First Horizon | Green | |
> | KeyBank | Green | |
> | SouthState | Green | |
> | Huntington | Amber | 2023Q4, 2024Q1 at about 2.0 SE |
> | Old National | Amber | 2020Q1 at 2.28 SE |
> | M&T | Red | 2020Q1, 2022Q3 at 3.06 SE, 2022Q4 |
> | Glacier | Red | θ 0.11–0.14 with tight standard errors at every start date to 2023Q1, up to 11 SE below 0.346 |
>
> Charts: `Beta_Backtesting/output/<bank>/beta_backtest_multiorigin.png` and `beta_backtest_multiorigin_all_banks.png`.
>
> Replacement text for §5.6, §6.x.7, §7.5, L17 and OI-23 is in `docs/resolutions/eval_selection.md`.
>
> **Open for the validator:**
> - whether to flag sustained moves that no single start date fails (Old National about 0.24 through 2020–2022);
> - whether the rated window should start at 2020Q1.
