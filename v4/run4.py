"""v4 receiver runs. usage: run4.py RECEIVER dev|test   (test reads the frozen settings in results/v4/frozen.json)"""
import sys, os, json, time, torch, numpy as np
sys.path.insert(0, "/workspace/glyph-exp/v4"); os.chdir("/workspace/glyph-exp")
from common4 import *
rk, phase = sys.argv[1], sys.argv[2]; t0 = time.time(); rng = np.random.default_rng(7)
R = Runner(rk); M = messages(); BK = torch.load("results/v4/book.pt", weights_only=False)
SS = {k: torch.load(f"results/v4/states_{k}.pt", weights_only=False) for k in MODELS}
unit = lambda x: x / (np.linalg.norm(x, axis=-1, keepdims=True) + 1e-12)
def enc(A, k, x): return ((x @ A["P"][k][0]) / A["P"][k][1]) @ A["Q"][k]
def dec(A, k, c): return ((c @ A["Q"][k].T) * A["P"][k][1]) @ A["P"][k][0].T
CAND = {}
def cands(t, q):
    if (t, q) not in CAND: CAND[(t, q)] = ENT if (t == "t2" or q in ("agent", "patient")) else ["yes", "no"]
    return CAND[(t, q)]
NL = R.tid("\n")
def answer_of(t, q, ids, layer=None, pos=None, H=None):
    """t1/t2: argmax over the answer candidates' first tokens. t3: greedy generation (<=3 new tokens, stop at newline), full string scored."""
    if t != "t3":
        c = cands(t, q); tids = [R.tid(" " + w) for w in c]
        lg = R.logits(ids, layer, pos, H) if H is not None else R.logits(ids)
        return [c[int(i)] for i in lg[:, tids].argmax(1)]
    B = 1 if H is None else H.shape[0]; cur = ids.repeat(B, 1); outs = [[] for _ in range(B)]; done = [False] * B
    for _ in range(3):
        lg = R.logits(cur, layer, pos, H) if H is not None else R.logits(cur)
        nx = lg.argmax(1)
        for b in range(B):
            if nx[b].item() == NL: done[b] = True
            if not done[b]: outs[b].append(nx[b].item())
        if all(done): break
        cur = torch.cat([cur, nx[:, None]], 1)
    return [R.tok.decode(o).strip() for o in outs]
FLIP = {"known": "suspected", "suspected": "known", "indeed": "never", "never": "indeed", "before": "after", "after": "before"}
def shuffled_msg(m, t, q):
    m2 = dict(m)
    if t == "t1" and q in ("agent", "patient"): m2["agent"], m2["patient"] = m["patient"], m["agent"]
    elif t == "t1": m2[q] = FLIP[m[q]]
    elif t == "t2": m2["ord"] = FLIP[m["ord"]]
    else: m2["left"], m2["right"] = m["right"], m["left"]
    return m2
def snap(book, sk, t, x):
    A = book["A"]; ch = []; ts = time.perf_counter()
    for si, s in enumerate(SLOTS[t]):
        gal = [e for e in book["entries"] if e[:2] == (t, s)]
        c = enc(A, sk, x[si] - book["mu"][sk]); ch.append(gal[int((unit(np.stack([book["can"][sk][g] for g in gal])) @ unit(c)).argmax())][2])
    return ch, time.perf_counter() - ts
def H_of(book, cvecs): return np.stack([book["mu"][rk] + dec(book["A"], rk, c) for c in cvecs])
if phase == "dev":
    LIS = list(range(len(FRACS))); split = "dev"
else:
    FZ = json.load(open("results/v4/frozen.json")); LIS = [FZ["li"]]; split = "test"
Qs = queries(M, split); rows = []; costs = []
if phase == "test":   # CPU budget: keep every t3 item and half of the t1/t2 test GROUPS (whole groups, so role/order swap pairs stay intact)
    gs = sorted({M[i]["group"] for i, _ in Qs if M[i]["t"] != "t3"}, key=lambda g: (g[:2], int(g[3:])))
    keep = {g for n, g in enumerate(gs) if n % 2 == 0}
    Qs = [(i, q) for i, q in Qs if M[i]["t"] == "t3" or M[i]["group"] in keep]
if os.environ.get("SMOKE"): Qs = [x for x in Qs if M[x[0]]["t"] == "t3"][:4] + Qs[:2]; phase_out = "smoke"
print("n queries", len(Qs), flush=True)
for li in LIS:
    L = BK["layers"][li]["layer"][rk]; book = BK["layers"][li]["main"]; nfb = BK["layers"][li]["nofilter"]; twb = BK["layers"][li]["twomodel"]
    for n, (mid, q) in enumerate(Qs):
        m = M[mid]; t = m["t"]; sl = SLOTS[t]; truth = [m[s] for s in sl]; gold = answer(t, q, m)
        base = {"li": li, "layer": L, "mid": mid, "t": t, "q": q, "group": m["group"], "gold": gold}
        def add(cond, pred, gold_=gold, **kw): rows.append({**base, "cond": cond, "pred": pred, "correct": int(pred == gold_), **kw})
        if phase == "test" or li == LIS[0]:
            for fmt in ("prose", "compact", "bag"):
                body = render(t, m, fmt, seed=mid); ids = R.tok(prompt(t, q, body, fmt), return_tensors="pt")["input_ids"]
                ts = time.perf_counter(); p = answer_of(t, q, ids)[0]; dt = time.perf_counter() - ts
                add(f"text_{fmt}", p, bytes=len(body.encode()), tokens=len(R.tok.encode(body, add_special_tokens=False)), fwd_s=dt)
        full = prompt(t, q, SKEL(t), "glyph"); ids, pos = encode_positions(R.tok, full, SKEL(t), ["?"] * len(sl))
        if phase == "test" or li == LIS[0]: add("none", answer_of(t, q, ids)[0])
        Hs, names, extra = [], [], []
        for sk in MODELS:
            x = SS[sk]["sender_states"][mid, :len(sl), li].double().numpy()
            ch, t_snap = snap(book, sk, t, x); okc = int(ch == truth)
            shv = [book["shared"][(t, s, y)] for s, y in zip(sl, ch)]
            ts = time.perf_counter(); Hid = H_of(book, shv); t_dec = time.perf_counter() - ts       # ID path: receiver expands its local float64 book
            vec32 = np.stack(shv).astype(np.float32)                                                   # vector path: sender transmits float32 canonical
            Hvec = H_of(book, vec32.astype(np.float64))
            ts = time.perf_counter()
            rec = [[e for e in book["entries"] if e[:2] == (t, s)][int((unit(np.stack([book["native"][rk][e] for e in book["entries"] if e[:2] == (t, s)])) @ unit(Hvec[si] - book["mu"][rk])).argmax())][2] for si, s in enumerate(sl)]
            t_chk = time.perf_counter() - ts
            costs.append({"sender": sk, "t": t, "snap_s": t_snap, "decode_s": t_dec, "receipt_check_s": t_chk, "receipt_ids_match": int(rec == ch),
                          "id_vs_vec_maxabs": float(np.abs(Hid.astype(np.float32) - Hvec.astype(np.float32)).max()), "sender_forward_s": SS[sk]["sender_forward_s"][mid]})
            kw = {"sender": sk, "snap_correct": okc, "choice": ch}
            Hs += [Hid, Hvec]; names += [("glyph_id", kw), ("glyph_vec", kw)]
            if phase == "test":
                m2 = shuffled_msg(dict(zip(sl, ch)) | {"t": t}, t, q)
                if all((t, s, m2[s]) in book["shared"] for s in sl):     # swapped symbol may be a rejected entry in that slot -> not covered
                    sh2 = [book["shared"][(t, s, m2[s])] for s in sl]
                    Hs.append(H_of(book, sh2)); names.append(("glyph_slot_shuffled", {**kw, "follow_gold": answer(t, q, shuffled_msg(m, t, q))}))
                else: rows.append({**base, "cond": "glyph_slot_shuffled_NOT_COVERED", "sender": sk, "pred": None, "correct": 0})
                # audit fix (3): match norms AFTER decoding, per slot, at the point of entry into the receiver
                dreal = [dec(book["A"], rk, c) for c in shv]; dsh = [dec(book["A"], rk, rng.permutation(c)) for c in shv]
                Hs.append(np.stack([book["mu"][rk] + ds * (np.linalg.norm(dr) / np.linalg.norm(ds)) for dr, ds in zip(dreal, dsh)]))
                names.append(("glyph_samenorm_shuffled", {**kw, "canon_norms": [float(np.linalg.norm(c)) for c in shv], "decoded_norm_ratio_before_match": [float(np.linalg.norm(ds) / np.linalg.norm(dr)) for dr, ds in zip(dreal, dsh)]}))
                Hs.append(H_of(book, [enc(book["A"], sk, x[si] - book["mu"][sk]) for si in range(len(sl))])); names.append(("glyph_raw_unsnapped", kw))
                Hs.append(np.stack([book["mu"][rk] + book["native"][rk][(t, s, y)] for s, y in zip(sl, ch)])); names.append(("receiver_word_state", kw))
                chn, _ = snap(nfb, sk, t, x); Hs.append(H_of(nfb, [nfb["shared"][(t, s, y)] for s, y in zip(sl, chn)])); names.append(("ablation_nofilter_vec", {**kw, "snap_correct": int(chn == truth)}))
                if rk in twb["mu"] and sk in twb["mu"]:
                    cht, _ = snap(twb, sk, t, x); Hs.append(np.stack([twb["mu"][rk] + dec(twb["A"], rk, twb["shared"][(t, s, y)]) for s, y in zip(sl, cht)]))
                    names.append(("ablation_twomodel_vec", {**kw, "snap_correct": int(cht == truth)}))
                tc = COMPACT(t, dict(zip(sl, ch)))
                ids2 = R.tok(prompt(t, q, tc, "compact"), return_tensors="pt")["input_ids"]
                extra.append(("text_compact_of_choice", answer_of(t, q, ids2)[0], {**kw, "bytes": len(tc.encode())}))
        H = np.stack(Hs); ts = time.perf_counter(); preds = answer_of(t, q, ids, L, pos, H); dtb = (time.perf_counter() - ts) / len(H)
        for (c, kw), p in zip(names, preds):
            fg = kw.pop("follow_gold", None) if "follow_gold" in kw else None
            add(c, p, **{a: b for a, b in kw.items()}, fwd_s_per_row=dtb, **({"follow_gold": fg, "follows": int(p == fg)} if fg is not None else {}))
        for c, p, kw in extra: add(c, p, **kw)
        if n % 50 == 0: print(li, n, len(Qs), f"{time.time()-t0:.0f}s", flush=True)
json.dump({"receiver": rk, "phase": phase, "rows": rows, "costs": costs, "runtime_s": time.time() - t0}, open(f"results/v4/{phase if not os.environ.get('SMOKE') else 'smoke'}_{rk}.json", "w"))
print("done", rk, phase, f"{time.time()-t0:.0f}s")
