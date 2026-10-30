"""Rolling-origin MAE backtest bar charts for one bank or all banks.

Usage (all arguments optional; defaults point at the files in the project folder):
    python MAE_Backtesting/run_backtest.py [--horizon 8Q] [--bank-name NAME|All]
        [--model "test_name | IC/selected lag | trend type"] [--min-train 20]
        [--summary FILE] [--estimates FILE] [--dependents FILE] [--independents FILE]
        [--y COLUMN] [--x COLUMN] [--group-column COLUMN] [--out-dir DIR]

--bank-name All (the default) runs every bank in "estimation result summary.csv". --model
picks the specification for a single bank; without it the bank's lowest in-sample MAE model
is used (ties broken EG > ARDL > Johansen). See backtest.py for the method. Output layout:

    <out-dir>/                          default: MAE_Backtesting/output
        <bank_name>/
            MAE_backtest_<N>Q.png       one bar per horizon 1Q..NQ
            MAE_backtest_<N>Q.csv       horizon, origin, forecast window, n_obs, MAE
        backtest_summary_<N>Q.csv       every bank's rows (only with --bank-name All)

A bank that cannot be backtested is logged and skipped; the others still run. Exit code: 0
when every bank ran, 2 when some were skipped, 1 when the arguments or inputs were invalid.
"""

import argparse
import logging
import re
import sys
from pathlib import Path

import pandas as pd

import backtest as bt

log = logging.getLogger("mae_backtest")
SUMMARY_DEFAULT = bt.ROOT / "estimation result summary.csv"


def parse_horizon(text):
    m = re.fullmatch(r"\s*(\d+)\s*Q\s*", str(text), re.IGNORECASE)
    if not m or int(m[1]) < 1:
        raise ValueError(f"horizon must look like '8Q', got {text!r}")
    return int(m[1])


def resolve_banks(name, summary, group_column):
    banks = list(summary[group_column].astype(str).str.strip().drop_duplicates())
    if name.strip().lower() == "all":
        return banks
    match = [b for b in banks if b.lower() == name.strip().lower()]
    if not match:
        raise ValueError(f"unknown bank {name!r}; available: {'; '.join(banks)}")
    return match


def main(argv=None):
    parser = argparse.ArgumentParser(description="Rolling-origin MAE backtest bar charts.")
    parser.add_argument("--horizon", default="8Q", help="backtest horizon in quarters, e.g. 8Q")
    parser.add_argument("--bank-name", default="All", help='a bank name, or "All"')
    parser.add_argument("--model", default=None,
                        help='"test_name | IC/selected lag | trend type"; single bank only '
                             "(default: lowest in-sample MAE)")
    parser.add_argument("--min-train", type=int, default=20, help="quarters required before the first origin")
    parser.add_argument("--summary", default=SUMMARY_DEFAULT)
    parser.add_argument("--estimates", default=bt.bp.DEFAULTS["estimates"])
    parser.add_argument("--dependents", default=bt.bp.DEFAULTS["dependents"])
    parser.add_argument("--independents", default=bt.bp.DEFAULTS["independents"])
    parser.add_argument("--y", default=bt.bp.DEFAULTS["y"], help="dependent column")
    parser.add_argument("--x", default=bt.bp.DEFAULTS["x"], help="regressor column")
    parser.add_argument("--group-column", default=bt.bp.DEFAULTS["group_column"])
    parser.add_argument("--out-dir", default=bt.HERE / "output")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)

    try:
        horizon = parse_horizon(args.horizon)
        summary = bt.bp.read_csv(args.summary)
        missing = [c for c in [args.group_column] + bt.SPEC_KEYS + ["MAE"] if c not in summary.columns]
        if missing:
            raise ValueError(f"{args.summary} is missing columns: {', '.join(missing)}")
        banks = resolve_banks(args.bank_name, summary, args.group_column)
        if args.model is not None and len(banks) > 1:
            raise ValueError("--model applies to one bank; give --bank-name too")
        estimates = bt.bp.load_estimates(args.estimates, args.group_column)
        source = bt.bp.load_source(args.dependents, args.independents)
    except (FileNotFoundError, ValueError) as e:
        log.error("%s", e)
        return 1

    out_dir = Path(args.out_dir)
    stem = f"MAE_backtest_{horizon}Q"
    log.info("backtesting %d bank(s) over %dQ into %s", len(banks), horizon, out_dir)
    results, skipped = [], 0
    for i, bank in enumerate(banks, start=1):
        try:
            model = bt.select_model(summary, bank, args.model, args.group_column)
            rows = bt.bank_rows(estimates, bank, args.group_column)
            spec_rows = rows[bt.model_mask(rows, model)]
            if spec_rows.empty:
                raise ValueError(f"model {' | '.join(model)} has no coefficients in the estimates")
            data = bt.bp.bank_data(source, args.group_column, bank, args.y, args.x)
            result = bt.MAEBacktest(bank, model, horizon, data, spec_rows, args.y, args.x, args.min_train).run()
        except Exception as e:
            log.warning("[%d/%d] %s skipped: %s", i, len(banks), bank, e)
            skipped += 1
            continue
        bank_dir = out_dir / bt.bp.INVALID_CHARS_RE.sub("-", bank)
        bank_dir.mkdir(parents=True, exist_ok=True)
        result.labelled().to_csv(bank_dir / f"{stem}.csv", index=False)
        bt.plot_mae_bars(result, bank_dir / f"{stem}.png", args.y)
        log.info("[%d/%d] %s: %s; MAE %s", i, len(banks), bank, " | ".join(model),
                 ", ".join(f"{r.horizon_q}={r.mae:.4f}" for r in result.table.itertuples()))
        results.append(result)

    if results and args.bank_name.strip().lower() == "all":
        pd.concat([r.labelled() for r in results]).to_csv(out_dir / f"backtest_summary_{horizon}Q.csv", index=False)
    log.info("done: %d chart(s) in %s, %d bank(s) skipped", len(results), out_dir, skipped)
    return 2 if skipped else 0


if __name__ == "__main__":
    sys.exit(main())
