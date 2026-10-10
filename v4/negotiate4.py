"""v4 three-party repository: per-model Delegates + a Keeper holding the versioned book.
-> results/v4/book.pt (all FRACS layers, main + ablation books), v4/book_v4.json (round log, checks, rules)"""
import sys, os, json, time, itertools, torch, numpy as np
sys.path.insert(0, "/workspace/glyph-exp/v4"); os.chdir("/workspace/glyph-exp")
from spec import *
KP, KC = 64, 32; t0 = time.time()
M = messages(); TR = [m for m in M if m["split"] == "train"]
unit = lambda x: x / (np.linalg.norm(x, axis=-1, keepdims=True) + 1e-12)
ST = {k: torch.load(f"results/v4/states_{k}.pt", weights_only=False) for k in MODELS}
BASE = {"ENT": ENT, "ACT": ACT, "MOD": MOD, "POL": POL, "ORD": ORD, "DIG": DIG, "OP": ["-"], "EQ": ["="]}
def entries_for(dom_syms):
    E = []
    for t, sl in SLOTS.items():
        for s in sl:
            d = DOMAIN[s]; syms = dom_syms[d]
            if t != "t1" and d in ("ENT", "ACT"): syms = [x for x in syms if x in BASE[d]]   # extension data exists only for t1
            E += [(t, s, y) for y in syms]
    return E
class Delegate:
    """one per model: holds its own states; builds native entries, trains its own read-out probes, proposes extensions, answers checks"""
    def __init__(self, key, li):
        self.key = key; X = ST[key]["book_states"][:, :, li].double().numpy(); self.X = X
        idx = [m["id"] for m in TR]; self.mu = np.concatenate([X[i, :len(SLOTS[M[i]["t"]])] for i in idx]).mean(0)
    def native(self, t, s, y):
        si = SLOTS[t].index(s); v = [self.X[m["id"], si] for m in TR if m["t"] == t and m[s] == y]
        return (np.mean(v, 0) - self.mu) if v else None
    def train_samples(self, ents):
        es = set(ents); rows, keys = [], []
        for m in TR:
            for si, s in enumerate(SLOTS[m["t"]]):
                if (m["t"], s, m[s]) in es: rows.append(self.X[m["id"], si] - self.mu); keys.append((m["id"], si))
        return np.array(rows), keys
    def probe(self, t, s, syms):
        si = SLOTS[t].index(s); Xs, Y = [], []
        for m in TR:
            if m["t"] == t and m[s] in syms: Xs.append(self.X[m["id"], si] - self.mu); Y.append(syms.index(m[s]))
        Xs = np.array(Xs); Yo = np.eye(len(syms))[Y] * 2 - 1
        return np.linalg.solve(Xs.T @ Xs + 10 * np.eye(Xs.shape[1]), Xs.T @ Yo)
    def propose(self, pool, existing, t="t1", s="agent"):
        """model-derived proposal: the pool candidate whose own native entry is farthest (cosine) from every existing entry in that slot"""
        best, bs = None, -1
        for c in pool:
            v = self.native(t, s, c)
            if v is None: continue
            sep = 1 - max(float(unit(v) @ unit(self.native(t, s, e))) for e in existing)
            if sep > bs: best, bs = c, sep
        return best, bs
class Keeper:
    def __init__(self, keys, li):
        self.keys = keys; self.D = {k: Delegate(k, li) for k in keys}; self.versions = []; self.log = []
    def fit(self, ents):
        Z0 = {}; keyref = None
        for k in self.keys:
            Z, kk = self.D[k].train_samples(ents); Z0[k] = Z; keyref = kk
        P = {}
        for k in self.keys:
            _, S, Vt = np.linalg.svd(Z0[k], full_matrices=False); P[k] = (Vt[:KP].T, (S[:KP] / np.sqrt(len(Z0[k]))) ** 0.5)
        Z = {k: (Z0[k] @ P[k][0]) / P[k][1] for k in self.keys}; _, _, vt = np.linalg.svd(Z[self.keys[0]], full_matrices=False)
        C = Z[self.keys[0]] @ vt[:KC].T
        for _ in range(40):
            Q = {}
            for k in self.keys: u, _, v2 = np.linalg.svd(Z[k].T @ C, full_matrices=False); Q[k] = u @ v2
            C = np.mean([Z[k] @ Q[k] for k in self.keys], 0)
        return {"P": P, "Q": Q}
    @staticmethod
    def enc(A, k, x): return ((x @ A["P"][k][0]) / A["P"][k][1]) @ A["Q"][k]
    @staticmethod
    def dec(A, k, c): return ((c @ A["Q"][k].T) * A["P"][k][1]) @ A["P"][k][0].T
    def build(self, ents, A):
        nat = {k: {e: self.D[k].native(*e) for e in ents} for k in self.keys}
        can = {k: {e: self.enc(A, k, nat[k][e]) for e in ents} for k in self.keys}
        sh = {e: np.mean([can[k][e] for k in self.keys], 0) for e in ents}
        return nat, can, sh
    def check(self, ents, A):
        nat, can, sh = self.build(ents, A); K = self.keys; res = {}
        slot_syms = {}
        for (t, s, y) in ents: slot_syms.setdefault((t, s), []).append(y)
        probes = {(k, ts): self.D[k].probe(*ts, syms) for k in K for ts, syms in slot_syms.items() if len(syms) > 1}
        def nn(vecs, q): return int((unit(np.stack(vecs)) @ unit(q)).argmax())
        rules = {}
        for (t, s), syms in slot_syms.items():
            gal = [(t, s, y) for y in syms]
            for e in gal:
                y = e[2]; r = {}
                r["meaning"] = all(gal[nn([can[j][g] for g in gal], can[i][e])] == e for i in K for j in K if i != j)
                rt = True
                for i in K:
                    for j in K:
                        if i == j: continue
                        jb = gal[nn([nat[j][g] for g in gal], self.dec(A, j, can[i][e]))]
                        ja = gal[nn([nat[i][g] for g in gal], self.dec(A, i, can[j][jb]))]
                        rt &= ja == e
                r["roundtrip"] = bool(rt); r["keeper"] = all(gal[nn([can[k][g] for g in gal], sh[e])] == e for k in K)
                r["readability"] = all(syms[int((self.dec(A, k, sh[e]) @ probes[(k, (t, s))]).argmax())] == y for k in K) if len(syms) > 1 else True
                # geometry rules
                d = DOMAIN[s]; pair = {"agent": "patient", "patient": "agent", "a1": "a2", "a2": "a1", "left": "right", "right": "left"}.get(s)
                if pair and (t, pair, y) in sh:
                    lo, hi = sorted([s, pair], key=lambda z: SLOTS[t].index(z))
                    off = {k: can[k][(t, hi, y)] - can[k][(t, lo, y)] for k in K}; rule = f"role:{t}:{lo}->{hi}"
                elif d in ("MOD", "POL", "ORD"):
                    a, b = BASE[d]; off = {k: can[k][(t, s, b)] - can[k][(t, s, a)] for k in K}; rule = f"qualifier:{t}:{s}:{a}->{b}"
                elif len(syms) > 1:
                    off = {k: can[k][e] - np.mean([can[k][g] for g in gal], 0) for k in K}; rule = None
                else: off = None; rule = None
                if off is not None:
                    cs = [float(unit(off[i]) @ unit(off[j])) for i, j in itertools.combinations(K, 2)]
                    r["geometry_min_pair_cos"] = min(cs); r["geometry"] = min(cs) >= 0.5
                    if rule: rules.setdefault(rule, []).append(min(cs))
                else: r["geometry"] = True; r["geometry_min_pair_cos"] = None; r["trivial_single_entry"] = True
                r["pass"] = bool(r["meaning"] and r["roundtrip"] and r["keeper"] and r["readability"] and r["geometry"]); res[e] = r
        return res, {k: float(np.min(v)) for k, v in rules.items()}
    def push(self, ents, A, note, res, rules):
        v = f"4.{len(self.versions)}"; nat, can, sh = self.build(ents, A)
        self.versions.append({"version": v, "entries": list(ents), "A": A, "native": nat, "can": can, "shared": sh, "mu": {k: self.D[k].mu for k in self.keys},
                              "rules": rules, "note": note})
        return v
    def run(self):
        dom = {d: list(v) for d, v in BASE.items()}; ents = entries_for(dom); rnd = 0
        while True:          # base negotiation: prune until stable
            rnd += 1; A = self.fit(ents); res, rules = self.check(ents, A); fail = [e for e in ents if not res[e]["pass"]]
            self.log.append({"round": rnd, "kind": "base", "n_entries": len(ents), "n_pass": len(ents) - len(fail), "rejected": [list(e) for e in fail],
                             "rates": {c: float(np.mean([r[c] for r in res.values()])) for c in ("meaning", "roundtrip", "keeper", "readability", "geometry")}, "rules": rules})
            if not fail: break
            ents = [e for e in ents if e not in fail]
            if rnd >= 6: break
        v = self.push(ents, A, "base alphabet", res, rules); self.log[-1]["version"] = v
        pools = {"ENT": [x for x in EXT_ENT], "ACT": [x for x in EXT_ACT]}
        for turn in range(6):        # delegates take turns proposing one extension; all must reproduce it
            k = self.keys[turn % len(self.keys)]; dname = ["ENT", "ACT"][(turn // len(self.keys)) % 2]
            if not pools[dname]: continue
            cur = [e[2] for e in ents if e[:2] == ("t1", "agent" if dname == "ENT" else "act")]
            c, sep = self.D[k].propose(pools[dname], cur, "t1", "agent" if dname == "ENT" else "act"); pools[dname].remove(c)
            prop = [("t1", s, c) for s in (["agent", "patient"] if dname == "ENT" else ["act"])]
            cand = ents + prop; rnd += 1; A2 = self.fit(cand); res2, rules2 = self.check(cand, A2)
            ok = all(res2[e]["pass"] for e in cand)
            entry = {"round": rnd, "kind": "proposal", "proposer": k, "proposal": c, "domain": dname, "proposer_separability": sep, "accepted": ok,
                     "failed_checks": {"|".join(e): [x for x in ("meaning", "roundtrip", "keeper", "readability", "geometry") if not res2[e][x]] for e in cand if not res2[e]["pass"]}}
            if ok: ents = cand; A, res, rules = A2, res2, rules2; entry["version"] = self.push(ents, A, f"{k} proposal {c} accepted; adapters refit", res, rules)
            self.log.append(entry)
        self.final_res = res
        return ents
out = {"layers": {}}; rep = {"layers": {}}
for li in range(len(FRACS)):
    kp = Keeper(list(MODELS), li); ents = kp.run()
    for e in kp.log: print(li, {a: b for a, b in e.items() if a not in ("rules",)}, flush=True)
    # ablation books: (i) no negotiation filters: every candidate incl. pool, adapters fit on all; (ii) two models only (qwen+smol), negotiated
    allents = entries_for({**BASE, "ENT": ENT + EXT_ENT, "ACT": ACT + EXT_ACT})
    nf = Keeper(list(MODELS), li); Anf = nf.fit(allents); nf.push(allents, Anf, "NO FILTERS (ablation)", {}, {})
    tw = Keeper(["qwen", "smol"], li); tw.run()
    out["layers"][li] = {"layer": {k: ST[k]["layers"][li] for k in MODELS}, "main": kp.versions[-1], "all_versions": [v["version"] for v in kp.versions],
                         "nofilter": nf.versions[-1], "twomodel": tw.versions[-1]}
    rep["layers"][str(li)] = {"frac": FRACS[li], "layer": out["layers"][li]["layer"], "log": kp.log, "final_version": kp.versions[-1]["version"],
                              "n_entries": len(ents), "rules": kp.versions[-1]["rules"],
                              "final_checks": {"|".join(e): r for e, r in kp.final_res.items()}, "twomodel_log": tw.log, "nofilter_n_entries": len(allents)}
torch.save(out, "results/v4/book.pt"); json.dump(rep, open("v4/book_v4.json", "w"), indent=1, default=str)
print(f"negotiation total {time.time()-t0:.1f}s")
