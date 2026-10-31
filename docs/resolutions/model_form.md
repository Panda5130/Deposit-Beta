# Model form (RC1): break tests, challengers and Huntington

Resolution notes for root cause RC1: every champion ECM is linear and symmetric, with no regime break and no asymmetry. This note covers GitHub issues [#5](https://github.com/Panda5130/Deposit-Beta/issues/5) (OI-20, Gregory-Hansen), [#2](https://github.com/Panda5130/Deposit-Beta/issues/2) (OI-11, challengers, and the open part of OI-8) and [#4](https://github.com/Panda5130/Deposit-Beta/issues/4) (OI-19, Huntington).

- Code: `model_form/` (`gregory_hansen.py`, `challengers.py`, `run_model_form.py`). It calls `MAE_Backtesting/backtest.py` and reads `Beta_Backtesting/output/`, and edits neither.
- Outputs: `model_form/output/`.
- Status: WIP. Nothing here has been folded into `WIP Regional Banking Deposit Beta Analyses.md`. The **Huntington scope decision is pending with the user** (§4).

```bash
python model_form/run_model_form.py --reps 2000 --first-origin 2016Q1 --horizon 8
```

A full run takes about 8 minutes, most of it on the Gregory-Hansen simulation. The run checks that the re-run champion matches `MAE_Backtesting/output/backtest_multiorigin_8Q.csv` on every horizon, start-date count and MAE (gap < 1e-9) and stops if it does not. Every challenger is therefore scored on exactly the same start dates as the champions.

---

## 1. Summary

1. **Gregory-Hansen (#5).** All seven banks were tested with level shift (C), level shift with trend (C/T), regime shift (C/S) and regime shift with trend (C/S/T). **No bank rejects "no cointegration" at 5% on ADF\* once the critical values are simulated for T = 62.** The one rejection is Glacier, on C/T, which rejects on Zt\* (−5.42 against −5.24) and on ADF\* only under the asymptotic value. The minimising break dates fall at 2023Q3–2024Q1 (C, C/T) or 2021Q3–Q4 (C/S), not at the 2022Q2–Q4 Zivot-Andrews level breaks. In short, allowing one break does not strengthen the cointegration evidence. Because no test rejects, the estimated break dates carry little information.
2. **Challengers (#2).** Seven challengers plus one sensitivity were scored on the champions' backtest. No challenger beats the champions across the peer group, and none should replace them wholesale.
   - The **asymmetric ECM** (separate λ for positive and negative disequilibrium) finds slower downward adjustment for six of seven banks. The difference is significant at 5% only for Huntington (λ+ −0.118 vs. λ− −0.459, Wald p 1.4e-07); it is borderline for Old National (p 0.051) and SouthState (0.077).
   - In the backtest, the asymmetric ECM **turns Huntington from Red to Green** (mean h-step MAE 0.334 → 0.264). It improves Old National and SouthState slightly, leaves M&T unchanged, and worsens First Horizon (Amber), Glacier (Red, skill 1.20 at 8Q) and KeyBank.
   - The static and cycle betas are Red or Amber everywhere.
   - The 2022 level dummy enters only from the 2023Q3 start date. Where it enters, it is worse than the champion except at M&T, where it is about equal.
3. **OI-8: asymmetry does not remove the shared error at the 2025Q1 start date.** The 5-quarter window MAE falls only from 0.335 to 0.316 (M&T), 0.364 to 0.279 (Old National) and 0.392 to 0.354 (SouthState).
   - Cause: 63% to 72% of the champions' forecast fall from 2025Q1 comes from the **lagged-Δy (momentum) terms**, which carry the sharp 2025Q1 drop (−0.24 to −0.27 pp) forward. Error correction, the term that asymmetry changes, contributes only −0.06 to −0.09 pp.
   - Only the anchored static and cycle betas, which have no momentum term, get the window right (0.045–0.104). They lose overall.
4. **Huntington (#4).** The two Huntington-only variants change the picture:
   - Adding a contemporaneous ΔFFT term to the champion ECM gives **Green, mean 0.240**, the best Huntington result. The term was never available to the pipeline: an EG long-run specification enters the one-step ECM with no short-run terms.
   - The asymmetric ECM also gives Green.
   - The cointegration evidence remains weak. It rests on one specification family, and Gregory-Hansen does not support it. EG without deterministic terms fails in 5 of the 15 sample windows tested, every one of which ends by 2021Q4 (windows ending in 2024 or later all pass). The long-run beta drifts from 0.551 to 0.465 across origins.
   - **Recommendation: keep Huntington in scope with a caveat and a re-specified champion.** The decision is the user's (§4).

---

## 2. Gregory-Hansen tests (issue #5, OI-20)

**Method** (`model_form/gregory_hansen.py`):
- Residual-based cointegration test with one unknown break, Gregory and Hansen (1996). The break τ runs over the trimmed range 15% to 85% of the sample. For each τ, the cointegrating regression of `rate_pf_clean` on FFT is fitted with a shift dummy D = 1 after τ, and its residuals are tested.
- **Statistics:** ADF\* (no constant; lag by AIC, max 4), Zt\* and Zα\* (Bartlett kernel), each the minimum over τ.
- **Break date:** the first quarter with D = 1, the same convention as `diagnostics/zivot_andrews.csv`.
- **Critical values:** the asymptotic values (GH 1996, Table 1, m = 1) are reported alongside finite-sample values simulated for T = 62. The simulation draws 2,000 pairs of independent random walks, with the same trimming and lag rule, and a fixed seed.
- The finite-sample values are markedly larger in magnitude. For example, the C model's ADF\* 5% value is −5.14 for T = 62 against −4.61 asymptotically. **The simulated values govern.**

**Table GH-1. ADF\* (minimum over breaks) and break date, 2011Q1–2026Q2.** No ADF\* value is below its simulated 5% critical value. "asy only" marks a rejection under the asymptotic value alone.

| Bank | C: ADF\*, break | C/T | C/S | C/S/T | ZA break `c` / `t` / `ct` |
| :--- | :-: | :-: | :-: | :-: | :-: |
| First Horizon | −4.05, 2016Q3 | −4.53, 2023Q4 | −4.50, 2021Q4 | −4.58, 2023Q4 | 2022Q3 / 2021Q4 / 2023Q1 |
| Glacier | −3.90, 2024Q1 | −5.44, 2023Q3 (asy only) | −4.09, 2021Q3 | −5.30, 2024Q1 | 2022Q4 / 2021Q3 / 2023Q1 |
| Huntington | −3.79, 2023Q4 | −4.42, 2023Q4 | −3.96, 2021Q3 | −4.37, 2023Q4 | 2022Q2 / 2021Q4 / 2022Q3 |
| KeyBank | −3.90, 2024Q1 | −4.72, 2024Q1 | −4.30, 2021Q3 | −4.75, 2024Q1 | 2022Q3 / 2021Q4 / 2022Q3 |
| M&T | −3.94, 2016Q1 | −4.49, 2024Q1 | −4.25, 2021Q4 | −4.78, 2023Q3 | 2022Q3 / 2021Q2 / 2022Q3 |
| Old National | −3.85, 2024Q1 | −4.60, 2024Q1 | −4.01, 2021Q3 | −4.53, 2024Q1 | 2022Q3 / 2022Q1 / 2019Q3 |
| SouthState | −3.82, 2024Q1 | −4.41, 2024Q1 | −3.87, 2024Q1 | −4.37, 2024Q1 | 2022Q3 / 2021Q3 / 2022Q4 |

**Table GH-2. Critical values (1% / 5% / 10%).**

| Model | ADF\*, Zt\*: asymptotic (GH 1996) | ADF\*: simulated, T = 62 | Zt\*: simulated | Zα\*: asymptotic | Zα\*: simulated |
| :--- | :-: | :-: | :-: | :-: | :-: |
| C | −5.13 / −4.61 / −4.34 | −5.69 / −5.14 / −4.82 | −5.51 / −4.89 / −4.54 | −50.07 / −40.48 / −36.19 | −39.59 / −33.68 / −30.31 |
| C/T | −5.45 / −4.99 / −4.72 | −6.18 / −5.50 / −5.23 | −5.96 / −5.24 / −5.01 | −57.28 / −47.96 / −43.22 | −43.79 / −37.33 / −34.96 |
| C/S | −5.47 / −4.95 / −4.68 | −6.14 / −5.46 / −5.08 | −5.89 / −5.21 / −4.87 | −57.17 / −47.04 / −41.85 | −43.57 / −36.80 / −33.55 |
| C/S/T | −6.02 / −5.50 / −5.24 | −6.45 / −5.82 / −5.55 | −6.34 / −5.70 / −5.36 | −69.37 / −58.58 / −53.31 | −47.16 / −41.28 / −38.36 |

Zt\* and Zα\* reach the same verdict. Of the 56 Zt\* and Zα\* results, the only 5% rejection is Glacier's C/T Zt\* (−5.42, break 2023Q3), which rejects against both the simulated and the asymptotic value. Every bank's values are in `gregory_hansen.csv`.

![Gregory-Hansen ADF t by candidate break](<../../model_form/output/gregory_hansen_adf_by_break.png>)

*Figure GH-1: ADF t on the cointegrating residuals at every candidate break, C (level shift) and C/S (regime shift), with the simulated 5% critical values. Source: `model_form/output/gregory_hansen_adf_by_break.png`.*

**Reading.**
- **The break hypothesis does not rescue or strengthen cointegration.** At no candidate date does a level or regime shift give residuals that reject a unit root at 5% (Figure GH-1). In the C model the lowest ADF t comes from a break before 2017 (First Horizon, M&T) or after 2023 (the other five), not from the 2022 rate break.
- **The ZA result is a property of each series, not of the relationship.** Zivot-Andrews rejects a unit root in each series once a 2022 level break is allowed. That 2022 break is common to the deposit rates and FFT. A break common to both series cancels in the cointegrating regression, which is consistent with GH finding no break in the relationship.
- **GH does not overturn the existing results.** GH tests no cointegration against cointegration with a break; it is not a test of the no-break model. With 62 quarters it also has lower power than the EG, Johansen and ARDL tests when there is no break. So a failure to reject does not contradict the existing cointegration results; it simply adds no support for a break.
- **The break dates are not informative.** Because the null is not rejected, the minimising τ is not an estimate of anything. Even so, the C and C/T minima cluster at 2023Q3–2024Q1, the top of the hiking cycle, which is where the champions' long-run fit is weakest.

**Champion ECM with a 2022 level dummy, full sample (challenger c).**

| Bank | δ on D2022.L1 (p) | Long-run shift −δ/λ (p) | θ with dummy | θ champion | λ with dummy |
| :--- | :-: | :-: | :-: | :-: | :-: |
| First Horizon | 0.115 (0.083) | 0.267 (0.066) | 0.453 | 0.517 | −0.430 |
| Glacier | 0.105 (0.006) | 0.656 (0.002) | 0.174 | 0.346 | −0.161 |
| Huntington | 0.136 (0.031) | 0.437 (0.038) | 0.386 | 0.469 | −0.311 |
| KeyBank | 0.060 (0.083) | 0.504 (0.116) | 0.297 | 0.398 | −0.119 |
| M&T | 0.131 (0.006) | 0.542 (0.003) | 0.301 | 0.432 | −0.241 |
| Old National | 0.091 (0.052) | 0.626 (0.068) | 0.295 | 0.419 | −0.145 |
| SouthState | 0.052 (0.131) | 0.646 (0.194) | 0.314 | 0.443 | −0.080 |

**What the dummy does.**
- It raises the post-2022 equilibrium deposit rate by 0.27 to 0.66 pp and lowers θ by 0.06 to 0.17. The shift and the beta trade off, because after the break there is only one hiking cycle to separate them.
- The dummy is significant at 5% for Glacier, Huntington and M&T.
- It does not improve forecasts (§3).

---

## 3. Challengers (issue #2, OI-11)

### 3.1 Specifications

Every challenger subclasses `MAEBacktest`, so `multi_errors` re-estimates it and scores it exactly as it does the champions:
- Start dates every quarter from 2016Q1 to 2026Q1, with an expanding window.
- Dynamic forecasts with predicted y fed back and realized FFT, h = 1 to 8.
- h-step MAE over 34 to 41 start dates, and the no-change benchmark.

| Code | Challenger | Form |
| :-: | :--- | :--- |
| a0 | Two-step ECM (control) | The long run (θ, deterministic terms) comes from the champion's one-step fit at each origin. Then Δy is regressed on ect(t−1) and the champion's short-run terms. Symmetric, so a1 and a2 can be compared without the two-step change. |
| a1 | Asymmetric ECM, sign of disequilibrium | As a0, with ect⁺(t−1) and ect⁻(t−1): λ+ applies when y is above its long-run level, λ− when below (threshold-autoregressive form) |
| a2 | Asymmetric ECM, FFT direction | As a0, with λ split between easing quarters (FFT down more than 0.25 pp over 4 quarters) and all others |
| b1 | Static OLS beta, levels | y = a + b·FFT, forecast a + b·FFT(t) |
| b2 | Static OLS beta, anchored | The same b applied to the FFT change since the origin: y(o) + b·(FFT(t) − FFT(o)) |
| b3 | Cycle-specific betas | The latest up-cycle and down-cycle beta available at the origin, applied quarter by quarter to the FFT change according to its sign |
| c | Champion ECM + 2022 level dummy | The champion's terms plus D(t−1), with D = 1 from 2022Q3 (the modal ZA `c` break) |
| c′ | Sensitivity | As c, with D = 1 from 2022Q1 (the FFT break) |

**Fallbacks** (each origin's choice is recorded in `fit_forms.csv`):
- **a1, a2:** when either regime has fewer than 6 training quarters, the model uses the symmetric ect. This applies to a1 at 56 of 287 bank-origins: 3 to 15 per bank, all before 2018 except Glacier (to 2019Q1), SouthState (to 2020Q2) and Old National (to 2022Q2). a2 falls back at 140 bank-origins.
- **c:** the dummy needs 4 post-break training quarters, so c equals the champion at every origin up to 2023Q2 and differs only from 2023Q3 to 2026Q1 (77 bank-origins; c′ 91).
- **b3:** before an FFT move of 0.20 pp the model uses the static beta. Before the first down cycle it uses the up-cycle beta for both directions.

**Cycle definitions:**
- Each cycle runs from the last quarter before the first policy move to the last quarter before the first opposite move, so the lagged pass-through falls inside the cycle.
- The four cycles: 2015Q3–2019Q2 (up, ΔFFT +2.26), 2019Q2–2021Q4 (down, −2.32), 2021Q4–2024Q2 (up, +5.25) and 2024Q2–2026Q2 (down, −1.70, ongoing).

**Table CH-1. Full-sample cycle betas** (Δ deposit rate ÷ Δ FFT over each cycle) and the static OLS beta.

| Bank | 2015–19 up | 2019–20 down | 2022–24 up | 2024–26 down | Static OLS (levels) |
| :--- | :-: | :-: | :-: | :-: | :-: |
| First Horizon | 0.328 | 0.408 | 0.448 | 0.399 | 0.374 |
| Glacier | 0.061 | 0.133 | 0.265 | 0.178 | 0.190 |
| Huntington | 0.273 | 0.340 | 0.448 | 0.339 | 0.366 |
| KeyBank | 0.274 | 0.326 | 0.413 | 0.390 | 0.341 |
| M&T | 0.195 | 0.279 | 0.372 | 0.374 | 0.290 |
| Old National | 0.229 | 0.271 | 0.394 | 0.278 | 0.317 |
| SouthState | 0.228 | 0.297 | 0.397 | 0.267 | 0.307 |

The 2022–24 up-cycle beta is the highest in every bank. In the current down cycle, pass-through is lower than in the 2022–24 up cycle for every bank except M&T (0.374 vs. 0.372). This is the asymmetry the ECMs miss.

### 3.2 Asymmetry tests, full sample

**Table CH-2. λ by regime (p-value) and Wald test of equal λ** (`asymmetry_tests.csv`).

| Bank | a1: λ+ (y above LR) | a1: λ− (y below LR) | a1: Wald p | a2: λ easing | a2: λ other | a2: Wald p |
| :--- | :-: | :-: | :-: | :-: | :-: | :-: |
| First Horizon | −0.378 (5.3e-04) | −0.381 (3.2e-05) | 0.975 | −0.499 (0.002) | −0.395 (1.0e-05) | 0.378 |
| Glacier | −0.065 (0.133) | −0.129 (2.9e-05) | 0.176 | −0.009 (0.889) | −0.125 (1.6e-05) | 0.101 |
| Huntington | −0.118 (0.008) | −0.459 (6.3e-18) | **1.4e-07** | −0.409 (0.045) | −0.310 (6.6e-12) | 0.629 |
| KeyBank | −0.101 (0.034) | −0.128 (0.029) | 0.654 | −0.160 (0.071) | −0.109 (0.011) | 0.517 |
| M&T | −0.137 (0.028) | −0.209 (6.3e-05) | 0.273 | −0.134 (0.161) | −0.188 (6.6e-05) | 0.551 |
| Old National | −0.090 (0.041) | −0.201 (1.4e-04) | 0.051 | −0.045 (0.751) | −0.133 (8.8e-04) | 0.514 |
| SouthState | −0.060 (0.058) | −0.142 (0.002) | 0.077 | 0.058 (0.594) | −0.077 (0.010) | 0.187 |

**Reading.**
- **The sign of λ+ − λ− is the same for six of seven banks.** Deposit rates above their long-run level close the gap more slowly (λ+ smaller in magnitude) than rates below it. This is downward stickiness. First Horizon has none.
- **The difference is significant at 5% only for Huntington,** and at 10% for Old National and SouthState.
- **Splitting λ by FFT direction (a2) finds nothing:** no Wald p below 0.10. Only 13 easing quarters are in the sample.

### 3.3 Many-start-date backtest

**Table CH-3. Mean h-step MAE over 1Q to 8Q (pp) and rating** (G/A/R) against the champions' band limits (1–2Q 0.15/0.20, 3–4Q 0.25/0.30, 5–8Q 0.40/0.50) and the skill test (`comparison_8Q.csv`, `assessment_fixed_limits_8Q.csv`). The champion column reproduces §7.1. **Bold** marks a challenger with a lower mean than the champion.

| Bank | Champion | a0 | a1 | a2 | b1 | b2 | b3 | c | c′ |
| :--- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| First Horizon | 0.242 G | **0.240 G** | 0.302 A | 0.498 R | 0.457 R | 0.389 R | 0.378 R | 0.318 R | 0.251 G |
| Glacier | 0.207 A | **0.205 A** | 0.261 R | 0.219 A | 0.375 R | 0.265 R | **0.204 A** | 0.221 A | **0.201 A** |
| Huntington | 0.334 R | 0.334 R | **0.264 G** | 0.348 R | 0.448 R | 0.348 R | **0.311 R** | 0.386 R | 0.379 R |
| KeyBank | 0.280 R | 0.280 R | 0.301 R | 0.292 R | 0.431 R | 0.344 R | 0.319 R | 0.302 R | 0.295 R |
| M&T | 0.218 G | **0.216 G** | 0.220 G | **0.211 G** | 0.414 R | 0.337 R | 0.285 A | **0.214 G** | **0.215 G** |
| Old National | 0.263 G | 0.263 G | **0.246 G** | 0.436 R | 0.495 R | 0.375 R | 0.313 R | 0.308 R | 0.290 R |
| SouthState | 0.264 G | 0.264 G | **0.250 G** | 0.273 G | 0.518 R | 0.408 R | 0.333 R | 0.297 A | 0.275 A |

**Table CH-4. Worst skill ratio** (challenger h-step MAE ÷ no-change h-step MAE; Red at 1.00 or above, Amber above 0.75).

| Bank | Champion | a0 | a1 | a2 | b1 | b2 | b3 | c | c′ |
| :--- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| First Horizon | 0.71 | 0.70 | 0.73 | 1.43 | 2.05 | 0.79 | 0.84 | 0.73 | 0.72 |
| Glacier | 0.96 | 0.96 | 1.20 | 0.97 | 4.34 | 1.18 | 0.89 | 0.96 | 0.96 |
| Huntington | 0.74 | 0.74 | 0.66 | 0.76 | 2.49 | 0.77 | 0.75 | 0.85 | 0.82 |
| KeyBank | 0.71 | 0.71 | 0.79 | 0.78 | 2.46 | 0.79 | 0.84 | 0.78 | 0.74 |
| M&T | 0.62 | 0.62 | 0.64 | 0.65 | 2.66 | 0.89 | 0.82 | 0.62 | 0.62 |
| Old National | 0.67 | 0.67 | 0.64 | 1.43 | 3.01 | 0.96 | 0.88 | 0.79 | 0.76 |
| SouthState | 0.70 | 0.70 | 0.65 | 0.69 | 3.03 | 1.03 | 0.95 | 0.75 | 0.76 |

**Table CH-5. Asymmetric ECM (a1), h-step MAE by horizon (pp)** (the champions' values are in §7.1).

| Bank | 1Q | 2Q | 3Q | 4Q | 5Q | 6Q | 7Q | 8Q | Rating |
| :--- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| First Horizon | 0.102 | 0.186 | 0.245 | 0.276 | 0.343 | 0.393 | 0.431 | 0.441 | Amber (3–4Q avg 0.261, 5–8Q avg 0.402) |
| Glacier | 0.045 | 0.106 | 0.169 | 0.223 | 0.283 | 0.354 | 0.422 | 0.483 | Red (skill 1.20 at 8Q) |
| Huntington | 0.075 | 0.139 | 0.198 | 0.252 | 0.302 | 0.346 | 0.382 | 0.418 | Green |
| KeyBank | 0.054 | 0.117 | 0.182 | 0.232 | 0.313 | 0.415 | 0.506 | 0.591 | Red (5–8Q max 0.591) |
| M&T | 0.060 | 0.119 | 0.177 | 0.211 | 0.261 | 0.292 | 0.309 | 0.331 | Green |
| Old National | 0.064 | 0.118 | 0.159 | 0.200 | 0.275 | 0.334 | 0.391 | 0.430 | Green |
| SouthState | 0.058 | 0.124 | 0.186 | 0.239 | 0.297 | 0.339 | 0.371 | 0.389 | Green |

**Reading.**
- **a0 confirms the two-step construction is neutral.** a0 is within 0.002 of the champion for every bank, so the differences between a1 or a2 and the champion are due to asymmetry alone.
- **a1 (asymmetric λ) helps where downward stickiness is measurable.**
  - It helps Huntington (−21%, Red → Green), Old National (−6%) and SouthState (−5%).
  - It hurts where it is not: First Horizon (+25%), Glacier (+26%) and KeyBank (+8%). There a small, noisy λ+ makes long-horizon forecasts drift.
  - It is not a peer-wide replacement. It could be a per-bank champion candidate for Huntington, and possibly for Old National and SouthState.
- **a2 is unstable.** With few easing quarters, its λ estimates swing; First Horizon and Old National reach skill ratios of 1.43.
- **b1 to b3 are poor forecasters.**
  - b1 (static levels) has no anchoring to the current rate and is worse than no-change at short horizons for every bank (skill 2.0 to 4.3).
  - b2 and b3 anchor at the origin and pass the FFT change through immediately, so they overshoot during hiking (no lag). b3 is competitive only for Glacier (0.204) and partly for Huntington (0.311, still Red).
- **c and c′ do not help.** When the dummy enters (origins from 2023Q3), it is estimated on 4 to 14 post-break quarters, and the long-run shift and θ trade off (§2). Forecasts worsen for six of seven banks; M&T is the exception (0.214 vs. 0.218).
- **Peer-derived limits give the same picture.** Rating each challenger family with `assess_multi` on its own seven banks (`assessment_peer_limits_8Q.csv`) changes only the labels, because weaker families get looser limits. For example, a1 gives Huntington Amber there because a1's own 1–2Q green limit is 0.10.

![Huntington challengers](<../../model_form/output/Huntington National Bank/challengers_8Q.png>)

*Figure CH-1: Huntington National Bank, many-start-date h-step MAE by horizon, champion vs. challengers vs. no-change. One chart per bank is in `model_form/output/<bank>/challengers_8Q.png`.*

### 3.4 OI-8: the 2025Q1 start date

**Table OI8-1. 5-quarter window MAE from the 2025Q1 start date** (2025Q2 to 2026Q2; the "5Q" single-window column of §7.2) (`oi8_origin_2025Q1.csv`).

| Bank | Champion | a0 | a1 | a2 | b1 | b2 | b3 | c | c′ | No-change |
| :--- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| First Horizon | 0.096 | 0.091 | 0.092 | 0.103 | 0.261 | 0.068 | 0.071 | 0.076 | 0.100 | 0.166 |
| Glacier | 0.116 | 0.111 | 0.068 | 0.040 | 0.378 | 0.033 | 0.042 | 0.072 | 0.114 | 0.090 |
| Huntington | 0.094 | 0.094 | 0.121 | 0.105 | 0.397 | 0.026 | 0.028 | 0.199 | 0.174 | 0.135 |
| KeyBank | 0.121 | 0.121 | 0.098 | 0.194 | 0.348 | 0.082 | 0.102 | 0.076 | 0.151 | 0.197 |
| **M&T** | 0.335 | 0.327 | 0.316 | 0.329 | 0.267 | 0.061 | 0.055 | 0.211 | 0.325 | 0.133 |
| **Old National** | 0.364 | 0.364 | 0.279 | 0.449 | 0.488 | 0.046 | 0.045 | 0.263 | 0.312 | 0.122 |
| **SouthState** | 0.392 | 0.392 | 0.354 | 0.451 | 0.411 | 0.078 | 0.104 | 0.357 | 0.468 | 0.068 |

**Table OI8-2. Where the champions' forecast fall from 2025Q1 comes from:** contributions summed over the 5 steps, pp (`oi8_decomposition_2025Q1.csv`). "Error correction" covers λ and the levels terms (const, trend, y.L1, FFT.L1); "momentum" covers the lagged Δy terms; "ΔFFT terms" covers the D.FFT lags.

| Bank | Δy in 2025Q1 | Error correction | Momentum (lagged Δy) | ΔFFT terms | Forecast change | Actual change |
| :--- | :-: | :-: | :-: | :-: | :-: | :-: |
| First Horizon | −0.328 | −0.232 | +0.058 | −0.153 | −0.327 | −0.257 |
| Glacier | −0.094 | −0.119 | −0.186 | −0.030 | −0.334 | −0.172 |
| Huntington | −0.182 | −0.139 | +0.000 | +0.000 | −0.139 | −0.211 |
| KeyBank | −0.181 | −0.106 | −0.201 | −0.205 | −0.513 | −0.398 |
| **M&T** | −0.268 | −0.089 | −0.437 | −0.083 | −0.609 | −0.251 |
| **Old National** | −0.244 | −0.090 | −0.435 | −0.093 | −0.619 | −0.192 |
| **SouthState** | −0.266 | −0.056 | −0.397 | −0.176 | −0.629 | −0.102 |

![OI-8 forecast paths](<../../model_form/output/oi8_paths_2025Q1.png>)

*Figure OI8-1: Dynamic forecasts from the 2025Q1 start date for M&T, SouthState and Old National, champion vs. challengers, with the actual deposit rate.*

**Conclusion for OI-8: asymmetry does not remove the shared error.**
- a1 trims the window MAE by 6% (M&T), 23% (Old National) and 10% (SouthState). The error is still 0.28 to 0.35 pp, two to five times the no-change error.
- **Root cause:** the shared error is a momentum effect, not an adjustment-speed effect. In 2025Q1 the three deposit rates fell by 0.24 to 0.27 pp in one quarter, after the late-2024 cuts. The champions' lagged-Δy terms (D.y.L1 0.33, 0.31 and 0.79) then extrapolate that fall: −0.40 to −0.44 pp of a −0.61 to −0.63 pp forecast fall. In fact, deposit rates flattened once FFT stopped moving (FFT about 4.3 from 2025Q1 to 2025Q3).
- The error-correction share (−0.06 to −0.09 pp) is too small for a change in λ to matter.
- The models that get this window right (b2, b3: 0.045 to 0.104) are those without momentum terms. They are Red or Amber over all start dates.
- **Remaining remedies,** all outside this issue's scope:
  - asymmetric or damped short-run dynamics (for example, Δy lags interacted with the FFT direction, or a cap on the momentum contribution once FFT is flat);
  - or a combination of an ECM with the anchored cycle beta.
- **OI-8 should stay open,** with the cause recorded as above.

---

## 4. Huntington (issue #4, OI-19): evidence and the scope decision

**Table H-1. Evidence** (`huntington_evidence.csv`).

| Item | Result | Reading |
| :--- | :--- | :--- |
| Baseline cointegration | Fails all four tests at 5% (EG long run p 0.085; Johansen r ≤ 0 13.05; ARDL F 2.78) | Weak |
| Re-specification grid | Passes only EG long run without deterministic terms (t −3.13, p 0.019) | One specification family |
| EG `n` by sample window (`huntington_eg_subsamples.csv`) | Passes in 10 of 15 windows. Every window ending in 2024Q2 or later passes (p 0.005 to 0.031). Windows ending in 2019Q4 fail, and so do 2021Q4 windows starting in 2013 or later (p 0.18 to 0.69). Only 2011Q1–2021Q4 passes (p 0.007) among windows ending by 2021Q4. | Cointegration is identified mainly by the 2022–24 cycle |
| Gregory-Hansen | No rejection under any model (C ADF\* −3.79; C/S −3.96; simulated 5% values −5.14 and −5.46) | A break does not help |
| Asymmetric λ (a1) | λ+ −0.118 vs. λ− −0.459, Wald p 1.4e-07: the strongest asymmetry in the peer set | Deposit rates fall toward equilibrium about four times more slowly than they rise |
| λ by FFT direction (a2) | Easing −0.409 vs. other −0.310, p 0.63 | No evidence |
| 2022Q3 level dummy (c) | δ 0.136 (p 0.031); long-run shift 0.437; θ 0.386 vs. 0.469 | Significant, but forecasts worsen (mean 0.386, Red) |
| Rolling-origin long-run beta (`Beta_Backtesting/output/Huntington National Bank/`) | 0.551 (2024Q2) to 0.465 (2026Q1), falling at 5 of 7 steps; the 2024Q2 origin is 2.06 origin standard errors from the full-sample value | The only one-directional drift in the peer set. It matches the asymmetry: easing-cycle data pull θ down. |
| Champion rating | Red: 3–4Q max 0.307 > 0.30; 5–8Q max 0.559 > 0.50 | |
| Asymmetric ECM (a1) rating | **Green**, mean 0.264, worst skill 0.66 | Fixes the long horizons |
| Champion + D.FFT.L0 (h1, Huntington only) | D.FFT.L0 0.209 (p < 0.001); **Green**, mean 0.240, h-step MAE 0.059 / 0.118 / 0.177 / 0.227 / 0.277 / 0.324 / 0.357 / 0.385 | The best Huntington model tested |

**Why the champion lacks short-run terms.**
- An `EG_LongRun` specification reaches the one-step ECM with only its levels terms. The step-2 output (`ECM param selection results.csv`) holds the long-run regression and the ADF residual lags (`ADF: D.resid.L1`), not ECM short-run terms.
- So no D.FFT or D.y lag was ever offered for screening. §6.3.6's "no short-run terms survive" describes this construction, not a test result.
- This is a pipeline gap. It also affects any other champion from the EG long-run family; none is a champion today.

**Options for the scope decision (decision pending with the user):**

| Option | What it means | Consequences |
| :--- | :--- | :--- |
| **A. Keep in scope, re-specify (recommended)** | Keep Huntington. Replace the champion with the EG `n` ECM plus D.FFT.L0 (h1), or a1 if the validator prefers the asymmetric form. Report with a caveat: cointegration rests on one family and on post-2022 data, and the beta drifts. | Rating Red → Green. Needs either a pipeline change (offer short-run terms to EG long-run specifications) or a documented manual override in §5.5. L15 stays open as a caveat, not a blocker. The peer band limits are re-derived with the new champion (Huntington is one of the seven peers). |
| B. Keep in scope, champion unchanged | Report the current champion as Red, with the caveat | No code change. Huntington stays Red, and the evidence that a better specification exists goes unused. |
| C. Remove from scope | Drop Huntington from the peer set until cointegration is robust | Six banks. The peer limits change. The analysis loses one of the two highest 2022–24 cycle betas (0.448, level with First Horizon). |

**Recommendation: A.**
- **The Red rating is a specification problem.** One missing short-run term and the symmetric adjustment explain it, and both are fixable.
- **The remaining weakness is the long-run evidence,** which no model form fixes. That is a caveat for the validator, not grounds for exclusion. The beta is stable in sign and stays between 0.465 and 0.551 across origins.
- **h1 is preferred to a1 for simplicity:** it is linear, one extra term, and has the lower MAE. A combined h1 + a1 form has not been tested.

---

## 5. Replacement text for `WIP Regional Banking Deposit Beta Analyses.md`

The main session folds these in. Text in [brackets] depends on the Huntington decision. OI-24 and OI-25 are provisional numbers; renumber them if another thread has used them.

### §5.3 Structural Break Testing

> Zivot-Andrews tests (`c`, `t`, `ct`; AIC lags, max 4) are run on the levels of every bank's series (§6, Appendix A.3). Every series rejects a unit root once a 2022 level break is allowed, and FFT shows the same break.
>
> Because a break common to both series need not break their relationship, cointegration is also tested allowing one unknown break: the Gregory-Hansen (1996) tests in four forms, level shift (C), level shift with trend (C/T), regime shift (C/S) and regime shift with trend (C/S/T) (`model_form/gregory_hansen.py`).
>
> - **Method:** breaks are searched over the middle 70% of the sample. The ADF\*, Zt\* and Zα\* statistics are each the minimum over breaks, and ADF lags are chosen by AIC (max 4).
> - **Critical values:** with 62 quarters, finite-sample critical values are simulated (2,000 replications) and govern. They are markedly larger in magnitude than the asymptotic values; for C ADF\* at 5%, −5.14 against −4.61.
> - **Result:** no bank rejects "no cointegration" on ADF\* at 5%. The only 5% rejection on any statistic is Glacier's C/T Zt\* (−5.42 against −5.24, break 2023Q3).
> - **Interpretation:** allowing a break neither strengthens nor overturns the cointegration results of §5.4. The 2022 break in the deposit-rate series mirrors the break in FFT and cancels in the cointegrating relation. Because the null is not rejected, the GH break dates (2021Q3 to 2024Q1) are not interpreted.
> - **Dummy test:** a 2022Q3 level dummy added to each champion ECM is significant at 5% for Glacier, Huntington and M&T. It trades off against θ and worsens out-of-sample forecasts (§7.4), so no champion carries it.

### §6.x.4 Cointegration: one bullet added per bank

The bullets below follow the existing **Baseline** and **Re-specification** bullets. The figures are ADF\* with the 5% simulated critical values: C −5.14, C/T −5.50, C/S −5.46, C/S/T −5.82.

- **6.1.4 First Horizon:** **Gregory-Hansen** (one break, §5.3): no rejection at 5%. ADF\* C −4.05 (2016Q3), C/T −4.53 (2023Q4), C/S −4.50 (2021Q4), C/S/T −4.58 (2023Q4).
- **6.2.4 Glacier:** **Gregory-Hansen:** ADF\* does not reject at 5% under any model: C −3.90 (2024Q1), C/T −5.44 (2023Q3; rejects only against the asymptotic −4.99), C/S −4.09 (2021Q3), C/S/T −5.30 (2024Q1). The C/T Zt\* (−5.42, break 2023Q3) rejects at 5%, the only GH rejection in the peer set.
- **6.3.4 Huntington:** **Gregory-Hansen:** no rejection at 5%. ADF\* C −3.79 (2023Q4), C/T −4.42 (2023Q4), C/S −3.96 (2021Q3), C/S/T −4.37 (2023Q4). EG without deterministic terms fails in every sample window ending in 2019Q4, and in 2021Q4 windows starting in 2013 or later (p 0.18 to 0.69). It passes in every window ending in 2024Q2 or later (`model_form/output/huntington_eg_subsamples.csv`; OI-19).
- **6.4.4 KeyBank:** **Gregory-Hansen:** no rejection at 5%. ADF\* C −3.90 (2024Q1), C/T −4.72 (2024Q1), C/S −4.30 (2021Q3), C/S/T −4.75 (2024Q1).
- **6.5.4 M&T:** **Gregory-Hansen:** no rejection at 5%. ADF\* C −3.94 (2016Q1), C/T −4.49 (2024Q1), C/S −4.25 (2021Q4), C/S/T −4.78 (2023Q3).
- **6.6.4 Old National:** **Gregory-Hansen:** no rejection at 5%. ADF\* C −3.85 (2024Q1), C/T −4.60 (2024Q1), C/S −4.01 (2021Q3), C/S/T −4.53 (2024Q1).
- **6.7.4 SouthState:** **Gregory-Hansen:** no rejection at 5%. ADF\* C −3.82 (2024Q1), C/T −4.41 (2024Q1), C/S −3.87 (2024Q1), C/S/T −4.37 (2024Q1).

[If option A is chosen, §6.3.6 and §6.3.7 also need the re-specified champion's coefficient table and backtest. Those are produced once the pipeline change or override is agreed.]

### §7.4 Benchmarking

> The no-change forecast is the benchmark in both backtests. Seven challengers are scored on the governing many-start-date backtest: the champions' start dates (2016Q1 onward, expanding window), h = 1 to 8, against the champions' band limits and the skill test (`model_form/`). The challengers are:
>
> - an asymmetric ECM with separate λ for positive and negative disequilibrium (a1), and one with λ split by FFT direction (a2), each with a symmetric two-step control (a0);
> - a static OLS beta in levels (b1) and applied to the FFT change (b2), and cycle-specific betas (b3);
> - each champion with a 2022Q3 level dummy (c).
>
> | Bank | Champion | a1 asymmetric λ | a2 λ by FFT direction | b2 static beta | b3 cycle betas | c 2022 dummy |
> | :--- | :-: | :-: | :-: | :-: | :-: | :-: |
> | First Horizon Bank | 0.242 Green | 0.302 Amber | 0.498 Red | 0.389 Red | 0.378 Red | 0.318 Red |
> | Glacier Bank | 0.207 Amber | 0.261 Red | 0.219 Amber | 0.265 Red | 0.204 Amber | 0.221 Amber |
> | Huntington National Bank | 0.334 Red | 0.264 Green | 0.348 Red | 0.348 Red | 0.311 Red | 0.386 Red |
> | KeyBank National Association | 0.280 Red | 0.301 Red | 0.292 Red | 0.344 Red | 0.319 Red | 0.302 Red |
> | Manufacturers and Traders Trust Company | 0.218 Green | 0.220 Green | 0.211 Green | 0.337 Red | 0.285 Amber | 0.214 Green |
> | Old National Bank | 0.263 Green | 0.246 Green | 0.436 Red | 0.375 Red | 0.313 Red | 0.308 Red |
> | SouthState Bank | 0.264 Green | 0.250 Green | 0.273 Green | 0.408 Red | 0.333 Red | 0.297 Amber |
>
> *Mean h-step MAE over 1Q to 8Q (pp) and rating. The static levels beta (b1) is Red for every bank (mean 0.375 to 0.518, worse than no-change at 1Q).*
>
> No challenger beats the champions across the peer group.
>
> - **Asymmetric λ (a1).** Downward adjustment is slower than upward for six of seven banks, significantly so for Huntington (Wald p 1.4e-07) and at the 10% level for Old National and SouthState. a1 improves exactly those three banks and makes Huntington Green. It hurts First Horizon, Glacier and KeyBank, where the asymmetry is not significant.
> - **Static and cycle betas.** They have no lag structure, overshoot during hiking, and are Red or Amber everywhere.
> - **The 2022 dummy.** It is identified from at most 14 post-break quarters and worsens six of seven banks.
> - **The 2025Q1 start date (OI-8).** No ECM challenger removes the shared error for M&T, Old National and SouthState (a1: 0.316, 0.279 and 0.354 against 0.335, 0.364 and 0.392). 63% to 72% of the champions' forecast fall from that date comes from lagged-Δy momentum terms extrapolating the sharp 2025Q1 drop, not from error correction.
>
> Details are in `docs/resolutions/model_form.md`.

### §8 Model Limitations: rows replaced

| # | Limitation | Affected banks | Impact |
| :-: | :--- | :--- | :--- |
| L2 | Stationarity classification depends on the specification. Glacier remains flagged (KPSS I(0) p 0.057). All series reject a unit root once a 2022 level break is allowed, but the break is common to FFT and cancels in the cointegrating relation: Gregory-Hansen finds no break in the relationship (§5.3). | All, esp. Glacier | Medium |
| L6 | Linear, symmetric pass-through. Downward adjustment is slower than upward for six of seven banks (significant for Huntington; 10% for Old National and SouthState). An asymmetric-λ challenger improves those three but not the peer set (§7.4). The 2025Q1 start-date error comes mainly from short-run momentum terms extrapolating the 2025Q1 fall, which asymmetric λ does not address (OI-8). | All, esp. Huntington, Old National, SouthState | High |
| L11 | Cointegration with one unknown break (Gregory-Hansen, four forms) does not reject at 5% for any bank on ADF\* (finite-sample critical values, T = 62). With 62 quarters the test has low power, and two or more breaks are not tested. | All | Low |
| L15 | Huntington cointegration rests on one specification family (EG long run, no deterministic terms) and on post-2022 data: the test fails in every window ending in 2019Q4 and in 2021Q4 windows starting in 2013 or later. GH finds no break. The long-run beta drifts down across origins (0.551 to 0.465). [Option A: the champion is re-specified with a contemporaneous ΔFFT term, Green. Option B: the champion is Red.] (OI-19) | Huntington | High |

### §9.2 Open Issues Log: rows replaced

| ID | Issue | Bank(s) | Priority | Status |
| :-: | :--- | :--- | :-: | :--- |
| OI-8 | Investigate the shared error at the 2025Q1 start date, including Old National's 2025Q2 drop | M&T, Old National, SouthState | Medium | Partially closed: the data artifact is fixed. Asymmetric λ does not remove the error (§7.4). The cause is lagged-Δy momentum extrapolating the 2025Q1 fall (`model_form/output/oi8_decomposition_2025Q1.csv`). Open for asymmetric or damped short-run dynamics. |
| OI-11 | Build benchmark/challenger models (static beta, asymmetric ECM, 2022 regime dummy) | All | High | Closed: seven challengers scored on the many-start-date backtest (§7.4, `model_form/`). None replaces the champions peer-wide. Asymmetric λ is a per-bank candidate for Huntington, Old National and SouthState. ([#2](https://github.com/Panda5130/Deposit-Beta/issues/2)) |
| OI-19 | Huntington cointegration rests on a single specification family; assess robustness and whether Huntington stays in scope | Huntington | High | [Decision pending. Evidence in `docs/resolutions/model_form.md` §4. Recommended: keep in scope with a caveat and re-specify the champion (contemporaneous ΔFFT term: Green, mean h-step MAE 0.240).] ([#4](https://github.com/Panda5130/Deposit-Beta/issues/4)) |
| OI-20 | Zivot-Andrews rejects a unit root with a 2022 level break for all banks and for FFT; test cointegration allowing a break (Gregory-Hansen) | All | Medium | Closed: Gregory-Hansen (C, C/T, C/S, C/S/T) finds no break-cointegration at 5% for any bank on ADF\* (T = 62 simulated critical values; one Zt\* rejection, Glacier C/T). A 2022 level dummy in the ECM does not improve forecasts (§5.3, §7.4). ([#5](https://github.com/Panda5130/Deposit-Beta/issues/5)) |
| OI-24 (new) | EG long-run specifications enter the one-step ECM with no short-run terms: the step-2 output carries only ADF residual lags, so D.FFT and D.y lags are never screened | Huntington (champion), any EG long-run specification | High | Open: Huntington's champion gains Green with D.FFT.L0 |
| OI-25 (new) | Damp or make asymmetric the short-run (lagged Δy) dynamics so a sharp one-quarter fall is not extrapolated once FFT is flat | M&T, Old National, SouthState | Medium | Open (from OI-8) |

---

## 6. Draft comments for the GitHub issues

Drafts only. Post them only after the user approves.

### Issue #5 (OI-20)

> **Gregory-Hansen results (model_form branch).** All 7 banks were tested, 2011Q1–2026Q2, under level shift (C), level shift with trend (C/T), regime shift (C/S) and regime shift with trend (C/S/T). The statistics are ADF\*, Zt\* and Zα\*, with breaks searched over the middle 70% of the sample.
>
> - **Critical values:** 62 quarters is short, so finite-sample critical values were simulated (2,000 reps). They are much larger in magnitude than the asymptotic ones; for C ADF\* at 5%, −5.14 vs. −4.61.
> - **Result:** no bank rejects "no cointegration" on ADF\* at 5%. The ADF\* range is −3.79 to −4.05 (C), −4.41 to −5.44 (C/T), −3.87 to −4.50 (C/S) and −4.37 to −5.30 (C/S/T). The single 5% rejection on any statistic is Glacier's C/T Zt\* (−5.42 vs. −5.24).
> - **Break dates:** the minimising breaks are at 2023Q3–2024Q1 (C, C/T) or 2021Q3–Q4 (C/S), not the 2022Q2–Q4 Zivot-Andrews breaks. Since the null is not rejected, they are not interpreted.
> - **Reading:** the 2022 break in each deposit-rate series mirrors FFT's and cancels in the cointegrating relation. Allowing a break neither strengthens nor overturns the EG, Johansen and ARDL results.
> - **Dummy in the ECM:** a 2022Q3 level dummy added to each champion ECM is significant at 5% for Glacier, Huntington and M&T. It trades off against θ (θ falls by 0.06–0.17) and worsens the many-start-date backtest for 6 of 7 banks, so no champion should carry it.
>
> Outputs: `model_form/output/gregory_hansen*.csv`, `gregory_hansen_adf_by_break.png`, `dummy_ecm.csv`. Write-up and replacement text for §5.3, §6.x.4, L2 and L11: `docs/resolutions/model_form.md`. Proposed to close once the doc is updated.

### Issue #2 (OI-11)

> **Challengers scored (model_form branch).** Each challenger subclasses `MAEBacktest` and is scored on the champions' identical start dates (2016Q1 onward, expanding window, h = 1–8) against the champions' band limits and the skill test. The re-run champion matches `backtest_multiorigin_8Q.csv` exactly.
>
> Mean h-step MAE, champion → challenger:
>
> | | FH | Glacier | Huntington | KeyBank | M&T | Old National | SouthState |
> | :-- | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
> | Champion | 0.242 G | 0.207 A | 0.334 R | 0.280 R | 0.218 G | 0.263 G | 0.264 G |
> | Asymmetric λ (sign of ect) | 0.302 A | 0.261 R | **0.264 G** | 0.301 R | 0.220 G | **0.246 G** | **0.250 G** |
> | λ by FFT direction | 0.498 R | 0.219 A | 0.348 R | 0.292 R | 0.211 G | 0.436 R | 0.273 G |
> | Static beta (anchored) | 0.389 R | 0.265 R | 0.348 R | 0.344 R | 0.337 R | 0.375 R | 0.408 R |
> | Cycle betas | 0.378 R | 0.204 A | 0.311 R | 0.319 R | 0.285 A | 0.313 R | 0.333 R |
> | 2022Q3 dummy | 0.318 R | 0.221 A | 0.386 R | 0.302 R | 0.214 G | 0.308 R | 0.297 A |
>
> - **Asymmetric λ:** downward adjustment is slower than upward for 6 of 7 banks. The difference is significant for Huntington (λ+ −0.118 vs. λ− −0.459, Wald p 1.4e-07), and at 10% for Old National and SouthState. a1 helps exactly those three and hurts the others. It is a per-bank candidate, not a peer-wide replacement.
> - **OI-8: asymmetry does not remove the 2025Q1 start-date error.** The window MAE goes 0.335 → 0.316 (M&T), 0.364 → 0.279 (Old National) and 0.392 → 0.354 (SouthState). 63–72% of the champions' forecast fall from 2025Q1 comes from the lagged-Δy terms extrapolating the sharp 2025Q1 drop, not from error correction. Proposed follow-up: damped or asymmetric short-run dynamics.
>
> Full tables, the cycle betas and the replacement text for §7.4, L6, OI-8 and OI-11 are in `docs/resolutions/model_form.md`. Proposed to close OI-11 once §7.4 is updated, with OI-8 kept open for the momentum issue.

### Issue #4 (OI-19)

> **Huntington evidence (model_form branch).**
>
> - **Cointegration is fragile.** EG without deterministic terms passes in every sample window ending in 2024Q2 or later. It fails in windows ending in 2019Q4, and in 2021Q4 windows starting in 2013 or later (p 0.18–0.69). Gregory-Hansen does not reject under any break form. The long-run beta drifts from 0.551 to 0.465 across origins.
> - **The Red rating is a specification problem.**
>   - The EG long-run specification reaches the one-step ECM with no short-run terms, so D.FFT.L0 was never screened. Adding it gives a coefficient of 0.209 (p < 0.001) and a **Green** rating, with mean h-step MAE 0.240 against 0.334.
>   - Huntington also has the strongest adjustment asymmetry in the peer set (λ+ −0.118 vs. λ− −0.459, p 1.4e-07). The asymmetric ECM is **Green** too (0.264).
>   - The 2022Q3 dummy does not help (Red, 0.386).
> - **Options:**
>   - (A) keep in scope with a caveat and a re-specified champion (recommended);
>   - (B) keep in scope with the current champion, Red;
>   - (C) remove from scope.
>
> [Decision: …]. Write-up: `docs/resolutions/model_form.md` §4.

---

## 7. Outputs

| File (`model_form/output/`) | Content |
| :--- | :--- |
| `gregory_hansen.csv`, `gregory_hansen_summary.csv`, `gregory_hansen_cv_sim.csv`, `gregory_hansen_adf_by_break.png` | GH statistics, breaks, critical values; comparison with ZA breaks |
| `errors/<code>.csv` | Per-origin forecasts and errors (h, origin, quarter, actual, predicted, err, no-change err) for every model |
| `multiorigin_8Q.csv` | h-step MAE per bank and model, champion re-run included |
| `assessment_fixed_limits_8Q.csv`, `assessment_peer_limits_8Q.csv`, `comparison_8Q.csv` | Ratings against the champions' limits and against each family's own peer limits; comparison with the champion |
| `fit_forms.csv` | Form used at each origin (fallbacks) |
| `asymmetry_tests.csv`, `dummy_ecm.csv`, `cycle_betas.csv` | Full-sample asymmetry tests, dummy ECM, cycle betas |
| `oi8_origin_2025Q1.csv`, `oi8_decomposition_2025Q1.csv`, `oi8_paths_2025Q1.png` | OI-8 window errors, champion forecast decomposition, forecast paths |
| `huntington_eg_subsamples.csv`, `huntington_h1_multiorigin_8Q.csv`, `huntington_evidence.csv` | Huntington sub-sample EG tests, D.FFT.L0 variant backtest, evidence summary |
| `<bank>/challengers_8Q.png` | h-step MAE by horizon, champion vs. challengers vs. no-change |
