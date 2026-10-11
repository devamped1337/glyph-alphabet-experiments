#!/usr/bin/env python3
"""Code hash = sha256 over the sorted (path, sha256) list of all E1b code + config files. --check refuses to run
if CODE_HASH.txt does not match (code changed after the hash was recorded)."""
import hashlib, sys
from pathlib import Path
R = Path(__file__).resolve().parent.parent
FILES = sorted([*R.glob("e1b/*.py"), R / "run_e1b.py", R / "run.sh", R / "config_e1b.json", R / "kaggle/e1b_kaggle.py",
                R / "tools/code_hash.py", R.parent / "checks/validate_v6.py"])
def h():
    s = hashlib.sha256()
    for f in FILES: s.update(f"{f.relative_to(R.parent)}:{hashlib.sha256(f.read_bytes()).hexdigest()}\n".encode())
    return s.hexdigest()
if __name__ == "__main__":
    cur = h()
    if "--check" in sys.argv:
        rec = (R / "CODE_HASH.txt").read_text().split()[0]
        if rec != cur: print(f"CODE_HASH mismatch: recorded {rec} != current {cur}"); sys.exit(2)
        print("code hash OK", cur)
    else:
        (R / "CODE_HASH.txt").write_text(cur + "\n"); print(cur)
