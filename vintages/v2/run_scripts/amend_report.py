"""Before -> after table for the amended v2 (before = current vintages/v2 + v1 files; after = a staging/other root)."""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
AFTER = ROOT / "vintages" / sys.argv[1]
BEFORE_V2 = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "vintages" / "v2"
BANKS = ["Manufacturers and Traders Trust Company", "Huntington National Bank", "SouthState Bank"]
SEL = "MAE_Backtesting/output/out_of_sample/selection_oos_scores_8Q.csv"
MUL = "MAE_Backtesting/output/out_of_sample/backtest_multiorigin_8Q.csv"
BET = "Beta_Backtesting/output/out_of_sample/beta_backtest_multiorigin_assessment.csv"


def before(rel):
    a = pd.read_csv(ROOT / rel)
    b = pd.read_csv(BEFORE_V2 / rel) if (BEFORE_V2 / rel).is_file() else a.iloc[:0]
    return pd.concat([a[~a.bank_name.isin(b.bank_name)], b])


def row(sel, mul, bet, bank):
    p = sel[(sel.bank_name == bank) & sel["pick"]].iloc[0]
    m = mul[mul.bank_name == bank]
    return {"champion": f"{p.test_name} | {p['IC/selected lag']} | {p['trend type']}", "theta": round(p.theta, 4), "lambda": round(p["lambda"], 4),
            "mean_mae": round(p.oos_mae, 4), "worst_skill": round(float((m.mae / m.naive_mae).max()), 3),
            "theta_stab": bet[bet.bank_name == bank].rating.iloc[0]}


rows = []
for b in BANKS:
    x = row(before(SEL), before(MUL), before(BET), b)
    y = row(*(pd.read_csv(AFTER / r) for r in (SEL, MUL, BET)), b)
    rows.append({"bank": b[:22], **{k: f"{x[k]} -> {y[k]}" if x[k] != y[k] else f"{x[k]} (same)" for k in x}})
print(pd.DataFrame(rows).set_index("bank").T.to_string())
