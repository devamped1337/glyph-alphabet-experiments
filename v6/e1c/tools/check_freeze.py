"""Freeze integrity (PREREG_E1c §9). Two immutable tags:
  prereg-e1c    REGISTRATION commit: status frozen, T1 cap set, test_book_sha256 null, no book_test.json.
  e1c-t1-exec   EXECUTION commit: a descendant of prereg-e1c whose diff vs prereg-e1c touches ONLY
                v6/e1c/data/book_test.json, v6/e1c/data/book_test.sha256, v6/e1c/data/test_seed_attempts.txt and
                config_e1c.json, where the config differs ONLY in test_book_sha256 (and seeds.test.generator if
                the seed rule fired), plus CODE_HASH.txt (the config is hashed). No code file may change.
  python tools/check_freeze.py prereg-e1c e1c-t1-exec"""
import sys, json, subprocess, copy
ALLOWED = {"v6/e1c/data/book_test.json", "v6/e1c/data/book_test.sha256", "v6/e1c/data/test_seed_attempts.txt",
           "v6/e1c/config_e1c.json", "v6/e1c/CODE_HASH.txt"}
CFG_KEYS = {"test_book_sha256"}

def cfg_diff_ok(a, b):
    ka = {k for k in set(a) | set(b) if a.get(k) != b.get(k)}
    extra = ka - CFG_KEYS - {"seeds"}
    if extra: return False, f"config keys changed: {sorted(extra)}"
    if a.get("seeds") != b.get("seeds"):
        sa, sb = copy.deepcopy(a["seeds"]), copy.deepcopy(b["seeds"]); ga = sa["test"].pop("generator"); gb = sb["test"].pop("generator")
        if sa != sb or (gb - ga) % 100 or gb < ga: return False, "seeds changed beyond the seed rule"
    if a.get("status") != "frozen" or a.get("test_book_sha256") is not None: return False, "registration commit not frozen / already has a TEST sha"
    if not b.get("test_book_sha256"): return False, "execution commit lacks test_book_sha256"
    return True, "ok"

def files_ok(changed):
    bad = sorted(set(changed) - ALLOWED); return (not bad), (f"disallowed files changed: {bad}" if bad else "ok")

def digest_ok(book_bytes, cfg_pin, sha_file_text):
    """r3 (optional): the execution commit's TEST book digest equals both pins."""
    import hashlib
    h = hashlib.sha256(book_bytes).hexdigest(); return (h == cfg_pin == sha_file_text.strip()), h

def main(reg, exe):
    g = lambda *a: subprocess.check_output(["git", *a], text=True)
    if subprocess.run(["git", "merge-base", "--is-ancestor", reg, exe]).returncode: raise SystemExit("execution tag is not a descendant of the registration tag")
    ok1, w1 = files_ok([l for l in g("diff", "--name-only", reg, exe).splitlines() if l])
    ok2, w2 = cfg_diff_ok(json.loads(g("show", f"{reg}:v6/e1c/config_e1c.json")), json.loads(g("show", f"{exe}:v6/e1c/config_e1c.json")))
    no_book = subprocess.run(["git", "cat-file", "-e", f"{reg}:v6/e1c/data/book_test.json"]).returncode != 0
    raw = subprocess.check_output(["git", "show", f"{exe}:v6/e1c/data/book_test.json"])
    ok3, h = digest_ok(raw, json.loads(g("show", f"{exe}:v6/e1c/config_e1c.json"))["test_book_sha256"], g("show", f"{exe}:v6/e1c/data/book_test.sha256"))
    print(w1, w2, "registration has no TEST book" if no_book else "REGISTRATION CONTAINS A TEST BOOK", "digest ok" if ok3 else f"digest mismatch {h}")
    sys.exit(0 if ok1 and ok2 and no_book and ok3 else 1)

if __name__ == "__main__": main(sys.argv[1], sys.argv[2])
