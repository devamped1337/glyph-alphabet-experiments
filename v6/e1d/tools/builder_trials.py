"""E1d (DRAFT): throwaway builder trials with the REAL E1b/E1c book builder (CPU only; no model, no network).
For each throwaway seed it builds (1) an E1d dev-new book (F2 role pairs = the new pairs only; dev-new core =
the first 4 distinct cores per new pair in build order) and (2) a TEST-size book (F2 role pairs = the new pairs only, 80 core per
family = first 80 distinct of 2n = 160 draws; old pairs are exhausted under the strict rule: their 5 fresh core
texts cannot get fresh load-bearing neighbours, found by the first trial), with the E1d strict exclusion list, and runs every check:
e1b verify (gold, text-derived gold, neighbour load-bearing and label rules), branch balance, distinct core,
strict freshness, verifier expected-spec parse, and the role-word leak check. Books are discarded (never
written, never shown to a model).

  python v6/e1d/tools/builder_trials.py [out.json] [n_seeds]

The new role list is passed by rebinding e1b.cases.ROLES in this process only (the file is not edited)."""
import sys, json, copy, time, re
from pathlib import Path
V6 = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(V6 / "e1b"), str(V6 / "e1c")]
from e1b import norm
import e1b.cases as C
from e1b.a9 import check_branches
from e1c import load_cfg
from e1c.book import sub_cfg
from e1c.verifier import GRAMMAR, parse_spec, expected_spec, matches, KEYS
from e1b.protocol import render_message

OLD_ROLES = list(C.ROLES)
NEW_ROLES = [("baker", "porter"), ("potter", "bearer"), ("tanner", "loader")]       # adopted (DRAFT_PLAN §7)
STEP_UP = [("farmer", "packer"), ("cooper", "driver"), ("grocer", "runner")]
OLD_BOOKS = ["e1b/data/cases_e1b.json", "e1b/data/cases_e1b_a9.json", "e1c/data/book_dev.json", "e1c/data/book_test.json"]
DEV_PER_PAIR, TEST_PER_FAM = 4, 80
KEYS_SEED = ("hard_messages", "generator", "probes_fresh", "sanity_subset", "cache_sample", "bootstrap")

def strict_excl(books):
    """Every entry text of ANY kind, every case text and every entry id.
    The builder is seeded with ALL old case texts and ids incl. the canary pool (as E1c build_book), so no new
    entry or case can take a canary id or text; the canary pool is only exempt in the freshness checks below."""
    can_t = {norm(c["text"]) for c in books[0]["cases"]["canary"]}; can_e = set(books[0]["groups"]["canary_F1"])
    texts = {norm(e["text"]) for b in books for k, e in b["entries"].items() if k not in can_e}
    cases = {norm(c["text"]) for b in books for cs in b["cases"].values() for c in cs}
    ids = {k for b in books for k in b["entries"]}
    return texts, cases, ids, can_t, can_e

def build(cfg, kind, seed0, n_core, roles, excl, frz):
    X = copy.deepcopy(cfg); X["e1c"]["seeds"][kind] = {k: seed0 + i for i, k in enumerate(KEYS_SEED)}
    X["e1c"]["sizes"][kind]["core_per_family"] = n_core; c = sub_cfg(X, kind)
    texts, cases, ids, _, _ = excl; C.ROLES[:] = roles
    try: B = C.build(c, seen_init=cases, ids_init=ids, forbid_texts=texts)
    finally: C.ROLES[:] = OLD_ROLES
    for eid in B["groups"]["canary_F1"]: B["entries"].pop(eid)
    B["cases"]["canary"] = list(frz["cases"]["canary"]); B["groups"]["canary_F1"] = list(frz["groups"]["canary_F1"])
    for eid in frz["groups"]["canary_F1"]: B["entries"][eid] = frz["entries"][eid]
    return B, c

def first_distinct(B, f, n, pred=lambda e: True, per=None):
    seen, keep, cnt = set(), [], {}
    for k in B["groups"][f"core_{f}"]:
        e = B["entries"][k]; t = norm(e["text"])
        if t in seen or not pred(e): continue
        g = (e["x"], e["y"]) if per else None
        if per and cnt.get(g, 0) >= per: continue
        seen.add(t); keep.append(k); cnt[g] = cnt.get(g, 0) + 1
        if len(keep) == n: break
    return keep

def checks(B, c, core, excl):
    texts, cases, ids, can_t, can_e = excl; E = B["entries"]; out = {}
    C.verify(B, c); out["e1b_verify"] = True
    check_branches(B, c["test_cases_per_entry"]); out["branch_balance"] = True
    shown = [x for k in core for x in [k] + B["neighbours"][k]]
    out["distinct_core"] = len({norm(E[k]["text"]) for k in core}) == len(core)
    out["fresh_entry_texts"] = all(norm(E[x]["text"]) not in texts for x in shown)
    out["fresh_ids"] = all(x not in ids for x in shown if x not in can_e)
    cs = [x for x in B["cases"]["test"] if x["entry"] in set(core)]
    out["fresh_cases"] = all(norm(x["text"]) not in cases for x in cs if norm(x["text"]) not in can_t)
    out["cases_per_core_ok"] = all(sum(1 for x in cs if x["entry"] == k) == c["test_cases_per_entry"] for k in core)
    bad = []
    for x in shown:   # the verifier's ideal reply for this entry must parse under the frozen grammar and match
        e = E[x]; sp = expected_spec(e)
        line = " ".join(f"{k}={sp[k] if not isinstance(sp[k], str) else sp[k]}" for k in KEYS[e["fam"]])
        spec, why = parse_spec(e["fam"], line); ok, _ = matches(spec, e)
        if why != "ok" or not ok: bad.append(x)
    out["verifier_spec_parse_all_shown"] = not bad
    return out, shown, cs

def main():
    out_p = sys.argv[1] if len(sys.argv) > 1 else None; n_seeds = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    cfg = load_cfg(); books = [json.load(open(V6 / p)) for p in OLD_BOOKS]; frz = books[0]
    excl0 = strict_excl(books); res = []; newset = set(NEW_ROLES)
    old_words = set()
    for b in books:
        for e in b["entries"].values(): old_words |= set(re.findall(r"[a-z]+", e["text"].lower()))
        for cs in b["cases"].values():
            for x in cs: old_words |= set(re.findall(r"[a-z]+", x["text"].lower()))
    for i in range(n_seeds):
        s = 99000 + 100 * i; r = dict(seed=s); t0 = time.time()
        try:
            D, cd = build(cfg, "dev", s, 3 * DEV_PER_PAIR * 2, NEW_ROLES, excl0, frz)
            dcore = first_distinct(D, "F2", DEV_PER_PAIR * len(NEW_ROLES), per=DEV_PER_PAIR)
            assert len(dcore) == DEV_PER_PAIR * len(NEW_ROLES), f"dev-new: only {len(dcore)} cores"
            dchk, dshown, dcs = checks(D, cd, dcore, excl0); r["dev_new"] = dict(core=len(dcore), shown_entries=len(dshown), cases=len(dcs), **dchk)
            texts, cases, ids, ct, ce = excl0
            excl1 = (texts | {norm(D["entries"][x]["text"]) for x in dshown}, cases | {norm(x["text"]) for x in dcs},
                     ids | set(dshown), ct, ce)
            T, ct_ = build(cfg, "test", s + 50, TEST_PER_FAM, NEW_ROLES, excl1, frz)
            core = {f: first_distinct(T, f, TEST_PER_FAM) for f in ("F1", "F2")}
            for f in core: assert len(core[f]) == TEST_PER_FAM, f"TEST: only {len(core[f])} distinct {f} cores"
            allc = core["F1"] + core["F2"]; tchk, tshown, tcs = checks(T, ct_, allc, excl1)
            pairs = {}
            for k in core["F2"]: e = T["entries"][k]; pairs[f"{e['x']}/{e['y']}"] = pairs.get(f"{e['x']}/{e['y']}", 0) + 1
            r["test"] = dict(core_F1=len(core["F1"]), core_F2=len(core["F2"]), cases=len(tcs), F2_by_pair=pairs,
                             F2_new_pair=sum(v for p, v in pairs.items() if tuple(p.split("/")) in newset), **tchk)
            sp = {norm(C.render_def(dict(fam="F2", x=x, y=y, sem=dict(xr=a, yr=b)))) for x, y in NEW_ROLES for a in range(2, 10) for b in range(2, 10) if a != b}
            dsh = {norm(D["entries"][x]["text"]) for x in dshown}; tco = {norm(T["entries"][k]["text"]) for k in core["F2"]}
            tsh = {norm(T["entries"][x]["text"]) for x in tshown if T["entries"][x]["fam"] == "F2"}
            r["new_pair_F2_space"] = dict(total=len(sp), used_by_dev_new_shown=len(sp & dsh), test_cores=len(sp & tco),
                                          left_after_test_cores=len(sp - dsh - tco), left_after_all_test_shown=len(sp - dsh - tsh))
            r["built"] = all(v is True for d in (dchk, tchk) for v in d.values())
        except (AssertionError, RuntimeError) as ex:
            r["built"] = False; r["error"] = f"{type(ex).__name__}: {str(ex)[:200]}"
        r["seconds"] = round(time.time() - t0, 1); res.append(r); print(json.dumps(r), flush=True)
    summ = dict(seeds=[r["seed"] for r in res], built=sum(r["built"] for r in res), n=len(res), rule="authoritative if >= 8 of 10 build",
                new_roles=NEW_ROLES, role_words_in_old_books=sorted(w for p in NEW_ROLES for w in p if w in old_words),
                dev_per_new_pair=DEV_PER_PAIR, test_core_per_family=TEST_PER_FAM, trials=res)
    if out_p: Path(out_p).write_text(json.dumps(summ, indent=1) + "\n")
    print(json.dumps({k: v for k, v in summ.items() if k != "trials"}))

if __name__ == "__main__": main()
