"""E1c (DRAFT): verified-ID hybrid with prose fallback (v6/e1c/PREREG_E1c.md). Reuses the frozen E1b modules."""
import json, sys, copy
from pathlib import Path
HERE = Path(__file__).resolve().parent.parent
E1B = HERE.parent / "e1b"
if str(E1B) not in sys.path: sys.path.insert(0, str(E1B))
RES = HERE / "results"; DATA = HERE / "data"
def load_cfg(path=None):
    """E1c cfg = E1b base config (unchanged) + the e1c block."""
    X = json.load(open(path or HERE / "config_e1c.json"))
    base = json.load(open((HERE / X["base_config"]).resolve()))
    c = copy.deepcopy(base); c["e1c"] = X; return c
