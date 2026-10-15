"""python run_e1c.py --stage D1|T1   (needs E1C_GO=<stage>)   |   --check (code hash)"""
import sys, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from e1c import load_cfg, HERE
ap = argparse.ArgumentParser(); ap.add_argument("--stage"); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
from e1c.stages import code_hash, run
if a.check:
    h = code_hash(); p = HERE / "CODE_HASH.txt"; pin = p.read_text().strip() if p.exists() else None
    print(h, "OK" if h == pin else "MISMATCH"); sys.exit(0 if h == pin else 16)
run(load_cfg(), a.stage)
