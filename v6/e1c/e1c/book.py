"""E1c books. dev: fresh dev seeds, built and committed now. test: TEST seeds pinned now; the TEST book is built
only after E1c is frozen. Each book is disjoint (case texts, entry texts, entry ids) from the E1b frozen book, the
A9 book and, for test, the dev book; only the frozen canary pool is spliced in (B0x canary refs are keyed by it)."""
import copy, json, hashlib
from . import DATA, E1B
from e1b import norm
from e1b.cases import build, verify
from e1b.a9 import check_branches

def _old_rule_texts(o):
    """Rule texts an E1c book may not reuse: every old-book entry except neighbours (a neighbour is a confusable
    distractor; forbidding all old neighbour texts as well exhausts the small F2 rule space at TEST size)."""
    return {norm(e["text"]) for e in o["entries"].values() if e.get("kind") != "neighbour"}

def check_fresh(B, o):
    """E1c freshness vs an old book: no case text (except the shared canary pool), no entry id outside the canary
    pool, and no E1c core entry (or non-neighbour entry) whose rule text is an old non-neighbour rule text."""
    can_t = {norm(c["text"]) for c in o["cases"]["canary"]}; can_e = set(o["groups"]["canary_F1"])
    old_t = {norm(c["text"]) for cs in o["cases"].values() for c in cs}; old_r = _old_rule_texts(o)
    for pool, cs in B["cases"].items():
        for c in cs:
            if pool == "canary": assert norm(c["text"]) in can_t; continue
            assert norm(c["text"]) not in old_t, f"E1c: case seen in an old book ({pool}): {c['text']}"
    for k, e in B["entries"].items():
        if k in can_e: continue
        assert k not in o["entries"], f"E1c: entry id reused: {k}"
        if e.get("kind") != "neighbour": assert norm(e["text"]) not in old_r, f"E1c: rule text reused: {k}"
    return True

def sub_cfg(cfg, kind):
    X = cfg["e1c"]; c = copy.deepcopy({k: v for k, v in cfg.items() if k != "e1c"})
    c["seeds"] = dict(X["seeds"][kind]); n = X["sizes"][kind]["core_per_family"]; n += spare(n)
    for k in c["configs"]: c["configs"][k]["core_per_family"] = n
    c["test_cases_per_entry"] = X["cases_per_entry"]; c["test_branch_balance"] = True
    return c

def spare(n): return n   # build 2n core entries per family so same-rule duplicates can be dropped (F2 rule space is small)

def old_books(kind):
    olds = [json.load(open(E1B / "data" / "cases_e1b.json")), json.load(open(E1B / "data" / "cases_e1b_a9.json"))]
    if kind == "test": olds.append(json.load(open(DATA / "book_dev.json")))
    return olds

def build_book(cfg, kind):
    if kind not in ("dev", "test"): raise ValueError(kind)
    if kind == "test" and cfg["e1c"]["status"] != "frozen":
        raise SystemExit("TEST book refused: E1c is not frozen (no TEST data before freeze)")
    c = sub_cfg(cfg, kind); olds = old_books(kind); frz = olds[0]
    seen = {norm(x["text"]) for o in olds for cs in o["cases"].values() for x in cs}
    ids = {k for o in olds for k in o["entries"]}; forbid = set().union(*(_old_rule_texts(o) for o in olds))
    B = build(c, seen_init=seen, ids_init=ids, forbid_texts=forbid)
    for eid in B["groups"]["canary_F1"]: B["entries"].pop(eid)
    B["cases"]["canary"] = list(frz["cases"]["canary"]); B["groups"]["canary_F1"] = list(frz["groups"]["canary_F1"])
    for eid in frz["groups"]["canary_F1"]: B["entries"][eid] = frz["entries"][eid]
    B["meta"] = dict(seeds=c["seeds"], study="E1c", kind=kind, core_per_family=c["configs"]["C100"]["core_per_family"],
                     canary_from="v6/e1b/data/cases_e1b.json",
                     note="pool 'test' of a dev book is DEV data, never E1c TEST")
    n = cfg["e1c"]["sizes"][kind]["core_per_family"]; B["e1c_core"] = {}; B["meta"]["e1c_core_n"] = n
    for f in ("F1", "F2"):     # pre-declared: the first n core entries in build order whose rule text is new
        seen_t, keep = set(), []
        for k in B["groups"][f"core_{f}"]:
            t = norm(B["entries"][k]["text"])
            if t not in seen_t and len(keep) < n: keep.append(k); seen_t.add(t)
        assert len(keep) == n, f"E1c: only {len(keep)} distinct {f} core entries"
        B["e1c_core"][f] = keep
    check(B, cfg, kind, olds); return B

def check(B, cfg, kind, olds=None):
    c = sub_cfg(cfg, kind); verify(B, c)
    for o in (olds or old_books(kind)): check_fresh(B, o)
    check_branches(B, c["test_cases_per_entry"]); check_unique(B, B["meta"]["e1c_core_n"]); return True

def check_unique(B, n):
    """E1c: no two E1c core entries state the same rule (E1b's builder allows it; the A9 book has two duplicate F2
    core pairs). A duplicate would be one cluster counted twice."""
    E = B["entries"]; seen = {}
    for f in ("F1", "F2"):
        ks = B["e1c_core"][f]; assert len(ks) == n and all(k in B["groups"][f"core_{f}"] for k in ks)
        for k in ks:
            t = norm(E[k]["text"]); assert t not in seen, f"E1c: core entries {seen.get(t)} and {k} state the same rule"; seen[t] = k
    return True

def core_ids(B, n_per_family):
    return [e for f in ("F1", "F2") for e in B["e1c_core"][f][:n_per_family]]

def cases_for(B, eids):
    s = set(eids); return [x for x in B["cases"]["test"] if x["entry"] in s]

def load_book(cfg, kind):
    p = DATA / f"book_{kind}.json"; raw = open(p, "rb").read(); h = hashlib.sha256(raw).hexdigest()
    pin = cfg["e1c"][f"{kind}_book_sha256"]
    if pin != h: raise SystemExit(f"{kind} book sha256 {h} != pinned {pin}")
    B = json.loads(raw); check(B, cfg, kind); return B
