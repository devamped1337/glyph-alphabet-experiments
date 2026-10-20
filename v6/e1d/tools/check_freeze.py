"""E1d freeze integrity (read-only).  python v6/e1d/tools/check_freeze.py [--exec]
freeze: config frozen; code hash == CODE_HASH.txt; TEST protocol hash == dev summary hash; dev results unchanged
(sha256 list in FREEZE_E1d.json); roles/seeds/cap/W as frozen.  --exec additionally: test pins exist, TEST book sha
matches, the book rebuilds byte-identically from the frozen seed, and the v1 artifact bytes match the pin."""
import sys, json, hashlib
from pathlib import Path
HERE = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(HERE))
from e1d import load_cfg
from e1d.stages import code_hash, protocol_hash, artifact_members
from e1d import book as BK
import measure_dict_artifact as MA
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    cfg = load_cfg(); X = cfg["e1d"]; F = json.load(open(HERE / "FREEZE_E1d.json")); bad = []
    if X["status"] != "frozen": bad.append("config not frozen")
    if code_hash() != (HERE / "CODE_HASH.txt").read_text().strip(): bad.append("code hash != CODE_HASH.txt")
    if code_hash() != F["code_hash"]: bad.append("code hash != FREEZE_E1d.json")
    dev = json.load(open(HERE / "results" / "D1-E1d" / "summary.json"))
    if protocol_hash(X, cfg) != dev["protocol_hash"] or dev["protocol_hash"] != F["protocol_hash"]: bad.append("protocol hash != dev")
    for p, h in F["dev_results_sha256"].items():
        if sha(HERE / p) != h: bad.append(f"dev result changed: {p}")
    for k, v in F["frozen"].items():
        if json.dumps(X[k], sort_keys=True) != json.dumps(v, sort_keys=True): bad.append(f"frozen field changed: {k}")
    if json.dumps(X["W"], sort_keys=True) != json.dumps(F["W"], sort_keys=True): bad.append("W changed")
    if "--exec" in sys.argv:
        P = json.load(open(BK.TEST_PINS))
        if sha(BK.TDATA / "book_test.json") != P["test_book_sha256"]: bad.append("TEST book sha != pin")
        B = BK.build_test(cfg, P["seed0"]); raw = json.dumps(B, sort_keys=True, ensure_ascii=False).encode()
        if hashlib.sha256(raw).hexdigest() != P["test_book_sha256"]: bad.append("TEST book does not rebuild identically")
        T = BK.load_test(cfg); r, hb, bb = MA.build(T["entries"], artifact_members(T, T["e1d_ids"]["test"]))
        if dict(artifact_bytes=len(r), body_bytes=bb, manifest_bytes=hb) != {k: P["artifact_v1"][k] for k in ("artifact_bytes", "body_bytes", "manifest_bytes")}: bad.append("artifact != pin")
    print("OK" if not bad else "FAIL: " + "; ".join(bad)); sys.exit(0 if not bad else 1)
if __name__ == "__main__": main()
