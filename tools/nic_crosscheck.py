"""NIC Transformations cross-check (issue #20): classify every NIC event into a target bank or a merger-tree predecessor.

    python tools/nic_crosscheck.py [-o events.csv] [--no-materiality]

Inputs (git-ignored download cache data_build/raw/nic/): CSV_TRANSFORMATIONS.CSV, CSV_ATTRIBUTES_ACTIVE.CSV and
CSV_ATTRIBUTES_CLOSED.CSV (RSSD -> ID_FDIC_CERT), and fdic_institutions.csv (public FDIC API: CERT, FED_RSSD),
which fills the RSSDs the NIC attributes leave without a cert (most closed banks).

Classes of an event whose successor is a survivor in the tree (targets + Mode A predecessors):
  covered                 predecessor already in /history events, the supplementary file or the waivers
  deposit transfer        predecessor has an FDIC cert different from the survivor's; materiality = predecessor
                          deposits at the quarter before / survivor deposits (Mode A >= 1%, else Mode B flag)
  same charter / non-depository   same cert, or the predecessor has no FDIC cert and is a non-bank entity type
  unresolved              predecessor in neither source, or a trust/foreign/agency entity that may hold deposits
Plus: survivor not in tree: a tree member (target or predecessor) whose successor is not a survivor in the tree.
"""
import argparse
import io
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
NIC = ROOT / "data_build" / "raw" / "nic"
MAY_HOLD_DEPOSITS = {"NTC", "IBK", "FBK", "AGB", "AGR", "EDG", "ECO", "FBO", "IFB", "IBR", "BRC"}  # trust, foreign, agency types


def load_map(nic=NIC):
    """(attributes frame indexed by RSSD with cert + entity type, cert -> set of RSSDs)."""
    cols = ["#ID_RSSD", "ID_FDIC_CERT", "NM_LGL", "ENTITY_TYPE"]
    a = pd.concat([pd.read_csv(nic / f"CSV_ATTRIBUTES_{k}.CSV", usecols=cols, dtype=str) for k in ("ACTIVE", "CLOSED")])
    a = a.rename(columns={"#ID_RSSD": "rssd"}).assign(rssd=lambda d: pd.to_numeric(d.rssd))
    a["cert"] = pd.to_numeric(a.ID_FDIC_CERT, errors="coerce").fillna(0).astype(int)
    pairs = set(zip(a.rssd, a.cert)) - {(r, 0) for r in a.rssd}
    a = a.drop_duplicates("rssd").set_index("rssd")
    inst = nic / "fdic_institutions.csv"
    if inst.is_file():  # one RSSD can belong to several certs over time (a successor charter reuses it)
        f = pd.read_csv(inst).dropna(subset=["FED_RSSD"])
        pairs |= {(int(r), int(c)) for c, r in zip(f.CERT, f.FED_RSSD) if r > 0}
    certs, c2r = {}, {}
    for r, c in pairs:
        certs.setdefault(r, set()).add(c)
        c2r.setdefault(c, set()).add(r)
    return a, certs, c2r


def classify(nic=NIC):
    from data_build import build_dataset as bd
    a, certs, c2r = load_map(nic)
    used = pd.read_csv(ROOT / "merger_events_used_v2.csv")
    sup = pd.read_csv(ROOT / "data_build" / "raw" / "supplementary_transfer_events.csv")
    wf = ROOT / "data_build" / "raw" / "nic_transfer_waivers.csv"
    waived = set(pd.to_numeric(pd.read_csv(wf).predecessor_rssd, errors="coerce").dropna().astype(int)) if wf.exists() else set()
    surv = set(bd.TARGETS) | set(used.loc[used.mode_applied == "A", "predecessor_cert"].astype(int)) | set(sup.survivor_cert.astype(int))
    tree = surv | set(used.predecessor_cert.astype(int)) | set(sup.predecessor_cert.astype(int))
    srssd = {r for c in surv for r in c2r.get(c, ())}
    trssd = {r for c in tree for r in c2r.get(c, ())}
    covered = ({r for c in used.predecessor_cert.astype(int) for r in c2r.get(c, ())}
               | set(sup.predecessor_rssd.dropna().astype(int)) | {r for c in sup.predecessor_cert.astype(int) for r in c2r.get(c, ())}
               | waived)
    t = pd.read_csv(nic / "CSV_TRANSFORMATIONS.CSV", dtype=str).rename(
        columns={"#ID_RSSD_PREDECESSOR": "pred_rssd", "ID_RSSD_SUCCESSOR": "succ_rssd"})
    t["date"] = pd.to_datetime(t.DT_TRANS, format="%Y%m%d", errors="coerce")
    t[["pred_rssd", "succ_rssd"]] = t[["pred_rssd", "succ_rssd"]].apply(pd.to_numeric)
    t = t[t.date >= pd.Timestamp(bd.START)]
    t["pred_certs"] = t.pred_rssd.map(lambda r: certs.get(r, set()))
    t["pred_cert"] = t.pred_certs.map(lambda c: max(c) if c else 0)
    t["succ_cert"] = t.succ_rssd.map(lambda r: max(surv & certs.get(r, set()), default=max(certs.get(r, {0}))))
    t["pred_name"] = t.pred_rssd.map(a.NM_LGL).str.strip()
    t["pred_type"] = t.pred_rssd.map(a.ENTITY_TYPE)
    e = t[t.succ_rssd.isin(srssd)].copy()

    def cls(r):
        if r.pred_rssd in covered or r.pred_certs & set(used.predecessor_cert.astype(int)):
            return "covered"
        if r.pred_cert > 0:
            return "same charter / non-depository" if r.succ_cert in r.pred_certs else "deposit transfer"
        if r.pred_rssd not in a.index:
            return "unresolved"
        return "unresolved" if r.pred_type in MAY_HOLD_DEPOSITS else "same charter / non-depository"
    e["class"] = e.apply(cls, axis=1)
    n = t[t.pred_rssd.isin(trssd) & ~t.succ_rssd.isin(srssd)].copy()
    n["class"] = "survivor not in tree"
    return e, n, surv


def deposits(cert, date):
    """(DEP in $000, REPDTE) of the latest FDIC report of cert before date (within 8 quarters), else (NaN, None)."""
    import requests
    d0 = (pd.Timestamp(date) - pd.DateOffset(years=2)).strftime("%Y%m%d")
    d1 = (pd.Timestamp(date) - pd.Timedelta(days=1)).strftime("%Y%m%d")
    r = requests.get("https://api.fdic.gov/banks/financials", params={
        "filters": f"CERT:{cert} AND REPDTE:[{d0} TO {d1}]", "fields": "CERT,REPDTE,DEP", "sort_by": "REPDTE",
        "sort_order": "DESC", "limit": 1, "format": "csv"}, timeout=60)
    d = pd.read_csv(io.StringIO(r.text)) if r.ok and r.text.strip() else pd.DataFrame()
    return (float(d.DEP.iloc[0]), int(d.REPDTE.iloc[0])) if len(d) and "DEP" in d else (float("nan"), None)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--output")
    ap.add_argument("--no-materiality", action="store_true")
    args = ap.parse_args(argv)
    e, n, _ = classify()
    e["pred_dep"] = e["succ_dep"] = e["share_of_survivor"] = float("nan")
    if not args.no_materiality:
        for i, r in e[e["class"] == "deposit transfer"].iterrows():
            (e.loc[i, "pred_dep"], e.loc[i, "pred_repdte"]), (e.loc[i, "succ_dep"], _) = deposits(r.pred_cert, r.date), deposits(r.succ_cert, r.date)
        e["share_of_survivor"] = e.pred_dep / e.succ_dep
    print(e["class"].value_counts().to_string(), f"\nsurvivor not in tree: {len(n)} events", sep="\n")
    if args.output:
        pd.concat([e, n]).to_csv(args.output, index=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
