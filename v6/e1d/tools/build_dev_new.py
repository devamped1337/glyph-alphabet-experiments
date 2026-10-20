"""Build + pin the E1d dev-new book (DRAFT_PLAN §7 step 2): generator 94062, +100 until it builds (attempts logged)."""
import sys, json, hashlib
from pathlib import Path
HERE = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(HERE))
from e1d import load_cfg, DATA
from e1d.book import build_dev_new
cfg = load_cfg(); s = cfg["e1d"]["seeds"]["dev_new_generator"]; log = []
for i in range(10):
    try: B = build_dev_new(cfg, s + 100 * i); log.append(f"{s + 100 * i} ok"); break
    except (AssertionError, RuntimeError, ValueError) as e: log.append(f"{s + 100 * i} fail: {str(e)[:120]}")
else: raise SystemExit("no dev-new seed built")
raw = json.dumps(B, sort_keys=True, ensure_ascii=False).encode(); (DATA / "book_dev_new.json").write_bytes(raw)
h = hashlib.sha256(raw).hexdigest(); (DATA / "book_dev_new.sha256").write_text(h + "\n"); (DATA / "dev_new_seed_attempts.txt").write_text("\n".join(log) + "\n")
print(h, log)
