"""Box-side: books (codebooks) for every (layer key x basis x seed), negotiation gate, leave-one-entry-out (LOO) books,
planted bad entries, null adapters, the confusable-entry selection test, and per-receiver delivery files.
usage: negotiate5.py   (needs results/states_smol.pt and results/states_qwen.pt, sha256-verified)
out: book5.pt, gate5.json, selection5.json, deliveries_smol.pt, deliveries_qwen.pt"""
import sys, itertools
from common5 import *
t0 = time.time(); KEYS = list(MODELS); M = messages()
ST = {k: load(f"states_{k}.pt") for k in KEYS}
mids = sorted(set.intersection(*[set(ST[k]["mids"]) for k in KEYS])); row = {k: {m: i for i, m in enumerate(ST[k]["mids"])} for k in KEYS}
MM = [M[i] for i in mids]; NLK = len(ST[KEYS[0]]["keys"])
LK = {k: ST[k]["keys"] for k in KEYS}                     # per-model layer keys; index li is aligned across models (emb, frac0, frac1)
def X(k, li, kind="book_states"):
    return ST[k][kind][[row[k][m] for m in mids]][:, :, li].float().numpy()      # [N,5,d] float32, rows aligned with MM
unit = lambda x: x / (np.linalg.norm(x, axis=-1, keepdims=True) + 1e-12)
TR = [j for j, m in enumerate(MM) if m["split"] == "train"]
def all_entries():
    E = []
    for t, sl in SLOTS.items():
        for s in sl: E += [(t, s, y) for y in DOMAIN[s]]
    return E
def enc(A, k, x): B, sc = A["P"][k]; return ((x @ B) / sc) @ A["Q"][k]
def dec(A, k, c): B, sc = A["P"][k]; return ((c @ A["Q"][k].T) * sc) @ B.T
class Layer:
    """all model-side data at one aligned layer index"""
    def __init__(self, li):
        self.li = li; self.Xb = {k: X(k, li) for k in KEYS}; self.Xs = {k: X(k, li, "sender_states") for k in KEYS}
        self.mu = {k: np.concatenate([self.Xb[k][j, :len(SLOTS[MM[j]["t"]])] for j in TR]).mean(0) for k in KEYS}
        self.probes = {}
    def rows(self, ents, msg_idx):
        es = set(ents); R = []
        for j in msg_idx:
            m = MM[j]
            for si, s in enumerate(SLOTS[m["t"]]):
                if (m["t"], s, m[s]) in es: R.append((j, si))
        return R
    def Z(self, k, R): return np.stack([self.Xb[k][j, si] for j, si in R]) - self.mu[k]
    def native(self, k, e, exclude=None):
        t, s, y = e; si = SLOTS[t].index(s); v = [self.Xb[k][j, si] for j in TR if MM[j]["t"] == t and MM[j][s] == y]
        return (np.mean(v, 0) - self.mu[k]) if v else None
    def probe(self, k, t, s, syms):
        key = (k, t, s, tuple(syms))
        if key not in self.probes:
            si = SLOTS[t].index(s); idx = [j for j in TR if MM[j]["t"] == t and MM[j][s] in syms]
            Xs = np.stack([self.Xb[k][j, si] for j in idx]).astype(np.float64) - self.mu[k]; Yo = np.eye(len(syms))[[syms.index(MM[j][s]) for j in idx]] * 2 - 1
            self.probes[key] = np.linalg.solve(Xs.T @ Xs + 10 * np.eye(Xs.shape[1]), Xs.T @ Yo)
        return self.probes[key]
def basis(L, k, Z, kind, seed):
    if kind == "pca": B = np.linalg.svd(Z, full_matrices=False)[2][:KP].T
    elif kind == "jlens":
        jl = ST[k]["jlens"]; kk = LK[k][L.li]
        if not jl or kk not in jl: return None
        B = jl[kk]["evecs"].double().numpy()
    else: B = np.linalg.qr(np.random.default_rng(1000 + seed).standard_normal((Z.shape[1], KP)))[0]
    sc = (Z @ B).std(0) ** 0.5 + 1e-6; return (B, sc)
def gpa(Zp, perm=None):
    """generalized Procrustes into KC dims. perm: optional row permutation applied to the FIRST model (shuffled-pair null)"""
    if perm is not None: Zp = {**Zp, KEYS[0]: Zp[KEYS[0]][perm]}
    _, _, vt = np.linalg.svd(Zp[KEYS[0]], full_matrices=False); C = Zp[KEYS[0]] @ vt[:KC].T
    for _ in range(40):
        Q = {}
        for k in KEYS: u, _, v2 = np.linalg.svd(Zp[k].T @ C, full_matrices=False); Q[k] = u @ v2
        C = np.mean([Zp[k] @ Q[k] for k in KEYS], 0)
    return Q
def fit(L, ents, kind, seed, frac=0.8, exclude_sym=None, shuffle=False):
    rng = np.random.default_rng(seed); msg = [j for j in TR if rng.random() < frac]
    R = L.rows(ents, msg)
    if exclude_sym is not None: R = [(j, si) for j, si in R if MM[j][SLOTS[MM[j]["t"]][si]] != exclude_sym]
    Z0 = {k: L.Z(k, R).astype(np.float64) for k in KEYS}; P = {}
    for k in KEYS:
        b = basis(L, k, Z0[k], kind, seed)
        if b is None: return None
        P[k] = b
    Zp = {k: (Z0[k] @ P[k][0]) / P[k][1] for k in KEYS}
    Q = gpa(Zp, rng.permutation(len(R)) if shuffle else None)
    return {"P": P, "Q": Q, "n_rows": len(R)}
def build(L, ents, A, override=None):
    nat = {k: {e: L.native(k, e) for e in ents} for k in KEYS}
    if override:
        for k in KEYS: nat[k].update(override[k])
    can = {k: {e: enc(A, k, nat[k][e]) for e in ents} for k in KEYS}; sh = {e: np.mean([can[k][e] for k in KEYS], 0) for e in ents}
    return nat, can, sh
def nn(vecs, q): return int((unit(np.stack(vecs)) @ unit(q)).argmax())
def check(L, ents, A, override=None):
    nat, can, sh = build(L, ents, A, override); res = {}; slot = {}
    for e in ents: slot.setdefault(e[:2], []).append(e[2])
    for (t, s), syms in slot.items():
        gal = [(t, s, y) for y in syms]
        pr = {k: L.probe(k, t, s, [y for y in syms if L.native(k, (t, s, y)) is not None]) for k in KEYS} if len(syms) > 1 else None
        for e in gal:
            r = {"meaning": all(gal[nn([can[j][g] for g in gal], can[i][e])] == e for i in KEYS for j in KEYS if i != j)}
            rt = True
            for i in KEYS:
                for j in KEYS:
                    if i == j: continue
                    jb = gal[nn([nat[j][g] for g in gal], dec(A, j, can[i][e]))]; ja = gal[nn([nat[i][g] for g in gal], dec(A, i, can[j][jb]))]; rt &= ja == e
            r["roundtrip"] = bool(rt); r["keeper"] = all(gal[nn([can[k][g] for g in gal], sh[e])] == e for k in KEYS)
            if pr:
                rd = True
                for k in KEYS:
                    ps = [y for y in syms if L.native(k, (t, s, y)) is not None]
                    rd &= (e[2] not in ps) or ps[int((dec(A, k, sh[e]) @ pr[k]).argmax())] == e[2]
                r["readability"] = bool(rd)
            else: r["readability"] = True
            if len(syms) > 1:
                off = {k: can[k][e] - np.mean([can[k][g] for g in gal], 0) for k in KEYS}
                r["geometry_cos"] = float(unit(off[KEYS[0]]) @ unit(off[KEYS[1]])); r["geometry"] = r["geometry_cos"] >= 0.5
            else: r["geometry"] = True
            r["pass"] = bool(r["meaning"] and r["roundtrip"] and r["keeper"] and r["readability"] and r["geometry"]); res[e] = r
    return res
def negotiate(L, kind, seed, ents=None, **kw):
    ents = [e for e in (ents or all_entries()) if all(L.native(k, e) is not None for k in KEYS)]; log = []
    for rnd in range(4):
        A = fit(L, ents, kind, seed, **kw)
        if A is None: return None
        res = check(L, ents, A); fail = [e for e in ents if not res[e]["pass"]]
        log.append({"round": rnd, "n": len(ents), "rejected": ["|".join(e) for e in fail]})
        if not fail: break
        ents = [e for e in ents if e not in fail]
    nat, can, sh = build(L, ents, A)
    return {"entries": ents, "A": A, "native": nat, "can": can, "shared": sh, "mu": L.mu, "log": log, "kind": kind, "seed": seed, "li": L.li}
def snap(book, k, t, xs, topk=5):
    """sender k snaps each slot vector to its OWN canonical gallery; returns chosen symbols and per-slot ranked symbols"""
    ch, rk = [], []
    for si, s in enumerate(SLOTS[t]):
        gal = [e for e in book["entries"] if e[:2] == (t, s)]
        if not gal: ch.append(None); rk.append([]); continue
        c = enc(book["A"], k, xs[si] - book["mu"][k]); sc = unit(np.stack([book["can"][k][g] for g in gal])) @ unit(c); o = np.argsort(-sc)
        ch.append(gal[o[0]][2]); rk.append([gal[i][2] for i in o[:topk]])
    return ch, rk
def boot(v, n=2000, seed=0):
    v = np.asarray(v, float)
    if len(v) == 0: return [None, None, None, 0]
    r = np.random.default_rng(seed); b = v[r.integers(0, len(v), (n, len(v)))].mean(1)
    return [float(v.mean()), float(np.quantile(b, .025)), float(np.quantile(b, .975)), len(v)]

BOOKS, GATE, SEL = {}, {"books": {}, "loo": {}, "planted": {}}, {}
LOO_SYMS = ENT + PLACES
NULLS = {}
for li in range(NLK):
    L = Layer(li); tl = time.time()
    for kind in BASES:
        for seed in SEEDS:
            b = negotiate(L, kind, seed)
            if b is None: print("skip", li, kind, seed, "(no J-lens subspace in states)"); continue
            BOOKS[(li, kind, seed)] = b; GATE["books"][f"{li}|{kind}|{seed}"] = {"n_entries": len(b["entries"]), "log": b["log"]}
            print("book", li, LK[KEYS[0]][li], kind, seed, len(b["entries"]), b["log"][-1]["round"], f"{time.time()-t0:.0f}s", flush=True)
    base = BOOKS[(li, "pca", 0)]
    # null adapters (pca, seed 0): random orthogonal Q for the sender side; shuffled-pair Procrustes
    Ar = base["A"]; rq = {k: np.linalg.qr(np.random.default_rng(77 + i).standard_normal((KP, KC)))[0] for i, k in enumerate(KEYS)}
    NULLS[li] = {"randorth": {"P": Ar["P"], "Q": rq, "realQ": Ar["Q"]}, "shufpair": fit(L, base["entries"], "pca", 0, shuffle=True)}
    # LOO: refit without the symbol's rows, rebuild the entry from natives, gate it
    loo = {}
    for y in LOO_SYMS:
        if os.environ.get("SMOKE") and y not in (ENT[0], PLACES[1]): continue
        A = fit(L, base["entries"] + [e for e in all_entries() if e[2] == y and e not in base["entries"]], "pca", 0, exclude_sym=y)
        ents = sorted(set(base["entries"]) | {e for e in all_entries() if e[2] == y}, key=str)
        ents = [e for e in ents if L.native(KEYS[0], e) is not None and L.native(KEYS[1], e) is not None]
        res = check(L, ents, A); held = [e for e in ents if e[2] == y]; nat, can, sh = build(L, ents, A)
        loo[y] = {"entries": ents, "A": A, "native": nat, "can": can, "shared": sh, "mu": L.mu}
        GATE["loo"][f"{li}|{y}"] = {"held_entries_pass": {"|".join(e): res[e]["pass"] for e in held},
                                    "held_failed_checks": {"|".join(e): [c for c in ("meaning", "roundtrip", "keeper", "readability", "geometry") if not res[e][c]] for e in held},
                                    "collateral_rejections": ["|".join(e) for e in ents if e[2] != y and not res[e]["pass"]], "n_rows": A["n_rows"]}
    BOOKS[(li, "loo")] = loo
    # planted bad entries: "Zed" = Alice-agent states in model 0 but Bob-agent states in model 1; "Noise" = random vector at the norm of a real entry
    for name in ("Zed", "Noise"):
        e = ("t1", "agent", name); r0 = np.random.default_rng(5)
        if name == "Zed": ov = {KEYS[0]: {e: L.native(KEYS[0], ("t1", "agent", "Alice"))}, KEYS[1]: {e: L.native(KEYS[1], ("t1", "agent", "Bob"))}}
        else: ov = {k: {e: unit(r0.standard_normal(L.mu[k].shape)) * np.linalg.norm(L.native(k, ("t1", "agent", "Alice")))} for k in KEYS}
        ents = base["entries"] + [e]; res = check(L, ents, base["A"], ov)
        GATE["planted"][f"{li}|{name}"] = {"pass": res[e]["pass"], "checks": {c: res[e][c] for c in ("meaning", "roundtrip", "keeper", "readability", "geometry")},
                                         "collateral_rejections": ["|".join(x) for x in ents if x != e and not res[x]["pass"]]}
    # selection test (confusable places + t1 agents): own-gallery snap top-k, confusion, cross-model gallery, string-match baseline
    for (kli, kind, seed), b in [(kk, v) for kk, v in BOOKS.items() if kk[0] == li and len(kk) == 3]:
        for sk in KEYS:
            other = [k for k in KEYS if k != sk][0]
            for split in ("dev", "test"):
                for task, slot in (("t4", "place"), ("t1", "agent")):
                    gal = [e for e in b["entries"] if e[:2] == (task, slot)]; syms = [e[2] for e in gal]; si = SLOTS[task].index(slot)
                    idx = [j for j, m in enumerate(MM) if m["t"] == task and m["split"] == split and m[slot] in syms]
                    if not idx: continue
                    cm = np.zeros((len(syms), len(syms)), int); rows = []
                    for j in idx:
                        m = MM[j]; x = L.Xs[sk][j, si] - L.mu[sk]; c = enc(b["A"], sk, x)
                        own = np.argsort(-(unit(np.stack([b["can"][sk][g] for g in gal])) @ unit(c)))
                        cross = int(np.argmax(unit(np.stack([b["can"][other][g] for g in gal])) @ unit(c)))
                        cm[syms.index(m[slot]), own[0]] += 1
                        sm = string_match(sender_text(task, m), syms)[0] if task == "t4" else None
                        rows.append({"kind": "clue" if m.get("clue") else "name", "top1": int(syms[own[0]] == m[slot]), "top3": int(m[slot] in [syms[i] for i in own[:3]]),
                                     "top5": int(m[slot] in [syms[i] for i in own[:5]]), "cross_top1": int(syms[cross] == m[slot]),
                                     "same_country_top1": int(COUNTRY.get(syms[own[0]]) == COUNTRY.get(m[slot])) if task == "t4" else None,
                                     "string_baseline": int(sm == m[slot]) if sm else None})
                    out = {"symbols": syms, "confusion": cm.tolist()}
                    for kd in ("name", "clue"):
                        rr = [r for r in rows if r["kind"] == kd]
                        if rr: out[kd] = {f: boot([r[f] for r in rr if r[f] is not None]) for f in ("top1", "top3", "top5", "cross_top1", "same_country_top1", "string_baseline") if rr[0][f] is not None}
                    SEL[f"{li}|{kind}|{seed}|{sk}|{split}|{task}"] = out
    # null-adapter cross-model selection (test, place + agent): sender raw vector vs other model's gallery
    for name, A in (("real", base["A"]), ("randorth", {"P": base["A"]["P"], "Q": {**base["A"]["Q"], **{k: rq[k] for k in KEYS}}}), ("shufpair", NULLS[li]["shufpair"])):
        nat, can, sh = build(L, base["entries"], A)
        for sk in KEYS:
            other = [k for k in KEYS if k != sk][0]; acc = []
            for task, slot in (("t4", "place"), ("t1", "agent")):
                gal = [e for e in base["entries"] if e[:2] == (task, slot)]; si = SLOTS[task].index(slot)
                for j, m in enumerate(MM):
                    if m["t"] == task and m["split"] == "test" and (task, slot, m[slot]) in gal and not m.get("clue"):
                        acc.append(int(gal[nn([can[other][g] for g in gal], enc(A, sk, L.Xs[sk][j, si] - L.mu[sk]))][2] == m[slot]))
            SEL[f"{li}|null:{name}|0|{sk}|test|cross"] = boot(acc)
    print("layer", li, "done", f"{time.time()-tl:.0f}s", flush=True)
    del L
save(GATE, "gate5.json"); save(SEL, "selection5.json")

# ---------- deliveries: what each receiver needs (decoders, entry tables, per-message codes) ----------
FLIP = {"known": "suspected", "suspected": "known", "indeed": "never", "never": "indeed", "before": "after", "after": "before"}
def swap_msg(t, q, m):
    m2 = dict(m)
    if t == "t1" and q in ("agent", "patient"): m2["agent"], m2["patient"] = m["patient"], m["agent"]
    elif t == "t1": m2[q] = FLIP[m[q]]
    elif t == "t2": m2["ord"] = FLIP[m["ord"]]
    elif t == "t3": m2["left"], m2["right"] = m["right"], m["left"]
    else: return None
    return m2
def operand_msg(t, m, rng):
    """change ONE operand to a different in-book symbol: t3 left digit; t1 agent; t4 place"""
    m2 = dict(m); s = {"t3": "left", "t1": "agent", "t4": "place"}.get(t)
    if s is None: return None
    pool = [y for y in DOMAIN[s] if y != m[s] and (t != "t1" or y != m["patient"])]; m2[s] = pool[rng.integers(len(pool))]; return m2
for rk in KEYS:
    D = {"receiver": rk, "keys": LK[rk], "decoders": {}, "books": {}, "msgs": {}, "env": env_info(), "commit": commit()}
    def add_dec(name, A, mu): B, sc = A["P"][rk]; D["decoders"][name] = {"B": torch.tensor(B, dtype=torch.float32), "sc": torch.tensor(sc, dtype=torch.float32), "Q": torch.tensor(A["Q"][rk], dtype=torch.float32), "mu": torch.tensor(mu[rk], dtype=torch.float32)}
    for kk, b in BOOKS.items():
        if len(kk) == 3:
            name = f"{kk[0]}|{kk[1]}|{kk[2]}"; add_dec(name, b["A"], b["mu"])
            D["books"][name] = {"entries": b["entries"], "shared": {e: torch.tensor(b["shared"][e], dtype=torch.float32) for e in b["entries"]},
                                "native": {e: torch.tensor(b["native"][rk][e], dtype=torch.float32) for e in b["entries"]} if kk[1:] == ("pca", 0) else None}
        else:
            for y, lb in b.items(): add_dec(f"{kk[0]}|loo|{y}", lb["A"], lb["mu"]); D["books"][f"{kk[0]}|loo|{y}"] = {"entries": lb["entries"], "shared": {e: torch.tensor(lb["shared"][e], dtype=torch.float32) for e in lb["entries"]}, "native": None}
    for li in range(NLK):
        sp = NULLS[li]["shufpair"]; add_dec(f"{li}|null:shufpair", sp, BOOKS[(li, "pca", 0)]["mu"]); add_dec(f"{li}|null:randorth", BOOKS[(li, "pca", 0)]["A"], BOOKS[(li, "pca", 0)]["mu"])
    rng = np.random.default_rng(11)
    for j, m in enumerate(MM):
        if m["split"] == "train": continue
        t = m["t"]; sl = SLOTS[t]; ent = {"sender": {}}
        ent["operand_msg"] = operand_msg(t, m, rng); ent["swap"] = {q: swap_msg(t, q, m) for q in QUESTIONS[t]}
        for sk in KEYS:
            e2 = {"choices": {}, "raw": {}, "null": {}, "loo": {}}
            for li in range(NLK):
                xs_all = ST[sk]["sender_states"][row[sk][mids[j]], :len(sl), li].double().numpy()
                for kk, b in BOOKS.items():
                    if len(kk) != 3 or kk[0] != li: continue
                    ch, rkd = snap(b, sk, t, xs_all); e2["choices"][f"{li}|{kk[1]}|{kk[2]}"] = {"ch": ch, "top": rkd}
                b = BOOKS[(li, "pca", 0)]
                e2["raw"][li] = torch.tensor(np.stack([enc(b["A"], sk, xs_all[si] - b["mu"][sk]) for si in range(len(sl))]), dtype=torch.float32)
                rq = NULLS[li]["randorth"]["Q"]; Arand = {"P": b["A"]["P"], "Q": {**b["A"]["Q"], sk: rq[sk]}}
                e2["null"][f"{li}|randorth"] = torch.tensor(np.stack([enc(Arand, sk, xs_all[si] - b["mu"][sk]) for si in range(len(sl))]), dtype=torch.float32)
                sp = NULLS[li]["shufpair"]
                e2["null"][f"{li}|shufpair"] = torch.tensor(np.stack([enc(sp, sk, xs_all[si] - b["mu"][sk]) for si in range(len(sl))]), dtype=torch.float32)
                for y, lb in BOOKS[(li, "loo")].items():
                    if y in [m.get(s) for s in sl]:
                        ch, _ = snap(lb, sk, t, xs_all); e2["loo"][f"{li}|loo|{y}"] = ch
            ent["sender"][sk] = e2
        D["msgs"][m["id"]] = ent
    save(D, f"deliveries_{rk}.pt", {"receiver": rk})
save({"note": "book summary", "books": {f"{k[0]}|{k[1]}|{k[2]}": {"n": len(v["entries"]), "entries": ["|".join(e) for e in v["entries"]]} for k, v in BOOKS.items() if len(k) == 3},
      "layer_keys": LK, "runtime_s": time.time() - t0, "env": env_info()}, "book5.json")
print("negotiation done", f"{time.time()-t0:.0f}s")
