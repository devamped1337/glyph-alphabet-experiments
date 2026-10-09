"""v3 completion test. usage: inject_v3.py RECEIVER SENDER -> results/v3/inject_SENDER_into_RECEIVER.json
Receiver reads PRE + '? ? ? ?' and its layer-L residual at the 4 placeholder positions is REPLACED by mu + decoded glyph (left, op, right, '=')."""
import sys, os, json, time, collections, torch, numpy as np
HERE = "/workspace/glyph-exp"; sys.path[:0] = [HERE, HERE + "/v3"]; os.chdir(HERE)
from common import *; from common3 import *
import jlens
tk, sk = sys.argv[1], sys.argv[2]; t0 = time.time(); rng = np.random.default_rng(3)
m, tok, hf = load(tk); lens = jlens.JacobianLens.load(lens_path(tk))
B = torch.load("results/v3/book.pt", weights_only=False)
SR, SS = (torch.load(f"results/v3/states_{k}.pt", weights_only=False) for k in (tk, sk))
E = SR["eqs"]; test = [i for i, e in enumerate(E) if e["split"] == "test"]
SLOTS = ["left", "op", "right", "eq"]
DIG = [tok.encode(str(d), add_special_tokens=False)[0] for d in range(10)]; TF = [tok.encode(w, add_special_tokens=False)[0] for w in ("true", "false")]
unit = lambda x: x / (np.linalg.norm(x, axis=-1, keepdims=True) + 1e-12)
state = {"L": None, "H": None}
def hook(mod, inp, out):
    h = out if torch.is_tensor(out) else out[0]
    if state["H"] is not None: h[0, -4:] = state["H"]
    return out
hooks = {}
@torch.no_grad()
def run(p, L=None, H=None):
    state["H"] = None if H is None else torch.tensor(H, dtype=torch.float32)
    hd = m.layers[L].register_forward_hook(hook) if L is not None else None
    lg = hf(input_ids=m.encode(p), use_cache=False).logits[0, -1].float()
    if hd: hd.remove()
    state["H"] = None
    return {"dig": int(lg[DIG].argmax()), "tf": ["true", "false"][int(lg[TF].argmax())]}
def ok(e, pr): return pr["tf"] == e["r"] if e["op"] == "gt" else pr["dig"] == e["r"]
SHUF = {"add": "sub", "sub": "add", "gt": "add"}; WORD = {"add": "plus", "sub": "minus"}
rows = []; leak = []
for li in (0, 1):
    bk = B["layers"][li]; L = bk["layer"][tk]; P, Q, mu = bk["PCA"], bk["Q"], bk["mu"]
    enc = lambda k, x: ((x @ P[k][0]) / P[k][1]) @ Q[k]; dec = lambda k, c: ((c @ Q[k].T) * P[k][1]) @ P[k][0].T
    acc = bk["accepted"]; sh = bk["shared"]
    U = (hf.lm_head.weight.float() * hf.model.norm.weight.float()).detach()
    Jt = lens.jacobians[L].float()
    def Vdir(tid): v = (U[tid] @ Jt).double().numpy(); return v / np.linalg.norm(v)
    def readrank(vec, target, cands):      # rank of target among candidate tokens in the J-lens readout of a glyph deviation
        s = (U[cands] @ (Jt @ torch.tensor(vec, dtype=torch.float32))).numpy(); return int((s > s[cands.index(target)]).sum() + 1)
    def H(cs): return np.stack([mu[tk] + dec(tk, c) for c in cs])
    for i in test:
        e = E[i]; base = {"li": li, "layer": L, "op": e["op"], "a": e["a"], "b": e["b"], "r": e["r"], "r_in_operands": int(e["op"] != "gt" and e["r"] in (e["a"], e["b"]))}
        def add(cond, pr, **kw): rows.append({**base, "cond": cond, "correct": int(ok(e, pr)), **pr, **kw})
        if li == 0:
            add("none", run(SCAFFOLD)); add("text_eq", run(PRE + e["text"]))
            syms = [str(e["a"]), OPS[e["op"]], str(e["b"])]; perms = [p for p in ([1, 0, 2], [2, 1, 0], [0, 2, 1], [1, 2, 0], [2, 0, 1]) if "".join(syms[j] for j in p) != "".join(syms)]
            p = perms[rng.integers(len(perms))] if perms else [0, 1, 2]
            add("text_bag_scrambled", run(PRE + "".join(syms[j] for j in p) + "="), bag="".join(syms[j] for j in p))
            if e["op"] in WORD: add("text_word_op", run(PRE + f"{e['a']} {WORD[e['op']]} {e['b']}="))
        xs = SS["states"][i, :, li].double().numpy() - bk["mu"][sk]
        cs = [enc(sk, xs[si]) for si in range(3)]
        snap = []
        for si, s in enumerate(SLOTS[:3]):
            g = acc[s]; y = g[int((unit(cs[si]) @ unit(np.stack([bk["can"][sk][s][x] for x in g])).T).argmax())]; snap.append(y)
        truth = [str(e["a"]), e["op"], str(e["b"])]
        G = [sh["left"][snap[0]], sh["op"][snap[1]], sh["right"][snap[2]], sh["eq"]["="]]
        kw = {"snap": snap, "snap_correct": int(snap == truth)}
        add("glyph_snap", run(SCAFFOLD, L, H(G)), **kw)
        add("glyph_raw", run(SCAFFOLD, L, H(cs + [sh["eq"]["="]])))
        nat = bk["native"][tk]; add("native_book_oracle", run(SCAFFOLD, L, np.stack([mu[tk] + nat[s][y] for s, y in zip(SLOTS, truth + ["="])])))
        Gs = list(G); Gs[1] = sh["op"][SHUF[snap[1]]]
        add("glyph_op_shuffled", run(SCAFFOLD, L, H(Gs)), shuffled_to=SHUF[snap[1]])
        for s_ in range(2): add("glyph_samenorm_shuffled", run(SCAFFOLD, L, H([rng.permutation(c) for c in G])), seed=s_)
        # result-leak: lens-readout presence of the result token in each slot of the sent glyph, then ablate those directions
        tid = TF[0 if e["r"] == "true" else 1] if e["op"] == "gt" else DIG[e["r"]]
        cands = TF if e["op"] == "gt" else DIG
        devs = [dec(tk, c) for c in G]
        leak.append({"li": li, "op": e["op"], "r_in_operands": base["r_in_operands"], "ranks_snap": [readrank(d, tid, cands) for d in devs],
                     "ranks_raw": [readrank(dec(tk, c), tid, cands) for c in cs], "n_cands": len(cands)})
        Vb = np.stack([Vdir(t) for t in cands]) if e["op"] == "gt" else Vdir(tid)[None]
        Qb, _ = np.linalg.qr(Vb.T)
        abl = [d - Qb @ (Qb.T @ d) for d in devs]
        add("glyph_snap_result_ablated", run(SCAFFOLD, L, np.stack([mu[tk] + d for d in abl])))
        rawd = [dec(tk, c) for c in cs] + [dec(tk, sh["eq"]["="])]
        add("glyph_raw_result_ablated", run(SCAFFOLD, L, np.stack([mu[tk] + d - Qb @ (Qb.T @ d) for d in rawd])))
        if e["op"] in WORD:
            w = WORD[e["op"]]; ws = SR["word_states"][w][li].double().numpy()
            Hw = H(G); Hw[1] = ws; add("op_slot_word_state", run(SCAFFOLD, L, Hw))          # receiver's own state at the ' plus'/' minus' word
            nrm = np.linalg.norm(devs[1])
            for name, tkn in ((f"op_slot_word_embedding", " " + w), ("op_slot_symbol_embedding", OPS[e["op"]])):
                em = SR["emb"][tkn].double().numpy(); Hx = H(G); Hx[1] = mu[tk] + nrm * em / np.linalg.norm(em); add(name, run(SCAFFOLD, L, Hx))
            Hz = H(G); Hz[1] = mu[tk]; add("op_slot_blank_mu", run(SCAFFOLD, L, Hz))
    print("layer", li, "done", f"{time.time()-t0:.0f}s", flush=True)
json.dump({"receiver": tk, "sender": sk, "rows": rows, "leak": leak, "runtime_s": time.time() - t0}, open(f"results/v3/inject_{sk}_into_{tk}.json", "w"))
agg = collections.defaultdict(list)
for r in rows: agg[(r["li"], r["cond"], r["op"])].append(r["correct"])
for k in sorted(agg): print(k, f"{np.mean(agg[k]):.3f} n={len(agg[k])}")
