#!/usr/bin/env python3
"""Build the A9 fresh book (data/cases_e1b_a9.json) from config a9.seeds and print its sha256 (pin it in
config a9.book_sha256 and commit both BEFORE any A9 run). Pure function of config; no model calls."""
import json, sys
from pathlib import Path
R = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(R))
from e1b import load_cfg, sha256_text
from e1b import a9
cfg = load_cfg(); old = json.load(open(R / "data" / "cases_e1b.json"))
B = a9.build_book(cfg, old); s = json.dumps(B)
(R / "data" / "cases_e1b_a9.json").write_text(s); h = sha256_text(s)
(R / "data" / "cases_e1b_a9.sha256").write_text(h + "\n")
print(h, {k: len(v) for k, v in B["cases"].items()}, "entries", len(B["entries"]))
