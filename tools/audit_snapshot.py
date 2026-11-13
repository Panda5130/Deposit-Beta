"""Write an audit manifest for files that are committed in git (no copies are made).

    python tools/audit_snapshot.py audit/<date>_<tag>.manifest.csv [--commit REV] FILE_OR_GLOB ...

Paths are relative to the repo root. Each row is path, sha256 of the file's content in git at REV
(default HEAD, which must already hold the files: commit first), baseline_commit. The verify check
`audit_*_manifest` re-reads every row from git. The run fails if the manifest already exists.
"""
import csv
import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(argv):
    commit = "HEAD"
    if "--commit" in argv:
        i = argv.index("--commit")
        commit = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    dest, patterns = ROOT / argv[0], argv[1:]
    if dest.exists():
        print(f"ERROR: {dest} exists; refusing to overwrite an audit manifest", file=sys.stderr)
        return 1
    full = subprocess.check_output(["git", "rev-parse", commit], cwd=ROOT, text=True).strip()
    files = sorted({p for pat in patterns for p in ROOT.glob(pat) if p.is_file()})
    rows = []
    for src in files:
        rel = src.relative_to(ROOT).as_posix()
        r = subprocess.run(["git", "show", f"{full}:{rel}"], cwd=ROOT, capture_output=True)
        if r.returncode:
            print(f"ERROR: {rel} is not in git at {commit}", file=sys.stderr)
            return 1
        rows.append([rel, hashlib.sha256(r.stdout).hexdigest(), full[:7]])
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["path", "sha256", "baseline_commit"])
        w.writerows(rows)
    print(f"{len(rows)} file(s) listed in {dest.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
