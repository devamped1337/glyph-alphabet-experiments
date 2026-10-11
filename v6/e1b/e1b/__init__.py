"""E1b implementation (v6/e1b/PREREG_E1b.md + Amendment A1)."""
import json, hashlib
from pathlib import Path
HERE = Path(__file__).resolve().parent.parent
def load_cfg(path=None):
    return json.load(open(path or HERE / "config_e1b.json"))
def sha256_text(s): return hashlib.sha256(s.encode("utf-8")).hexdigest()
def norm(s): return " ".join(s.lower().split())
