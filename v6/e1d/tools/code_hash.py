"""E1d code hash: e1d/*.py, run_e1d.py, config_e1d.json, w_e1d.json, kaggle/e1d_kaggle.py, ALL v6/e1d/tools/*.py,
the pinned dev-new book, and the E1c (e1c/*.py) and E1b (e1b/*.py) modules it imports."""
import hashlib
from pathlib import Path
HERE = Path(__file__).resolve().parent.parent
def files():
    fs = sorted((HERE / "e1d").glob("*.py")) + [HERE / "run_e1d.py", HERE / "config_e1d.json", HERE / "w_e1d.json", HERE / "kaggle" / "e1d_kaggle.py",
                                                HERE / "data" / "book_dev_new.json"]
    fs += sorted((HERE / "tools").glob("*.py")) + sorted((HERE.parent / "e1c" / "e1c").glob("*.py")) + sorted((HERE.parent / "e1b" / "e1b").glob("*.py"))
    return [f for f in fs if f.exists()]
def compute():
    h = hashlib.sha256()
    for f in files(): h.update(str(f.relative_to(HERE.parent)).encode() + b"\0" + f.read_bytes() + b"\0")
    return h.hexdigest()
if __name__ == "__main__": print(compute())
