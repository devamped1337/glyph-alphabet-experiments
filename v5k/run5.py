"""Receiver tests (runs on the receiver's own machine).  usage: run5.py RECEIVER dev|test
reads results/deliveries_RECEIVER.pt (+ results/frozen5.json for test), sha256-verified. -> results/{dev,test}_RECEIVER.json
env: N_DEV (per task|question, default 60), N_TEST (default 250), RB (rows per forward, default 16), SMOKE=N (N queries per task)"""
import sys
from common5 import *
rk, phase = sys.argv[1], sys.argv[2]; t0 = time.time(); R = Runner(rk); M = messages(); D = load(f"deliveries_{rk}.pt"); KEYS = list(MODELS)
NLK = len(D["keys"]); RB = int(os.environ.get("RB", 16))
if phase == "test":
    FZ = load("frozen5.json"); LI = FZ["li"]; COUNTED = set(FZ["counted"][rk])
else: LI = None; COUNTED = None
def H_of(dname, C):
    d = D["decoders"][dname]; return d["mu"] + ((C @ d["Q"].T) * d["sc"]) @ d["B"].T
def shared(bname, syms, t):
    b = D["books"][bname]; ks = [(t, s, y) for s, y in zip(SLOTS[t], syms)]
    return torch.stack([b["shared"][k] for k in ks]) if all(k in b["shared"] for k in ks) else None
def payload(bname, t, syms):
    """the ID message: per-slot index in the book's slot gallery, as ASCII ('3.0.1.2.4'); identical bytes for glyph_id and id_text_expanded"""
    b = D["books"][bname]; out = []
    for s, y in zip(SLOTS[t], syms):
        gal = [e[2] for e in b["entries"] if e[:2] == (t, s)]
        if y not in gal: return None
        out.append(str(gal.index(y)))
    return ".".join(out)
def expand(bname, t, pl):
    """receiver side: ID payload -> symbols via the local book table; any unknown/malformed ID -> UNRECOGNIZED (no guessing)"""
    b = D["books"][bname]; parts = pl.split(".")
    if len(parts) != len(SLOTS[t]): return UNRECOGNIZED
    out = []
    for s, p_ in zip(SLOTS[t], parts):
        gal = [e[2] for e in b["entries"] if e[:2] == (t, s)]
        if not p_.isdigit() or int(p_) >= len(gal): return UNRECOGNIZED
        out.append(gal[int(p_)])
    return out
TID = {}
def cand_info(t, q):
    if (t, q) not in TID:
        c = candidates(t, q); tids = R.first_tids(c) if c else None
        TID[(t, q)] = (c, tids if tids and len(set(tids)) == len(tids) else None)
    return TID[(t, q)]
NL = R.tok.encode("\n", add_special_tokens=False)[0]
def run_rows(t, q, rows):
    """rows: list of dicts with ids (list[int]) and optional patch (layer_key, pos list, H [P,d]). Returns predictions (strings)."""
    c, tids = cand_info(t, q); preds = []
    for b0 in range(0, len(rows), RB):
        ch = rows[b0:b0 + RB]; ids = torch.tensor([r["ids"] for r in ch]); groups = {}
        for i, r in enumerate(ch):
            if r.get("patch"): lk, pos, H = r["patch"]; groups.setdefault((lk, tuple(pos)), []).append((i, H))
        patches = [(lk, torch.tensor([i for i, _ in v]), torch.tensor(pos), torch.stack([H for _, H in v])) for (lk, pos), v in groups.items()]
        if tids is not None:
            try:
                lg = R.logits(ids, patches); preds += [c[int(i)] for i in lg[:, tids].argmax(1)]
            except FloatingPointError as e:
                print(f"  overflow at {t}|{q} B={len(ch)}: {e}; marking __OVERFLOW__", flush=True)
                preds += ["__OVERFLOW__"] * len(ch)
            continue
        try:
            cur = ids; outs = [[] for _ in ch]; done = [False] * len(ch)
            for _ in range(3 if t == "t3" else 4):
                nx = R.logits(cur, patches).argmax(1)
                for i in range(len(ch)):
                    if nx[i].item() == NL: done[i] = True
                    if not done[i]: outs[i].append(nx[i].item())
                if all(done): break
                cur = torch.cat([cur, nx[:, None]], 1)
            txt = [R.tok.decode(o).strip() for o in outs]
            preds += txt if t == "t3" else [next((w for w in c if x.startswith(w)), x) for x in txt]
        except FloatingPointError as e:
            print(f"  overflow decode at {t}|{q}: {e}; marking __OVERFLOW__", flush=True)
            preds += ["__OVERFLOW__"] * len(ch)
    return preds
split = phase; Qs = [(i, q) for i, q in queries(M, split) if i in D["msgs"]]
if COUNTED is not None: Qs = [(i, q) for i, q in Qs if f"{M[i]['t']}|{q}" in COUNTED]
cap = int(os.environ.get("SMOKE") or os.environ.get("N_DEV" if phase == "dev" else "N_TEST", 60 if phase == "dev" else 250)); rng = np.random.default_rng(0); sel = []
for tq in sorted({(M[i]["t"], q) for i, q in Qs}):
    pool = [x for x in Qs if (M[x[0]]["t"], x[1]) == tq]; sel += [pool[k] for k in sorted(rng.choice(len(pool), min(cap, len(pool)), replace=False))]
print(phase, rk, "queries", len(sel), "layer index", LI, flush=True)
out = []; tq0 = time.time()
for n, (mid, q) in enumerate(sel):
    m = M[mid]; t = m["t"]; sl = SLOTS[t]; gold = answer(t, q, m); E = D["msgs"][mid]
    sk_ids, off, core = R.ids64(t, q, skel(t, m), "glyph"); pos = R.positions(sk_ids, off, core, ["?"] * len(sl))
    rows = []; meta = []
    def addrow(cond, ids=None, patch=None, **kw): rows.append({"ids": ids or sk_ids, "patch": patch}); meta.append({"cond": cond, **kw})
    addrow("none")
    for fmt, txt in (("prose", body(t, m)), ("compact", compact(t, m)), ("bag", bag(t, m, mid))):
        addrow(f"text_{fmt}", R.ids64(t, q, txt, "compact" if fmt == "compact" else "prose")[0], bytes=len(txt.encode()), tokens=len(R.tok.encode(txt, add_special_tokens=False)))
    lis = list(range(NLK)) if phase == "dev" else [LI]
    for sk in KEYS:
        S = E["sender"][sk]
        def glyph(cond, dname, C, li, **kw):
            if C is None: meta.append({"cond": cond, "sender": sk, "li": li, "covered": 0, **{a: b for a, b in kw.items() if a != "follow_gold"}}); rows.append(None); return
            addrow(cond, patch=(D["keys"][li], pos, H_of(dname, C)), sender=sk, li=li, **kw)
        for li in lis:
            bn = f"{li}|pca|0"; ch = S["choices"][bn]["ch"]; snap_ok = int(ch == [m[s] for s in sl]); pl = payload(bn, t, ch)
            glyph("glyph_id", bn, shared(bn, ch, t), li, basis="pca", seed=0, snap_correct=snap_ok, bytes=len(pl.encode()) if pl else None)
            if pl and (os.environ.get("DEV_ID_LI") is None or phase == "test" or li == int(os.environ["DEV_ID_LI"])):   # (1) the same ID bytes, expanded by the receiver into a prose sentence from its local book table
                ex = expand(bn, t, pl); assert ex == ch, (ex, ch)
                txt = body(t, dict(m, **dict(zip(sl, ex)))); addrow("id_text_expanded", R.ids64(t, q, txt, "prose")[0], sender=sk, li=li, bytes=len(pl.encode()), snap_correct=snap_ok)
                addrow("id_text_raw", R.ids64(t, q, pl, "prose")[0], sender=sk, li=li, bytes=len(pl.encode()))
            elif os.environ.get("DEV_ID_LI") is None or phase == "test" or li == int(os.environ["DEV_ID_LI"]):
                for c_ in ("id_text_expanded", "id_text_raw"): meta.append({"cond": c_, "sender": sk, "li": li, "covered": 0}); rows.append(None)
        if phase == "test":
            li = LI
            for kind in BASES:
                for seed in [int(x) for x in os.environ.get("TEST_SEEDS", ",".join(map(str, SEEDS))).split(",")]:
                    bn = f"{li}|{kind}|{seed}"
                    if (kind, seed) == ("pca", 0) or bn not in S["choices"]: continue
                    ch = S["choices"][bn]["ch"]; glyph("glyph_id", bn, shared(bn, ch, t), li, basis=kind, seed=seed, snap_correct=int(ch == [m[s] for s in sl]))
            if li != 0:   # (3) embedding-level patching with the embedding-level book
                ch0 = S["choices"]["0|pca|0"]["ch"]; glyph("glyph_emb", "0|pca|0", shared("0|pca|0", ch0, t), 0, snap_correct=int(ch0 == [m[s] for s in sl]))
            bn = f"{li}|pca|0"; ch = S["choices"][bn]["ch"]
            glyph("glyph_raw_unsnapped", bn, S["raw"][li], li)
            glyph("null_randorth", f"{li}|null:randorth", S["null"][f"{li}|randorth"], li)       # (6)
            glyph("null_shufpair", f"{li}|null:shufpair", S["null"][f"{li}|shufpair"], li)
            sw = E["swap"][q]
            if sw is not None:   # slot / operand-order swap applied to the chosen symbols
                cm = dict(zip(sl, ch)); sm = dict(cm)
                if t == "t1" and q in ("agent", "patient"): sm["agent"], sm["patient"] = cm["patient"], cm["agent"]
                elif t == "t3": sm["left"], sm["right"] = cm["right"], cm["left"]
                else:
                    FL = {"known": "suspected", "suspected": "known", "indeed": "never", "never": "indeed", "before": "after", "after": "before"}
                    for s in sl:
                        if sw[s] != m[s]: sm[s] = FL.get(cm[s], sw[s])
                glyph("glyph_slot_shuffled", bn, shared(bn, [sm[s] for s in sl], t), li, follow_gold=answer(t, q, sw))
            om = E["operand_msg"]
            if om is not None:   # (7) operand change: one operand replaced by another in-book symbol
                glyph("glyph_operand_changed", bn, shared(bn, [om[s] for s in sl], t), li, follow_gold=answer(t, q, om))
            C = shared(bn, ch, t)
            if C is not None:
                d = D["decoders"][bn]; dr = ((C @ d["Q"].T) * d["sc"]) @ d["B"].T; g = torch.Generator().manual_seed(mid)
                Cp = torch.stack([c[torch.randperm(len(c), generator=g)] for c in C]); ds = ((Cp @ d["Q"].T) * d["sc"]) @ d["B"].T
                Hs = d["mu"] + ds * (dr.norm(dim=1, keepdim=True) / ds.norm(dim=1, keepdim=True))
                addrow("glyph_samenorm_shuffled", patch=(D["keys"][li], pos, Hs), sender=sk, li=li)
                nat = D["books"][bn]["native"]; ks = [(t, s, y) for s, y in zip(sl, ch)]
                if nat and all(k in nat for k in ks): addrow("receiver_word_state", patch=(D["keys"][li], pos, d["mu"] + torch.stack([nat[k] for k in ks])), sender=sk, li=li)
            for lname, lch in S["loo"].items():   # (2) leave-one-entry-out book
                if int(lname.split("|")[0]) == li: glyph("glyph_loo", lname, shared(lname + "|" + sk, lch, t), li, loo_symbol=lname.split("|")[2], snap_correct=int(lch == [m[s] for s in sl]))
    if phase == "test":   # UNRECOGNIZED fallback: an out-of-range ID must expand to UNRECOGNIZED and inject nothing (no model call)
        bn = f"{LI}|pca|0"; gal0 = [e for e in D["books"][bn]["entries"] if e[:2] == (t, sl[0])]
        bad = ".".join([str(len(gal0) + 7)] + ["0"] * (len(sl) - 1)); fb = expand(bn, t, bad)
        meta.append({"cond": "unknown_id_fallback", "payload": bad, "fixed_pred": fb if fb == UNRECOGNIZED else "|".join(fb)}); rows.append(None)
    keep = [i for i, r in enumerate(rows) if r is not None]; ts = time.perf_counter(); preds = run_rows(t, q, [rows[i] for i in keep]); dt = time.perf_counter() - ts
    P = dict(zip(keep, preds))
    for i, mt in enumerate(meta):
        r = {"mid": mid, "t": t, "q": q, "group": m["group"], "gold": gold, "clue": bool(m.get("clue")), **mt}
        if mt["cond"] == "unknown_id_fallback": r["pred"] = mt["fixed_pred"]; r["correct"] = int(mt["fixed_pred"] == UNRECOGNIZED); r["fallback_check"] = 1
        if i in P:
            r["pred"] = P[i]; r["correct"] = int(P[i] == gold)
            if t == "t3": r.update(score_maths(P[i], gold))
            if "follow_gold" in mt: r["follows"] = int(P[i] == mt["follow_gold"])
        out.append(r)
    if n % 20 == 0: print(n, len(sel), f"{time.time()-t0:.0f}s, {dt:.1f}s for {len(keep)} rows, RSS {guard('run'):.1f} GB", flush=True)
name = f"{'smoke' if os.environ.get('SMOKE') else phase}_{rk}.json"
save({"receiver": rk, "phase": phase, "li": LI, "rows": out, "runtime_s": time.time() - t0, "query_s_mean": (time.time() - tq0) / max(1, len(sel)), "env": env_info(),
      "peak_rss_gb": rss_gb()}, name)
print("done", rk, phase, f"{time.time()-t0:.0f}s")
