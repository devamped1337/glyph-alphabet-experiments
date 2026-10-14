"""Amendment A9 (DRAFT until frozen): B1-B3 for the post-hoc pair qwen7b + falcon7b (A8 / B0x).
- Fresh book: rebuilt with NEW pinned seeds (config a9.seeds) and a scaled TEST size; only the canary pool
  (needed for the B0x canary references) is copied verbatim from the frozen book. Every other case and entry
  text must be absent from the frozen book (asserted). The book file and its sha256 are committed before any run.
- Scale-down ladder (pre-registered, pilot timings only, never accuracy): first level whose summed stage caps
  (cap = projection / headroom, rounded up to 0.05 h) fit the A9 total.
- Fixed caps: each A9 stage has its own ledger allocation; the cap is fixed in config and never recomputed.
- Launch gate: stages refuse unless a9.status == 'frozen' AND E1B_GO names this stage (Stefan's explicit go)."""
import copy, json, math, os, sys
from . import HERE, sha256_text, norm
from .cases import build, verify, templates

DATA = HERE / "data"; BOOK = DATA / "cases_e1b_a9.json"

def require_go(cfg, stage):
    X = cfg.get("a9")
    if not X or X.get("status") != "frozen":
        print(f"{stage} refused: A9 is not frozen (config a9.status != 'frozen')"); sys.exit(13)
    if os.environ.get("E1B_GO") != stage:
        print(f"{stage} refused: no explicit go (E1B_GO must equal '{stage}'; set only on Stefan's instruction)"); sys.exit(14)
    return X

def a9_cfg(cfg, level=None):
    """cfg with A9 seeds and the ladder level's TEST cases per entry (the book is built at that size)."""
    X = cfg["a9"]; lv = level or X["frozen_level"]; c2 = copy.deepcopy(cfg)
    c2["seeds"] = dict(X["seeds"]); c2["test_cases_per_entry"] = lv["cases_per_entry"]
    return c2, lv

def build_book(cfg, old):
    c2, lv = a9_cfg(cfg)
    B = build(c2, seen_init={norm(c["text"]) for cs in old["cases"].values() for c in cs}, ids_init=set(old["entries"]),
              forbid_texts={norm(e["text"]) for e in old["entries"].values()})
    # splice the frozen canary pool (B0x canary references are keyed by these exact texts)
    for eid in B["groups"]["canary_F1"]: B["entries"].pop(eid)
    B["cases"]["canary"] = list(old["cases"]["canary"]); B["groups"]["canary_F1"] = list(old["groups"]["canary_F1"])
    for eid in old["groups"]["canary_F1"]: B["entries"][eid] = old["entries"][eid]
    B["meta"] = dict(seeds=c2["seeds"], amendment="A9", level=lv, canary_from="cases_e1b.json")
    verify(B, c2); check_fresh(B, old); return B

def check_fresh(B, old):
    """No case text, entry text or entry id of the frozen book appears in the A9 book, except the canary pool."""
    can_t = {norm(c["text"]) for c in old["cases"]["canary"]}; can_e = set(old["groups"]["canary_F1"])
    old_t = {norm(c["text"]) for cs in old["cases"].values() for c in cs}
    old_et = {norm(e["text"]) for k, e in old["entries"].items() if k not in can_e}
    for pool, cs in B["cases"].items():
        for c in cs:
            if pool == "canary": assert norm(c["text"]) in can_t; continue
            assert norm(c["text"]) not in old_t, f"A9: case seen in frozen book ({pool}): {c['text']}"
    for k, e in B["entries"].items():
        if k in can_e: continue
        assert k not in old["entries"], f"A9: entry id reused from frozen book: {k}"
        assert norm(e["text"]) not in old_et, f"A9: entry text reused from frozen book: {k}"
    return True

def get_book(cfg):
    X = cfg["a9"]; old = json.load(open(DATA / "cases_e1b.json"))
    if not BOOK.exists(): print("A9 book missing: build it with tools/build_a9_book.py and commit it before any run"); sys.exit(15)
    raw = open(BOOK).read(); h = sha256_text(raw)
    if h != X["book_sha256"]: print(f"A9 book sha256 {h} != pinned {X['book_sha256']}"); sys.exit(15)
    B = json.loads(raw); c2, _ = a9_cfg(cfg); verify(B, c2); check_fresh(B, old); return B

def ids_for(B, cfg, lv):
    n = cfg["configs"][lv["config"]]["core_per_family"]
    core = {f: B["groups"][f"core_{f}"][:n] for f in cfg["families_core"]}
    f3l = list(B["groups"]["F3L"]) if lv["f3l"] else []
    return core, f3l

# ------------------------------------------------------------------ projection + ladder
def call_counts(cfg, lv, n_models=2):
    c = cfg["configs"][lv["config"]]; F = len(cfg["families_core"]); E = c["core_per_family"] * F
    T = lv["cases_per_entry"]; P = c["planted_calib"]; PT = cfg["planted_testgate"]; L = cfg["f3l_entries"] if lv["f3l"] else 0
    probes = max(len(templates(f)) for f in ("F1", "F2", "F3L")); N = cfg["n_neighbours"]
    items = (E + L) * T; sanity = cfg["sanity_subset_per_family"] * F * T
    cache = cfg["cache"]["fixed_per_model"] + cfg["cache"]["stress_per_model"]; K = cfg["a9"]["batch_check_items"]
    return {
        "B1c": {"receiver_b1": n_models * K, "receiver": n_models * K},
        "B1": {"probe": n_models * probes * ((E + P + L) + N * (E + L) + E + PT), "receiver": 5 * P},
        "B2": {"receiver": n_models * (items * 2 + 2 * sanity + cfg["byte_identity_paired_items"] + 5 * cache),
               "receiver_warm": n_models * items * 2},
        "B3": {"sender": n_models * (E + L), "receiver": n_models * items * 2},
    }

def project(cfg, timings, lv):
    """timings[model] = B0x pilot_timings entry (+ 'receiver_b1' = batch-1 qualification arithmetic latency).
    Each call type: count/2 x sum over models (each model does half the calls) + measured setup of both."""
    out = {}; h = cfg["a9"]["headroom"]; ms = list(timings)
    for st, calls in call_counts(cfg, lv, len(ms)).items():
        s = sum(n / len(ms) * sum(timings[m][ct] for m in ms) for ct, n in calls.items()) + sum(timings[m]["setup_s"] for m in ms)
        p = s / 3600; out[st] = dict(projected_h=round(p, 3), cap_h=math.ceil(p / h / 0.05 - 1e-9) * 0.05)
        out[st]["cap_h"] = round(out[st]["cap_h"], 2)
    return out

def choose(cfg, timings):
    X = cfg["a9"]; rep = []
    for lv in X["ladder"]:
        p = project(cfg, timings, lv); tot = round(sum(v["cap_h"] for v in p.values()), 2)
        rep.append(dict(level=lv, stages=p, total_cap_h=tot, fits=tot <= X["total_cap_h"]))
        if tot <= X["total_cap_h"]: return dict(choice=lv, report=rep)
    return dict(choice=None, report=rep)

def pilot_timings(res_dir):
    """B0x pilot timings + batch-1 arithmetic latency from the B0x qualification rows (both pair models)."""
    t = json.load(open(res_dir / "B0x" / "pilot_timings.json"))
    for m in t:
        rows = [json.loads(l) for l in open(res_dir / "B0x" / f"qual_{m}.jsonl")]
        a = [r["latency_s"] for r in rows if r["step"] == "qual_arith"]; t[m]["receiver_b1"] = sum(a) / len(a)
    return t

def batch_rule(cfg, pair_rows):
    """(c) batch-size rule: batched predictions must equal batch-1 predictions on >= a9.batch_match_min of the
    non-TEST check items, per model. pair_rows[m] = list of (pred_b1, pred_bN)."""
    out = {}
    for m, rows in pair_rows.items():
        k = sum(a == b for a, b in rows); out[m] = dict(n=len(rows), match=k, rate=k / len(rows) if rows else 0.0)
    ok = all(v["n"] > 0 and v["rate"] >= cfg["a9"]["batch_match_min"] for v in out.values())
    return dict(pass_=ok, per_model=out, batch_size=cfg["stageB_batch_size"] if ok else 1)

def entry_pass_prob(n, bar, p):
    """(a) P(an entry passes) when a model answers each of n probes correctly with prob p (binomial)."""
    k = math.ceil(bar * n - 1e-9)
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))
