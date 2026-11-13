"""bank_plots.vfile: per-file fallback from a vintage folder to the v1 (repo root) file."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bank_plots as bp  # noqa: E402


def test_fallback_order(tmp_path, monkeypatch):
    new, old = tmp_path / "new", tmp_path / "old"
    new.mkdir(), old.mkdir()
    (old / "a.csv").write_text("old"), (old / "b.csv").write_text("old"), (new / "b.csv").write_text("new")
    monkeypatch.setattr(bp, "VINTAGE_CHAIN", [new, old])
    monkeypatch.setattr(bp, "OUTPUT_ROOT", new)
    assert bp.vfile("b.csv") == new / "b.csv"      # present in the newest vintage
    assert bp.vfile("a.csv") == old / "a.csv"      # absent there: falls back to the older file
    assert bp.vfile("c.csv") == new / "c.csv"      # absent everywhere: the write location


def test_candidates_resolve_to_existing_files():
    for key, path in bp.CANDIDATE_FILES.items():
        assert Path(path).is_file(), key
