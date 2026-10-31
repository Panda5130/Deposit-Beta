"""Rolling-origin long-run beta stability bar charts for one bank or all banks.

Usage (all arguments optional; defaults point at the files in the project folder):
    python Beta_Backtesting/run_beta_backtest.py [--horizon 8Q] [--bank-name NAME|All]
        [--model "test_name | IC/selected lag | trend type"] [--select in-sample|out-of-sample]
        [--first-origin 2016Q1] [--no-cache] [--min-train 20]
        [--summary FILE] [--estimates FILE] [--dependents FILE] [--independents FILE]
        [--y COLUMN] [--x COLUMN] [--group-column COLUMN] [--out-dir DIR]

--bank-name All (the default) runs every bank in "estimation result summary.csv". --model
picks the specification for a single bank; without it the bank's champion is used (lowest
in-sample MAE, ties broken EG > ARDL > Johansen), as in the MAE backtest. --select
out-of-sample uses the MAE backtest's optional out-of-sample pick instead (from origins
--first-origin, default 2016Q1, reusing MAE_Backtesting/output/out_of_sample/cache) and writes
to Beta_Backtesting/output/out_of_sample by default. See beta_backtest.py for the method.
Output layout:

    <out-dir>/                              default: Beta_Backtesting/output
        <bank_name>/
            beta_backtest_origins_<N>Q.csv  beta, its SE and p-value, lambda at each origin T-N..T-1
            beta_backtest_<N>Q.csv          per horizon kQ: mean/min/max/std beta over origins T-k..T-1,
                                            full-sample beta, max |deviation| from it
            beta_backtest_<N>Q.png          one bar (mean beta) per horizon 1Q..NQ
            beta_backtest_multiorigin.csv   with --first-origin: beta, SE, lambda at every origin from that
                                            quarter to T-1, deviation from the full-sample beta (pp, share, SEs)
            beta_backtest_multiorigin.png   beta by origin, +/- 2 SE, full-sample beta +/- 20%, rating
        beta_backtest_summary_<N>Q.csv      every bank's horizon rows (only with --bank-name All)
        beta_backtest_all_banks_<N>Q.png    mean beta by horizon, one line per bank (only with --bank-name All)
        beta_backtest_multiorigin_all_banks.csv/.png   with --first-origin and All: every bank's origins
        beta_backtest_multiorigin_assessment.csv       with --first-origin: Green/Amber/Red per bank on the
                                            origins from 2020Q1 (beta_backtest.assess_multi); with a single
                                            --bank-name the bank name is appended
        cache/<bank_name>.csv               per-origin betas, reused while model, first origin and data match

A bank that cannot be backtested is logged and skipped; the others still run. Exit code: 0
when every bank ran, 2 when some were skipped, 1 when the arguments or inputs were invalid.
"""

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

import beta_backtest as bb

sys.path.insert(0, str(bb.ROOT / "MAE_Backtesting"))
import run_backtest as rb  # noqa: E402

bt, bp = bb.bt, bb.bp
log = logging.getLogger("beta_backtest")


class BetaStabilityRun:
    """Loads the inputs once, then backtests and writes the outputs bank by bank."""

    def __init__(self, args):
        self.args = args
        self.horizon = rb.parse_horizon(args.horizon)
        self.summary = bp.read_csv(args.summary)
        missing = [c for c in [args.group_column] + bt.SPEC_KEYS + ["MAE"] if c not in self.summary.columns]
        if missing:
            raise ValueError(f"{args.summary} is missing columns: {', '.join(missing)}")
        self.banks = rb.resolve_banks(args.bank_name, self.summary, args.group_column)
        if args.model is not None and len(self.banks) > 1:
            raise ValueError("--model applies to one bank; give --bank-name too")
        self.estimates = bp.load_estimates(args.estimates, args.group_column)
        self.source = bp.load_source(args.dependents, args.independents)
        if args.model is not None and args.select == "out-of-sample":
            raise ValueError("give --model or --select out-of-sample, not both")
        oos = args.select == "out-of-sample"
        self.out_dir = Path(args.out_dir or (bb.HERE / "output" / "out_of_sample" if oos else bb.HERE / "output"))
        # The out-of-sample pick reuses the MAE backtest's per-model error cache (and fills it if needed).
        self.select_args = argparse.Namespace(**{**vars(args), "first_origin": args.first_origin or "2016Q1"})
        self.select_cache = bt.ErrorCache(bt.HERE / "output" / "out_of_sample" / "cache", per_model=True)
        self.stem = f"beta_backtest_{self.horizon}Q"
        self.plotter = bb.BetaPlotter(args.y, args.x)
        self.cache = bb.BetaCache(self.out_dir / "cache")

    def backtest(self, bank):
        a = self.args
        data = bp.bank_data(self.source, a.group_column, bank, a.y, a.x)
        model, _ = rb.choose_model(self.select_args, self.summary, self.estimates, data, bank, self.select_cache,
                                   self.horizon, a.model)
        rows = bt.bank_rows(self.estimates, bank, a.group_column)
        spec_rows = rows[bt.model_mask(rows, model)]
        if spec_rows.empty:
            raise ValueError(f"model {' | '.join(model)} has no coefficients in the estimates")
        return bb.BetaBacktest(bank, model, self.horizon, data, spec_rows, a.y, a.x, a.min_train)

    def multi_betas(self, backtest):
        """Betas at every origin from --first-origin: from the cache when a stored run matches."""
        key = (backtest.bank, backtest.model, self.args.first_origin, backtest.data_hash())
        betas = None if self.args.no_cache else self.cache.load(*key)
        if betas is None:
            betas = backtest.origin_betas(self.args.first_origin)
            self.cache.store(*key, betas)
            log.info("%s: many-origin betas computed (%d origins)", backtest.bank, len(betas))
        else:
            log.info("%s: many-origin betas reused from cache", backtest.bank)
        return betas

    def run_bank(self, bank):
        backtest = self.backtest(bank)
        result = backtest.run()
        bank_dir = self.out_dir / bp.INVALID_CHARS_RE.sub("-", bank)
        bank_dir.mkdir(parents=True, exist_ok=True)
        result.labelled_origins().to_csv(bank_dir / f"beta_backtest_origins_{self.horizon}Q.csv", index=False)
        result.labelled_summary().to_csv(bank_dir / f"{self.stem}.csv", index=False)
        self.plotter.bars(result, bank_dir / f"{self.stem}.png")
        if self.args.first_origin:
            result.multi = bb.deviations(self.multi_betas(backtest), result.full_sample)
            result.assessment = bb.assess_multi(result.multi)
            result.labelled_multi().to_csv(bank_dir / "beta_backtest_multiorigin.csv", index=False)
            self.plotter.origins_chart(result, bank_dir / "beta_backtest_multiorigin.png",
                                       rating=result.assessment["rating"])
        return result

    def write_all(self, results):
        pd.concat([r.labelled_summary() for r in results]).to_csv(
            self.out_dir / f"beta_backtest_summary_{self.horizon}Q.csv", index=False)
        self.plotter.all_banks(results, self.out_dir / f"beta_backtest_all_banks_{self.horizon}Q.png")
        multi = [r for r in results if r.multi is not None]
        if multi:
            pd.concat([r.labelled_multi() for r in multi]).to_csv(
                self.out_dir / "beta_backtest_multiorigin_all_banks.csv", index=False)
            self.plotter.all_banks_origins(multi, self.out_dir / "beta_backtest_multiorigin_all_banks.png",
                                           ratings={r.bank: r.assessment["rating"] for r in multi})

    def write_assessment(self, results):
        multi = [r for r in results if r.multi is not None]
        if not multi:
            return
        run_all = self.args.bank_name.strip().lower() == "all"
        suffix = "" if run_all else "_" + bp.INVALID_CHARS_RE.sub("-", multi[0].bank)
        pd.DataFrame([{"bank_name": r.bank, "model": " | ".join(r.model), "first_origin": r.multi.origin.iloc[0],
                       "last_origin": r.multi.origin.iloc[-1], **r.assessment} for r in multi]).to_csv(
            self.out_dir / f"beta_backtest_multiorigin_assessment{suffix}.csv", index=False)
        for r in multi:
            a = r.assessment
            log.info("  %s: %s%s", r.bank, a["rating"], f" ({a['reason']})" if a["reason"] else "")

    def run(self):
        log.info("backtesting beta of %d bank(s) over %dQ into %s", len(self.banks), self.horizon, self.out_dir)
        results, skipped = [], 0
        for i, bank in enumerate(self.banks, start=1):
            try:
                result = self.run_bank(bank)
            except Exception as e:
                log.warning("[%d/%d] %s skipped: %s", i, len(self.banks), bank, e)
                skipped += 1
                continue
            log.info("[%d/%d] %s: %s; full-sample beta %.4f; mean beta %s", i, len(self.banks), bank,
                     " | ".join(result.model), result.full_sample["beta"],
                     ", ".join(f"{r.horizon_q}={r.mean_beta:.4f}" for r in result.summary.itertuples()))
            results.append(result)
        if results and self.args.bank_name.strip().lower() == "all":
            self.write_all(results)
        self.write_assessment(results)
        log.info("done: %d chart(s) in %s, %d bank(s) skipped", len(results), self.out_dir, skipped)
        return 2 if skipped else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Rolling-origin long-run beta stability bar charts.")
    parser.add_argument("--horizon", default="8Q", help="backtest horizon in quarters, e.g. 8Q")
    parser.add_argument("--bank-name", default="All", help='a bank name, or "All"')
    parser.add_argument("--model", default=None,
                        help='"test_name | IC/selected lag | trend type"; single bank only '
                             "(default: lowest in-sample MAE)")
    parser.add_argument("--min-train", type=int, default=20, help="quarters required before the first origin")
    parser.add_argument("--summary", default=rb.SUMMARY_DEFAULT)
    parser.add_argument("--estimates", default=bp.DEFAULTS["estimates"])
    parser.add_argument("--dependents", default=bp.DEFAULTS["dependents"])
    parser.add_argument("--independents", default=bp.DEFAULTS["independents"])
    parser.add_argument("--y", default=bp.DEFAULTS["y"], help="dependent column")
    parser.add_argument("--x", default=bp.DEFAULTS["x"], help="regressor column")
    parser.add_argument("--group-column", default=bp.DEFAULTS["group_column"])
    parser.add_argument("--out-dir", default=None,
                        help="default: Beta_Backtesting/output (in-sample) or output/out_of_sample")
    parser.add_argument("--select", choices=["in-sample", "out-of-sample"], default="in-sample",
                        help="model choice when --model is not given (default: in-sample MAE); "
                             "see MAE_Backtesting/run_backtest.py")
    parser.add_argument("--first-origin", default=None,
                        help="also re-estimate beta at every origin from this quarter, e.g. 2016Q1")
    parser.add_argument("--no-cache", action="store_true", help="recompute the many-origin betas")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)

    try:
        run = BetaStabilityRun(args)
    except (FileNotFoundError, ValueError) as e:
        log.error("%s", e)
        return 1
    return run.run()


if __name__ == "__main__":
    sys.exit(main())
