"""python run_e1c.py --stage D1|T1   (supervisor; needs E1C_GO=<stage>)   |   --check (code hash)
--child <stage> is launched only by the supervisor (it refuses without the running attempt's token)."""
import sys, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from e1c import load_cfg, HERE
ap = argparse.ArgumentParser(); ap.add_argument("--stage"); ap.add_argument("--child"); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
from e1c.stages import code_hash
if a.check:
    h = code_hash(); p = HERE / "CODE_HASH.txt"; pin = p.read_text().strip() if p.exists() else None
    print(h, "OK" if h == pin else "MISMATCH"); sys.exit(0 if h == pin else 16)
if a.child:
    from e1c.stages import child_main; child_main(load_cfg(), a.child); sys.exit(0)
from e1c.supervisor import supervise
supervise(load_cfg(), a.stage)
