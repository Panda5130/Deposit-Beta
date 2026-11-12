"""Tests for the frozen reference limits (issue #8) and the trend freeze; synthetic data only.

    python -m pytest MAE_Backtesting/test_backtest_reference.py -q --tb=line
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import backtest as bt  # noqa: E402


def synthetic_errors(seed, n_origins=30):
    rng = np.random.default_rng(seed)
    rows = [(h, str(pd.Period("2016Q1", "Q") + o), abs(rng.normal(0, 0.05 * h)), abs(rng.normal(0, 0.08 * h)))
            for o in range(n_origins) for h in range(1, bt.REF_HORIZON + 1) if o + h <= n_origins]
    return pd.DataFrame(rows, columns=bt.ERROR_COLUMNS)


@pytest.fixture
def tables():
    return {f"Bank{i}": bt.summarise_errors(synthetic_errors(i), bt.REF_HORIZON) for i in range(6)}


def freeze(tables, directory, trigger="initial"):
    champs = {b: ("EG", "n", "n") for b in tables}
    return bt.freeze_reference(tables, champs, {b: "abc" for b in tables}, "2016Q1", trigger, directory)


def test_reference_reproduces_peer_limits_for_any_horizon(tables, tmp_path):
    csv, _ = freeze(tables, tmp_path)
    ref, meta = bt.load_reference(csv)
    for n in (4, 8, 12):
        peer, _ = bt.assess_multi({b: bt.summarise_errors(synthetic_errors(int(b[-1])), n) for b in tables}, n)
        pd.testing.assert_frame_equal(bt.limits_from_reference(ref, n), peer)
    assert meta["approved_by"] == "" and meta["max_horizon"] == 12 and meta["trigger"] == "initial"


def test_fixed_limits_are_used_by_assess_multi(tables, tmp_path):
    csv, _ = freeze(tables, tmp_path)
    ref, _ = bt.load_reference(csv)
    limits = bt.limits_from_reference(ref, 8)
    one = {"Bank0": bt.summarise_errors(synthetic_errors(0), 8)}  # alone, peers would skip the absolute test
    used, assessment = bt.assess_multi(one, 8, limits)
    pd.testing.assert_frame_equal(used, limits)
    assert assessment.absolute_rating.iloc[0] != "n/a"


def test_versions_never_overwrite(tables, tmp_path):
    first, _ = freeze(tables, tmp_path)
    before = first.read_bytes()
    second, _ = freeze(tables, tmp_path, "annual-review")
    assert first.name == "reference_v1.csv" and second.name == "reference_v2.csv" and first.read_bytes() == before
    with open(first.with_suffix(".json")) as f:
        assert json.load(f)["version"] == 1
    with pytest.raises(FileExistsError):
        with open(first, "x"):
            pass


def test_tampered_reference_is_rejected(tables, tmp_path):
    csv, _ = freeze(tables, tmp_path)
    csv.write_text(csv.read_text().replace("Bank0", "BankX", 1))
    with pytest.raises(ValueError, match="immutable"):
        bt.load_reference(csv)


def test_trigger_required_and_default_needs_approval(tables, tmp_path):
    with pytest.raises(ValueError, match="trigger"):
        freeze(tables, tmp_path, "because")
    csv, js = freeze(tables, tmp_path)
    assert bt.approved_reference(tmp_path) is None  # approved_by empty -> peer limits stay the default
    meta = json.loads(js.read_text())
    meta["approved_by"] = "model owner"
    js.write_text(json.dumps(meta))
    assert bt.approved_reference(tmp_path) == csv


def test_horizon_beyond_reference_rejected(tables, tmp_path):
    csv, _ = freeze(tables, tmp_path)
    with pytest.raises(ValueError, match="covers"):
        bt.limits_from_reference(bt.load_reference(csv)[0], 13)
