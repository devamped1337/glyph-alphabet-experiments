import json, collections, numpy as np
P = [("qwen","qwen"),("smol","smol"),("qwen","smol"),("smol","qwen")]  # (sender, receiver)
out = {}
for s, r in P:
    d = json.load(open(f"results/v2/inject_{s}_into_{r}.json")); cov = set(d["covered_bridges"])
    agg = collections.defaultdict(lambda: {"all": [], "cov": []}); mg = collections.defaultdict(list)
    for row in d["rows"]:
        agg[row["cond"]]["all"].append(row["correct"]); mg[row["cond"]].append(row["margin"])
        if row["bridge"] in cov: agg[row["cond"]]["cov"].append(row["correct"])
    base = collections.defaultdict(dict)
    for c, v in agg.items():
        b, a = (c.rsplit("_a", 1) if "_a" in c and c.rsplit("_a",1)[1][0].isdigit() else (c, "-"))
        base[b][a] = {"all": float(np.mean(v["all"])), "cov": float(np.mean(v["cov"])) if v["cov"] else None, "n_all": len(v["all"]), "n_cov": len(v["cov"]), "margin": float(np.mean(mg[c]))}
    v1 = d["v1_summary"]
    v1real = {a: v1[f"inj_real_a{a}"]["acc"] for a in ("1.0","2.0","4.0","8.0")}
    out[f"{s}->{r}"] = {"conds": base, "v1_real": v1real, "v1_shuf": {a: v1[f"inj_shuffled_a{a}"]["acc"] for a in ("1.0","2.0","4.0","8.0")},
                         "snap_correct": d["snap_correct"], "snaps": d["sender_snap"], "tokens": d["text_tokens_mean"], "covered": sorted(cov)}
    print(f"\n== {s} glyph -> {r} receiver  (snap correct {d['snap_correct']:.3f}; text tokens {d['text_tokens_mean']})")
    for b, al in base.items():
        print(f"  {b:28s}", "  ".join(f"a{a}:{v['all']:.3f}/{(v['cov'] if v['cov'] is not None else float('nan')):.3f}(n{v['n_all']}/{v['n_cov']}) m{v['margin']:+.2f}" for a, v in sorted(al.items())))
    print("  v1 raw bundle", v1real, "v1 shuffled", out[f"{s}->{r}"]["v1_shuf"])
    print("  snaps", d["sender_snap"])
json.dump(out, open("results/v2/inject_tables.json", "w"), indent=1)
