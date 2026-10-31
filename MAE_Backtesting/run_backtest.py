"""Rolling-origin MAE backtest bar charts for one bank or all banks.

Usage (all arguments optional; defaults point at the files in the project folder):
    python MAE_Backtesting/run_backtest.py [--horizon 8Q] [--bank-name NAME|All]
        [--model "test_name | IC/selected lag | trend type"] [--select in-sample|out-of-sample]
        [--first-origin 2016Q1] [--no-cache] [--min-train 20] [--summary FILE] [--estimates FILE] [--dependents FILE] [--independents FILE]
        [--y COLUMN] [--x COLUMN] [--group-column COLUMN] [--out-dir DIR]

--bank-name All (the default) runs every bank in "estimation result summary.csv". --model
picks the specification for a single bank; without it the bank's lowest in-sample MAE model
is used (ties broken EG > ARDL > Johansen). See backtest.py for the method.

--select out-of-sample (optional; the default stays in-sample) backtests instead each bank's
out-of-sample pick (backtest.select_model_oos): admissible models ranked by mean many-origin
h-step MAE from --first-origin (default 2016Q1 in this mode), most parsimonious within one SE
of the best. It writes to <out-dir> = MAE_Backtesting/output/out_of_sample by default, caches
errors per model (cache/<bank>__<model id>.csv), and adds selection_oos_scores_<N>Q.csv: every
model's lambda, theta, admissibility, score, SE and whether it was picked. Output layout:

    <out-dir>/                          default: MAE_Backtesting/output
        <bank_name>/
            MAE_backtest_<N>Q.png       one bar per horizon 1Q..NQ
            MAE_backtest_<N>Q.csv       horizon, origin, forecast window, n_obs, MAE
        backtest_summary_<N>Q.csv       every bank's rows (only with --bank-name All)
        backtest_assessment_<N>Q.csv    Green/Amber/Red rating per bank (only with --bank-name All)
            MAE_backtest_multiorigin_<N>Q.png/.csv  with --first-origin: h-step MAE, no-change MAE
                                        and band limits per horizon
        backtest_multiorigin_<N>Q.csv   with --first-origin: h-step MAE over every origin from
                                        that quarter (expanding window), n_windows per horizon
        backtest_multiorigin_limits_<N>Q.csv       horizon-band green/red limits from this run
        backtest_multiorigin_assessment_<N>Q.csv   band avg/max, worst skill ratio, rating, reason
        cache/<bank_name>.csv           per-origin errors, reused by later runs with horizon <= N

With --first-origin and a single --bank-name, the band limits use the other banks' cached
errors (same first origin, current data and champion), and the limits/assessment files get
the bank name as a suffix; with fewer than 4 banks only the skill-ratio test is applied.

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


def multi_errors(backtest, cache, first_origin, horizon, no_cache=False):
    """Per-origin errors for one bank: from the cache when a stored run covers horizon."""
    key = (backtest.bank, backtest.model, first_origin, backtest.data_hash())
    errors = None if no_cache else cache.load(*key, horizon)
    if errors is None:
        errors = backtest.multi_errors(first_origin)
        cache.store(*key, horizon, errors)
        log.info("%s: many-origin errors computed (%d origins)", backtest.bank, errors.origin.nunique())
    else:
        log.info("%s: many-origin errors reused from cache", backtest.bank)
    return errors[bt.ERROR_COLUMNS]


def choose_model(args, summary, estimates, data, bank, cache, horizon, model=None):
    """(model, scores): the in-sample champion (scores None) or the out-of-sample pick."""
    if args.select == "in-sample":
        return bt.select_model(summary, bank, model, args.group_column), None
    scores = bt.oos_scores(summary, estimates, data, bank, cache, args.first_origin, horizon, args.y, args.x,
                           args.group_column, args.min_train)
    return bt.select_model_oos(scores)


def peer_errors(summary, estimates, source, cache, args, horizon, exclude):
    """Cached errors of the other banks, if they match their current data and model choice."""
    peers = {}
    for bank in resolve_banks("All", summary, args.group_column):
        if bank in exclude:
            continue
        try:
            data = bt.bp.bank_data(source, args.group_column, bank, args.y, args.x)
            model, _ = choose_model(args, summary, estimates, data, bank, cache, horizon)
            rows = bt.bank_rows(estimates, bank, args.group_column)
            peer = bt.MAEBacktest(bank, model, horizon, data, rows[bt.model_mask(rows, model)], args.y, args.x,
                                  args.min_train)
            errors = cache.load(bank, model, args.first_origin, peer.data_hash(), horizon)
        except Exception:
            errors = None
        if errors is not None:
            peers[bank] = errors
    return peers


def write_multi(multi, args, summary, estimates, source, cache, horizon, out_dir):
    tables = {bank: bt.summarise_errors(errors, horizon) for bank, (_, errors) in multi.items()}
    peers = {bank: bt.summarise_errors(e, horizon)
             for bank, e in peer_errors(summary, estimates, source, cache, args, horizon, multi).items()}
    limits, assessment = bt.assess_multi({**peers, **tables}, horizon)
    assessment = assessment[assessment.bank_name.isin(list(multi))].copy()
    assessment.insert(1, "model", assessment.bank_name.map(lambda b: " | ".join(multi[b][0])))
    assessment.insert(2, "min_windows", assessment.bank_name.map(lambda b: int(tables[b].n_windows.min())))
    for bank, table in tables.items():
        bank_dir = out_dir / bt.bp.INVALID_CHARS_RE.sub("-", bank)
        table.assign(bank_name=bank).to_csv(bank_dir / f"MAE_backtest_multiorigin_{horizon}Q.csv", index=False)
    run_all = args.bank_name.strip().lower() == "all"
    suffix = "" if run_all else "_" + bt.bp.INVALID_CHARS_RE.sub("-", next(iter(multi)))
    if run_all:
        pd.concat([t.assign(bank_name=b, model=" | ".join(multi[b][0])) for b, t in tables.items()]).to_csv(
            out_dir / f"backtest_multiorigin_{horizon}Q.csv", index=False)
    limits.to_csv(out_dir / f"backtest_multiorigin_limits_{horizon}Q{suffix}.csv", index=False)
    assessment.to_csv(out_dir / f"backtest_multiorigin_assessment_{horizon}Q{suffix}.csv", index=False)
    log.info("many-origin limits from %d bank(s): %s", int(limits.n_banks.iloc[0]),
             "; ".join(f"{r.band} {r.green:.2f}/{r.red:.2f}" for r in limits.itertuples()))
    for r in assessment.itertuples():
        log.info("  %s: %s%s", r.bank_name, r.rating, f" ({r.reason})" if r.reason else "")
        bank_dir = out_dir / bt.bp.INVALID_CHARS_RE.sub("-", r.bank_name)
        bt.plot_multi_bars(r.bank_name, multi[r.bank_name][0], tables[r.bank_name], limits, r.rating,
                           bank_dir / f"MAE_backtest_multiorigin_{horizon}Q.png", args.y)


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
    parser.add_argument("--out-dir", default=None,
                        help="default: MAE_Backtesting/output (in-sample) or output/out_of_sample")
    parser.add_argument("--select", choices=["in-sample", "out-of-sample"], default="in-sample",
                        help="model choice when --model is not given (default: in-sample MAE)")
    parser.add_argument("--first-origin", default=None,
                        help="also run the many-origin backtest from this quarter, e.g. 2016Q1 "
                             "(default with --select out-of-sample: 2016Q1)")
    parser.add_argument("--no-cache", action="store_true", help="recompute the many-origin errors")
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
        if args.model is not None and args.select == "out-of-sample":
            raise ValueError("give --model or --select out-of-sample, not both")
        estimates = bt.bp.load_estimates(args.estimates, args.group_column)
        source = bt.bp.load_source(args.dependents, args.independents)
    except (FileNotFoundError, ValueError) as e:
        log.error("%s", e)
        return 1

    oos = args.select == "out-of-sample"
    if oos:
        args.first_origin = args.first_origin or "2016Q1"
    out_dir = Path(args.out_dir or (bt.HERE / "output" / "out_of_sample" if oos else bt.HERE / "output"))
    stem = f"MAE_backtest_{horizon}Q"
    log.info("backtesting %d bank(s) over %dQ into %s (%s model choice)", len(banks), horizon, out_dir, args.select)
    cache = bt.ErrorCache(out_dir / "cache", per_model=oos)
    results, multi, scores, skipped = [], {}, [], 0
    for i, bank in enumerate(banks, start=1):
        try:
            data = bt.bp.bank_data(source, args.group_column, bank, args.y, args.x)
            model, bank_scores = choose_model(args, summary, estimates, data, bank, cache, horizon, args.model)
            if bank_scores is not None:
                scores.append(bank_scores)
            rows = bt.bank_rows(estimates, bank, args.group_column)
            spec_rows = rows[bt.model_mask(rows, model)]
            if spec_rows.empty:
                raise ValueError(f"model {' | '.join(model)} has no coefficients in the estimates")
            backtest = bt.MAEBacktest(bank, model, horizon, data, spec_rows, args.y, args.x, args.min_train)
            result = backtest.run()
            if args.first_origin:
                multi[bank] = (model, multi_errors(backtest, cache, args.first_origin, horizon, args.no_cache))
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
        assessment = pd.DataFrame([{"bank_name": r.bank, "model": " | ".join(r.model), **bt.assess(r.table)}
                                   for r in results])
        assessment.to_csv(out_dir / f"backtest_assessment_{horizon}Q.csv", index=False)
    if multi:
        write_multi(multi, args, summary, estimates, source, cache, horizon, out_dir)
    if scores:
        suffix = "" if args.bank_name.strip().lower() == "all" else "_" + bt.bp.INVALID_CHARS_RE.sub("-", banks[0])
        pd.concat(scores).to_csv(out_dir / f"selection_oos_scores_{horizon}Q{suffix}.csv", index=False)
    log.info("done: %d chart(s) in %s, %d bank(s) skipped", len(results), out_dir, skipped)
    return 2 if skipped else 0


if __name__ == "__main__":
    sys.exit(main())
