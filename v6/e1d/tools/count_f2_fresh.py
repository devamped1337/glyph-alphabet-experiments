"""E1d (DRAFT): count fresh F1/F2 rule texts under the E1d exclusion list, and simulate whether the frozen builder
procedure (2n core draws, keep the first n distinct) can fill dev and TEST. CPU only, reads the old books, builds no
book, calls no model.  python v6/e1d/tools/count_f2_fresh.py [out.json]

APPROXIMATE: the fill simulation is a simplified occupancy model (dev cores drawn from the whole pool, each
neighbour generated once, no builder rejection rules). The authoritative feasibility check is the real builder,
tools/builder_trials.py (DRAFT_PLAN v4 §7).

Exclusion list (DRAFT_PLAN §7): every entry text of ANY kind, every case text and every entry ID in the E1b frozen
book, the E1b A9 book, the E1c dev book and the E1c TEST book (strict; stricter than E1c's true-rule rule)."""
import sys, json, random, copy
from pathlib import Path
V6 = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(V6 / "e1b"), str(V6 / "e1c")]
from e1b import norm
from e1b.cases import ROLES, NOUNS, UNITS, render_def, neighbour_params
from e1c.book import _old_rule_texts

NEW_ROLES = [("baker", "porter"), ("potter", "bearer"), ("tanner", "loader"),
             ("farmer", "packer"), ("cooper", "driver"), ("grocer", "runner")]   # order = order of adoption
OLD_BOOKS = ["e1b/data/cases_e1b.json", "e1b/data/cases_e1b_a9.json", "e1c/data/book_dev.json", "e1c/data/book_test.json"]
RATES = range(2, 10)

def f2(x, y, a, b): return dict(fam="F2", x=x, y=y, sem=dict(xr=a, yr=b))
def space(roles): return {norm(render_def(f2(x, y, a, b))): (x, y, a, b) for x, y in roles for a in RATES for b in RATES if a != b}

def simulate(pool, n_dev, n_test, trials, seed):
    """Uniform draws from the fresh pool (the builder's rejection sampling is uniform over non-forbidden texts).
    Dev: 2*n_dev draws, keep n_dev distinct; their texts AND in-pool neighbour texts are then excluded.
    TEST: 2*n_test draws must contain >= n_test distinct texts. Returns the share of trials that fill both."""
    rng = random.Random(seed); keys = sorted(pool); ok = 0; left = []
    for _ in range(trials):
        avail = set(keys)
        seen, dev = set(), []
        for _ in range(2 * n_dev):
            k = keys[rng.randrange(len(keys))]
            if k not in seen and len(dev) < n_dev: seen.add(k); dev.append(k)
        if len(dev) < n_dev: continue
        for k in dev:
            x, y, a, b = pool[k]; e = f2(x, y, a, b); avail.discard(k)
            for j in range(3):
                p = neighbour_params(e, j, rng); t = norm(render_def(dict(fam="F2", **p))); avail.discard(t)
        av = sorted(avail); got = set()
        for _ in range(2 * n_test): got.add(av[rng.randrange(len(av))])
        if len(got) >= n_test: ok += 1; left.append(len(avail) - n_test)
    return ok / trials, (min(left) if left else None)

def main():
    books = [json.load(open(V6 / p)) for p in OLD_BOOKS]
    all_ent = {norm(e["text"]) for b in books for e in b["entries"].values()}
    true_r = set().union(*(_old_rule_texts(b) for b in books))
    old = space(ROLES)
    out = dict(old_books=OLD_BOOKS, new_roles=NEW_ROLES,
               F2_old_pair_space=len(old), F2_old_fresh_vs_old_true_rules_E1c_rule=len(set(old) - true_r),
               F2_old_fresh_vs_all_old_entry_texts_E1d_rule=len(set(old) - all_ent),
               F2_per_new_pair=len(space(NEW_ROLES[:1])))
    F1 = {norm(render_def(dict(fam="F1", g=g, unit=u, sem=dict(mem=a, non=b)))) for g in NOUNS for u in UNITS for a in RATES for b in RATES if a != b}
    out["F1_space"] = len(F1); out["F1_fresh_vs_all_old_entry_texts"] = len(F1 - all_ent)
    words = set()
    for b in books:
        for e in b["entries"].values(): words |= set(norm(e["text"]).replace(".", " ").replace(",", " ").replace("'", " ").split())
        for cs in b["cases"].values():
            for c in cs: words |= set(norm(c["text"]).replace(".", " ").replace(",", " ").replace("'", " ").replace("?", " ").split())
    out["new_role_words_seen_in_old_books"] = sorted(w for p in NEW_ROLES for w in p if w in words)
    out["new_role_words_colliding_with_old_roles_nouns_units"] = sorted(w for p in NEW_ROLES for w in p if w in {v for q in ROLES for v in q} | {x.lower() for x in NOUNS + UNITS})
    out["by_k"] = {}
    for k in range(1, 7):
        sp = space(ROLES + NEW_ROLES[:k]); fresh = {t: v for t, v in sp.items() if t not in all_ent}
        p, left = simulate(fresh, n_dev=4 * k, n_test=80, trials=2000, seed=99000 + k)
        out["by_k"][k] = dict(fresh_F2_texts=len(fresh), dev_new_core=4 * k, test_core_F2=80,
                              p_fill_dev_and_test=p, min_unused_after_test=left)
    sp = space(ROLES + NEW_ROLES[:3]); fresh = {t: v for t, v in sp.items() if t not in all_ent}
    out["k3_dev_sensitivity"] = {d: dict(zip(("p_fill_dev_and_test", "min_unused_after_test"), simulate(fresh, d, 80, 2000, 99100 + d)))
                                 for d in (12, 24)}
    s = json.dumps(out, indent=1)
    if len(sys.argv) > 1: Path(sys.argv[1]).write_text(s + "\n")
    print(s)

if __name__ == "__main__": main()
