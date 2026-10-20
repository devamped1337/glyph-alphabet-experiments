"""AFTER the freeze tag: build + pin the E1d TEST book (seed0 95061 -> generator 95062; +100 until it builds, logged)
and pin the measured v1 artifact bytes into data/test_pins.json."""
import sys, json, hashlib
from pathlib import Path
HERE = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(HERE))
from e1d import load_cfg, DATA
from e1d.book import build_test, TEST_PINS, load_test, TDATA
from e1d.stages import artifact_members
import measure_dict_artifact as MA
from e1d.lifetime import gz9
cfg = load_cfg(); s0 = int(sys.argv[1]) if len(sys.argv) > 1 and TDATA != DATA else cfg["e1d"]["seeds"]["test"]["first"]; log = []   # argv seed = throwaway, test mode only
for i in range(20):
    try: B = build_test(cfg, s0 + 100 * i); log.append(f"{s0 + 100 * i} ok"); break
    except (AssertionError, RuntimeError, ValueError) as e: log.append(f"{s0 + 100 * i} fail: {str(e)[:150]}")
else: raise SystemExit("no TEST seed built: " + "; ".join(log))
raw = json.dumps(B, sort_keys=True, ensure_ascii=False).encode(); (TDATA / "book_test.json").write_bytes(raw)
h = hashlib.sha256(raw).hexdigest(); (TDATA / "test_seed_attempts.txt").write_text("\n".join(log) + "\n")
TEST_PINS.write_text(json.dumps(dict(seed0=s0 + 100 * (len(log) - 1), test_book_sha256=h, artifact_v1={}), indent=1))
T = load_test(cfg); ids = T["e1d_ids"]["test"]; r, hb, bb = MA.build(T["entries"], artifact_members(T, ids))
art = dict(artifact_bytes=len(r), manifest_bytes=hb, body_bytes=bb, n_entries=len(artifact_members(T, ids)), n_core=len(ids),
           gzip9_bytes=gz9(r), sha256=hashlib.sha256(r).hexdigest())
pairs = {}
for k in T["e1d_test_core"]["F2"]: e = T["entries"][k]; pairs[f"{e['x']}/{e['y']}"] = pairs.get(f"{e['x']}/{e['y']}", 0) + 1
TEST_PINS.write_text(json.dumps(dict(seed0=s0 + 100 * (len(log) - 1), test_book_sha256=h, artifact_v1=art, F2_by_pair=pairs), indent=1))
print(h, log, art, pairs)
