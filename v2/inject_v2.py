"""v2 injection with dictionary glyphs. usage: inject_v2.py RECEIVER SENDER -> results/v2/inject_SENDER_into_RECEIVER.json
Same target prompts, layer (band centre), positions (all non-BOS), alphas and scoring as v1 inject.py."""
import sys, os, json, time, collections, torch, numpy as np
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, HERE); sys.path.insert(0, HERE + "/v2"); os.chdir(HERE)
from common import *; from prompts import *
import jlens
tk, sk = sys.argv[1], sys.argv[2]; t0 = time.time(); rng = np.random.default_rng(1)
m, tok, hf = load(tk)
D = torch.load("results/v2/dictionary_v2.pt", weights_only=False)
AD = {k: {a: (v.double().numpy() if torch.is_tensor(v) else v) for a, v in D["adapters"][k].items()} for k in D["adapters"]}
L = AD[tk]["layer"]; words = D["words"]; Cd = D["canonical"].double().numpy(); NCd = len(words)
def enc(k, x): return (((x - AD[k]["mu"]) @ AD[k]["P"]) / AD[k]["s"]) @ AD[k]["Q"]
def dec(k, c): return ((c @ AD[k]["Q"].T) * AD[k]["s"]) @ AD[k]["P"].T
CA = {"qwen": D["canonical_A"].double().numpy(), "smol": D["canonical_B"].double().numpy()}
SS = torch.load(f"results/v2/states_{sk}.pt", weights_only=False)
hop1 = SS["sets"]["bridge_src"][:, 1].double().numpy()           # sender's state on the hop-1 prompt at its layer L
names = list(BRIDGES)
# core subspace (depth test): top-16 principal directions of accepted canonical vectors
_, _, Vt = np.linalg.svd(Cd - Cd.mean(0), full_matrices=False); Pc = Vt[:16].T
v1 = json.load(open(f"results/inject_{sk}_into_{tk}_k16.json")); bundles = v1["bundles"]
def first_id(w): return tok.encode(" " + w, add_special_tokens=False)[0]
state = {"delta": None}
def hook(mod, inp, out):
    h = out if torch.is_tensor(out) else out[0]
    if state["delta"] is not None: h[:, 1:] += state["delta"]
    return out
m.layers[L].register_forward_hook(hook)
@torch.no_grad()
def next_logp(p): return torch.log_softmax(hf(input_ids=m.encode(p, max_length=128), use_cache=False).logits[0, -1].float(), -1)
@torch.no_grad()
def ref_norm(p):
    with jlens.ActivationRecorder(m.layers, at=[L]) as rec:
        m.forward(m.encode(p, max_length=128)); return rec.activations[L][0, 1:].norm(dim=-1).median().item()
def score(lp, rel, b):
    ai = REL[rel][1]; cands = sorted({first_id(v[ai]) for v in BRIDGES.values()}); c = first_id(BRIDGES[b][ai]); s = lp[cands]
    return {"correct": int(cands[int(s.argmax())] == c), "margin": (lp[c] - s[torch.tensor([x != c for x in cands])].mean()).item()}
def tvec(canon): v = torch.tensor(dec(tk, canon), dtype=torch.float32); return v / v.norm()
ALPHAS = [1.0, 2.0, 4.0, 8.0]; rows = []; snaps = {}; ntok = collections.defaultdict(list)
unit = lambda x: x / np.linalg.norm(x, axis=-1, keepdims=True)
for rel in REL:
    tp = REL[rel][0]; rn = ref_norm(tp)
    for i, b in enumerate(names):
        base = {"rel": rel, "bridge": b}; covered = b in words
        state["delta"] = None
        rows.append({**base, "cond": "none", **score(next_logp(tp), rel, b)})
        bow = ", ".join(bundles[b]) + ".\n"; one = b + ".\n"
        rows.append({**base, "cond": "text_bow16_v1bundle", **score(next_logp(bow + tp), rel, b)})
        rows.append({**base, "cond": "text_single_word", **score(next_logp(one + tp), rel, b)})
        if rel == "capital":
            ntok["text_bow16"].append(len(tok.encode(bow, add_special_tokens=False))); ntok["text_single_word"].append(len(tok.encode(one, add_special_tokens=False)))
        cs = enc(sk, hop1[i]); j = int((unit(cs) @ unit(CA[sk]).T).argmax()); snaps[b] = words[j]
        glyphs = {"glyph_dict_lookup": Cd[words.index(b)] if covered else None,           # agreed canonical entry for the true bridge
                  "glyph_sender_snap": CA[sk][j],                                         # sender resolves hop 1, snaps to its nearest dictionary entry
                  "glyph_sender_raw": cs,                                                 # sender hop-1 state in canonical space, no snapping
                  "glyph_core16_lookup": (Cd[words.index(b)] - Cd.mean(0)) @ Pc @ Pc.T + Cd.mean(0) if covered else None}
        for a in ALPHAS:
            for g, c in glyphs.items():
                if c is None: continue
                state["delta"] = tvec(c) * a * rn; rows.append({**base, "cond": f"{g}_a{a}", **score(next_logp(tp), rel, b)})
            if covered:
                c = Cd[words.index(b)]
                for s_ in range(3):
                    state["delta"] = tvec(rng.permutation(c)) * a * rn          # same-norm shuffled glyph (canonical coords permuted)
                    rows.append({**base, "cond": f"glyph_shuffled_a{a}", "seed": s_, **score(next_logp(tp), rel, b)})
                    w = rng.choice([x for x in range(NCd) if words[x] != b])     # wrong dictionary concept
                    state["delta"] = tvec(Cd[w]) * a * rn
                    rows.append({**base, "cond": f"glyph_wrong_concept_a{a}", "seed": s_, "wrong": words[w], **score(next_logp(tp), rel, b)})
                    wc = rng.choice([x for x in range(NCd) if words[x] != b and words[x] in BRIDGES])  # wrong *country* concept (harder control)
                    state["delta"] = tvec(Cd[wc]) * a * rn
                    rows.append({**base, "cond": f"glyph_wrong_country_a{a}", "seed": s_, "wrong": words[wc], **score(next_logp(tp), rel, b)})
        state["delta"] = None
agg = collections.defaultdict(list)
for r in rows: agg[r["cond"]].append(r)
summ = {c: {"acc": float(np.mean([r["correct"] for r in rs])), "margin": float(np.mean([r["margin"] for r in rs])), "n": len(rs)} for c, rs in agg.items()}
out = {"receiver": tk, "sender": sk, "layer": L, "covered_bridges": [b for b in names if b in words], "sender_snap": snaps,
       "snap_correct": float(np.mean([snaps[b] == b for b in names])), "text_tokens_mean": {k: float(np.mean(v)) for k, v in ntok.items()},
       "v1_summary": {k: v1["summary"][k] for k in v1["summary"] if k.startswith(("inj_real_a", "inj_shuffled", "text_bow_k16", "text_bridge", "none"))},
       "summary": summ, "rows": rows, "runtime_s": time.time() - t0}
json.dump(out, open(f"results/v2/inject_{sk}_into_{tk}.json", "w"), indent=1)
for c, s in summ.items(): print(f"{c:30s} acc={s['acc']:.3f} margin={s['margin']:+.2f} n={s['n']}")
print("snaps", snaps, "tokens", out["text_tokens_mean"], f"{time.time()-t0:.0f}s")
