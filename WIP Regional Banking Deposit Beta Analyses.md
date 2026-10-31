# WIP Regional Banking Deposit Beta Analyses

> **STATUS: WORK IN PROGRESS. NOT VALIDATED. NOT APPROVED FOR PRODUCTION USE.**
> This document describes a banking-group analysis that is still in development. Its results, specifications and conclusions are provisional and may change. It has not been through independent model validation under SR 11-7 / OCC 2011-12.

---

## 0. Document Control

| Item | Detail |
| :--- | :--- |
| Document title | WIP Regional Banking Deposit Beta Analyses |
| Model family | Regional bank deposit-rate error-correction models (deposit beta) |
| Model type | Single-equation, one-step error-correction models (ECM) selected from Engle-Granger, Johansen VECM and ARDL bounds-test specifications |
| Development status | Work in progress (development / exploratory) |
| Validation status | Not validated |
| Model tier / materiality | Not yet assigned |
| Developer | Shivam Panda (GitHub: Panda5130) |
| Code repository | `Panda5130/Deposit-Beta` |
| Source documentation | Obsidian vault: `Modeling/Deposit Beta/Documentation.md` |
| Code version documented | The repository commit that adds this version of the document (2026-10-30) |
| Document date | 2026-10-30 |
| Data period | 2011Q1 to 2026Q2 (main); 2008Q1 to 2026Q2 (sensitivity, Appendix A.2) |

### 0.1 Revision History

| Version | Date | Description |
| :--- | :--- | :--- |
| 0 (WIP) | 2026-10-30 | First SR 11-7 style draft, built from the vault documentation and the repository's code and outputs. Rebuilt the data on deposit interest expense only (`EDEPDOMQ` + `EDEPFORQ`) over a two-point average of total deposits, with full pro forma backfill for every merger of 1% or more since 2007 using real FDIC certs. This fixed the Glacier 2012, Huntington 2021Q1 and Old National 2025Q2 anomalies. Re-ran cointegration, re-specification and estimation for all seven banks, with deterministic terms matched to each test and insignificant short-run lags pruned; new champions for every bank. Added Zivot-Andrews tests for all banks, a many-start-date backtest with horizon-aware, peer-derived limits and a no-change skill test, and per-bank figures, with many-start-date backtest bar charts (model vs. no-change, with band limits); Figure 1 regenerated from `EDA1_Stationarity_Tests.ipynb`. Removed the Key Open Issues summary; issues are tracked in §8 and §9 (OI-1 to OI-22). |
| 0.1 (WIP) | 2026-10-31 | Added the rolling-origin long-run beta stability backtest (`Beta_Backtesting/`): method (§5.6), per-bank results and figures (§6.x.7), peer comparison (§7.5), limitation L17 and OI-23. Linked the remaining open issues to GitHub issues #1 to #8. Folded in the root-cause work from PR #11: an FFT builder with complete quarters only and a projection layer with the trend freeze (§3.3, §4.1, §5.7, §10.2); Gregory-Hansen break tests and seven challenger models (§5.3, §6.x.4, §7.4); EG long-run specifications now carry their short-run lags (OI-24), which re-specifies Huntington (Red → Green), changes the Old National champion and relabels KeyBank's; the beta stability test from 2016Q1 with a rating (§5.6, §7.5); and an optional out-of-sample model choice, not adopted (§5.5, §7.6). Issues #2, #4, #5, #6, #7 and #10 closed. |

---

## 1. Executive Summary

### 1.1 Purpose
The analysis estimates the **deposit beta** of seven U.S. regional banks: the long-run share of a change in the federal funds rate that passes through to the bank's average deposit rate. It also estimates the short-run speed at which deposit rates adjust toward that long-run relationship. Each bank is modeled separately.

### 1.2 Banks in Scope

| # | Bank | FDIC Cert | Merger treatment in final dataset |
| :-: | :--- | :-: | :--- |
| 1 | First Horizon Bank | 4977 | Pro forma, 4 Mode A events since 2011 (incl. Capital Bank 2017, IBERIABANK 2020) |
| 2 | Glacier Bank | 30788 | Pro forma, 25 Mode A events since 2011 (incl. 10-charter consolidation 2012), 1 Mode B |
| 3 | Huntington National Bank | 6560 | Pro forma, 6 Mode A events since 2011 (incl. FirstMerit 2016, TCF 2021, Cadence 2026) |
| 4 | KeyBank National Association | 17534 | Pro forma, 1 Mode A event (First Niagara 2016), 1 Mode B |
| 5 | Manufacturers and Traders Trust Company | 588 | Pro forma, 2 Mode A events (Hudson City 2015, People's United 2022) |
| 6 | Old National Bank | 3832 | Pro forma, 13 Mode A events since 2011 (incl. First Midwest 2022, Bremer 2025), 1 Mode B |
| 7 | SouthState Bank | 33555 | Pro forma, 19 Mode A events since 2011 (incl. South State 2020, Atlantic Capital 2022, Independent 2025) |

### 1.3 Summary of Current Results (2011Q1 to 2026Q2, pro forma)
Every bank has at least one specification that is cointegrated with the federal funds rate at the 5% level, although for Huntington and Old National only after re-specification. The selected model for each bank is the specification with the lowest in-sample MAE (§5.5). The MAE rating is the governing many-start-date backtest rating, and the beta rating is the long-run beta stability rating from 2016Q1 (§5.6).

| Bank | Selected specification | Speed of adjustment (λ) | Long-run deposit beta (θ) | In-sample MAE (pp) | Many-start-date mean h-step MAE (pp) | MAE rating | Beta stability rating |
| :--- | :--- | :-: | :-: | :-: | :-: | :-: | :-: |
| First Horizon Bank | ARDL(3,4), case 4, AIC | -0.375 | 0.517 | 0.0469 | 0.242 | Red | Green |
| Glacier Bank | ARDL(3,1), case 4, BIC | -0.112 | 0.346 | 0.0292 | 0.207 | Amber | Red |
| Huntington National Bank | EG long run, no deterministic terms, AIC (ADF lag 1, ECM lag 3) | -0.066 | 0.463 | 0.0234 | 0.221 | Green | Green |
| KeyBank National Association | EG long run, no deterministic terms, BIC (ADF lag 1, ECM lag 3) | -0.110 | 0.398 | 0.0317 | 0.280 | Red | Green |
| Manufacturers and Traders Trust Company | ARDL(2,1), case 4, AIC | -0.184 | 0.432 | 0.0383 | 0.218 | Green | Red |
| Old National Bank | EG long run, no deterministic terms, BIC (ADF lag 1, ECM lag 3) | -0.086 | 0.394 | 0.0285 | 0.249 | Green | Green |
| SouthState Bank | ARDL(4,3), case 1, AIC | -0.082 | 0.443 | 0.0336 | 0.264 | Green | Green |

All θ estimates are significant at 1%, and all λ at 5% (at 1% except KeyBank p 0.010, Old National 0.010 and Huntington 0.016). KeyBank's EG specification is the same regression as ARDL(4,4) case 1 and is chosen on the EG > ARDL tie-break (§5.5). Long-run betas fall between 0.35 and 0.52. Six series are I(1) under the default unit-root specification; Glacier is flagged (KPSS I(0) p 0.057).

- **First Horizon** is rated Red on MAE only because the peer-derived 1–2Q red limit fell to 0.15 when the re-specified Huntington and Old National champions improved; its own errors are unchanged (§7.1).
- **Glacier and M&T** are Red on beta stability: Glacier's θ sat at 0.11–0.14 until the 2022–23 hiking cycle entered the sample, and M&T fails at three start dates (§7.5).
- Allowing a structural break (Gregory-Hansen) does not change the cointegration results, and no challenger model beats the champions across the peer group (§5.3, §7.4).

---

## 2. Model Purpose, Scope and Intended Use

### 2.1 Business Purpose
Deposit betas feed interest-rate risk measurement (NII and EVE sensitivity), deposit pricing analysis, funds-transfer pricing, and peer benchmarking. This analysis gives a peer set of regional-bank betas estimated from public regulatory data.

### 2.2 Intended Use (once validated)
- Peer benchmarking of long-run deposit pass-through.
- Scenario projection of deposit rates conditional on a federal funds rate path, over horizons of up to 8 quarters.

### 2.3 Uses Outside Scope
- Production pricing or regulatory capital decisions while the model is WIP.
- Product-level or customer-segment deposit betas: the data is bank-level deposit interest expense over total deposits.
- Forecasts beyond 8 quarters, or under rate regimes outside the 2011 to 2026 sample (for example, negative rates).

### 2.4 Model Output
For each bank: the estimated one-step ECM (short-run coefficients, speed of adjustment λ, long-run coefficients θ with delta-method standard errors), in-sample MAE, rolling-origin dynamic-forecast MAE by horizon, and the long-run beta re-estimated at rolling origins.

---

## 3. Model Overview

### 3.1 Variables

| Role | Variable | Definition | Source |
| :--- | :--- | :--- | :--- |
| Dependent (y) | `rate_pf_clean` | 400 × quarterly deposit interest expense ÷ average of current and prior quarter-end total deposits, pro forma for mergers | FDIC BankFind Suite, Financials API |
| Regressor (x) | `FFT` | Quarterly average of the monthly effective federal funds rate (%) | FRED series `FEDFUNDS` |

### 3.2 Model Form
Each final model is a one-step ECM, fitted by OLS in linear form:

$$\Delta y_t = \lambda\,(y_{t-1} - c - \theta x_{t-1}) + \sum_i \gamma_i \Delta x_{t-i} + \sum_j \phi_j \Delta y_{t-j} + \varepsilon_t$$

- **λ (speed of adjustment)** is the coefficient on $y_{t-1}$. It must be negative for the model to error-correct.
- **θ (long-run deposit beta)** is recovered as $-\beta_{x_{t-1}}/\lambda$.
- **c** (and a trend, where it survives) is recovered the same way as $-\beta_{const}/\lambda$.
- Standard errors on the long-run terms use the delta method.

### 3.3 Development Pipeline

| Step | Component | Code | Output |
| :-: | :--- | :--- | :--- |
| 1 | Data pull, rate construction and merger adjustment | `data_build/build_dataset.py` (supersedes `FDIC Fincancials pull and aggeregation.ipynb` and `TargetBank_merger_adjusted_features.ipynb`) | `consolidated_fdic_quarterly_financials_*.csv`, `merger_events_used.csv`, `merger_adjustment_log.md`, `data_build/raw/` |
| 1b | FFT regressor: FEDFUNDS averaged to complete calendar quarters | `data_build/build_fft.py` | `FFT_2011-2026.csv`, `FFT_2008-2026.csv` (from `FEDFUNDS.csv`) |
| 2 | Exploratory chart (Figure 1) | `EDA1_Stationarity_Tests.ipynb` | `docs/Historical Deposit Rates vs FFT.png` |
| 3 | Baseline cointegration tests | `Co-integration Tests.py` with `test_params.csv` | `Co-integration_results.csv` |
| 4 | Cointegration re-specification grid (all banks) | `FlaggedRates_co-integration_respecification.py` | `co-integration_respecification_results.csv` |
| 5 | Model selection (test p < 0.05) | `ECM model selection.py` | `ECM model selection results.csv` |
| 6 | Parameter selection (short-run coef p < 0.05) | `ECM Param selection.py` | `ECM param selection results.csv` |
| 7 | One-step ECM estimation and lag pruning | `ECM estimation.py` | `ECM estimation results.csv`, `estimation result summary.csv` |
| 8 | Backtests and ratings | `MAE_Backtesting/run_backtest.py`, `backtest.py` | `MAE_Backtesting/output/` |
| 8b | Long-run beta stability backtest and rating | `Beta_Backtesting/run_beta_backtest.py`, `beta_backtest.py` | `Beta_Backtesting/output/` |
| 8c | Optional out-of-sample model choice and comparison | `run_backtest.py --select out-of-sample`, `MAE_Backtesting/compare_selection.py` | `MAE_Backtesting/output/out_of_sample/`, `Beta_Backtesting/output/out_of_sample/` |
| 8d | Break tests and challenger models | `model_form/run_model_form.py` (`gregory_hansen.py`, `challengers.py`) | `model_form/output/` |
| 9 | Actual vs. predicted charts | `plotting_workflow.py`, `bank_plots.py` | `Actuals vs Predictions/<bank>/*.png` |
| 10 | Unit-root and structural-break diagnostics | `diagnostics/stationarity_and_breaks.py` | `diagnostics/*.csv` |
| 11 | Documentation figures | `docs/make_figures.py` | `docs/figures/` |
| 12 | Scenario projection with trend freeze | `projection/project.py` with a scenario CSV of FFT by quarter | `projection/output/<scenario>_projection.csv` |

Steps 5 to 7 are run together by `ECM workflow.py`. Steps 1b and 12 have tests: `python -m pytest data_build projection`.

---

## 4. Data

### 4.1 Sources
- **FDIC BankFind Suite, Financials endpoint** (`https://banks.data.fdic.gov/api/financials`). Fields: `CERT`, `REPDTE`, `EDEPDOMQ` and `EDEPFORQ` (quarterly interest expense on domestic and foreign-office deposits), `DEP` (total deposits). Quarterly Call Report data, 2007 to 2026Q2.
- **FDIC BankFind Suite, History endpoint** (`/api/history`), change codes 2xx (mergers, absorptions, whole-bank failure acquisitions), used to build the merger event list.
- **FRED `FEDFUNDS`**: monthly effective federal funds rate (`FEDFUNDS.csv`). `data_build/build_fft.py` averages it over the three months of each calendar quarter and writes `FFT_2011-2026.csv` and `FFT_2008-2026.csv`. Only complete quarters are kept: an incomplete current quarter is dropped with a warning that names it, and a missing month inside the series stops the build. `--refresh` re-downloads `FEDFUNDS` from FRED. The files run to 2026Q3; the estimation sample ends at 2026Q2, the last quarter of bank data.
- Built by `data_build/build_dataset.py`. The raw pulls used for this version are cached in `data_build/raw/`.

### 4.2 Transformations
1. **Quarterly deposit interest expense** is taken directly from FDIC's quarterly fields (`EDEPDOMQ` + `EDEPFORQ`). No year-to-date de-cumulation is needed.
2. **Annualization:** × 4.
3. **Average deposits:** mean of the current and previous quarter-end `DEP`. No calendar-year averaging, so there is no look-ahead.
4. **Deposit rate:** `deposit_rate = 100 × 4 × deposit interest expense ÷ average deposits`.
5. **Merger adjustment (pro forma).** See §4.3. The modeled series is `rate_pf_clean`.
6. **Alignment.** Bank and FFT series are joined on quarterly periods.

### 4.3 Merger Adjustment Methodology
- **Event list:** every merger, absorption or whole-bank failure acquisition into a target bank since 2007, from FDIC `/history`, with real predecessor certs (`merger_events_used.csv`). Materiality = predecessor deposits ÷ survivor deposits at the predecessor's last pre-merger quarter.
- **Mode A (≥ 1%):** full pro forma backfill. The predecessor's deposit interest expense and deposits are added to every pre-merger quarter of the survivor. In the merger quarter, the predecessor's last quarterly interest expense is added pro rata to the days before the effective date. Applied recursively to predecessors' own Mode A acquisitions.
- **Mode B (< 1%):** flagged only; rows are kept in `rate_pf_clean`. In the main sample: Glacier/Treasure State Bank 2016Q3 (0.84%), KeyBank/KeyTrust 2014Q3 (0%), Old National/Old National Trust 2014Q3 (0%).
- **Counts:** 73 events into the seven banks from 2011Q1 (70 Mode A, 3 Mode B); 92 since 2007; 300 predecessor-level events folded in.
- **Validations** (`merger_adjustment_log.md`): pro forma rate reconstruction difference 0.0; no duplicate keys; no negative or missing rates.

**Corrected events from the earlier draft's event list** (the earlier list used placeholder certs and a uniform 5,000,000 deposit figure):

| Predecessor | Survivor | FDIC cert | FDIC effective date | Last pre-merger deposits ($000) | % of survivor | Mode |
| :--- | :--- | :-: | :-: | --: | --: | :-: |
| First Niagara Bank | KeyBank | 16004 | 2016-10-08 | 27,347,485 | 34.2 | A |
| FirstMerit Bank | Huntington | 13675 | 2016-08-16 | 21,074,218 | 36.8 | A |
| TCF National Bank | Huntington | 28330 | 2021-06-09 | 39,975,492 | 37.5 | A |
| IBERIABANK | First Horizon | 28100 | 2020-07-02 | 28,436,334 | 72.9 | A |
| South State Bank (listed earlier as "CenterState Bank") | SouthState (former CenterState charter) | 13425 | 2020-06-08 | 12,393,605 | 87.7 | A (was B) |
| Atlantic Capital Bank | SouthState | 35525 | 2022-03-01 | 3,335,446 | 9.5 | A |
| First Midwest Bank | Old National | 3709 | 2022-02-16 | 17,578,256 | 94.1 | A |
| People's United Bank | M&T | 27334 | 2022-04-02 | 53,542,021 | 41.6 | A |

### 4.4 Sample
- Main: 2011Q1 to 2026Q2, 62 quarterly observations per bank.
- Sensitivity: 2008Q1 to 2026Q2, 74 observations per bank (Appendix A.2).

### 4.5 Exploratory Review
Figure 1 shows the series. Deposit rates track FFT with a lag and partial pass-through through the 2016 to 2019 tightening, the 2020 cut to the zero bound, and the 2022 to 2023 tightening. Since late 2024, deposit rates have fallen more slowly than FFT. Glacier's rate sits well below its peers through both tightening cycles.

Figure 1 is produced by the first cell of `EDA1_Stationarity_Tests.ipynb` from `rate_pf_clean` in `consolidated_fdic_quarterly_financials_2011-2026_merger_adjusted.csv` and `FFT_2011-2026.csv`. Bank rates use the left axis and FFT the right axis. The chart ends in 2026Q2, the last observed quarter.

![Historical deposit rates of the seven banks vs. FFT, 2011Q1 to 2026Q2](<docs/Historical Deposit Rates vs FFT.png>)

*Figure 1: Historical deposit rates (`rate_pf_clean`, left axis) of the seven banks vs. the federal funds rate (right axis), 2011Q1 to 2026Q2. Source: `EDA1_Stationarity_Tests.ipynb`.*

---

## 5. Methodology and Conceptual Soundness

### 5.1 Rationale
Deposit rates and policy rates are each non-stationary but are expected to share a long-run equilibrium. Regressing levels on levels without testing would risk spurious regression. The approach is therefore:
1. Establish the order of integration of each series.
2. Test for cointegration with three complementary procedures.
3. Estimate an ECM that separates long-run pass-through (θ) from short-run dynamics and the speed of adjustment (λ).

### 5.2 Unit Root Testing
- **ADF** (null: unit root) and **KPSS** (null: stationarity) on levels (I(0)) and first differences (I(1)).
- **Decision rule:** ADF indicates stationarity if p < 0.05. KPSS indicates stationarity if p ≥ 0.05. A series is classified only when both tests agree.
- Banks with inconclusive results under the default specification are **flagged** and re-tested over a grid:
  - ADF: regression `c` / `n` × lag selection AIC / BIC / t-stat.
  - KPSS: regression `c` / `ct` × bandwidth auto / long / short.
- KPSS p-values come from a lookup table bounded at 0.10. A reported 0.100 means "at least 0.10".
- Unit-root tests and Zivot-Andrews break tests are run for all banks and both samples by `diagnostics/stationarity_and_breaks.py`.

### 5.3 Structural Break Testing
Zivot-Andrews tests (`c`, `t`, `ct`; AIC lags, max 4) are run on the levels of every bank's series (§6, Appendix A.3). Every series rejects a unit root once a 2022 level break is allowed, and FFT shows the same break.

Because a break common to both series need not break their relationship, cointegration is also tested allowing one unknown break: the Gregory-Hansen (1996) tests in four forms, level shift (C), level shift with trend (C/T), regime shift (C/S) and regime shift with trend (C/S/T) (`model_form/gregory_hansen.py`).

- **Method:** breaks are searched over the middle 70% of the sample. The ADF\*, Zt\* and Zα\* statistics are each the minimum over breaks, and ADF lags are chosen by AIC (max 4).
- **Critical values:** with 62 quarters, finite-sample critical values are simulated (2,000 replications) and govern. They are markedly larger in magnitude than the asymptotic values: for C ADF\* at 5%, −5.14 against −4.61.
- **Result:** no bank rejects "no cointegration" on ADF\* at 5%. The only 5% rejection on any statistic is Glacier's C/T Zt\* (−5.42 against −5.24, break 2023Q3).
- **Interpretation:** allowing a break neither strengthens nor overturns the cointegration results of §5.4. The 2022 break in the deposit-rate series mirrors the break in FFT and cancels in the cointegrating relation. Because the null is not rejected, the GH break dates (2021Q3 to 2024Q1) are not interpreted.
- **Dummy test:** a 2022Q3 level dummy added to each champion ECM is significant at 5% for Glacier, M&T, Huntington and Old National. It trades off against θ and worsens out-of-sample forecasts for most banks (§7.4), so no champion carries it.

### 5.4 Cointegration Testing

| Procedure | Statistic | p-value | Specification grid |
| :--- | :--- | :--- | :--- |
| Engle-Granger, long run (`EG_LongRun`) | ADF *t* on step-1 OLS residuals | MacKinnon (2010), N = 2 | Trend `n` / `c` / `ct`; ADF and ECM lags by AIC / BIC / t-stat (general-to-specific) / fixed = 4 |
| Engle-Granger, short run (`EG_ShortRun`) | *t* on `ect.L1` in the short-run ECM | MacKinnon (2010), same trend and N | As above |
| Johansen trace | Trace statistic for r ≤ 0, r ≤ 1 | Bounded from critical values (<0.01, <0.05, <0.10, >0.10) | `det_order` -1 / 0 / 1; `k_ar_diff` by VECM AIC / BIC / HQIC / FPE or fixed at 1 |
| ARDL bounds test (PSS) | Bounds F | I(1) upper-bound p-value | PSS cases 1 to 5; lags by AIC / BIC / HQIC (max 4); at least 1 lag of the regressor |

- **Baseline run** (`Co-integration Tests.py`, all 7 banks): trend `c`, max lag 4, EG and ARDL lags by AIC, Johansen `det_order 0` with `k_ar_diff = 1`, ARDL case 3.
- **Re-specification run** (`FlaggedRates_co-integration_respecification.py`): full grid for all seven banks. On the rebuilt data, Huntington and Old National fail the baseline and qualify only through the grid.
- Coefficient t- and p-values on levels regressors (EG step 1, VECM β) do not follow standard distributions when the series are I(1). They are descriptive only.

### 5.5 Model and Parameter Selection
1. **Model screen:** keep every specification whose cointegration test p-value is below α = 0.05. A Johansen VECM takes the r ≤ 0 trace result of the same specification. A bounded Johansen p-value "<x" passes when x ≤ α.
2. **Parameter screen:** within each surviving specification, keep short-run terms with coefficient p-value < 0.05. Deterministic terms are set by the test specification (`n` / case 1 / det_order -1: none; `c` / cases 2–3 / det_order 0: constant; `ct` / cases 4–5 / det_order 1: constant and trend) and are not screened.
3. **Mapping to a one-step ECM:** surviving deterministic terms, short-run lags, and the error-correction term (`ect.L1`, `y.L1` or VECM `D.y: ec1`) define the regressors. Specifications without a surviving error-correction term are dropped. `EG_LongRun` is treated as error-correcting by construction. Its short-run candidates are the D.y and D.FFT lags of the Engle-Granger second-step regression of the same specification, screened in step 2 like any other short-run term (OI-24).
4. **Estimation:** one-step OLS ECM (§3.2), with long-run coefficients and delta-method standard errors. Short-run lags with p ≥ 0.05 are then removed one at a time (largest p first) and the model refit. λ, the long-run regressor and the deterministic terms are never removed.
5. **Champion choice:** lowest in-sample MAE of Δy per bank. Ties are broken EG > ARDL > Johansen, then file order. This is the default and the basis of every result in this document.
6. **Optional out-of-sample rule (OI-9, not adopted; deferred to the validator):** `run_backtest.py --select out-of-sample`.
   - **Admissibility:** keep models with λ in (−1, 0) and θ in [0, 1].
   - **Ranking:** by mean many-start-date h-step MAE (h = 1 to N, start dates from 2016Q1, §5.6).
   - **Pick:** the model with the fewest parameters among those within one standard error of the best. The standard error is Newey-West with N−1 lags over the start dates with all N steps.
   - **Effect:** the rule changes the model for six of seven banks (§7.6).

### 5.6 Performance Testing (Backtest)
**Governing test: many-start-date backtest.**
- At every start date from 2016Q1 to T-1 (T = 2026Q2), the champion specification is re-estimated on data up to that start date (expanding window) and forecast dynamically up to N quarters ahead, with predicted y fed back as the lag and realized FFT used for the regressor. The horizon N is a user input (`--horizon`, default 8Q).
- **Metric:** h-step-ahead MAE, averaged over every start date with start + h ≤ T (34 start dates at 8Q, 41 at 1Q).
- **Benchmark:** a no-change forecast (deposit rate held at its start-date value), scored the same way. Skill ratio = model h-step MAE ÷ no-change h-step MAE.
- **Horizon bands, derived from N:** 1 to ⌈N/4⌉, ⌈N/4⌉+1 to ⌈N/2⌉, ⌈N/2⌉+1 to N (8Q: 1–2Q, 3–4Q, 5–8Q).
- **Band limits, derived each run from the peer group:** green = the 75th percentile of the banks' band-average MAE, rounded up to 0.05; red = the 75th percentile of the banks' band-maximum MAE, rounded up to 0.05, and at least green + 0.05.
- **Rating:** absolute test, Red if a band maximum exceeds red, Amber if a band average exceeds green; skill test, Red if any ratio ≥ 1.00, Amber if any ratio > 0.75. The rating is the worse of the two. With fewer than four banks, only the skill test applies.
- The limits are relative to the peer group: by construction, about a quarter of banks exceed the green limit in each band. The skill test is the only absolute standard. Fixing the limits from a reference run is a candidate refinement.
- Per-origin errors are cached (`MAE_Backtesting/output/cache/`) so that a shorter horizon reuses a longer run without refitting.

**Parameter stability test: long-run beta from 2016Q1.**
- **Method:** at every start date from 2016Q1 to T−1 (41 at T = 2026Q2), the champion is re-estimated on data up to that start date (expanding window, the same fit and start dates as the many-start-date backtest). θ = −β(FFT.L1)/λ, its delta-method standard error and λ are recorded.
- **Deviation:** each start date's deviation from the full-sample θ is reported in pp, as a share of θ and in origin standard errors.
- **Rating:** on the start dates from 2020Q1. Earlier samples are mostly at the zero lower bound, where θ is weakly identified; they are charted but not rated.
  - A start date fails if its θ is more than 2 origin standard errors **and** more than 20% away from the full-sample θ.
  - Green: no failing start date.
  - Amber: one or two failing start dates, none more than 3 standard errors and 20% away.
  - Red: three or more failing start dates, or any start date more than 3 standard errors and 20% away.
- **Rationale for the joint test:** it counts only deviations that are both statistically and economically large. A large move with a wide standard error (λ near zero) is treated as imprecision, not instability.
- **Supplementary view:** the 8-start-date view (start dates T−8 to T−1, mean θ per horizon) is kept in `Beta_Backtesting/output/<bank>/beta_backtest_8Q.png`.
- Per-start-date θ is cached (`Beta_Backtesting/output/cache/`). The backtest caches are keyed on the fitted terms as well as the model label, so a change to a model's terms is never served stale errors.

**Supplementary test: single-window 8Q backtest.** For each k = 1 to 8, one forecast from start date T−k to T, with MAE averaged over its k quarters. Each kQ figure rests on one start date. Rated Green (mean ≤ 0.15 pp and below the no-change mean), Amber (mean 0.15–0.25 pp, or beats no-change on fewer than 6 of 8 horizons) or Red (mean > 0.25 pp, or any horizon > 0.50 pp).

### 5.7 Key Assumptions
- FFT is weakly exogenous to each bank's deposit rate (single-equation ECM).
- One cointegrating vector (rank 1) between the deposit rate and FFT.
- Linear, symmetric pass-through: no asymmetry between rising and falling rates, and no threshold at the zero lower bound. An asymmetric-λ challenger is tested in §7.4.
- Parameters are stable over 2011 to 2026, apart from any deterministic trend.
- Deposit interest expense ÷ total deposits (interest-bearing and non-interest-bearing) is an adequate measure of the deposit rate, giving a total-deposit beta.
- For projection, a deterministic trend in the long-run relation is frozen at its end-of-sample value: for every quarter after T the trend regressor is held at its value at T (62 at 2026Q2, counting from 1 at 2011Q1). The equilibrium is therefore $c + \delta T + \theta x$, and with FFT held flat a projection converges to that level instead of drifting by δ per quarter. This is implemented in `projection/project.py` and tested in `projection/test_project.py`. It affects the First Horizon, M&T and Glacier champions; champions without a trend are unchanged.

---

## 6. Bank-Specific Development and Treatment

Each subsection follows the same structure: data treatment, stationarity, structural breaks, cointegration, specifications estimated, champion model, and outcomes and issues. All results use the 2011Q1 to 2026Q2 pro forma (merger-adjusted) series built from deposit interest expense (§4), unless stated otherwise. Rates are in percentage points (pp).

### 6.1 First Horizon Bank

#### 6.1.1 Data Treatment
- FDIC cert 4977. Pro forma for Mountain National (2013), TrustAtlantic (2015), Capital Bank Corporation (2017, 37%) and IBERIABANK (2020-07-02, 73%).

#### 6.1.2 Stationarity

| Sample (pro forma) | Levels I(0) | First difference I(1) |
| :--- | :--- | :--- |
| 2011Q1 to 2026Q2 (main) | ADF -2.373 (p 0.149), KPSS 0.558 (p 0.029): non-stationary | ADF -3.679 (p 0.0044), KPSS 0.112 (p ≥ 0.10): stationary |
| 2008Q1 to 2026Q2 | ADF -2.868 (p 0.049), KPSS 0.284 (p ≥ 0.10): stationary | ADF -3.565 (p 0.0065), KPSS 0.366 (p 0.092): stationary |

Default specification: ADF `c` / AIC and KPSS `c` / auto.

**Robustness** (share of the six re-specifications agreeing with the default, main sample): ADF I(0) 6/6, KPSS I(0) 2/6, ADF I(1) 6/6, KPSS I(1) 6/6.

**Conclusion (main sample):** **I(1)** under the default specification. Not flagged. 2008 to 2026 sample: I(0).

#### 6.1.3 Structural Breaks
Zivot-Andrews on levels, 2011 to 2026 (AIC lags, max 4): `c`: -6.27, p 5.4e-04, break 2022Q3; `t`: -4.80, p 0.019, break 2021Q4; `ct`: -5.07, p 0.051, break 2023Q1. The unit root is rejected when a 2022 level break is allowed, mirroring the break in FFT itself (OI-20).

#### 6.1.4 Cointegration
- **Baseline:** EG long run p 0.264; EG short run p 0.424; Johansen trace r ≤ 0 = 21.59 (p < 0.01), r ≤ 1 = 2.93 (p < 0.10); ARDL(4,4) case 3 F = 3.54 (p 0.169). Only Johansen passes.
- **Re-specification:** run for all seven banks (§5.4). Specifications that pass and reach estimation: Johansen `det_order` -1, 0, 1; EG short run `n`; EG long run `c`, `ct`; ARDL cases 1, 4, 5.
- **Gregory-Hansen** (one break, §5.3; 5% simulated critical values C −5.14, C/T −5.50, C/S −5.46, C/S/T −5.82): no rejection at 5%. ADF\* C −4.05 (2016Q3), C/T −4.53 (2023Q4), C/S −4.50 (2021Q4), C/S/T −4.58 (2023Q4).

#### 6.1.5 Specifications Estimated
23 one-step ECMs (9 ARDL, 7 Johansen, 7 EG). In-sample MAE 0.0469 to 0.0798. Long-run beta 0.404 to 0.527.

#### 6.1.6 Champion Model: ARDL(3,4), case 4 (unrestricted constant, restricted trend), AIC
Tied on in-sample MAE with the HQIC selection of the same lags and with case 5 under AIC and HQIC; the tie-break kept the case 4 AIC row. The deterministic terms follow the case 4 test specification (§5.5).

| Term | Coefficient | *t* | p-value |
| :--- | :-: | :-: | :-: |
| const | 0.1266 | 2.83 | 0.0068 |
| trend | -0.00400 | -2.83 | 0.0068 |
| y.L1 (λ) | **-0.3747** | -4.21 | 1.1e-04 |
| FFT.L1 | 0.1935 | 4.34 | 7.1e-05 |
| D.y.L1 | 0.3469 | 3.35 | 0.0016 |
| D.y.L2 | -0.4059 | -4.54 | 3.7e-05 |
| D.FFT.L0 | 0.2171 | 5.08 | 5.9e-06 |
| D.FFT.L1 | -0.1563 | -2.30 | 0.026 |
| D.FFT.L3 | 0.1511 | 2.73 | 0.0087 |
| LR: const | 0.3378 | 4.71 | 2.1e-05 |
| LR: trend | -0.0107 | -3.71 | 5.3e-04 |
| **LR: FFT (θ)** | **0.5165** | 16.88 | 4.6e-22 |

![First Horizon Bank: actual vs. predicted deposit rate, champion model](<docs/figures/First Horizon Bank - Actual vs Predicted.png>)

*Figure 2: First Horizon Bank, actual vs. one-step ECM fitted deposit rate (`rate_pf_clean`), champion model. In-sample.*

#### 6.1.7 Outcomes Analysis and Issues
- **Governing MAE rating (many-start-date backtest, §5.6): Red** (1-2Q max 0.179 > red 0.15). h-step MAE, 1Q to 8Q, over 34 to 41 start dates: 0.100, 0.179, 0.227, 0.239, 0.283, 0.308, 0.312, 0.292 (mean 0.242). Worst skill ratio against the no-change forecast: 0.71 at 1Q.
- Single-window 8Q backtest (one start date per horizon, supplementary): 0.094, 0.044, 0.030, 0.067, 0.096, 0.086, 0.177, 0.103; mean 0.087, no-change mean 0.307, beats no-change on 7/8 horizons (Green).

![First Horizon Bank: many-start-date backtest MAE by horizon](<docs/figures/First Horizon Bank - MAE Backtest 8Q.png>)

*Figure 3: First Horizon Bank, many-start-date backtest: h-step MAE by horizon over 34 to 41 start dates (n under each bar), with the no-change forecast and the 8Q band limits (§5.6), champion model.*

- The MAE rating is Red only because the 1–2Q red limit is derived from the peer group and fell from 0.20 to 0.15 when the re-specified Huntington and Old National champions improved (OI-24). First Horizon's own errors are unchanged; with the previous limits it was Green. Fixing the limits from a reference run is tracked in [#8](https://github.com/Panda5130/Deposit-Beta/issues/8).
- The long-run trend (-0.011 pp per quarter, p 0.0005) survives full pro forma adjustment for IBERIABANK and Capital Bank, so it does not stand in for an unmodeled merger. For projection it is frozen at its 2026Q2 value (§5.7).
- λ = -0.37: about 37% of any disequilibrium closes each quarter, the fastest adjustment in the peer set.

- **Long-run beta stability (§5.6): Green.** From 2020Q1 to 2026Q1, θ ranges from 0.437 to 0.596 against the full-sample 0.517. The largest deviation is 15% (2023Q3) and at most 1.57 origin standard errors (2023Q4). Failing start dates: none. It is the most stable beta in the peer set. Over the last eight start dates (2024Q2–2026Q1) the range is 0.494–0.542.

![First Horizon Bank: long-run beta at every start date](<docs/figures/First Horizon Bank - Beta Backtest.png>)

*Figure 4: First Horizon Bank, long-run beta θ re-estimated at every start date from 2016Q1 (expanding window), with ±2 origin standard errors, the full-sample θ ±20% and the unrated window before 2020Q1 shaded, champion model.*

### 6.2 Glacier Bank

#### 6.2.1 Data Treatment
- FDIC cert 30788. Pro forma for 25 Mode A events since 2011, including the 2012-04-30 consolidation of 10 affiliate charters (First Security Bank of Missoula, Mountain West Bank, Western Security Bank, 1ST BANK, Valley Bank of Helena, First Bank of Wyoming, Citizens Community Bank, Big Sky Western Bank, Bank of the San Juans, First Bank of Montana) and Altabank (2021, 19%). Treasure State Bank (2016, 0.84%) is Mode B.
- The 2012Q1 dip (0.14%) and 2012Q2 spike (1.50%) in the earlier build came from the charter consolidation combined with calendar-year deposit averaging and year-to-date de-cumulation. Both are gone in the rebuilt series (0.487% and 0.494%).

#### 6.2.2 Stationarity

| Sample (pro forma) | Levels I(0) | First difference I(1) |
| :--- | :--- | :--- |
| 2011Q1 to 2026Q2 (main) | ADF -1.226 (p 0.662), KPSS 0.447 (p 0.057): inconclusive | ADF -3.539 (p 0.0070), KPSS 0.223 (p ≥ 0.10): stationary |
| 2008Q1 to 2026Q2 | ADF -1.749 (p 0.406), KPSS 0.295 (p ≥ 0.10): inconclusive | ADF -2.870 (p 0.049), KPSS 0.647 (p 0.018): inconclusive |

Default specification: ADF `c` / AIC and KPSS `c` / auto.

**Robustness** (share of the six re-specifications agreeing with the default, main sample): ADF I(0) 6/6, KPSS I(0) 1/6, ADF I(1) 6/6, KPSS I(1) 6/6.

**Conclusion (main sample):** **Flagged:** the default specification is inconclusive on levels. 2008 to 2026 sample: flagged.

#### 6.2.3 Structural Breaks
Zivot-Andrews on levels, 2011 to 2026 (AIC lags, max 4): `c`: -7.57, p 1.0e-05, break 2022Q4; `t`: -3.79, p 0.210, break 2021Q3; `ct`: -5.20, p 0.036, break 2023Q1. The unit root is rejected when a 2022 level break is allowed, mirroring the break in FFT itself (OI-20).

#### 6.2.4 Cointegration
- **Baseline:** none pass. EG long run p 0.353; Johansen trace r ≤ 0 = 13.17 (p > 0.10); ARDL(3,4) case 3 F = 2.95 (p 0.278).
- **Re-specification:** Johansen `det_order 1`, k_ar_diff = 1 (BIC, fixed): r ≤ 0 = 20.31 (p < 0.05), r ≤ 1 = 5.64 (p < 0.05). ARDL(3,1) cases 4 and 5 under BIC (F 6.04, p 0.007; F 8.25, p 0.004).
- The Johansen r ≤ 1 rejection, if taken literally, implies rank 2. Rank 1 is imposed by assumption.
- **Gregory-Hansen** (one break, §5.3; 5% simulated critical values C −5.14, C/T −5.50, C/S −5.46, C/S/T −5.82): ADF\* does not reject at 5% under any model: C −3.90 (2024Q1), C/T −5.44 (2023Q3; rejects only against the asymptotic −4.99), C/S −4.09 (2021Q3), C/S/T −5.30 (2024Q1). The C/T Zt\* (−5.42, break 2023Q3) rejects at 5%, the only GH rejection in the peer set.

#### 6.2.5 Specifications Estimated
4 one-step ECMs (2 Johansen, 2 ARDL). In-sample MAE 0.0292 to 0.0310. Long-run beta 0.277 to 0.346.

#### 6.2.6 Champion Model: ARDL(3,1), case 4 (unrestricted constant, restricted trend), BIC
The constant and trend are individually insignificant (p 0.106 and 0.103) but are kept because the case 4 test that qualifies the model includes them (§5.5).

| Term | Coefficient | *t* | p-value |
| :--- | :-: | :-: | :-: |
| const | 0.0265 | 1.64 | 0.106 |
| trend | -0.00094 | -1.66 | 0.103 |
| y.L1 (λ) | **-0.1123** | -3.65 | 6.0e-04 |
| FFT.L1 | 0.0388 | 3.99 | 2.0e-04 |
| D.y.L1 | 0.7268 | 6.15 | 1.1e-07 |
| D.y.L2 | -0.2730 | -2.47 | 0.017 |
| D.FFT.L0 | 0.0485 | 2.87 | 0.0059 |
| LR: const | 0.2360 | 1.97 | 0.055 |
| LR: trend | -0.00835 | -1.73 | 0.090 |
| **LR: FFT (θ)** | **0.3459** | 6.05 | 1.6e-07 |

![Glacier Bank: actual vs. predicted deposit rate, champion model](<docs/figures/Glacier Bank - Actual vs Predicted.png>)

*Figure 5: Glacier Bank, actual vs. one-step ECM fitted deposit rate (`rate_pf_clean`), champion model. In-sample.*

#### 6.2.7 Outcomes Analysis and Issues
- **Governing MAE rating (many-start-date backtest, §5.6): Amber** (skill ratio 0.96 at 3Q). h-step MAE, 1Q to 8Q, over 34 to 41 start dates: 0.047, 0.103, 0.156, 0.195, 0.238, 0.277, 0.306, 0.331 (mean 0.207). Worst skill ratio against the no-change forecast: 0.96 at 3Q.
- Single-window 8Q backtest (one start date per horizon, supplementary): 0.094, 0.031, 0.021, 0.017, 0.116, 0.172, 0.150, 0.040; mean 0.080, no-change mean 0.119, beats no-change on 5/8 horizons (Amber).

![Glacier Bank: many-start-date backtest MAE by horizon](<docs/figures/Glacier Bank - MAE Backtest 8Q.png>)

*Figure 6: Glacier Bank, many-start-date backtest: h-step MAE by horizon over 34 to 41 start dates (n under each bar), with the no-change forecast and the 8Q band limits (§5.6), champion model.*

- The skill ratio is close to 1 (0.96 at 3Q): Glacier's rate moves little, so the no-change forecast is nearly as accurate as the model. This is the reason for the Amber MAE rating.
- The champion carries a long-run trend, frozen at its 2026Q2 value for projection (§5.7).
- The levels series is flagged in both samples (KPSS I(0) p 0.057 in the main sample).

- **Long-run beta stability (§5.6): Red.** From 2020Q1 to 2026Q1, θ ranges from 0.110 to 0.383 against the full-sample 0.346. The largest deviation is 68% (2020Q1) and at most 11.37 origin standard errors (2022Q4). Failing start dates: 14 (2020Q1 2020Q2 2020Q3 2020Q4 2021Q1 2021Q2 2021Q3 2021Q4 2022Q1 2022Q2 2022Q3 2022Q4 2023Q1 2023Q4). θ is 0.11–0.14 at every start date from 2020Q1 to 2023Q1, with standard errors of 0.02–0.04, and reaches 0.29–0.38 only once the 2022–23 hiking cycle is in the sample: the long-run beta is identified almost entirely by the last cycle. Over the last eight start dates (2024Q2–2026Q1) the range is 0.294–0.383.

![Glacier Bank: long-run beta at every start date](<docs/figures/Glacier Bank - Beta Backtest.png>)

*Figure 7: Glacier Bank, long-run beta θ re-estimated at every start date from 2016Q1 (expanding window), with ±2 origin standard errors, the full-sample θ ±20% and the unrated window before 2020Q1 shaded, champion model.*

### 6.3 Huntington National Bank

#### 6.3.1 Data Treatment
- FDIC cert 6560. Pro forma for Fidelity Bank (2012), Advantage Bank (2014), FirstMerit (2016-08-16, 37%), TCF (2021-06-09, 38%), Veritex (2025-10-20, 6%) and Cadence Bank (2026-02-01, 24%).
- The earlier build showed a 0.00% rate in 2021Q1 because FDIC total interest expense was negative that quarter (probably hedge income) and was clipped to zero. Deposit interest expense is positive (rebuilt rate 0.131%).

#### 6.3.2 Stationarity

| Sample (pro forma) | Levels I(0) | First difference I(1) |
| :--- | :--- | :--- |
| 2011Q1 to 2026Q2 (main) | ADF -1.595 (p 0.486), KPSS 0.589 (p 0.024): non-stationary | ADF -3.804 (p 0.0029), KPSS 0.158 (p ≥ 0.10): stationary |
| 2008Q1 to 2026Q2 | ADF -1.690 (p 0.436), KPSS 0.280 (p ≥ 0.10): inconclusive | ADF -2.805 (p 0.058), KPSS 0.500 (p 0.042): non-stationary |

Default specification: ADF `c` / AIC and KPSS `c` / auto.

**Robustness** (share of the six re-specifications agreeing with the default, main sample): ADF I(0) 6/6, KPSS I(0) 2/6, ADF I(1) 6/6, KPSS I(1) 6/6.

**Conclusion (main sample):** **I(1)** under the default specification. Not flagged. 2008 to 2026 sample: flagged.

#### 6.3.3 Structural Breaks
Zivot-Andrews on levels, 2011 to 2026 (AIC lags, max 4): `c`: -6.34, p 4.7e-04, break 2022Q2; `t`: -5.41, p 0.0049, break 2021Q4; `ct`: -5.64, p 0.0082, break 2022Q3. The unit root is rejected when a 2022 level break is allowed, mirroring the break in FFT itself (OI-20).

#### 6.3.4 Cointegration
- **Baseline:** none pass at 5%. EG long run p 0.085; EG short run p 0.882; Johansen trace r ≤ 0 = 13.05 (p > 0.10); ARDL(4,3) case 3 F = 2.78 (p 0.318).
- **Re-specification** (now run, OI-4): only EG long run with no deterministic terms passes (t -3.13, p 0.019 under AIC, BIC and t-stat). Johansen gives r ≤ 1 rejections only.
- **Gregory-Hansen** (one break, §5.3; 5% simulated critical values C −5.14, C/T −5.50, C/S −5.46, C/S/T −5.82): no rejection at 5%. ADF\* C −3.79 (2023Q4), C/T −4.42 (2023Q4), C/S −3.96 (2021Q3), C/S/T −4.37 (2023Q4). EG without deterministic terms fails in every sample window ending in 2019Q4, and in 2021Q4 windows starting in 2013 or later (p 0.18 to 0.69). It passes in every window ending in 2024Q2 or later (`model_form/output/huntington_eg_subsamples.csv`; OI-19).

#### 6.3.5 Specifications Estimated
3 one-step ECMs (3 EG), all the same regression: in-sample MAE 0.0234, long-run beta 0.463.

#### 6.3.6 Champion Model: Engle-Granger long run, trend `n`, AIC (ADF lag=1, ECM lag=3)
All three passing specifications (AIC, BIC, t-stat) give the same one-step ECM. Short-run candidates are the D.y and D.FFT lags of the Engle-Granger second-step regression (§5.5, OI-24): D.y L1–L3 and D.FFT L0–L2 pass the screen and survive pruning; D.FFT.L3 (p 0.61) fails the screen.

| Term | Coefficient | *t* | p-value |
| :--- | :-: | :-: | :-: |
| y.L1 (λ) | **-0.0665** | -2.49 | 0.016 |
| FFT.L1 | 0.0308 | 2.51 | 0.015 |
| D.y.L1 | 0.8553 | 7.22 | 2.7e-09 |
| D.y.L2 | -0.8956 | -6.09 | 1.6e-07 |
| D.y.L3 | 0.4322 | 4.92 | 9.7e-06 |
| D.FFT.L0 | 0.1738 | 9.75 | 3.7e-13 |
| D.FFT.L1 | -0.0995 | -3.05 | 0.0036 |
| D.FFT.L2 | 0.1566 | 4.98 | 8.0e-06 |
| **LR: FFT (θ)** | **0.4627** | 13.28 | 5.2e-18 |

Before OI-24 the champion had no short-run terms (λ −0.313, θ 0.469, in-sample MAE 0.0709). The contemporaneous ΔFFT term now passes about 17% of a rate change through in the same quarter, and λ falls to −0.066: adjustment runs mainly through the short-run terms rather than through error correction.

![Huntington National Bank: actual vs. predicted deposit rate, champion model](<docs/figures/Huntington National Bank - Actual vs Predicted.png>)

*Figure 8: Huntington National Bank, actual vs. one-step ECM fitted deposit rate (`rate_pf_clean`), champion model. In-sample.*

#### 6.3.7 Outcomes Analysis and Issues
- **Governing MAE rating (many-start-date backtest, §5.6): Green**. h-step MAE, 1Q to 8Q, over 34 to 41 start dates: 0.042, 0.097, 0.148, 0.199, 0.255, 0.307, 0.339, 0.381 (mean 0.221). Worst skill ratio against the no-change forecast: 0.49 at 6Q.
- Single-window 8Q backtest (one start date per horizon, supplementary): 0.094, 0.132, 0.069, 0.049, 0.187, 0.287, 0.169, 0.214; mean 0.150, no-change mean 0.231, beats no-change on 4/8 horizons (Amber).

![Huntington National Bank: many-start-date backtest MAE by horizon](<docs/figures/Huntington National Bank - MAE Backtest 8Q.png>)

*Figure 9: Huntington National Bank, many-start-date backtest: h-step MAE by horizon over 34 to 41 start dates (n under each bar), with the no-change forecast and the 8Q band limits (§5.6), champion model.*

- The re-specified champion (OI-24) lowers the many-start-date mean MAE from 0.334 (Red) to 0.221 (Green). The single window from 2025Q1 (5Q column of §7.2) worsens from 0.094 to 0.187, above the no-change forecast (0.135): the new champion carries large lagged-Δy terms, which OI-8 identified as the source of the 2025Q1 error at M&T, Old National and SouthState (OI-25).
- **Scope decision (2026-10-31): Huntington stays in scope with a caveat** (OI-19, L15). Cointegration rests on one specification family (EG long run, no deterministic terms) and is identified mainly by the 2022–24 cycle, and Gregory-Hansen finds no break.
- **Adjustment asymmetry.** With the previous champion Huntington had the strongest asymmetry in the peer set (Wald p 1.4e-07). Against the re-specified champion the difference is no longer significant (λ+ −0.048 vs. λ− −0.112, Wald p 0.11), and an asymmetric-λ variant is only marginally better (mean MAE 0.214 vs. 0.221, §7.4).

- **Long-run beta stability (§5.6): Green.** From 2020Q1 to 2026Q1, θ ranges from 0.243 to 0.553 against the full-sample 0.463. The largest deviation is 47% (2020Q2) and at most 1.29 origin standard errors (2022Q4). Failing start dates: none. θ is about 0.41 from 2020Q4 to 2022Q1, rises to 0.55 at 2024Q2, dips to 0.35 at 2024Q4 at the turn of the easing cycle, then settles at 0.42–0.45. The largest share deviation (2020Q2, 0.243) has a standard error of 0.31 and is imprecise rather than significant. With the previous champion the rating was Amber (2023Q4 and 2024Q1 failed). Over the last eight start dates (2024Q2–2026Q1) the range is 0.352–0.553.

![Huntington National Bank: long-run beta at every start date](<docs/figures/Huntington National Bank - Beta Backtest.png>)

*Figure 10: Huntington National Bank, long-run beta θ re-estimated at every start date from 2016Q1 (expanding window), with ±2 origin standard errors, the full-sample θ ±20% and the unrated window before 2020Q1 shaded, champion model.*

### 6.4 KeyBank National Association

#### 6.4.1 Data Treatment
- FDIC cert 17534. Pro forma for First Niagara Bank (cert 16004, FDIC effective 2016-10-08, 34%). KeyTrust Company (2014, no deposits) is Mode B.

#### 6.4.2 Stationarity

| Sample (pro forma) | Levels I(0) | First difference I(1) |
| :--- | :--- | :--- |
| 2011Q1 to 2026Q2 (main) | ADF -1.952 (p 0.308), KPSS 0.572 (p 0.025): non-stationary | ADF -3.732 (p 0.0037), KPSS 0.138 (p ≥ 0.10): stationary |
| 2008Q1 to 2026Q2 | ADF -1.576 (p 0.496), KPSS 0.272 (p ≥ 0.10): inconclusive | ADF -2.855 (p 0.051), KPSS 0.459 (p 0.052): inconclusive |

Default specification: ADF `c` / AIC and KPSS `c` / auto.

**Robustness** (share of the six re-specifications agreeing with the default, main sample): ADF I(0) 6/6, KPSS I(0) 2/6, ADF I(1) 6/6, KPSS I(1) 6/6.

**Conclusion (main sample):** **I(1)** under the default specification. Not flagged. 2008 to 2026 sample: flagged.

#### 6.4.3 Structural Breaks
Zivot-Andrews on levels, 2011 to 2026 (AIC lags, max 4): `c`: -6.81, p 1.0e-05, break 2022Q3; `t`: -4.67, p 0.024, break 2021Q4; `ct`: -4.93, p 0.076, break 2022Q3. The unit root is rejected when a 2022 level break is allowed, mirroring the break in FFT itself (OI-20).

#### 6.4.4 Cointegration
- **Baseline:** EG long run p 0.198 (fails; the earlier build passed); Johansen trace r ≤ 0 = 13.78 (p < 0.10); ARDL(4,4) case 3 F = 3.39 (p 0.193).
- **Re-specification:** broad support. Specifications that pass and reach estimation: EG long run `c`, `n`; EG short run `n`; Johansen `det_order` 1; ARDL cases 1, 3, 4, 5.
- **Gregory-Hansen** (one break, §5.3; 5% simulated critical values C −5.14, C/T −5.50, C/S −5.46, C/S/T −5.82): no rejection at 5%. ADF\* C −3.90 (2024Q1), C/T −4.72 (2024Q1), C/S −4.30 (2021Q3), C/S/T −4.75 (2024Q1).

#### 6.4.5 Specifications Estimated
17 one-step ECMs (8 EG, 8 ARDL, 1 Johansen). In-sample MAE 0.0317 to 0.0453. Long-run beta 0.398 to 0.487.

#### 6.4.6 Champion Model: Engle-Granger long run, trend `n`, BIC (ADF lag=1, ECM lag=3)
With short-run candidates now offered to EG long-run specifications (OI-24), EG long run `n` (BIC and t-stat) gives exactly the regression of ARDL(4,4) case 1, AIC (in-sample MAE 0.0317 for both). The EG > ARDL tie-break (§5.5) selects the EG label. Coefficients, backtests and ratings are unchanged.

| Term | Coefficient | *t* | p-value |
| :--- | :-: | :-: | :-: |
| y.L1 (λ) | **-0.1102** | -2.67 | 0.010 |
| FFT.L1 | 0.0438 | 2.58 | 0.013 |
| D.y.L1 | 0.5143 | 4.94 | 8.9e-06 |
| D.y.L2 | -0.4424 | -3.15 | 0.0028 |
| D.y.L3 | 0.2780 | 2.71 | 0.0091 |
| D.FFT.L0 | 0.1207 | 5.70 | 6.0e-07 |
| D.FFT.L2 | 0.0956 | 2.45 | 0.018 |
| **LR: FFT (θ)** | **0.3975** | 13.68 | 1.1e-18 |

![KeyBank National Association: actual vs. predicted deposit rate, champion model](<docs/figures/KeyBank National Association - Actual vs Predicted.png>)

*Figure 11: KeyBank National Association, actual vs. one-step ECM fitted deposit rate (`rate_pf_clean`), champion model. In-sample.*

#### 6.4.7 Outcomes Analysis and Issues
- **Governing MAE rating (many-start-date backtest, §5.6): Red** (5-8Q max 0.533 > red 0.45). h-step MAE, 1Q to 8Q, over 34 to 41 start dates: 0.054, 0.115, 0.172, 0.224, 0.294, 0.384, 0.464, 0.533 (mean 0.280). Worst skill ratio against the no-change forecast: 0.71 at 8Q.
- Single-window 8Q backtest (one start date per horizon, supplementary): 0.075, 0.026, 0.184, 0.060, 0.121, 0.171, 0.358, 0.123; mean 0.140, no-change mean 0.272, beats no-change on 7/8 horizons (Green).

![KeyBank National Association: many-start-date backtest MAE by horizon](<docs/figures/KeyBank National Association - MAE Backtest 8Q.png>)

*Figure 12: KeyBank National Association, many-start-date backtest: h-step MAE by horizon over 34 to 41 start dates (n under each bar), with the no-change forecast and the 8Q band limits (§5.6), champion model.*

- The 8Q-ahead error (0.533) is above the peer-derived red limit for the 5–8Q band (0.45), which is the reason for the Red MAE rating.
- λ = -0.11: slow adjustment, so errors compound over long horizons.
- The beta range across passing specifications is 0.40 to 0.49.

- **Long-run beta stability (§5.6): Green.** From 2020Q1 to 2026Q1, θ ranges from 0.275 to 0.532 against the full-sample 0.398. The largest deviation is 34% (2024Q3) and at most 1.29 origin standard errors (2022Q3). Failing start dates: none. The largest deviations (31% at 2022Q3, 34% at 2024Q3) are within 1.3 origin standard errors, because λ is small and the estimates are imprecise. Over the last eight start dates (2024Q2–2026Q1) the range is 0.354–0.532.

![KeyBank National Association: long-run beta at every start date](<docs/figures/KeyBank National Association - Beta Backtest.png>)

*Figure 13: KeyBank National Association, long-run beta θ re-estimated at every start date from 2016Q1 (expanding window), with ±2 origin standard errors, the full-sample θ ±20% and the unrated window before 2020Q1 shaded, champion model.*

### 6.5 Manufacturers and Traders Trust Company (M&T)

#### 6.5.1 Data Treatment
- FDIC cert 588. Pro forma for Hudson City Savings Bank (2015-11-01, 24%) and People's United Bank (2022-04-02, 42%).

#### 6.5.2 Stationarity

| Sample (pro forma) | Levels I(0) | First difference I(1) |
| :--- | :--- | :--- |
| 2011Q1 to 2026Q2 (main) | ADF -2.098 (p 0.245), KPSS 0.528 (p 0.035): non-stationary | ADF -3.861 (p 0.0023), KPSS 0.127 (p ≥ 0.10): stationary |
| 2008Q1 to 2026Q2 | ADF -1.652 (p 0.456), KPSS 0.264 (p ≥ 0.10): inconclusive | ADF -4.758 (p 6.5e-05), KPSS 0.457 (p 0.053): stationary |

Default specification: ADF `c` / AIC and KPSS `c` / auto.

**Robustness** (share of the six re-specifications agreeing with the default, main sample): ADF I(0) 6/6, KPSS I(0) 2/6, ADF I(1) 6/6, KPSS I(1) 6/6.

**Conclusion (main sample):** **I(1)** under the default specification. Not flagged. 2008 to 2026 sample: flagged.

#### 6.5.3 Structural Breaks
Zivot-Andrews on levels, 2011 to 2026 (AIC lags, max 4): `c`: -6.42, p 3.9e-04, break 2022Q3; `t`: -4.09, p 0.111, break 2021Q2; `ct`: -4.91, p 0.079, break 2022Q3. The unit root is rejected when a 2022 level break is allowed, mirroring the break in FFT itself (OI-20).

#### 6.5.4 Cointegration
- **Baseline:** EG long run p 0.048 (pass); ARDL(2,1) case 3 F = 5.18 (p 0.034, pass); Johansen trace r ≤ 0 = 12.98 (p > 0.10).
- **Re-specification:** specifications that pass and reach estimation: EG long run `c`, `n`; ARDL cases 1, 3, 4, 5; Johansen `det_order` 1.
- **Gregory-Hansen** (one break, §5.3; 5% simulated critical values C −5.14, C/T −5.50, C/S −5.46, C/S/T −5.82): no rejection at 5%. ADF\* C −3.94 (2016Q1), C/T −4.49 (2024Q1), C/S −4.25 (2021Q4), C/S/T −4.78 (2023Q3).

#### 6.5.5 Specifications Estimated
22 one-step ECMs (11 ARDL, 6 EG, 5 Johansen). In-sample MAE 0.0383 to 0.0654. Long-run beta 0.342 to 0.432.

#### 6.5.6 Champion Model: ARDL(2,1), case 4 (unrestricted constant, restricted trend), AIC
The deterministic terms follow the case 4 test specification (§5.5).

| Term | Coefficient | *t* | p-value |
| :--- | :-: | :-: | :-: |
| const | 0.0556 | 2.38 | 0.021 |
| trend | -0.00202 | -2.44 | 0.018 |
| y.L1 (λ) | **-0.1835** | -3.91 | 2.6e-04 |
| FFT.L1 | 0.0792 | 4.06 | 1.6e-04 |
| D.y.L1 | 0.3335 | 3.81 | 3.6e-04 |
| D.FFT.L0 | 0.1385 | 5.74 | 4.4e-07 |
| LR: const | 0.3030 | 3.25 | 0.0020 |
| LR: trend | -0.0110 | -2.83 | 0.0065 |
| **LR: FFT (θ)** | **0.4316** | 10.25 | 2.9e-14 |

![Manufacturers and Traders Trust Company: actual vs. predicted deposit rate, champion model](<docs/figures/Manufacturers and Traders Trust Company - Actual vs Predicted.png>)

*Figure 14: Manufacturers and Traders Trust Company, actual vs. one-step ECM fitted deposit rate (`rate_pf_clean`), champion model. In-sample.*

#### 6.5.7 Outcomes Analysis and Issues
- **Governing MAE rating (many-start-date backtest, §5.6): Green**. h-step MAE, 1Q to 8Q, over 34 to 41 start dates: 0.059, 0.117, 0.170, 0.211, 0.261, 0.290, 0.304, 0.329 (mean 0.218). Worst skill ratio against the no-change forecast: 0.62 at 3Q.
- Single-window 8Q backtest (one start date per horizon, supplementary): 0.107, 0.043, 0.065, 0.029, 0.335, 0.115, 0.069, 0.104; mean 0.108, no-change mean 0.235, beats no-change on 6/8 horizons (Green).

![Manufacturers and Traders Trust Company: many-start-date backtest MAE by horizon](<docs/figures/Manufacturers and Traders Trust Company - MAE Backtest 8Q.png>)

*Figure 15: Manufacturers and Traders Trust Company, many-start-date backtest: h-step MAE by horizon over 34 to 41 start dates (n under each bar), with the no-change forecast and the 8Q band limits (§5.6), champion model.*

- The large single-window error at 5Q is one start date (2025Q1), where the model over-predicted the post-cut decline in deposit rates (OI-8). Over 37 start dates the 5-step-ahead MAE is 0.26 pp.
- The champion carries a long-run trend (-0.011 pp per quarter, p 0.0065), frozen at its 2026Q2 value for projection (§5.7).

- **Long-run beta stability (§5.6): Red.** From 2020Q1 to 2026Q1, θ ranges from 0.290 to 1.285 against the full-sample 0.432. The largest deviation is 198% (2023Q4) and at most 3.06 origin standard errors (2022Q3). Failing start dates: 3 (2020Q1 2022Q3 2022Q4). At 2023Q3–Q4, λ is about −0.02 and θ is unidentified (1.14 and 1.29, standard error 2.3); those start dates do not count as failures because their standard errors are wide. From 2024Q3, θ is 0.37–0.43. Over the last eight start dates (2024Q2–2026Q1) the range is 0.366–0.431.

![Manufacturers and Traders Trust Company: long-run beta at every start date](<docs/figures/Manufacturers and Traders Trust Company - Beta Backtest.png>)

*Figure 16: Manufacturers and Traders Trust Company, long-run beta θ re-estimated at every start date from 2016Q1 (expanding window), with ±2 origin standard errors, the full-sample θ ±20% and the unrated window before 2020Q1 shaded, champion model.*

### 6.6 Old National Bank

#### 6.6.1 Data Treatment
- FDIC cert 3832. Pro forma for 13 Mode A events since 2011, including Integra Bank (2011 failure, 28%), AnchorBank (2016, 21%), First Midwest (2022-02-16, 94%), CapStar (2024, 7%) and Bremer Bank (2025-05-01, 32%). Old National Trust Company (2014, no deposits) is Mode B.
- The 2025Q2 drop in the earlier build was a data artifact (unadjusted Bremer merger plus calendar-year deposit averaging) and is fixed.

#### 6.6.2 Stationarity

| Sample (pro forma) | Levels I(0) | First difference I(1) |
| :--- | :--- | :--- |
| 2011Q1 to 2026Q2 (main) | ADF -1.401 (p 0.582), KPSS 0.549 (p 0.031): non-stationary | ADF -3.779 (p 0.0031), KPSS 0.194 (p ≥ 0.10): stationary |
| 2008Q1 to 2026Q2 | ADF -2.236 (p 0.194), KPSS 0.274 (p ≥ 0.10): inconclusive | ADF -2.878 (p 0.048), KPSS 0.551 (p 0.030): inconclusive |

Default specification: ADF `c` / AIC and KPSS `c` / auto.

**Robustness** (share of the six re-specifications agreeing with the default, main sample): ADF I(0) 6/6, KPSS I(0) 2/6, ADF I(1) 6/6, KPSS I(1) 6/6.

**Conclusion (main sample):** **I(1)** under the default specification. Not flagged. 2008 to 2026 sample: flagged.

#### 6.6.3 Structural Breaks
Zivot-Andrews on levels, 2011 to 2026 (AIC lags, max 4): `c`: -6.21, p 6.1e-04, break 2022Q3; `t`: -4.31, p 0.065, break 2022Q1; `ct`: -4.26, p 0.335, break 2019Q3. The unit root is rejected when a 2022 level break is allowed, mirroring the break in FFT itself (OI-20).

#### 6.6.4 Cointegration
- **Baseline:** none pass at 5%. EG long run p 0.379; Johansen trace r ≤ 0 = 15.49 (p < 0.10); ARDL(4,4) case 3 F = 2.85 (p 0.302).
- **Re-specification** (now run, OI-4): EG long run `n` / BIC (p 0.0077); Johansen `det_order -1`, k_ar_diff = 1 (r ≤ 0 = 13.91, p < 0.05).
- **Gregory-Hansen** (one break, §5.3; 5% simulated critical values C −5.14, C/T −5.50, C/S −5.46, C/S/T −5.82): no rejection at 5%. ADF\* C −3.85 (2024Q1), C/T −4.60 (2024Q1), C/S −4.01 (2021Q3), C/S/T −4.53 (2024Q1).

#### 6.6.5 Specifications Estimated
2 one-step ECMs (1 EG, 1 Johansen). In-sample MAE 0.0285 to 0.0414. Long-run beta 0.394 to 0.419.

#### 6.6.6 Champion Model: Engle-Granger long run, trend `n`, BIC (ADF lag=1, ECM lag=3)
EG ADF t −3.43 (p 0.008). Short-run candidates come from the Engle-Granger second-step regression (OI-24). The Johansen VECM (det_order −1, k_ar_diff 1), the champion before OI-24, now has the higher in-sample MAE (0.0414).

| Term | Coefficient | *t* | p-value |
| :--- | :-: | :-: | :-: |
| y.L1 (λ) | **-0.0856** | -2.67 | 0.010 |
| FFT.L1 | 0.0337 | 2.51 | 0.015 |
| D.y.L1 | 0.7163 | 6.65 | 2.1e-08 |
| D.y.L2 | -0.7376 | -5.73 | 5.8e-07 |
| D.y.L3 | 0.4607 | 5.05 | 6.3e-06 |
| D.FFT.L0 | 0.1388 | 5.99 | 2.3e-07 |
| D.FFT.L1 | -0.0956 | -2.68 | 0.0099 |
| D.FFT.L2 | 0.1374 | 4.13 | 1.4e-04 |
| **LR: FFT (θ)** | **0.3937** | 11.11 | 4.1e-15 |

![Old National Bank: actual vs. predicted deposit rate, champion model](<docs/figures/Old National Bank - Actual vs Predicted.png>)

*Figure 17: Old National Bank, actual vs. one-step ECM fitted deposit rate (`rate_pf_clean`), champion model. In-sample.*

#### 6.6.7 Outcomes Analysis and Issues
- **Governing MAE rating (many-start-date backtest, §5.6): Green**. h-step MAE, 1Q to 8Q, over 34 to 41 start dates: 0.047, 0.117, 0.179, 0.225, 0.286, 0.349, 0.382, 0.405 (mean 0.249). Worst skill ratio against the no-change forecast: 0.65 at 6Q.
- Single-window 8Q backtest (one start date per horizon, supplementary): 0.005, 0.082, 0.067, 0.048, 0.363, 0.213, 0.271, 0.149; mean 0.150, no-change mean 0.207, beats no-change on 7/8 horizons (Green).

![Old National Bank: many-start-date backtest MAE by horizon](<docs/figures/Old National Bank - MAE Backtest 8Q.png>)

*Figure 18: Old National Bank, many-start-date backtest: h-step MAE by horizon over 34 to 41 start dates (n under each bar), with the no-change forecast and the 8Q band limits (§5.6), champion model.*

- The champion changed with OI-24, from the Johansen VECM (mean h-step MAE 0.263) to EG long run `n`, BIC (0.249). Both are Green.
- The large single-window error at 5Q (start date 2025Q1, 0.363) is unchanged and remains the shared easing-cycle effect (OI-8, OI-25).

- **Long-run beta stability (§5.6): Green.** From 2020Q1 to 2026Q1, θ ranges from -0.100 to 0.575 against the full-sample 0.394. The largest deviation is 125% (2020Q2) and at most 1.80 origin standard errors (2023Q1). Failing start dates: none. θ is about 0.34 from 2020Q3 to 2022Q1 and 0.28–0.32 from 2022Q3 to 2023Q1, then 0.38–0.49. The extreme values at 2020Q2 (−0.10, standard error 1.06) and 2023Q3 (0.575, standard error 0.28) are imprecise. With the previous champion the rating was Amber (2020Q1 failed). Over the last eight start dates (2024Q2–2026Q1) the range is 0.300–0.493.

![Old National Bank: long-run beta at every start date](<docs/figures/Old National Bank - Beta Backtest.png>)

*Figure 19: Old National Bank, long-run beta θ re-estimated at every start date from 2016Q1 (expanding window), with ±2 origin standard errors, the full-sample θ ±20% and the unrated window before 2020Q1 shaded, champion model.*

### 6.7 SouthState Bank

#### 6.7.1 Data Treatment
- FDIC cert 33555, the former CenterState Bank charter. Pro forma for 19 Mode A events since 2011, including South State Bank (cert 13425, 2020-06-08, 88%; previously mislabelled as CenterState, Mode B, 0.5%), Atlantic Capital (2022-03-01, 9%) and Independent Bank (2025-01-01, 40%).

#### 6.7.2 Stationarity

| Sample (pro forma) | Levels I(0) | First difference I(1) |
| :--- | :--- | :--- |
| 2011Q1 to 2026Q2 (main) | ADF -2.033 (p 0.272), KPSS 0.517 (p 0.038): non-stationary | ADF -3.725 (p 0.0038), KPSS 0.207 (p ≥ 0.10): stationary |
| 2008Q1 to 2026Q2 | ADF -1.810 (p 0.375), KPSS 0.278 (p ≥ 0.10): inconclusive | ADF -3.452 (p 0.0093), KPSS 0.593 (p 0.023): inconclusive |

Default specification: ADF `c` / AIC and KPSS `c` / auto.

**Robustness** (share of the six re-specifications agreeing with the default, main sample): ADF I(0) 6/6, KPSS I(0) 2/6, ADF I(1) 5/6, KPSS I(1) 6/6.

**Conclusion (main sample):** **I(1)** under the default specification. Not flagged. 2008 to 2026 sample: flagged.

#### 6.7.3 Structural Breaks
Zivot-Andrews on levels, 2011 to 2026 (AIC lags, max 4): `c`: -6.23, p 5.8e-04, break 2022Q3; `t`: -4.43, p 0.048, break 2021Q3; `ct`: -5.21, p 0.035, break 2022Q4. The unit root is rejected when a 2022 level break is allowed, mirroring the break in FFT itself (OI-20).

#### 6.7.4 Cointegration
- **Baseline:** EG long run p 0.312; Johansen trace r ≤ 0 = 14.06 (p < 0.10); ARDL(4,3) case 3 F = 3.50 (p 0.174).
- **Re-specification:** specifications that pass and reach estimation: Johansen `det_order` -1, 0; ARDL cases 1, 4, 5.
- **Gregory-Hansen** (one break, §5.3; 5% simulated critical values C −5.14, C/T −5.50, C/S −5.46, C/S/T −5.82): no rejection at 5%. ADF\* C −3.82 (2024Q1), C/T −4.41 (2024Q1), C/S −3.87 (2024Q1), C/S/T −4.37 (2024Q1).

#### 6.7.5 Specifications Estimated
7 one-step ECMs (5 ARDL, 2 Johansen). In-sample MAE 0.0336 to 0.0437. Long-run beta 0.424 to 0.524.

#### 6.7.6 Champion Model: ARDL(4,3), case 1 (no deterministic terms), AIC
No deterministic terms (case 1).

| Term | Coefficient | *t* | p-value |
| :--- | :-: | :-: | :-: |
| y.L1 (λ) | **-0.0816** | -2.72 | 0.0090 |
| FFT.L1 | 0.0361 | 2.78 | 0.0076 |
| D.y.L1 | 0.7917 | 5.85 | 3.8e-07 |
| D.y.L2 | -0.6669 | -4.04 | 1.8e-04 |
| D.y.L3 | 0.2762 | 2.72 | 0.0090 |
| D.FFT.L0 | 0.1849 | 6.83 | 1.1e-08 |
| D.FFT.L1 | -0.1443 | -3.13 | 0.0029 |
| D.FFT.L2 | 0.1447 | 3.54 | 8.6e-04 |
| **LR: FFT (θ)** | **0.4428** | 11.20 | 3.1e-15 |

![SouthState Bank: actual vs. predicted deposit rate, champion model](<docs/figures/SouthState Bank - Actual vs Predicted.png>)

*Figure 20: SouthState Bank, actual vs. one-step ECM fitted deposit rate (`rate_pf_clean`), champion model. In-sample.*

#### 6.7.7 Outcomes Analysis and Issues
- **Governing MAE rating (many-start-date backtest, §5.6): Green**. h-step MAE, 1Q to 8Q, over 34 to 41 start dates: 0.061, 0.134, 0.202, 0.262, 0.312, 0.355, 0.384, 0.406 (mean 0.264). Worst skill ratio against the no-change forecast: 0.70 at 3Q.
- Single-window 8Q backtest (one start date per horizon, supplementary): 0.077, 0.091, 0.057, 0.124, 0.392, 0.126, 0.314, 0.129; mean 0.164, no-change mean 0.182, beats no-change on 5/8 horizons (Amber).

![SouthState Bank: many-start-date backtest MAE by horizon](<docs/figures/SouthState Bank - MAE Backtest 8Q.png>)

*Figure 21: SouthState Bank, many-start-date backtest: h-step MAE by horizon over 34 to 41 start dates (n under each bar), with the no-change forecast and the 8Q band limits (§5.6), champion model.*

- λ = -0.08 is the slowest adjustment in the peer set.
- Shares the easing-cycle error at the 2025Q1 start date (OI-8, OI-25).

- **Long-run beta stability (§5.6): Green.** From 2020Q1 to 2026Q1, θ ranges from -0.009 to 0.524 against the full-sample 0.443. The largest deviation is 102% (2020Q2) and at most 1.27 origin standard errors (2025Q1). Failing start dates: none. The low values at 2020Q2–Q3 (λ −0.02 to −0.04, standard error up to 0.93) and the 2025Q1 dip (0.330, 1.27 SE) are imprecise rather than significant. Over the last eight start dates (2024Q2–2026Q1) the range is 0.330–0.524.

![SouthState Bank: long-run beta at every start date](<docs/figures/SouthState Bank - Beta Backtest.png>)

*Figure 22: SouthState Bank, long-run beta θ re-estimated at every start date from 2016Q1 (expanding window), with ±2 origin standard errors, the full-sample θ ±20% and the unrated window before 2020Q1 shaded, champion model.*

---

## 7. Outcomes Analysis: Peer Comparison

### 7.1 Many-Start-Date Backtest (governing; h-step MAE, pp)
Start dates every quarter from 2016Q1, expanding estimation window, dynamic forecasts with realized FFT. Each h-step figure averages 34 (8Q) to 41 (1Q) start dates.

| Bank | 1Q | 2Q | 3Q | 4Q | 5Q | 6Q | 7Q | 8Q | Mean | No-change mean | Worst skill ratio | Rating |
| :--- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| First Horizon Bank | 0.100 | 0.179 | 0.227 | 0.239 | 0.283 | 0.308 | 0.312 | 0.292 | 0.242 | 0.539 | 0.71 | **Red** |
| Glacier Bank | 0.047 | 0.103 | 0.156 | 0.195 | 0.238 | 0.277 | 0.306 | 0.331 | 0.207 | 0.235 | 0.96 | **Amber** |
| Huntington National Bank | 0.042 | 0.097 | 0.148 | 0.199 | 0.255 | 0.307 | 0.339 | 0.381 | 0.221 | 0.467 | 0.49 | **Green** |
| KeyBank National Association | 0.054 | 0.115 | 0.172 | 0.224 | 0.294 | 0.384 | 0.464 | 0.533 | 0.280 | 0.448 | 0.71 | **Red** |
| Manufacturers and Traders Trust Company | 0.059 | 0.117 | 0.170 | 0.211 | 0.261 | 0.290 | 0.304 | 0.329 | 0.218 | 0.394 | 0.62 | **Green** |
| Old National Bank | 0.047 | 0.117 | 0.179 | 0.225 | 0.286 | 0.349 | 0.382 | 0.405 | 0.249 | 0.404 | 0.65 | **Green** |
| SouthState Bank | 0.061 | 0.134 | 0.202 | 0.262 | 0.312 | 0.355 | 0.384 | 0.406 | 0.264 | 0.413 | 0.70 | **Green** |

Band limits for N = 8, derived from this run (§5.6):

| Band | Green limit (band average) | Red limit (band maximum) |
| :-: | :-: | :-: |
| 1-2Q | 0.10 | 0.15 |
| 3-4Q | 0.25 | 0.30 |
| 5-8Q | 0.40 | 0.45 |

First Horizon is Red on the 1–2Q band (2Q 0.179 > red 0.15), and KeyBank on the 5–8Q band (8Q 0.533 > red 0.45). First Horizon's errors are unchanged from the previous run, where the 1–2Q limits were 0.15/0.20 and it was Green. The limits tightened because the re-specified Huntington and Old National champions have lower short-horizon errors (OI-24). This is the peer-relative effect noted in §5.6 ([#8](https://github.com/Panda5130/Deposit-Beta/issues/8)).

### 7.2 Single-Window 8Q Backtest (supplementary; MAE, pp)
Each column is one forecast window, starting at T−k and ending at 2026Q2, with MAE averaged over its k quarters. Each column therefore rests on a single start date, and the windows overlap.

| Bank | 1Q | 2Q | 3Q | 4Q | 5Q | 6Q | 7Q | 8Q | Mean | No-change mean | Rating |
| :--- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| First Horizon Bank | 0.094 | 0.044 | 0.030 | 0.067 | 0.096 | 0.086 | 0.177 | 0.103 | 0.087 | 0.307 | Green |
| Glacier Bank | 0.094 | 0.031 | 0.021 | 0.017 | 0.116 | 0.172 | 0.150 | 0.040 | 0.080 | 0.119 | Amber |
| Huntington National Bank | 0.094 | 0.132 | 0.069 | 0.049 | 0.187 | 0.287 | 0.169 | 0.214 | 0.150 | 0.231 | Amber |
| KeyBank National Association | 0.075 | 0.026 | 0.184 | 0.060 | 0.121 | 0.171 | 0.358 | 0.123 | 0.140 | 0.272 | Green |
| Manufacturers and Traders Trust Company | 0.107 | 0.043 | 0.065 | 0.029 | 0.335 | 0.115 | 0.069 | 0.104 | 0.108 | 0.235 | Green |
| Old National Bank | 0.005 | 0.082 | 0.067 | 0.048 | 0.363 | 0.213 | 0.271 | 0.149 | 0.150 | 0.207 | Green |
| SouthState Bank | 0.077 | 0.091 | 0.057 | 0.124 | 0.392 | 0.126 | 0.314 | 0.129 | 0.164 | 0.182 | Amber |

### 7.3 Observations
- Over 34 to 41 start dates per horizon, h-step errors rise smoothly from 0.04 to 0.10 pp at 1Q to 0.29 to 0.53 pp at 8Q, and every champion beats the no-change forecast at every horizon.
- Governing MAE ratings: Huntington, M&T, Old National and SouthState Green; Glacier Amber (skill ratio 0.96 at 3Q); First Horizon and KeyBank Red (above the peer-derived red limit).
- M&T, SouthState, Old National and now Huntington share a large error in the single window starting 2025Q1 (the "5Q" column of §7.2). 63% to 72% of the champions' forecast fall from that date comes from lagged-Δy (momentum) terms extrapolating the sharp 2025Q1 drop, not from error correction (OI-8, OI-25). Over 37 start dates the 5-step error is 0.26 to 0.31 pp for these banks.
- In-sample MAE is 0.022 to 0.047 and out-of-sample errors are several times larger.
- Long-run betas range from 0.35 (Glacier) to 0.52 (First Horizon); the other five lie between 0.39 and 0.46.

### 7.4 Benchmarking
The no-change forecast is the benchmark in both backtests. Seven challengers are scored on the governing many-start-date backtest: the champions' start dates (2016Q1 onward, expanding window), h = 1 to 8, against the champions' band limits and the skill test (`model_form/`). The challengers are:

- an asymmetric ECM with separate λ for positive and negative disequilibrium (a1), and one with λ split by FFT direction (a2), each with a symmetric two-step control (a0);
- a static OLS beta in levels (b1) and applied to the FFT change (b2), and cycle-specific betas (b3);
- each champion with a 2022Q3 level dummy (c).

| Bank | Champion | a1 asymmetric λ | a2 λ by FFT direction | b2 static beta | b3 cycle betas | c 2022 dummy |
| :--- | :-: | :-: | :-: | :-: | :-: | :-: |
| First Horizon Bank | 0.242 Red | 0.302 Red | 0.498 Red | 0.389 Red | 0.378 Red | 0.318 Red |
| Glacier Bank | 0.207 Amber | 0.261 Red | 0.219 Amber | 0.265 Red | 0.204 Amber | 0.221 Amber |
| Huntington National Bank | 0.221 Green | 0.214 Green | 0.206 Green | 0.348 Red | 0.311 Red | 0.245 Green |
| KeyBank National Association | 0.280 Red | 0.301 Red | 0.292 Red | 0.344 Red | 0.319 Red | 0.302 Red |
| Manufacturers and Traders Trust Company | 0.218 Green | 0.220 Green | 0.211 Green | 0.337 Red | 0.285 Red | 0.214 Green |
| Old National Bank | 0.249 Green | 0.247 Green | 0.272 Red | 0.375 Red | 0.313 Red | 0.296 Red |
| SouthState Bank | 0.264 Green | 0.250 Green | 0.273 Red | 0.408 Red | 0.333 Red | 0.297 Red |

*Mean h-step MAE over 1Q to 8Q (pp) and rating against the champions' band limits. The static levels beta (b1) is Red for every bank (mean 0.375 to 0.518).*

No challenger beats the champions across the peer group.

- **Asymmetric λ (a1).** Downward adjustment is slower than upward for six of seven banks, but against the current champions the difference is significant only at the 10% level for SouthState (Wald p 0.077); Huntington (p 0.11) and Old National (0.18) are no longer significant after OI-24. a1 is marginally better for Huntington, Old National and SouthState and worse for First Horizon, Glacier and KeyBank.
- **Static and cycle betas.** They have no lag structure, overshoot during hiking, and are Red or Amber everywhere.
- **The 2022 dummy.** It is identified from at most 14 post-break quarters and worsens six of seven banks (M&T is about equal).
- **The 2025Q1 start date (OI-8).** No ECM challenger removes the shared error. The cause is the lagged-Δy momentum terms (OI-25).

Details are in `docs/resolutions/model_form.md`; the tables above use the rerun against the current champions.

### 7.5 Long-Run Beta Stability (start dates from 2016Q1)
Each champion is re-estimated at every start date from 2016Q1 to 2026Q1 (expanding window), and θ is compared with the full-sample estimate through 2026Q2 (`Beta_Backtesting/run_beta_backtest.py --first-origin 2016Q1`). Ratings use the start dates from 2020Q1 (§5.6).

| Bank | Full-sample θ | θ range, 2020Q1–2026Q1 | Largest deviation (share), start date | Largest deviation in SEs, start date | Failing start dates | Rating |
| :--- | :-: | :-: | :-: | :-: | :-: | :-: |
| First Horizon Bank | 0.517 | 0.437 to 0.596 | 15%, 2023Q3 | 1.57, 2023Q4 | 0 | **Green** |
| Glacier Bank | 0.346 | 0.110 to 0.383 | 68%, 2020Q1 | 11.37, 2022Q4 | 14 | **Red** |
| Huntington National Bank | 0.463 | 0.243 to 0.553 | 47%, 2020Q2 | 1.29, 2022Q4 | 0 | **Green** |
| KeyBank National Association | 0.398 | 0.275 to 0.532 | 34%, 2024Q3 | 1.29, 2022Q3 | 0 | **Green** |
| Manufacturers and Traders Trust Company | 0.432 | 0.290 to 1.285 | 198%, 2023Q4 | 3.06, 2022Q3 | 3 | **Red** |
| Old National Bank | 0.394 | -0.100 to 0.575 | 125%, 2020Q2 | 1.80, 2023Q1 | 0 | **Green** |
| SouthState Bank | 0.443 | -0.009 to 0.524 | 102%, 2020Q2 | 1.27, 2025Q1 | 0 | **Green** |

![All banks: long-run beta re-estimated at every start date](<docs/figures/All Banks - Beta Backtest.png>)

*Figure 23: Long-run beta θ re-estimated at every start date from 2016Q1, all banks.*

- Before 2020, θ is poorly identified for every bank: those samples are mostly zero-lower-bound data, with wide standard errors.
- Glacier's beta is the least stable: 0.11–0.14 with tight standard errors until the 2022–23 hiking cycle enters the sample. M&T fails at 2020Q1 and 2022Q3–Q4.
- The re-specified Huntington and Old National champions are Green; both were Amber with their previous champions.
- Over the last eight start dates (2024Q2–2026Q1), most banks dip at the 2024Q4 and 2025Q1 start dates, at the turn of the easing cycle (OI-8). The 8-start-date charts are in `Beta_Backtesting/output/<bank>/beta_backtest_8Q.png`.

### 7.6 Out-of-Sample Model Choice (optional rule, not adopted)

| Bank | Model | Params | In-sample MAE | Many-start-date mean MAE (SE) | θ | MAE rating | Beta rating |
| :--- | :--- | :-: | :-: | :-: | :-: | :-: | :-: |
| First Horizon Bank | Champion: ARDL(3,4), case 4, AIC | 9 | 0.0469 | 0.242 (0.039) | 0.517 | Red | Green |
| | Pick: Johansen VECM, k_ar_diff = 1, det_order -1, BIC | 3 | 0.0720 | 0.284 (0.059) | 0.477 | Green | Green |
| Glacier Bank | Champion: ARDL(3,1), case 4, BIC | 7 | 0.0292 | 0.207 (0.079) | 0.346 | Amber | Red |
| | Pick: Johansen VECM, k_ar_diff = 1, det_order 1, BIC | 5 | 0.0310 | 0.263 (0.087) | 0.277 | Red | Red |
| Huntington National Bank | Champion = pick: EG long run, `n`, AIC (ADF lag=1, ECM lag=3) | 8 | 0.0234 | 0.221 (0.040) | 0.463 | Green | Green |
| KeyBank National Association | Champion: EG long run, `n`, BIC (ADF lag=1, ECM lag=3) | 7 | 0.0317 | 0.280 (0.062) | 0.398 | Red | Green |
| | Pick: ARDL(2,1), case 1, BIC | 4 | 0.0343 | 0.189 (0.041) | 0.412 | Green | Green |
| Manufacturers and Traders Trust Company | Champion: ARDL(2,1), case 4, AIC | 6 | 0.0383 | 0.218 (0.068) | 0.432 | Green | Red |
| | Pick: EG long run, `n`, AIC (ADF lag=1, ECM lag=4) | 3 | 0.0499 | 0.275 (0.059) | 0.402 | Green | Red |
| Old National Bank | Champion: EG long run, `n`, BIC (ADF lag=1, ECM lag=3) | 8 | 0.0285 | 0.249 (0.048) | 0.394 | Green | Green |
| | Pick: Johansen VECM, k_ar_diff = 1, det_order -1, fixed | 4 | 0.0414 | 0.263 (0.065) | 0.419 | Green | Amber |
| SouthState Bank | Champion: ARDL(4,3), case 1, AIC | 8 | 0.0336 | 0.264 (0.039) | 0.443 | Green | Green |
| | Pick: ARDL(3,2), case 4, BIC | 8 | 0.0347 | 0.197 (0.039) | 0.524 | Green | Red |

Source: `MAE_Backtesting/output/out_of_sample/selection_comparison_8Q.csv`. The picks' MAE ratings use the picks' own peer limits.

- The rule (§5.5 step 6) changes the model for six of seven banks; Huntington is unchanged.
- The one-standard-error band is wide (0.04–0.08 against scores of 0.19–0.33), so the rule leans heavily on parsimony.
- The effects are mixed: KeyBank's MAE improves from Red to Green; First Horizon gives up accuracy for 3 parameters instead of 9; SouthState gains on MAE but its beta turns Red; Glacier's pick is Red on MAE; M&T's pick has fewer parameters but a higher MAE and is still Red on beta; Old National's pick is its previous Johansen champion (beta Amber).
- Selecting on the governing backtest makes that backtest optimistic for the selected model. Adoption is deferred to the validator (OI-9, [#1](https://github.com/Panda5130/Deposit-Beta/issues/1)).

---

## 8. Model Limitations and Assumptions

| # | Limitation | Affected banks | Impact |
| :-: | :--- | :--- | :--- |
| L1 | Short sample (62 quarters, 2011Q1 to 2026Q2) lowers the power of unit-root and cointegration tests | All | High |
| L2 | Stationarity classification depends on the specification. Glacier remains flagged (KPSS I(0) p 0.057). All series reject a unit root once a 2022 level break is allowed, but the break is common to FFT and cancels in the cointegrating relation: Gregory-Hansen finds no break in the relationship (§5.3). | All, esp. Glacier | Medium |
| L3 | Results are not robust to the 2008 to 2026 sample: six banks are inconclusive on levels and First Horizon looks I(0) (Appendix A.2) | All | Medium |
| L4 | Pro forma merger adjustment assumes the combined franchise priced like the sum of its parts before the merger; merger-quarter interest is pro-rated by days; predecessors without FDIC Call Reports (none so far) would be skipped | All | Low to medium |
| L5 | The deposit rate is deposit interest expense over total deposits: a total-deposit (not interest-bearing-deposit) beta that does not separate product mix | All | Low |
| L6 | Linear, symmetric pass-through. Downward adjustment is slower than upward for six of seven banks, though against the current champions only SouthState is significant (10%). An asymmetric-λ challenger does not improve the peer set (§7.4). The 2025Q1 start-date error comes mainly from short-run momentum terms extrapolating the 2025Q1 fall, which asymmetric λ does not address (OI-8, OI-25). | All | High |
| L7 | Post-selection inference: short-run terms screened and pruned on p < 0.05, so p-values are optimistic | All | Medium |
| L8 | Champion chosen on in-sample MAE, and several specifications collapse to the same ECM. An optional out-of-sample rule (§5.5 step 6) would change six of seven models with mixed effects. It is not adopted (OI-9), and selecting on the backtest would bias that backtest. | All | Medium |
| L9 | Johansen p-values are bounds; r ≤ 1 rejections (implying rank 2) are overridden by assuming rank 1 | Glacier, Huntington, First Horizon | Medium |
| L10 | Single regressor (FFT). No competitive, liquidity or balance-sheet drivers | All | Medium |
| L11 | Cointegration with one unknown break (Gregory-Hansen, four forms) does not reject at 5% for any bank on ADF\* (finite-sample critical values, T = 62). With 62 quarters the test has low power, and two or more breaks are not tested. | All | Low |
| L12 | Glacier's champion keeps an insignificant constant and trend because its case 4 test requires them | Glacier | Low |
| L13 | KPSS p-values are truncated at 0.10 | All | Low |
| L14 | Deterministic trends in the First Horizon, M&T and Glacier champions (δ = −0.011, −0.011 and −0.008 pp per quarter) are frozen at their 2026Q2 value for projection (`projection/project.py`). The freeze is a judgment overlay, not an estimated feature: the estimated model would keep lowering these banks' equilibrium by \|δ\| each quarter (0.04 to 0.07 pp over 8Q, 0.30 to 0.41 pp over 40Q at flat FFT). Projections for these banks depend on that choice. | First Horizon, M&T, Glacier | Medium |
| L15 | Huntington cointegration rests on one specification family (EG long run, no deterministic terms) and on post-2022 data: the test fails in every window ending in 2019Q4 and in 2021Q4 windows starting in 2013 or later. GH finds no break. Kept in scope with this caveat (decision 2026-10-31). The re-specified champion (short-run terms added, OI-24) is Green, but its λ is small (−0.066). | Huntington | High |
| L16 | Backtest limits are percentiles of the peer group, so the absolute test is a relative standard: one bank's re-specification can change another's rating (First Horizon turned Red after OI-24 with unchanged errors). The single-window backtest has one start date per horizon. | All | Medium |
| L17 | Beta stability is rated only from 2020Q1, because earlier samples are mostly zero-lower-bound data. The joint 2-SE-and-20% test does not flag large moves with wide standard errors (for example M&T at 2023Q3–Q4). Glacier and M&T are rated Red. | All, esp. Glacier, M&T | Medium |

---

## 9. Validation Status and Open Issues

### 9.1 Validation Status
No independent validation has been performed. The items below should be resolved before the model is submitted for validation.

### 9.2 Open Issues Log
Items still open are tracked as GitHub issues on `Panda5130/Deposit-Beta`, linked in the Status column.

| ID | Issue | Bank(s) | Priority | Status |
| :-: | :--- | :--- | :-: | :--- |
| OI-1 | Replace placeholder predecessor certs and deposits with actual FDIC values; re-derive materiality | All with events | High | Closed: real certs and deposits from FDIC (`merger_events_used.csv`) |
| OI-2 | Apply the missing Mode A adjustments | All with events | High | Closed: every ≥ 1% event since 2007 applied as pro forma backfill |
| OI-3 | Decide on Mode B treatment | Glacier, KeyBank, Old National | Medium | Closed: Mode B rows kept (3 events, all < 1%) |
| OI-4 | Run the cointegration re-specification grid for Huntington and Old National | Huntington, Old National | Medium | Closed: the grid runs all seven banks |
| OI-5 | Fix Zivot-Andrews failures and extend the break tests to all banks | All | Medium | Closed: runs for all banks; see OI-20 |
| OI-6 | Refit models with insignificant short-run terms | Huntington, all | Medium | Closed: short-run lags pruned in the one-step ECM |
| OI-7 | Reconcile the deterministic terms between the cointegration test and the estimated ECM | Glacier, M&T, KeyBank, SouthState | Medium | Closed: deterministic terms follow the test specification |
| OI-8 | Investigate the shared error at the 2025Q1 start date, including Old National's 2025Q2 drop | M&T, Old National, SouthState, Huntington | Medium | Partially closed: the data artifact is fixed. Asymmetric λ does not remove the error (§7.4). The cause is lagged-Δy momentum extrapolating the 2025Q1 fall (`model_form/output/oi8_decomposition_2025Q1.csv`); carried to OI-25. |
| OI-9 | Select the champion on out-of-sample backtest MAE (or a combination), not in-sample MAE | All | Medium | Partially closed: optional rule implemented (`run_backtest.py --select out-of-sample`) with a side-by-side comparison (§7.6). In-sample MAE retained as the default; adoption deferred to the validator ([#1](https://github.com/Panda5130/Deposit-Beta/issues/1)) |
| OI-10 | Define acceptance thresholds for backtest MAE | All | Medium | Closed: superseded for the governing rating by OI-22; single-window ratings kept as a supplementary view |
| OI-11 | Build benchmark/challenger models (static beta, asymmetric ECM, 2022 regime dummy) | All | High | Closed: seven challengers scored on the many-start-date backtest (§7.4, `model_form/`). None replaces the champions peer-wide ([#2](https://github.com/Panda5130/Deposit-Beta/issues/2)) |
| OI-12 | Rerun or archive the stale KeyBank 4Q backtest | KeyBank | Low | Closed: deleted |
| OI-13 | Investigate the Glacier 2012Q1 dip and 2012Q2 spike | Glacier | Medium | Closed: rate rebuilt from quarterly fields with a two-point deposit average |
| OI-14 | Assess whether long-run trends are economically justified for projection | First Horizon, M&T, Glacier | Medium | Closed: trend kept for estimation; frozen at its end-of-sample value in projection, implemented and tested in `projection/project.py` (L14, [#7](https://github.com/Panda5130/Deposit-Beta/issues/7)) |
| OI-15 | Isolate deposit interest expense from total interest expense | All | Medium | Closed: deposit interest expense only |
| OI-16 | Fill the empty "ADF re-specification" placeholders in the vault documentation (2008 to 2026 merger-adjusted) | All | Low | Closed: filled from `diagnostics/unit_root_grid.csv` on 2026-10-31 ([#3](https://github.com/Panda5130/Deposit-Beta/issues/3)) |
| OI-17 | Regenerate Figure 1 from the modeled dataset | All | Low | Closed: regenerated from `EDA1_Stationarity_Tests.ipynb`, 2011Q1 to 2026Q2 |
| OI-18 | Update Appendix A with the rebuilt unit-root results | All | Medium | Closed: Appendix A regenerated from `diagnostics/` |
| OI-19 | Huntington cointegration rests on a single specification family; assess robustness and whether Huntington stays in scope | Huntington | High | Closed (decision 2026-10-31): kept in scope with a caveat (L15). The champion is re-specified through OI-24 and rates Green on MAE (0.221 vs. 0.334) and on beta stability ([#4](https://github.com/Panda5130/Deposit-Beta/issues/4)) |
| OI-20 | Zivot-Andrews rejects a unit root with a 2022 level break for all banks and for FFT; test cointegration allowing a break (Gregory-Hansen) | All | Medium | Closed: Gregory-Hansen finds no break-cointegration at 5% for any bank on ADF\* (one Zt\* rejection, Glacier C/T). A 2022 level dummy does not improve forecasts (§5.3, §7.4) ([#5](https://github.com/Panda5130/Deposit-Beta/issues/5)) |
| OI-21 | FFT input carried 2026Q3 and 2026Q4 at 3.67 by hand, and 2026Q4 was not complete | All | Low | Closed: `data_build/build_fft.py` builds FFT from FRED `FEDFUNDS` with complete quarters only; history through 2026Q2 is reproduced exactly; 2026Q3 is the true average (3.67); 2026Q4 is dropped ([#6](https://github.com/Panda5130/Deposit-Beta/issues/6)) |
| OI-22 | The single-window backtest has one start date per horizon | All | Medium | Closed: many-start-date backtest with horizon-aware, peer-derived limits and a skill test; validator to confirm the relative-limit design; fixed reference-run limits are on hold ([#8](https://github.com/Panda5130/Deposit-Beta/issues/8)) |
| OI-23 | Set an acceptance threshold for long-run beta stability and extend the start dates back to 2016Q1 | All | Medium | Closed: start dates from 2016Q1; rating on start dates from 2020Q1 (fail = >2 SE and >20%; Amber 1–2, Red 3+ or any >3 SE). Glacier and M&T Red, all others Green. The validator should confirm the threshold ([#10](https://github.com/Panda5130/Deposit-Beta/issues/10)) |
| OI-24 | EG long-run specifications entered the one-step ECM with no short-run terms, so their D.FFT and D.y lags were never screened | Huntington, Old National, KeyBank | High | Closed: `ECM model selection.py` gives each passing EG long-run spec the D.* lags of its own EG second-step regression (§5.5). Champions change for Huntington (Red → Green) and Old National (Johansen → EG, Green); KeyBank's label changes (identical regression). The tighter peer 1–2Q limits turn First Horizon Red (§7.1) |
| OI-25 | Damp, or make asymmetric, the short-run lagged-Δy dynamics so a sharp one-quarter fall is not extrapolated once FFT is flat | M&T, Old National, SouthState, Huntington | Medium | Open (from OI-8) |

---

## 10. Implementation and Reproducibility

### 10.1 Environment
Python with `pandas`, `numpy`, `statsmodels` (ADF, KPSS, `coint_johansen`, `VECM`, `ARDL`/`UECM`, `mackinnonp`), `scipy` and `matplotlib`. `data_build/build_dataset.py` replaces the data-pull and merger-adjustment notebooks; `EDA1_Stationarity_Tests.ipynb` produces Figure 1. Package versions are not pinned yet; a `requirements.txt` should be added.

### 10.2 Execution

```bash
python data_build/build_dataset.py
```

```bash
python data_build/build_fft.py
```

```bash
python "Co-integration Tests.py" consolidated_fdic_quarterly_financials_2011-2026_merger_adjusted.csv FFT_2011-2026.csv test_params.csv
```

```bash
python FlaggedRates_co-integration_respecification.py
```

```bash
python "ECM workflow.py"
```

```bash
python MAE_Backtesting/run_backtest.py --horizon 8Q --bank-name All --first-origin 2016Q1
```

```bash
python Beta_Backtesting/run_beta_backtest.py --horizon 8Q --bank-name All
```

```bash
python Beta_Backtesting/run_beta_backtest.py --first-origin 2016Q1
```

```bash
python model_form/run_model_form.py
```

```bash
python plotting_workflow.py
```

```bash
python diagnostics/stationarity_and_breaks.py
```

```bash
python docs/make_figures.py
```

```bash
python projection/project.py --scenario projection/scenarios/flat_8Q.csv
```

```bash
python -m pytest data_build projection
```

Optional out-of-sample comparison (§7.6):

```bash
python MAE_Backtesting/run_backtest.py --horizon 8Q --bank-name All --select out-of-sample
```

```bash
python Beta_Backtesting/run_beta_backtest.py --first-origin 2016Q1 --select out-of-sample
```

```bash
python MAE_Backtesting/compare_selection.py
```

`python data_build/build_dataset.py --refresh` re-downloads the FDIC data instead of using the cached snapshot, and `python data_build/build_fft.py --refresh` re-downloads `FEDFUNDS` from FRED. The projection takes any scenario CSV with the layout of the FFT files (quarter, `FFT`) covering T+1 onward and writes `projection/output/<scenario>_projection.csv`; `--no-freeze-trend` shows the unfrozen path for diagnostics.

### 10.3 Controls
- Scripts exit with an error and stop at the first failing step (`ECM workflow.py`).
- Banks that fail are logged and skipped in the backtest; the exit code is 2 if any were skipped.
- Merger adjustment checks are recorded in `merger_adjustment_log.md`.
- The FDIC snapshot used for a run is cached in `data_build/raw/` and committed with the outputs. The backtest caches are keyed on a hash of each bank's input data and on each model's fitted terms.
- Gaps: unit tests cover only the FFT builder and the projection layer (15 tests); the backtests have no unit tests; no version pinning.

---

## 11. Governance

| Item | Status |
| :--- | :--- |
| Model owner | Shivam Panda |
| Model inventory registration | Not registered (WIP) |
| Independent validation | Not performed |
| Ongoing monitoring plan | Not defined. Proposed: quarterly refresh after each Call Report cycle, with the many-start-date backtest rated against the horizon-aware limits and skill test (§5.6) |
| Change management | Git version control (`Panda5130/Deposit-Beta`) |

---

## Appendix A: Stationarity Test Detail

All tests use the rebuilt pro forma series (`rate_pf_clean`). Default specification: ADF `c` / AIC and KPSS `c` / auto. Robustness counts the share of the six alternative specifications that agree with the default conclusion (ADF: `c` / `n` × AIC / BIC / t-stat; KPSS: `c` / `ct` × auto / long / short). KPSS p-values are bounded at 0.01 and 0.10. All 336 individual results are in `diagnostics/unit_root_grid.csv`; produced by `diagnostics/stationarity_and_breaks.py`.

### A.1 Main Sample: 2011Q1 to 2026Q2

| Bank | I(0) ADF p | I(0) KPSS p | I(0) verdict | I(0) robustness (ADF / KPSS) | I(1) ADF p | I(1) KPSS p | I(1) verdict | I(1) robustness (ADF / KPSS) | Classification |
| :--- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| First Horizon Bank | 0.149 | 0.029 | non-stationary | 6/6 / 2/6 | 0.0044 | ≥ 0.10 | stationary | 6/6 / 6/6 | **I(1)** |
| Glacier Bank | 0.662 | 0.057 | inconclusive | 6/6 / 1/6 | 0.0070 | ≥ 0.10 | stationary | 6/6 / 6/6 | **flagged** |
| Huntington National Bank | 0.486 | 0.024 | non-stationary | 6/6 / 2/6 | 0.0029 | ≥ 0.10 | stationary | 6/6 / 6/6 | **I(1)** |
| KeyBank National Association | 0.308 | 0.025 | non-stationary | 6/6 / 2/6 | 0.0037 | ≥ 0.10 | stationary | 6/6 / 6/6 | **I(1)** |
| Manufacturers and Traders Trust Company | 0.245 | 0.035 | non-stationary | 6/6 / 2/6 | 0.0023 | ≥ 0.10 | stationary | 6/6 / 6/6 | **I(1)** |
| Old National Bank | 0.582 | 0.031 | non-stationary | 6/6 / 2/6 | 0.0031 | ≥ 0.10 | stationary | 6/6 / 6/6 | **I(1)** |
| SouthState Bank | 0.272 | 0.038 | non-stationary | 6/6 / 2/6 | 0.0038 | ≥ 0.10 | stationary | 5/6 / 6/6 | **I(1)** |

### A.2 Extended Sample: 2008Q1 to 2026Q2

| Bank | I(0) ADF p | I(0) KPSS p | I(0) verdict | I(0) robustness (ADF / KPSS) | I(1) ADF p | I(1) KPSS p | I(1) verdict | I(1) robustness (ADF / KPSS) | Classification |
| :--- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| First Horizon Bank | 0.049 | ≥ 0.10 | stationary | 3/6 / 3/6 | 0.0065 | 0.092 | stationary | 5/6 / 6/6 | **I(0)** |
| Glacier Bank | 0.406 | ≥ 0.10 | inconclusive | 3/6 / 3/6 | 0.049 | 0.018 | inconclusive | 6/6 / 5/6 | **flagged** |
| Huntington National Bank | 0.436 | ≥ 0.10 | inconclusive | 6/6 / 3/6 | 0.058 | 0.042 | non-stationary | 3/6 / 5/6 | **flagged** |
| KeyBank National Association | 0.496 | ≥ 0.10 | inconclusive | 6/6 / 3/6 | 0.051 | 0.052 | inconclusive | 5/6 / 6/6 | **flagged** |
| Manufacturers and Traders Trust Company | 0.456 | ≥ 0.10 | inconclusive | 6/6 / 3/6 | 6.5e-05 | 0.053 | stationary | 6/6 / 6/6 | **flagged** |
| Old National Bank | 0.194 | ≥ 0.10 | inconclusive | 6/6 / 3/6 | 0.048 | 0.030 | inconclusive | 6/6 / 5/6 | **flagged** |
| SouthState Bank | 0.375 | ≥ 0.10 | inconclusive | 6/6 / 3/6 | 0.0093 | 0.023 | inconclusive | 6/6 / 5/6 | **flagged** |

In the extended sample, First Horizon looks I(0) (ADF p 0.049) and the other six banks are inconclusive on levels. The main-sample I(1) classification is therefore not robust to the longer sample (L3).

### A.3 Zivot-Andrews Structural Break Tests, 2011Q1 to 2026Q2

| Bank | `c`: stat, p, break | `t`: stat, p, break | `ct`: stat, p, break |
| :--- | :-: | :-: | :-: |
| First Horizon Bank | -6.27, 5.4e-04, 2022Q3 | -4.80, 0.019, 2021Q4 | -5.07, 0.051, 2023Q1 |
| Glacier Bank | -7.57, 1.0e-05, 2022Q4 | -3.79, 0.210, 2021Q3 | -5.20, 0.036, 2023Q1 |
| Huntington National Bank | -6.34, 4.7e-04, 2022Q2 | -5.41, 0.0049, 2021Q4 | -5.64, 0.0082, 2022Q3 |
| KeyBank National Association | -6.81, 1.0e-05, 2022Q3 | -4.67, 0.024, 2021Q4 | -4.93, 0.076, 2022Q3 |
| Manufacturers and Traders Trust Company | -6.42, 3.9e-04, 2022Q3 | -4.09, 0.111, 2021Q2 | -4.91, 0.079, 2022Q3 |
| Old National Bank | -6.21, 6.1e-04, 2022Q3 | -4.31, 0.065, 2022Q1 | -4.26, 0.335, 2019Q3 |
| SouthState Bank | -6.23, 5.8e-04, 2022Q3 | -4.43, 0.048, 2021Q3 | -5.21, 0.035, 2022Q4 |

FFT itself gives ZA `c` = -5.49, p 0.004, break 2022Q1. The break in the deposit rates mirrors the break in the regressor (OI-20).

---

## Appendix B: Artifacts

| Artifact | Location |
| :--- | :--- |
| Figures included in this document (champion models only) | `docs/figures/` |
| Actual vs. predicted charts, every estimated specification | `Actuals vs Predictions/<bank>/` |
| MAE stability bar charts and tables | `MAE_Backtesting/output/<bank>/MAE_backtest_8Q.{png,csv}` (single window); `MAE_backtest_multiorigin_8Q.{png,csv}` (many start dates; shown in §6) |
| MAE stability summary, all banks | `MAE_Backtesting/output/backtest_summary_8Q.csv` |
| Full coefficient tables, all estimated ECMs | `ECM estimation results.csv` |
| In-sample MAE, all estimated ECMs | `estimation result summary.csv` |
| Merger event inputs and log | `merger_events_used.csv`, `merger_adjustment_log.md` (`merger_events_raw.csv` is from the superseded notebook) |
| Data build and FDIC snapshot | `data_build/build_dataset.py`, `data_build/raw/*.csv` |
| Unit-root and break diagnostics | `diagnostics/*.csv` |
| Many-start-date backtest, limits and ratings | `MAE_Backtesting/output/backtest_multiorigin_8Q.csv`, `backtest_multiorigin_limits_8Q.csv`, `backtest_multiorigin_assessment_8Q.csv` |
| Single-window ratings | `MAE_Backtesting/output/backtest_assessment_8Q.csv` |
| Long-run beta stability from 2016Q1: per-start-date estimates, ratings and charts | `Beta_Backtesting/output/<bank>/beta_backtest_multiorigin.{csv,png}`; `Beta_Backtesting/output/beta_backtest_multiorigin_assessment.csv`, `beta_backtest_multiorigin_all_banks.{csv,png}` |
| Long-run beta stability, last eight start dates (supplementary) | `Beta_Backtesting/output/<bank>/beta_backtest_origins_8Q.csv`, `beta_backtest_8Q.{csv,png}`; `Beta_Backtesting/output/beta_backtest_summary_8Q.csv`, `beta_backtest_all_banks_8Q.png` |
| Out-of-sample model choice (optional) | `MAE_Backtesting/output/out_of_sample/` (incl. `selection_comparison_8Q.{csv,png}`), `Beta_Backtesting/output/out_of_sample/` |
| Break tests, challengers, Huntington evidence, 2025Q1 decomposition | `model_form/output/` |
| FFT builder and projection | `data_build/build_fft.py`, `projection/project.py`, `projection/scenarios/`, `projection/output/` |
| Root-cause resolution notes (2026-10-31) | `docs/resolutions/*.md` |
| Open-issue resolution record | `docs/open_issue_resolutions.md` |

---
