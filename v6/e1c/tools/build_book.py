"""Build an E1c book: python tools/build_book.py dev|test  (test refuses unless E1c is frozen)."""
import sys, json, hashlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from e1c import load_cfg, DATA
from e1c.book import build_book
kind = sys.argv[1]; B = build_book(load_cfg(), kind); p = DATA / f"book_{kind}.json"
p.write_text(json.dumps(B, sort_keys=True)); h = hashlib.sha256(p.read_bytes()).hexdigest()
(DATA / f"book_{kind}.sha256").write_text(h + "\n"); print(kind, h, len(B["entries"]), {k: len(v) for k, v in B["cases"].items()})
