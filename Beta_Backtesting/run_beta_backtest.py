"""Deposit-beta backtests for one bank or all banks: theta stability, and with --realized the
realized-beta backtest.

Usage (all arguments optional; defaults point at the files in the project folder):
    python Beta_Backtesting/run_beta_backtest.py [--horizon 8Q] [--bank-name NAME|All]
        [--model "test_name | IC/selected lag | trend type"] [--select out-of-sample|in-sample]
        [--first-origin 2016Q1] [--realized] [--min-move 0.25] [--no-cache] [--min-train 20]
        [--summary FILE] [--estimates FILE] [--asym-summary FILE] [--asym-estimates FILE]
        [--dependents FILE] [--independents FILE] [--y COLUMN] [--x COLUMN] [--group-column COLUMN]
        [--out-dir DIR]

--bank-name All (the default) runs every bank in "estimation result summary.csv". --model
picks the specification for a single bank; without it the bank's champion under --select is
used, as in the MAE backtest: out-of-sample (the default, backtest.DEFAULT_SELECT; reuses and
fills MAE_Backtesting/output/out_of_sample/cache, scored from --first-origin) or in-sample.
See beta_backtest.py for the methods. Output layout:

    <out-dir>/                              default: backtest.output_dir(--select, "Beta")
        <bank_name>/
            beta_backtest_multiorigin.csv   theta (or theta+ and theta-), SE, lambda(+-) at every origin
                                            from --first-origin to T-1, deviation from the full-sample value
            beta_backtest_multiorigin.png   theta by origin, +/- 2 SE, full-sample value +/- 20%, rating
            realized_beta_<N>Q.csv          with --realized: per h, scored pairs, mean actual and implied
                                            beta, MAE, bias, no-change MAE, skill, mean reference theta
            realized_beta_pairs_<N>Q.csv    with --realized: every (start date, h) pair, scored or not
            realized_beta_<N>Q.png          with --realized: actual vs implied beta; MAE vs no-change
        beta_backtest_multiorigin_all_banks.csv/.png   with All: every bank's origins
        beta_backtest_multiorigin_assessment.csv       Green/Amber/Red per bank on the origins from
                                            2020Q1 (beta_backtest.assess_multi; worst of theta+-)
        realized_beta_summary_<N>Q.csv      with --realized and All: every bank's per-h rows
        realized_beta_assessment_<N>Q.csv   with --realized: band MAE, bias, skill and rating per bank
        realized_beta_all_banks_<N>Q.png    with --realized and All: skill ratio by band, every bank
        cache/<bank_name>.csv               per-origin thetas, reused while model, first origin and data match
With a single --bank-name the bank name is appended to the assessment file names.

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


class BetaRun:
    """Loads the inputs once, then backtests and writes the outputs bank by bank."""

    def __init__(self, args):
        self.args = args
        self.horizon = rb.parse_horizon(args.horizon)
        self.summary, self.estimates = bt.load_candidates(args.summary, args.estimates, args.asym_summary,
                                                          args.asym_estimates, args.group_column)
        missing = [c for c in [args.group_column] + bt.SPEC_KEYS + ["MAE"] if c not in self.summary.columns]
        if missing:
            raise ValueError(f"{args.summary} is missing columns: {', '.join(missing)}")
        self.banks = rb.resolve_banks(args.bank_name, self.summary, args.group_column)
        if args.model is not None and len(self.banks) > 1:
            raise ValueError("--model applies to one bank; give --bank-name too")
        self.source = bp.load_source(args.dependents, args.independents)
        self.out_dir = Path(args.out_dir or bt.output_dir(args.select, "Beta"))
        # The out-of-sample pick reuses the MAE backtest's per-model error cache (and fills it if needed).
        self.select_cache = bt.ErrorCache(bt.output_dir("out-of-sample") / "cache", per_model=True)
        self.plotter = bb.BetaPlotter(args.y, args.x)
        self.cache = bb.BetaCache(self.out_dir / "cache")
        self.suffix = "" if args.bank_name.strip().lower() == "all" else "_" + bp.INVALID_CHARS_RE.sub("-", self.banks[0])

    def model(self, bank, data):
        a = self.args
        model, _ = rb.choose_model(a, self.summary, self.estimates, data, bank, self.select_cache, self.horizon, a.model)
        rows = bt.bank_rows(self.estimates, bank, a.group_column)
        spec_rows = rows[bt.model_mask(rows, model)]
        if spec_rows.empty:
            raise ValueError(f"model {' | '.join(model)} has no coefficients in the estimates")
        return model, spec_rows

    def multi_betas(self, backtest):
        """Betas at every origin from --first-origin: from the cache when a stored run matches."""
        key = (backtest.bank, backtest.model, self.args.first_origin, backtest.data_hash(), backtest.spec())
        betas = None if self.args.no_cache else self.cache.load(*key)
        if betas is None:
            betas = backtest.origin_betas(self.args.first_origin)
            self.cache.store(*key, betas)
            log.info("%s: many-origin betas computed (%d origins)", backtest.bank, betas.origin.nunique())
        else:
            log.info("%s: many-origin betas reused from cache", backtest.bank)
        return betas

    def run_bank(self, bank):
        a = self.args
        data = bp.bank_data(self.source, a.group_column, bank, a.y, a.x)
        model, spec_rows = self.model(bank, data)
        backtest = bb.BetaBacktest(bank, model, self.horizon, data, spec_rows, a.y, a.x, a.min_train)
        result = bb.BetaResult(bank, model, backtest.full_sample_beta())
        result.multi = bb.deviations(self.multi_betas(backtest), result.full_sample)
        result.assessment = bb.assess_multi(result.multi, x=a.x)
        bank_dir = self.out_dir / bp.INVALID_CHARS_RE.sub("-", bank)
        bank_dir.mkdir(parents=True, exist_ok=True)
        result.labelled_multi().to_csv(bank_dir / "beta_backtest_multiorigin.csv", index=False)
        self.plotter.origins_chart(result, bank_dir / "beta_backtest_multiorigin.png", rating=result.assessment["rating"])
        realized = None
        if a.realized:
            rbt = bb.RealizedBetaBacktest(bank, model, self.horizon, data, spec_rows, a.y, a.x, a.min_train)
            pairs = rbt.pairs(a.first_origin, a.min_move)
            table = bb.summarise_realized(pairs, self.horizon)
            assessment = {"first_origin": pairs.origin.iloc[0], "last_origin": pairs.origin.iloc[-1],
                          **bb.assess_realized(pairs, self.horizon)}
            keys = dict(zip(["bank_name"] + bt.SPEC_KEYS, [bank, *model]))
            pairs.assign(**keys).to_csv(bank_dir / f"realized_beta_pairs_{self.horizon}Q.csv", index=False)
            table.assign(**keys).to_csv(bank_dir / f"realized_beta_{self.horizon}Q.csv", index=False)
            self.plotter.realized_chart(bank, model, table, assessment, bank_dir / f"realized_beta_{self.horizon}Q.png",
                                        self.horizon, a.min_move)
            realized = (table, assessment)
        return result, realized

    def write_all(self, results, realized):
        run_all = not self.suffix
        if run_all:
            pd.concat([r.labelled_multi() for r in results]).to_csv(
                self.out_dir / "beta_backtest_multiorigin_all_banks.csv", index=False)
            self.plotter.all_banks_origins(results, self.out_dir / "beta_backtest_multiorigin_all_banks.png",
                                           ratings={r.bank: r.assessment["rating"] for r in results})
        pd.DataFrame([{"bank_name": r.bank, "model": " | ".join(r.model), "first_origin": r.multi.origin.iloc[0],
                       "last_origin": r.multi.origin.iloc[-1], **r.assessment} for r in results]).to_csv(
            self.out_dir / f"beta_backtest_multiorigin_assessment{self.suffix}.csv", index=False)
        for r in results:
            log.info("  theta stability %s: %s%s", r.bank, r.assessment["rating"],
                     f" ({r.assessment['reason']})" if r.assessment["reason"] else "")
        if realized:
            assessment = pd.DataFrame([{"bank_name": b, "model": " | ".join(m), **a} for b, (m, _, a) in realized.items()])
            assessment.to_csv(self.out_dir / f"realized_beta_assessment_{self.horizon}Q{self.suffix}.csv", index=False)
            for r in assessment.itertuples():
                log.info("  realized beta %s: %s (worst skill %.2f in %s)%s", r.bank_name, r.rating, r.worst_skill,
                         r.worst_band, f"; {r.reason}" if r.reason else "")
            if run_all:
                pd.concat([t.assign(bank_name=b, model=" | ".join(m)) for b, (m, t, _) in realized.items()]).to_csv(
                    self.out_dir / f"realized_beta_summary_{self.horizon}Q.csv", index=False)
                self.plotter.realized_all_banks(assessment, self.horizon,
                                                self.out_dir / f"realized_beta_all_banks_{self.horizon}Q.png")

    def run(self):
        log.info("beta backtests of %d bank(s) from %s into %s (%s model choice%s)", len(self.banks),
                 self.args.first_origin, self.out_dir, self.args.select, ", realized beta" if self.args.realized else "")
        results, realized, skipped = [], {}, 0
        for i, bank in enumerate(self.banks, start=1):
            try:
                result, real = self.run_bank(bank)
            except Exception as e:
                log.warning("[%d/%d] %s skipped: %s", i, len(self.banks), bank, e)
                skipped += 1
                continue
            log.info("[%d/%d] %s: %s; %s", i, len(self.banks), bank, " | ".join(result.model),
                     result.assessment["ratings_by_param"])
            results.append(result)
            if real is not None:
                realized[bank] = (result.model, *real)
        if results:
            self.write_all(results, realized)
        log.info("done: %d bank(s) in %s, %d skipped", len(results), self.out_dir, skipped)
        return 2 if skipped else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Theta-stability and realized-beta backtests.")
    parser.add_argument("--horizon", default="8Q", help="horizon in quarters (realized beta, out-of-sample scoring)")
    parser.add_argument("--bank-name", default="All", help='a bank name, or "All"')
    parser.add_argument("--model", default=None,
                        help='"test_name | IC/selected lag | trend type"; single bank only (default: the --select rule)')
    parser.add_argument("--min-train", type=int, default=20, help="quarters required before the first origin")
    parser.add_argument("--summary", default=rb.SUMMARY_DEFAULT)
    parser.add_argument("--estimates", default=bp.DEFAULTS["estimates"])
    parser.add_argument("--asym-summary", default=bt.CANDIDATE_FILES["asym_summary"])
    parser.add_argument("--asym-estimates", default=bt.CANDIDATE_FILES["asym_estimates"])
    parser.add_argument("--dependents", default=bp.DEFAULTS["dependents"])
    parser.add_argument("--independents", default=bp.DEFAULTS["independents"])
    parser.add_argument("--y", default=bp.DEFAULTS["y"], help="dependent column")
    parser.add_argument("--x", default=bp.DEFAULTS["x"], help="regressor column")
    parser.add_argument("--group-column", default=bp.DEFAULTS["group_column"])
    parser.add_argument("--out-dir", default=None,
                        help="default: Beta_Backtesting/output/out_of_sample (out-of-sample) or output (in-sample)")
    parser.add_argument("--select", choices=bt.SELECT_CHOICES, default=bt.DEFAULT_SELECT,
                        help=f"model choice when --model is not given (default: {bt.DEFAULT_SELECT}); "
                             "see MAE_Backtesting/run_backtest.py")
    parser.add_argument("--first-origin", default="2016Q1", help="first start date (expanding window)")
    parser.add_argument("--realized", action="store_true", help="also run the realized-beta backtest")
    parser.add_argument("--min-move", type=float, default=bb.EASING_DROP,
                        help="smallest |FFT_{t+h} - FFT_t| in pp for a realized-beta pair to be scored")
    parser.add_argument("--no-cache", action="store_true", help="recompute the many-origin betas")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)

    try:
        run = BetaRun(args)
    except (FileNotFoundError, ValueError) as e:
        log.error("%s", e)
        return 1
    return run.run()


if __name__ == "__main__":
    sys.exit(main())
