"""Per-model feature extraction: lens sanity checks, band selection, and anchor-score
features for every test prompt. usage: extract.py KEY  -> results/feat_KEY.pt"""
import os, sys, json, time, torch, numpy as np, jlens
from common import *
from prompts import *
key = sys.argv[1]; t0 = time.time()
m, tok, hf = load(key)
lens = jlens.JacobianLens.load(lens_path(key))
SRC = lens.source_layers; FINAL = m.n_layers - 1
A = json.load(open("data/anchors.json")); words = A["words"]; aid = torch.tensor(A["ids"][key])
D = "jacobian-lens/data/evaluations/"
multihop = json.load(open(D + "lens-eval-multihop.json"))["items"]
assoc = json.load(open(D + "lens-eval-association.json"))["items"]
wiki = [p for p in fit_prompts()[40:100]]  # NOT used in lens fit (fit used [:32])

@torch.no_grad()
def resid(prompt, max_len=64):
    ids = m.encode(prompt.rstrip(), max_length=max_len)
    with jlens.ActivationRecorder(m.layers, at=SRC + [FINAL]) as rec:
        m.forward(ids)
        return {l: rec.activations[l][0, -1].float().clone() for l in SRC + [FINAL]}

@torch.no_grad()
def readouts(r):
    """full-vocab logits per source layer for J-lens and logit-lens, plus final output."""
    H = torch.stack([r[l] for l in SRC])
    JH = torch.stack([lens.transport(r[l], l) for l in SRC])
    return m.unembed(JH), m.unembed(H), m.unembed(r[FINAL][None])[0]

def first_id(w): return tok.encode(" " + w, add_special_tokens=False)[0]

out = {"key": key, "model": MODELS[key], "src_layers": SRC, "n_layers": m.n_layers}
# ---- band selection on lens-eval-multihop: rank of the bridge entity at the last position
def eval_ranks(items):
    rj_, rl_ = [], []
    for it in items:
        jl, ll, _ = readouts(resid(it["prompt"], 128))
        tid = first_id(it["intermediates"][0])
        rj_.append([(jl[i] > jl[i, tid]).sum().item() + 1 for i in range(len(SRC))])
        rl_.append([(ll[i] > ll[i, tid]).sum().item() + 1 for i in range(len(SRC))])
    return np.array(rj_), np.array(rl_)
for name, items in (("multihop", multihop), ("association", assoc)):
    rj, rl = eval_ranks(items)
    out[name] = {f"{lt}_pass{k}": ((r <= k).mean(0)).tolist() for lt, r in (("jlens", rj), ("logit", rl)) for k in (1, 10, 50)}
    out[name].update({"jlens_median_rank": np.median(rj, 0).tolist(), "logit_median_rank": np.median(rl, 0).tolist(),
                      "jlens_any_layer_pass10": float((rj.min(1) <= 10).mean()), "logit_any_layer_pass10": float((rl.min(1) <= 10).mean())})
# band = 3 consecutive layers maximising mean J-lens pass@50 over both eval sets
crit = (np.array(out["multihop"]["jlens_pass50"]) + np.array(out["association"]["jlens_pass50"])) / 2
p = np.convolve(crit, np.ones(3) / 3, mode="same"); p[0] = p[-1] = -1
best = SRC[int(p.argmax())]; band = [best - 1, best, best + 1]
SUF = os.environ.get("BAND_MID") and "_mid" or ""
if SUF: band = [m.n_layers // 2 - 1, m.n_layers // 2, m.n_layers // 2 + 1]  # fixed mid-depth band variant
out["band"] = band
print(key, "band criterion (J-lens pass@50, multihop+assoc) per layer", dict(zip(SRC, np.round(crit, 3).tolist())), "band", band, flush=True)
# ---- sanity readouts
SANITY = ["The capital of France is", multihop[1]["prompt"], multihop[2]["prompt"], assoc[0]["prompt"], "Fact: The capital city of the country where the Eiffel Tower stands is"]
san = {}
for p in SANITY:
    jl, ll, fo = readouts(resid(p, 128))
    san[p] = {"final_top": [tok.decode([t]) for t in fo.topk(8).indices]}
    for l in sorted(set([SRC[0], m.n_layers // 3, m.n_layers // 2, *band, SRC[-1]])):
        i = SRC.index(l)
        san[p][f"L{l}_jlens"] = [tok.decode([t]) for t in jl[i].topk(8).indices]
        san[p][f"L{l}_logit"] = [tok.decode([t]) for t in ll[i].topk(8).indices]
out["sanity"] = san
# ---- anchor features for all test prompts: z-scored anchor logits per band layer
bi = [SRC.index(l) for l in band]
def feats(prompt):
    jl, ll, fo = readouts(resid(prompt))
    z = lambda x: (x - x.mean(-1, keepdim=True)) / x.std(-1, keepdim=True)
    return {"jlens": z(jl[bi][:, aid]).mean(0), "logit": z(ll[bi][:, aid]).mean(0), "final": z(fo[aid])}
sets = {"para": [p for pr in PARAPHRASES for p in pr], "minimal": [p for pr in MINIMAL for p in pr[:2]],
        "multihop": [it["prompt"] for it in multihop], "assoc": [it["prompt"] for it in assoc], "wiki": wiki,
        "bridge_src": [SRC_TMPL.format(desc=v[0]) for v in BRIDGES.values()]}
F = {}
for s, ps in sets.items():
    fs = [feats(p) for p in ps]
    F[s] = {k: torch.stack([f[k] for f in fs]) for k in fs[0]}
out["feats"] = F; out["sets"] = sets
out["runtime_s"] = time.time() - t0
torch.save(out, f"results/feat_{key}{SUF}.pt")
json.dump({k: v for k, v in out.items() if k not in ("feats", "sets")}, open(f"results/extract_{key}{SUF}.json", "w"), indent=1)
print("done", key, f"{out['runtime_s']:.0f}s")
