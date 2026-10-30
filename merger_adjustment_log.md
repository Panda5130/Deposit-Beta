# Merger Adjustment Log

## Methodology & Model Configuration
- Mode A: Material mergers (>= 1.0% deposit share acquired) mathematically adjusted on both interest expense and average deposits.
- Mode B: Sub-material mergers (< 1.0% deposit share) flagged only for exclusion in downstream pricing models.

## Execution Statistics
- Total Records Evaluated: 434
- Mode A Adjustments applied: 6
- Mode B Adjustments flagged: 2

## Validations Performed
- Pro forma deposit rate formula verified: 100.0 * ie_ann_pf / dep_avg_pf matches rate_pf with < 1e-12 error.
- Unique Key constraint verified: No duplicate cert_number + quarter pairs.
- Integrity constraint verified: Baseline source columns completely unchanged.
