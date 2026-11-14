"""Harvest v2 outputs from the scratch run copy into <repo>/vintages/v2/ (new files only, never overwrite).

1. Upstream candidate files (merged: 5 banks carried over + M&T/ON re-run) -> vintages/v2/<name>.
2. Unpruned estimation files (merged the same way) -> vintages/v2/<name>.
3. Every other file in the copy that is new or differs from the repo -> vintages/v2/<same relative path>.
"""
import hashlib
import shutil
import sys
from pathlib import Path

import pandas as pd

RUN = Path(sys.argv[1])
REPO = Path(sys.argv[2])
DEST = REPO / "vintages" / "v2"
BANKS = ["Manufacturers and Traders Trust Company", "Old National Bank"]
UPSTREAM = [p.name for p in (RUN / "up_v2").glob("*.csv")]
SKIP_TOP = {"up_v1", "up_v2", "up_v2_unpruned", "run_upstream.py", "run_downstream.py", "down.log", "up_v1.log",
            "up_v2.log", "deps2_v1.csv", "deps2_v2.csv", "__pycache__", "vintages"}
DATA = {f"consolidated_fdic_quarterly_financials_{s}-2026_merger_adjusted.csv" for s in ("2008", "2011")}


def h(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def put(src, rel):
    out = DEST / rel
    if out.exists():
        raise FileExistsError(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, out)


def merged(orig, new):
    o, n = pd.read_csv(orig), pd.read_csv(new)
    order = {b: i for i, b in enumerate(dict.fromkeys(o.bank_name))}
    m = pd.concat([o[~o.bank_name.isin(BANKS)], n], ignore_index=True)
    return m.iloc[m.bank_name.map(order).argsort(kind="stable")]


if DEST.exists():
    sys.exit(f"{DEST} exists; refusing to overwrite")
n = 0
for name in UPSTREAM:
    put(RUN / name, name)                      # already merged into the copy root
    n += 1
for p in (RUN / "up_v2_unpruned").glob("*.csv"):
    if p.name.startswith("unused"):
        continue
    DEST.mkdir(parents=True, exist_ok=True)
    merged(REPO / p.name, p).to_csv(DEST / p.name, index=False)
    n += 1
for p in RUN.rglob("*"):
    rel = p.relative_to(RUN)
    if not p.is_file() or rel.parts[0] in SKIP_TOP or rel.name in UPSTREAM or rel.name in DATA \
            or "__pycache__" in rel.parts or p.suffix in (".pyc", ".py", ".md", ".ipynb"):
        continue
    q = REPO / rel
    if q.exists() and h(p) == h(q):
        continue
    put(p, rel)
    n += 1
print(f"{n} files -> {DEST}")
