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
| Code version documented | Commit `326b641` (initial commit, 2026-10-30) |
| Document date | 2026-10-30 |
| Data period | 2011Q1 to 2026Q2 (main); 2008Q1 to 2026Q3 (sensitivity, Appendix A1) |

### 0.1 Revision History

| Version | Date | Description |
| :--- | :--- | :--- |
| 0.1 (WIP) | 2026-10-30 | First SR 11-7 style draft, built from the vault documentation and the development code and outputs in the repository. |

---

## 1. Executive Summary

### 1.1 Purpose
The analysis estimates the **deposit beta** of seven U.S. regional banks: the long-run share of a change in the federal funds rate that passes through to the bank's average deposit rate. It also estimates the short-run speed at which deposit rates adjust toward that long-run relationship. Each bank is modeled separately.

### 1.2 Banks in Scope

| # | Bank | FDIC Cert | Merger treatment in final dataset |
| :-: | :--- | :-: | :--- |
| 1 | First Horizon Bank | 4977 | None applied (see §6.1) |
| 2 | Glacier Bank | n/a in event file | None (no events) |
| 3 | Huntington National Bank | 6560 | Mode A (TCF National Bank, 2021) |
| 4 | KeyBank National Association | 17534 | Mode A (First Niagara Bank, 2016) |
| 5 | Manufacturers and Traders Trust Company | 588 | Mode A (People's United Bank, 2022) |
| 6 | Old National Bank | 3832 | None applied (see §6.6) |
| 7 | SouthState Bank | 33555 | Mode B flag (CenterState Bank, 2020) |

### 1.3 Summary of Current Results (2011Q1 to 2026Q2, merger-adjusted)
All seven deposit-rate series are classified as I(1) once flagged banks are re-specified (§5.2). Every bank has at least one cointegrating specification with the federal funds rate at the 5% level. The selected model for each bank is the specification with the lowest in-sample MAE (§5.5).

| Bank | Selected specification | Speed of adjustment (λ) | Long-run deposit beta (θ) | In-sample MAE (pp) | Mean 8Q backtest MAE (pp) |
| :--- | :--- | :-: | :-: | :-: | :-: |
| First Horizon Bank | ARDL(3,2), case 4, AIC | -0.517 | 0.560 | 0.0607 | 0.140 |
| Glacier Bank | Johansen VECM rank 1, k_ar_diff=1, det_order 1, AIC | -0.207 | 0.412 | 0.1157 | 0.248 |
| Huntington National Bank | ARDL(4,4), case 3, AIC | -0.286 | 0.532 | 0.0713 | 0.176 |
| KeyBank National Association | EG short-run ECM, no deterministic terms, AIC (ADF lag 1, ECM lag 3) | -0.184 | 0.495 | 0.0545 | 0.130 |
| Manufacturers and Traders Trust Company | ARDL(2,1), case 3, AIC | -0.127 | 0.452 | 0.0521 | 0.174 |
| Old National Bank | ARDL(3,1), case 3, AIC | -0.316 | 0.541 | 0.0858 | 0.201 |
| SouthState Bank | Johansen VECM rank 1, k_ar_diff=2, det_order -1, AIC | -0.215 | 0.434 | 0.0588 | 0.104 |

All λ and θ estimates are significant at the 1% level. Long-run betas fall between 0.41 and 0.56.

### 1.4 Key Open Issues (detail in §8 and §9)
1. Merger adjustment inputs contain placeholder values, and four of the eight listed Mode A events do not appear as adjustments in the modeled dataset.
2. Stationarity for Glacier, Huntington and M&T depends on the test specification chosen.
3. Model selection uses in-sample MAE after screening coefficients on p-values, which overstates in-sample fit and makes reported p-values post-selection.
4. Out-of-sample errors are large at some horizons (M&T and Old National above 0.53 pp at the 5Q horizon).
5. The deposit-rate proxy uses total interest expense, which includes interest on non-deposit liabilities.

---

## 2. Model Purpose, Scope and Intended Use

### 2.1 Business Purpose
Deposit betas feed interest-rate risk measurement (NII and EVE sensitivity), deposit pricing analysis, funds-transfer pricing, and peer benchmarking. This analysis gives a peer set of regional-bank betas estimated from public regulatory data.

### 2.2 Intended Use (once validated)
- Peer benchmarking of long-run deposit pass-through.
- Scenario projection of deposit rates conditional on a federal funds rate path, over horizons of up to 8 quarters.

### 2.3 Uses Outside Scope
- Production pricing or regulatory capital decisions while the model is WIP.
- Product-level or customer-segment deposit betas: the data is bank-level total interest expense over total deposits.
- Forecasts beyond 8 quarters, or under rate regimes outside the 2011 to 2026 sample (for example, negative rates).

### 2.4 Model Output
For each bank: the estimated one-step ECM (short-run coefficients, speed of adjustment λ, long-run coefficients θ with delta-method standard errors), in-sample MAE, and rolling-origin dynamic-forecast MAE by horizon.

---

## 3. Model Overview

### 3.1 Variables

| Role | Variable | Definition | Source |
| :--- | :--- | :--- | :--- |
| Dependent (y) | `rate_pf_clean` | Annualized quarterly interest expense ÷ annual average total deposits × 100, merger-adjusted (pro forma) | FDIC BankFind Suite, Financials API |
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
| 1 | Data pull and aggregation | `FDIC Fincancials pull and aggeregation.ipynb` | `consolidated_fdic_quarterly_financials_*.csv` |
| 2 | Merger adjustment | `TargetBank_merger_adjusted_features.ipynb` | `*_merger_adjusted.csv`, `merger_events_*.csv`, `merger_adjustment_log.md` |
| 3 | Stationarity tests (ADF/KPSS) | `EDA1_Stationarity_Tests.ipynb`, `Flagged Rates Analysis - ADF respecification.ipynb` | Vault documentation tables |
| 4 | Structural breaks (Zivot-Andrews) | `Flagged Rate Analysis - Structural Breaks.ipynb` | Vault documentation |
| 5 | Baseline cointegration tests | `Co-integration Tests.py` with `test_params.csv` | `Co-integration_results.csv` |
| 6 | Cointegration re-specification grid | `FlaggedRates_co-integration_respecification.py` | `co-integration_respecification_results.csv` |
| 7 | Model selection (test p < 0.05) | `ECM model selection.py` | `ECM model selection results.csv` |
| 8 | Parameter selection (coef p < 0.05) | `ECM Param selection.py` | `ECM param selection results.csv` |
| 9 | One-step ECM estimation | `ECM estimation.py` | `ECM estimation results.csv`, `estimation result summary.csv` |
| 10 | Actual vs. predicted charts | `plotting_workflow.py`, `bank_plots.py` | `Actuals vs Predictions/<bank>/*.png` |
| 11 | Rolling-origin MAE backtest | `MAE_Backtesting/run_backtest.py`, `backtest.py` | `MAE_Backtesting/output/` |

Steps 7 to 9 are run together by `ECM workflow.py`.

---

## 4. Data

### 4.1 Sources
- **FDIC BankFind Suite, Financials endpoint** (`https://banks.data.fdic.gov/api/financials`). Fields: `CERT`, `REPDTE`, `EINTEXP` (total interest expense, year-to-date), `DEP` (total deposits). Quarterly Call Report data, pulled for 2008Q1 to 2026Q4. Each quarterly file covers every insured institution and was filtered to the seven banks in scope.
- **FDIC BankFind Suite, History and Institutions endpoints** (`/api/history`, `/api/institutions`), used to identify merger events.
- **FRED `FEDFUNDS`**: monthly effective federal funds rate, averaged to quarters (`FFT_2011-2026.csv`, `FFT_2008-2026.csv`).

### 4.2 Transformations
1. **De-cumulation of interest expense.** Call Report interest expense is year-to-date. Quarterly interest expense is computed as the current year-to-date figure minus the prior quarter's figure (Q1 is used as reported).
2. **Annualization.** Quarterly interest expense is annualized.
3. **Average deposits.** Total deposits are converted to annual averages.
4. **Deposit rate.** `deposit_rate = 100 × annualized interest expense ÷ annual average deposits`.
5. **Merger adjustment (pro forma).** See §4.3. The modeled series is `rate_pf_clean`.
6. **Alignment.** Bank and FFT series are joined on quarterly periods. Rows with missing values are dropped.

### 4.3 Merger Adjustment Methodology
- **Mode A (material):** acquisitions of 1.0% or more of the survivor's deposits. Interest expense and average deposits are adjusted to a pro forma basis (`ie_ann_pf`, `dep_avg_pf`, `rate_pf`).
- **Mode B (sub-material):** acquisitions below 1.0%. Flagged only, intended for exclusion in downstream pricing models.
- **Recorded validations** (`merger_adjustment_log.md`): the pro forma rate formula reproduces `rate_pf` to within 1e-12; there are no duplicate cert/quarter keys; baseline source columns are unchanged. The log counts 434 records evaluated, 6 Mode A adjustments and 2 Mode B flags.

**Events listed in `merger_events_used.csv`:**

| Predecessor | Survivor | Effective date | Mode listed | Appears as an adjustment in the 2011 to 2026 modeled data |
| :--- | :--- | :-: | :-: | :--- |
| First Niagara Bank | KeyBank National Association | 2016-08-01 | A | Yes: 2016Q3 (18% of deposits acquired), 2016Q4 rate adjusted |
| FirstMerit Bank | Huntington National Bank | 2016-08-16 | A | **No** |
| TCF National Bank | Huntington National Bank | 2021-06-09 | A | Yes: 2021Q2 (15%), 2021Q3 rate adjusted |
| IBERIABANK | First Horizon Bank | 2020-07-02 | A | **No** |
| CenterState Bank | SouthState Bank | 2020-06-08 | B | Flagged: 2020Q2 (0.5%), rate not changed |
| Atlantic Capital Bank | SouthState Bank | 2022-03-01 | A | **No** |
| First Midwest Bank | Old National Bank | 2022-02-15 | A | **No** |
| People's United Bank | Manufacturers and Traders Trust Company | 2022-04-02 | A | Yes: 2022Q2 (28%), 2022Q3 rate adjusted |

**Data quality findings (open, see §9):**
- In `merger_events_used.csv`, the predecessor cert numbers for seven events are placeholders (11111, 22222, ...), and `deposits_at_last_pre_merger_quarter` is the same value (5,000,000) for every event. The materiality classification therefore does not rest on actual predecessor deposits.
- The log's "6 Mode A adjustments" matches 6 adjusted bank-quarter *rows* (3 events × 2 quarters), not 6 events.
- Mode B rows are not excluded from `rate_pf_clean`, which is the series used in modeling.
- The adjustment changes only the quarter after the merger (largest change: KeyBank 2016Q4, -0.042 pp). Effects on the level of the series are small.

### 4.4 Sample
- Main: 2011Q1 to 2026Q2, 62 quarterly observations per bank.
- Sensitivity: 2008Q1 to 2026Q3 (Appendix A1), with and without merger adjustment (Appendix A2).

### 4.5 Exploratory Review
The figure below shows the series. Deposit rates track FFT with a lag and partial pass-through through the 2016 to 2019 tightening, the 2020 cut to the zero bound, and the 2022 to 2023 tightening. Huntington's deposit rate stays above its peers from 2011 to 2016. Glacier's rate shows an isolated spike in 2012Q1.

![Historical deposit rates of the seven banks vs. FFT, 2011Q1 to 2026Q4](<docs/Historical Deposit Rates vs FFT.png>)

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

### 5.3 Structural Break Testing
Zivot-Andrews tests with automatic lag selection were run on the flagged banks (§6).

### 5.4 Cointegration Testing

| Procedure | Statistic | p-value | Specification grid |
| :--- | :--- | :--- | :--- |
| Engle-Granger, long run (`EG_LongRun`) | ADF *t* on step-1 OLS residuals | MacKinnon (2010), N = 2 | Trend `n` / `c` / `ct`; ADF and ECM lags by AIC / BIC / t-stat (general-to-specific) / fixed = 4 |
| Engle-Granger, short run (`EG_ShortRun`) | *t* on `ect.L1` in the short-run ECM | MacKinnon (2010), same trend and N | As above |
| Johansen trace | Trace statistic for r ≤ 0, r ≤ 1 | Bounded from critical values (<0.01, <0.05, <0.10, >0.10) | `det_order` -1 / 0 / 1; `k_ar_diff` by VECM AIC / BIC / HQIC / FPE or fixed at 1 |
| ARDL bounds test (PSS) | Bounds F | I(1) upper-bound p-value | PSS cases 1 to 5; lags by AIC / BIC / HQIC (max 4); at least 1 lag of the regressor |

- **Baseline run** (`Co-integration Tests.py`, all 7 banks): trend `c`, max lag 4, EG and ARDL lags by AIC, Johansen `det_order 0` with `k_ar_diff = 1`, ARDL case 3.
- **Re-specification run** (`FlaggedRates_co-integration_respecification.py`): full grid for First Horizon, Glacier, KeyBank, M&T and SouthState. Huntington and Old National were **not** re-specified because they passed under the baseline.
- Coefficient t- and p-values on levels regressors (EG step 1, VECM β) do not follow standard distributions when the series are I(1). They are descriptive only.

### 5.5 Model and Parameter Selection
1. **Model screen:** keep every specification whose cointegration test p-value is below α = 0.05. A Johansen VECM takes the r ≤ 0 trace result of the same specification. A bounded Johansen p-value "<x" passes when x ≤ α.
2. **Parameter screen:** within each surviving specification, keep terms with coefficient p-value < 0.05.
3. **Mapping to a one-step ECM:** surviving deterministic terms, short-run lags, and the error-correction term (`ect.L1`, `y.L1` or VECM `D.y: ec1`) define the regressors. Specifications without a surviving error-correction term are dropped. `EG_LongRun` is treated as error-correcting by construction.
4. **Estimation:** one-step OLS ECM (§3.2), with long-run coefficients and delta-method standard errors.
5. **Champion choice:** lowest in-sample MAE of Δy per bank. Ties are broken EG > ARDL > Johansen, then file order.

### 5.6 Performance Testing (Backtest)
- **Rolling-origin dynamic forecast:** with horizon N = 8 and last observation T = 2026Q2, origins run from T-8 to T-1. At each origin the champion specification is re-estimated on data up to that origin and forecast dynamically to T, with predicted y fed back as the lag and realized FFT used for the regressor.
- **Metric:** MAE over the k quarters of each forecast window (1Q to 8Q). The minimum training window is 20 quarters.

### 5.7 Key Assumptions
- FFT is weakly exogenous to each bank's deposit rate (single-equation ECM).
- One cointegrating vector (rank 1) between the deposit rate and FFT.
- Linear, symmetric pass-through: no asymmetry between rising and falling rates, and no threshold at the zero lower bound.
- Parameters are stable over 2011 to 2026, apart from any deterministic trend.
- Total interest expense ÷ total deposits is an adequate proxy for the deposit rate.

---

## 6. Bank-Specific Development and Treatment

Each subsection follows the same structure: data treatment, stationarity, structural breaks, cointegration, specifications estimated, champion model, and outcomes and issues. All results use 2011Q1 to 2026Q2 merger-adjusted data unless stated otherwise. Rates are in percentage points (pp).

### 6.1 First Horizon Bank

#### 6.1.1 Data Treatment
- FDIC cert 4977. The IBERIABANK merger (2020-07-02) is listed as Mode A in `merger_events_used.csv`, but **no adjustment appears in the modeled data** (`adjustment_mode = none` in all 62 quarters). Open issue.

#### 6.1.2 Stationarity

| Sample | Levels I(0) | First difference I(1) |
| :--- | :--- | :--- |
| 2011 to 2026 raw | ADF -1.061 (p 0.730), KPSS 0.640 (p 0.019): non-stationary | ADF -3.557 (p 0.0066), KPSS 0.095 (p 0.100): stationary |
| 2011 to 2026 merger-adjusted (main) | ADF -1.980 (p 0.296), KPSS 0.640 (p 0.019): **non-stationary** | ADF -3.420 (p 0.0103), KPSS 0.103 (p 0.100): **stationary** |
| 2008 to 2026 raw | ADF -1.805 (p 0.378), KPSS 0.245 (p 0.100): inconclusive | ADF -3.771 (p 0.0032), KPSS 0.500 (p 0.042): inconclusive |
| 2008 to 2026 merger-adjusted | ADF -2.134 (p 0.231), KPSS 0.245 (p 0.100): inconclusive | ADF -3.614 (p 0.0055), KPSS 0.519 (p 0.037): inconclusive |

**Conclusion: I(1) under the default specification.** Not flagged.

#### 6.1.3 Structural Breaks
Not tested.

#### 6.1.4 Cointegration
- **Baseline:** EG long run p 0.252; EG short run p 0.347; Johansen trace r ≤ 0 = 26.61 (p < 0.01), r ≤ 1 = 4.40 (p < 0.05); ARDL(3,4) case 3 F = 3.68 (p 0.149). Only Johansen passes.
- **Re-specification:** included in the grid as a precaution. Passing specifications include EG with `ct` (long run p 0.032; short run p 4.9e-06 under BIC and p 0.046 under t-stat), Johansen with `det_order` -1, 0 and 1, and ARDL cases 2 to 5 (F between 9.8 and 21.4, all p < 1e-05).

#### 6.1.5 Specifications Estimated
17 one-step ECMs (8 ARDL, 3 EG, 6 Johansen). In-sample MAE 0.0607 to 0.0922. Long-run beta 0.445 to 0.567.

#### 6.1.6 Champion Model: ARDL(3,2), case 4 (unrestricted constant, restricted trend), AIC
Bounds F = 14.77, p = 1.3e-08. Tied on in-sample MAE with the HQIC selection of the same lags; the tie-break kept the AIC row.

| Term | Coefficient | *t* | p-value |
| :--- | :-: | :-: | :-: |
| const | 0.2248 | 4.61 | 2.7e-05 |
| trend | -0.00571 | -3.76 | 4.4e-04 |
| y.L1 (λ) | **-0.5170** | -6.23 | 8.8e-08 |
| FFT.L1 | 0.2895 | 6.54 | 2.9e-08 |
| D.y.L1 | 0.4878 | 4.88 | 1.1e-05 |
| D.y.L2 | -0.2722 | -2.97 | 4.6e-03 |
| D.FFT.L0 | 0.2057 | 3.77 | 4.2e-04 |
| D.FFT.L1 | -0.1691 | -2.18 | 0.034 |
| LR: const | 0.4349 | 6.96 | 6.3e-09 |
| LR: trend | -0.01105 | -4.25 | 9.0e-05 |
| **LR: FFT (θ)** | **0.5599** | 20.28 | 4.5e-26 |

#### 6.1.7 Outcomes Analysis and Issues
- 8Q backtest MAE (1Q to 8Q): 0.247, 0.121, 0.085, 0.066, 0.174, 0.140, 0.154, 0.137. Mean 0.140.
- The long-run trend (-0.011 pp per quarter) lowers the equilibrium rate by about 0.68 pp over the sample. Projections beyond the sample will carry this trend forward, which may not be economically justified. A reviewer should assess whether the trend stands in for the unmodeled IBERIABANK merger.
- The fastest adjustment in the peer set (λ = -0.52) means about half of any disequilibrium closes each quarter.

### 6.2 Glacier Bank

#### 6.2.1 Data Treatment
No merger events recorded. `adjustment_mode = none` throughout.

#### 6.2.2 Stationarity

| Sample | Levels I(0) | First difference I(1) |
| :--- | :--- | :--- |
| 2011 to 2026 raw | ADF -1.685 (p 0.439), KPSS 0.441 (p 0.060): insufficient evidence | ADF -3.515 (p 0.0076), KPSS 0.170 (p 0.100): stationary |
| 2011 to 2026 merger-adjusted, default | ADF -1.063 (p 0.730), KPSS 0.443 (p 0.059): **inconclusive, flagged** | ADF -9.773 (p 7.0e-17), KPSS 0.169 (p 0.100): stationary |
| 2008 to 2026 raw | ADF -3.440 (p 0.0097), KPSS 0.291 (p 0.100): stationary (I(0)) | ADF -4.211 (p 0.0006), KPSS 0.490 (p 0.044): inconclusive |
| 2008 to 2026 merger-adjusted | ADF -3.871 (p 0.0023), KPSS 0.290 (p 0.100): stationary (I(0)) | ADF -4.894 (p 3.6e-05), KPSS 0.419 (p 0.069): stationary |

**Re-specification (2011 to 2026 raw, ADF on levels):** no specification rejects a unit root (`c` p 0.373; `n` p 0.243 under AIC, BIC and t-stat).

**Re-specification (2011 to 2026 merger-adjusted), selected ADF `c` / BIC and KPSS `c` / auto:**
- I(0): ADF -1.047 (p 0.736); KPSS 0.466 (p 0.049). **Non-stationary.**
- I(1): ADF -9.605 (p 1.9e-16); KPSS 0.176 (p 0.100). **Stationary.**

**Robustness** (share of the six re-specifications supporting the conclusion): ADF I(0) 6/6, KPSS I(0) 5/6, ADF I(1) 5/6, KPSS I(1) 6/6.

**Conclusion: I(1), conditional on specification.** The KPSS I(0) rejection is borderline (p 0.0494 under `c`/auto and `c`/short; 0.0499 under `ct`/long). `ct`/auto is clearer (p 0.010). In the longer 2008 to 2026 sample the levels series looks I(0).

#### 6.2.3 Structural Breaks
Zivot-Andrews statistic -4.649, p 0.154 (critical values: 1% -5.58, 5% -5.07, 10% -4.83). Estimated break at 2011-09-30 (index 2). The test does not reject a unit root with a break.

#### 6.2.4 Cointegration
- **Baseline:** none pass. EG long run p 0.338; EG short run p 0.843; Johansen trace r ≤ 0 = 13.12 (p > 0.10); ARDL(2,4) case 3 F = 2.49 (p 0.394).
- **Re-specification:** Johansen with `det_order 1` (linear trend), k_ar_diff = 1 under every lag criterion: trace r ≤ 0 = 21.86 (p < 0.05), r ≤ 1 = 4.04 (p < 0.05). ARDL(2,1) cases 1 to 5 under BIC and HQIC, plus cases 4 and 5 under AIC: F between 5.65 and 10.71 (p 0.0002 to 0.0035). No EG specification passes.
- The Johansen r ≤ 1 rejection, if taken literally, implies rank 2 (both series stationary). Rank 1 is imposed by assumption.

#### 6.2.5 Specifications Estimated
17 one-step ECMs (12 ARDL, 5 Johansen). In-sample MAE 0.1157 to 0.1264, the highest in the peer set. Long-run beta 0.412 to 0.462.

#### 6.2.6 Champion Model: Johansen VECM (rank 1), det_order 1 (linear trend), k_ar_diff = 1, AIC
All five Johansen lag criteria give the same model. The deterministic terms did not survive the parameter screen, so the estimated ECM has **no constant or trend**, even though the cointegration test used a linear trend.

| Term | Coefficient | *t* | p-value |
| :--- | :-: | :-: | :-: |
| y.L1 (λ) | **-0.2068** | -3.01 | 4.0e-03 |
| FFT.L1 | 0.0852 | 3.13 | 2.8e-03 |
| D.y.L1 | -0.3260 | -2.93 | 4.9e-03 |
| D.FFT.L1 | 0.2204 | 2.67 | 9.8e-03 |
| **LR: FFT (θ)** | **0.4119** | 6.97 | 3.9e-09 |

#### 6.2.7 Outcomes Analysis and Issues
- 8Q backtest MAE (1Q to 8Q): 0.176, 0.274, 0.177, 0.152, 0.148, 0.279, 0.354, 0.429. Mean 0.248, the **worst in the peer set**, and errors grow with horizon.
- The mismatch between the test's deterministic specification (linear trend) and the estimated ECM (none) needs review.
- The 2012Q1 spike in the deposit rate is a candidate data anomaly and has not been investigated.
- Evidence on the order of integration is mixed across samples (§6.2.2).

### 6.3 Huntington National Bank

#### 6.3.1 Data Treatment
- FDIC cert 6560. **TCF National Bank (2021-06-09), Mode A:** 15% of deposits acquired in 2021Q2. The 2021Q3 rate was adjusted from 0.0836 to 0.0778.
- **FirstMerit Bank (2016-08-16), Mode A, is listed but not applied** in the modeled data. Open issue.

#### 6.3.2 Stationarity

| Sample | Levels I(0) | First difference I(1) |
| :--- | :--- | :--- |
| 2011 to 2026 raw | ADF 0.917 (p 0.993), KPSS 0.574 (p 0.025): non-stationary | ADF -2.321 (p 0.165), KPSS 0.247 (p 0.100): **insufficient evidence** |
| 2011 to 2026 merger-adjusted, default | ADF 0.952 (p 0.994), KPSS 0.645 (p 0.019): non-stationary | ADF -2.358 (p 0.154), KPSS 0.171 (p 0.100): **inconclusive, flagged** |
| 2008 to 2026 raw | ADF -1.694 (p 0.434), KPSS 0.287 (p 0.100): inconclusive | ADF -1.943 (p 0.312), KPSS 0.546 (p 0.031): non-stationary |
| 2008 to 2026 merger-adjusted | ADF -2.150 (p 0.225), KPSS 0.290 (p 0.100): inconclusive | ADF -5.327 (p 4.8e-06), KPSS 0.557 (p 0.029): inconclusive |

**Re-specification (2011 to 2026 raw, ADF on levels):** no specification rejects a unit root (p 0.54 to 0.99).

**Re-specification (2011 to 2026 merger-adjusted), selected ADF `c` / BIC and KPSS `c` / auto:**
- I(0): ADF -1.032 (p 0.741); KPSS 0.585 (p 0.024). **Non-stationary.**
- I(1): ADF -3.978 (p 0.0015); KPSS 0.181 (p 0.100). **Stationary.**

**Robustness:** ADF I(0) 6/6, KPSS I(0) 4/6, **ADF I(1) 2/6**, KPSS I(1) 6/6.

**Conclusion: I(1), conditional on specification.** First-difference stationarity holds only under BIC lag selection (`c` p 0.0015; `n` p 8.6e-05). AIC and t-stat fail (p 0.30 with a constant, 0.11 without). KPSS I(0) non-stationarity holds under auto and short bandwidths but not long (p 0.085).

#### 6.3.3 Structural Breaks
The Zivot-Andrews test **could not be run**: the auxiliary exogenous matrix is not full rank (12 columns, rank 11).

#### 6.3.4 Cointegration
- **Baseline:** EG long run p 0.421; EG short run p 0.724 (both fail). Johansen trace r ≤ 0 = 22.33 (p < 0.01), r ≤ 1 = 3.33 (p < 0.10). ARDL(4,4) case 3 F = 9.40 (p 0.0003). Johansen and ARDL pass.
- Not included in the re-specification grid.

#### 6.3.5 Specifications Estimated
2 one-step ECMs (1 ARDL, 1 Johansen). In-sample MAE 0.0713 to 0.0750. Long-run beta 0.532 to 0.541.

#### 6.3.6 Champion Model: ARDL(4,4), case 3 (unrestricted constant), AIC

| Term | Coefficient | *t* | p-value |
| :--- | :-: | :-: | :-: |
| y.L1 (λ) | **-0.2858** | -4.69 | 1.9e-05 |
| FFT.L1 | 0.1521 | 4.80 | 1.3e-05 |
| D.y.L1 | -0.1170 | -1.07 | **0.291** |
| D.FFT.L0 | 0.2514 | 6.48 | 3.1e-08 |
| D.FFT.L3 | 0.1012 | 2.03 | 0.048 |
| **LR: FFT (θ)** | **0.5320** | 25.16 | 3.8e-31 |

#### 6.3.7 Outcomes Analysis and Issues
- 8Q backtest MAE (1Q to 8Q): 0.280, 0.161, 0.143, 0.184, 0.215, 0.143, 0.138, 0.141. Mean 0.176. The 1Q error is the highest in the peer set.
- `D.y.L1` survived the parameter screen in the UECM but is **not significant** (p 0.29) in the re-estimated one-step ECM. The model should be refit without it.
- Stationarity of the first difference depends on lag selection, and the structural-break test failed.
- Huntington's rate stayed well above its peers from 2011 to 2016, possibly linked to the unadjusted FirstMerit merger.
- No re-specification grid was run, so robustness of the cointegration result has not been assessed.

### 6.4 KeyBank National Association

#### 6.4.1 Data Treatment
- FDIC cert 17534. **First Niagara Bank (2016-08-01), Mode A:** 18% of deposits acquired in 2016Q3. The 2016Q4 rate was adjusted from 0.514 to 0.472.

#### 6.4.2 Stationarity

| Sample | Levels I(0) | First difference I(1) |
| :--- | :--- | :--- |
| 2011 to 2026 raw | ADF -2.320 (p 0.166), KPSS 0.637 (p 0.019): non-stationary | ADF -3.348 (p 0.013), KPSS 0.097 (p 0.100): stationary |
| 2011 to 2026 merger-adjusted (main) | ADF -1.642 (p 0.461), KPSS 0.640 (p 0.019): **non-stationary** | ADF -3.552 (p 0.0068), KPSS 0.099 (p 0.100): **stationary** |
| 2008 to 2026 raw | ADF -1.748 (p 0.407), KPSS 0.293 (p 0.100): inconclusive | ADF -2.946 (p 0.040), KPSS 0.402 (p 0.076): stationary |
| 2008 to 2026 merger-adjusted | ADF -2.703 (p 0.073), KPSS 0.294 (p 0.100): inconclusive | ADF -3.229 (p 0.018), KPSS 0.400 (p 0.077): stationary |

**Conclusion: I(1) under the default specification.** Not flagged.

#### 6.4.3 Structural Breaks
Not tested.

#### 6.4.4 Cointegration
- **Baseline:** EG long run -3.499 (**p 0.033, pass**); EG short run p 0.143; Johansen trace r ≤ 0 = 15.05 (p < 0.10); ARDL(3,4) case 3 F = 4.69 (p 0.056).
- **Re-specification:** broad support. EG with `n` passes under every lag rule (long run p 0.010 to 0.035; short run p 0.011 to 0.022), as do EG `c`/BIC and EG short run `ct`/BIC. Johansen passes with `det_order` -1 (k_ar_diff = 3) and 1 (k_ar_diff = 1 or 3), trace p < 0.05. ARDL(3,4) cases 1 and 2 and ARDL(2,1) cases 2 to 5 pass (p 0.001 to 0.046).

#### 6.4.5 Specifications Estimated
28 one-step ECMs (12 EG, 9 ARDL, 7 Johansen). In-sample MAE 0.0545 to 0.1095. Long-run beta **0.175 to 0.539**, the widest range in the peer set; the low end comes from EG long-run specifications.

#### 6.4.6 Champion Model: Engle-Granger Short-Run ECM, trend `n`, AIC (ADF lag 1, ECM lag 3)
EG short-run *t* = -3.135, p 0.019. Tied on in-sample MAE (0.054483) with EG short run t-stat/fixed `n` and ARDL(3,4) cases 1 and 2. The EG > ARDL tie-break selected this row.

| Term | Coefficient | *t* | p-value |
| :--- | :-: | :-: | :-: |
| y.L1 (λ) | **-0.1839** | -3.93 | 2.5e-04 |
| FFT.L1 | 0.0910 | 3.69 | 5.4e-04 |
| D.y.L2 | -0.3121 | -2.79 | 7.4e-03 |
| D.FFT.L0 | 0.2437 | 7.73 | 3.5e-10 |
| D.FFT.L2 | 0.1967 | 3.83 | 3.5e-04 |
| D.FFT.L3 | 0.1738 | 3.40 | 1.3e-03 |
| **LR: FFT (θ)** | **0.4948** | 19.05 | 4.1e-25 |

#### 6.4.7 Outcomes Analysis and Issues
- 8Q backtest MAE (1Q to 8Q): 0.098, 0.097, 0.103, 0.064, 0.078, 0.119, 0.285, 0.195. Mean 0.130.
- An earlier 4Q backtest (`MAE_backtest_4Q.csv`) used a **different model**, EG long run `c`/AIC: 0.006, 0.197, 0.282, 0.254. It is not comparable to the champion and should be rerun or archived.
- The wide beta range across passing specifications (0.17 to 0.54) is a model-risk signal: the beta depends on specification.

### 6.5 Manufacturers and Traders Trust Company (M&T)

#### 6.5.1 Data Treatment
- FDIC cert 588. **People's United Bank (2022-04-02), Mode A:** 28% of deposits acquired in 2022Q2, the largest event in scope. The 2022Q3 rate was adjusted from 0.212 to 0.186.

#### 6.5.2 Stationarity

| Sample | Levels I(0) | First difference I(1) |
| :--- | :--- | :--- |
| 2011 to 2026 raw | ADF 1.797 (p 0.998), KPSS 0.629 (p 0.020): non-stationary | ADF -2.627 (p 0.088), KPSS 0.114 (p 0.100): **insufficient evidence** |
| 2011 to 2026 merger-adjusted, default | ADF 1.870 (p 0.998), KPSS 0.631 (p 0.020): non-stationary | ADF -2.493 (p 0.117), KPSS 0.108 (p 0.100): **inconclusive, flagged** |
| 2008 to 2026 raw | ADF -1.922 (p 0.322), KPSS 0.283 (p 0.100): inconclusive | ADF -4.707 (p 8.2e-05), KPSS 0.503 (p 0.041): inconclusive |
| 2008 to 2026 merger-adjusted | ADF -1.408 (p 0.578), KPSS 0.285 (p 0.100): inconclusive | ADF -3.099 (p 0.027), KPSS 0.501 (p 0.042): inconclusive |

**Re-specification (2011 to 2026 raw, ADF on levels):** no specification rejects a unit root (p 0.34 to 1.00).

**Re-specification (2011 to 2026 merger-adjusted), selected ADF `c` / t-stat and KPSS `c` / auto:**
- I(0): ADF 2.764 (p 1.000); KPSS 0.574 (p 0.025). **Non-stationary.**
- I(1): ADF -3.965 (p 0.0016); KPSS 0.115 (p 0.100). **Stationary.**

**Robustness:** ADF I(0) 6/6, KPSS I(0) 4/6, **ADF I(1) 2/6**, KPSS I(1) 6/6.

**Conclusion: I(1), conditional on specification.** `c`/t-stat was chosen over the `c`/BIC used for Glacier and Huntington because `c`/BIC narrowly misses at I(1) (p 0.0508). Only `c`/t-stat (p 0.0016) and `n`/BIC (p 0.0045) pass; `n`/AIC and `n`/t-stat (both p 0.0523) narrowly miss. KPSS I(0) does not hold under the long bandwidth (p 0.086).

#### 6.5.3 Structural Breaks
The Zivot-Andrews test **could not be run**: an array broadcast error (shape (52,) into (2,)), attributed to zero-bound values in the series.

#### 6.5.4 Cointegration
- **Baseline:** EG long run p 0.151; EG short run p 0.421; Johansen trace r ≤ 0 = 11.32 (p > 0.10). **ARDL(2,1) case 3 F = 6.18 (p 0.0115), pass.**
- **Re-specification:** EG long run `n` passes under AIC, BIC and t-stat (p 0.041). ARDL(2,1) passes in cases 1 to 5 under AIC, BIC and HQIC (F 4.12 to 7.10, p 0.005 to 0.034). Johansen `det_order 1` gives only r ≤ 1 rejections (p < 0.05) without an r ≤ 0 rejection, so no Johansen VECM survived.

#### 6.5.5 Specifications Estimated
18 one-step ECMs (15 ARDL, 3 EG). In-sample MAE 0.0521 to 0.0840. Long-run beta 0.452 to 0.460. All 15 ARDL specifications collapse to **the same estimated ECM** (MAE 0.052069), because no deterministic term survived the parameter screen.

#### 6.5.6 Champion Model: ARDL(2,1), case 3 (unrestricted constant), AIC (baseline)

| Term | Coefficient | *t* | p-value |
| :--- | :-: | :-: | :-: |
| y.L1 (λ) | **-0.1267** | -3.27 | 1.8e-03 |
| FFT.L1 | 0.0572 | 3.38 | 1.3e-03 |
| D.y.L1 | 0.4433 | 5.38 | 1.5e-06 |
| D.FFT.L0 | 0.1519 | 5.30 | 2.0e-06 |
| **LR: FFT (θ)** | **0.4518** | 12.85 | 2.5e-18 |

#### 6.5.7 Outcomes Analysis and Issues
- 8Q backtest MAE (1Q to 8Q): 0.199, 0.089, 0.083, 0.061, **0.534**, 0.202, 0.096, 0.126. Mean 0.174.
- The 5Q window (origin 2025Q1) has a large error. Old National shows the same pattern, which points to a common shock around 2025Q2 that the FFT-only model does not capture.
- The slowest adjustment in the peer set (λ = -0.127) means roughly 12.7% of any disequilibrium closes per quarter.
- The constant in a case 3 specification was dropped by the parameter screen. The champion is effectively a no-intercept model.

### 6.6 Old National Bank

#### 6.6.1 Data Treatment
- FDIC cert 3832. **First Midwest Bank (2022-02-15)** is listed as Mode A but **no adjustment appears in the modeled data**. Open issue.

#### 6.6.2 Stationarity

| Sample | Levels I(0) | First difference I(1) |
| :--- | :--- | :--- |
| 2011 to 2026 raw | ADF -1.473 (p 0.547), KPSS 0.648 (p 0.018): non-stationary | ADF -3.211 (p 0.019), KPSS 0.198 (p 0.100): stationary |
| 2011 to 2026 merger-adjusted (main) | ADF -1.206 (p 0.671), KPSS 0.651 (p 0.018): **non-stationary** | ADF -2.969 (p 0.038), KPSS 0.233 (p 0.100): **stationary** |
| 2008 to 2026 raw | ADF -1.199 (p 0.674), KPSS 0.326 (p 0.100): inconclusive | ADF -5.177 (p 9.8e-06), KPSS 0.530 (p 0.035): inconclusive |
| 2008 to 2026 merger-adjusted | ADF -1.986 (p 0.293), KPSS 0.328 (p 0.100): inconclusive | ADF -2.631 (p 0.087), KPSS 0.607 (p 0.022): non-stationary |

**Conclusion: I(1) under the default specification** in the main sample. The I(1) ADF p-value (0.038) is the closest to the threshold among the unflagged banks.

#### 6.6.3 Structural Breaks
Not tested.

#### 6.6.4 Cointegration
- **Baseline:** EG long run p 0.245; EG short run p 0.801 (both fail). Johansen trace r ≤ 0 = 18.27 (p < 0.05), r ≤ 1 = 2.33 (p > 0.10): rank 1 is supported cleanly. **ARDL(3,1) case 3 F = 17.12 (p 4.3e-08).**
- Not included in the re-specification grid.

#### 6.6.5 Specifications Estimated
2 one-step ECMs (1 ARDL, 1 Johansen). In-sample MAE 0.0858 to 0.0912. Long-run beta 0.521 to 0.541.

#### 6.6.6 Champion Model: ARDL(3,1), case 3 (unrestricted constant), AIC

| Term | Coefficient | *t* | p-value |
| :--- | :-: | :-: | :-: |
| y.L1 (λ) | **-0.3156** | -5.64 | 6.0e-07 |
| FFT.L1 | 0.1708 | 6.23 | 6.7e-08 |
| D.y.L2 | -0.2429 | -2.42 | 0.019 |
| D.FFT.L0 | 0.1697 | 3.39 | 1.3e-03 |
| **LR: FFT (θ)** | **0.5412** | 19.24 | 4.3e-26 |

#### 6.6.7 Outcomes Analysis and Issues
- 8Q backtest MAE (1Q to 8Q): 0.058, 0.092, 0.054, 0.105, **0.539**, 0.223, 0.339, 0.196. Mean 0.201.
- Large errors at 5Q to 7Q (origins 2024Q3 to 2025Q1) coincide with the M&T error spike.
- The unapplied First Midwest merger (2022) falls inside the rate-hiking cycle and may bias the post-2022 relationship.
- No re-specification grid was run.

### 6.7 SouthState Bank

#### 6.7.1 Data Treatment
- FDIC cert 33555. **CenterState Bank (2020-06-08): Mode B**, 0.5% of deposits acquired in 2020Q2. Flagged but **not excluded** from `rate_pf_clean`.
- **Atlantic Capital Bank (2022-03-01)** is listed as Mode A but **not applied** in the modeled data. Open issue.
- Note: under the 1.0% materiality rule CenterState is classified as sub-material, which follows from the placeholder deposit value (§4.3), not from actual deposits.

#### 6.7.2 Stationarity

| Sample | Levels I(0) | First difference I(1) |
| :--- | :--- | :--- |
| 2011 to 2026 raw | ADF -1.464 (p 0.551), KPSS 0.633 (p 0.020): non-stationary | ADF -4.274 (p 0.0005), KPSS 0.212 (p 0.100): stationary |
| 2011 to 2026 merger-adjusted (main) | ADF -0.972 (p 0.763), KPSS 0.633 (p 0.020): **non-stationary** | ADF -4.488 (p 0.0002), KPSS 0.239 (p 0.100): **stationary** |
| 2008 to 2026 raw | ADF -1.966 (p 0.302), KPSS 0.293 (p 0.100): inconclusive | ADF -12.412 (p 4.3e-23), KPSS 0.476 (p 0.047): inconclusive |
| 2008 to 2026 merger-adjusted | ADF -1.829 (p 0.366), KPSS 0.287 (p 0.100): inconclusive | ADF -13.100 (p 1.7e-24), KPSS 0.355 (p 0.097): stationary |

**Conclusion: I(1) under the default specification.** Not flagged.

#### 6.7.3 Structural Breaks
Not tested.

#### 6.7.4 Cointegration
- **Baseline:** EG long run p 0.383; EG short run p 0.955 (both fail). Johansen trace r ≤ 0 = 24.81 (p < 0.01), r ≤ 1 = 4.17 (p < 0.05). ARDL(4,4) case 3 F = 10.12 (p 0.0001).
- **Re-specification:** the strongest support in the peer set. EG short run with ECM lag 0 under BIC passes for `n`, `c` and `ct` (p 3.6e-05 to 0.0045). Johansen passes for every `det_order` and lag criterion (trace p < 0.01 or < 0.05). ARDL passes in every case and criterion (F 6.75 to 22.15, p < 0.001).
- Under `det_order` 0 and 1 the r ≤ 1 statistic also rejects, which taken literally points to rank 2.

#### 6.7.5 Specifications Estimated
31 one-step ECMs (15 ARDL, 3 EG, 13 Johansen). In-sample MAE 0.0588 to 0.0650, the tightest range in the peer set. Long-run beta 0.407 to 0.482.

#### 6.7.6 Champion Model: Johansen VECM (rank 1), det_order -1 (none), k_ar_diff = 2, AIC
Trace r ≤ 0 = 16.58 (p < 0.01). Tied on in-sample MAE with the FPE selection and with `det_order 0` (AIC and FPE); file order kept this row.

| Term | Coefficient | *t* | p-value |
| :--- | :-: | :-: | :-: |
| y.L1 (λ) | **-0.2145** | -3.88 | 2.8e-04 |
| FFT.L1 | 0.0930 | 4.40 | 5.1e-05 |
| D.y.L2 | -0.2556 | -2.39 | 0.020 |
| D.FFT.L2 | 0.1360 | 2.84 | 6.3e-03 |
| **LR: FFT (θ)** | **0.4338** | 13.87 | 1.3e-19 |

#### 6.7.7 Outcomes Analysis and Issues
- 8Q backtest MAE (1Q to 8Q): 0.136, 0.073, 0.071, 0.110, 0.125, 0.140, 0.093, 0.087. Mean 0.104, the **best and most stable in the peer set**.
- The champion has no contemporaneous FFT term. Pass-through starts after two quarters.
- The unapplied Atlantic Capital merger (2022) is an open data issue.

---

## 7. Outcomes Analysis: Peer Comparison

### 7.1 Rolling-Origin 8Q Backtest (MAE, pp)

| Bank | 1Q | 2Q | 3Q | 4Q | 5Q | 6Q | 7Q | 8Q | Mean |
| :--- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| First Horizon Bank | 0.247 | 0.121 | 0.085 | 0.066 | 0.174 | 0.140 | 0.154 | 0.137 | 0.140 |
| Glacier Bank | 0.176 | 0.274 | 0.177 | 0.152 | 0.148 | 0.279 | 0.354 | 0.429 | 0.248 |
| Huntington National Bank | 0.280 | 0.161 | 0.143 | 0.184 | 0.215 | 0.143 | 0.138 | 0.141 | 0.176 |
| KeyBank National Association | 0.098 | 0.097 | 0.103 | 0.064 | 0.078 | 0.119 | 0.285 | 0.195 | 0.130 |
| Manufacturers and Traders Trust Company | 0.199 | 0.089 | 0.083 | 0.061 | 0.534 | 0.202 | 0.096 | 0.126 | 0.174 |
| Old National Bank | 0.058 | 0.092 | 0.054 | 0.105 | 0.539 | 0.223 | 0.339 | 0.196 | 0.201 |
| SouthState Bank | 0.136 | 0.073 | 0.071 | 0.110 | 0.125 | 0.140 | 0.093 | 0.087 | 0.104 |

Each kQ forecast window runs from origin + 1 to 2026Q2. Because the windows overlap, the horizons are not independent tests.

### 7.2 Observations
- Out-of-sample MAE is about 2 to 3 times in-sample MAE for every bank. This is expected given dynamic forecasting, but it shows that in-sample MAE is a weak criterion for choosing the champion.
- Long-run betas cluster in two groups: about 0.53 to 0.56 (First Horizon, Huntington, Old National) and about 0.41 to 0.50 (Glacier, SouthState, M&T, KeyBank).
- No performance thresholds (acceptance criteria) have been defined yet.

### 7.3 Benchmarking
No challenger or benchmark model has been built yet, such as a static OLS beta, a cycle-specific beta, or an asymmetric ECM. Open item.

---

## 8. Model Limitations and Assumptions

| # | Limitation | Affected banks | Impact |
| :-: | :--- | :--- | :--- |
| L1 | Short sample (62 quarters, 2011Q1 to 2026Q2) lowers the power of unit-root and cointegration tests | All | High |
| L2 | Stationarity classification depends on the specification; specifications were selected to give a consistent I(0)/I(1) result | Glacier, Huntington, M&T | High |
| L3 | Results are not robust to the 2008 to 2026 sample (Appendix A1 and A2) | All | Medium |
| L4 | Merger adjustment uses placeholder inputs; four Mode A events are not applied; Mode B rows are not excluded | First Horizon, Huntington, Old National, SouthState (missing events); all (inputs) | High |
| L5 | The deposit rate is total interest expense ÷ deposits, which includes interest on borrowings and other non-deposit liabilities | All | Medium |
| L6 | Linear, symmetric pass-through. No asymmetry or zero-lower-bound nonlinearity, although 2011 to 2015 and 2020 to 2021 sit at the zero bound | All | Medium |
| L7 | Post-selection inference: coefficients screened on p < 0.05 and then re-estimated, so p-values are optimistic | All | Medium |
| L8 | Champion chosen on in-sample MAE, with ties broken mechanically; many specifications collapse to the same ECM | All (especially M&T, SouthState, KeyBank) | Medium |
| L9 | Johansen p-values are bounds; r ≤ 1 rejections (implying rank 2) are overridden by assuming rank 1 | First Horizon, Glacier, SouthState, KeyBank | Medium |
| L10 | Single regressor (FFT). No competitive, liquidity or balance-sheet drivers | All | Medium |
| L11 | Zivot-Andrews break tests failed to run or were not run | Huntington, M&T (failed); four other banks (not run) | Medium |
| L12 | The deterministic terms used in the cointegration test differ from those in the estimated ECM | Glacier, M&T | Low to medium |
| L13 | KPSS p-values are truncated at 0.10 | All | Low |

---

## 9. Validation Status and Open Issues

### 9.1 Validation Status
No independent validation has been performed. The items below should be resolved before the model is submitted for validation.

### 9.2 Open Issues Log

| ID | Issue | Bank(s) | Priority | Status |
| :-: | :--- | :--- | :-: | :-: |
| OI-1 | Replace placeholder predecessor certs and deposits in `merger_events_used.csv` with actual FDIC values; re-derive materiality | All with events | High | Open |
| OI-2 | Apply the four missing Mode A adjustments (FirstMerit, IBERIABANK, Atlantic Capital, First Midwest), or document why they were excluded | Huntington, First Horizon, SouthState, Old National | High | Open |
| OI-3 | Decide on Mode B treatment: exclude the flagged quarters, or document why they are kept | SouthState | Medium | Open |
| OI-4 | Run the cointegration re-specification grid for Huntington and Old National | Huntington, Old National | Medium | Open |
| OI-5 | Fix Zivot-Andrews failures (rank deficiency; zero-bound values) and extend the break tests to all banks | All | Medium | Open |
| OI-6 | Refit the Huntington champion without the insignificant `D.y.L1` | Huntington | Medium | Open |
| OI-7 | Reconcile the deterministic terms between the cointegration test and the estimated ECM | Glacier, M&T | Medium | Open |
| OI-8 | Investigate the shared 5Q backtest error spike (origin 2025Q1) | M&T, Old National | Medium | Open |
| OI-9 | Select the champion on out-of-sample backtest MAE (or a combination), not in-sample MAE | All | Medium | Open |
| OI-10 | Define acceptance thresholds for backtest MAE | All | Medium | Open |
| OI-11 | Build benchmark/challenger models (static beta, asymmetric ECM) | All | Medium | Open |
| OI-12 | Rerun or archive the stale KeyBank 4Q backtest, which used a non-champion model | KeyBank | Low | Open |
| OI-13 | Investigate the Glacier 2012Q1 deposit-rate spike | Glacier | Low | Open |
| OI-14 | Assess whether the First Horizon long-run trend is economically justified for projection | First Horizon | Medium | Open |
| OI-15 | Isolate deposit interest expense from total interest expense, if Call Report detail allows | All | Medium | Open |
| OI-16 | Fill the empty "ADF re-specification" placeholders in the vault documentation (2008 to 2026 merger-adjusted) | All | Low | Open |

---

## 10. Implementation and Reproducibility

### 10.1 Environment
Python with `pandas`, `numpy`, `statsmodels` (ADF, KPSS, `coint_johansen`, `VECM`, `ARDL`/`UECM`, `mackinnonp`), `scipy` and `matplotlib`. Jupyter notebooks are used for data pulls, merger adjustment and stationarity work. Package versions are not pinned yet; a `requirements.txt` should be added.

### 10.2 Execution

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
python MAE_Backtesting/run_backtest.py --horizon 8Q --bank-name All
```

### 10.3 Controls
- Scripts exit with an error and stop at the first failing step (`ECM workflow.py`).
- Banks that fail are logged and skipped in the backtest; the exit code is 2 if any were skipped.
- Merger adjustment checks are recorded in `merger_adjustment_log.md`.
- Gaps: no unit tests, no version pinning, and no data snapshot hashing.

---

## 11. Governance

| Item | Status |
| :--- | :--- |
| Model owner | Shivam Panda |
| Model inventory registration | Not registered (WIP) |
| Independent validation | Not performed |
| Ongoing monitoring plan | Not defined. Proposed: quarterly refresh after each Call Report cycle, with backtest MAE tracked against thresholds (OI-10) |
| Change management | Git version control (`Panda5130/Deposit-Beta`) |

---

## Appendix A: Stationarity Test Detail

### A.0 Main Sample: 2011Q1 to 2026Q2 (raw, before merger adjustment)

**Levels I(0):**

| Bank Name | Test | Q-statistic | p-value | PASS/FAIL |
| :--- | :-: | :-: | :-: | :-: |
| First Horizon Bank | ADF | -1.060903 | 0.730409 | FAIL |
| First Horizon Bank | KPSS | 0.640311 | 0.018972 | PASS |
| Glacier Bank | ADF | -1.684885 | 0.438916 | FAIL |
| Glacier Bank | KPSS | 0.440720 | 0.059603 | FAIL |
| Huntington National Bank | ADF | 0.916821 | 0.993306 | FAIL |
| Huntington National Bank | KPSS | 0.573670 | 0.025074 | PASS |
| KeyBank National Association | ADF | -2.320130 | 0.165558 | FAIL |
| KeyBank National Association | KPSS | 0.636798 | 0.019291 | PASS |
| Manufacturers and Traders Trust Company | ADF | 1.796809 | 0.998343 | FAIL |
| Manufacturers and Traders Trust Company | KPSS | 0.629025 | 0.019998 | PASS |
| Old National Bank | ADF | -1.472862 | 0.546891 | FAIL |
| Old National Bank | KPSS | 0.647564 | 0.018312 | PASS |
| SouthState Bank | ADF | -1.463703 | 0.551385 | FAIL |
| SouthState Bank | KPSS | 0.632615 | 0.019671 | PASS |

**First difference I(1):**

| Bank Name | Test | Q-statistic | p-value | PASS/FAIL |
| :--- | :-- | --: | --: | :-- |
| First Horizon Bank | ADF (Diff) | -3.557292 | 0.006632 | PASS |
| First Horizon Bank | KPSS (Diff) | 0.094867 | 0.100000 | FAIL |
| Glacier Bank | ADF (Diff) | -3.515144 | 0.007607 | PASS |
| Glacier Bank | KPSS (Diff) | 0.169815 | 0.100000 | FAIL |
| Huntington National Bank | ADF (Diff) | -2.320805 | 0.165346 | FAIL |
| Huntington National Bank | KPSS (Diff) | 0.246826 | 0.100000 | FAIL |
| KeyBank National Association | ADF (Diff) | -3.348473 | 0.012846 | PASS |
| KeyBank National Association | KPSS (Diff) | 0.096688 | 0.100000 | FAIL |
| Manufacturers and Traders Trust Company | ADF (Diff) | -2.626846 | 0.087575 | FAIL |
| Manufacturers and Traders Trust Company | KPSS (Diff) | 0.114222 | 0.100000 | FAIL |
| Old National Bank | ADF (Diff) | -3.210515 | 0.019384 | PASS |
| Old National Bank | KPSS (Diff) | 0.197643 | 0.100000 | FAIL |
| SouthState Bank | ADF (Diff) | -4.273840 | 0.000493 | PASS |
| SouthState Bank | KPSS (Diff) | 0.211500 | 0.100000 | FAIL |

**Flagged-bank ADF re-specification (levels):**

| Bank | Regression | Lag selection | Q-stat | p-value |
| :--- | :-: | :-: | :-: | :-: |
| Glacier Bank | c | AIC | -1.815232 | 0.372926 |
| Glacier Bank | n | AIC | -1.107472 | 0.243035 |
| Glacier Bank | c | BIC | -1.815232 | 0.372926 |
| Glacier Bank | n | BIC | -1.107472 | 0.243035 |
| Glacier Bank | c | t-stat | -1.815232 | 0.372926 |
| Glacier Bank | n | t-stat | -1.107472 | 0.243035 |
| Huntington National Bank | c | AIC | 0.825702 | 0.992040 |
| Huntington National Bank | n | AIC | 1.288890 | 0.949505 |
| Huntington National Bank | c | BIC | -1.467271 | 0.549635 |
| Huntington National Bank | n | BIC | -0.381929 | 0.543925 |
| Huntington National Bank | c | t-stat | 0.825702 | 0.992040 |
| Huntington National Bank | n | t-stat | 1.081504 | 0.926678 |
| Manufacturers and Traders Trust Company | c | AIC | 3.848277 | 1.000000 |
| Manufacturers and Traders Trust Company | n | AIC | 2.731905 | 0.999282 |
| Manufacturers and Traders Trust Company | c | BIC | 3.848277 | 1.000000 |
| Manufacturers and Traders Trust Company | n | BIC | -0.873958 | 0.339627 |
| Manufacturers and Traders Trust Company | c | t-stat | 3.848277 | 1.000000 |
| Manufacturers and Traders Trust Company | n | t-stat | 2.731905 | 0.999282 |

### A.1 Extended Sample: 2008Q1 to 2026Q3 (raw)
All banks show mixed or insufficient evidence for I(0). Results on first differences are also inconclusive.

| Bank Name | Test | Test Statistic | p-value | Result |
| :--- | :-: | :-: | :-: | :-: |
| First Horizon Bank | ADF | -1.805291 | 0.377838 | FAIL |
| First Horizon Bank | KPSS | 0.244523 | 0.100000 | FAIL |
| Glacier Bank | ADF | -3.440396 | 0.009656 | PASS |
| Glacier Bank | KPSS | 0.290829 | 0.100000 | FAIL |
| Huntington National Bank | ADF | -1.693522 | 0.434453 | FAIL |
| Huntington National Bank | KPSS | 0.287357 | 0.100000 | FAIL |
| KeyBank National Association | ADF | -1.747726 | 0.406705 | FAIL |
| KeyBank National Association | KPSS | 0.292908 | 0.100000 | FAIL |
| Manufacturers and Traders Trust Company | ADF | -1.922125 | 0.321726 | FAIL |
| Manufacturers and Traders Trust Company | KPSS | 0.282536 | 0.100000 | FAIL |
| Old National Bank | ADF | -1.199373 | 0.673865 | FAIL |
| Old National Bank | KPSS | 0.326018 | 0.100000 | FAIL |
| SouthState Bank | ADF | -1.966362 | 0.301514 | FAIL |
| SouthState Bank | KPSS | 0.292720 | 0.100000 | FAIL |

| Bank Name | Test | Test Statistic | p-value | Result |
| :--- | :-: | :-: | :-: | :-: |
| First Horizon Bank | ADF (Diff) | -3.771440 | 3.213421e-03 | PASS |
| First Horizon Bank | KPSS (Diff) | 0.499750 | 4.172303e-02 | PASS |
| Glacier Bank | ADF (Diff) | -4.210950 | 6.313356e-04 | PASS |
| Glacier Bank | KPSS (Diff) | 0.490107 | 4.389475e-02 | PASS |
| Huntington National Bank | ADF (Diff) | -1.943275 | 3.119850e-01 | FAIL |
| Huntington National Bank | KPSS (Diff) | 0.546272 | 3.124503e-02 | PASS |
| KeyBank National Association | ADF (Diff) | -2.945576 | 4.029910e-02 | PASS |
| KeyBank National Association | KPSS (Diff) | 0.402187 | 7.621240e-02 | FAIL |
| Manufacturers and Traders Trust Company | ADF (Diff) | -4.706779 | 8.171940e-05 | PASS |
| Manufacturers and Traders Trust Company | KPSS (Diff) | 0.502988 | 4.099363e-02 | PASS |
| Old National Bank | ADF (Diff) | -5.176730 | 9.806538e-06 | PASS |
| Old National Bank | KPSS (Diff) | 0.530131 | 3.488047e-02 | PASS |
| SouthState Bank | ADF (Diff) | -12.412110 | 4.320502e-23 | PASS |
| SouthState Bank | KPSS (Diff) | 0.476047 | 4.706158e-02 | PASS |

### A.2 Merger-Adjusted Samples

#### A.2.1 2008 to 2026, Merger-Adjusted

**I(0):**

| Bank Name | Test | Q-Stat | P-Value | Pass/Fail |
| :--- | :-- | :-- | :-- | :-- |
| Manufacturers and Traders Trust Company | ADF | -1.407901 | 0.578482 | FAIL |
| Manufacturers and Traders Trust Company | KPSS | 0.284572 | 0.100000 | FAIL |
| Old National Bank | ADF | -1.986054 | 0.292721 | FAIL |
| Old National Bank | KPSS | 0.327791 | 0.100000 | FAIL |
| First Horizon Bank | ADF | -2.133826 | 0.231132 | FAIL |
| First Horizon Bank | KPSS | 0.244639 | 0.100000 | FAIL |
| Huntington National Bank | ADF | -2.149955 | 0.224907 | FAIL |
| Huntington National Bank | KPSS | 0.289711 | 0.100000 | FAIL |
| KeyBank National Association | ADF | -2.703219 | 0.073483 | FAIL |
| KeyBank National Association | KPSS | 0.293966 | 0.100000 | FAIL |
| Glacier Bank | ADF | -3.871115 | 0.002258 | PASS |
| Glacier Bank | KPSS | 0.289632 | 0.100000 | FAIL |
| SouthState Bank | ADF | -1.829126 | 0.366100 | FAIL |
| SouthState Bank | KPSS | 0.286655 | 0.100000 | FAIL |

**I(1):**

| Bank Name | Test | Q-Stat | P-Value | Pass/Fail |
| :--- | :-- | :-- | :-- | :-- |
| Manufacturers and Traders Trust Company | ADF (Diff) | -3.098538 | 2.666160e-02 | PASS |
| Manufacturers and Traders Trust Company | KPSS (Diff) | 0.500608 | 4.152962e-02 | PASS |
| Old National Bank | ADF (Diff) | -2.631116 | 8.673520e-02 | FAIL |
| Old National Bank | KPSS (Diff) | 0.606700 | 2.202732e-02 | PASS |
| First Horizon Bank | ADF (Diff) | -3.614234 | 5.494670e-03 | PASS |
| First Horizon Bank | KPSS (Diff) | 0.518592 | 3.747927e-02 | PASS |
| Huntington National Bank | ADF (Diff) | -5.327346 | 4.804869e-06 | PASS |
| Huntington National Bank | KPSS (Diff) | 0.556937 | 2.884296e-02 | PASS |
| KeyBank National Association | ADF (Diff) | -3.229156 | 1.835786e-02 | PASS |
| KeyBank National Association | KPSS (Diff) | 0.400140 | 7.709483e-02 | FAIL |
| Glacier Bank | ADF (Diff) | -4.894380 | 3.576351e-05 | PASS |
| Glacier Bank | KPSS (Diff) | 0.419413 | 6.878748e-02 | FAIL |
| SouthState Bank | ADF (Diff) | -13.099538 | 1.721277e-24 | PASS |
| SouthState Bank | KPSS (Diff) | 0.355030 | 9.653858e-02 | FAIL |

KeyBank, Glacier and SouthState show I(1) stationarity with inconclusive evidence for I(0). Old National shows non-stationarity at I(1) and inconclusive evidence for I(0). The other banks show insufficient or inconclusive evidence at both orders. The ADF re-specification for this sample has not been documented yet (OI-16).

#### A.2.2 2011 to 2026, Merger-Adjusted (main modeling sample)

**I(0), default specification:**

| Bank Name | Test | Q-Stat | P-Value | Pass/Fail |
| --- | --- | --- | --- | --- |
| Manufacturers and Traders Trust Company | ADF | 1.870028 | 0.998478 | FAIL |
| Manufacturers and Traders Trust Company | KPSS | 0.631062 | 0.019813 | PASS |
| Old National Bank | ADF | -1.206334 | 0.670865 | FAIL |
| Old National Bank | KPSS | 0.651021 | 0.017998 | PASS |
| First Horizon Bank | ADF | -1.979647 | 0.295568 | FAIL |
| First Horizon Bank | KPSS | 0.639535 | 0.019042 | PASS |
| Huntington National Bank | ADF | 0.952043 | 0.993733 | FAIL |
| Huntington National Bank | KPSS | 0.645216 | 0.018526 | PASS |
| KeyBank National Association | ADF | -1.641734 | 0.461355 | FAIL |
| KeyBank National Association | KPSS | 0.639624 | 0.019034 | PASS |
| Glacier Bank | ADF | -1.062503 | 0.729791 | FAIL |
| Glacier Bank | KPSS | 0.443122 | 0.058568 | FAIL |
| SouthState Bank | ADF | -0.971912 | 0.763370 | FAIL |
| SouthState Bank | KPSS | 0.633147 | 0.019623 | PASS |

**I(1), default specification:**

| Bank Name | Test | Q-Stat | P-Value | Pass/Fail |
| --- | --- | --- | --- | --- |
| Manufacturers and Traders Trust Company | ADF (Diff) | -2.492835 | 1.172274e-01 | FAIL |
| Manufacturers and Traders Trust Company | KPSS (Diff) | 0.107946 | 1.000000e-01 | FAIL |
| Old National Bank | ADF (Diff) | -2.969027 | 3.788989e-02 | PASS |
| Old National Bank | KPSS (Diff) | 0.232648 | 1.000000e-01 | FAIL |
| First Horizon Bank | ADF (Diff) | -3.420248 | 1.028770e-02 | PASS |
| First Horizon Bank | KPSS (Diff) | 0.103450 | 1.000000e-01 | FAIL |
| Huntington National Bank | ADF (Diff) | -2.357536 | 1.540820e-01 | FAIL |
| Huntington National Bank | KPSS (Diff) | 0.170974 | 1.000000e-01 | FAIL |
| KeyBank National Association | ADF (Diff) | -3.551664 | 6.755268e-03 | PASS |
| KeyBank National Association | KPSS (Diff) | 0.098900 | 1.000000e-01 | FAIL |
| Glacier Bank | ADF (Diff) | -9.773145 | 7.048406e-17 | PASS |
| Glacier Bank | KPSS (Diff) | 0.169244 | 1.000000e-01 | FAIL |
| SouthState Bank | ADF (Diff) | -4.488455 | 2.063040e-04 | PASS |
| SouthState Bank | KPSS (Diff) | 0.239026 | 1.000000e-01 | FAIL |

**ADF re-specification, I(0):**

| Bank | Regression | Lag selection | Q-stat | p-value |
| --- | --- | --- | --- | --- |
| Glacier Bank | c | AIC | -1.750662 | 0.405217 |
| Glacier Bank | n | AIC | -0.712748 | 0.407239 |
| Glacier Bank | c | BIC | -1.047006 | 0.735736 |
| Glacier Bank | n | BIC | -0.530700 | 0.483464 |
| Glacier Bank | c | t-stat | -1.750662 | 0.405217 |
| Glacier Bank | n | t-stat | -0.712748 | 0.407239 |
| Huntington National Bank | c | AIC | 2.574499 | 0.999070 |
| Huntington National Bank | n | AIC | 2.439859 | 0.997643 |
| Huntington National Bank | c | BIC | -1.031970 | 0.741426 |
| Huntington National Bank | n | BIC | -0.283604 | 0.582380 |
| Huntington National Bank | c | t-stat | 2.574499 | 0.999070 |
| Huntington National Bank | n | t-stat | 2.439859 | 0.997643 |
| Manufacturers and Traders Trust Company | c | AIC | 2.764095 | 1.000000 |
| Manufacturers and Traders Trust Company | n | AIC | 2.421510 | 0.997479 |
| Manufacturers and Traders Trust Company | c | BIC | -1.833185 | 0.364115 |
| Manufacturers and Traders Trust Company | n | BIC | -0.937330 | 0.313498 |
| Manufacturers and Traders Trust Company | c | t-stat | 2.764095 | 1.000000 |
| Manufacturers and Traders Trust Company | n | t-stat | 2.421510 | 0.997479 |

**ADF re-specification, I(1):**

| Bank | Regression | Lag selection | Q-stat | p-value |
| --- | --- | --- | --- | --- |
| Glacier Bank | c | AIC | -2.639751 | 8.505659e-02 |
| Glacier Bank | n | AIC | -2.760372 | 5.625891e-03 |
| Glacier Bank | c | BIC | -9.605240 | 1.873819e-16 |
| Glacier Bank | n | BIC | -9.679696 | 5.102918e-17 |
| Glacier Bank | c | t-stat | -3.558846 | 6.598327e-03 |
| Glacier Bank | n | t-stat | -3.584903 | 3.554124e-04 |
| Huntington National Bank | c | AIC | -1.966777 | 3.013276e-01 |
| Huntington National Bank | n | AIC | -1.577809 | 1.079110e-01 |
| Huntington National Bank | c | BIC | -3.978251 | 1.528774e-03 |
| Huntington National Bank | n | BIC | -3.960377 | 8.561507e-05 |
| Huntington National Bank | c | t-stat | -1.966777 | 3.013276e-01 |
| Huntington National Bank | n | t-stat | -1.577809 | 1.079110e-01 |
| Manufacturers and Traders Trust Company | c | AIC | -2.288571 | 1.756804e-01 |
| Manufacturers and Traders Trust Company | n | AIC | -1.920927 | 5.225037e-02 |
| Manufacturers and Traders Trust Company | c | BIC | -2.855342 | 5.079298e-02 |
| Manufacturers and Traders Trust Company | n | BIC | -2.835059 | 4.479075e-03 |
| Manufacturers and Traders Trust Company | c | t-stat | -3.965140 | 1.604461e-03 |
| Manufacturers and Traders Trust Company | n | t-stat | -1.920927 | 5.225037e-02 |

**KPSS re-specification, I(0):**

| Bank | Regression | Bandwidth | Q-stat | p-value |
| --- | --- | --- | --- | --- |
| Glacier Bank | c | auto | 0.465840 | 0.049360 |
| Glacier Bank | ct | auto | 0.242657 | 0.010000 |
| Glacier Bank | c | long | 0.264913 | 0.100000 |
| Glacier Bank | ct | long | 0.146123 | 0.049898 |
| Glacier Bank | c | short | 0.465840 | 0.049360 |
| Glacier Bank | ct | short | 0.242657 | 0.010000 |
| Huntington National Bank | c | auto | 0.585036 | 0.023997 |
| Huntington National Bank | ct | auto | 0.193670 | 0.018374 |
| Huntington National Bank | c | long | 0.382595 | 0.084657 |
| Huntington National Bank | ct | long | 0.130534 | 0.078641 |
| Huntington National Bank | c | short | 0.678562 | 0.015494 |
| Huntington National Bank | ct | short | 0.193670 | 0.018374 |
| Manufacturers and Traders Trust Company | c | auto | 0.573902 | 0.025022 |
| Manufacturers and Traders Trust Company | ct | auto | 0.187843 | 0.020559 |
| Manufacturers and Traders Trust Company | c | long | 0.380546 | 0.085541 |
| Manufacturers and Traders Trust Company | ct | long | 0.126572 | 0.085978 |
| Manufacturers and Traders Trust Company | c | short | 0.663984 | 0.016820 |
| Manufacturers and Traders Trust Company | ct | short | 0.187843 | 0.020559 |

**KPSS re-specification, I(1):**

| Bank | Regression | Bandwidth | Q-stat | p-value |
| --- | --- | --- | --- | --- |
| Glacier Bank | c | auto | 0.176341 | 0.1 |
| Glacier Bank | ct | auto | 0.066651 | 0.1 |
| Glacier Bank | c | long | 0.165459 | 0.1 |
| Glacier Bank | ct | long | 0.076851 | 0.1 |
| Glacier Bank | c | short | 0.160084 | 0.1 |
| Glacier Bank | ct | short | 0.062276 | 0.1 |
| Huntington National Bank | c | auto | 0.181045 | 0.1 |
| Huntington National Bank | ct | auto | 0.055112 | 0.1 |
| Huntington National Bank | c | long | 0.179397 | 0.1 |
| Huntington National Bank | ct | long | 0.065291 | 0.1 |
| Huntington National Bank | c | short | 0.181045 | 0.1 |
| Huntington National Bank | ct | short | 0.055112 | 0.1 |
| Manufacturers and Traders Trust Company | c | auto | 0.115464 | 0.1 |
| Manufacturers and Traders Trust Company | ct | auto | 0.052761 | 0.1 |
| Manufacturers and Traders Trust Company | c | long | 0.129636 | 0.1 |
| Manufacturers and Traders Trust Company | ct | long | 0.066783 | 0.1 |
| Manufacturers and Traders Trust Company | c | short | 0.115464 | 0.1 |
| Manufacturers and Traders Trust Company | ct | short | 0.052761 | 0.1 |

**Final classification (2011 to 2026 merger-adjusted):**

| Bank Name | Order | ADF Spec | ADF Q-stat | ADF p-value | KPSS Spec | KPSS Q-stat | KPSS p-value | Conclusion |
| :--- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| First Horizon Bank | I(0) | default | -1.979647 | 0.295568 | default | 0.639535 | 0.019042 | Non-Stationary |
| First Horizon Bank | I(1) | default | -3.420248 | 1.028770e-02 | default | 0.103450 | 0.100000 | Stationary |
| Old National Bank | I(0) | default | -1.206334 | 0.670865 | default | 0.651021 | 0.017998 | Non-Stationary |
| Old National Bank | I(1) | default | -2.969027 | 3.788989e-02 | default | 0.232648 | 0.100000 | Stationary |
| KeyBank National Association | I(0) | default | -1.641734 | 0.461355 | default | 0.639624 | 0.019034 | Non-Stationary |
| KeyBank National Association | I(1) | default | -3.551664 | 6.755268e-03 | default | 0.098900 | 0.100000 | Stationary |
| SouthState Bank | I(0) | default | -0.971912 | 0.763370 | default | 0.633147 | 0.019623 | Non-Stationary |
| SouthState Bank | I(1) | default | -4.488455 | 2.063040e-04 | default | 0.239026 | 0.100000 | Stationary |
| Glacier Bank | I(0) | c / BIC | -1.047006 | 0.735736 | c / auto | 0.465840 | 0.049360 | Non-Stationary |
| Glacier Bank | I(1) | c / BIC | -9.605240 | 1.873819e-16 | c / auto | 0.176341 | 0.100000 | Stationary |
| Huntington National Bank | I(0) | c / BIC | -1.031970 | 0.741426 | c / auto | 0.585036 | 0.023997 | Non-Stationary |
| Huntington National Bank | I(1) | c / BIC | -3.978251 | 1.528774e-03 | c / auto | 0.181045 | 0.100000 | Stationary |
| Manufacturers and Traders Trust Company | I(0) | c / t-stat | 2.764095 | 1.000000 | c / auto | 0.573902 | 0.025022 | Non-Stationary |
| Manufacturers and Traders Trust Company | I(1) | c / t-stat | -3.965140 | 1.604461e-03 | c / auto | 0.115464 | 0.100000 | Stationary |

**Specification choice for flagged banks:**
- The constant (`c`) is kept in every ADF choice. The levels have a nonzero mean, so dropping it would bias the I(0) test toward non-stationarity.
- Within each bank and test, the same specification is used for I(0) and I(1).
- KPSS uses `c` / auto for all three banks. Every `c` / auto I(1) result has p = 0.100.
- Glacier and Huntington use ADF `c` / BIC. M&T uses `c` / t-stat, because `c` / BIC narrowly misses at I(1) (p = 0.0508).
- Uniform alternative: ADF `n` / BIC for all three banks gives the same classification. It is not preferred, because removing the constant on levels favors the non-stationary I(0) result.

---

## Appendix B: Artifacts

| Artifact | Location |
| :--- | :--- |
| Actual vs. predicted charts, every estimated specification | `Actuals vs Predictions/<bank>/` |
| MAE stability bar charts and tables | `MAE_Backtesting/output/<bank>/MAE_backtest_8Q.{png,csv}` |
| MAE stability summary, all banks | `MAE_Backtesting/output/backtest_summary_8Q.csv` |
| Full coefficient tables, all estimated ECMs | `ECM estimation results.csv` |
| In-sample MAE, all estimated ECMs | `estimation result summary.csv` |
| Merger event inputs and log | `merger_events_raw.csv`, `merger_events_used.csv`, `merger_adjustment_log.md` |

---

