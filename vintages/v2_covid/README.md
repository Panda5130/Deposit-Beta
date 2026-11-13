# v2_covid: COVID liquidity-injection dummy test on data vintage v2

Status: **pending owner approval** (built 2026-11-13). The doc update waits on that approval.

## Specification
`covid_liq` = 1 for 2020Q2-2021Q4 (7 quarters), else 0. Short-run only: an exogenous term in the d(rate)
equation (`bank_plots.COVID`, `covid_series`, `sr_term`). The long-run relation and the cointegration
screen are untouched. It is a candidate short-run regressor, pruned at p >= 0.05 like the lags
(symmetric: one-term p-value; asymmetric variants: one-term Wald, not split into +/-). It depends only on the
calendar quarter, so backtests know it in advance (no look-ahead), and it is 0 in every projection and
scenario (`Projection.project` refuses a projection that reaches the window).

## Output isolation
`bank_plots.OUTPUT_VINTAGE = "v2_covid"` is the one output-root setting next to `DATA_VINTAGE`. Every writer
(estimation, asymmetric variants, pruning log, backtests, beta, realized beta, scenarios and figures, model_form)
writes under `vintages/v2_covid/` at its usual relative path; reads fall back per file to `vintages/v2/`, then
the v1 files in the repo root (`bank_plots.vfile`). Verify check `no_outputs_outside_vintages`.

## Run order (`run_scripts/`)
1. `python "ECM estimation.py" --covid` and `python "ECM asymmetric variants.py" --covid` (all 78 surviving specs, 7 banks)
2. `python vintages/v2_covid/run_scripts/seed_cache.py` (copies the v1/v2 backtest caches; unchanged specs are reused)
3. `python MAE_Backtesting/run_backtest.py --bank-name All`
4. `python Beta_Backtesting/run_beta_backtest.py --bank-name All --realized`
5. `python projection/run_scenarios.py`, `python model_form/run_model_form.py`
6. `python vintages/v2_covid/run_scripts/make_decision.py` -> `covid_dummy_decision.csv`

"Without the dummy" is the v2 result (unchanged). The with-dummy estimates of specs that keep no dummy equal v2
exactly for the symmetric models; three asymmetric specs prune to a different pair set once the dummy is a
candidate (general-to-specific order), none of them a champion.

## Inclusion rule (all three)
(1) the dummy survives pruning in the selected champion; (2) the champion's OOS mean MAE is no worse than
without it beyond one `oos_se`; (3) the theta-stability rating does not worsen (Green < Amber < Red).
See `covid_dummy_decision.csv`.
