# Data vintage v2: supplementary deposit transfers (issue #20)

Status: **amended 2026-11-13, pending owner approval of the amendment** (see "Amendment 1"). Doc edits wait on that approval.

## What changed
FDIC `/history` logs charter mergers only (codes 2xx). v2 adds three deposit transfers found by a NIC
Transformations cross-check, recorded in `data_build/raw/supplementary_transfer_events.csv`, with
`transfer_share` checked against FDIC financials:

| Predecessor | Survivor | Effective | Share | % of survivor | Mode |
|---|---|---|---|---|---|
| Wilmington Trust Co (680) | M&T (588) | 2011-05-16 | 0.92014 | 13.08 | A |
| Voyager Bank (32173) | Anchor (8868), then Old National (3832) | 2015-04-15 | 1.0 | 23.68 (of Anchor) | A, depth 1 |
| SouthBank FSB (33848) | SouthState (33555) | 2015-07-25 | 1.0 | 0.54 | B (flag only) |

## Files
- Data, repo root: `consolidated_fdic_quarterly_financials_{2008,2011}-2026[_merger_adjusted]_v2.csv`,
  `merger_events_used_v2.csv` (with a `source` and a `transfer_share` column), `merger_adjustment_log_v2.md`.
- This folder: the screen, selection, estimation (unpruned and det-pruned), asymmetric variants and pruning log.
  M&T and Old National rows were re-run on v2 data; the other 5 banks' rows were carried over unchanged
  (their `rate_pf_clean` is identical, max abs diff 0).
- Downstream outputs (backtests, beta, realized beta, selection comparison, scenarios, model_form), at the same
  relative paths as the v1 outputs. Only files that differ from v1 are stored here. Glacier's in-sample (`MAE_Backtesting/output`,
  `Beta_Backtesting/output`) files differ only because the v1 in-sample run predates deterministic pruning;
  its data did not change.
- `run_scripts/`: the exact rerun (`run_upstream.py v2`, `run_downstream.py`, `harvest.py`) and logs. The
  rerun ran in a scratch copy of the repo, so no v1 output was overwritten. As a check, `run_upstream.py v1`
  reproduced the original v1 files for both banks exactly.
- Pre-change snapshot: `audit/2026-11-13_pre_transfer_fix.manifest.csv` (path, SHA-256, baseline commit 057d5dd; the files are in git history).

## Pipeline switch
`bank_plots.DATA_VINTAGE = "v2"` points every reader (`CANDIDATE_FILES`, `DEFAULTS["dependents"]`) and the
`ECM workflow.py` / `ECM estimation.py` / `ECM asymmetric variants.py` default inputs and outputs at v2.
Set it to `"v1"` to go back to the original files.
The backtest, beta, scenario and model_form scripts still write to their usual `output/` folders. Re-running
them in the repo replaces those v1 outputs (the copies in `audit/` remain).

## Result (M&T, Old National)
- Rate change, 2011-2026 sample: M&T max |diff| 0.0012 pp (2011Q1-Q2); Old National 0.0011 pp (2011Q1-2015Q2).
- The screen pass set, the selections and the pruning decisions are unchanged. Champions are unchanged, and
  their metrics move only in the 4th decimal.

## Amendment 1 (2026-11-13): four more NIC-found transfers
The real NIC Attributes cross-check (`tools/nic_crosscheck.py`) found four deposit transfers that /history does not log.
Added to `data_build/raw/supplementary_transfer_events.csv` (owner approved), all Mode A:

| Predecessor | Survivor | Effective | Share | % of survivor | Flows into |
|---|---|---|---|---|---|
| Wilmington Trust NA (33911) | M&T (588) | 2011-05-16 | 0.94193 (partial) | 3.47 | M&T |
| Prudential Bank & Trust (32957) | TCF (28330) | 2012-06-02 | 0.97035 (partial) | 12.78 | Huntington |
| CenterBank of Jacksonville (35542) | FirstAtlantic (35200) | 2011-12-17 | 1.0 | 78.7 | SouthState |
| CenterState Bank Mid Florida (57334) | CenterState NA (32699) | 2007-11-30 | 1.0 | 34.5 | SouthState |

Rate change vs the previous v2 (2011 sample, pp): M&T max 0.0023 (2011Q1-Q2); Huntington 0.0026 (2011Q1-2012Q2);
SouthState 0.0052 (2011Q1-Q4). First Horizon, Glacier, KeyBank and Old National: max abs diff 0. The full chain was
rerun for M&T, Huntington and SouthState (`run_scripts/amend_v2.py`: staged in `vintages/v2_stage`, then harvested here),
with the other banks' candidate rows carried over. No champion changed. Because Huntington and SouthState now differ
from v1, this folder holds their outputs too. Files of unaffected banks also appear where the v1 in-sample run
predates deterministic pruning.
