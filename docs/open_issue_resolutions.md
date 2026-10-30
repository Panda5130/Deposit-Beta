# Open Issue Resolutions (OI-1 to OI-17)

Companion to `WIP Regional Banking Deposit Beta Analyses.md` v0.2. This file records what was done on branch `claude/resolve-open-issues-22ace3` for every open issue in §9.2 and limitation in §8, and gives the replacement text for the doc. The doc itself was **not** edited here; another session owns it.

Nothing on this branch has been pushed to GitHub or copied to the Obsidian vault.

## 0. Summary

| ID | Status | One-line outcome |
| :-: | :-: | :--- |
| OI-1 | Resolved | Real predecessor certs and last pre-merger deposits from FDIC for every event; materiality re-derived |
| OI-2 | Resolved | The four missing events plus all other ≥1% acquisitions since 2007 applied as full pro forma backfill |
| OI-3 | Resolved | Mode B rows kept in `rate_pf_clean` (decision); only 3 Mode B events remain in the main sample, all < 1% |
| OI-4 | Resolved | Re-specification grid now runs all 7 banks; it is now what qualifies Huntington and Old National |
| OI-5 | Resolved | Zivot-Andrews runs for all 7 banks (c / t / ct); the old failures were caused by data defects |
| OI-6 | Resolved | One-step ECMs now prune insignificant short-run lags; 0 of 163 short-run terms have p ≥ 0.05 |
| OI-7 | Resolved | Estimated ECMs carry the deterministic terms of their cointegration test; 0 mismatches (was 17 of 78) |
| OI-8 | Partially resolved | Old National's 2025Q2 drop was a data artifact (fixed). The shared 5Q error at origin 2025Q1 remains and is a model effect (symmetric pass-through); it goes to OI-11 |
| OI-9 | Deferred (user decision) | In-sample MAE rule retained for now; validation-window comparison recorded as evidence |
| OI-10 | Resolved | Green/Amber/Red thresholds adopted and implemented (`backtest_assessment_8Q.csv`) |
| OI-11 | Deferred | No challenger built; scope and the specific trigger (OI-8) documented |
| OI-12 | Resolved | Stale KeyBank 4Q backtest deleted |
| OI-13 | Resolved | Glacier 2012 anomaly was the calendar-year deposit average plus YTD de-cumulation across a charter consolidation; fixed by the rebuild |
| OI-14 | Resolved (user decision) | First Horizon trend kept for estimation; frozen at its 2026Q2 value for projection |
| OI-15 | Resolved (user decision) | y is now deposit interest expense only (`EDEPDOMQ` + `EDEPFORQ`) |
| OI-16 | Partially resolved | 2008–2026 merger-adjusted ADF/KPSS grid produced (`diagnostics/unit_root_grid.csv`); the vault placeholders still need to be filled by hand |
| OI-17 | Resolved | Figure 1 regenerated from the modeled dataset (`docs/figures_rebuild/`) |
| New | Open | OI-18 to OI-21: see §3 |

## 1. Decisions taken with the user (2026-10-30)

1. **Rate definition (OI-13, OI-15, Huntington 2021):** deposit interest expense only, FDIC quarterly fields, divided by the 2-point average of total deposits.
2. **Mergers (OI-1, OI-2, OI-3):** full pro forma backfill for every merger or failure acquisition ≥ 1% of survivor deposits, with the event list built from FDIC history. Mode B (< 1%) is flagged and kept.
3. **Champion rule (OI-9):** deferred to the validator; keep in-sample MAE for now.
4. **First Horizon trend (OI-14):** keep for estimation; freeze at the end-of-sample value in projections.
5. **Backtest thresholds (OI-10):** absolute plus no-change benchmark (rules in OI-10 below).

## 2. Changes on this branch

| Area | File(s) | Change |
| :--- | :--- | :--- |
| Data build | `data_build/build_dataset.py` (new), `data_build/raw/` (FDIC snapshot) | Replaces the Colab notebooks `FDIC Fincancials pull and aggeregation.ipynb` and `TargetBank_merger_adjusted_features.ipynb` (left unchanged, now superseded). Pulls FDIC financials and history, builds the pro forma series, and writes the four `consolidated_fdic_quarterly_financials_*` CSVs, `merger_events_used.csv` and `merger_adjustment_log.md`. `python data_build/build_dataset.py` uses the cached snapshot; `--refresh` re-downloads. |
| Data | `consolidated_fdic_quarterly_financials_{2008,2011}-2026[_merger_adjusted].csv`, `merger_events_used.csv`, `merger_adjustment_log.md` | Regenerated. New columns: `deposit_interest_expense`, `total_deposits`, `average_deposits`. Dropped: `interest_expense`, `total_domestic_deposits`, `annual_average_deposits`, `post_merger_quarter`, `avg_window_spans_merger`. `rate_pf_clean` keeps its name. |
| Cointegration | `FlaggedRates_co-integration_respecification.py` | Default bank list is now all 7 banks (OI-4). |
| Estimation | `ECM estimation.py`, `ECM workflow.py` | Deterministic terms follow the test specification (OI-7); short-run lags pruned general-to-specific (OI-6). Old behaviour is available with `--screen-deterministics --no-refine`. The workflow passes `--alpha` to estimation. |
| Backtest | `MAE_Backtesting/backtest.py`, `run_backtest.py` | Adds `naive_mae` (no-change forecast) to every table; new `backtest_assessment_8Q.csv` with the OI-10 rating. KeyBank `MAE_backtest_4Q.*` deleted (OI-12). |
| Diagnostics | `diagnostics/stationarity_and_breaks.py` (new) + 3 CSVs | ADF/KPSS grid for all banks and both samples; Zivot-Andrews for all banks (OI-5, OI-16). |
| Figures | `docs/make_figures.py` (new), `docs/figures_rebuild/` | Figure 1 and the 14 per-bank champion figures, regenerated. Written to `figures_rebuild/` so they don't overwrite the untracked `docs/figures/` in the main checkout. |
| Outputs | `Co-integration_results.csv`, `co-integration_respecification_results.csv`, `ECM * results.csv`, `estimation result summary.csv`, `Actuals vs Predictions/`, `MAE_Backtesting/output/` | All regenerated on the rebuilt data. |

Run order to reproduce:

```bash
python data_build/build_dataset.py
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
python MAE_Backtesting/run_backtest.py --horizon 8Q --bank-name All
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

## 3. Per-issue detail

### OI-1: Placeholder predecessor certs and deposits

**Status: Resolved.**

**Change:** `merger_events_used.csv` is now generated from FDIC `/history` (change codes 2xx: mergers, absorptions, whole-bank failure acquisitions) for each target cert, and recursively for each predecessor. Each row has the real `predecessor_cert`, the predecessor's last pre-merger quarter, its deposits that quarter, the survivor's deposits the same quarter, and `pct_of_survivor_deposits`. Rows with `depth = 0` are events into the 7 banks; `depth ≥ 1` are predecessors' own acquisitions.

**Evidence: the eight originally listed events, corrected:**

| Predecessor (old placeholder) | Real FDIC cert | FDIC effective date | Last pre-merger deposits ($000) | % of survivor | Mode |
| :--- | :-: | :-: | --: | --: | :-: |
| First Niagara Bank (22274) | 16004 | 2016-10-08 | 27,347,485 | 34.2 | A |
| FirstMerit Bank (11111) | 13675 | 2016-08-16 | 21,074,218 | 36.8 | A |
| TCF National Bank (22222) | 28330 | 2021-06-09 | 39,975,492 | 37.5 | A |
| IBERIABANK (33333) | 28100 | 2020-07-02 | 28,436,334 | 72.9 | A |
| "CenterState Bank" (44444) | **13425, South State Bank** | 2020-06-08 | 12,393,605 | 87.7 | **A (was B)** |
| Atlantic Capital Bank (55555) | 35525 | 2022-03-01 | 3,335,446 | 9.5 | A |
| First Midwest Bank (66666) | 3709 | 2022-02-16 | 17,578,256 | 94.1 | A |
| People's United Bank (77777) | 27334 | 2022-04-02 | 53,542,021 | 41.6 | A |

Notes:
- Cert 33555 ("SouthState Bank") is the former CenterState Bank charter. In the 2020 merger of equals, the predecessor charter that closed was South State Bank (cert 13425), so the event is South State into CenterState, at 88% of deposits. It is not a 0.5% Mode B event.
- The First Niagara cert in the old file (22274) was wrong (real: 16004). FDIC's charter merger date (2016-10-08) is later than the holding-company closing date (2016-08-01) used before.

### OI-2: Missing Mode A adjustments

**Status: Resolved.**

**Change:** pro forma backfill. For each Mode A event, the predecessor's quarterly deposit interest expense and quarter-end deposits are added to every pre-merger quarter of the survivor. In the merger quarter, the predecessor's last quarterly interest expense is added pro rata to the days before the effective date. Predecessors are made pro forma for their own Mode A events first (recursively). The old method adjusted only the quarter after the merger.

**Evidence:**
- Events into the 7 banks, effective 2011Q1 or later: **73 (70 Mode A, 3 Mode B)**. By bank (Mode A): First Horizon 4, Glacier 25, Huntington 6, KeyBank 1, M&T 2, Old National 13, SouthState 19. Since 2007: 92 events (83 A, 9 B). 300 predecessor-level events folded in.
- Events not in the old list include: Old National/Bremer 2025Q2 (32%), Old National/CapStar 2024Q2 (7%), SouthState/Independent Bank 2025Q1 (40%), First Horizon/Capital Bank 2017Q4 (37%), M&T/Hudson City 2015Q4 (24%), Glacier's 10-charter consolidation 2012Q2 (about 490% combined), Huntington/Veritex 2025Q4 (6%), and Huntington/Cadence 2026Q1 (24%).
- Validation (`merger_adjustment_log.md`): pro forma rate reconstruction difference 0.0; 0 duplicate keys; 0 negative rates; 0 missing `rate_pf_clean`.
- Mean change in `rate_pf_clean` against v0.2, 2011–2026 (rate definition and merger effects combined): First Horizon -0.13 pp, Glacier -0.20, Huntington -0.13, KeyBank -0.25, M&T -0.11, Old National -0.18, SouthState +0.11.

### OI-3: Mode B treatment

**Status: Resolved (decision: keep Mode B rows).**

**Evidence:** after re-deriving materiality, only three Mode B events fall in the main sample: Glacier/Treasure State Bank 2016Q3 (0.84%), KeyBank/KeyTrust Company 2014Q3 (0%, a trust company with no deposits), and Old National/Old National Trust Company 2014Q3 (0%). Excluding them would put gaps in a quarterly series used for an ECM, and their effect is below 1% of deposits.

### OI-4: Re-specification grid for Huntington and Old National

**Status: Resolved.**

**Change:** the grid's default bank list now covers all 7 banks.

**Evidence:** on the rebuilt data, Huntington and Old National **fail the baseline** at 5%:
- Huntington: EG long run p 0.085, EG short run 0.88, Johansen trace r ≤ 0 = 13.05 (> 0.10), ARDL(4,3) case 3 F 2.78 (p 0.32).
- Old National: EG long run 0.38, Johansen r ≤ 0 = 15.49 (< 0.10), ARDL(4,4) F 2.85 (p 0.30).

The grid is now what qualifies them:
- Huntington: only EG long run with no deterministic terms (t -3.13, p 0.019, AIC/BIC/t-stat). Johansen gives only r ≤ 1 rejections.
- Old National: EG long run `n` / BIC (p 0.0077) and Johansen `det_order -1`, k_ar_diff = 1 (r ≤ 0 = 13.91, p < 0.05).

Huntington's cointegration evidence is now the thinnest in the peer set (see OI-19).

### OI-5: Zivot-Andrews failures and coverage

**Status: Resolved.**

**Change:** `diagnostics/stationarity_and_breaks.py` runs ZA (c, t, ct; lag by AIC, max 4, with a fixed-lag fallback) for all 7 banks. No fallback was needed. The old failures (Huntington rank deficiency; M&T broadcast error) came from the zero-valued Huntington 2021Q1 quarter and the near-zero values of the old build.

**Evidence (2011–2026, levels, `regression = c`):** every bank rejects a unit root with a level break at 2022Q2–Q4:

| Bank | ZA stat (c) | p | Break | ct p |
| :--- | :-: | :-: | :-: | :-: |
| First Horizon | -6.28 | 0.001 | 2022Q3 | 0.051 |
| Glacier | -7.57 | 0.000 | 2022Q4 | 0.036 |
| Huntington | -6.34 | 0.000 | 2022Q2 | 0.008 |
| KeyBank | -6.81 | 0.000 | 2022Q3 | 0.076 |
| M&T | -6.42 | 0.000 | 2022Q3 | 0.079 |
| Old National | -6.21 | 0.001 | 2022Q3 | 0.335 |
| SouthState | -6.23 | 0.001 | 2022Q3 | 0.035 |

FFT itself gives the same result: ZA c = -5.49, p 0.004, break 2022Q1. The break in y mirrors the break in the regressor, so it does not contradict cointegration, but the I(1) classification is not robust to allowing a 2022 break. Recorded as OI-20.

### OI-6: Huntington `D.y.L1` insignificant

**Status: Resolved.**

**Change:** `ECM estimation.py` now refits each one-step ECM general-to-specific: it drops the least significant short-run lag while its p ≥ 0.05. λ, the long-run regressor and the test's deterministic terms are never dropped.

**Evidence:**
- Insignificant short-run terms across all estimated models: 0 of 163 now; 4 of 167 without pruning; 2 of 167 under the old method.
- The specific v0.2 model (Huntington ARDL(4,4) case 3) no longer passes the model screen on the rebuilt data (bounds F 2.78, p 0.32). Huntington's new champion is EG long run `n`, whose ECM has only λ and FFT.L1.

### OI-7: Deterministic terms, test vs. estimated ECM

**Status: Resolved.**

**Change:** each ECM's deterministic terms are now set by its test specification: `n` / case 1 / det_order -1 give none; `c` / cases 2–3 / det_order 0 give a constant; `ct` / cases 4–5 / det_order 1 give a constant and trend. The p-value screen no longer removes them.

**Evidence:**
- Under the old method on the rebuilt data, 17 of 78 models had a mismatch (Glacier 4/4, KeyBank 4/17, M&T 8/22, SouthState 1/7). Now there are 0 of 78.
- Champions are unchanged by this switch except KeyBank: under the old method, EG short run `n` (MAE 0.0316) would have won; with matched terms the winner is ARDL(4,4) case 1 (MAE 0.0317).
- Glacier's champion now carries a constant and trend that are individually insignificant (p 0.106 and 0.103) but required by its case 4 test.

### OI-8: Shared 5Q backtest spike (origin 2025Q1); Old National 2025Q2

**Status: Partially resolved.**

**Evidence:**
- **Old National 2025Q2 was a data artifact.** Bremer Bank (32% of deposits) merged on 2025-05-01 and was not in the event list. The calendar-year deposit average then divided 2025Q1 interest by mostly post-merger deposits. v0.2: 2025Q1 1.846%, 2025Q2 2.361%. Rebuilt: 1.867%, 1.908%.
- **The 5Q spike remains for M&T (0.335), SouthState (0.392) and Old National (0.364), and it is a model effect, not data.** At origin 2025Q1, deposit rates had just fallen sharply after the late-2024 cuts (M&T -0.27 pp in 2025Q1). With FFT flat at 4.33 in 2025Q2–Q3, the actual rates stopped falling: M&T 1.62 → 1.67 → 1.68, then 1.56, 1.37. The models kept moving toward their long-run equilibrium and predicted 1.42 → 1.01 for M&T (SouthState: 1.65 → 1.21 against an actual of about 1.8; Old National: 1.66 → 1.25 against about 1.9). Origins 2024Q4 and 2025Q2 show much smaller errors.
- Interpretation: in this easing cycle, deposit rates have so far passed through less on the way down than the symmetric long-run beta implies. This is L6 (symmetric pass-through) and is the specific trigger for the asymmetric-ECM challenger in OI-11.

### OI-9: Champion on out-of-sample MAE

**Status: Deferred (user decision 2026-10-30).** The in-sample MAE rule is retained.

**Evidence:** each model was ranked by dynamic-forecast MAE over the 8Q window before the holdout (validation, 2022Q3–2024Q2), and the pick was scored on the last 8Q (holdout, 2024Q3–2026Q2):

| Bank | Holdout, in-sample pick | Holdout, validation pick |
| :--- | :-: | :-: |
| First Horizon | **0.087** | 0.116 |
| M&T | **0.108** | 0.123 |
| Glacier | 0.080 | 0.080 (same) |
| SouthState | 0.164 | **0.139** |
| KeyBank | 0.140 | **0.130** |
| Huntington | 0.203 | 0.203 (same) |
| Old National | **0.173** | 0.196 |

Validation-window selection wins for 2 banks, loses for 3 and ties for 2. The validation window covers the hiking cycle and the holdout the easing cycle, so neither rule dominates. This should be revisited once a longer history or a challenger exists (OI-11).

### OI-10: Backtest acceptance thresholds

**Status: Resolved.**

**Rule (implemented in `MAE_Backtesting/backtest.py::assess`), on the 8 horizons' MAE (pp):**
- **Green:** mean ≤ 0.15 and mean below the no-change forecast's mean.
- **Amber:** mean 0.15–0.25, or the model beats no-change on fewer than 6 of 8 horizons.
- **Red:** mean > 0.25, or any horizon > 0.50.

**Evidence (`MAE_Backtesting/output/backtest_assessment_8Q.csv`):**

| Bank | Mean | Max | No-change mean | Beats no-change | Rating |
| :--- | :-: | :-: | :-: | :-: | :-: |
| First Horizon | 0.087 | 0.177 | 0.307 | 7/8 | Green |
| M&T | 0.108 | 0.335 | 0.235 | 6/8 | Green |
| KeyBank | 0.140 | 0.358 | 0.272 | 7/8 | Green |
| Glacier | 0.080 | 0.172 | 0.119 | 5/8 | Amber |
| SouthState | 0.164 | 0.392 | 0.182 | 5/8 | Amber |
| Old National | 0.173 | 0.364 | 0.207 | 6/8 | Amber |
| Huntington | 0.203 | 0.448 | 0.231 | 6/8 | Amber |

### OI-11: Benchmark / challenger models

**Status: Deferred.** No challenger was built in this pass. The no-change forecast added for OI-10 is a naive benchmark, not a challenger.

Proposed scope:
1. Static OLS beta (level on level), cycle-specific (2015–19, 2022–24 up; 2019–20, 2024–26 down).
2. Asymmetric ECM: separate λ (or θ) for positive and negative disequilibrium. This is triggered directly by OI-8.
3. An ECM with a 2022 regime dummy, for OI-20.

### OI-12: Stale KeyBank 4Q backtest

**Status: Resolved.** `MAE_Backtesting/output/KeyBank National Association/MAE_backtest_4Q.csv` and `.png` were deleted. The 8Q backtest for the current champion is the only KeyBank backtest.

### OI-13: Glacier 2012Q1 dip / 2012Q2 spike

**Status: Resolved.**

**Root cause:** on 2012-04-30, Glacier Bancorp merged 10 affiliate bank charters into Glacier Bank (cert 30788), and deposits went from $0.85bn to $5.0bn. Two defects combined:
1. The calendar-year average deposit denominator divided 2012Q1 interest by a year average that was mostly post-merger, giving 0.14%.
2. De-cumulating YTD interest (Q2 YTD minus Q1) mixed the combined entity's restated Q2 YTD with Glacier-only Q1, giving 15,428 against FDIC's quarterly 8,003.

**Evidence:** `rate_pf_clean` for 2012Q1/Q2 went from 0.144% / 1.497% (v0.2) to 0.487% / 0.494% (rebuilt). The pro forma series now runs smoothly through 2012 (0.605, 0.530, 0.487, 0.494, 0.410 for 2011Q3–2012Q3).

**Related, same root cause:** Huntington 2021Q1 was 0.000% because FDIC total interest expense (`EINTEXP`) is negative that quarter (YTD -118,334), probably hedge income, and the build clipped it to zero. Deposit-only interest expense is 10,760, and the rebuilt rate is 0.131%. Huntington 2011Q1 also moves from 1.007% to 0.752% (pro forma for FirstMerit, Fidelity and Advantage Bank, deposit-only).

### OI-14: First Horizon long-run trend

**Status: Resolved (user decision 2026-10-30): keep the trend for estimation and backtest; freeze it at its 2026Q2 value for projection.**

**Evidence:**
- The trend survives the full pro forma rebuild with Iberiabank (2020) and Capital Bank (2017) folded in, so it is not a stand-in for an unmodelled merger. LR trend -0.01068 pp/quarter (p 0.0005), about -0.65 pp over 2011–2026.
- The best no-trend alternative (ARDL(3,4) case 1 / EG short run `n`) has θ 0.467, in-sample MAE 0.0511 and holdout 0.118, against 0.517 / 0.0469 / 0.087 for the trend model.

**Projection overlay:** for any projection beyond the last observation, hold the trend term at its value at T (2026Q2), so the equilibrium is $c + \delta T + \theta x$, not $c + \delta t + \theta x$. There is no projection module in the repo yet, so this is a documented rule, not code.

> **Needs confirmation:** on the rebuilt data the M&T champion (ARDL(2,1) case 4, LR trend -0.011, p 0.0065) and the Glacier champion (case 4, trend p 0.10) also carry a trend. The proposed text below applies the same overlay to all trend champions.

### OI-15: Deposit interest expense instead of total interest expense

**Status: Resolved (user decision 2026-10-30).**

**Change:** y = 400 × (`EDEPDOMQ` + `EDEPFORQ`) ÷ ((`DEP`_t + `DEP`_{t-1}) / 2). Interest on borrowings, subordinated debt and other non-deposit liabilities is excluded. The denominator is still total deposits (interest-bearing and non-interest-bearing), so the beta is a total-deposit beta.

**Evidence:** levels fall by about 0.1–0.25 pp on average (see OI-2). The Huntington negative-total-interest-expense problem disappears.

### OI-16: Vault "ADF re-specification" placeholders (2008–2026 merger-adjusted)

**Status: Partially resolved.** The numbers exist (`diagnostics/unit_root_grid.csv`, `sample = 2008-2026`; summary in `diagnostics/unit_root_summary.csv`). They have **not** been written to the vault, which needs your approval.

Summary for 2008–2026 merger-adjusted, default spec (ADF c/AIC, KPSS c/auto):
- First Horizon is classified I(0): ADF p 0.049, KPSS p ≥ 0.10.
- The other six banks are flagged as inconclusive at levels: ADF does not reject, and KPSS p ≥ 0.10 (bounded).

### OI-17: Figure 1 does not match the modeled data

**Status: Resolved.** The main session closed OI-17 by regenerating Figure 1 from `EDA1_Stationarity_Tests.ipynb`. That figure reads the v0.2 data, so it goes stale once this branch's rebuilt data is merged; replace it then with the version below. `docs/make_figures.py` regenerates Figure 1 from `rate_pf_clean` (rebuilt) and FFT, 2011Q1–2026Q2: `docs/figures_rebuild/Historical Deposit Rates vs FFT.png`. The 14 per-bank champion figures are in the same folder. They are written there, not to `docs/`, because a parallel session owns Figure 1 and the untracked `docs/figures/` in the main checkout.

### New issues raised by this work

| ID | Issue | Bank(s) | Priority |
| :-: | :--- | :--- | :-: |
| OI-18 | Re-run the stationarity notebooks' replacements and update Appendix A (A.0–A.2) with the rebuilt data (`diagnostics/unit_root_grid.csv`) | All | Medium |
| OI-19 | Huntington cointegration rests on a single specification family (EG long run, no deterministic terms, p 0.019). Assess robustness, and consider whether Huntington should stay in scope | Huntington | High |
| OI-20 | Zivot-Andrews rejects a unit root with a 2022 level break for all banks (and for FFT). Test cointegration allowing a break (Gregory-Hansen) | All | Medium |
| OI-21 | FFT input carries 2026Q3 and 2026Q4 at 3.67; 2026Q4 is not yet complete (data date 2026-10-30). Not used in estimation (data end 2026Q2), but refresh before the next cycle | All | Low |

## 4. Replacement text for the doc

All numbers below come from the rebuilt outputs on this branch.

### §1.2 Banks in Scope (replace the "Merger treatment" column)

| # | Bank | FDIC Cert | Merger treatment in final dataset |
| :-: | :--- | :-: | :--- |
| 1 | First Horizon Bank | 4977 | Pro forma, 4 Mode A events since 2011 (incl. Capital Bank 2017, Iberiabank 2020) |
| 2 | Glacier Bank | 30788 | Pro forma, 25 Mode A events since 2011 (incl. 10-charter consolidation 2012), 1 Mode B |
| 3 | Huntington National Bank | 6560 | Pro forma, 6 Mode A events since 2011 (incl. FirstMerit 2016, TCF 2021, Cadence 2026) |
| 4 | KeyBank National Association | 17534 | Pro forma, 1 Mode A event (First Niagara 2016), 1 Mode B |
| 5 | Manufacturers and Traders Trust Company | 588 | Pro forma, 2 Mode A events (Hudson City 2015, People's United 2022) |
| 6 | Old National Bank | 3832 | Pro forma, 13 Mode A events since 2011 (incl. First Midwest 2022, Bremer 2025), 1 Mode B |
| 7 | SouthState Bank | 33555 | Pro forma, 19 Mode A events since 2011 (incl. South State 2020, Atlantic Capital 2022, Independent 2025) |

### §1.3 Summary of Current Results (replace table and following sentence)

| Bank | Selected specification | λ | θ | In-sample MAE (pp) | Mean 8Q backtest MAE (pp) | Rating |
| :--- | :--- | :-: | :-: | :-: | :-: | :-: |
| First Horizon Bank | ARDL(3,4), case 4, AIC | -0.375 | 0.517 | 0.0469 | 0.087 | Green |
| Glacier Bank | ARDL(3,1), case 4, BIC | -0.112 | 0.346 | 0.0292 | 0.080 | Amber |
| Huntington National Bank | EG long run, no deterministic terms, AIC (ADF lag 1) | -0.313 | 0.469 | 0.0709 | 0.203 | Amber |
| KeyBank National Association | ARDL(4,4), case 1, AIC | -0.110 | 0.398 | 0.0317 | 0.140 | Green |
| Manufacturers and Traders Trust Company | ARDL(2,1), case 4, AIC | -0.184 | 0.432 | 0.0383 | 0.108 | Green |
| Old National Bank | Johansen VECM rank 1, k_ar_diff=1 (fixed), det_order -1 | -0.135 | 0.419 | 0.0414 | 0.173 | Amber |
| SouthState Bank | ARDL(4,3), case 1, AIC | -0.082 | 0.443 | 0.0336 | 0.164 | Amber |

All λ and θ estimates are significant at the 5% level (all at 1% except KeyBank λ, p 0.010). Long-run betas fall between 0.35 and 0.52. On the rebuilt data, six series are I(1) under the default unit-root specification; Glacier is flagged (KPSS I(0) p 0.057).

### §1.4 Key Open Issues

Owned by the parallel session; suggested items to reflect: (1) Huntington's cointegration rests on one specification (OI-19); (2) the symmetric model over-predicts deposit-rate declines in the 2025 easing (OI-8, OI-11); (3) champion selection uses in-sample MAE (OI-9, deferred); (4) unit-root and cointegration results are sensitive to a 2022 break (OI-20).

### §4.1 Sources (replace fields sentence)

Fields: `CERT`, `REPDTE`, `EDEPDOMQ` and `EDEPFORQ` (quarterly interest expense on domestic and foreign-office deposits), `DEP` (total deposits). History endpoint change codes 2xx (mergers, absorptions, whole-bank failure acquisitions). Built by `data_build/build_dataset.py`; raw pulls cached in `data_build/raw/`.

### §4.2 Transformations (replace items 1–4)

1. **Quarterly deposit interest expense** is taken directly from FDIC's quarterly fields (`EDEPDOMQ` + `EDEPFORQ`). No year-to-date de-cumulation.
2. **Annualization:** × 4.
3. **Average deposits:** mean of the current and previous quarter-end `DEP`. No calendar-year averaging, so no look-ahead.
4. **Deposit rate:** `deposit_rate = 100 × 4 × deposit interest expense ÷ average deposits`.

### §4.3 Merger Adjustment Methodology (replace whole subsection)

- **Event list:** every merger, absorption or whole-bank failure acquisition into a target bank since 2007, from FDIC `/history`, with real predecessor certs (`merger_events_used.csv`). Materiality = predecessor deposits ÷ survivor deposits at the predecessor's last pre-merger quarter.
- **Mode A (≥ 1%):** full pro forma backfill. The predecessor's deposit interest expense and deposits are added to every pre-merger quarter; in the merger quarter, the predecessor's last quarterly interest expense is added pro rata to days before the effective date. Applied recursively to predecessors' own Mode A acquisitions.
- **Mode B (< 1%):** flagged only, rows kept in `rate_pf_clean`. In the main sample: Glacier/Treasure State Bank 2016Q3 (0.84%), KeyBank/KeyTrust 2014Q3 (0%), Old National/Old National Trust 2014Q3 (0%).
- **Counts:** 73 events into the 7 banks from 2011Q1 (70 Mode A, 3 Mode B); 92 since 2007; 300 predecessor-level events folded in.
- **Validations** (`merger_adjustment_log.md`): pro forma rate reconstruction difference 0.0; no duplicate keys; no negative or missing rates.

Remove the "Events listed" table and the "Data quality findings" bullets, or replace the table with the 8-row table in OI-1 above, marked "corrected".

### §4.5 Exploratory Review (replace second and third sentences and the Figure 1 note)

Deposit rates track FFT with a lag and partial pass-through through the 2016–2019 tightening, the 2020 cut to the zero bound, and the 2022–2023 tightening. Since late 2024, deposit rates have fallen more slowly than FFT. Figure 1 is generated from `rate_pf_clean` by `docs/make_figures.py`.

### §5.2 / §5.5 / §5.6 additions

- §5.2: "Unit-root tests and Zivot-Andrews break tests are run for all banks by `diagnostics/stationarity_and_breaks.py`."
- §5.5 item 2: "Parameter screen: within each surviving specification, keep short-run terms with coefficient p-value < 0.05. Deterministic terms are set by the test specification (n / case 1 / det_order -1: none; c / cases 2–3 / det_order 0: constant; ct / cases 4–5 / det_order 1: constant and trend) and are not screened."
- §5.5 new item 4b: "Refinement: in the one-step ECM, short-run lags with p ≥ 0.05 are removed one at a time (largest p first) and the model refit."
- §5.6 add: "Each window's MAE is compared with a no-change forecast (y held at its origin value). Ratings: Green, mean MAE ≤ 0.15 pp and below the no-change mean; Amber, mean 0.15–0.25 pp or beats no-change on fewer than 6 of 8 horizons; Red, mean > 0.25 pp or any horizon > 0.50 pp."
- §5.7 add: "For projection, a deterministic trend in the long-run relation is frozen at its end-of-sample value."

### §6 bank sections (data-treatment, cointegration, champion and outcomes paragraphs)

Champion coefficient tables are in `ECM estimation results.csv`; figures are in `docs/figures_rebuild/`.

**6.1 First Horizon**
- 6.1.1: "Pro forma for Mountain National (2013), TrustAtlantic (2015), Capital Bank Corporation (2017, 37%) and Iberiabank (2020-07-02, 73%)."
- 6.1.4 baseline: EG long run p 0.264; EG short run p 0.424; Johansen r ≤ 0 = 21.59 (< 0.01), r ≤ 1 = 2.93 (< 0.10); ARDL(4,4) case 3 F = 3.54 (p 0.169).
- 6.1.5: 23 one-step ECMs (9 ARDL, 7 EG, 7 Johansen). In-sample MAE 0.0469–0.0798. Long-run beta 0.404–0.527.
- 6.1.6 champion: ARDL(3,4), case 4, AIC; tied with HQIC and with case 5 AIC/HQIC. const 0.1266 (p 0.007), trend -0.00400 (p 0.007), λ -0.3747 (t -4.21), FFT.L1 0.1935, D.y.L1 0.3469, D.y.L2 -0.4059, D.FFT.L0 0.2171, D.FFT.L1 -0.1563 (p 0.026), D.FFT.L3 0.1511; LR const 0.338, LR trend -0.01068 (p 0.0005), **θ 0.5165** (t 16.9).
- 6.1.7: 8Q MAE 0.094, 0.044, 0.030, 0.067, 0.096, 0.086, 0.177, 0.103; mean 0.087 (Green). Replace the trend bullet with: "The long-run trend (-0.011 pp per quarter) survives full pro forma adjustment for Iberiabank and Capital Bank, so it does not stand in for an unmodelled merger. For projection it is frozen at its 2026Q2 value (§5.7)." Replace the λ bullet with: "λ = -0.37: about 37% of any disequilibrium closes each quarter."

**6.2 Glacier**
- 6.2.1: "Pro forma for 25 Mode A events since 2011, including the 2012-04-30 consolidation of 10 affiliate charters (First Security Bank of Missoula, Mountain West Bank, Western Security Bank, 1ST BANK, Valley Bank of Helena, First Bank of Wyoming, Citizens Community Bank, Big Sky Western Bank, Bank of the San Juans, First Bank of Montana) and Altabank (2021, 19%). Treasure State Bank (2016, 0.84%) is Mode B."
- 6.2.2 main row (rebuilt): I(0) ADF p 0.662, KPSS p 0.057, inconclusive (flagged); I(1) ADF p 0.0070, KPSS ≥ 0.10, stationary.
- 6.2.3: "Zivot-Andrews (c) -7.57, p < 0.001, break 2022Q4; (ct) p 0.036. A unit root is rejected when a 2022 level break is allowed (OI-20)."
- 6.2.4: baseline none pass (EG long run 0.353; Johansen r ≤ 0 = 13.17, > 0.10; ARDL(3,4) case 3 F 2.95, p 0.278). Re-specification: Johansen det_order 1, k_ar_diff = 1 (BIC, fixed): r ≤ 0 = 20.31 (< 0.05), r ≤ 1 = 5.64 (< 0.05); ARDL(3,1) cases 4 and 5 under BIC (F 6.04, p 0.007; F 8.25, p 0.004).
- 6.2.5: 4 one-step ECMs (2 ARDL, 2 Johansen). In-sample MAE 0.0292–0.0310. Long-run beta 0.277–0.346.
- 6.2.6 champion: ARDL(3,1), case 4, BIC. const 0.0265 (p 0.106) and trend -0.00094 (p 0.103) kept per test spec; λ -0.1123 (t -3.65); FFT.L1 0.0388; D.y.L1 0.7268; D.y.L2 -0.2730; D.FFT.L0 0.0485; **θ 0.3459** (t 6.05).
- 6.2.7: 8Q MAE 0.094, 0.031, 0.021, 0.017, 0.116, 0.172, 0.150, 0.040; mean 0.080 (Amber: beats no-change on 5 of 8 horizons). Delete the 2012 anomaly bullet and the deterministic-mismatch bullet (resolved: OI-13, OI-7). Check whether the negative fitted rate in 2020Q4 is still present (see the figure).

**6.3 Huntington**
- 6.3.1: "Pro forma for Fidelity Bank (2012), Advantage Bank (2014), FirstMerit (2016-08-16, 37%), TCF (2021-06-09, 38%), Veritex (2025-10-20, 6%) and Cadence Bank (2026-02-01, 24%)."
- 6.3.2 main row: I(0) ADF p 0.486, KPSS p 0.024, non-stationary; I(1) ADF p 0.0029, KPSS ≥ 0.10, stationary. **No longer flagged** (ADF I(1) robustness 6/6).
- 6.3.3: "Zivot-Andrews now runs: (c) -6.34, p < 0.001, break 2022Q2; (ct) p 0.008."
- 6.3.4: "Baseline: none pass at 5% (EG long run p 0.085; EG short run 0.882; Johansen r ≤ 0 = 13.05, > 0.10; ARDL(4,3) case 3 F 2.78, p 0.318). Re-specification (now run, OI-4): only EG long run with no deterministic terms passes (t -3.13, p 0.019 under AIC, BIC and t-stat). Johansen gives r ≤ 1 rejections only."
- 6.3.5: 3 one-step ECMs (all EG long run `n`, identical). In-sample MAE 0.0709. Long-run beta 0.469.
- 6.3.6 champion: EG long run, `n`, AIC (ADF lag 1, ECM lag 3). λ -0.3133 (t -7.97), FFT.L1 0.1471; **θ 0.4694** (t 26.8). No short-run terms survive.
- 6.3.7: 8Q MAE 0.101, 0.065, 0.163, 0.118, 0.094, 0.208, 0.424, 0.448; mean 0.203 (Amber). Replace the bullets with: "Cointegration rests on one specification family (OI-19)." and "Errors grow at 7Q–8Q (origins 2024Q2–Q3): with no contemporaneous FFT term, the model passes the late-2024 cuts through too slowly (forecast 2.5–2.6% in 2024Q4–2025Q2 against an actual of 2.1–2.25%)."

**6.4 KeyBank**
- 6.4.1: "Pro forma for First Niagara Bank (cert 16004, FDIC effective 2016-10-08, 34%). KeyTrust Company (2014, no deposits) is Mode B."
- 6.4.4 baseline: EG long run p 0.198 (fails; v0.2 passed); Johansen r ≤ 0 = 13.78 (< 0.10); ARDL(4,4) case 3 F 3.39 (p 0.193).
- 6.4.5: 17 one-step ECMs (8 ARDL, 8 EG, 1 Johansen). In-sample MAE 0.0317–0.0612. Long-run beta 0.397–0.487 (was 0.175–0.539).
- 6.4.6 champion: ARDL(4,4), case 1, AIC. λ -0.1102 (t -2.67, p 0.010); FFT.L1 0.0438; D.y.L1 0.5143; D.y.L2 -0.4424; D.y.L3 0.2780; D.FFT.L0 0.1207; D.FFT.L2 0.0956; **θ 0.3975** (t 13.7).
- 6.4.7: 8Q MAE 0.075, 0.026, 0.184, 0.060, 0.121, 0.171, 0.358, 0.123; mean 0.140 (Green). Delete the 4Q backtest bullet (OI-12). Replace the beta-range bullet with: "The beta range across passing specifications narrowed to 0.40–0.49 after the rebuild."

**6.5 M&T**
- 6.5.1: "Pro forma for Hudson City Savings Bank (2015-11-01, 24%) and People's United Bank (2022-04-02, 42%)."
- 6.5.2 main row: I(0) ADF p 0.245, KPSS p 0.035; I(1) ADF p 0.0023, KPSS ≥ 0.10. **No longer flagged.**
- 6.5.3: "Zivot-Andrews now runs: (c) -6.42, p < 0.001, break 2022Q3; (ct) p 0.079."
- 6.5.4 baseline: EG long run p 0.048 (pass); ARDL(2,1) case 3 F 5.18 (p 0.034, pass); Johansen r ≤ 0 = 12.98 (> 0.10).
- 6.5.5: 22 one-step ECMs (11 ARDL, 6 EG, 5 Johansen). In-sample MAE 0.0383–0.0654. Long-run beta 0.342–0.432.
- 6.5.6 champion: ARDL(2,1), case 4, AIC. const 0.0556 (p 0.021), trend -0.00202 (p 0.018); λ -0.1835 (t -3.91); FFT.L1 0.0792; D.y.L1 0.3335; D.FFT.L0 0.1385; LR trend -0.0110 (p 0.0065); **θ 0.4316** (t 10.3).
- 6.5.7: 8Q MAE 0.107, 0.043, 0.065, 0.029, 0.335, 0.115, 0.069, 0.104; mean 0.108 (Green). Replace the 5Q bullet with the OI-8 explanation. Delete the "no-intercept" bullet (OI-7). Add: "The champion carries a long-run trend; frozen for projection (§5.7)."

**6.6 Old National**
- 6.6.1: "Pro forma for 13 Mode A events since 2011, including Integra Bank (2011 failure, 28%), AnchorBank (2016, 21%), First Midwest (2022-02-16, 94%), CapStar (2024, 7%) and Bremer Bank (2025-05-01, 32%)."
- 6.6.2 main row: I(0) ADF p 0.582, KPSS p 0.031; I(1) ADF p 0.0031, KPSS ≥ 0.10.
- 6.6.3: "Zivot-Andrews (c) -6.21, p 0.001, break 2022Q3; (ct) p 0.335."
- 6.6.4: "Baseline: none pass at 5% (EG long run 0.379; Johansen r ≤ 0 = 15.49, < 0.10; ARDL(4,4) case 3 F 2.85, p 0.302). Re-specification (now run, OI-4): EG long run `n`/BIC (p 0.0077); Johansen det_order -1, k_ar_diff = 1 (r ≤ 0 = 13.91, < 0.05)."
- 6.6.5: 2 one-step ECMs (1 EG, 1 Johansen). In-sample MAE 0.0414–0.0585. Long-run beta 0.419–0.429.
- 6.6.6 champion: Johansen VECM rank 1, k_ar_diff = 1 (fixed), det_order -1. λ -0.1354 (t -3.49); FFT.L1 0.0567; D.y.L1 0.3063; D.FFT.L1 0.1024; **θ 0.4191** (t 13.9).
- 6.6.7: 8Q MAE 0.106, 0.052, 0.191, 0.094, 0.364, 0.173, 0.289, 0.114; mean 0.173 (Amber). Replace the 2025Q2 bullet with: "The 2025Q2 drop in v0.2 was a data artifact (unadjusted Bremer merger plus calendar-year deposit averaging) and is fixed. The remaining 5Q error is the shared easing-cycle effect (OI-8)." Delete the First Midwest bullet (applied) and the "no re-specification grid" bullet (run).

**6.7 SouthState**
- 6.7.1: "Cert 33555 is the former CenterState Bank charter. Pro forma for 19 Mode A events since 2011, including South State Bank (cert 13425, 2020-06-08, 88%; previously mislabelled as CenterState, Mode B, 0.5%), Atlantic Capital (2022-03-01, 9%) and Independent Bank (2025-01-01, 40%)." Delete the CenterState Mode B and placeholder notes.
- 6.7.4 baseline: EG long run 0.312; Johansen r ≤ 0 = 14.06 (< 0.10); ARDL(4,3) case 3 F 3.50 (p 0.174).
- 6.7.5: 7 one-step ECMs (5 ARDL, 2 Johansen). In-sample MAE 0.0336–0.0437. Long-run beta 0.424–0.524.
- 6.7.6 champion: ARDL(4,3), case 1, AIC. λ -0.0816 (t -2.72, p 0.009); FFT.L1 0.0361; D.y.L1 0.7917; D.y.L2 -0.6669; D.y.L3 0.2762; D.FFT.L0 0.1849; D.FFT.L1 -0.1443; D.FFT.L2 0.1447; **θ 0.4428** (t 11.2).
- 6.7.7: 8Q MAE 0.077, 0.091, 0.057, 0.124, 0.392, 0.126, 0.314, 0.129; mean 0.164 (Amber; was 0.104, best in v0.2). Replace the bullets with: "λ = -0.08 is the slowest adjustment in the peer set." and "Shares the 5Q easing-cycle error (OI-8)."

### §7.1 Rolling-Origin 8Q Backtest (replace table)

| Bank | 1Q | 2Q | 3Q | 4Q | 5Q | 6Q | 7Q | 8Q | Mean | No-change mean | Rating |
| :--- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| First Horizon Bank | 0.094 | 0.044 | 0.030 | 0.067 | 0.096 | 0.086 | 0.177 | 0.103 | 0.087 | 0.307 | Green |
| Glacier Bank | 0.094 | 0.031 | 0.021 | 0.017 | 0.116 | 0.172 | 0.150 | 0.040 | 0.080 | 0.119 | Amber |
| Huntington National Bank | 0.101 | 0.065 | 0.163 | 0.118 | 0.094 | 0.208 | 0.424 | 0.448 | 0.203 | 0.231 | Amber |
| KeyBank National Association | 0.075 | 0.026 | 0.184 | 0.060 | 0.121 | 0.171 | 0.358 | 0.123 | 0.140 | 0.272 | Green |
| Manufacturers and Traders Trust Company | 0.107 | 0.043 | 0.065 | 0.029 | 0.335 | 0.115 | 0.069 | 0.104 | 0.108 | 0.235 | Green |
| Old National Bank | 0.106 | 0.052 | 0.191 | 0.094 | 0.364 | 0.173 | 0.289 | 0.114 | 0.173 | 0.207 | Amber |
| SouthState Bank | 0.077 | 0.091 | 0.057 | 0.124 | 0.392 | 0.126 | 0.314 | 0.129 | 0.164 | 0.182 | Amber |

### §7.2 Observations (replace)

- Out-of-sample MAE is about 2 to 5 times in-sample MAE. In-sample MAE fell for every bank after the rebuild (now 0.029–0.071), mostly because the de-cumulation and denominator artifacts are gone.
- Long-run betas range from 0.35 (Glacier) to 0.52 (First Horizon); the other five lie between 0.40 and 0.47.
- Acceptance thresholds are defined (§5.6): 3 Green, 4 Amber, 0 Red.
- M&T, SouthState and Old National share a large 5Q error at origin 2025Q1, where the models over-predict the post-cut decline in deposit rates (OI-8).

### §8 Model Limitations (replace rows)

| # | Limitation | Affected banks | Impact |
| :-: | :--- | :--- | :-: |
| L1 | Short sample (62 quarters, 2011Q1 to 2026Q2) lowers the power of unit-root and cointegration tests | All | High |
| L2 | Stationarity classification depends on the specification; Glacier remains flagged (KPSS I(0) p 0.057), and all series reject a unit root once a 2022 level break is allowed (OI-20) | All, esp. Glacier | High |
| L3 | Results are not robust to the 2008–2026 sample: six banks inconclusive at levels, First Horizon I(0) (Appendix A) | All | Medium |
| L4 | Pro forma merger adjustment assumes the combined franchise priced like the sum of its parts before the merger; merger-quarter interest is pro-rated by days; predecessors without FDIC Call Reports (none so far) would be skipped | All | Low to medium |
| L5 | The deposit rate covers deposit interest expense over total deposits; it is a total-deposit (not interest-bearing-deposit) beta and does not separate product mix | All | Low |
| L6 | Linear, symmetric pass-through. The 2025 backtest shows the models over-predict deposit-rate declines after cuts (OI-8) | All | High |
| L7 | Post-selection inference: short-run terms screened and pruned on p < 0.05, so p-values are optimistic | All | Medium |
| L8 | Champion chosen on in-sample MAE (OI-9 deferred); several specifications still collapse to the same ECM | All | Medium |
| L9 | Johansen p-values are bounds; r ≤ 1 rejections (implying rank 2) are overridden by assuming rank 1 | Glacier, Huntington, First Horizon | Medium |
| L10 | Single regressor (FFT). No competitive, liquidity or balance-sheet drivers | All | Medium |
| L11 | Zivot-Andrews is univariate; no cointegration test allowing a break (Gregory-Hansen) has been run | All | Medium |
| L12 | *(Resolved: deterministic terms now match the test specification.)* Glacier's champion keeps an insignificant constant and trend required by its case 4 test | Glacier | Low |
| L13 | KPSS p-values are truncated at 0.10 | All | Low |
| L14 | Deterministic trends in the First Horizon, M&T and Glacier champions are frozen at their end-of-sample value for projection; the overlay has no code yet | First Horizon, M&T, Glacier | Medium |
| L15 | Huntington cointegration rests on one specification family (OI-19) | Huntington | High |

### §9.2 Open Issues Log (replace Status column; add rows)

| ID | Status |
| :-: | :--- |
| OI-1 | Closed: real certs and deposits from FDIC (`merger_events_used.csv`) |
| OI-2 | Closed: all ≥1% events since 2007 applied as pro forma backfill |
| OI-3 | Closed: Mode B rows kept (3 events, all < 1%) |
| OI-4 | Closed: grid runs all 7 banks |
| OI-5 | Closed: ZA runs for all banks; see OI-20 |
| OI-6 | Closed: short-run lags pruned in the one-step ECM |
| OI-7 | Closed: deterministic terms follow the test specification |
| OI-8 | Partially closed: Old National 2025Q2 data artifact fixed; shared 5Q error is a model effect, moved to OI-11 |
| OI-9 | Deferred: in-sample MAE retained; validation-window comparison recorded |
| OI-10 | Closed: Green / Amber / Red thresholds adopted |
| OI-11 | Open: asymmetric ECM now a priority (OI-8) |
| OI-12 | Closed: stale 4Q backtest deleted |
| OI-13 | Closed: rate rebuilt from quarterly fields with a 2-point deposit average |
| OI-14 | Closed: trend kept; frozen in projection |
| OI-15 | Closed: deposit interest expense only |
| OI-16 | Partially closed: numbers produced; vault update pending approval |
| OI-17 | Closed: Figure 1 regenerated |
| OI-18 | Open (new): update Appendix A with rebuilt unit-root results |
| OI-19 | Open (new), High: Huntington cointegration robustness |
| OI-20 | Open (new): cointegration allowing a 2022 break |
| OI-21 | Open (new), Low: refresh FFT; 2026Q4 not yet complete |

### §10 Implementation (additions)

- §10.2: add `python data_build/build_dataset.py` as the first step, `python diagnostics/stationarity_and_breaks.py` after the cointegration steps, and `python docs/make_figures.py` last.
- §10.3: add "The FDIC snapshot used for a run is cached in `data_build/raw/` and committed with the outputs."

### Appendix B (additions)

`data_build/build_dataset.py`, `data_build/raw/*.csv`, `diagnostics/*.csv`, `MAE_Backtesting/output/backtest_assessment_8Q.csv`, `docs/figures_rebuild/`, `docs/open_issue_resolutions.md`. `merger_events_raw.csv` (branch-level history only) and the two Colab notebooks are superseded.
