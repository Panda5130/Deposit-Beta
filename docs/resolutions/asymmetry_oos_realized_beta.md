# Asymmetric variants, out-of-sample default selection, realized-beta backtest: results (for review)

Generated after rerunning section E of the plan. The WIP doc is not edited; nothing is pushed. Before = in-sample champion over the original models (the old default, now `--select in-sample`); after = out-of-sample pick over the original and asymmetric candidates (the new default). MAE = many-start-date rating from 2016Q1; theta stability = option C, rated from 2020Q1 (worst of theta+/theta- for split models). Realized beta (start dates from 2016Q1, h = 1-8, |dFFT| >= 0.25 pp) is descriptive: actual vs model-implied beta per horizon with theta on a second axis, in Beta_Backtesting/output[/out_of_sample]/realized_beta_all_banks_8Q.png; it is not rated.

## Champions before and after

| Bank | | Champion | n params | theta | lambda | MAE | theta stability |
| :-- | :-- | :-- | --: | :-- | :-- | :-- | :-- |
| First Horizon | before (in-sample) | ARDL bounds F (ARDL(3,4), case 4) | AIC / ARDL(3,4) | ct - case 4 (unrestricted constant, restricted trend) | 9 | 0.517 | -0.375 | Red | Green |
| First Horizon | after (out-of-sample) | Johansen VECM (rank 1) | BIC / k_ar_diff=1 | det_order -1 (none) | 3 | 0.477 | -0.228 | Green | Green |
| M&T | before (in-sample) | ARDL bounds F (ARDL(2,1), case 4) | AIC / ARDL(2,1) | ct - case 4 (unrestricted constant, restricted trend) | 6 | 0.432 | -0.184 | Green | Red |
| M&T | after (out-of-sample) | EG_LongRun | AIC / ADF lag=1, ECM lag=4 | n (none) | 3 | 0.402 | -0.195 | Green | Red |
| Glacier | before (in-sample) | ARDL bounds F (ARDL(3,1), case 4) | BIC / ARDL(3,1) | ct - case 4 (unrestricted constant, restricted trend) | 7 | 0.346 | -0.112 | Amber | Red |
| Glacier | after (out-of-sample) | Johansen VECM (rank 1) | BIC / k_ar_diff=1 | det_order 1 (linear trend) | 5 | 0.277 | -0.158 | Red | Red |
| SouthState | before (in-sample) | ARDL bounds F (ARDL(4,3), case 1) | AIC / ARDL(4,3) | n - case 1 (no deterministic terms) | 8 | 0.443 | -0.082 | Green | Green |
| SouthState | after (out-of-sample) | ARDL bounds F (ARDL(3,2), case 4) | BIC / ARDL(3,2) | ct - case 4 (unrestricted constant, restricted trend) | 8 | 0.524 | -0.165 | Green | Red |
| KeyBank | before (in-sample) | EG_LongRun | BIC / ADF lag=1, ECM lag=3 | n (none) | 7 | 0.398 | -0.110 | Red | Green |
| KeyBank | after (out-of-sample) | ARDL bounds F (ARDL(2,1), case 1) | asymmetric | BIC / ARDL(2,1) | n - case 1 (no deterministic terms) | 7 | 0.402 | -0.089 (+) / -0.331 (-) | Green | Red |
| Huntington | before (in-sample) | EG_LongRun | AIC / ADF lag=1, ECM lag=3 | n (none) | 8 | 0.463 | -0.066 | Green | Green |
| Huntington | after (out-of-sample) | EG_LongRun | AIC / ADF lag=1, ECM lag=3 | n (none) | 8 | 0.463 | -0.066 | Green | Green |
| Old National | before (in-sample) | EG_LongRun | BIC / ADF lag=1, ECM lag=3 | n (none) | 8 | 0.394 | -0.086 | Green | Green |
| Old National | after (out-of-sample) | Johansen VECM (rank 1) | fixed / k_ar_diff=1 | det_order -1 (none) | 4 | 0.419 | -0.135 | Green | Amber |

## Wald tests on each after-champion

| Bank | lambda+ = lambda- | theta+ = theta- | sum gamma dFFT | sum phi dy | form | pairs kept |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| First Horizon | (champion is symmetric) | | | | | |
| M&T | (champion is symmetric) | | | | | |
| Glacier | (champion is symmetric) | | | | | |
| SouthState | (champion is symmetric) | | | | | |
| KeyBank | F=11.77, p=0.001: asymmetric kept | F=2.21, p=0.143: collapsed to symmetric | F=39.35, p=0.000: asymmetric at 5% | F=0.20, p=0.654: not rejected at 5% | lambda split | D.rate_pf_clean.L1 D.FFT.L0 |
| Huntington | (champion is symmetric) | | | | | |
| Old National | (champion is symmetric) | | | | | |

## Asymmetries surviving pruning, all variants

| Bank | variants | lambda split kept | theta split kept | dFFT pairs kept (mean) | dy pairs kept (mean) | sum gamma asymmetric at 5% | sum phi asymmetric at 5% | TAR cycled |
| :-- | --: | --: | --: | --: | --: | --: | --: | --: |
| First Horizon | 23 | 14 | 5 | 2.3 | 1.3 | 5 | 9 | 2 |
| Glacier | 4 | 2 | 2 | 1.0 | 1.5 | 4 | 2 | 2 |
| Huntington | 3 | 3 | 0 | 2.0 | 3.0 | 3 | 3 | 0 |
| KeyBank | 17 | 17 | 6 | 1.5 | 1.8 | 8 | 7 | 12 |
| M&T | 22 | 12 | 13 | 1.1 | 1.0 | 15 | 6 | 2 |
| Old National | 2 | 1 | 0 | 2.0 | 2.0 | 0 | 1 | 0 |
| SouthState | 7 | 5 | 5 | 1.7 | 2.1 | 5 | 7 | 5 |

All banks: 78 variants; lambda split kept in 54, theta split kept in 31; Wald lambda+ = lambda- rejected at 5% in 54, not rejected in 18, regime too small in 6; theta+ = theta- rejected in 31 of 78.

## Candidates

| bank_name                               |   candidates |   asymmetric |   admissible |   admissible asymmetric |
|:----------------------------------------|-------------:|-------------:|-------------:|------------------------:|
| First Horizon Bank                      |           46 |           23 |           43 |                      20 |
| Glacier Bank                            |            8 |            4 |            8 |                       4 |
| Huntington National Bank                |            6 |            3 |            6 |                       3 |
| KeyBank National Association            |           34 |           17 |           32 |                      15 |
| Manufacturers and Traders Trust Company |           44 |           22 |           38 |                      16 |
| Old National Bank                       |            4 |            2 |            4 |                       2 |
| SouthState Bank                         |           14 |            7 |            9 |                       2 |

## Caveats

- 23 of 78 TAR fits ended in a 2-state indicator cycle; the lowest-SSR pass is kept and the form says so (`ECM asymmetric tests.csv`).
- Several admissible asymmetric variants are explosive out of sample (best asymmetric mean h-step MAE: Old National 76.6 pp, SouthState 4.57, M&T 0.76). The many-start-date score screens them out, but they are fragile.
- Only KeyBank's new champion is asymmetric. Huntington's best asymmetric score (0.204) beats its symmetric champion (0.221), but the one-SE parsimony rule keeps the 8-parameter symmetric model.
- `--select in-sample` reproduces the previous champions and MAE and theta-stability ratings; the in-sample MAE files differ only by CSV float round-trip noise (max 1.7e-16) and were left as committed.
