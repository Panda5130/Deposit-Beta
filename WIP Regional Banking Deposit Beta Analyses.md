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
| 0 (WIP) | 2026-10-30 | Rebuilt the data on deposit interest expense only (`EDEPDOMQ` + `EDEPFORQ`) over a two-point average of total deposits, with full pro forma backfill for every merger of 1% or more since 2007 using real FDIC certs. This fixed the Glacier 2012, Huntington 2021Q1 and Old National 2025Q2 anomalies. Re-ran cointegration, re-specification and estimation for all seven banks, with deterministic terms matched to each test and insignificant short-run lags pruned; new champions for every bank. Added Zivot-Andrews tests for all banks, a many-start-date backtest with horizon-aware, peer-derived limits and a no-change skill test, and per-bank figures, with many-start-date backtest bar charts (model vs. no-change, with band limits); Figure 1 regenerated from `EDA1_Stationarity_Tests.ipynb`. Removed the Key Open Issues summary; issues are tracked in §8 and §9. |
| 0.1 (WIP) | 2026-10-31 | Added the rolling-origin long-run beta stability backtest (`Beta_Backtesting/`): method (§5.6), per-bank results and figures (§6.x.7), peer comparison (§7.5), limitation L17 and a beta-stability threshold issue. Folded in the root-cause work from PR #11: an FFT builder with complete quarters only and a projection layer with the trend freeze (§3.3, §4.1, §5.7, §10.2); Gregory-Hansen break tests and seven challenger models (§5.3, §6.x.4, §7.4); EG long-run specifications now carry their short-run lags (§5.5), which re-specifies Huntington (Red → Green), changes the Old National champion and relabels KeyBank's; the beta stability test from 2016Q1 with a rating (§5.6, §7.5); and an optional out-of-sample model choice, not adopted (§5.5, §7.6). Issues #2, #4, #5, #6, #7 and #10 closed. |
| 0.2 (WIP) | 2026-11-11 | Champions are now chosen out of sample (§5.5), over the original specifications and one asymmetric variant of each (long-run FFT⁺/FFT⁻, short-run ΔFFT and Δy split by sign, λ split by the sign of the equilibrium error; §3.2). Six of seven champions change; KeyBank's is asymmetric. Added the realized-beta backtest (§5.6, §7.7), which replaces the 8-start-date beta view. Issues #1 and #13 closed by PR #15. The deposit rate keeps the 2-point average; a 4-point trailing average was tested and rejected (§4.2). |

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

Mode A and Mode B are defined in §4.3.

### 1.3 Summary of Current Results (2011Q1 to 2026Q2, pro forma)
Every bank has at least one specification that is cointegrated with the federal funds rate at the 5% level, although for Huntington and Old National only after re-specification. Each specification that passes also gets one asymmetric variant (§3.2). The champion is chosen out of sample: the most parsimonious admissible model within one standard error of the best many-start-date MAE (§5.5). The MAE rating is the governing many-start-date backtest rating, the skill ratio is the worst ratio of h-step MAE to the no-change forecast's, and the beta rating is the long-run beta stability rating from 2016Q1 (§5.6).

| Bank | Selected specification | Speed of adjustment (λ) | Long-run deposit beta (θ) | In-sample MAE (pp) | Many-start-date mean h-step MAE (pp) | Worst skill ratio | MAE rating | Beta stability rating |
| :--- | :--- | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| First Horizon Bank | Johansen VECM (rank 1), k_ar_diff = 1, det_order -1, BIC | -0.228 | 0.477 | 0.0720 | 0.284 | 0.73 | Green | Green |
| Glacier Bank | Johansen VECM (rank 1), k_ar_diff = 1, det_order 1, BIC | -0.158 | 0.277 | 0.0310 | 0.263 | 1.19 | Red | Red |
| Huntington National Bank | EG long run, trend `n`, AIC (ADF lag=1, ECM lag=3) | -0.066 | 0.463 | 0.0234 | 0.221 | 0.49 | Green | Green |
| KeyBank National Association | ARDL(2,1), case 1, BIC, asymmetric | -0.089 (above) / -0.331 (below) | 0.402 | 0.0268 | 0.126 | 0.37 | Green | Red |
| Manufacturers and Traders Trust Company | EG long run, trend `n`, AIC (ADF lag=1, ECM lag=4) | -0.195 | 0.402 | 0.0499 | 0.275 | 0.74 | Green | Red |
| Old National Bank | Johansen VECM (rank 1), k_ar_diff = 1, det_order -1, fixed | -0.135 | 0.419 | 0.0414 | 0.263 | 0.67 | Green | Amber |
| SouthState Bank | ARDL(3,2), case 4, BIC | -0.165 | 0.524 | 0.0347 | 0.197 | 0.60 | Green | Red |

Long-run betas fall between 0.28 (Glacier) and 0.52 (SouthState). Six series are I(1) under the default unit-root specification; Glacier is flagged (KPSS I(0) p 0.057).

- **Six of seven champions change** from the in-sample rule used in version 0.1; Huntington keeps its champion (§7.6). Every new champion has the same number of parameters as the version 0.1 champion or fewer.
- **KeyBank's champion is asymmetric:** it adjusts toward equilibrium almost four times faster when its deposit rate is below equilibrium than when above (λ⁻ −0.331 vs λ⁺ −0.089), and its short-run ΔFFT and Δy terms are split by sign (§6.4.6).
- **Glacier is Red on MAE:** its new champion loses to the no-change forecast at 5Q (skill ratio 1.19). Glacier, M&T, SouthState and KeyBank are Red on beta stability (§7.5).
- MAE ratings use limits set from the new champions as a peer group, which are looser at 1–2Q than version 0.1's (§7.1).

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

**Asymmetric variants.** Each specification that passes the model screen (§5.5) also gets one fully split variant:

$$\Delta y_t = \lambda^+ ect^+_{t-1} + \lambda^- ect^-_{t-1} + \sum_i (\gamma^+_i \Delta x^+_{t-i} + \gamma^-_i \Delta x^-_{t-i}) + \sum_j (\phi^+_j \Delta y^+_{t-j} + \phi^-_j \Delta y^-_{t-j}) + \varepsilon_t$$

- $ect_{t-1} = y_{t-1} - c - \delta t - \theta^+ x^+_{t-1} - \theta^- x^-_{t-1}$, with deterministic terms as in the original specification. $ect^+ = \max(ect, 0)$ and $ect^- = \min(ect, 0)$: λ⁺ applies when the deposit rate is above equilibrium and λ⁻ when below.
- $\Delta x^+_t = \max(\Delta x_t, 0)$ and $\Delta x^-_t = \min(\Delta x_t, 0)$, and the same for Δy. Like the symmetric terms, these are single-quarter changes.
- The long run uses partial sums, $x^+_t = x_0 + \sum_{s \le t} \max(\Delta x_s, 0)$ and $x^-_t = \sum_{s \le t} \min(\Delta x_s, 0)$. They cumulate because the level of FFT is itself a running sum of its changes; with the starting level in $x^+$, $x^+_t + x^-_t = x_t$ exactly, so the variant nests the symmetric model even without a constant.
- The Σ over i and j are the usual sums over lags, as in the symmetric form.

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
| 7b | Asymmetric variant of each surviving specification | `ECM asymmetric variants.py` | `ECM asymmetric estimation results.csv`, `asymmetric estimation result summary.csv`, `ECM asymmetric tests.csv` |
| 8 | Out-of-sample champion choice, backtests and ratings | `MAE_Backtesting/run_backtest.py`, `backtest.py` | `MAE_Backtesting/output/out_of_sample/` |
| 8b | Long-run beta stability backtest and rating; realized-beta backtest (`--realized`) | `Beta_Backtesting/run_beta_backtest.py`, `beta_backtest.py` | `Beta_Backtesting/output/out_of_sample/` |
| 8c | Optional in-sample model choice and comparison | `run_backtest.py --select in-sample`, `MAE_Backtesting/compare_selection.py` | `MAE_Backtesting/output/`, `Beta_Backtesting/output/` |
| 8d | Break tests and challenger models | `model_form/run_model_form.py` (`gregory_hansen.py`, `challengers.py`) | `model_form/output/` |
| 9 | Actual vs. predicted charts | `plotting_workflow.py`, `bank_plots.py` | `Actuals vs Predictions/<bank>/*.png` |
| 10 | Unit-root and structural-break diagnostics | `diagnostics/stationarity_and_breaks.py` | `diagnostics/*.csv` |
| 11 | Documentation figures | `docs/make_figures.py` | `docs/figures/` |
| 12 | Scenario projection with trend freeze | `projection/project.py` with a scenario CSV of FFT by quarter | `projection/output/<scenario>_projection.csv` |

Steps 5 to 7b are run together by `ECM workflow.py`. Steps 1b, 7b and 12 have tests: `python -m pytest data_build projection ecm_tests`.

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
3. **Average deposits:** mean of the current and previous quarter-end `DEP`. No calendar-year averaging, so there is no look-ahead. A trailing 4-point average (quarter-ends t to t−3) was tested on 2026-11-06 and rejected: it centres the denominator about 1.5 quarters back, and it raised mean h-step MAE for five of seven banks under both selection rules.
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
- KPSS p-values come from a lookup table bounded at 0.10. A reported 0.100 means "at least 0.10". The bound comes from the function used, `statsmodels.tsa.stattools.kpss`: it interpolates the p-value from the critical values in Table 1 of Kwiatkowski et al. (1992), which cover only the 10%, 5%, 2.5% and 1% levels, and returns the boundary value, with an `InterpolationWarning`, when the statistic falls outside that table. The p-value is therefore bounded below at 0.01 as well: a reported 0.010 means "at most 0.01".
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
1. **Model screen:** keep every specification whose cointegration test p-value is below α = 0.05 (tests and grid in §5.4). A Johansen VECM takes the r ≤ 0 trace result of the same specification. A bounded Johansen p-value "<x" passes when x ≤ α.
2. **Parameter screen:** within each surviving specification, keep short-run terms with coefficient p-value < 0.05. Deterministic terms are set by the test specification (`n` / case 1 / det_order -1: none; `c` / cases 2–3 / det_order 0: constant; `ct` / cases 4–5 / det_order 1: constant and trend) and are not screened (cases as in the §5.4 table).
3. **Mapping to a one-step ECM:** surviving deterministic terms, short-run lags, and the error-correction term (`ect.L1`, `y.L1` or VECM `D.y: ec1`) define the regressors. Specifications without a surviving error-correction term are dropped. `EG_LongRun` is treated as error-correcting by construction. Its short-run candidates are the D.y and D.FFT lags of the Engle-Granger second-step regression of the same specification, screened in step 2 like any other short-run term.
4. **Estimation:** one-step OLS ECM (§3.2), with long-run coefficients and delta-method standard errors. Short-run lags with p ≥ 0.05 are then removed one at a time (largest p first) and the model refit. λ, the long-run regressor and the deterministic terms are never removed.
5. **Asymmetric variants (`ECM asymmetric variants.py`):** each specification that passes step 1 gets one fully split variant (§3.2), built from its full pre-screen lag set. No new cointegration test is run, and the original results are not changed.
   - **Fit:** a linear one-step fit with the long-run and short-run splits gives starting values. λ⁺, λ⁻, θ± and the deterministic terms are then fitted by nonlinear least squares with the regime indicator (sign of ect) held fixed, and the indicator is recomputed until it stops changing (at most 20 passes). If a regime has fewer than 6 quarters, λ stays symmetric.
   - **Pruning by pairs:** the + and − terms of a short-run lag are dropped together, highest joint-F p-value first, while that p-value is ≥ 0.05. λ± and θ± can't be dropped; a pair collapses to one symmetric term when a Wald test doesn't reject equality at 5%. A model never keeps only one of its + or − terms.
   - Wald tests of λ⁺ = λ⁻, θ⁺ = θ⁻, Σγ⁺ = Σγ⁻ and Σφ⁺ = Σφ⁻ are reported in `ECM asymmetric tests.csv`.
6. **Champion choice (default: out of sample; `--select out-of-sample`):** over the original and asymmetric candidates.
   - **Admissibility:** λ (λ⁺ and λ⁻) in (−1, 0) and θ (θ⁺ and θ⁻) in [0, 1].
   - **Ranking:** by mean many-start-date h-step MAE (h = 1 to N, start dates from 2016Q1, §5.6).
   - **Pick:** the model with the fewest parameters among those within one standard error of the best. The standard error is Newey-West with N−1 lags over the start dates with all N steps.
   - **Tie-break:** asymmetric > EG > ARDL > Johansen, then file order.
   - The default is set in one place, `DEFAULT_SELECT` in `MAE_Backtesting/backtest.py`, and every consumer follows it.
7. **Optional in-sample rule (`--select in-sample`):** lowest in-sample MAE of Δy per bank, the rule used up to version 0.1. It reproduces version 0.1's champions exactly (§7.6).

Out-of-sample selection is the default because the asymmetric variants have more parameters: ranking on in-sample MAE would reward them for fitting noise. Selecting on the governing backtest does make that backtest somewhat optimistic for the chosen models.

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
- For an asymmetric champion with θ split, the rating covers θ⁺ and θ⁻ and the worse rating counts.
- Per-start-date θ is cached (`Beta_Backtesting/output/cache/`). The backtest caches are keyed on the fitted terms as well as the model label, so a change to a model's terms is never served stale errors.

**Realized-beta backtest (descriptive, not rated).** It replaces the 8-start-date beta view.
- **Pairs:** every start date t from 2016Q1 and horizon h = 1 to 8 where |FFT_{t+h} − FFT_t| ≥ 0.25 pp, so the ratio isn't blown up when FFT barely moves.
- **Actual beta:** (y_{t+h} − y_t) ÷ (FFT_{t+h} − FFT_t). At h = 1 this is Δy_t ÷ ΔFFT_t.
- **Model-implied beta:** (ŷ_{t+h} − y_t) ÷ (FFT_{t+h} − FFT_t), from the same dynamic forecast with realized FFT as the MAE backtest.
- The chart shows the mean actual and mean implied beta per horizon, each over its own start dates, with the long-run θ at those start dates on a second axis for reference (§7.7).

**Supplementary test: single-window 8Q backtest.** For each k = 1 to 8, one forecast from start date T−k to T, with MAE averaged over its k quarters. Each kQ figure rests on one start date. Rated Green (mean ≤ 0.15 pp and below the no-change mean), Amber (mean 0.15–0.25 pp, or beats no-change on fewer than 6 of 8 horizons) or Red (mean > 0.25 pp, or any horizon > 0.50 pp).

### 5.7 Key Assumptions
- FFT is weakly exogenous to each bank's deposit rate (single-equation ECM).
- One cointegrating vector (rank 1) between the deposit rate and FFT.
- Linear, symmetric pass-through: no asymmetry between rising and falling rates, and no threshold at the zero lower bound. An asymmetric-λ challenger is tested in §7.4.
- Parameters are stable over 2011 to 2026, apart from any deterministic trend.
- Deposit interest expense ÷ total deposits (interest-bearing and non-interest-bearing) is an adequate measure of the deposit rate, giving a total-deposit beta.
- For projection, a deterministic trend in the long-run relation is frozen at its end-of-sample value: for every quarter after T the trend regressor is held at its value at T (62 at 2026Q2, counting from 1 at 2011Q1). The equilibrium is therefore $c + \delta T + \theta x$, and with FFT held flat a projection converges to that level instead of drifting by δ per quarter. This is implemented in `projection/project.py` and tested in `projection/test_project.py`. It affects the Glacier and SouthState champions; champions without a trend are unchanged.

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
Zivot-Andrews on levels, 2011 to 2026 (AIC lags, max 4): `c`: -6.27, p 5.4e-04, break 2022Q3; `t`: -4.80, p 0.019, break 2021Q4; `ct`: -5.07, p 0.051, break 2023Q1. The unit root is rejected when a 2022 level break is allowed, mirroring the break in FFT itself (§5.3).

#### 6.1.4 Cointegration
- **Baseline:** EG long run p 0.264; EG short run p 0.424; Johansen trace r ≤ 0 = 21.59 (p < 0.01), r ≤ 1 = 2.93 (p < 0.10); ARDL(4,4) case 3 F = 3.54 (p 0.169). Only Johansen passes.
- **Re-specification:** run for all seven banks (§5.4). Specifications that pass and reach estimation: Johansen `det_order` -1, 0, 1; EG short run `n`; EG long run `c`, `ct`; ARDL cases 1, 4, 5.
- **Gregory-Hansen** (one break, §5.3; 5% simulated critical values C −5.14, C/T −5.50, C/S −5.46, C/S/T −5.82): no rejection at 5%. ADF\* C −4.05 (2016Q3), C/T −4.53 (2023Q4), C/S −4.50 (2021Q4), C/S/T −4.58 (2023Q4).

#### 6.1.5 Specifications Estimated
23 one-step ECMs (9 ARDL, 7 Johansen, 7 EG), in-sample MAE 0.0469 to 0.0742, long-run beta 0.404 to 0.527. Plus 23 asymmetric variants, one per specification: λ split kept in 14, θ split kept in 5 (§5.5).

#### 6.1.6 Champion Model: Johansen VECM (rank 1), k_ar_diff = 1, det_order -1, BIC
Chosen by the parsimony step (§5.5): 3 parameters, against 9 for the version 0.1 champion (ARDL(3,4), case 4), whose score was within one standard error. It has no deterministic terms, so no trend is frozen for projection.

| Term | Coefficient | *t* | p-value |
| :--- | :-: | :-: | :-: |
| y.L1 (λ) | **-0.2283** | -3.86 | 2.9e-04 |
| FFT.L1 | 0.1088 | 4.01 | 1.8e-04 |
| D.FFT.L1 | 0.2148 | 4.25 | 8.0e-05 |
| **LR: FFT (θ)** | **0.4765** | 16.97 | 6.0e-24 |

![First Horizon Bank: actual vs. predicted deposit rate, champion model](<docs/figures/First Horizon Bank - Actual vs Predicted.png>)

*Figure 2: First Horizon Bank, actual vs. one-step ECM fitted deposit rate (`rate_pf_clean`), champion model. In-sample.*

#### 6.1.7 Outcomes Analysis and Issues
- **Governing MAE rating (many-start-date backtest, §5.6): Green**. h-step MAE, 1Q to 8Q, over 34 to 41 start dates: 0.102, 0.155, 0.201, 0.256, 0.318, 0.371, 0.419, 0.449 (mean 0.284). Worst skill ratio against the no-change forecast: 0.73 at 1Q.
- Single-window 8Q backtest (one start date per horizon, supplementary): 0.113, 0.077, 0.218, 0.147, 0.113, 0.187, 0.450, 0.325; mean 0.204, no-change mean 0.307, beats no-change on 7/8 horizons (Amber).

![First Horizon Bank: many-start-date backtest MAE by horizon](<docs/figures/First Horizon Bank - MAE Backtest 8Q.png>)

*Figure 3: First Horizon Bank, many-start-date backtest: h-step MAE by horizon over 34 to 41 start dates (n under each bar), with the no-change forecast and the 8Q band limits (§5.6), champion model.*

- Mean h-step MAE rises from 0.242 to 0.284 against the version 0.1 champion, the cost of the simpler model. Its skill ratio stays below 0.75 at every horizon.

- **Long-run beta stability (§5.6): Green.** From 2020Q1 to 2026Q1, θ ranges from 0.378 to 0.706 against the full-sample 0.477. The largest deviation is 48% (2023Q3) and at most 2.00 origin standard errors (2023Q3). Failing start dates: none.

![First Horizon Bank: long-run beta at every start date](<docs/figures/First Horizon Bank - Beta Backtest.png>)

*Figure 4: First Horizon Bank, long-run beta θ re-estimated at every start date from 2016Q1 (expanding window), with ±2 origin standard errors, the full-sample θ ±20% and the unrated window before 2020Q1 shaded, champion model.*

- **Realized beta (§5.6, descriptive):** mean actual beta 1Q to 8Q 0.60, 0.51, 0.46, 0.47, 0.48, 0.35, 0.33, 0.38; model-implied 0.26, 0.32, 0.31, 0.32, 0.25, 0.16, 0.15, 0.25.

![First Horizon Bank: realized vs model-implied beta by horizon](<docs/figures/First Horizon Bank - Realized Beta 8Q.png>)

*Figure 5: First Horizon Bank, mean actual and model-implied beta by horizon over start dates where FFT moved at least 0.25 pp, with long-run θ on a second axis, champion model.*

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
Zivot-Andrews on levels, 2011 to 2026 (AIC lags, max 4): `c`: -7.57, p 1.0e-05, break 2022Q4; `t`: -3.79, p 0.210, break 2021Q3; `ct`: -5.20, p 0.036, break 2023Q1. The unit root is rejected when a 2022 level break is allowed, mirroring the break in FFT itself (§5.3).

#### 6.2.4 Cointegration
- **Baseline:** none pass. EG long run p 0.353; Johansen trace r ≤ 0 = 13.17 (p > 0.10); ARDL(3,4) case 3 F = 2.95 (p 0.278).
- **Re-specification:** Johansen `det_order 1`, k_ar_diff = 1 (BIC, fixed): r ≤ 0 = 20.31 (p < 0.05), r ≤ 1 = 5.64 (p < 0.05). ARDL(3,1) cases 4 and 5 under BIC (F 6.04, p 0.007; F 8.25, p 0.004).
- The Johansen r ≤ 1 rejection, if taken literally, implies rank 2. Rank 1 is imposed by assumption.
- **Gregory-Hansen** (one break, §5.3; 5% simulated critical values C −5.14, C/T −5.50, C/S −5.46, C/S/T −5.82): ADF\* does not reject at 5% under any model: C −3.90 (2024Q1), C/T −5.44 (2023Q3; rejects only against the asymptotic −4.99), C/S −4.09 (2021Q3), C/S/T −5.30 (2024Q1). The C/T Zt\* (−5.42, break 2023Q3) rejects at 5%, the only GH rejection in the peer set.

#### 6.2.5 Specifications Estimated
4 one-step ECMs (2 Johansen, 2 ARDL), in-sample MAE 0.0292 to 0.0310, long-run beta 0.277 to 0.346. Plus 4 asymmetric variants, one per specification: λ split kept in 2, θ split kept in 2 (§5.5).

#### 6.2.6 Champion Model: Johansen VECM (rank 1), k_ar_diff = 1, det_order 1, BIC
Chosen by the parsimony step: 5 parameters, against 7 for the version 0.1 champion (ARDL(3,1), case 4). The constant and trend follow the det_order 1 test. The best-scoring model is still the version 0.1 champion.

| Term | Coefficient | *t* | p-value |
| :--- | :-: | :-: | :-: |
| const | 0.0440 | 2.57 | 0.013 |
| trend | -0.00095 | -1.54 | 0.129 |
| y.L1 (λ) | **-0.1580** | -5.24 | 2.6e-06 |
| FFT.L1 | 0.0437 | 4.13 | 1.2e-04 |
| D.y.L1 | 0.5333 | 5.72 | 4.5e-07 |
| LR: const | 0.2786 | 3.09 | 0.0032 |
| LR: trend | -0.00602 | -1.68 | 0.099 |
| **LR: FFT (θ)** | **0.2769** | 7.44 | 7.3e-10 |

![Glacier Bank: actual vs. predicted deposit rate, champion model](<docs/figures/Glacier Bank - Actual vs Predicted.png>)

*Figure 6: Glacier Bank, actual vs. one-step ECM fitted deposit rate (`rate_pf_clean`), champion model. In-sample.*

#### 6.2.7 Outcomes Analysis and Issues
- **Governing MAE rating (many-start-date backtest, §5.6): Red** (skill ratio 1.19 at 5Q). h-step MAE, 1Q to 8Q, over 34 to 41 start dates: 0.049, 0.111, 0.179, 0.248, 0.313, 0.369, 0.403, 0.434 (mean 0.263). Worst skill ratio against the no-change forecast: 1.19 at 5Q.
- Single-window 8Q backtest (one start date per horizon, supplementary): 0.102, 0.042, 0.033, 0.102, 0.253, 0.290, 0.146, 0.306; mean 0.159, no-change mean 0.119, beats no-change on 3/8 horizons (Amber).

![Glacier Bank: many-start-date backtest MAE by horizon](<docs/figures/Glacier Bank - MAE Backtest 8Q.png>)

*Figure 7: Glacier Bank, many-start-date backtest: h-step MAE by horizon over 34 to 41 start dates (n under each bar), with the no-change forecast and the 8Q band limits (§5.6), champion model.*

- **MAE Red:** the champion loses to the no-change forecast at 5Q (skill ratio 1.19). Glacier's deposit rate moves little, so the no-change forecast is hard to beat; the version 0.1 champion was Amber for the same reason (0.96).

- **Long-run beta stability (§5.6): Red.** From 2020Q1 to 2026Q1, θ ranges from 0.103 to 0.273 against the full-sample 0.277. The largest deviation is 63% (2022Q3) and at most 8.47 origin standard errors (2022Q4). Failing start dates: 15 (2020Q1 2020Q2 2020Q3 2020Q4 2021Q1 2021Q2 2021Q3 2021Q4 2022Q1 2022Q2 2022Q3 2022Q4 2023Q1 2023Q4 2024Q1).

![Glacier Bank: long-run beta at every start date](<docs/figures/Glacier Bank - Beta Backtest.png>)

*Figure 8: Glacier Bank, long-run beta θ re-estimated at every start date from 2016Q1 (expanding window), with ±2 origin standard errors, the full-sample θ ±20% and the unrated window before 2020Q1 shaded, champion model.*

- **Realized beta (§5.6, descriptive):** mean actual beta 1Q to 8Q 0.24, 0.21, 0.21, 0.21, 0.22, 0.09, 0.09, 0.11; model-implied 0.14, 0.17, 0.22, 0.22, 0.15, -0.04, -0.02, -0.02.

![Glacier Bank: realized vs model-implied beta by horizon](<docs/figures/Glacier Bank - Realized Beta 8Q.png>)

*Figure 9: Glacier Bank, mean actual and model-implied beta by horizon over start dates where FFT moved at least 0.25 pp, with long-run θ on a second axis, champion model.*

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
Zivot-Andrews on levels, 2011 to 2026 (AIC lags, max 4): `c`: -6.34, p 4.7e-04, break 2022Q2; `t`: -5.41, p 0.0049, break 2021Q4; `ct`: -5.64, p 0.0082, break 2022Q3. The unit root is rejected when a 2022 level break is allowed, mirroring the break in FFT itself (§5.3).

#### 6.3.4 Cointegration
- **Baseline:** none pass at 5%. EG long run p 0.085; EG short run p 0.882; Johansen trace r ≤ 0 = 13.05 (p > 0.10); ARDL(4,3) case 3 F = 2.78 (p 0.318).
- **Re-specification** (now run for all seven banks, §5.4): only EG long run with no deterministic terms passes (t -3.13, p 0.019 under AIC, BIC and t-stat). Johansen gives r ≤ 1 rejections only.
- **Gregory-Hansen** (one break, §5.3; 5% simulated critical values C −5.14, C/T −5.50, C/S −5.46, C/S/T −5.82): no rejection at 5%. ADF\* C −3.79 (2023Q4), C/T −4.42 (2023Q4), C/S −3.96 (2021Q3), C/S/T −4.37 (2023Q4). EG without deterministic terms fails in every sample window ending in 2019Q4, and in 2021Q4 windows starting in 2013 or later (p 0.18 to 0.69). It passes in every window ending in 2024Q2 or later (`model_form/output/huntington_eg_subsamples.csv`; §6.3.7).

#### 6.3.5 Specifications Estimated
3 one-step ECMs (3 EG), in-sample MAE 0.0234 to 0.0234, long-run beta 0.463 to 0.463. Plus 3 asymmetric variants, one per specification: λ split kept in 3, θ split kept in 0 (§5.5).

#### 6.3.6 Champion Model: EG long run, trend `n`, AIC (ADF lag=1, ECM lag=3)
Unchanged from version 0.1. Its asymmetric variant scores better (mean MAE 0.204), but within one standard error, so the parsimony step keeps the 8-parameter symmetric model.

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

![Huntington National Bank: actual vs. predicted deposit rate, champion model](<docs/figures/Huntington National Bank - Actual vs Predicted.png>)

*Figure 10: Huntington National Bank, actual vs. one-step ECM fitted deposit rate (`rate_pf_clean`), champion model. In-sample.*

#### 6.3.7 Outcomes Analysis and Issues
- **Governing MAE rating (many-start-date backtest, §5.6): Green**. h-step MAE, 1Q to 8Q, over 34 to 41 start dates: 0.042, 0.097, 0.148, 0.199, 0.255, 0.307, 0.339, 0.381 (mean 0.221). Worst skill ratio against the no-change forecast: 0.49 at 6Q.
- Single-window 8Q backtest (one start date per horizon, supplementary): 0.094, 0.132, 0.069, 0.049, 0.187, 0.287, 0.169, 0.214; mean 0.150, no-change mean 0.231, beats no-change on 4/8 horizons (Amber).

![Huntington National Bank: many-start-date backtest MAE by horizon](<docs/figures/Huntington National Bank - MAE Backtest 8Q.png>)

*Figure 11: Huntington National Bank, many-start-date backtest: h-step MAE by horizon over 34 to 41 start dates (n under each bar), with the no-change forecast and the 8Q band limits (§5.6), champion model.*

- Unchanged champion and ratings. The large lagged-Δy terms still carry the 2025Q1 start-date error (§7.3).
- **Scope decision (2026-10-31): Huntington stays in scope with a caveat** (L15).

- **Long-run beta stability (§5.6): Green.** From 2020Q1 to 2026Q1, θ ranges from 0.243 to 0.553 against the full-sample 0.463. The largest deviation is 47% (2020Q2) and at most 1.29 origin standard errors (2022Q4). Failing start dates: none.

![Huntington National Bank: long-run beta at every start date](<docs/figures/Huntington National Bank - Beta Backtest.png>)

*Figure 12: Huntington National Bank, long-run beta θ re-estimated at every start date from 2016Q1 (expanding window), with ±2 origin standard errors, the full-sample θ ±20% and the unrated window before 2020Q1 shaded, champion model.*

- **Realized beta (§5.6, descriptive):** mean actual beta 1Q to 8Q 0.40, 0.38, 0.38, 0.39, 0.39, 0.28, 0.26, 0.31; model-implied 0.36, 0.35, 0.34, 0.33, 0.23, 0.18, 0.13, 0.19.

![Huntington National Bank: realized vs model-implied beta by horizon](<docs/figures/Huntington National Bank - Realized Beta 8Q.png>)

*Figure 13: Huntington National Bank, mean actual and model-implied beta by horizon over start dates where FFT moved at least 0.25 pp, with long-run θ on a second axis, champion model.*

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
Zivot-Andrews on levels, 2011 to 2026 (AIC lags, max 4): `c`: -6.81, p 1.0e-05, break 2022Q3; `t`: -4.67, p 0.024, break 2021Q4; `ct`: -4.93, p 0.076, break 2022Q3. The unit root is rejected when a 2022 level break is allowed, mirroring the break in FFT itself (§5.3).

#### 6.4.4 Cointegration
- **Baseline:** EG long run p 0.198 (fails; the earlier build passed); Johansen trace r ≤ 0 = 13.78 (p < 0.10); ARDL(4,4) case 3 F = 3.39 (p 0.193).
- **Re-specification:** broad support. Specifications that pass and reach estimation: EG long run `c`, `n`; EG short run `n`; Johansen `det_order` 1; ARDL cases 1, 3, 4, 5.
- **Gregory-Hansen** (one break, §5.3; 5% simulated critical values C −5.14, C/T −5.50, C/S −5.46, C/S/T −5.82): no rejection at 5%. ADF\* C −3.90 (2024Q1), C/T −4.72 (2024Q1), C/S −4.30 (2021Q3), C/S/T −4.75 (2024Q1).

#### 6.4.5 Specifications Estimated
17 one-step ECMs (8 EG, 8 ARDL, 1 Johansen), in-sample MAE 0.0317 to 0.0453, long-run beta 0.398 to 0.487. Plus 17 asymmetric variants, one per specification: λ split kept in 17, θ split kept in 6 (§5.5).

#### 6.4.6 Champion Model: ARDL(2,1), case 1, BIC, asymmetric
The asymmetric variant of ARDL(2,1), case 1. The Wald tests keep λ split (F 11.77, p 0.001) and collapse θ to one value (p 0.143). The short-run ΔFFT and Δy pairs are kept by joint F-tests; within the ΔFFT pair only the cut side is individually significant (γ⁻ 0.256, p 1.4e-13; γ⁺ 0.025, p 0.335). Its many-start-date MAE is the lowest in the peer set.

| Term | Coefficient | *t* | p-value |
| :--- | :-: | :-: | :-: |
| ect⁺.L1 (λ⁺) | **-0.0893** | -2.59 | 0.012 |
| ect⁻.L1 (λ⁻) | **-0.3307** | -5.71 | 5.2e-07 |
| D.y⁺.L1 | 0.3461 | 3.24 | 0.0021 |
| D.y⁻.L1 | 0.2782 | 3.09 | 0.0032 |
| D.FFT⁺.L0 | 0.0252 | 0.97 | 0.335 |
| D.FFT⁻.L0 | 0.2563 | 9.85 | 1.4e-13 |
| **LR: FFT (θ)** | **0.4020** | 23.79 | 5.9e-30 |

![KeyBank National Association: actual vs. predicted deposit rate, champion model](<docs/figures/KeyBank National Association - Actual vs Predicted.png>)

*Figure 14: KeyBank National Association, actual vs. one-step ECM fitted deposit rate (`rate_pf_clean`), champion model. In-sample.*

#### 6.4.7 Outcomes Analysis and Issues
- **Governing MAE rating (many-start-date backtest, §5.6): Green**. h-step MAE, 1Q to 8Q, over 34 to 41 start dates: 0.042, 0.068, 0.091, 0.104, 0.147, 0.176, 0.187, 0.195 (mean 0.126). Worst skill ratio against the no-change forecast: 0.37 at 1Q.
- Single-window 8Q backtest (one start date per horizon, supplementary): 0.067, 0.079, 0.137, 0.057, 0.072, 0.044, 0.165, 0.048; mean 0.084, no-change mean 0.272, beats no-change on 7/8 horizons (Green).

![KeyBank National Association: many-start-date backtest MAE by horizon](<docs/figures/KeyBank National Association - MAE Backtest 8Q.png>)

*Figure 15: KeyBank National Association, many-start-date backtest: h-step MAE by horizon over 34 to 41 start dates (n under each bar), with the no-change forecast and the 8Q band limits (§5.6), champion model.*

- **MAE Green** (was Red with the version 0.1 champion): mean h-step MAE 0.126 against 0.280, the lowest in the peer set.
- Beta stability is Red (was Green): the failing start dates, 2022Q4 to 2024Q1, are the quarters when the hiking cycle entered the sample.

- **Long-run beta stability (§5.6): Red.** From 2020Q1 to 2026Q1, θ ranges from 0.294 to 0.429 against the full-sample 0.402. The largest deviation is 27% (2022Q4) and at most 7.00 origin standard errors (2022Q4). Failing start dates: 5 (2022Q4 2023Q2 2023Q3 2023Q4 2024Q1).

![KeyBank National Association: long-run beta at every start date](<docs/figures/KeyBank National Association - Beta Backtest.png>)

*Figure 16: KeyBank National Association, long-run beta θ re-estimated at every start date from 2016Q1 (expanding window), with ±2 origin standard errors, the full-sample θ ±20% and the unrated window before 2020Q1 shaded, champion model.*

- **Realized beta (§5.6, descriptive):** mean actual beta 1Q to 8Q 0.42, 0.40, 0.38, 0.39, 0.39, 0.27, 0.25, 0.30; model-implied 0.35, 0.34, 0.35, 0.35, 0.29, 0.22, 0.21, 0.26.

![KeyBank National Association: realized vs model-implied beta by horizon](<docs/figures/KeyBank National Association - Realized Beta 8Q.png>)

*Figure 17: KeyBank National Association, mean actual and model-implied beta by horizon over start dates where FFT moved at least 0.25 pp, with long-run θ on a second axis, champion model.*

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
Zivot-Andrews on levels, 2011 to 2026 (AIC lags, max 4): `c`: -6.42, p 3.9e-04, break 2022Q3; `t`: -4.09, p 0.111, break 2021Q2; `ct`: -4.91, p 0.079, break 2022Q3. The unit root is rejected when a 2022 level break is allowed, mirroring the break in FFT itself (§5.3).

#### 6.5.4 Cointegration
- **Baseline:** EG long run p 0.048 (pass); ARDL(2,1) case 3 F = 5.18 (p 0.034, pass); Johansen trace r ≤ 0 = 12.98 (p > 0.10).
- **Re-specification:** specifications that pass and reach estimation: EG long run `c`, `n`; ARDL cases 1, 3, 4, 5; Johansen `det_order` 1.
- **Gregory-Hansen** (one break, §5.3; 5% simulated critical values C −5.14, C/T −5.50, C/S −5.46, C/S/T −5.82): no rejection at 5%. ADF\* C −3.94 (2016Q1), C/T −4.49 (2024Q1), C/S −4.25 (2021Q4), C/S/T −4.78 (2023Q3).

#### 6.5.5 Specifications Estimated
22 one-step ECMs (11 ARDL, 6 EG, 5 Johansen), in-sample MAE 0.0383 to 0.0502, long-run beta 0.355 to 0.432. Plus 22 asymmetric variants, one per specification: λ split kept in 12, θ split kept in 13 (§5.5).

#### 6.5.6 Champion Model: EG long run, trend `n`, AIC (ADF lag=1, ECM lag=4)
Chosen by the parsimony step: 3 parameters, against 6 for the version 0.1 champion (ARDL(2,1), case 4), which is still the best-scoring model. It has no deterministic terms, so no trend is frozen for projection.

| Term | Coefficient | *t* | p-value |
| :--- | :-: | :-: | :-: |
| y.L1 (λ) | **-0.1949** | -5.28 | 2.0e-06 |
| FFT.L1 | 0.0783 | 6.00 | 1.4e-07 |
| D.FFT.L0 | 0.1656 | 5.98 | 1.5e-07 |
| **LR: FFT (θ)** | **0.4021** | 16.94 | 4.0e-24 |

![Manufacturers and Traders Trust Company: actual vs. predicted deposit rate, champion model](<docs/figures/Manufacturers and Traders Trust Company - Actual vs Predicted.png>)

*Figure 18: Manufacturers and Traders Trust Company, actual vs. one-step ECM fitted deposit rate (`rate_pf_clean`), champion model. In-sample.*

#### 6.5.7 Outcomes Analysis and Issues
- **Governing MAE rating (many-start-date backtest, §5.6): Green**. h-step MAE, 1Q to 8Q, over 34 to 41 start dates: 0.070, 0.141, 0.205, 0.265, 0.313, 0.364, 0.403, 0.436 (mean 0.275). Worst skill ratio against the no-change forecast: 0.74 at 3Q.
- Single-window 8Q backtest (one start date per horizon, supplementary): 0.023, 0.160, 0.180, 0.143, 0.110, 0.319, 0.401, 0.443; mean 0.222, no-change mean 0.235, beats no-change on 6/8 horizons (Amber).

![Manufacturers and Traders Trust Company: many-start-date backtest MAE by horizon](<docs/figures/Manufacturers and Traders Trust Company - MAE Backtest 8Q.png>)

*Figure 19: Manufacturers and Traders Trust Company, many-start-date backtest: h-step MAE by horizon over 34 to 41 start dates (n under each bar), with the no-change forecast and the 8Q band limits (§5.6), champion model.*

- Mean h-step MAE rises from 0.218 to 0.275 against the version 0.1 champion. Beta stability stays Red.

- **Long-run beta stability (§5.6): Red.** From 2020Q1 to 2026Q1, θ ranges from 0.339 to 0.686 against the full-sample 0.402. The largest deviation is 71% (2023Q4) and at most 2.24 origin standard errors (2023Q4). Failing start dates: 3 (2023Q3 2023Q4 2024Q1).

![Manufacturers and Traders Trust Company: long-run beta at every start date](<docs/figures/Manufacturers and Traders Trust Company - Beta Backtest.png>)

*Figure 20: Manufacturers and Traders Trust Company, long-run beta θ re-estimated at every start date from 2016Q1 (expanding window), with ±2 origin standard errors, the full-sample θ ±20% and the unrated window before 2020Q1 shaded, champion model.*

- **Realized beta (§5.6, descriptive):** mean actual beta 1Q to 8Q 0.38, 0.36, 0.34, 0.35, 0.34, 0.23, 0.22, 0.26; model-implied 0.17, 0.18, 0.18, 0.20, 0.16, 0.06, 0.06, 0.14.

![Manufacturers and Traders Trust Company: realized vs model-implied beta by horizon](<docs/figures/Manufacturers and Traders Trust Company - Realized Beta 8Q.png>)

*Figure 21: Manufacturers and Traders Trust Company, mean actual and model-implied beta by horizon over start dates where FFT moved at least 0.25 pp, with long-run θ on a second axis, champion model.*

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
Zivot-Andrews on levels, 2011 to 2026 (AIC lags, max 4): `c`: -6.21, p 6.1e-04, break 2022Q3; `t`: -4.31, p 0.065, break 2022Q1; `ct`: -4.26, p 0.335, break 2019Q3. The unit root is rejected when a 2022 level break is allowed, mirroring the break in FFT itself (§5.3).

#### 6.6.4 Cointegration
- **Baseline:** none pass at 5%. EG long run p 0.379; Johansen trace r ≤ 0 = 15.49 (p < 0.10); ARDL(4,4) case 3 F = 2.85 (p 0.302).
- **Re-specification** (now run for all seven banks, §5.4): EG long run `n` / BIC (p 0.0077); Johansen `det_order -1`, k_ar_diff = 1 (r ≤ 0 = 13.91, p < 0.05).
- **Gregory-Hansen** (one break, §5.3; 5% simulated critical values C −5.14, C/T −5.50, C/S −5.46, C/S/T −5.82): no rejection at 5%. ADF\* C −3.85 (2024Q1), C/T −4.60 (2024Q1), C/S −4.01 (2021Q3), C/S/T −4.53 (2024Q1).

#### 6.6.5 Specifications Estimated
2 one-step ECMs (1 EG, 1 Johansen), in-sample MAE 0.0285 to 0.0414, long-run beta 0.394 to 0.419. Plus 2 asymmetric variants, one per specification: λ split kept in 1, θ split kept in 0 (§5.5).

#### 6.6.6 Champion Model: Johansen VECM (rank 1), k_ar_diff = 1, det_order -1, fixed
The Johansen VECM that was Old National's champion before EG long-run specifications gained their short-run lags. Chosen by the parsimony step: 4 parameters, against 8 for the version 0.1 champion (EG long run, trend `n`, BIC), which is still the best-scoring model.

| Term | Coefficient | *t* | p-value |
| :--- | :-: | :-: | :-: |
| y.L1 (λ) | **-0.1354** | -3.49 | 9.4e-04 |
| FFT.L1 | 0.0567 | 3.56 | 7.5e-04 |
| D.y.L1 | 0.3063 | 2.83 | 0.0064 |
| D.FFT.L1 | 0.1024 | 3.20 | 0.0022 |
| **LR: FFT (θ)** | **0.4191** | 13.85 | 9.8e-20 |

![Old National Bank: actual vs. predicted deposit rate, champion model](<docs/figures/Old National Bank - Actual vs Predicted.png>)

*Figure 22: Old National Bank, actual vs. one-step ECM fitted deposit rate (`rate_pf_clean`), champion model. In-sample.*

#### 6.6.7 Outcomes Analysis and Issues
- **Governing MAE rating (many-start-date backtest, §5.6): Green**. h-step MAE, 1Q to 8Q, over 34 to 41 start dates: 0.067, 0.132, 0.182, 0.230, 0.300, 0.359, 0.396, 0.437 (mean 0.263). Worst skill ratio against the no-change forecast: 0.67 at 2Q.
- Single-window 8Q backtest (one start date per horizon, supplementary): 0.106, 0.052, 0.191, 0.094, 0.364, 0.173, 0.289, 0.114; mean 0.173, no-change mean 0.207, beats no-change on 6/8 horizons (Amber).

![Old National Bank: many-start-date backtest MAE by horizon](<docs/figures/Old National Bank - MAE Backtest 8Q.png>)

*Figure 23: Old National Bank, many-start-date backtest: h-step MAE by horizon over 34 to 41 start dates (n under each bar), with the no-change forecast and the 8Q band limits (§5.6), champion model.*

- Mean h-step MAE 0.263 against 0.249 for the version 0.1 champion. Beta stability Amber (was Green).

- **Long-run beta stability (§5.6): Amber.** From 2020Q1 to 2026Q1, θ ranges from -0.295 to 0.491 against the full-sample 0.419. The largest deviation is 170% (2020Q2) and at most 2.28 origin standard errors (2020Q1). Failing start dates: 1 (2020Q1).

![Old National Bank: long-run beta at every start date](<docs/figures/Old National Bank - Beta Backtest.png>)

*Figure 24: Old National Bank, long-run beta θ re-estimated at every start date from 2016Q1 (expanding window), with ±2 origin standard errors, the full-sample θ ±20% and the unrated window before 2020Q1 shaded, champion model.*

- **Realized beta (§5.6, descriptive):** mean actual beta 1Q to 8Q 0.39, 0.36, 0.35, 0.35, 0.35, 0.20, 0.19, 0.24; model-implied 0.23, 0.26, 0.29, 0.27, 0.19, 0.08, 0.06, 0.09.

![Old National Bank: realized vs model-implied beta by horizon](<docs/figures/Old National Bank - Realized Beta 8Q.png>)

*Figure 25: Old National Bank, mean actual and model-implied beta by horizon over start dates where FFT moved at least 0.25 pp, with long-run θ on a second axis, champion model.*

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
Zivot-Andrews on levels, 2011 to 2026 (AIC lags, max 4): `c`: -6.23, p 5.8e-04, break 2022Q3; `t`: -4.43, p 0.048, break 2021Q3; `ct`: -5.21, p 0.035, break 2022Q4. The unit root is rejected when a 2022 level break is allowed, mirroring the break in FFT itself (§5.3).

#### 6.7.4 Cointegration
- **Baseline:** EG long run p 0.312; Johansen trace r ≤ 0 = 14.06 (p < 0.10); ARDL(4,3) case 3 F = 3.50 (p 0.174).
- **Re-specification:** specifications that pass and reach estimation: Johansen `det_order` -1, 0; ARDL cases 1, 4, 5.
- **Gregory-Hansen** (one break, §5.3; 5% simulated critical values C −5.14, C/T −5.50, C/S −5.46, C/S/T −5.82): no rejection at 5%. ADF\* C −3.82 (2024Q1), C/T −4.41 (2024Q1), C/S −3.87 (2024Q1), C/S/T −4.37 (2024Q1).

#### 6.7.5 Specifications Estimated
7 one-step ECMs (5 ARDL, 2 Johansen), in-sample MAE 0.0336 to 0.0437, long-run beta 0.424 to 0.524. Plus 7 asymmetric variants, one per specification: λ split kept in 5, θ split kept in 5 (§5.5).

#### 6.7.6 Champion Model: ARDL(3,2), case 4, BIC
Chosen on its score: it is the best-scoring model, 0.197 against 0.264 for the version 0.1 champion (ARDL(4,3), case 1). It carries a constant and trend; the trend is frozen at its 2026Q2 value for projection (§5.7).

| Term | Coefficient | *t* | p-value |
| :--- | :-: | :-: | :-: |
| const | 0.0589 | 2.52 | 0.015 |
| trend | -0.00220 | -2.79 | 0.0074 |
| y.L1 (λ) | **-0.1647** | -3.90 | 2.8e-04 |
| FFT.L1 | 0.0862 | 4.37 | 6.1e-05 |
| D.y.L1 | 0.7090 | 5.17 | 4.0e-06 |
| D.y.L2 | -0.3057 | -2.83 | 0.0066 |
| D.FFT.L0 | 0.1990 | 6.64 | 2.0e-08 |
| D.FFT.L1 | -0.1127 | -2.45 | 0.018 |
| LR: const | 0.3576 | 3.63 | 6.5e-04 |
| LR: trend | -0.0133 | -3.25 | 0.0021 |
| **LR: FFT (θ)** | **0.5236** | 10.57 | 1.9e-14 |

![SouthState Bank: actual vs. predicted deposit rate, champion model](<docs/figures/SouthState Bank - Actual vs Predicted.png>)

*Figure 26: SouthState Bank, actual vs. one-step ECM fitted deposit rate (`rate_pf_clean`), champion model. In-sample.*

#### 6.7.7 Outcomes Analysis and Issues
- **Governing MAE rating (many-start-date backtest, §5.6): Green**. h-step MAE, 1Q to 8Q, over 34 to 41 start dates: 0.061, 0.117, 0.172, 0.217, 0.238, 0.254, 0.257, 0.260 (mean 0.197). Worst skill ratio against the no-change forecast: 0.60 at 3Q.
- Single-window 8Q backtest (one start date per horizon, supplementary): 0.115, 0.102, 0.070, 0.122, 0.378, 0.179, 0.196, 0.104; mean 0.158, no-change mean 0.182, beats no-change on 4/8 horizons (Amber).

![SouthState Bank: many-start-date backtest MAE by horizon](<docs/figures/SouthState Bank - MAE Backtest 8Q.png>)

*Figure 27: SouthState Bank, many-start-date backtest: h-step MAE by horizon over 34 to 41 start dates (n under each bar), with the no-change forecast and the 8Q band limits (§5.6), champion model.*

- Beta stability is Red (was Green with the version 0.1 champion).
- Shares the easing-cycle error at the 2025Q1 start date (§7.3).

- **Long-run beta stability (§5.6): Red.** From 2020Q1 to 2026Q1, θ ranges from 0.374 to 0.586 against the full-sample 0.524. The largest deviation is 29% (2022Q3) and at most 2.24 origin standard errors (2022Q3). Failing start dates: 3 (2020Q1 2022Q3 2022Q4).

![SouthState Bank: long-run beta at every start date](<docs/figures/SouthState Bank - Beta Backtest.png>)

*Figure 28: SouthState Bank, long-run beta θ re-estimated at every start date from 2016Q1 (expanding window), with ±2 origin standard errors, the full-sample θ ±20% and the unrated window before 2020Q1 shaded, champion model.*

- **Realized beta (§5.6, descriptive):** mean actual beta 1Q to 8Q 0.37, 0.34, 0.34, 0.34, 0.35, 0.23, 0.21, 0.27; model-implied 0.29, 0.29, 0.31, 0.31, 0.27, 0.11, 0.11, 0.14.

![SouthState Bank: realized vs model-implied beta by horizon](<docs/figures/SouthState Bank - Realized Beta 8Q.png>)

*Figure 29: SouthState Bank, mean actual and model-implied beta by horizon over start dates where FFT moved at least 0.25 pp, with long-run θ on a second axis, champion model.*

---

## 7. Outcomes Analysis: Peer Comparison

### 7.1 Many-Start-Date Backtest (governing; h-step MAE, pp)
Start dates every quarter from 2016Q1, expanding estimation window, dynamic forecasts with realized FFT. Each h-step figure averages 34 (8Q) to 41 (1Q) start dates.

| Bank | 1Q | 2Q | 3Q | 4Q | 5Q | 6Q | 7Q | 8Q | Mean | No-change mean | Worst skill ratio | Rating |
| :--- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| First Horizon Bank | 0.102 | 0.155 | 0.201 | 0.256 | 0.318 | 0.371 | 0.419 | 0.449 | 0.284 | 0.539 | 0.73 | **Green** |
| Glacier Bank | 0.049 | 0.111 | 0.179 | 0.248 | 0.313 | 0.369 | 0.403 | 0.434 | 0.263 | 0.235 | 1.19 | **Red** |
| Huntington National Bank | 0.042 | 0.097 | 0.148 | 0.199 | 0.255 | 0.307 | 0.339 | 0.381 | 0.221 | 0.467 | 0.49 | **Green** |
| KeyBank National Association | 0.042 | 0.068 | 0.091 | 0.104 | 0.147 | 0.176 | 0.187 | 0.195 | 0.126 | 0.448 | 0.37 | **Green** |
| Manufacturers and Traders Trust Company | 0.070 | 0.141 | 0.205 | 0.265 | 0.313 | 0.364 | 0.403 | 0.436 | 0.275 | 0.394 | 0.74 | **Green** |
| Old National Bank | 0.067 | 0.132 | 0.182 | 0.230 | 0.300 | 0.359 | 0.396 | 0.437 | 0.263 | 0.404 | 0.67 | **Green** |
| SouthState Bank | 0.061 | 0.117 | 0.172 | 0.217 | 0.238 | 0.254 | 0.257 | 0.260 | 0.197 | 0.413 | 0.60 | **Green** |

Band limits for N = 8, derived from this run (§5.6):

| Band | Green limit (band average) | Red limit (band maximum) |
| :-: | :-: | :-: |
| 1-2Q | 0.15 | 0.20 |
| 3-4Q | 0.25 | 0.30 |
| 5-8Q | 0.40 | 0.45 |

The limits come from the new champions as a peer group. The 1–2Q limits are looser than version 0.1's (0.10/0.15), because the simpler champions have higher short-horizon errors. The skill ratio does not depend on the peer group: every champion is below 0.75 except Glacier (1.19 at 5Q). Fixing the limits from a reference run is tracked in [#8](https://github.com/Panda5130/Deposit-Beta/issues/8).

### 7.2 Single-Window 8Q Backtest (supplementary; MAE, pp)
Each column is one forecast window, starting at T−k and ending at 2026Q2, with MAE averaged over its k quarters. Each column therefore rests on a single start date, and the windows overlap.

| Bank | 1Q | 2Q | 3Q | 4Q | 5Q | 6Q | 7Q | 8Q | Mean | No-change mean | Rating |
| :--- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| First Horizon Bank | 0.113 | 0.077 | 0.218 | 0.147 | 0.113 | 0.187 | 0.450 | 0.325 | 0.204 | 0.307 | Amber |
| Glacier Bank | 0.102 | 0.042 | 0.033 | 0.102 | 0.253 | 0.290 | 0.146 | 0.306 | 0.159 | 0.119 | Amber |
| Huntington National Bank | 0.094 | 0.132 | 0.069 | 0.049 | 0.187 | 0.287 | 0.169 | 0.214 | 0.150 | 0.231 | Amber |
| KeyBank National Association | 0.067 | 0.079 | 0.137 | 0.057 | 0.072 | 0.044 | 0.165 | 0.048 | 0.084 | 0.272 | Green |
| Manufacturers and Traders Trust Company | 0.023 | 0.160 | 0.180 | 0.143 | 0.110 | 0.319 | 0.401 | 0.443 | 0.222 | 0.235 | Amber |
| Old National Bank | 0.106 | 0.052 | 0.191 | 0.094 | 0.364 | 0.173 | 0.289 | 0.114 | 0.173 | 0.207 | Amber |
| SouthState Bank | 0.115 | 0.102 | 0.070 | 0.122 | 0.378 | 0.179 | 0.196 | 0.104 | 0.158 | 0.182 | Amber |

### 7.3 Observations
- Over 34 to 41 start dates per horizon, h-step errors rise with horizon, and every champion except Glacier beats the no-change forecast at every horizon.
- KeyBank's asymmetric champion has the lowest error in the peer set (mean 0.126 pp); the next best is SouthState (0.197).
- The shared error in the single window starting 2025Q1 (the "5Q" column of §7.2) remains for the symmetric champions with large lagged-Δy terms. 63% to 72% of the version 0.1 champions' forecast fall from that date came from those momentum terms. The asymmetric variants' Δy split survives pruning in many variants (§7.8), but only KeyBank's is chosen.
- Long-run betas range from 0.28 (Glacier) to 0.52 (SouthState).

### 7.4 Benchmarking
The no-change forecast is the benchmark in both backtests. The `model_form` challengers are scored against the current champions on the same start dates, against the champions' band limits and the skill test:

- an asymmetric ECM with separate λ for positive and negative disequilibrium (a1), and one with λ split by FFT direction (a2);
- a static OLS beta applied to the FFT change (b2), and cycle-specific betas (b3);
- each champion with a 2022Q3 level dummy (c).

| Bank | Champion | a1 asymmetric λ | a2 λ by FFT direction | b2 static beta | b3 cycle betas | c 2022 dummy |
| :--- | :-: | :-: | :-: | :-: | :-: | :-: |
| First Horizon Bank | 0.284 Green | 0.276 Amber | 0.314 Red | 0.389 Red | 0.378 Red | 0.321 Red |
| Glacier Bank | 0.263 Red | 0.344 Red | 0.305 Red | 0.265 Red | 0.204 Amber | 0.253 Red |
| Huntington National Bank | 0.221 Green | 0.214 Green | 0.206 Green | 0.348 Red | 0.311 Red | 0.245 Green |
| KeyBank National Association | 0.126 Green | 0.129 Green | 0.168 Green | 0.344 Red | 0.319 Red | 0.192 Green |
| Manufacturers and Traders Trust Company | 0.275 Green | 0.264 Green | 0.244 Green | 0.337 Red | 0.285 Red | 0.315 Red |
| Old National Bank | 0.263 Green | 0.246 Green | 0.436 Red | 0.375 Red | 0.313 Red | 0.308 Red |
| SouthState Bank | 0.197 Green | 0.193 Green | 0.220 Green | 0.408 Red | 0.333 Red | 0.198 Green |

*Mean h-step MAE over 1Q to 8Q (pp) and rating against the champions' band limits.*

The asymmetric variants of §5.5 now sit inside the candidate set, so the a1 and a2 challengers are kept as reference results. Because the parsimony step chose simpler champions, several challengers now score below their champion: a1 at First Horizon (0.276 vs 0.284), Old National (0.246 vs 0.263) and M&T (0.264 vs 0.275), a2 at M&T (0.244), and the cycle betas at Glacier (0.204 vs 0.263). The challengers are not candidates in the selection rule, so they don't replace the champions. Glacier's cycle betas also beat every candidate model, which adds to the case that Glacier's champion is weak (§6.2.7).

### 7.5 Long-Run Beta Stability (start dates from 2016Q1)
Each champion is re-estimated at every start date from 2016Q1 to 2026Q1 (expanding window), and θ is compared with the full-sample estimate through 2026Q2. Ratings use the start dates from 2020Q1 (§5.6).

| Bank | Full-sample θ | θ range, 2020Q1–2026Q1 | Largest deviation (share), start date | Largest deviation in SEs, start date | Failing start dates | Rating |
| :--- | :-: | :-: | :-: | :-: | :-: | :-: |
| First Horizon Bank | 0.477 | 0.378 to 0.706 | 48%, 2023Q3 | 2.00, 2023Q3 | 0 | **Green** |
| Glacier Bank | 0.277 | 0.103 to 0.273 | 63%, 2022Q3 | 8.47, 2022Q4 | 15 | **Red** |
| Huntington National Bank | 0.463 | 0.243 to 0.553 | 47%, 2020Q2 | 1.29, 2022Q4 | 0 | **Green** |
| KeyBank National Association | 0.402 | 0.294 to 0.429 | 27%, 2022Q4 | 7.00, 2022Q4 | 5 | **Red** |
| Manufacturers and Traders Trust Company | 0.402 | 0.339 to 0.686 | 71%, 2023Q4 | 2.24, 2023Q4 | 3 | **Red** |
| Old National Bank | 0.419 | -0.295 to 0.491 | 170%, 2020Q2 | 2.28, 2020Q1 | 1 | **Amber** |
| SouthState Bank | 0.524 | 0.374 to 0.586 | 29%, 2022Q3 | 2.24, 2022Q3 | 3 | **Red** |

![All banks: long-run beta re-estimated at every start date](<docs/figures/All Banks - Beta Backtest.png>)

*Figure 30: Long-run beta θ re-estimated at every start date from 2016Q1, all banks.*

- Two champions are Green (First Horizon, Huntington), one Amber (Old National) and four Red (Glacier, KeyBank, M&T, SouthState). Version 0.1's in-sample champions had five Green (§7.6).
- Glacier's beta is the least stable: about 0.10–0.14 until the 2022–23 hiking cycle enters the sample.

### 7.6 Champion Choice: Out-of-Sample Default vs In-Sample Option

| Bank | Model | Params | In-sample MAE | Many-start-date mean MAE (SE) | θ | MAE rating | Beta rating |
| :--- | :--- | :-: | :-: | :-: | :-: | :-: | :-: |
| First Horizon Bank | Out of sample (default): Johansen VECM (rank 1), k_ar_diff = 1, det_order -1, BIC | 3 | 0.0720 | 0.284 (0.059) | 0.477 | Green | Green |
| | In sample (optional): ARDL(3,4), case 4, AIC | 9 | 0.0469 | 0.242 (0.039) | 0.517 | Red | Green |
| Glacier Bank | Out of sample (default): Johansen VECM (rank 1), k_ar_diff = 1, det_order 1, BIC | 5 | 0.0310 | 0.263 (0.087) | 0.277 | Red | Red |
| | In sample (optional): ARDL(3,1), case 4, BIC | 7 | 0.0292 | 0.207 (0.079) | 0.346 | Amber | Red |
| Huntington National Bank | Both rules: EG long run, trend `n`, AIC (ADF lag=1, ECM lag=3) | 8 | 0.0234 | 0.221 (0.040) | 0.463 | Green | Green |
| KeyBank National Association | Out of sample (default): ARDL(2,1), case 1, BIC, asymmetric | 7 | 0.0268 | 0.126 (0.021) | 0.402 | Green | Red |
| | In sample (optional): EG long run, trend `n`, BIC (ADF lag=1, ECM lag=3) | 7 | 0.0317 | 0.280 (0.062) | 0.398 | Red | Green |
| Manufacturers and Traders Trust Company | Out of sample (default): EG long run, trend `n`, AIC (ADF lag=1, ECM lag=4) | 3 | 0.0499 | 0.275 (0.059) | 0.402 | Green | Red |
| | In sample (optional): ARDL(2,1), case 4, AIC | 6 | 0.0383 | 0.218 (0.068) | 0.432 | Green | Red |
| Old National Bank | Out of sample (default): Johansen VECM (rank 1), k_ar_diff = 1, det_order -1, fixed | 4 | 0.0414 | 0.263 (0.065) | 0.419 | Green | Amber |
| | In sample (optional): EG long run, trend `n`, BIC (ADF lag=1, ECM lag=3) | 8 | 0.0285 | 0.249 (0.048) | 0.394 | Green | Green |
| SouthState Bank | Out of sample (default): ARDL(3,2), case 4, BIC | 8 | 0.0347 | 0.197 (0.039) | 0.524 | Green | Red |
| | In sample (optional): ARDL(4,3), case 1, AIC | 8 | 0.0336 | 0.264 (0.039) | 0.443 | Green | Green |

Source: `MAE_Backtesting/output/out_of_sample/selection_comparison_8Q.csv`. Each rule's MAE ratings use limits from its own champions as a peer group.

- The rules agree only for Huntington.
- On the skill test, which doesn't depend on the peer group, both rules have six of seven champions Green; Glacier is the exception under both.
- The out-of-sample rule gains most at KeyBank (0.280 to 0.126) and SouthState (0.264 to 0.197), and gives up accuracy for simpler models at First Horizon, Glacier, M&T and Old National.
- Beta stability is weaker under the out-of-sample rule: two Green against five.

### 7.7 Realized vs Model-Implied Beta
Mean actual / model-implied beta at selected horizons, over start dates where FFT moved at least 0.25 pp (§5.6). Descriptive; not rated.

| Bank | 1Q | 2Q | 4Q | 8Q |
| :--- | :-: | :-: | :-: | :-: |
| First Horizon Bank | 0.60 / 0.26 | 0.51 / 0.32 | 0.47 / 0.32 | 0.38 / 0.25 |
| Glacier Bank | 0.24 / 0.14 | 0.21 / 0.17 | 0.21 / 0.22 | 0.11 / -0.02 |
| Huntington National Bank | 0.40 / 0.36 | 0.38 / 0.35 | 0.39 / 0.33 | 0.31 / 0.19 |
| KeyBank National Association | 0.42 / 0.35 | 0.40 / 0.34 | 0.39 / 0.35 | 0.30 / 0.26 |
| Manufacturers and Traders Trust Company | 0.38 / 0.17 | 0.36 / 0.18 | 0.35 / 0.20 | 0.26 / 0.14 |
| Old National Bank | 0.39 / 0.23 | 0.36 / 0.26 | 0.35 / 0.27 | 0.24 / 0.09 |
| SouthState Bank | 0.37 / 0.29 | 0.34 / 0.29 | 0.34 / 0.31 | 0.27 / 0.14 |

![All banks: realized vs model-implied beta by horizon](<docs/figures/All Banks - Realized Beta 8Q.png>)

*Figure 31: Mean actual and model-implied beta by horizon, one panel per bank, with long-run θ on a second axis.*

- In most bank-horizon pairs the model-implied beta is below the actual beta: given the realized FFT path, the champions under-predict how far deposit rates move over the forecast window.
- Averaged over the horizons shown, the gap is largest for First Horizon (0.20) and M&T (0.17) and smallest for KeyBank, Glacier and Huntington (0.05 to 0.07). Glacier's implied beta turns slightly negative at 8Q.

### 7.8 Asymmetric Variants

| Bank | Variants | λ split kept | θ split kept |
| :--- | :-: | :-: | :-: |
| First Horizon Bank | 23 | 14 | 5 |
| Glacier Bank | 4 | 2 | 2 |
| Huntington National Bank | 3 | 3 | 0 |
| KeyBank National Association | 17 | 17 | 6 |
| Manufacturers and Traders Trust Company | 22 | 12 | 13 |
| Old National Bank | 2 | 1 | 0 |
| SouthState Bank | 7 | 5 | 5 |

- Across all 78 variants, λ⁺ = λ⁻ is rejected at 5% in 54 and θ⁺ = θ⁻ in 31: asymmetric adjustment is common, asymmetric long-run beta less so.
- 23 of the 78 fits cycled between two regime splits; the lowest-error pass is kept and the outputs flag it.
- Several admissible variants forecast explosively out of sample (best asymmetric mean h-step MAE: Old National 76.6 pp, SouthState 4.57, M&T 0.76). The out-of-sample score screens them out, but they are fragile.
- Only KeyBank's champion is asymmetric. Huntington's best asymmetric variant scores 0.204 against 0.221, but within one standard error, so parsimony keeps the symmetric model.

Details are in `docs/resolutions/asymmetry_oos_realized_beta.md`.

---

## 8. Model Limitations and Assumptions

| # | Limitation | Affected banks | Impact |
| :-: | :--- | :--- | :--- |
| L1 | Short sample (62 quarters, 2011Q1 to 2026Q2) lowers the power of unit-root and cointegration tests | All | High |
| L2 | Stationarity classification depends on the specification. Glacier remains flagged (KPSS I(0) p 0.057). All series reject a unit root once a 2022 level break is allowed, but the break is common to FFT and cancels in the cointegrating relation: Gregory-Hansen finds no break in the relationship (§5.3). | All, esp. Glacier | Medium |
| L3 | Results are not robust to the 2008 to 2026 sample: six banks are inconclusive on levels and First Horizon looks I(0) (Appendix A.2) | All | Medium |
| L4 | Pro forma merger adjustment assumes the combined franchise priced like the sum of its parts before the merger; merger-quarter interest is pro-rated by days; predecessors without FDIC Call Reports (none so far) would be skipped | All | Low to medium |
| L5 | The deposit rate is deposit interest expense over total deposits: a total-deposit (not interest-bearing-deposit) beta that does not separate product mix | All | Low |
| L6 | Pass-through is linear and symmetric for six of seven champions. Asymmetric variants are now candidates (§3.2, §5.5), and λ asymmetry is common among them (§7.8), but out-of-sample selection keeps a symmetric champion for six banks. The 2025Q1 start-date error from lagged-Δy momentum remains for those champions (§7.3). | All, esp. Huntington, M&T, Old National, SouthState | High |
| L7 | Post-selection inference: short-run terms screened and pruned on p < 0.05, so p-values are optimistic | All | Medium |
| L8 | Champions are chosen out of sample (§5.5). Selecting on the governing backtest makes that backtest optimistic for the chosen models, and the one-standard-error parsimony rule trades accuracy for fewer parameters at four banks. The out-of-sample champions are less stable in θ than the in-sample ones (§7.6). | All | Medium |
| L9 | Johansen p-values are bounds; r ≤ 1 rejections (implying rank 2) are overridden by assuming rank 1 | Glacier, Huntington, First Horizon | Medium |
| L10 | Single regressor (FFT). No competitive, liquidity or balance-sheet drivers | All | Medium |
| L11 | Cointegration with one unknown break (Gregory-Hansen, four forms) does not reject at 5% for any bank on ADF\* (finite-sample critical values, T = 62). With 62 quarters the test has low power, and two or more breaks are not tested. | All | Low |
| L12 | Glacier's champion keeps an insignificant constant and trend because its case 4 test requires them | Glacier | Low |
| L13 | KPSS p-values are truncated at 0.10 | All | Low |
| L14 | Deterministic trends in the Glacier and SouthState champions are frozen at their 2026Q2 value for projection (`projection/project.py`). The freeze is a judgment overlay, not an estimated feature; projections for these banks depend on that choice. | Glacier, SouthState | Medium |
| L15 | Huntington cointegration rests on one specification family (EG long run, no deterministic terms) and on post-2022 data: the test fails in every window ending in 2019Q4 and in 2021Q4 windows starting in 2013 or later. GH finds no break. Kept in scope with this caveat (decision 2026-10-31). The re-specified champion (short-run terms added, §5.5) is Green, but its λ is small (−0.066). | Huntington | High |
| L16 | Backtest limits are percentiles of the peer group, so the absolute test is a relative standard: one bank's re-specification can change another's rating (First Horizon turned Red after the Huntington and Old National re-specification (§5.5) with unchanged errors). The single-window backtest has one start date per horizon. | All | Medium |
| L17 | Beta stability is rated only from 2020Q1, because earlier samples are mostly zero-lower-bound data. The joint 2-SE-and-20% test does not flag large moves with wide standard errors. Four champions are Red. The realized-beta test is descriptive and has no threshold. | All, esp. Glacier, KeyBank, M&T, SouthState | Medium |
| L18 | The asymmetric fits are fragile: 23 of 78 cycled between regime splits, and several admissible variants forecast explosively. KeyBank's asymmetric champion rests on a λ split estimated from the regimes of one sample. | KeyBank, all asymmetric variants | Medium |

---

## 9. Validation Status and Open Issues

### 9.1 Validation Status
No independent validation has been performed. The open issues in §9.2 should be resolved before the model is submitted for validation.

### 9.2 Open Issues
Open issues are tracked as GitHub issues on [`Panda5130/Deposit-Beta`](https://github.com/Panda5130/Deposit-Beta/issues). GitHub replaces the open-issues log kept in earlier versions of this document; new issues are logged there. Closed issues and how they were resolved are recorded in `docs/open_issue_resolutions.md` and `docs/resolutions/*.md`.

Open at this version:

| Issue | Topic | Section |
| :-: | :--- | :--- |
| [#8](https://github.com/Panda5130/Deposit-Beta/issues/8) | Fix backtest band limits from an approved reference run instead of deriving them from the peer group each run (on hold) | §5.6, §7.1 |

Closed by [PR #15](https://github.com/Panda5130/Deposit-Beta/pull/15) on 2026-11-11: [#1](https://github.com/Panda5130/Deposit-Beta/issues/1) (champion selection on out-of-sample performance, now the default, §5.5) and [#13](https://github.com/Panda5130/Deposit-Beta/issues/13) (asymmetric lagged-Δy dynamics, now part of the asymmetric variants, §3.2).

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
python Beta_Backtesting/run_beta_backtest.py --first-origin 2016Q1 --realized
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
python -m pytest data_build projection ecm_tests
```

Optional in-sample comparison (§7.6):

```bash
python MAE_Backtesting/run_backtest.py --horizon 8Q --bank-name All --select in-sample
```

```bash
python Beta_Backtesting/run_beta_backtest.py --first-origin 2016Q1 --select in-sample
```

```bash
python MAE_Backtesting/compare_selection.py
```

`ECM workflow.py` also runs `ECM asymmetric variants.py`. The backtests write the default (out-of-sample) champions to `*/output/out_of_sample/` and the in-sample option to `*/output/`. `python data_build/build_dataset.py --refresh` re-downloads the FDIC data instead of using the cached snapshot, and `python data_build/build_fft.py --refresh` re-downloads `FEDFUNDS` from FRED. The projection takes any scenario CSV with the layout of the FFT files (quarter, `FFT`) covering T+1 onward and writes `projection/output/<scenario>_projection.csv`; `--no-freeze-trend` shows the unfrozen path for diagnostics.

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

FFT itself gives ZA `c` = -5.49, p 0.004, break 2022Q1. The break in the deposit rates mirrors the break in the regressor (§5.3).

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
| Asymmetric variants: estimates, summary and Wald tests | `ECM asymmetric estimation results.csv`, `asymmetric estimation result summary.csv`, `ECM asymmetric tests.csv` |
| Default (out-of-sample) champions: backtests, ratings, selection comparison | `MAE_Backtesting/output/out_of_sample/`, `Beta_Backtesting/output/out_of_sample/` |
| Realized-beta backtest | `Beta_Backtesting/output/out_of_sample/<bank>/realized_beta_8Q.{csv,png}`, `realized_beta_summary_8Q.csv`, `realized_beta_all_banks_8Q.png` |
| Open-issue resolution record | `docs/open_issue_resolutions.md` |

---
