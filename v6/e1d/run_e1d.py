"""python run_e1d.py --stage D1-E1d (supervisor; needs E1D_GO=<stage>) | --check (code hash) | --eligibility <stage>
--child <stage> is launched only by the supervisor."""
import sys, argparse, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from e1d import load_cfg, HERE
ap = argparse.ArgumentParser(); ap.add_argument("--stage"); ap.add_argument("--child"); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
from e1d.stages import code_hash
if a.check:
    h = code_hash(); p = HERE / "CODE_HASH.txt"; pin = p.read_text().strip() if p.exists() else None
    print(h, "OK" if h == pin else "MISMATCH"); sys.exit(0 if h == pin else 16)
if a.child:
    from e1d.stages import child_main; child_main(load_cfg(), a.child); sys.exit(0)
from e1d.supervisor import supervise
supervise(load_cfg(), a.stage)
