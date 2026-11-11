"""Copy outputs into an audit folder with a SHA-256 manifest (never deletes or overwrites).

    python tools/audit_snapshot.py audit/<date>_<tag> FILE_OR_GLOB ...

Paths are relative to the repo root and keep their layout under the audit folder. The
manifest (MANIFEST.sha256.csv: path, sha256, bytes) hashes the copies; the run fails if the
folder already exists.
"""
import csv
import hashlib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "MANIFEST.sha256.csv"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main(argv):
    dest, patterns = ROOT / argv[0], argv[1:]
    if dest.exists():
        print(f"ERROR: {dest} exists; refusing to overwrite an audit copy", file=sys.stderr)
        return 1
    files = sorted({p for pat in patterns for p in ROOT.glob(pat) if p.is_file()})
    rows = []
    for src in files:
        rel = src.relative_to(ROOT)
        out = dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, out)
        h = sha256(out)
        assert h == sha256(src), f"copy mismatch: {rel}"
        rows.append([rel.as_posix(), h, out.stat().st_size])
    with open(dest / MANIFEST, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["path", "sha256", "bytes"])
        w.writerows(rows)
    print(f"{len(rows)} file(s) copied to {dest.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
