"""a = a tests on saved features. usage: analyze.py A B -> results/metrics.json"""
import sys, json, itertools, torch, numpy as np
from prompts import PARAPHRASES, MINIMAL
ka, kb = sys.argv[1], sys.argv[2]
SUF = sys.argv[3] if len(sys.argv) > 3 else ""
FA, FB = torch.load(f"results/feat_{ka}{SUF}.pt", weights_only=False), torch.load(f"results/feat_{kb}{SUF}.pt", weights_only=False)
words = json.load(open("data/anchors.json"))["words"]; NA = len(words)
K = 32; rng = np.random.default_rng(0)

def glyph(F, s, kind, centred=True, sparse=False):
    X = F["feats"][s][kind].numpy().astype(np.float64)
    if centred: X = X - F["feats"]["wiki"][kind].numpy().mean(0)   # mean from held-out wikitext prompts
    if sparse:
        Y = np.zeros_like(X); idx = np.argsort(-X, 1)[:, :K]
        np.put_along_axis(Y, idx, np.take_along_axis(X, idx, 1).clip(min=0), 1); X = Y
    return X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-12)

VARIANTS = [(k, c, s) for k in ("jlens", "logit", "final") for c in (False, True) for s in (False, True)]
vname = lambda k, c, s: f"{k}{'-centred' if c else '-raw'}{'-top32' if s else '-dense'}"
M = {"models": [FA["model"], FB["model"]], "bands": [FA["band"], FB["band"]], "n_anchors": NA, "topk": K}

# (a) within-model paraphrase consistency
npair = len(PARAPHRASES); M["a_within"] = {}
for F in (FA, FB):
    for v in VARIANTS:
        G = glyph(F, "para", *v); S = G @ G.T
        para = [S[2*i, 2*i+1] for i in range(npair)]
        rand = [S[i, j] for i in range(2*npair) for j in range(i+1, 2*npair) if i // 2 != j // 2]
        # paraphrase retrieval: is the partner the nearest of the other 79 prompts?
        S2 = S.copy(); np.fill_diagonal(S2, -9); hit = np.mean([S2[i].argmax() == (i ^ 1) for i in range(2*npair)])
        M["a_within"][f"{F['key']}|{vname(*v)}"] = {"para_cos": float(np.mean(para)), "para_cos_sd": float(np.std(para)),
            "random_cos": float(np.mean(rand)), "random_cos_sd": float(np.std(rand)), "partner_retrieval_top1": float(hit),
            "chance": 1 / (2*npair - 1)}

# (b) cross-model retrieval
def retrieval(GA, GB):
    S = GA @ GB.T; n = len(S)
    return {"N": n, "matched_cos": float(np.mean(np.diag(S))), "mismatched_cos": float((S.sum() - np.trace(S)) / (n*n - n)),
            "A2B_top1": float(np.mean(S.argmax(1) == np.arange(n))), "B2A_top1": float(np.mean(S.argmax(0) == np.arange(n))),
            "A2B_top5": float(np.mean([i in np.argsort(-S[i])[:5] for i in range(n)])), "chance_top1": 1 / n, "chance_top5": 5 / n}
M["b_cross"] = {}
for s in ("multihop", "assoc", "para"):
    for v in VARIANTS:
        GA, GB = glyph(FA, s, *v), glyph(FB, s, *v)
        r = retrieval(GA, GB)
        ctrl = [retrieval(GA, GB[:, rng.permutation(NA)]) for _ in range(20)]  # shuffled-anchor control
        r["shuffled_anchor_A2B_top1_mean"] = float(np.mean([c["A2B_top1"] for c in ctrl]))
        r["shuffled_anchor_A2B_top1_max"] = float(np.max([c["A2B_top1"] for c in ctrl]))
        r["shuffled_anchor_matched_cos"] = float(np.mean([c["matched_cos"] for c in ctrl]))
        M["b_cross"][f"{s}|{vname(*v)}"] = r

# (c) minimal pairs (dense centred glyph)
widx = {w: i for i, w in enumerate(words)}
def rank_in(vec, w): return int((vec > vec[widx[w]]).sum() + 1)
M["c_minimal"] = {}
for kind in ("jlens", "logit", "final"):
    GD = {F["key"]: glyph(F, "minimal", kind, True, False) for F in (FA, FB)}
    rows = []; diffs = {}
    for k, G in GD.items():
        d = G[0::2] - G[1::2]; diffs[k] = d / np.linalg.norm(d, axis=1, keepdims=True)
        for i, (p1, p2, w1, w2) in enumerate(MINIMAL):
            r1, r2 = (rank_in(d[i], w1), rank_in(-d[i], w2)) if w1 != w2 else (None, None)
            rows.append({"model": k, "pair": i, "cos_pair": float(G[2*i] @ G[2*i+1]), "rank_w1_in_diff": r1, "rank_w2_in_negdiff": r2,
                         "top_pos": [words[j] for j in np.argsort(-d[i])[:5]], "top_neg": [words[j] for j in np.argsort(d[i])[:5]]})
    summ = {}
    for k in GD:
        R = [r for r in rows if r["model"] == k and r["rank_w1_in_diff"] is not None]
        rk = np.array([[r["rank_w1_in_diff"], r["rank_w2_in_negdiff"]] for r in R])
        summ[k] = {"n_pairs_scored": len(R), "mean_pair_cos": float(np.mean([r["cos_pair"] for r in rows if r["model"] == k])),
                   "frac_w1_top10": float((rk[:, 0] <= 10).mean()), "frac_w2_top10": float((rk[:, 1] <= 10).mean()),
                   "frac_both_top10": float(((rk <= 10).all(1)).mean()), "frac_both_top50": float(((rk <= 50).all(1)).mean()),
                   "median_rank_w1": float(np.median(rk[:, 0])), "median_rank_w2": float(np.median(rk[:, 1])),
                   "frac_pairs_cos_below_0.9": float(np.mean([r["cos_pair"] < 0.9 for r in rows if r["model"] == k]))}
    C = diffs[FA["key"]] @ diffs[FB["key"]].T; n = len(C)
    summ["cross_diff_matched_cos"] = float(np.mean(np.diag(C))); summ["cross_diff_mismatched_cos"] = float((C.sum() - np.trace(C)) / (n*n - n))
    summ["cross_diff_A2B_top1"] = float(np.mean(C.argmax(1) == np.arange(n))); summ["chance"] = 1 / n
    M["c_minimal"][kind] = {"summary": summ, "rows": rows}
json.dump(M, open(f"results/metrics{SUF}.json", "w"), indent=1)

# compact print
print("== (a) within-model paraphrase vs random cos ==")
for k, r in M["a_within"].items(): print(f"{k:40s} para={r['para_cos']:.3f} rand={r['random_cos']:.3f} partner@1={r['partner_retrieval_top1']:.2f} (chance {r['chance']:.3f})")
print("== (b) cross-model ==")
for k, r in M["b_cross"].items(): print(f"{k:40s} N={r['N']} A2B@1={r['A2B_top1']:.3f} B2A@1={r['B2A_top1']:.3f} @5={r['A2B_top5']:.3f} chance={r['chance_top1']:.3f} shufctrl={r['shuffled_anchor_A2B_top1_mean']:.3f}(max {r['shuffled_anchor_A2B_top1_max']:.3f}) cos m/mm={r['matched_cos']:.3f}/{r['mismatched_cos']:.3f}")
print("== (c) minimal pairs ==")
for k, r in M["c_minimal"].items(): print(k, json.dumps(r["summary"]))
