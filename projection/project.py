"""Dynamic projection of a bank's deposit rate under an FFT scenario, with the trend freeze (issue #7).

Usage (all arguments except --scenario optional; defaults point at the files in the repo root):
    python projection/project.py --scenario FILE [--bank-name NAME|All] [--model "test | IC | trend"]
        [--no-freeze-trend] [-o OUTPUT_CSV] [--estimates FILE] [--summary FILE]
        [--dependents FILE] [--independents FILE]

The model is the bank's champion (MAE_Backtesting/backtest.py select_model: lowest in-sample
MAE in "estimation result summary.csv") unless --model names another; its coefficients are
the full-sample one-step ECM in "ECM estimation results.csv". From the last observed quarter
T the ECM is iterated forward for every scenario quarter T+1..T+H: predicted y is fed back as
the lag (as in the backtest's dynamic forecast) and FFT takes the scenario values.

Trend freeze (§5.7, L14): a deterministic trend in the long-run relation is held at its value
at T for every projected quarter, so the equilibrium is c + delta*T + theta*x rather than
c + delta*t + theta*x. With FFT held flat the path converges to that level instead of drifting
by delta per quarter. Models without a trend are unaffected. --no-freeze-trend lets the trend
keep counting (diagnostic only).

The scenario CSV has the same layout as the FFT files: first column the quarter (2026Q3 or a
date), column FFT. Quarters up to T are ignored; the rest must run without gaps from T+1.

Output: one row per (bank, projected quarter) with the model keys, step h, FFT, the projected
rate_pf_clean, the trend value used and the long-run equilibrium c + delta*trend + theta*FFT.
"""

import argparse
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "MAE_Backtesting"))
import backtest as bt  # noqa: E402  (also puts ROOT on sys.path)
import bank_plots as bp  # noqa: E402

log = logging.getLogger("projection")
DEFAULTS = {**bp.DEFAULTS, "summary": ROOT / "estimation result summary.csv"}
OUTPUT_COLUMNS = ["bank_name"] + bp.SPEC_KEYS + ["quarter", "h", "FFT", "rate_pf_clean", "trend",
                                                 "long_run_equilibrium"]


def read_scenario(path, x=DEFAULTS["x"]):
    """Scenario FFT path as a quarter-indexed Series."""
    df = bp.read_csv(path)
    if x not in df.columns:
        raise ValueError(f"{path} has no {x} column")
    s = pd.Series(pd.to_numeric(df[x], errors="coerce").values, index=bp.to_periods(df[df.columns[0]]), name=x)
    if s.isna().any():
        raise ValueError(f"{path}: {x} is missing or not numeric for {', '.join(map(str, s.index[s.isna()]))}")
    if s.index.duplicated().any():
        raise ValueError(f"{path}: duplicate quarters {', '.join(map(str, s.index[s.index.duplicated()]))}")
    return s.sort_index()


class Projection:
    """One bank's ECM, ready to be iterated forward from the last observed quarter T."""

    def __init__(self, bank, model, history, params, y=DEFAULTS["y"], x=DEFAULTS["x"]):
        self.bank, self.model, self.y, self.x = bank, tuple(model), y, x
        self.history = history[[y, x]]
        self.params = params
        bt.spec_from_terms(list(params.index), y, x)  # rejects terms the ECM does not know
        self.T = self.history.index[-1]
        self.trend_T = float(bp.regressor(self.history, "trend").iloc[-1])

    @classmethod
    def champion(cls, bank, estimates, summary, source, model=None, y=DEFAULTS["y"], x=DEFAULTS["x"],
                 group_column=DEFAULTS["group_column"]):
        """The bank's champion (or `model`) with its full-sample coefficients."""
        model = bt.select_model(summary, bank, model, group_column)
        rows = bt.bank_rows(estimates, bank, group_column)
        rows = rows[bt.model_mask(rows, model)]
        params = rows[~rows["term"].astype(str).str.startswith("LR: ")].set_index("term")["coef"].astype(float)
        if params.empty:
            raise ValueError(f"{bank} has no coefficients for {' | '.join(model)}")
        return cls(bank, model, bp.bank_data(source, group_column, bank, y, x), params, y, x)

    def long_run(self):
        """(c, delta, theta) = -(const, trend, x.L1 coefficient) / lambda; 0 for absent terms."""
        lam = self.params[f"{self.y}.L1"]
        return tuple(-self.params.get(term, 0.0) / lam for term in ("const", "trend", f"{self.x}.L1"))

    def equilibrium(self, x_value, trend=None):
        """Long-run level c + delta*trend + theta*x; the trend defaults to its frozen value at T."""
        c, delta, theta = self.long_run()
        return c + delta * (self.trend_T if trend is None else trend) + theta * x_value

    def future_path(self, scenario):
        """Scenario values for T+1..T+H (quarters up to T dropped), checked for gaps."""
        future = scenario[scenario.index > self.T]
        if future.empty:
            raise ValueError(f"scenario has no quarter after {self.T}")
        expected = pd.period_range(self.T + 1, periods=len(future), freq="Q")
        if not future.index.equals(expected):
            missing = sorted(set(expected) - set(future.index)) or [future.index[0]]
            raise ValueError(f"scenario must run without gaps from {self.T + 1}; check {missing[0]}")
        return future

    def project(self, scenario, freeze_trend=True):
        """Projected y for every scenario quarter after T (OUTPUT_COLUMNS)."""
        future = self.future_path(scenario)
        path = pd.concat([self.history, pd.DataFrame({self.y: np.nan, self.x: future})])
        trend = bp.regressor(path, "trend")
        if freeze_trend:
            trend = trend.clip(upper=self.trend_T)
        for t in future.index:
            # Same recursion as MAEBacktest.forecast, except that the trend is the (frozen) series above.
            X = pd.Series({term: trend[t] if term == "trend" else bp.regressor(path, term)[t]
                           for term in self.params.index})
            path.loc[t, self.y] = path.loc[t - 1, self.y] + float(X @ self.params)
        out = path.loc[future.index].assign(trend=trend[future.index] if "trend" in self.params else np.nan)
        out["long_run_equilibrium"] = self.equilibrium(out[self.x], out["trend"].fillna(0.0))
        keys = dict(zip(["bank_name"] + bp.SPEC_KEYS, [self.bank, *self.model]))
        out = out.assign(**keys, quarter=out.index.astype(str), h=np.arange(1, len(out) + 1))
        return out.rename(columns={self.y: "rate_pf_clean", self.x: "FFT"})[OUTPUT_COLUMNS].reset_index(drop=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Project each bank's deposit rate under an FFT scenario.")
    parser.add_argument("--scenario", required=True, help="CSV of FFT by quarter for T+1..T+H")
    parser.add_argument("--bank-name", default="All", help='a bank exactly as in the estimates, or "All"')
    parser.add_argument("--model", help='override the champion: "test_name | IC/selected lag | trend type"')
    parser.add_argument("--no-freeze-trend", action="store_true",
                        help="let a deterministic trend keep counting after T (diagnostic only)")
    parser.add_argument("-o", "--output", help="output CSV (default projection/output/<scenario>_projection.csv)")
    parser.add_argument("--estimates", default=DEFAULTS["estimates"])
    parser.add_argument("--summary", default=DEFAULTS["summary"])
    parser.add_argument("--dependents", default=DEFAULTS["dependents"])
    parser.add_argument("--independents", default=DEFAULTS["independents"])
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)

    try:
        estimates = bp.load_estimates(args.estimates)
        summary = bp.read_csv(args.summary)
        source = bp.load_source(args.dependents, args.independents)
        scenario = read_scenario(args.scenario)
    except (FileNotFoundError, ValueError) as e:
        bp.err(e)
        return 1
    banks = (sorted(summary["bank_name"].astype(str).str.strip().unique()) if args.bank_name == "All"
             else [args.bank_name])
    if args.model and len(banks) > 1:
        bp.err("--model needs a single --bank-name")
        return 1

    frames, failed = [], []
    for bank in banks:
        try:
            p = Projection.champion(bank, estimates, summary, source, args.model)
            out = p.project(scenario, freeze_trend=not args.no_freeze_trend)
        except (ValueError, KeyError) as e:
            bp.err(f"{bank}: {e}")
            failed.append(bank)
            continue
        frames.append(out)
        last = out.iloc[-1]
        trend_note = (f"trend frozen at {p.trend_T:g} ({p.T})" if "trend" in p.params and not args.no_freeze_trend
                      else "trend not frozen" if "trend" in p.params else "no trend")
        log.info("%s | %s | T=%s y_T=%.3f -> %s y=%.3f, equilibrium %.3f; %s", bank, " | ".join(p.model),
                 p.T, p.history[p.y].iloc[-1], last.quarter, last.rate_pf_clean, last.long_run_equilibrium,
                 trend_note)
    if not frames:
        return 1
    output = Path(args.output) if args.output else HERE / "output" / f"{Path(args.scenario).stem}_projection.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    pd.concat(frames, ignore_index=True).to_csv(output, index=False)
    log.info("wrote %s (%d banks, %d rows)", output, len(frames), sum(map(len, frames)))
    return 2 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
