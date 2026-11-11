# Frozen MAE-stability reference (issue #8)

`reference_v<k>.csv/.json` are written by `python MAE_Backtesting/run_backtest.py --freeze-reference
--reference-trigger {initial,new-champion,data-restatement,annual-review}` and are immutable: a new
freeze adds the next version, the CSV hash is stored in the JSON and checked on load. `approved_by` is
empty until the model owner edits it into the JSON; only then does the reference become the default limits
for MAE stability (`--limits auto`). `--limits peer` keeps the peer-derived limits; `--limits-from FILE`
forces one reference. No version is frozen yet.
