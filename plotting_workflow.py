"""Predicted vs. actual plots for every bank and every surviving ECM model.

Usage (all arguments optional; defaults point at the files in this folder):
    python plotting_workflow.py [--banks NAME ...] [--estimates FILE] [--dependents FILE]
        [--independents FILE] [--y COLUMN] [--x COLUMN] [--group-column COLUMN] [--out-dir DIR]

Runs bank_plots.plot_bank for each bank in "ECM estimation results.csv" (or the --banks
given), reading the input files once. Output layout:

    <out-dir>/                      default: "Actuals vs Predictions" in this folder
        <bank_name>/
            {test_name}+{IC/selected lag}+{trend type}.png   one per surviving model
            _gaps.txt                                         only if a model could not be plotted

A bank with no estimates or no source data is logged as a warning and skipped; a model
that cannot be plotted is logged and listed in that bank's _gaps.txt. The other banks
and models still run. Exit code: 0 when everything was plotted, 2 when there were gaps or
skipped banks, 1 when the inputs could not be read.
"""

import argparse
import logging
import sys
from pathlib import Path

import bank_plots as bp

log = logging.getLogger("plotting_workflow")
GAPS_NAME = "_gaps.txt"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Predicted vs. actual ECM plots for every bank.")
    parser.add_argument("--banks", nargs="+", help="banks to plot (default: every bank in the estimates)")
    parser.add_argument("--estimates", default=bp.DEFAULTS["estimates"])
    parser.add_argument("--dependents", default=bp.DEFAULTS["dependents"])
    parser.add_argument("--independents", default=bp.DEFAULTS["independents"])
    parser.add_argument("--y", default=bp.DEFAULTS["y"], help="dependent column")
    parser.add_argument("--x", default=bp.DEFAULTS["x"], help="regressor column")
    parser.add_argument("--group-column", default=bp.DEFAULTS["group_column"])
    parser.add_argument("--out-dir", default=bp.DEFAULTS["out_dir"], help="parent folder for the bank folders")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)

    try:
        estimates = bp.load_estimates(args.estimates, args.group_column)
        source = bp.load_source(args.dependents, args.independents)
    except (FileNotFoundError, ValueError) as e:
        log.error("%s", e)
        return 1

    banks = args.banks or list(estimates[args.group_column].astype(str).str.strip().drop_duplicates())
    out_dir = Path(args.out_dir)
    log.info("plotting %d bank(s) into %s", len(banks), out_dir)
    total, problems = 0, 0
    for i, bank in enumerate(banks, start=1):
        try:
            written, gaps = bp.plot_bank(bank, estimates, source, out_dir, args.y, args.x, args.group_column)
        except ValueError as e:
            log.warning("[%d/%d] %s skipped: %s", i, len(banks), bank, e)
            problems += 1
            continue
        gaps_file = out_dir / bank / GAPS_NAME
        if gaps:
            for label, reason in gaps:
                log.warning("%s / %s not plotted: %s", bank, label, reason)
            gaps_file.write_text("".join(f"{label}: {reason}\n" for label, reason in gaps), encoding="utf-8")
            problems += len(gaps)
        elif gaps_file.exists():
            gaps_file.unlink()  # stale note from an earlier run
        log.info("[%d/%d] %s: %d plot(s), %d gap(s)", i, len(banks), bank, len(written), len(gaps))
        total += len(written)

    log.info("done: %d plot(s) in %s, %d warning(s)", total, out_dir, problems)
    return 2 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
