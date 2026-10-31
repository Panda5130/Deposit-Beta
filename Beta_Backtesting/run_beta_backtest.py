"""Rolling-origin long-run beta stability bar charts for one bank or all banks.

Usage (all arguments optional; defaults point at the files in the project folder):
    python Beta_Backtesting/run_beta_backtest.py [--horizon 8Q] [--bank-name NAME|All]
        [--model "test_name | IC/selected lag | trend type"] [--min-train 20]
        [--summary FILE] [--estimates FILE] [--dependents FILE] [--independents FILE]
        [--y COLUMN] [--x COLUMN] [--group-column COLUMN] [--out-dir DIR]

--bank-name All (the default) runs every bank in "estimation result summary.csv". --model
picks the specification for a single bank; without it the bank's champion is used (lowest
in-sample MAE, ties broken EG > ARDL > Johansen), as in the MAE backtest. See
beta_backtest.py for the method. Output layout:

    <out-dir>/                              default: Beta_Backtesting/output
        <bank_name>/
            beta_backtest_origins_<N>Q.csv  beta, its SE and p-value, lambda at each origin T-N..T-1
            beta_backtest_<N>Q.csv          per horizon kQ: mean/min/max/std beta over origins T-k..T-1,
                                            full-sample beta, max |deviation| from it
            beta_backtest_<N>Q.png          one bar (mean beta) per horizon 1Q..NQ
        beta_backtest_summary_<N>Q.csv      every bank's horizon rows (only with --bank-name All)
        beta_backtest_all_banks_<N>Q.png    mean beta by horizon, one line per bank (only with --bank-name All)

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
        self.out_dir = Path(args.out_dir)
        self.stem = f"beta_backtest_{self.horizon}Q"
        self.plotter = bb.BetaPlotter(args.y, args.x)

    def backtest(self, bank):
        a = self.args
        model = bt.select_model(self.summary, bank, a.model, a.group_column)
        rows = bt.bank_rows(self.estimates, bank, a.group_column)
        spec_rows = rows[bt.model_mask(rows, model)]
        if spec_rows.empty:
            raise ValueError(f"model {' | '.join(model)} has no coefficients in the estimates")
        data = bp.bank_data(self.source, a.group_column, bank, a.y, a.x)
        return bb.BetaBacktest(bank, model, self.horizon, data, spec_rows, a.y, a.x, a.min_train)

    def run_bank(self, bank):
        result = self.backtest(bank).run()
        bank_dir = self.out_dir / bp.INVALID_CHARS_RE.sub("-", bank)
        bank_dir.mkdir(parents=True, exist_ok=True)
        result.labelled_origins().to_csv(bank_dir / f"beta_backtest_origins_{self.horizon}Q.csv", index=False)
        result.labelled_summary().to_csv(bank_dir / f"{self.stem}.csv", index=False)
        self.plotter.bars(result, bank_dir / f"{self.stem}.png")
        return result

    def write_all(self, results):
        pd.concat([r.labelled_summary() for r in results]).to_csv(
            self.out_dir / f"beta_backtest_summary_{self.horizon}Q.csv", index=False)
        self.plotter.all_banks(results, self.out_dir / f"beta_backtest_all_banks_{self.horizon}Q.png")

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
    parser.add_argument("--out-dir", default=bb.HERE / "output")
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
