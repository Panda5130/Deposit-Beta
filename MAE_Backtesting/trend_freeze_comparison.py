"""Many-origin backtest with the trend frozen at each origin vs unfrozen, for the trend champions.

    python MAE_Backtesting/trend_freeze_comparison.py [--banks Glacier,SouthState,Huntington] [--horizon 8Q]

Writes MAE_Backtesting/output/out_of_sample/trend_freeze_comparison.csv: per bank and horizon the
unfrozen and frozen mean MAE, their difference, the no-change MAE and both skill ratios. A bank whose
champion has no deterministic trend shows zero differences (the freeze is a no-op for it).
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import backtest as bt  # noqa: E402
import run_backtest as rb  # noqa: E402


def compare(banks, horizon, first_origin="2016Q1", out_dir=None, min_train=20):
    out_dir = Path(out_dir or bt.output_dir(bt.DEFAULT_SELECT))
    summary, estimates = bt.load_candidates()
    source = bt.bp.load_source(bt.bp.DEFAULTS["dependents"], bt.bp.DEFAULTS["independents"])
    cache = bt.ErrorCache(out_dir / "cache", per_model=True)  # the standard run's cache: read-only here
    frozen_cache = bt.ErrorCache(out_dir / "cache_trend_freeze", per_model=True)  # untracked scratch
    gc = bt.bp.DEFAULTS["group_column"]
    args = argparse.Namespace(select=bt.DEFAULT_SELECT, first_origin=first_origin, y=bt.bp.DEFAULTS["y"],
                              x=bt.bp.DEFAULTS["x"], group_column=gc, min_train=min_train)
    names = [b for b in rb.resolve_banks("All", summary, gc) if any(k.lower() in b.lower() for k in banks)]
    rows = []
    for bank in names:
        data = bt.bp.bank_data(source, gc, bank, args.y, args.x)
        model, _ = rb.choose_model(args, summary, estimates, data, bank, cache, horizon)
        spec = bt.bank_rows(estimates, bank, gc)
        spec = spec[bt.model_mask(spec, model)]
        tabs = {}
        for frozen in (False, True):
            b = bt.MAEBacktest(bank, model, horizon, data, spec, args.y, args.x, min_train, frozen)
            tabs[frozen] = bt.summarise_errors(rb.multi_errors(b, frozen_cache if frozen else cache, first_origin, horizon), horizon)
        has_trend = "trend" in b.det
        for u, f in zip(tabs[False].itertuples(), tabs[True].itertuples()):
            rows.append({"bank_name": bank, "model": " | ".join(model), "has_trend": has_trend,
                         "h": int(u.horizon_q[:-1]), "n_windows": u.n_windows, "mae_unfrozen": u.mae,
                         "mae_frozen": f.mae, "mae_diff": f.mae - u.mae, "naive_mae": u.naive_mae,
                         "skill_unfrozen": u.mae / u.naive_mae, "skill_frozen": f.mae / f.naive_mae,
                         "skill_diff": f.mae / f.naive_mae - u.mae / u.naive_mae})
    out = pd.DataFrame(rows)
    out.to_csv(out_dir / "trend_freeze_comparison.csv", index=False)
    return out


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--banks", default="Glacier,SouthState,Huntington", help="comma-separated name fragments")
    p.add_argument("--horizon", default="8Q")
    a = p.parse_args()
    res = compare([s.strip() for s in a.banks.split(",")], rb.parse_horizon(a.horizon))
    print(res.groupby("bank_name")[["mae_diff", "skill_diff"]].agg(["mean", "max"]).round(4))
