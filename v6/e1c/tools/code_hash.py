"""E1c code hash: e1c/*.py, run_e1c.py, config_e1c.json, kaggle/e1c_kaggle.py and the E1b modules it imports."""
import hashlib
from pathlib import Path
HERE = Path(__file__).resolve().parent.parent
def files():
    fs = sorted((HERE / "e1c").glob("*.py")) + [HERE / "run_e1c.py", HERE / "config_e1c.json", HERE / "kaggle" / "e1c_kaggle.py"]
    fs += sorted((HERE.parent / "e1b" / "e1b").glob("*.py"))
    return [f for f in fs if f.exists()]
def compute():
    h = hashlib.sha256()
    for f in files(): h.update(str(f.relative_to(HERE.parent)).encode() + b"\0" + f.read_bytes() + b"\0")
    return h.hexdigest()
if __name__ == "__main__": print(compute())
