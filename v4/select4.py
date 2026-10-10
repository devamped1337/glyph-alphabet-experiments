import json, numpy as np, os
os.chdir("/workspace/glyph-exp"); acc = {}; txt = {}
for r in ("qwen", "smol", "pythia"):
    d = json.load(open(f"results/v4/dev_{r}.json"))
    for x in d["rows"]:
        if x["cond"] == "glyph_vec": acc.setdefault(x["li"], []).append(x["correct"])
        if x["cond"].startswith("text"): txt.setdefault((r, x["cond"]), []).append(x["correct"])
s = {li: float(np.mean(v)) for li, v in acc.items()}; li = max(s, key=s.get)
json.dump({"li": li, "dev_glyph_vec_acc_by_li": s, "dev_text": {f"{a}|{b}": float(np.mean(v)) for (a, b), v in txt.items()},
           "frozen": "layer fraction index li, replace-mode patching at placeholder positions, PCA64 half-whitened, 32-d canonical, book version = final main version at li"},
          open("results/v4/frozen.json", "w"), indent=1)
print(s, "chosen", li)
