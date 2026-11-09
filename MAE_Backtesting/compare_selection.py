"""Side-by-side table of each bank's in-sample champion and its out-of-sample pick (OI-9, #1).

The out-of-sample pick (over the original models and their asymmetric variants) is the
default champion (backtest.DEFAULT_SELECT); the in-sample champion is the optional rule.
Reads the outputs of four runs (run them first; all from the project folder):
    python MAE_Backtesting/run_backtest.py --horizon 8Q --bank-name All --select in-sample --first-origin 2016Q1
    python MAE_Backtesting/run_backtest.py --horizon 8Q --bank-name All --select out-of-sample
    python Beta_Backtesting/run_beta_backtest.py --select in-sample --realized
    python Beta_Backtesting/run_beta_backtest.py --select out-of-sample --realized

Usage:
    python MAE_Backtesting/compare_selection.py [--horizon 8Q]

Writes MAE_Backtesting/output/out_of_sample/selection_comparison_<N>Q.csv (one row per bank:
model, asymmetric flag, parameter count, in-sample MAE, many-origin mean h-step MAE with its
SE, lambda (lambda+-), theta (theta+-), MAE backtest rating, theta-stability rating and
realized-beta rating (when that run exists), for the champion and for the pick; the
lowest-scoring admissible model is added as a sensitivity) and selection_comparison_<N>Q.png.
A run whose model does not match the selection table stops the script, so stale outputs are
not mixed.
"""

import argparse
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import backtest as bt
import run_backtest as rb

MAE_OUT = bt.HERE / "output"
BETA_OUT = bt.ROOT / "Beta_Backtesting" / "output"
KEY = " | ".join


def model_of(row):
    return KEY(str(row[k]).strip() for k in bt.SPEC_KEYS)


def ratings(path, label):
    """{bank: (model, rating)} from an assessment CSV (empty when the run has not been made)."""
    if not path.exists():
        return {}, label
    t = pd.read_csv(path)
    return {r.bank_name: (r.model, r.rating) for r in t.itertuples()}, label


def lookup(table, bank, model, required=True):
    found, label = table
    if not found and not required:
        return "not run"
    if bank not in found:
        raise ValueError(f"{label}: no row for {bank}")
    if found[bank][0] != model:
        raise ValueError(f"{label}: {bank} was run with {found[bank][0]!r}, expected {model!r}; rerun it")
    return found[bank][1]


def compare(horizon):
    oos_dir, in_dir = bt.output_dir("out-of-sample"), bt.output_dir("in-sample")
    b_oos, b_in = bt.output_dir("out-of-sample", "Beta"), bt.output_dir("in-sample", "Beta")
    scores = pd.read_csv(oos_dir / f"selection_oos_scores_{horizon}Q.csv")
    summary, _ = bt.load_candidates()
    mae_in = ratings(in_dir / f"backtest_multiorigin_assessment_{horizon}Q.csv", "MAE backtest (in-sample)")
    mae_oos = ratings(oos_dir / f"backtest_multiorigin_assessment_{horizon}Q.csv", "MAE backtest (out-of-sample)")
    beta_in = ratings(b_in / "beta_backtest_multiorigin_assessment.csv", "theta stability (in-sample)")
    beta_oos = ratings(b_oos / "beta_backtest_multiorigin_assessment.csv", "theta stability (out-of-sample)")
    real_in = ratings(b_in / f"realized_beta_assessment_{horizon}Q.csv", "realized beta (in-sample)")
    real_oos = ratings(b_oos / f"realized_beta_assessment_{horizon}Q.csv", "realized beta (out-of-sample)")
    rows = []
    for bank, s in scores.groupby("bank_name", sort=False):
        s = s.assign(model=s.apply(model_of, axis=1))
        champ = s[s.model == KEY(bt.select_model(summary, bank))].iloc[0]
        pick, best = s[s.pick].iloc[0], s[s.best_oos].iloc[0]
        row = {"bank_name": bank, "same_model": champ.model == pick.model,
               "same_ecm": champ.terms == pick.terms, "one_se_threshold": pick.one_se_threshold}
        for tag, r, mae, beta, real in [("champion", champ, mae_in, beta_in, real_in),
                                        ("oos_pick", pick, mae_oos, beta_oos, real_oos)]:
            row.update({f"{tag}_model": r.model, f"{tag}_asymmetric": bool(r.asymmetric),
                        f"{tag}_n_params": r.n_params, f"{tag}_in_sample_mae": r.in_sample_mae,
                        f"{tag}_oos_mae": r.oos_mae, f"{tag}_oos_se": r.oos_se,
                        f"{tag}_theta": r.theta, f"{tag}_theta_pos": r.theta_pos, f"{tag}_theta_neg": r.theta_neg,
                        f"{tag}_lambda": r["lambda"], f"{tag}_lambda_pos": r.lambda_pos,
                        f"{tag}_lambda_neg": r.lambda_neg, f"{tag}_mae_rating": lookup(mae, bank, r.model),
                        f"{tag}_beta_rating": lookup(beta, bank, r.model),
                        f"{tag}_realized_beta_rating": lookup(real, bank, r.model, required=False)})
        row.update({"best_oos_model": best.model, "best_oos_n_params": best.n_params, "best_oos_mae": best.oos_mae,
                    "best_oos_theta": best.theta})
        rows.append(row)
    return pd.DataFrame(rows)


def plot(table, path, horizon):
    """Many-origin mean h-step MAE (+/- 1 SE) of champion and pick, with the one-SE threshold."""
    y = np.arange(len(table))
    fig, ax = plt.subplots(figsize=(10, 0.8 * len(table) + 1.5))
    for offset, tag, color, label in [(-0.2, "champion", "#1f4e79", "In-sample champion"),
                                      (0.2, "oos_pick", "#e08a2e", "Out-of-sample pick")]:
        ax.barh(y + offset, table[f"{tag}_oos_mae"], height=0.38, xerr=table[f"{tag}_oos_se"], color=color,
                ecolor="#555555", capsize=3, label=label + " (+/- 1 SE)")
        for yi, v, n in zip(y + offset, table[f"{tag}_oos_mae"], table[f"{tag}_n_params"]):
            ax.text(0.005, yi, f"{v:.3f} ({n} params)", va="center", fontsize=7, color="white")
    ax.scatter(table["one_se_threshold"], y, marker="|", s=400, color="#c62828", zorder=3,
               label="One-SE threshold (best + SE of best)")
    ax.set_yticks(y, table["bank_name"])
    ax.invert_yaxis()
    ax.set_xlabel(f"Mean many-start-date h-step MAE, h = 1..{horizon} (pp), origins from 2016Q1")
    ax.set_title("In-sample champion vs out-of-sample pick (original and asymmetric candidates)", fontsize=10)
    ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=3)
    ax.grid(True, axis="x", alpha=0.3)
    ax.set_axisbelow(True)
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def main(argv=None):
    parser = argparse.ArgumentParser(description="In-sample champion vs out-of-sample pick, per bank.")
    parser.add_argument("--horizon", default="8Q")
    args = parser.parse_args(argv)
    try:
        horizon = rb.parse_horizon(args.horizon)
        table = compare(horizon)
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    out = bt.output_dir("out-of-sample")
    table.to_csv(out / f"selection_comparison_{horizon}Q.csv", index=False)
    plot(table, out / f"selection_comparison_{horizon}Q.png", horizon)
    print(f"wrote {out / f'selection_comparison_{horizon}Q.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
