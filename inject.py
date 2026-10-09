"""Causal self-/cross-injection test. usage: inject.py TARGET_KEY BUNDLE_SOURCE_KEY
Bundle = top-k anchor words of SOURCE model's J-lens glyph on the hop-1 prompt (bridge resolved).
It is injected into TARGET model at its band-centre layer while TARGET reads a bridge-omitted prompt."""
import sys, json, time, torch, numpy as np, jlens
from common import *
from prompts import *
tk, sk = sys.argv[1], sys.argv[2]; t0 = time.time()
KB = int(sys.argv[3]) if len(sys.argv) > 3 else 16
m, tok, hf = load(tk); lens = jlens.JacobianLens.load(lens_path(tk))
FT = torch.load(f"results/feat_{tk}.pt", weights_only=False); FS = torch.load(f"results/feat_{sk}.pt", weights_only=False)
A = json.load(open("data/anchors.json")); words = A["words"]; aid = torch.tensor(A["ids"][tk]); NA = len(words)
band = FT["band"]; L = band[1]
# residual directions whose J-lens readout is each anchor: grad of (g*u_c).(J_L h) wrt h = J_L^T (g*u_c)
U = m._lm_head.weight[aid].float() * m._final_norm.weight.float()
V = U @ lens.jacobians[L]; V = V / V.norm(dim=1, keepdim=True)            # [NA, d]
# source glyph (centred dense) on the hop-1 prompts
G = FS["feats"]["bridge_src"]["jlens"].numpy() - FS["feats"]["wiki"]["jlens"].numpy().mean(0)
names = list(BRIDGES); rng = np.random.default_rng(0)
bundles = []
for i, b in enumerate(names):
    idx = np.argsort(-G[i])[:KB]; w = np.clip(G[i][idx], 0, None)
    bundles.append((idx, w))
ANSWERS = {v[1] for v in BRIDGES.values()} | {v[2] for v in BRIDGES.values()}
bundles_noans = []
for i, b in enumerate(names):
    order = [j for j in np.argsort(-G[i]) if words[j] not in ANSWERS][:KB]
    bundles_noans.append((np.array(order), np.clip(G[i][order], 0, None)))
bridge_rank = [int((G[i] > G[i][words.index(b)]).sum() + 1) if b in words else None for i, b in enumerate(names)]
def first_id(w): return tok.encode(" " + w, add_special_tokens=False)[0]

state = {"delta": None, "pos": "all", "proj": None}
def hook(mod, inp, out):
    h = out if torch.is_tensor(out) else out[0]
    if state["delta"] is not None:
        if state["pos"] == "last": h[:, -1] += state["delta"]
        else: h[:, 1:] += state["delta"]
    if state["proj"] is not None:
        Q = state["proj"]; h -= (h @ Q) @ Q.T
    return out
@torch.no_grad()
def next_logp(prompt):
    ids = m.encode(prompt, max_length=128)
    return torch.log_softmax(hf(input_ids=ids, use_cache=False).logits[0, -1].float(), -1)
@torch.no_grad()
def ref_norm(prompt):
    ids = m.encode(prompt, max_length=128)
    with jlens.ActivationRecorder(m.layers, at=[L]) as rec:
        m.forward(ids); return rec.activations[L][0, 1:].norm(dim=-1).median().item()

def score(lp, rel, b):
    ans_i = REL[rel][1]; cands = sorted({first_id(v[ans_i]) for v in BRIDGES.values()})
    c = first_id(BRIDGES[b][ans_i]); s = lp[cands]
    return {"correct": int(cands[int(s.argmax())] == c), "logp": lp[c].item(),
            "margin": (lp[c] - s[torch.tensor([x != c for x in cands])].mean()).item(), "n_cands": len(cands)}
def vec(idx, w):
    v = torch.tensor(w, dtype=torch.float32) @ V[torch.tensor(idx)]; return v / v.norm()

handles = [m.layers[l].register_forward_hook(hook) for l in band]   # proj uses all band layers; delta only at L
def set_delta(d): state["delta"] = d
# only layer L receives delta: wrap by toggling on module identity
def hook_L(mod, inp, out):
    return out
for h_ in handles: h_.remove()
hL = m.layers[L].register_forward_hook(hook)
ALPHAS = [1.0, 2.0, 4.0, 8.0]; NSHUF = 5
rows = []
for rel in REL:
    for i, b in enumerate(names):
        tp = REL[rel][0]; rn = ref_norm(tp); idx, w = bundles[i]
        base = {"rel": rel, "bridge": b}
        state.update(delta=None, proj=None)
        rows.append({**base, "cond": "none", **score(next_logp(tp), rel, b)})
        rows.append({**base, "cond": "oracle_text_bridge_named", **score(next_logp(ORACLE[rel].format(b=b)), rel, b)})
        rows.append({**base, "cond": "full_twohop_prompt", **score(next_logp(TWOHOP[rel].format(desc=BRIDGES[b][0])), rel, b)})
        bow = ", ".join(words[j] for j in idx) + ".\n" + tp
        rows.append({**base, "cond": f"text_bow_k{KB}", **score(next_logp(bow), rel, b)})
        idx2, w2 = bundles_noans[i]
        bow2 = ", ".join(words[j] for j in idx2) + ".\n" + tp
        rows.append({**base, "cond": f"text_bow_noanswers_k{KB}", **score(next_logp(bow2), rel, b)})
        rows.append({**base, "cond": "text_bridge_word_only", **score(next_logp(b + ".\n" + tp), rel, b)})
        state["pos"] = "all"
        for a in ALPHAS:
            state["delta"] = vec(idx, w) * a * rn
            rows.append({**base, "cond": f"inj_real_a{a}", **score(next_logp(tp), rel, b)})
            state["delta"] = vec(idx2, w2) * a * rn
            rows.append({**base, "cond": f"inj_real_noanswers_a{a}", **score(next_logp(tp), rel, b)})
            if b in words:
                state["delta"] = vec([words.index(b)], [1.0]) * a * rn
                rows.append({**base, "cond": f"inj_bridge_only_a{a}", **score(next_logp(tp), rel, b)})
            for s_ in range(NSHUF):
                ridx = rng.choice(np.setdiff1d(np.arange(NA), idx), KB, replace=False)
                state["delta"] = vec(ridx, w) * a * rn
                rows.append({**base, "cond": f"inj_shuffled_a{a}", "seed": s_, **score(next_logp(tp), rel, b)})
        state["delta"] = None
print("injection done", f"{time.time()-t0:.0f}s", flush=True)
# ---- ablation on the full two-hop prompt: project out bundle directions at all band layers, all positions
hL.remove()
def basis(ix): Q, _ = torch.linalg.qr(V[torch.tensor(ix)].T); return Q
# NB: directions V are defined at layer L; we project the same subspace out at every layer in the set
# (residual-stream directions are approximately shared across nearby layers; this is an approximation)
if sk == tk:
    for lset_name, lset in (("band", band), ("all_fitted", lens.source_layers)):
        hs = [m.layers[l].register_forward_hook(hook) for l in lset]
        for rel in REL:
            for i, b in enumerate(names):
                tp = TWOHOP[rel].format(desc=BRIDGES[b][0]); idx, w = bundles[i]; idx2, _ = bundles_noans[i]; base = {"rel": rel, "bridge": b}
                state.update(delta=None, proj=None)
                if lset_name == "band": rows.append({**base, "cond": "abl_none", **score(next_logp(tp), rel, b)})
                state["proj"] = basis(idx); rows.append({**base, "cond": f"abl_{lset_name}_bundle_k{KB}", **score(next_logp(tp), rel, b)})
                state["proj"] = basis(idx2); rows.append({**base, "cond": f"abl_{lset_name}_bundle_noanswers_k{KB}", **score(next_logp(tp), rel, b)})
                for s_ in range(NSHUF):
                    state["proj"] = basis(rng.choice(np.setdiff1d(np.arange(NA), idx), KB, replace=False))
                    rows.append({**base, "cond": f"abl_{lset_name}_random_k{KB}", "seed": s_, **score(next_logp(tp), rel, b)})
                if b in words:
                    state["proj"] = basis([words.index(b)]); rows.append({**base, "cond": f"abl_{lset_name}_bridge_only", **score(next_logp(tp), rel, b)})
                    state["proj"] = basis(rng.choice(NA, 1)); rows.append({**base, "cond": f"abl_{lset_name}_random_1", **score(next_logp(tp), rel, b)})
                state["proj"] = None
        for h_ in hs: h_.remove()
# ---- summary
import collections
agg = collections.defaultdict(list)
for r in rows: agg[r["cond"]].append(r)
summ = {c: {"acc": float(np.mean([r["correct"] for r in rs])), "mean_margin": float(np.mean([r["margin"] for r in rs])),
            "mean_logp": float(np.mean([r["logp"] for r in rs])), "n": len(rs)} for c, rs in agg.items()}
for rel in REL:
    for c, rs in agg.items():
        rr = [r for r in rs if r["rel"] == rel]
        summ[c][f"acc_{rel}"] = float(np.mean([r["correct"] for r in rr]))
out = {"target": FT["model"], "bundle_source": FS["model"], "layer": L, "band": band, "k": KB,
       "bridge_rank_in_source_glyph": dict(zip(names, bridge_rank)),
       "bundles": {b: [words[j] for j in bundles[i][0]] for i, b in enumerate(names)},
       "bundles_noanswers": {b: [words[j] for j in bundles_noans[i][0]] for i, b in enumerate(names)},
       "summary": summ, "rows": rows, "runtime_s": time.time() - t0}
json.dump(out, open(f"results/inject_{sk}_into_{tk}_k{KB}.json", "w"), indent=1)
for c, s in summ.items(): print(f"{c:28s} acc={s['acc']:.3f} (cap {s['acc_capital']:.2f} lang {s['acc_language']:.2f}) margin={s['mean_margin']:+.2f} n={s['n']}")
print("bridge rank in source glyph:", out["bridge_rank_in_source_glyph"]); print(f"{time.time()-t0:.0f}s")
