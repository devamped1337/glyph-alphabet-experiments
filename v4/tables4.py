import json, os, math, collections, numpy as np, torch, sys
sys.path.insert(0, "/workspace/glyph-exp/v4"); os.chdir("/workspace/glyph-exp")
from spec import *
rng = np.random.default_rng(0); KEYS = list(MODELS)
def ci(v):
    v = np.array(v, float)
    if len(v) == 0: return None
    b = [v[rng.integers(0, len(v), len(v))].mean() for _ in range(1000)]
    return [round(float(v.mean()), 3), round(float(np.percentile(b, 2.5)), 3), round(float(np.percentile(b, 97.5)), 3), len(v)]
def task(r): return {"agent": "role", "patient": "role", "pol": "negation", "mod": "uncertainty", "first": "order", "result": "maths_signed"}[r["q"]]
D = {k: json.load(open(f"results/v4/{os.environ.get('PFX','test')}_{k}.json")) for k in KEYS}; FZ = json.load(open("results/v4/frozen.json"))
BK = torch.load("results/v4/book.pt", weights_only=False)["layers"][FZ["li"]]
OUT = {"frozen": FZ, "layer": BK["layer"], "book_version": BK["main"]["version"], "n_entries": len(BK["main"]["entries"])}
TASKS = ["role", "negation", "uncertainty", "order", "maths_signed"]
tab = {}
for rk in KEYS:
    for r in D[rk]["rows"]:
        key = (rk, r.get("sender", "-"), r["cond"], task(r)); tab.setdefault(key, []).append(r["correct"])
OUT["acc"] = {"|".join(k): ci(v) for k, v in tab.items()}
# pooled over tasks
pool = collections.defaultdict(list)
for (rk, sk, c, t), v in tab.items(): pool[(rk, sk, c)] += v
OUT["acc_pooled"] = {"|".join(k): ci(v) for k, v in pool.items()}
# snapping accuracy per sender & type (each message counted once per receiver run -> use qwen receiver rows of glyph_vec)
snap = collections.defaultdict(list)
for r in D["qwen"]["rows"]:
    if r["cond"] == "glyph_vec": snap[(r["sender"], r["t"])].append(r["snap_correct"])
OUT["snap_acc"] = {"|".join(k): ci(v) for k, v in snap.items()}
# shuffled-slot follows (only where the swap changes the answer: audit fix 4)
fol = collections.defaultdict(list); excl = collections.Counter()
for rk in KEYS:
    for r in D[rk]["rows"]:
        if r["cond"] == "glyph_slot_shuffled":
            if r["follow_gold"] == r["gold"]: excl[(rk, r["sender"], task(r))] += 1; continue
            fol[(rk, r["sender"], task(r))].append(r["follows"])
OUT["slot_shuffled_follows"] = {"|".join(k): ci(v) for k, v in fol.items()}; OUT["slot_shuffled_excluded_same_answer"] = {"|".join(k): v for k, v in excl.items()}
# ID vs vector
idv = {}
for rk in KEYS:
    by = collections.defaultdict(dict)
    for r in D[rk]["rows"]:
        if r["cond"] in ("glyph_id", "glyph_vec"): by[(r["mid"], r["q"], r["sender"])][r["cond"]] = r["pred"]
    same = [int(v["glyph_id"] == v["glyph_vec"]) for v in by.values()]
    mx = max(c["id_vs_vec_maxabs"] for c in D[rk]["costs"])
    idv[rk] = {"n": len(same), "identical_predictions": float(np.mean(same)), "max_abs_state_diff_float32": mx,
               "receipt_ids_match": float(np.mean([c["receipt_ids_match"] for c in D[rk]["costs"]]))}
OUT["id_vs_vec"] = idv
# maths role-swap pair consistency: both 7-2 and 2-7 right
pc = collections.defaultdict(list)
for rk in KEYS:
    grp = collections.defaultdict(dict)
    for r in D[rk]["rows"]:
        if r["t"] == "t3": grp[(r.get("sender", "-"), r["cond"], r["group"])][r["mid"]] = r["correct"]
    for (sk, c, g), d in grp.items():
        if len(d) == 2: pc[(rk, sk, c)].append(int(all(d.values())))
OUT["maths_swap_pair_both_correct"] = {"|".join(k): ci(v) for k, v in pc.items()}
# signed split for maths
sg = collections.defaultdict(list)
for rk in KEYS:
    for r in D[rk]["rows"]:
        if r["t"] == "t3": sg[(rk, r.get("sender", "-"), r["cond"], "neg" if r["gold"].startswith("-") else "nonneg")].append(r["correct"])
OUT["maths_by_sign"] = {"|".join(k): ci(v) for k, v in sg.items()}
# bytes
ents = BK["main"]["entries"]; per = collections.Counter(e[:2] for e in ents)
bits = {t: sum(math.ceil(math.log2(per[(t, s)])) if per[(t, s)] > 1 else 0 for s in SLOTS[t]) for t in SLOTS}
by = collections.defaultdict(list)
for r in D["qwen"]["rows"]:
    if r["cond"] in ("text_prose", "text_compact"): by[(r["cond"], r["t"])].append((r["bytes"], r["tokens"]))
tokn = {k: collections.defaultdict(list) for k in KEYS}
for k in KEYS:
    for r in D[k]["rows"]:
        if r["cond"] in ("text_prose", "text_compact"): tokn[k][(r["cond"], r["t"])].append(r["tokens"])
OUT["bytes"] = {t: {"prose_utf8_bytes": float(np.mean([b for b, _ in by[("text_prose", t)]])), "compact_utf8_bytes": float(np.mean([b for b, _ in by[("text_compact", t)]])),
                    "prose_tokens": {k: float(np.mean(tokn[k][("text_prose", t)])) for k in KEYS}, "compact_tokens": {k: float(np.mean(tokn[k][("text_compact", t)])) for k in KEYS},
                    "id_bits": bits[t], "id_bytes_packed_plus_2B_version_header": math.ceil(bits[t] / 8) + 2,
                    "id_bits_if_maths_had_4_ops": (bits[t] + 2) if t == "t3" else None,
                    "vector_float32_bytes": len(SLOTS[t]) * 32 * 4, "vector_float32_bytes_plus_header": len(SLOTS[t]) * 32 * 4 + 2} for t in SLOTS}
OUT["slot_sizes"] = {f"{t}|{s}": per[(t, s)] for t, s in per}
# compute
cs = collections.defaultdict(list)
for k in KEYS:
    for c in D[k]["costs"]:
        for a in ("snap_s", "decode_s", "receipt_check_s", "sender_forward_s"): cs[a].append(c[a])
    for r in D[k]["rows"]:
        if "fwd_s" in r: cs[f"text_receiver_forward_s|{k}"].append(r["fwd_s"])
        if "fwd_s_per_row" in r: cs[f"glyph_receiver_forward_s_per_batched_row|{k}"].append(r["fwd_s_per_row"])
OUT["compute_median_ms"] = {a: round(float(np.median(v)) * 1000, 3) for a, v in cs.items()}
ST = {k: torch.load(f"results/v4/states_{k}.pt", weights_only=False)["runtime_s"] for k in KEYS}
OUT["setup_s"] = {"extraction_per_model_s(3 models in parallel, 3 threads each)": ST, "negotiation_all_layers_and_ablation_books_s": 106.3}
OUT["runtime_test_s"] = {k: D[k]["runtime_s"] for k in KEYS}
json.dump(OUT, open("results/v4/tables_v4.json", "w"), indent=1)
# compact prints
C = ["none", "text_prose", "text_compact", "text_bag", "text_compact_of_choice", "glyph_id", "glyph_vec", "glyph_raw_unsnapped", "receiver_word_state",
     "glyph_slot_shuffled", "glyph_samenorm_shuffled", "ablation_nofilter_vec", "ablation_twomodel_vec"]
for rk in KEYS:
    for sk in ["-"] + KEYS:
        for c in C:
            cells = [OUT["acc"].get(f"{rk}|{sk}|{c}|{t}") for t in TASKS]
            if any(cells): print(f"R={rk:6s} S={sk:6s} {c:24s}", "  ".join(f"{t[:5]}:{x[0]:.2f}[{x[1]:.2f},{x[2]:.2f}]n{x[3]}" if x else f"{t[:5]}:-" for t, x in zip(TASKS, cells)))
for k in ("snap_acc", "slot_shuffled_follows", "slot_shuffled_excluded_same_answer", "id_vs_vec", "maths_swap_pair_both_correct", "bytes", "compute_median_ms", "setup_s", "runtime_test_s"):
    print("==", k); print(json.dumps(OUT[k])[:3000])
