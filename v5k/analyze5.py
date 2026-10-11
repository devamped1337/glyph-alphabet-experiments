"""Tables (audit-fixed): coverage, conditional accuracy and END-TO-END accuracy (unsupported deliveries = failures); paired cluster bootstrap of
accuracy differences with the pre-registered equivalence margin; dropped tasks from frozen5.json; LOO split by gate verdict; seeds per-seed and pooled.
-> results/tables5.json + results/TABLES_v5.md"""
import sys
from common5 import *
MARGIN = 0.05
def cboot(rows, f="correct", n=2000, seed=0):
    g = {}
    for r in rows:
        if not isinstance(r, dict): continue
        if r.get(f) is not None: g.setdefault(r["group"], []).append(r[f])
    if not g: return None
    G = list(g.values()); s = np.array([sum(x) for x in G], float); c = np.array([len(x) for x in G], float)
    idx = np.random.default_rng(seed).integers(0, len(G), (n, len(G))); b = s[idx].sum(1) / c[idx].sum(1)
    return [float(s.sum() / c.sum()), float(np.quantile(b, .025)), float(np.quantile(b, .975)), int(c.sum()), len(G)]
def e2e(r): return 0 if r.get("covered") == 0 else r.get("correct")
def is_overflow(r): return isinstance(r, dict) and r.get("pred") == "__OVERFLOW__"
def row_dicts(v):
    """keep only mapping rows (skip already-bootstrapped float lists / non-dicts)"""
    return [x for x in v if isinstance(x, dict)] if isinstance(v, list) else []
def paired(A, B, n=2000, seed=0):
    """A, B: {(mid,q): (group, value)}; paired cluster bootstrap of mean(A-B) over the common items"""
    ks = sorted(set(A) & set(B))
    if not ks: return None
    g = {}
    for k in ks: g.setdefault(A[k][0], []).append(A[k][1] - B[k][1])
    G = list(g.values()); s = np.array([sum(x) for x in G], float); c = np.array([len(x) for x in G], float)
    idx = np.random.default_rng(seed).integers(0, len(G), (n, len(G))); b = s[idx].sum(1) / c[idx].sum(1); lo, hi = float(np.quantile(b, .025)), float(np.quantile(b, .975))
    v = "equivalent" if lo >= -MARGIN and hi <= MARGIN else "A better" if lo > 0 else "B better" if hi < 0 else "inconclusive"
    return {"diff": float(s.sum() / c.sum()), "lo": lo, "hi": hi, "n": int(c.sum()), "groups": len(G), "verdict": v}
names = sys.argv[1:] or [f"test_{rk}.json" for rk in MODELS]
FZ = load("frozen5.json") if os.path.exists(os.path.join(OUT, "frozen5.json")) else None
GATE = load("gate5.json") if os.path.exists(os.path.join(OUT, "gate5.json")) else None
T = {"cells": {}, "dropped": {}, "paired": {}, "seeds": {}, "loo_by_gate": {}, "fallback": {}, "overflow": {}, "margin": MARGIN}
f = lambda x: "-" if not x else f"{x[0]:.3f} [{x[1]:.3f}, {x[2]:.3f}] ({x[3]}/{x[4]})"
md = ["# v5 tables (generated)", "", "mean [95% cluster-bootstrap CI] (n queries / n groups). cond acc = among covered deliveries; e2e = unsupported deliveries count as failures.", ""]
if FZ:
    for rk, det in FZ["task_gate_detail"].items(): T["dropped"][rk] = {x: v for x, v in det.items() if x not in FZ["counted"][rk]}
    md += ["## pre-registered task gate (dev)", "", "```", json.dumps({"counted": FZ["counted"], "dropped": T["dropped"]}, indent=1), "```", ""]
for nm in names:
    if not os.path.exists(os.path.join(OUT, nm)): continue
    d = load(nm); rk = d["receiver"]; R = d["rows"]
    n_ov = sum(1 for r in R if is_overflow(r)); T["overflow"][rk] = {"n": n_ov, "of": len(R)}
    if n_ov: print(f"  {rk}: skipping {n_ov}/{len(R)} __OVERFLOW__ rows", flush=True)
    fb = [r for r in R if r["cond"] == "unknown_id_fallback" and not is_overflow(r)]; T["fallback"][rk] = {"n": len(fb), "all_UNRECOGNIZED": all(r["correct"] for r in fb)}
    R = [r for r in R if r["cond"] != "unknown_id_fallback" and not is_overflow(r)]
    cells = {}
    for r in R: cells.setdefault((f"{r['t']}|{r['q']}", r["cond"], r.get("sender", "-"), r.get("basis", "-"), str(r.get("seed", "-"))), []).append(r)
    md += [f"## receiver {rk} ({nm})", "", "| task | cond | sender | basis | seed | coverage | cond acc | e2e acc | follows | magnitude | sign |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for k in sorted(cells):
        v = cells[k]; cov = cboot([{**r, "cov": 0 if r.get("covered") == 0 else 1} for r in v], "cov")
        ca = cboot([r for r in v if r.get("covered") != 0]); ea = cboot([{**r, "e": e2e(r)} for r in v], "e")
        fo = cboot([r for r in v if "follows" in r], "follows") if any("follows" in r for r in v) else None
        mg = cboot(v, "magnitude") if k[0].startswith("t3") else None; sg = cboot(v, "sign") if k[0].startswith("t3") else None
        T["cells"]["|".join((rk,) + k)] = {"coverage": cov, "cond_acc": ca, "e2e_acc": ea, "follows": fo, "magnitude": mg, "sign": sg}
        md.append(f"| {k[0]} | {k[1]} | {k[2]} | {k[3]} | {k[4]} | {f(cov)} | {f(ca)} | {f(ea)} | {f(fo)} | {f(mg)} | {f(sg)} |")
    # paired comparisons (e2e): glyph_id(pca,0) vs prose / id_text_expanded / compact / receiver_word_state
    def vec(cond, sk=None, basis=None, seed=None):
        out = {}
        for r in R:
            if r["cond"] == cond and (sk is None or r.get("sender") == sk) and (basis is None or r.get("basis") == basis) and (seed is None or r.get("seed") == seed):
                val = e2e(r)
                if val is not None: out[(r["mid"], r["q"], r["t"])] = (r["group"], val)
        return out
    md += ["", "| task | sender | A | B | diff A-B [95% paired CI] | verdict (margin ±0.05) |", "|---|---|---|---|---|---|"]
    for tq in sorted({k[0] for k in cells}):
        t, q = tq.split("|")
        for sk in MODELS:
            sel = lambda D_: {k: v for k, v in D_.items() if k[0] in {r["mid"] for r in R if r["t"] == t and r["q"] == q} and k[1] == q}
            A = sel(vec("glyph_id", sk, "pca", 0))
            for bn, B in (("text_prose", vec("text_prose")), ("id_text_expanded", vec("id_text_expanded", sk)), ("text_compact", vec("text_compact")), ("receiver_word_state", vec("receiver_word_state", sk))):
                p = paired(A, sel(B))
                if p: T["paired"][f"{rk}|{tq}|{sk}|glyph_id-vs-{bn}"] = p; md.append(f"| {tq} | {sk} | glyph_id | {bn} | {p['diff']:+.3f} [{p['lo']:+.3f}, {p['hi']:+.3f}] (n={p['n']}) | {p['verdict']} |")
    # LOO by gate verdict (collect rows only; bootstrap once after all receivers)
    if GATE:
        for r in R:
            if r["cond"] != "glyph_loo": continue
            ok = all(GATE["loo"].get(f"{r['li']}|{r['loo_symbol']}", {}).get("held_entries_pass", {}).values()) if GATE["loo"].get(f"{r['li']}|{r['loo_symbol']}") else None
            T["loo_by_gate"].setdefault(f"{rk}|{r['t']}|{r['q']}|{r['sender']}|{'gate_pass' if ok else 'gate_fail'}", []).append(r)
    for bas in BASES:
        for sk in MODELS:
            per = {s: [e2e(r) for r in R if r["cond"] == "glyph_id" and r.get("basis") == bas and r.get("seed") == s and r.get("sender") == sk and e2e(r) is not None] for s in SEEDS}
            ms = [float(np.mean(v)) for v in per.values() if v]
            if ms: T["seeds"][f"{rk}|{sk}|{bas}"] = {"per_seed_e2e": ms, "mean": float(np.mean(ms)), "sd": float(np.std(ms, ddof=1)) if len(ms) > 1 else None}
    md.append("")
# bootstrap LOO buckets once (values may be row lists; skip non-mapping leftovers)
T["loo_by_gate"] = {k: cboot([{**x, "e": e2e(x)} for x in row_dicts(v)], "e") for k, v in T["loo_by_gate"].items() if row_dicts(v)}
md += ["## LOO by gate verdict (e2e)", "", "```", json.dumps(T["loo_by_gate"], indent=0), "```", "", "## seeds", "```", json.dumps(T["seeds"], indent=0), "```",
       "", "## overflow rows skipped", "```", json.dumps(T["overflow"]), "```",
       "", "## UNRECOGNIZED fallback", "```", json.dumps(T["fallback"]), "```"]
save(T, "tables5.json"); open(os.path.join(OUT, "TABLES_v5.md"), "w").write("\n".join(md)); print("\n".join(md[:60]))
