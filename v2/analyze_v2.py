"""v2 retrieval + minimal pairs in the negotiated canonical space. -> results/v2/metrics_v2.json"""
import sys, os, json, torch, numpy as np
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, HERE); sys.path.insert(0, HERE + "/v2"); os.chdir(HERE)
from prompts import MINIMAL
from common import MODELS, lens_path
import transformers, jlens
KEYS = ["qwen", "smol"]; rng = np.random.default_rng(0)
D = torch.load("results/v2/dictionary_v2.pt", weights_only=False)
AD = {k: {a: (v.double().numpy() if torch.is_tensor(v) else v) for a, v in D["adapters"][k].items()} for k in KEYS}
ST = {k: torch.load(f"results/v2/states_{k}.pt", weights_only=False) for k in KEYS}
def enc(k, x, Q=None): return (((x - AD[k]["mu"]) @ AD[k]["P"]) / AD[k]["s"]) @ (AD[k]["Q"] if Q is None else Q)
def dec(k, c): return ((c @ AD[k]["Q"].T) * AD[k]["s"]) @ AD[k]["P"].T
unit = lambda x: x / (np.linalg.norm(x, axis=-1, keepdims=True) + 1e-12)
def retrieval(GA, GB):
    S = unit(GA) @ unit(GB).T; n = len(S)
    return {"N": n, "A2B_top1": float(np.mean(S.argmax(1) == np.arange(n))), "B2A_top1": float(np.mean(S.argmax(0) == np.arange(n))),
            "A2B_top5": float(np.mean([i in np.argsort(-S[i])[:5] for i in range(n)])), "matched_cos": float(np.mean(np.diag(S))),
            "mismatched_cos": float((S.sum() - np.trace(S)) / (n * n - n)), "chance_top1": 1 / n}
# control adapters: same pipeline but Procrustes fit with shuffled concept correspondence between A and B
idx = D["concept_index"]
Z = {k: ((ST[k]["probe"][:, :5, 1].double().numpy().mean(1) - AD[k]["mu"]) @ AD[k]["P"]) / AD[k]["s"] for k in KEYS}
def ctrl_Q():
    perm = rng.permutation(len(idx)); ZA, ZB = Z["qwen"][idx], Z["smol"][np.array(idx)[perm]]
    _, _, vt = np.linalg.svd(ZA, full_matrices=False); Cn = ZA @ vt[:96].T
    for _ in range(30):
        Q = {}
        for k, Zk in (("qwen", ZA), ("smol", ZB)): u, _, v2 = np.linalg.svd(Zk.T @ Cn, full_matrices=False); Q[k] = u @ v2
        Cn = (ZA @ Q["qwen"] + ZB @ Q["smol"]) / 2
    return Q
CQ = [ctrl_Q() for _ in range(10)]
v1 = json.load(open("results/metrics.json"))["b_cross"]; v1mid = json.load(open("results/metrics_mid.json"))["b_cross"]
M = {"retrieval": {}, "minimal": {}}
for s in ("multihop", "assoc", "para"):
    XA, XB = (ST[k]["sets"][s][:, 1].double().numpy() for k in KEYS)
    for cen in ("adapter_mu", "set_mean"):
        xa, xb = (XA - XA.mean(0) + AD["qwen"]["mu"], XB - XB.mean(0) + AD["smol"]["mu"]) if cen == "set_mean" else (XA, XB)
        r = retrieval(enc("qwen", xa), enc("smol", xb))
        cr = [retrieval(enc("qwen", xa, q["qwen"]), enc("smol", xb, q["smol"]))["A2B_top1"] for q in CQ]
        r["shuffled_correspondence_adapter_A2B_top1_mean"] = float(np.mean(cr)); r["shuffled_correspondence_adapter_A2B_top1_max"] = float(np.max(cr))
        M["retrieval"][f"{s}|{cen}"] = r
    M["retrieval"][f"{s}|v1_jlens_late_band"] = {a: v1[f"{s}|jlens-centred-dense"][a] for a in ("A2B_top1", "B2A_top1", "A2B_top5", "shuffled_anchor_A2B_top1_mean")}
    M["retrieval"][f"{s}|v1_jlens_mid_band"] = {a: v1mid[f"{s}|jlens-centred-dense"][a] for a in ("A2B_top1", "B2A_top1", "A2B_top5")}
    M["retrieval"][f"{s}|v1_final_output"] = {a: v1[f"{s}|final-centred-dense"][a] for a in ("A2B_top1", "B2A_top1", "A2B_top5")}
# minimal pairs
A = json.load(open("data/anchors.json")); words = A["words"]; widx = {w: i for i, w in enumerate(words)}
dif = {}; summ = {}; rows = []
for k in KEYS:
    X = ST[k]["sets"]["minimal"][:, 1].double().numpy(); c = enc(k, X); dif[k] = unit(c[0::2] - c[1::2])
CD = (dif["qwen"] + dif["smol"]) / 2
C = dif["qwen"] @ dif["smol"].T; n = len(C)
summ["cross_diff_matched_cos"] = float(np.mean(np.diag(C))); summ["cross_diff_mismatched_cos"] = float((C.sum() - np.trace(C)) / (n * n - n))
summ["cross_diff_A2B_top1"] = float(np.mean(C.argmax(1) == np.arange(n))); summ["chance"] = 1 / n
for k in KEYS:
    tok = transformers.AutoTokenizer.from_pretrained(MODELS[k]); hf = transformers.AutoModelForCausalLM.from_pretrained(MODELS[k], dtype=torch.float32)
    lens = jlens.JacobianLens.load(lens_path(k)); L = AD[k]["layer"]; aid = torch.tensor(A["ids"][k])
    W = ((hf.lm_head.weight[aid].float() * hf.model.norm.weight.float()) @ lens.jacobians[L].float()).detach().double().numpy(); del hf
    X = ST[k]["sets"]["minimal"][:, 1].double().numpy()
    for lab, dv in (("canonical_shared_diff", CD), ("canonical_own_diff", dif[k]), ("native_layerL_diff", X[0::2] - X[1::2])):
        R = (dv if lab.startswith("native") else dec(k, dv)) @ W.T; R = (R - R.mean(1, keepdims=True)) / R.std(1, keepdims=True)
        rk = []
        for i, (p1, p2, w1, w2) in enumerate(MINIMAL):
            if w1 == w2: continue
            rk.append([int((R[i] > R[i, widx[w1]]).sum() + 1), int((-R[i] > -R[i, widx[w2]]).sum() + 1)])
        rk = np.array(rk)
        summ[f"{k}|{lab}"] = {"n": len(rk), "frac_w1_top10": float((rk[:, 0] <= 10).mean()), "frac_w2_top10": float((rk[:, 1] <= 10).mean()),
                              "frac_both_top10": float((rk <= 10).all(1).mean()), "median_rank_w1": float(np.median(rk[:, 0])), "median_rank_w2": float(np.median(rk[:, 1]))}
v1m = json.load(open("results/metrics.json"))["c_minimal"]
summ["v1_jlens"] = v1m["jlens"]["summary"]; summ["v1_final"] = v1m["final"]["summary"]
M["minimal"] = summ
json.dump(M, open("results/v2/metrics_v2.json", "w"), indent=1)
for k, r in M["retrieval"].items(): print(k, {a: round(b, 3) for a, b in r.items()})
for k, r in summ.items(): print(k, r if not isinstance(r, dict) else {a: (round(b, 3) if isinstance(b, float) else b) for a, b in r.items()})
