"""Tests for the FFT builder (issue #6). Run: python -m pytest data_build"""

import logging
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_fft as bf  # noqa: E402


def monthly(start, values):
    return pd.Series(values, index=pd.date_range(start, periods=len(values), freq="MS"), dtype=float)


def test_committed_fft_files_are_the_complete_quarter_means():
    fft = bf.quarterly(bf.read_monthly(bf.ROOT / "FEDFUNDS.csv"))
    for start in bf.STARTS:
        committed = pd.read_csv(bf.ROOT / f"FFT_{start}-2026.csv", index_col=0, float_precision="round_trip")["FFT"]
        assert committed.index[0] == f"{start}Q1"
        pd.testing.assert_series_equal(fft.loc[committed.index], committed, check_exact=True, check_names=False)
        assert committed.index[-1] == fft.index[-1]


def test_quarter_mean_of_three_months():
    fft = bf.quarterly(monthly("2026-01-01", [3.0, 3.5, 4.0, 1.0, 2.0, 3.0]))
    assert fft.to_dict() == {"2026Q1": 3.5, "2026Q2": 2.0}


def test_trailing_incomplete_quarter_dropped_with_warning(caplog):
    with caplog.at_level(logging.WARNING, logger="build_fft"):
        fft = bf.quarterly(monthly("2026-04-01", [3.63, 3.63, 3.63, 3.63, 3.63, 3.75, 3.70]))
    assert list(fft.index) == ["2026Q2", "2026Q3"]
    assert "dropping incomplete quarter 2026Q4: 1 of 3 months" in caplog.text


def test_leading_incomplete_quarter_dropped_with_warning(caplog):
    with caplog.at_level(logging.WARNING, logger="build_fft"):
        fft = bf.quarterly(monthly("2026-02-01", [1.0, 2.0, 3.0, 3.0, 3.0]))
    assert list(fft.index) == ["2026Q2"]
    assert "dropping incomplete quarter 2026Q1: 2 of 3 months" in caplog.text


def test_missing_month_inside_series_is_an_error():
    m = monthly("2026-01-01", [1.0] * 9)
    with pytest.raises(ValueError, match=r"2026Q2 \(2 of 3 months\)"):
        bf.quarterly(m.drop(pd.Timestamp("2026-05-01")))
    m.loc[pd.Timestamp("2026-05-01")] = float("nan")  # FRED's "." for a missing month
    with pytest.raises(ValueError, match="2026Q2"):
        bf.quarterly(m)


def test_build_writes_both_files_in_the_existing_format(tmp_path):
    src = tmp_path / "FEDFUNDS.csv"
    src.write_text("observation_date,FEDFUNDS\n" + "".join(
        f"{d.date()},{v:.2f}\n" for d, v in monthly("2007-10-01", [4.0] * 15 * 12 + [3.0, 3.1]).items()))
    bf.build(src, tmp_path)
    for start in bf.STARTS:
        lines = (tmp_path / f"FFT_{start}-2026.csv").read_text().splitlines()
        assert lines[0] == ",FFT" and lines[1] == f"{start}Q1,4.0"
        assert lines[-1] == "2022Q3,4.0"  # 2022Q4 has two months only
