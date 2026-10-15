"""Build an E1c book with the pre-declared seed rule: python tools/build_book.py dev|test
(test refuses unless E1c is frozen). If the build fails at the pinned generator seed, the seed is raised by 100
until it builds (max 50 tries); every attempt is logged in data/<kind>_seed_attempts.txt and the seed that built
is written back to config_e1c.json (seeds.<kind>.generator) together with <kind>_book_sha256."""
import sys, json, hashlib, copy
from pathlib import Path
HERE = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(HERE))
from e1c import load_cfg, DATA
from e1c.book import build_book
kind = sys.argv[1]; cfg = load_cfg(); g0 = cfg["e1c"]["seeds"][kind]["generator"]; log = []
for i in range(50):
    c = copy.deepcopy(cfg); g = g0 + 100 * i; c["e1c"]["seeds"][kind]["generator"] = g
    try: B = build_book(c, kind); log.append(f"{g}: built"); break
    except AssertionError as e: log.append(f"{g}: {e}")
else: raise SystemExit("no seed built in 50 tries")
p = DATA / f"book_{kind}.json"; p.write_text(json.dumps(B, sort_keys=True)); h = hashlib.sha256(p.read_bytes()).hexdigest()
(DATA / f"book_{kind}.sha256").write_text(h + "\n"); (DATA / f"{kind}_seed_attempts.txt").write_text("\n".join(log) + "\n")
cp = HERE / "config_e1c.json"; X = json.load(open(cp)); X["seeds"][kind]["generator"] = g; X[f"{kind}_book_sha256"] = h
json.dump(X, open(cp, "w"), indent=1); print(kind, h, "\n".join(log))
