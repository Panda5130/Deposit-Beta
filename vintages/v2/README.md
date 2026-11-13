# Data vintage v2: supplementary deposit transfers (issue #20)

Status: **pending owner approval** (built 2026-11-13). Phase 2 and any doc edits wait on that approval.

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
- Pre-change snapshot: `audit/2026-11-13_pre_transfer_fix/` (SHA-256 manifest).

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
