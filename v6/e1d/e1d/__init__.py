"""E1d (v6/e1d/DRAFT_PLAN.md, tag prereg-e1d): lifetime-byte criterion on a declared workload W, arm A0 only.
Reuses the frozen E1b modules and the E1c stage code (imported, not edited)."""
import json, sys, copy, os
from pathlib import Path
HERE = Path(__file__).resolve().parent.parent
V6 = HERE.parent; E1B = V6 / "e1b"; E1C = V6 / "e1c"
for p in (E1B, E1C, HERE / "tools"):
    if str(p) not in sys.path: sys.path.insert(0, str(p))
RES = HERE / "results"; DATA = HERE / "data"
if os.environ.get("E1B_ALLOW_NO_GPU") == "1" and os.environ.get("E1D_RES"): RES = Path(os.environ["E1D_RES"])   # tests only
def load_cfg(path=None):
    """E1d cfg = E1b base config (unchanged) + the e1d block (+ the W file)."""
    if path is None and os.environ.get("E1B_ALLOW_NO_GPU") == "1" and os.environ.get("E1D_CONFIG"): path = os.environ["E1D_CONFIG"]   # tests only
    X = json.load(open(path or HERE / "config_e1d.json"))
    base = json.load(open((HERE / X["base_config"]).resolve()))
    c = copy.deepcopy(base); c["e1d"] = X; c["e1d"]["W"] = json.load(open(HERE / X["w_file"])); return c
