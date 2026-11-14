"""Seed vintages/v2_covid caches with the v1 and v2 backtest caches (copies; originals untouched).

Cache entries are keyed on model, data hash and the fitted terms, so an unchanged specification is reused
and only the specifications that gained covid_liq (or changed terms) are re-run. v2 entries override v1.
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
import bank_plots as bp  # noqa: E402

n = 0
for rel in ("MAE_Backtesting/output/out_of_sample/cache", "Beta_Backtesting/output/out_of_sample/cache"):
    for base in (ROOT, bp.DATA_ROOT):  # v1 first, v2 overrides
        src = base / rel
        if src.is_dir() and src != bp.OUTPUT_ROOT / rel:
            (bp.OUTPUT_ROOT / rel).mkdir(parents=True, exist_ok=True)
            for f in src.glob("*.csv"):
                shutil.copy2(f, bp.OUTPUT_ROOT / rel / f.name)
                n += 1
print(n, "cache files copied into", bp.OUTPUT_ROOT)
