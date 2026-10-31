# Data and projection: FFT builder and trend-freeze projection (RC3, issues #6 and #7)

Branch `claude/data-projection-8d60e5`. Nothing has been pushed, posted to GitHub or written to the vault, and the WIP doc is unchanged. Replacement text for the doc is in Part C.

## A. Results and verification

### A.1 FFT builder (#6, OI-21)

`data_build/build_fft.py` reads the monthly FRED `FEDFUNDS.csv`. It sets FFT for each calendar quarter to the mean of that quarter's three months and writes `FFT_2008-2026.csv` and `FFT_2011-2026.csv` in the existing format (blank index header, labels like `2011Q1`, column `FFT`).

- **Complete quarters only.** An incomplete quarter at either end of the series, such as the current quarter, is dropped with a warning that names it: `dropping incomplete quarter 2026Q4: 1 of 3 months of FEDFUNDS`. A missing month between complete quarters raises an error, because dropping it would leave a hole in the regressor.
- **`--refresh`** downloads `FEDFUNDS` from FRED (`fredgraph.csv`, no API key) and overwrites `FEDFUNDS.csv`. The file is overwritten only after the download parses. It was tested into a scratch folder: today's FRED download is byte-identical to the committed `FEDFUNDS.csv` (867 months, 1954-07 to 2026-09).
- **The quarterly average is kept as the regressor definition.** A quarter-end rate was considered on 2026-10-31 and rejected.

**Verification**

| Check | Result |
| :--- | :--- |
| Rebuilt files vs. hand-made files, 2008Q1 (2011Q1) to 2026Q2 | Byte-identical: same text, same float representation (the values are bit-for-bit equal) |
| 2026Q3 | Unchanged at 3.67, which is now the true average of Jul 3.63, Aug 3.63 and Sep 3.75. The hand-made 3.67 happened to equal it. |
| 2026Q4 | **Dropped.** FEDFUNDS has no 2026Q4 month yet, so the files now end at 2026Q3 (75 and 63 rows). |
| `python "ECM workflow.py"` rerun | `ECM model selection results.csv`, `ECM param selection results.csv`, `ECM estimation results.csv` and `estimation result summary.csv` are byte-identical (the bank data end at 2026Q2) |
| `Co-integration Tests.py` and `FlaggedRates_co-integration_respecification.py` rerun | `Co-integration_results.csv` and `co-integration_respecification_results.csv` are byte-identical |
| Tests (`data_build/test_build_fft.py`, 6 tests) | Pass: the committed files equal the complete-quarter means exactly; three-month mean; a trailing or leading partial quarter is dropped with a warning; a missing interior month raises; output format |

### A.2 Projection with trend freeze (#7, L14)

`projection/project.py` projects `rate_pf_clean` dynamically from the last observed quarter T (2026Q2) under a user-supplied FFT path for T+1 to T+H.

- **Model.** The bank's champion comes from `MAE_Backtesting/backtest.py::select_model`; `--model` overrides it. The coefficients are the full-sample one-step ECM in `ECM estimation results.csv`. Term names are validated with `backtest.spec_from_terms`, and regressors are rebuilt with `bank_plots.regressor`. The ECM is not re-implemented.
- **Recursion.** It is the same as `MAEBacktest.forecast`: predicted y is fed back as the lag, and FFT (level, `D.FFT.L0` and lagged differences) takes the scenario values.
- **Trend freeze.** For every t > T the `trend` regressor is held at its value at T. The trend counts from 1 at 2011Q1, so it is held at 62 for 2026Q2. With FFT held flat, the path converges to $c + \delta T + \theta x$. `--no-freeze-trend` lets the trend keep counting, for diagnostics only.
- **CLI.**

  ```bash
  python projection/project.py --scenario projection/scenarios/flat_8Q.csv
  ```

  This writes `projection/output/flat_8Q_projection.csv`. Columns: bank and model keys, `quarter`, `h`, `FFT`, `rate_pf_clean`, `trend` (value used) and `long_run_equilibrium` ($c + \delta\cdot$trend$ + \theta\cdot$FFT). Scenario quarters up to T are ignored. Quarters after T must run from T+1 without gaps.

**Sample flat scenario** (`projection/scenarios/flat_8Q.csv`): FFT = 3.67 (the observed 2026Q3 average) for 2026Q3 to 2028Q2. All 7 banks run.

| Bank | Champion | c | δ (per quarter) | θ | y at 2026Q2 | Equilibrium at FFT 3.67 | 4Q | 8Q | 8Q, trend not frozen | 40Q | 40Q, trend not frozen |
| :--- | :--- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| First Horizon | ARDL(3,4) case 4, AIC | 0.338 | −0.0107 | 0.517 | 1.742 | 1.571 | 1.595 | 1.567 | 1.500 | 1.571 | 1.164 |
| Glacier | ARDL(3,1) case 4, BIC | 0.236 | −0.0084 | 0.346 | 1.169 | 0.988 | 1.089 | 1.022 | 0.983 | 0.988 | 0.686 |
| M&T | ARDL(2,1) case 4, AIC | 0.303 | −0.0110 | 0.432 | 1.366 | 1.205 | 1.251 | 1.212 | 1.152 | 1.205 | 0.794 |
| Huntington | EG long run, `n`, AIC | – | – | 0.469 | 1.853 | 1.723 | 1.750 | 1.729 | same | 1.723 | same |
| KeyBank | ARDL(4,4) case 1, AIC | – | – | 0.398 | 1.540 | 1.459 | 1.462 | 1.454 | same | 1.459 | same |
| Old National | Johansen, det_order −1, fixed | – | – | 0.419 | 1.674 | 1.538 | 1.602 | 1.562 | same | 1.538 | same |
| SouthState | ARDL(4,3) case 1, AIC | – | – | 0.443 | 1.740 | 1.625 | 1.676 | 1.654 | same | 1.625 | same |

The equilibrium is $c + 62\delta + 3.67\,\theta$, in pp. Without the freeze, a trend champion's equilibrium falls by |δ| (0.008 to 0.011 pp) every quarter, with no limit. That is 0.04 to 0.07 pp by 8Q and 0.30 to 0.41 pp by 40Q, a drift that comes from the trend alone and not from FFT.

**Tests** (`projection/test_project.py`, 9 tests, all pass):
- **Three trend champions.** Exactly First Horizon, Glacier and M&T carry a trend.
- **Convergence.** With FFT held flat for 300Q, each trend champion converges to $c + \delta T + \theta x$. That value is computed from the `LR:` rows of `ECM estimation results.csv`, and the path ends within 1e-8 of it. The equilibrium column is constant, and y moves less than 1e-8 over the last 100 quarters, so there is no drift.
- **Drift without the freeze.** The unfrozen path drifts by exactly 100δ over the same 100 quarters, so the test above would catch a missing freeze.
- **No-trend champions.** The 4 banks without a trend give identical output with and without the overlay.
- **Coefficients.** The CSV coefficients equal a full-sample refit by `MAEBacktest.fit` (to 1e-10).
- **Recursion.** Without the freeze, projecting from T−8 with realized FFT reproduces `MAEBacktest.forecast` for all 7 banks (to 1e-12).
- **Scenario checks.** Quarters up to T are ignored, and gaps or a late start are rejected.
- **CLI.** It writes 7 banks × 8 quarters.

```bash
python -m pytest data_build projection
```

Result: 15 passed.

### A.3 Notes and follow-ups (not done here)
- **File names.** `FFT_*-2026.csv` keep their names so that every script still finds them. Once FEDFUNDS reaches 2027 the "2026" in the names will be stale; renaming touches every consumer and belongs to whoever owns the pipeline defaults.
- **Coverage check.** Nothing checks that FFT covers every bank quarter. `bank_plots.load_source` left-joins FFT, and `bank_data` silently drops quarters with a missing FFT. When 2026Q3 Call Report data are added before FEDFUNDS has October to December, nothing breaks (2026Q3 is complete), but a later bank quarter without FFT would be dropped silently. A warning in the estimation loader would close this.
- **Dependency on another thread's code.** The projection imports `select_model`, `spec_from_terms`, `bank_rows` and `model_mask` from `MAE_Backtesting/backtest.py`, which the eval-selection thread owns. If those signatures change, `projection/test_project.py` will fail and show it. If the model-form thread changes the champions, the projection picks them up from the CSVs with no code change.
- **Inputs only.** The projection is a point path given an FFT path, with no forecast intervals.

---

## B. Files

| File | Purpose |
| :--- | :--- |
| `data_build/build_fft.py` | FEDFUNDS → complete-quarter FFT files; `--refresh` downloads from FRED |
| `data_build/test_build_fft.py` | Builder tests |
| `FFT_2008-2026.csv`, `FFT_2011-2026.csv` | Rebuilt: 2026Q4 removed, earlier rows unchanged |
| `projection/project.py` | Projection module and CLI with the trend freeze |
| `projection/test_project.py` | Projection tests |
| `projection/scenarios/flat_8Q.csv` | Sample flat scenario (FFT 3.67, 2026Q3 to 2028Q2) |
| `projection/output/flat_8Q_projection.csv` | Projection for all 7 banks under the sample scenario |

---

## C. Replacement text for `WIP Regional Banking Deposit Beta Analyses.md`

### §3.3 Development Pipeline: replace rows 1 and 11, and add rows 1b and 12

| Step | Component | Code | Output |
| :-: | :--- | :--- | :--- |
| 1 | Data pull, rate construction and merger adjustment | `data_build/build_dataset.py` (supersedes `FDIC Fincancials pull and aggeregation.ipynb` and `TargetBank_merger_adjusted_features.ipynb`) | `consolidated_fdic_quarterly_financials_*.csv`, `merger_events_used.csv`, `merger_adjustment_log.md`, `data_build/raw/` |
| 1b | FFT regressor: FEDFUNDS averaged to complete calendar quarters | `data_build/build_fft.py` | `FFT_2011-2026.csv`, `FFT_2008-2026.csv` (from `FEDFUNDS.csv`) |
| … | *(rows 2 to 10 unchanged)* | | |
| 11 | Documentation figures | `docs/make_figures.py` | `docs/figures/` |
| 12 | Scenario projection with trend freeze | `projection/project.py` with a scenario CSV of FFT by quarter | `projection/output/<scenario>_projection.csv` |

Keep the closing line, "Steps 5 to 7 are run together by `ECM workflow.py`.", and add after it: "Steps 1b and 12 have tests: `python -m pytest data_build projection`."

### §4.1 Sources: replace the FRED bullet

- **FRED `FEDFUNDS`**: monthly effective federal funds rate (`FEDFUNDS.csv`). `data_build/build_fft.py` averages it over the three months of each calendar quarter and writes `FFT_2011-2026.csv` and `FFT_2008-2026.csv`. Only complete quarters are kept: an incomplete current quarter is dropped with a warning that names it, and a missing month inside the series stops the build. `--refresh` re-downloads `FEDFUNDS` from FRED. The files currently run to 2026Q3; the estimation sample ends at 2026Q2, the last quarter of bank data.

### §5.7 Key Assumptions: replace the last bullet

- For projection, a deterministic trend in the long-run relation is frozen at its end-of-sample value: for every quarter after T the trend regressor is held at its value at T (62 at 2026Q2, counting from 1 at 2011Q1). The equilibrium is therefore $c + \delta T + \theta x$, and with FFT held flat a projection converges to that level instead of drifting by δ per quarter. This is implemented in `projection/project.py` and tested in `projection/test_project.py`. It affects the First Horizon, M&T and Glacier champions; champions without a trend are unchanged.

### §8 Model Limitations: replace row L14

| L14 | Deterministic trends in the First Horizon, M&T and Glacier champions (δ = −0.011, −0.011 and −0.008 pp per quarter) are frozen at their 2026Q2 value for projection (`projection/project.py`). The freeze is a judgment overlay, not an estimated feature: the estimated model would keep lowering these banks' equilibrium by \|δ\| each quarter (0.04 to 0.07 pp over 8Q, 0.30 to 0.41 pp over 40Q at flat FFT). Projections for these banks depend on that choice. | First Horizon, M&T, Glacier | Medium |

### §9.2 Open Issues Log: replace rows OI-14 and OI-21

| OI-14 | Assess whether long-run trends are economically justified for projection | First Horizon, M&T, Glacier | Medium | Closed: trend kept for estimation; frozen at its end-of-sample value in projection, implemented and tested in `projection/project.py` (L14, [#7](https://github.com/Panda5130/Deposit-Beta/issues/7)) |
| OI-21 | FFT input carried 2026Q3 and 2026Q4 at 3.67 by hand, and 2026Q4 was not complete | All | Low | Closed: `data_build/build_fft.py` builds FFT from FRED `FEDFUNDS` with complete quarters only and warns on any quarter it drops; history through 2026Q2 is reproduced exactly; 2026Q3 is the true average (3.67); 2026Q4 is dropped ([#6](https://github.com/Panda5130/Deposit-Beta/issues/6)) |

### §10.2 Execution: replace the first block and add the projection and test blocks

```bash
python data_build/build_dataset.py
```

```bash
python data_build/build_fft.py
```

*(the cointegration, ECM workflow, backtest, plotting, diagnostics and figure blocks are unchanged)*

```bash
python projection/project.py --scenario projection/scenarios/flat_8Q.csv
```

```bash
python -m pytest data_build projection
```

Replace the closing sentence with:

`python data_build/build_dataset.py --refresh` re-downloads the FDIC data instead of using the cached snapshot, and `python data_build/build_fft.py --refresh` re-downloads `FEDFUNDS` from FRED. The projection takes any scenario CSV with the layout of the FFT files (quarter, `FFT`) covering T+1 onward. It writes `projection/output/<scenario>_projection.csv`. `--bank-name` and `--model` select one bank or model, and `--no-freeze-trend` shows the unfrozen path for diagnostics.

*(Optional, §10.3: the line "Gaps: no unit tests and no version pinning" becomes "Gaps: unit tests cover only the FFT builder and the projection layer; no version pinning.")*

---

## D. Draft GitHub comments (not posted)

### Issue #6: OI-21, refresh the FFT input

> Fixed on branch `claude/data-projection-8d60e5` (not pushed yet).
>
> - New `data_build/build_fft.py` builds `FFT_2008-2026.csv` and `FFT_2011-2026.csv` from FRED `FEDFUNDS`. FFT is the mean of each calendar quarter's three months.
> - Only complete quarters are written. An incomplete quarter at the end (or start) is dropped with a warning that names it, e.g. `dropping incomplete quarter 2026Q4: 1 of 3 months of FEDFUNDS`. A missing month inside the series is an error.
> - `--refresh` re-downloads `FEDFUNDS` from FRED. Today's download is identical to the committed `FEDFUNDS.csv` (to 2026-09).
>
> Verification:
> - The rebuilt files are byte-identical to the hand-made ones through 2026Q2.
> - 2026Q3 stays 3.67, which is now the true Jul to Sep average (3.63, 3.63, 3.75).
> - 2026Q4 is removed.
> - Rerunning `Co-integration Tests.py`, the re-specification grid and `ECM workflow.py` leaves every results CSV byte-identical, since the bank data end at 2026Q2.
> - Tests: `python -m pytest data_build`.
>
> Proposing to close once merged.

### Issue #7: trend-freeze projection overlay

> Implemented on branch `claude/data-projection-8d60e5` (not pushed yet).
>
> `projection/project.py` projects `rate_pf_clean` from 2026Q2 under a user-supplied FFT path.
> - The model is the champion from `select_model` with the coefficients in `ECM estimation results.csv`.
> - The recursion is the same as the backtest's dynamic forecast.
> - Any `trend` term is held at its value at T (62 at 2026Q2), so the equilibrium is c + δT + θx.
> - Usage: `python projection/project.py --scenario projection/scenarios/flat_8Q.csv`. This writes one CSV for all banks with the path and the long-run equilibrium per quarter.
>
> Under a flat 3.67 FFT scenario:
> - **First Horizon:** converges to 1.571; without the freeze it is at 1.164 by 40Q and still falling.
> - **Glacier:** 0.988 (0.686 without the freeze).
> - **M&T:** 1.205 (0.794 without the freeze).
> - **Other four banks:** unchanged by the overlay.
>
> Tests (`python -m pytest projection`):
> - With FFT flat for 300Q, each trend champion converges to c + δT + θx from the `LR:` rows, within 1e-8, and stops moving: less than 1e-8 change over the last 100Q.
> - The unfrozen path drifts by exactly 100δ.
> - No-trend champions are identical with and without the overlay.
> - Without the freeze, the recursion matches `MAEBacktest.forecast` for all 7 banks.
>
> Proposing to close once merged.
