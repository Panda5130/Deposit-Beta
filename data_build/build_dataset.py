"""Rebuild the bank deposit-rate datasets from FDIC BankFind, with full pro forma merger adjustment.

Usage:
    python data_build/build_dataset.py [--refresh]

Rate definition (replaces the calendar-year-average / YTD de-cumulation build):
    deposit_rate = 400 * deposit interest expense in the quarter / average deposits
    deposit interest expense in the quarter = EDEPDOMQ + EDEPFORQ   (FDIC quarterly fields, not YTD)
    average deposits = mean of this and the previous quarter-end total deposits (DEP)

Merger adjustment (pro forma):
    Every merger or whole-bank failure acquisition into a target bank (FDIC /history, change codes 2xx)
    is an event. Materiality = predecessor deposits / survivor deposits at the predecessor's last
    pre-merger quarter-end.
    Mode A (>= 1%): the predecessor's deposit interest expense and deposits are added to every
        pre-merger quarter of the survivor; in the merger quarter the predecessor's last reported
        quarterly interest expense is added pro rata to the days before the effective date.
        Predecessors are themselves made pro forma for their own Mode A events (recursively).
    Mode B (< 1%): flagged in the merger quarter only, no adjustment.

FDIC pulls are cached in data_build/raw/; --refresh re-downloads them.
Outputs (repo root):
    consolidated_fdic_quarterly_financials_{2008,2011}-2026.csv                  standalone (no merger adjustment)
    consolidated_fdic_quarterly_financials_{2008,2011}-2026_merger_adjusted.csv  pro forma; model uses rate_pf_clean
    merger_events_used.csv, merger_adjustment_log.md
"""

import argparse
import io
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import requests

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RAW = HERE / "raw"
API = "https://api.fdic.gov/banks"
log = logging.getLogger("build_dataset")

TARGETS = {
    4977: "First Horizon Bank",
    30788: "Glacier Bank",
    6560: "Huntington National Bank",
    17534: "KeyBank National Association",
    588: "Manufacturers and Traders Trust Company",
    3832: "Old National Bank",
    33555: "SouthState Bank",
}
START, END = "20070101", "20261231"      # 2007Q4 is needed for the 2008Q1 average
MATERIALITY = 0.01
FIN_FIELDS = "CERT,REPDTE,DEP,EDEPDOMQ,EDEPFORQ"
HIST_FIELDS = "CERT,ACQ_CERT,OUT_CERT,OUT_INSTNAME,CHANGECODE,CHANGECODE_DESC,EFFDATE"


def get_csv(endpoint, filters, fields):
    params = {"filters": filters, "fields": fields, "limit": 10000, "format": "csv"}
    res = requests.get(f"{API}/{endpoint}", params=params, timeout=60)
    res.raise_for_status()
    return pd.read_csv(io.StringIO(res.text)) if res.text.strip() else pd.DataFrame()


def cached(name, fetch, refresh):
    path = RAW / name
    if path.exists() and not refresh:
        return pd.read_csv(path)
    df = fetch()
    RAW.mkdir(exist_ok=True)
    df.to_csv(path, index=False)
    return df


class Fdic:
    """FDIC financials and history, fetched per cert and cached in data_build/raw/."""

    def __init__(self, refresh):
        self.refresh = refresh
        self.fin = cached("financials_targets.csv", lambda: get_csv(
            "financials", f"CERT:({' OR '.join(map(str, TARGETS))}) AND REPDTE:[{START} TO {END}]", FIN_FIELDS),
            refresh)
        self.hist = cached("history_targets.csv", lambda: self._history(list(TARGETS)), refresh)

    @staticmethod
    def _history(certs):
        f = (f"ACQ_CERT:({' OR '.join(map(str, certs))}) AND CHANGECODE:[200 TO 299] "
             f"AND EFFDATE:[1990-01-01 TO 2026-12-31]")
        return get_csv("history", f, HIST_FIELDS)

    def extend(self, certs):
        """Make sure financials and history are cached for these (predecessor) certs."""
        new = sorted(set(certs) - set(self.fin.CERT))
        if not new:
            return
        log.info("fetching financials and history for %d predecessor certs", len(new))
        fins, hists = [self.fin], [self.hist]
        for i in range(0, len(new), 25):
            chunk = new[i:i + 25]
            fins.append(get_csv("financials", f"CERT:({' OR '.join(map(str, chunk))}) AND REPDTE:[{START} TO {END}]",
                                FIN_FIELDS))
            hists.append(self._history(chunk))
        self.fin = pd.concat(fins, ignore_index=True).drop_duplicates(["CERT", "REPDTE"])
        self.hist = pd.concat(hists, ignore_index=True).drop_duplicates()
        self.fin.to_csv(RAW / "financials_targets.csv", index=False)
        self.hist.to_csv(RAW / "history_targets.csv", index=False)

    def series(self, cert):
        """Quarter-indexed DEP and quarterly deposit interest expense for one cert."""
        f = self.fin[self.fin.CERT == cert].copy()
        f["q"] = pd.to_datetime(f.REPDTE.astype(str)).dt.to_period("Q")
        f["ie"] = f.EDEPDOMQ.fillna(0) + f.EDEPFORQ.fillna(0)
        return f.set_index("q").sort_index()[["DEP", "ie"]].astype(float)

    def events(self, cert):
        h = self.hist[self.hist.ACQ_CERT == cert].copy()
        h["EFFDATE"] = pd.to_datetime(h.EFFDATE.astype(str).str[:10])
        return h[h.EFFDATE >= pd.Timestamp(START)].sort_values("EFFDATE")


def pro_forma(fdic, cert, event_rows, depth=0):
    """Pro forma DEP and deposit IE for `cert`, with all its Mode A predecessors folded in."""
    own = fdic.series(cert)
    pf = own.copy()
    pf["n_pred"] = 0
    ev = fdic.events(cert)
    fdic.extend(ev.OUT_CERT.astype(int).tolist())
    for e in ev.itertuples():
        pred_cert = int(e.OUT_CERT)
        mq = pd.Period(e.EFFDATE, "Q")
        pred = fdic.series(pred_cert)
        pred = pred[pred.index < mq]
        row = {"predecessor_cert": pred_cert, "predecessor_name": e.OUT_INSTNAME, "survivor_cert": cert,
               "effective_date": e.EFFDATE.date(), "merger_quarter": str(mq), "change_code": e.CHANGECODE,
               "change_desc": e.CHANGECODE_DESC, "depth": depth}
        if pred.empty:
            event_rows.append({**row, "mode_applied": "B", "reason_if_skipped": "no predecessor financials"})
            continue
        last_q = pred.index.max()
        pred_dep = pred.loc[last_q, "DEP"]
        surv_dep = own["DEP"].get(last_q, np.nan)
        share = pred_dep / surv_dep if surv_dep else np.nan
        mode = "A" if share >= MATERIALITY else "B"
        event_rows.append({**row, "predecessor_last_quarter": str(last_q),
                           "deposits_at_last_pre_merger_quarter": pred_dep,
                           "survivor_deposits_same_quarter": surv_dep, "pct_of_survivor_deposits": 100 * share,
                           "mode_applied": mode,
                           "reason_if_skipped": "" if mode == "A" else "below 1% materiality"})
        if mode == "B":
            continue
        pred_pf = pro_forma(fdic, pred_cert, event_rows, depth + 1)
        pred_pf = pred_pf[pred_pf.index < mq]
        idx = pf.index.intersection(pred_pf.index)
        pf.loc[idx, ["DEP", "ie"]] += pred_pf.loc[idx, ["DEP", "ie"]]
        pf.loc[idx, "n_pred"] += 1 + pred_pf.loc[idx, "n_pred"]
        if mq in pf.index:
            q_start = mq.start_time
            frac = (e.EFFDATE - q_start).days / ((mq.end_time.normalize() - q_start).days + 1)
            pf.loc[mq, "ie"] += frac * pred_pf.loc[last_q, "ie"]
    return pf


def rate_frame(series):
    """deposit IE, 2-point average deposits and the annualized rate (%) for one bank."""
    out = series.copy()
    out["avg_dep"] = (out["DEP"] + out["DEP"].shift(1)) / 2
    out["rate"] = 400 * out["ie"] / out["avg_dep"]
    return out


def build(refresh):
    fdic = Fdic(refresh)
    rows, events = [], []
    for cert, name in TARGETS.items():
        sa = rate_frame(fdic.series(cert))
        pf = rate_frame(pro_forma(fdic, cert, events))
        ev = pd.DataFrame([e for e in events if e["survivor_cert"] == cert and e["depth"] == 0])
        df = pd.DataFrame({
            "bank_name": name, "cert_number": cert, "quarter": sa.index.to_timestamp(how="end").strftime("%Y-%m-%d"),
            "deposit_interest_expense": sa["ie"], "total_deposits": sa["DEP"], "average_deposits": sa["avg_dep"],
            "deposit_rate": sa["rate"],
            "ie_ann_pf": 4 * pf["ie"], "dep_avg_pf": pf["avg_dep"], "rate_pf": pf["rate"],
            "n_predecessors_included": pf["n_pred"].astype(int)}, index=sa.index)
        df["rate_pf_clean"] = df["rate_pf"]
        df["merger_quarter"] = 0
        df["pct_deposits_acquired_in_quarter"] = 0.0
        df["adjustment_mode"] = "none"
        for e in ev.itertuples():
            q = pd.Period(e.merger_quarter, "Q")
            if q not in df.index:
                continue
            df.loc[q, "merger_quarter"] = 1
            df.loc[q, "pct_deposits_acquired_in_quarter"] += getattr(e, "pct_of_survivor_deposits", 0) or 0
            mode = e.mode_applied.lower()
            if df.loc[q, "adjustment_mode"] != "a":
                df.loc[q, "adjustment_mode"] = mode
        rows.append(df)
    data = pd.concat(rows).reset_index(drop=True)
    data = data[data.quarter >= "2008-01-01"].dropna(subset=["rate_pf"])
    events = pd.DataFrame(events)
    events["survivor_name"] = events.survivor_cert.map(TARGETS)
    return data, events


def validate(data):
    checks = {}
    recon = 100 * data.ie_ann_pf / data.dep_avg_pf
    checks["pro forma rate reconstruction max abs diff"] = float((data.rate_pf - recon).abs().max())
    checks["duplicate cert/quarter keys"] = int(data.duplicated(["cert_number", "quarter"]).sum())
    checks["negative deposit rates"] = int((data.rate_pf < 0).sum())
    checks["missing rate_pf_clean"] = int(data.rate_pf_clean.isna().sum())
    assert checks["pro forma rate reconstruction max abs diff"] < 1e-9
    assert checks["duplicate cert/quarter keys"] == 0
    return checks


def write(data, events, checks):
    standalone = ["bank_name", "cert_number", "quarter", "deposit_interest_expense", "total_deposits",
                  "average_deposits", "deposit_rate"]
    for start in ("2008", "2011"):
        sub = data[data.quarter >= f"{start}-01-01"]
        sub[standalone].to_csv(ROOT / f"consolidated_fdic_quarterly_financials_{start}-2026.csv", index=False)
        sub.to_csv(ROOT / f"consolidated_fdic_quarterly_financials_{start}-2026_merger_adjusted.csv", index=False)
    cols = ["predecessor_cert", "predecessor_name", "survivor_cert", "survivor_name", "effective_date",
            "merger_quarter", "change_code", "change_desc", "predecessor_last_quarter",
            "deposits_at_last_pre_merger_quarter", "survivor_deposits_same_quarter", "pct_of_survivor_deposits",
            "mode_applied", "reason_if_skipped", "depth"]
    events.reindex(columns=cols).to_csv(ROOT / "merger_events_used.csv", index=False)

    top = events[events.depth == 0]
    in_main = top[top.merger_quarter >= "2011Q1"]
    lines = [
        "# Merger Adjustment Log", "",
        "Generated by `data_build/build_dataset.py`.", "",
        "## Method",
        "- Deposit rate = 400 x quarterly deposit interest expense (FDIC `EDEPDOMQ` + `EDEPFORQ`) / "
        "average of current and prior quarter-end total deposits (`DEP`).",
        "- Mode A (predecessor deposits >= 1% of survivor deposits at the last pre-merger quarter): predecessor "
        "deposit interest expense and deposits added to every pre-merger quarter; merger quarter gets the "
        "predecessor's last quarterly interest expense pro rata to the days before the effective date. "
        "Applied recursively to predecessors' own Mode A events.",
        "- Mode B (< 1%): flagged in the merger quarter, no adjustment, rows kept in `rate_pf_clean`.", "",
        "## Execution statistics",
        f"- Bank-quarter records: {len(data)} (2008Q1 to {data.quarter.max()})",
        f"- Events into the 7 target banks since 2007: {len(top)} "
        f"(Mode A {int((top.mode_applied == 'A').sum())}, Mode B {int((top.mode_applied == 'B').sum())})",
        f"- Of which effective 2011Q1 or later: {len(in_main)} "
        f"(Mode A {int((in_main.mode_applied == 'A').sum())}, Mode B {int((in_main.mode_applied == 'B').sum())})",
        f"- Predecessor-of-predecessor events folded in (depth >= 1): {int((events.depth > 0).sum())}", "",
        "## Validations",
        *[f"- {k}: {v}" for k, v in checks.items()], "",
    ]
    (ROOT / "merger_adjustment_log.md").write_text("\n".join(lines), encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Rebuild FDIC deposit-rate datasets with pro forma merger adjustment.")
    parser.add_argument("--refresh", action="store_true", help="re-download FDIC data instead of using data_build/raw/")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
    data, events = build(args.refresh)
    checks = validate(data)
    write(data, events, checks)
    log.info("wrote %d rows; %d events; checks %s", len(data), len(events), checks)
    return 0


if __name__ == "__main__":
    sys.exit(main())
