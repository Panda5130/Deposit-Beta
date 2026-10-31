"""Build the quarterly FFT regressor files from FRED FEDFUNDS (OI-21, issue #6).

Usage:
    python data_build/build_fft.py [--refresh] [--fedfunds FILE] [--out-dir DIR]

FFT for a calendar quarter = mean of the three monthly FEDFUNDS observations (effective
federal funds rate, %). Only complete quarters (all three months present) are written:
a trailing incomplete quarter is dropped with a warning naming it; an incomplete quarter
inside the series (a missing month) is an error, since dropping it would leave a hole.

--refresh re-downloads FEDFUNDS from FRED (fredgraph.csv, no API key) into the FEDFUNDS
file first; otherwise the committed FEDFUNDS.csv is used.

Outputs (repo root, same format as before: index like 2011Q1, column FFT):
    FFT_2008-2026.csv   2008Q1 to the last complete quarter
    FFT_2011-2026.csv   2011Q1 to the last complete quarter
"""

import argparse
import io
import logging
import sys
from pathlib import Path

import pandas as pd
import requests

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=FEDFUNDS"
SERIES = "FEDFUNDS"
STARTS = ("2008", "2011")
log = logging.getLogger("build_fft")


def download(path):
    res = requests.get(FRED_URL, timeout=60)
    res.raise_for_status()
    monthly = read_monthly(io.StringIO(res.text))  # fail before overwriting if the download is not usable
    Path(path).write_text(res.text, encoding="utf-8")
    log.info("downloaded %s: %d months to %s", SERIES, len(monthly), monthly.index[-1].date())


def read_monthly(path):
    """FEDFUNDS as a month-start-indexed float Series (round-trip float parsing)."""
    df = pd.read_csv(path, na_values=["."], float_precision="round_trip")
    date_col = next(c for c in df.columns if c.lower() in ("observation_date", "date"))
    s = df.set_index(pd.to_datetime(df[date_col]))[SERIES].astype(float)
    if s.index.duplicated().any():
        raise ValueError(f"duplicate months in {SERIES}: {sorted(set(s.index[s.index.duplicated()].date))}")
    return s.sort_index()


def quarterly(monthly):
    """Quarterly mean over complete quarters only.

    Incomplete quarters at either end (e.g. the current quarter) are dropped with a warning;
    an incomplete or missing quarter between complete ones raises ValueError.
    """
    q = monthly.index.to_period("Q")
    n = monthly.notna().groupby(q).sum()
    complete = n.index[n == 3]
    if complete.empty:
        raise ValueError(f"{SERIES} has no complete quarter")
    edge = [p for p in n.index[n < 3] if p < complete.min() or p > complete.max()]
    for p in edge:
        log.warning("dropping incomplete quarter %s: %d of 3 months of %s", p, int(n[p]), SERIES)
    gaps = [p for p in pd.period_range(complete.min(), complete.max(), freq="Q") if p not in complete]
    if gaps:
        raise ValueError(f"incomplete quarter(s) inside the {SERIES} series: "
                         + ", ".join(f"{p} ({int(n.get(p, 0))} of 3 months)" for p in gaps))
    out = monthly.groupby(q).mean().loc[complete].rename("FFT").rename_axis(None)
    out.index = out.index.astype(str)
    return out


def build(fedfunds, out_dir):
    fft = quarterly(read_monthly(fedfunds))
    written = {}
    for start in STARTS:
        path = Path(out_dir) / f"FFT_{start}-2026.csv"
        sub = fft[fft.index >= f"{start}Q1"]
        sub.to_frame().to_csv(path)
        written[path.name] = sub
        log.info("wrote %s: %s to %s (%d quarters)", path.name, sub.index[0], sub.index[-1], len(sub))
    return written


def main(argv=None):
    parser = argparse.ArgumentParser(description="Average FRED FEDFUNDS to complete calendar quarters.")
    parser.add_argument("--refresh", action="store_true", help="re-download FEDFUNDS from FRED first")
    parser.add_argument("--fedfunds", default=ROOT / "FEDFUNDS.csv", help="monthly FEDFUNDS CSV")
    parser.add_argument("--out-dir", default=ROOT, help="folder for FFT_2008-2026.csv and FFT_2011-2026.csv")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
    if args.refresh:
        download(args.fedfunds)
    build(args.fedfunds, args.out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
