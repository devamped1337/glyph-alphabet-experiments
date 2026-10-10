"""Tables: cluster (group) bootstrap CIs per receiver x sender x condition x task|question; seeds reported separately and pooled.
Only COUNTED task|questions (frozen5.json) enter headline tables; dropped ones are listed. -> results/tables5.json + TABLES_v5.md"""
import sys
from common5 import *
def cboot(rows, f="correct", n=2000, seed=0):
    g = {}
    for r in rows:
        if r.get(f) is not None: g.setdefault(r["group"], []).append(r[f])
    if not g: return None
    G = list(g.values()); s = np.array([sum(x) for x in G], float); c = np.array([len(x) for x in G], float); r_ = np.random.default_rng(seed)
    idx = r_.integers(0, len(G), (n, len(G))); b = s[idx].sum(1) / c[idx].sum(1)
    return [float(s.sum() / c.sum()), float(np.quantile(b, .025)), float(np.quantile(b, .975)), int(c.sum()), len(G)]
names = sys.argv[1:] or [f"test_{rk}.json" for rk in MODELS]
FZ = load("frozen5.json") if os.path.exists(os.path.join(OUT, "frozen5.json")) else None
T = {"cells": {}, "dropped": {}, "follow": {}, "maths": {}, "seeds": {}, "bytes": {}}
md = ["# v5 tables (generated)", "", "mean [95% cluster-bootstrap CI] (n queries / n groups)", ""]
for nm in names:
    if not os.path.exists(os.path.join(OUT, nm)): continue
    d = load(nm); rk = d["receiver"]; rows = [r for r in d["rows"] if "correct" in r]
    if FZ and d["phase"] == "test": T["dropped"][rk] = sorted({f"{r['t']}|{r['q']}" for r in rows} - set(FZ["counted"][rk]))
    cells = {}
    for r in rows: cells.setdefault((f"{r['t']}|{r['q']}", r["cond"], r.get("sender", "-"), r.get("basis", "-"), str(r.get("seed", "-"))), []).append(r)
    md += [f"## receiver {rk} ({nm})", "", "| task | cond | sender | basis | seed | acc | follows (swap/operand) | magnitude | sign |", "|---|---|---|---|---|---|---|---|---|"]
    for k in sorted(cells):
        v = cells[k]; a = cboot(v); fo = cboot(v, "follows") if "follows" in v[0] else None
        mg = cboot(v, "magnitude") if k[0].startswith("t3") else None; sg = cboot(v, "sign") if k[0].startswith("t3") else None
        T["cells"]["|".join((rk,) + k)] = {"acc": a, "follows": fo, "magnitude": mg, "sign": sg}
        f = lambda x: "-" if not x else f"{x[0]:.3f} [{x[1]:.3f}, {x[2]:.3f}] ({x[3]}/{x[4]})"
        md.append(f"| {k[0]} | {k[1]} | {k[2]} | {k[3]} | {k[4]} | {f(a)} | {f(fo)} | {f(mg)} | {f(sg)} |")
    # seeds pooled for glyph_id per basis
    for bas in BASES:
        for sk in MODELS:
            per = {s: [r for r in rows if r["cond"] == "glyph_id" and r.get("basis") == bas and r.get("seed") == s and r.get("sender") == sk] for s in SEEDS}
            ms = [np.mean([r["correct"] for r in v]) for v in per.values() if v]
            if ms: T["seeds"][f"{rk}|{sk}|{bas}"] = {"per_seed": [float(x) for x in ms], "mean": float(np.mean(ms)), "sd": float(np.std(ms, ddof=1)) if len(ms) > 1 else None}
    md.append("")
save(T, "tables5.json"); open(os.path.join(OUT, "TABLES_v5.md"), "w").write("\n".join(md)); print("\n".join(md[:80]))
