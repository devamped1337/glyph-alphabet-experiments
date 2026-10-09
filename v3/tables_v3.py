import json, collections, numpy as np, sys
sys.path.insert(0, "v3"); from common3 import answer
P = [("qwen","qwen"),("smol","smol"),("qwen","smol"),("smol","qwen")]
OUT = {}; lines = []
C = ["none","text_eq","text_bag_scrambled","text_word_op","glyph_snap","glyph_raw","native_book_oracle","glyph_op_shuffled","glyph_samenorm_shuffled",
     "glyph_snap_result_ablated","glyph_raw_result_ablated","op_slot_word_state","op_slot_word_embedding","op_slot_symbol_embedding","op_slot_blank_mu"]
for s, r in P:
    d = json.load(open(f"results/v3/inject_{s}_into_{r}.json")); rows = d["rows"]
    for li in (0, 1):
        R = [x for x in rows if x["li"] == li or x["cond"] in ("none","text_eq","text_bag_scrambled","text_word_op")]
        L = [x for x in rows if x["li"] == li][0]["layer"]
        T = {}
        for c in C:
            T[c] = {}
            for op in ("add","sub","gt"):
                v = [x["correct"] for x in R if x["cond"] == c and x["op"] == op]
                T[c][op] = (float(np.mean(v)), len(v)) if v else None
        # shuffled-op: does the answer follow the swapped operator? (only where swapped answer is a valid digit)
        fol = {}
        for op in ("add","sub","gt"):
            xs = [x for x in R if x["cond"] == "glyph_op_shuffled" and x["op"] == op]
            ok = [(x["dig"] == answer(x["a"], x["shuffled_to"], x["b"])) for x in xs if 0 <= answer(x["a"], x["shuffled_to"], x["b"]) <= 9]
            fol[op] = (float(np.mean(ok)), len(ok)) if ok else None
        # result-in-operands split for snap glyph and text
        split = {}
        for c in ("text_eq","glyph_snap","glyph_raw"):
            for f in (0, 1):
                v = [x["correct"] for x in R if x["cond"] == c and x["op"] != "gt" and x["r_in_operands"] == f]
                split[f"{c}|r_in_operands={f}"] = (float(np.mean(v)), len(v))
        lk = [x for x in d["leak"] if x["li"] == li]
        leak = {k: {op: [float(np.mean([x[k][j] for x in lk if x["op"] == op])) for j in range(len(lk[0][k]))] for op in ("add","sub","gt")} for k in ("ranks_snap","ranks_raw")}
        snapc = float(np.mean([x["snap_correct"] for x in R if x["cond"] == "glyph_snap"]))
        OUT[f"{s}->{r}|L{L}"] = {"table": T, "shuffled_follow": fol, "r_in_operands_split": split, "leak_mean_rank": leak, "snap_correct": snapc}
        print(f"\n=== sender {s} -> receiver {r}, receiver layer {L} (li {li}); snap correct {snapc:.3f}")
        for c in C: print(f"  {c:28s}", "  ".join(f"{op}:{T[c][op][0]:.3f}(n{T[c][op][1]})" if T[c][op] else f"{op}:  -  " for op in ("add","sub","gt")))
        print("  shuffled-op follows swapped op:", fol); print("  split:", {k: (round(a,3), n) for k, (a, n) in split.items()})
        print("  leak mean rank of result token per slot [left,op,right,eq] (snap) / [left,op,right] (raw); digits chance 5.5, tf 1.5:", {k: {o: [round(z,2) for z in v] for o, v in vv.items()} for k, vv in leak.items()})
json.dump(OUT, open("results/v3/tables_v3.json", "w"), indent=1)
