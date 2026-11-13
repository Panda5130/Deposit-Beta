"""Tests for supplementary deposit transfers in the pro forma merger adjustment (issue #20).

Run: python -m pytest data_build -q
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_dataset as bd  # noqa: E402

QUARTERS = ["20140331", "20140630", "20140930", "20141231", "20150331", "20150630", "20150930"]


def fake_fdic(fin_rows, hist_rows, supp_rows):
    """An Fdic with in-memory financials / history / supplementary events and no network."""
    f = bd.Fdic.__new__(bd.Fdic)
    f.refresh = False
    f.fin = pd.DataFrame(fin_rows, columns=["CERT", "REPDTE", "DEP", "EDEPDOMQ", "EDEPFORQ"])
    f.hist = pd.DataFrame(hist_rows, columns=["ACQ_CERT", "OUT_CERT", "OUT_INSTNAME", "CHANGECODE",
                                              "CHANGECODE_DESC", "EFFDATE"])
    f.supp = pd.DataFrame(supp_rows, columns=bd.SUPP_COLUMNS + ["predecessor_name"])
    f.extend = lambda certs: None
    return f


def bank(cert, dep, ie, quarters=QUARTERS):
    return [(cert, q, dep, ie, 0.0) for q in quarters]


def supp(pred, surv, date, share, name="pred"):
    return (pred, surv, date, share, "NIC test", "", name)


def test_partial_transfer_scales_deposits_and_interest_expense():
    fdic = fake_fdic(bank(1, 1000.0, 10.0) + bank(2, 200.0, 4.0, QUARTERS[:5]), [],
                     [supp(2, 1, "2015-05-16", 0.25)])
    events = []
    pf = bd.pro_forma(fdic, 1, events)
    pre = pf.index < pd.Period("2015Q2", "Q")
    assert (pf.loc[pre, "DEP"] == 1000 + 0.25 * 200).all()
    assert (pf.loc[pre, "ie"] == 10 + 0.25 * 4).all()
    frac = (pd.Timestamp("2015-05-16") - pd.Timestamp("2015-04-01")).days / 91
    assert pf.loc[pd.Period("2015Q2", "Q"), "ie"] == pytest.approx(10 + frac * 0.25 * 4)
    assert pf.loc[pd.Period("2015Q3", "Q"), "DEP"] == 1000            # after the transfer: own only
    (row,) = events
    assert row["mode_applied"] == "A" and row["source"] == "NIC test" and row["transfer_share"] == 0.25
    assert row["deposits_at_last_pre_merger_quarter"] == 50.0           # transferred deposits
    assert row["pct_of_survivor_deposits"] == pytest.approx(5.0)       # materiality on transferred share


def test_partial_share_can_fall_below_materiality():
    fdic = fake_fdic(bank(1, 1000.0, 10.0) + bank(2, 40.0, 1.0, QUARTERS[:5]), [],
                     [supp(2, 1, "2015-05-16", 0.2)])                   # 4% of survivor whole, 0.8% transferred
    events = []
    pf = bd.pro_forma(fdic, 1, events)
    assert events[0]["mode_applied"] == "B" and (pf.DEP == 1000).all()


def test_recursive_voyager_anchor_old_national():
    # Old National (3832) <- Anchor (8868) by /history 2015Q3; Anchor <- Voyager (32173) supplementary 2015Q1
    fin = bank(3832, 10000.0, 20.0) + bank(8868, 1300.0, 5.0, QUARTERS[:6]) + bank(32173, 320.0, 2.0, QUARTERS[:4])
    hist = [(3832, 8868, "Anchor", 223, "Merger", "2015-08-01T00:00:00")]
    fdic = fake_fdic(fin, hist, [supp(32173, 8868, "2015-02-15", 1.0, "Voyager")])
    events = []
    pf = bd.pro_forma(fdic, 3832, events)
    q = lambda s: pd.Period(s, "Q")  # noqa: E731
    assert pf.loc[q("2014Q4"), "DEP"] == 10000 + 1300 + 320              # Voyager folded in before its transfer
    assert pf.loc[q("2015Q2"), "DEP"] == 10000 + 1300                    # after Voyager, before Anchor
    assert pf.loc[q("2014Q4"), "n_pred"] == 2
    voy = next(e for e in events if e["predecessor_cert"] == 32173)
    assert voy["depth"] == 1 and voy["survivor_cert"] == 8868 and voy["mode_applied"] == "A"
    assert voy["source"] == "NIC test"
    anc = next(e for e in events if e["predecessor_cert"] == 8868)
    assert anc["depth"] == 0 and anc["source"] == bd.HISTORY_SOURCE and anc["transfer_share"] == 1.0


def test_southbank_style_small_transfer_is_mode_b_flag_only():
    fdic = fake_fdic(bank(33555, 3137585.0, 1369.0) + bank(33848, 16978.0, 34.0, QUARTERS[:6]), [],
                     [supp(33848, 33555, "2015-07-25", 1.0, "SouthBank")])
    events = []
    pf = bd.pro_forma(fdic, 33555, events)
    assert events[0]["mode_applied"] == "B" and events[0]["pct_of_survivor_deposits"] == pytest.approx(0.5411, 1e-3)
    assert (pf.DEP == 3137585.0).all() and (pf.n_pred == 0).all()


def test_supplementary_file_validates(tmp_path):
    s = bd.load_supplementary(bd.SUPPLEMENTARY)
    assert set(s.predecessor_cert) == {680, 32173, 33848}
    bad = tmp_path / "bad.csv"
    s.assign(transfer_share=1.5).to_csv(bad, index=False)
    with pytest.raises(ValueError):
        bd.load_supplementary(bad)
    s.drop(columns="source").to_csv(bad, index=False)
    with pytest.raises(ValueError):
        bd.load_supplementary(bad)


REAL = bd.RAW / "financials_targets.csv"


@pytest.mark.skipif(not REAL.exists() or not {680, 32173, 33848} <= set(pd.read_csv(REAL).CERT),
                    reason="cached FDIC financials for the supplementary certs not present")
def test_real_events_modes_against_cached_fdic_data():
    fdic = bd.Fdic(refresh=False)
    fdic.extend = lambda certs: None
    rows = {}
    for cert in (588, 3832, 33555):
        ev = []
        bd.pro_forma(fdic, cert, ev)
        rows.update({(e["predecessor_cert"], e["survivor_cert"]): e for e in ev})
    wtc, voy, sb = rows[(680, 588)], rows[(32173, 8868)], rows[(33848, 33555)]
    assert wtc["mode_applied"] == "A" and wtc["pct_of_survivor_deposits"] == pytest.approx(13.08, abs=0.01)
    assert voy["mode_applied"] == "A" and voy["depth"] == 1 and voy["pct_of_survivor_deposits"] == pytest.approx(23.68, abs=0.01)
    assert sb["mode_applied"] == "B" and sb["pct_of_survivor_deposits"] < 1
