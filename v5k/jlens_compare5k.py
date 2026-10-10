"""v5k quick J-lens comparison (CPU, after jgram5 + negotiate5 [+ test]):
 per model and layer key: J-subspace split-half stability, overlap of the top-KP J-subspace with the top-KP PCA subspace of the
 book states (train split), the chance level KP/d, J spectrum concentration, and (if test files exist) glyph_id accuracy by basis.
 usage: jlens_compare5k.py  -> results/jlens_compare5k.json"""
from common5 import *
M = messages(); out = {"KP": KP, "models": {}}
for k in MODELS:
    S = load(f"states_{k}.pt"); J = S["jlens"]; tr = [i for i, m in enumerate(S["mids"]) if M[m]["split"] == "train"]; r = {}
    for li, lk in enumerate(S["keys"]):
        if lk not in J: continue
        X = S["book_states"][tr][:, :, li].reshape(-1, S["d"]).double(); X = X - X.mean(0)
        P = torch.linalg.svd(X, full_matrices=False)[2][:KP].T.float(); Vj = J[lk]["evecs"]; ev = J[lk]["evals"]
        r[str(lk)] = {"overlap_J_vs_PCA": float((Vj.T @ P).pow(2).sum() / KP), "chance": KP / S["d"],
                      "J_top8_energy_frac": float(ev[:8].sum() / J[lk]["trace"]), "J_topKP_energy_frac": float(ev.sum() / J[lk]["trace"]),
                      "split_half": J.get("_split_half", {}).get(str(lk))}
    out["models"][k] = {"model": S["model"], "jgram_meta": J.get("_meta"), "layers": r}
acc = {}
for rk in MODELS:
    n = f"test_{rk}.json"
    if not os.path.exists(os.path.join(OUT, n)): continue
    for row in load(n)["rows"]:
        if row["cond"] == "glyph_id" and "correct" in row: acc.setdefault(f"{rk}|{row.get('basis')}", []).append(row["correct"])
out["test_glyph_id_by_basis"] = {k: {"acc": float(np.mean(v)), "n": len(v)} for k, v in sorted(acc.items())}
save(out, "jlens_compare5k.json"); print(json.dumps(out, indent=1, default=str)[:4000])
