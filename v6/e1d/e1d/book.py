"""E1d books (DRAFT_PLAN §7). dev-new: 4k F2 cores on the adopted NEW role pairs only (built now, pinned).
The D1-E1d data = the E1c dev book (reused, pinned by E1c) + dev-new, merged into one book object.
Exclusion (frozen, strict): no entry text of ANY kind, no case text, no entry id from the E1b frozen book, the A9
book, the E1c dev book and the E1c TEST book (canary pool spliced in as in E1c). TEST additionally excludes
everything shown in any E1d dev stage (cores, neighbours, cases, ids of every dev-new book)."""
import json, hashlib, copy
from . import DATA, V6, E1C
from e1b import norm
import builder_trials as BT          # v6/e1d/tools (in the code hash)

OLD_BOOKS = list(BT.OLD_BOOKS)       # e1b frozen, e1b A9, e1c dev, e1c TEST
E1C_DEV_SHA = "a7ea724dfb856547dbfba38d04a49a8f59d781b3a9e66596f2582ce112ae78c4"   # v6/e1c/config_e1c.json dev_book_sha256

def olds(): return [json.load(open(V6 / p)) for p in OLD_BOOKS]

def shown_of(B, core): return [x for k in core for x in [k] + B["neighbours"][k]]

def exclusions(kind, dev_new_books=()):
    """Strict list. kind 'dev_new': the 4 old books. kind 'test': + everything shown in every E1d dev-new book."""
    texts, cases, ids, ct, ce = BT.strict_excl(olds())
    if kind == "test":
        for D in dev_new_books:
            sh = shown_of(D, D["e1d_dev_new_core"]); cs = [x for x in D["cases"]["test"] if x["entry"] in set(D["e1d_dev_new_core"])]
            texts = texts | {norm(D["entries"][x]["text"]) for x in sh}; cases = cases | {norm(x["text"]) for x in cs}; ids = ids | set(sh)
    elif kind != "dev_new": raise ValueError(kind)
    return texts, cases, ids, ct, ce

def check_fresh_e1d(B, core, excl):
    """E1d freshness (strict): every shown entry (core + neighbours) has a fresh text and id; every case of a core
    is fresh (canary pool exempt). Raises AssertionError naming the failed check."""
    texts, cases, ids, can_t, can_e = excl; E = B["entries"]; sh = shown_of(B, core)
    for x in sh:
        assert norm(E[x]["text"]) not in texts, f"E1d: entry text reused: {x}"
        assert x in can_e or x not in ids, f"E1d: entry id reused: {x}"
    for c in B["cases"]["test"]:
        if c["entry"] in set(core) and norm(c["text"]) not in can_t: assert norm(c["text"]) not in cases, f"E1d: case text reused: {c['text']}"
    return True

def build_dev_new(cfg, gen_seed):
    """Real builder (as the trials), F2 roles = adopted new pairs; core = first 4 distinct per pair."""
    X = cfg["e1d"]; roles = [tuple(p) for p in X["roles_adopted"]]; per = X["sizes"]["dev_new"]["per_pair"]
    excl = exclusions("dev_new"); frz = olds()[0]; ccfg = e1c_cfg()
    B, c = BT.build(ccfg, "dev", gen_seed - 1, 3 * per * 2, roles, excl, frz)     # seed0 + 1 = generator seed (BT.KEYS_SEED order)
    core = BT.first_distinct(B, "F2", per * len(roles), per=per)
    assert len(core) == per * len(roles), f"dev-new: only {len(core)} cores"
    assert all((B["entries"][k]["x"], B["entries"][k]["y"]) in set(roles) for k in core)
    chk, _, _ = BT.checks(B, c, core, excl); assert all(chk.values()), chk
    check_fresh_e1d(B, core, excl)
    B["e1d_dev_new_core"] = core; B["meta"] = dict(B.get("meta", {}), study="E1d", kind="dev_new", generator=gen_seed,
                                                   roles=[list(r) for r in roles], checks=chk)
    return B

def e1c_cfg():
    from e1c import load_cfg as L; return L()

def _load(p, pin):
    raw = open(p, "rb").read(); h = hashlib.sha256(raw).hexdigest()
    if h != pin: raise SystemExit(f"{p.name} sha256 {h} != pinned {pin}")
    return json.loads(raw)

def load_dev(cfg):
    """-> merged D1-E1d book with B['e1d_ids'] = dict(e1c_dev_sel, e1c_dev_recv, dev_new)."""
    X = cfg["e1d"]; Dv = _load(E1C / "data" / "book_dev.json", E1C_DEV_SHA); N = _load(DATA / "book_dev_new.json", X["dev_new_book_sha256"])
    check_fresh_e1d(N, N["e1d_dev_new_core"], exclusions("dev_new"))
    assert [list(r) for r in X["roles_adopted"]] == N["meta"]["roles"], "dev-new roles != adopted roles"
    return merge(Dv, N, X)

def merge(Dv, N, X):
    B = copy.deepcopy(Dv); new = N["e1d_dev_new_core"]; sh = shown_of(N, new)
    for k in sh:
        if k in B["entries"]: assert B["entries"][k] == N["entries"][k], f"id collision {k}"
        B["entries"][k] = N["entries"][k]
    for k in new: B["neighbours"][k] = N["neighbours"][k]
    B["dictionary"] = sorted(set(B["dictionary"]) | set(sh))
    B["cases"]["test"] = list(B["cases"]["test"]) + [c for c in N["cases"]["test"] if c["entry"] in set(new)]
    n = X["sizes"]["e1c_dev"]["core_per_family"]; nr = X["sizes"]["e1c_dev"]["receiver_entries_per_family"]
    ed = [e for f in ("F1", "F2") for e in Dv["e1c_core"][f][:n]]; er = [e for f in ("F1", "F2") for e in Dv["e1c_core"][f][:nr]]
    B["e1c_core"] = dict(F1=list(Dv["e1c_core"]["F1"]), F2=list(Dv["e1c_core"]["F2"]) + new)   # (fake test backend keys)
    B["e1d_ids"] = dict(e1c_dev_sel=ed, e1c_dev_recv=er, dev_new=list(new)); return B

def pair_of(e): return f"{e['x']}/{e['y']}" if e.get("fam") == "F2" else None

# ---------------------------------------------------------------- TEST (built only after freeze)
import os
from pathlib import Path
TDATA = Path(os.environ["E1D_TEST_DATA"]) if os.environ.get("E1B_ALLOW_NO_GPU") == "1" and os.environ.get("E1D_TEST_DATA") else DATA   # tests only (throwaway book)
TEST_PINS = TDATA / "test_pins.json"     # written AFTER the freeze tag (book sha256 + measured v1 artifact); not in the code hash

def build_test(cfg, seed0):
    """Frozen procedure (§7): seeds seed0..seed0+5 in BT.KEYS_SEED order (95061 -> generator 95062), F2 roles = adopted
    new pairs only, 2n = 160 draws per family, core = first 80 distinct per family; strict exclusions incl. dev-new."""
    X = cfg["e1d"]
    if X["status"] != "frozen": raise SystemExit("TEST book refused: E1d is not frozen")
    roles = [tuple(p) for p in X["roles_adopted"]]; n = X["sizes"]["test"]["core_per_family"]
    N = json.load(open(DATA / "book_dev_new.json")); excl = exclusions("test", [N]); frz = olds()[0]
    B, c = BT.build(e1c_cfg(), "test", seed0, n, roles, excl, frz)      # sub_cfg doubles n (spare = n) -> 2n draws
    core = {f: BT.first_distinct(B, f, n) for f in ("F1", "F2")}
    for f in core: assert len(core[f]) == n, f"TEST: only {len(core[f])} distinct {f} cores"
    assert all((B["entries"][k]["x"], B["entries"][k]["y"]) in set(roles) for k in core["F2"]), "TEST F2 core on an old pair"
    allc = core["F1"] + core["F2"]; chk, _, _ = BT.checks(B, c, allc, excl); assert all(chk.values()), chk
    check_fresh_e1d(B, allc, excl)
    B["e1d_test_core"] = core; B["meta"] = dict(B.get("meta", {}), study="E1d", kind="test", seed0=seed0, generator=seed0 + 1,
                                                roles=[list(r) for r in roles], checks=chk)
    return B

def load_test(cfg):
    X = cfg["e1d"]
    if X["status"] != "frozen": raise SystemExit("TEST refused: E1d is not frozen")
    P = json.load(open(TEST_PINS)); B = _load(TDATA / "book_test.json", P["test_book_sha256"])
    N = json.load(open(DATA / "book_dev_new.json")); allc = B["e1d_test_core"]["F1"] + B["e1d_test_core"]["F2"]
    check_fresh_e1d(B, allc, exclusions("test", [N]))
    assert [list(r) for r in X["roles_adopted"]] == B["meta"]["roles"]
    n = X["sizes"]["test"]["core_per_family"]; assert all(len(B["e1d_test_core"][f]) == n for f in ("F1", "F2"))
    B["e1c_core"] = {f: list(B["e1d_test_core"][f]) for f in ("F1", "F2")}     # (fake test backend keys)
    B["e1d_ids"] = dict(test=allc); return B
