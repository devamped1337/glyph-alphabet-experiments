"""No-model control: glyph = which anchor words literally appear in the prompt text.
Cross-'model' retrieval with this is trivially 100% (both sides see the same text), so instead we
report (i) the within-set paraphrase test and (ii) how well a lexical glyph of prompt i retrieves
model B's J-lens glyph of prompt i (A=text, B=model), to gauge how much of (b) is surface word overlap."""
import json, re, numpy as np, torch
from prompts import PARAPHRASES
words = json.load(open("data/anchors.json"))["words"]; widx = {w: i for i, w in enumerate(words)}
def lex(ps):
    X = np.zeros((len(ps), len(words)))
    for i, p in enumerate(ps):
        for t in re.findall(r"[A-Za-z]+", p):
            for w in (t, t.lower(), t.capitalize()):
                if w in widx: X[i, widx[w]] = 1
    return X
def norm(X): return X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-12)
out = {}
ps = [p for pr in PARAPHRASES for p in pr]; G = norm(lex(ps)); S = G @ G.T; n = len(PARAPHRASES)
out["para_lexical"] = {"para_cos": float(np.mean([S[2*i, 2*i+1] for i in range(n)])),
    "random_cos": float(np.mean([S[i, j] for i in range(2*n) for j in range(i+1, 2*n) if i//2 != j//2])),
    "frac_prompts_with_no_anchor_word": float((np.linalg.norm(lex(ps), axis=1) == 0).mean())}
S2 = S.copy(); np.fill_diagonal(S2, -9); out["para_lexical"]["partner_top1"] = float(np.mean([S2[i].argmax() == (i ^ 1) for i in range(2*n)]))
for key in ("qwen", "smol"):
    F = torch.load(f"results/feat_{key}.pt", weights_only=False)
    for s in ("multihop", "assoc", "para"):
        L = norm(lex(F["sets"][s]))
        for kind in ("jlens", "final"):
            X = F["feats"][s][kind].numpy() - F["feats"]["wiki"][kind].numpy().mean(0); X = norm(X)
            C = L @ X.T
            out[f"text->{key}|{s}|{kind}-centred-dense"] = {"top1": float(np.mean(C.argmax(1) == np.arange(len(C)))), "chance": 1/len(C)}
json.dump(out, open("results/lexical_baseline.json", "w"), indent=1)
for k, v in out.items(): print(k, v)
