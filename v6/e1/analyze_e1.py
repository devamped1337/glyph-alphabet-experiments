#!/usr/bin/env python3
"""E1 analysis: gate TEST (acceptance/rejection + Wilson CI), primary paired comparisons
(cluster bootstrap over message groups), coverage/abstention/invalid, efficiency. Writes results/summary_e1.json."""
import json, math, random
from pathlib import Path
from collections import defaultdict
import e1
RES = e1.RES; CFG = e1.CFG
PARAMS = {"qwen3b": 3.09e9, "smol17": 1.71e9}  # FLOPs ~ 2*params*tokens (approximate)
def wilson(k, n, z=1.96):
    if n == 0: return (None, None)
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(c - h, 4), round(c + h, 4))
def main():
    D = json.load(open(e1.DATA / "cases.json")); G = json.load(open(RES / "gate_frozen.json")); out = {"gate_calibration": {k: v for k, v in G.items() if k != "scores"}}
    tg = {m: e1.load(RES / f"predictions_testgate_{m}.jsonl") for m in CFG["gate_models"]}
    sc = e1.gate_scores(tg, D["honest"] + D["test_planted"]); thr = G["threshold"]
    acc = [i for i in D["honest"] if sc[i]["score"] >= thr]; rej = [i for i in D["test_planted"] if sc[i]["score"] < thr]
    nh, npl = len(D["honest"]), len(D["test_planted"])
    out["gate_test"] = dict(gate_frozen=G["gate_frozen"], valid_accepted=len(acc), valid_n=nh, accept_rate=len(acc) / nh, accept_ci=wilson(len(acc), nh),
        planted_rejected=len(rej), planted_n=npl, reject_rate=len(rej) / npl, reject_ci=wilson(len(rej), npl),
        outcome=("PASS" if len(acc) / nh >= .90 and len(rej) / npl >= .95 else ("WEAKER (80-95% rejection)" if len(acc) / nh >= .90 and len(rej) / npl >= .80 else "FAIL")),
        by_corruption={}, scores=sc)
    book = json.load(open(e1.DATA / "book.json"))["entries"]
    for i in D["test_planted"]:
        c = book[i + "@v1"]["corr"]; b = out["gate_test"]["by_corruption"].setdefault(c, [0, 0]); b[1] += 1; b[0] += i in rej
    out["main"] = {}
    for m in CFG["gate_models"]:
        R = e1.load(RES / f"predictions_main_{m}.jsonl"); by = defaultdict(dict)
        for r in R:
            if r["stage"] == "test_main": by[r["cond"]][r["semantic_item"]] = r
        conds = sorted(by); M = {}
        for c in conds:
            rs = list(by[c].values())
            M[c] = dict(n=len(rs), acc=sum(r["correct"] for r in rs) / len(rs), abstain=sum(r["abstained"] for r in rs) / len(rs),
                        invalid=sum(r["pred"] is None for r in rs) / len(rs), coverage=sum(bool(r["coverage"]) for r in rs) / len(rs),
                        prompt_tokens=sum(r["prompt_tokens"] for r in rs) / len(rs), latency_s=sum(r["latency_s"] for r in rs) / len(rs),
                        flops_est=2 * PARAMS[m] * sum(r["prompt_tokens"] + r["gen_tokens"] for r in rs) / len(rs))
            covered = [r for r in rs if r["entry"] in acc]
            M[c]["acc_covered_only(gate-accepted entries)"] = sum(r["correct"] for r in covered) / len(covered) if covered else None
        groups = sorted({r["message_group"] for r in by["id_expanded"].values()}); rng = random.Random(0); cmp = {}
        for c in conds:
            if c in ("id_expanded", "id_expanded_cached"): continue
            items = sorted(set(by[c]) & set(by["id_expanded"])); g2 = defaultdict(list)
            for it in items: g2[by[c][it]["message_group"]].append(by["id_expanded"][it]["correct"] - by[c][it]["correct"])
            pt = sum(sum(v) for v in g2.values()) / len(items); bs = []
            for _ in range(2000):
                s = [g2[rng.choice(groups)] for _ in groups]; bs.append(sum(map(sum, s)) / sum(map(len, s)))
            bs.sort(); lo, hi = bs[50], bs[1949]
            cmp[f"id_expanded_minus_{c}"] = dict(diff=pt, ci95=(lo, hi), pairs=len(items), groups=len(g2),
                discordant=sum(x != 0 for v in g2.values() for x in v) / len(items),
                verdict=("id_expanded better" if lo > 0 else "id_expanded worse" if hi < 0 else ("equivalent (within ±0.05)" if lo > -.05 and hi < .05 else "inconclusive")))
        lat = {c: M[c]["latency_s"] for c in conds}
        unk = [r for r in R if r["stage"] == "test_unknown"]
        out["main"][m] = dict(conditions=M, paired=cmp, latency_vs_cached={c: 1 - lat[c] / lat["id_expanded_cached"] for c in conds},
            unknown_id=dict(parser_test_correct=sum(r["correct"] for r in unk if r["cond"] == "unknown_id_parser_test"),
                            model_abstained=sum(r["abstained"] for r in unk if r["cond"] == "unknown_id_model_abstention"),
                            model_n=sum(r["cond"] == "unknown_id_model_abstention" for r in unk)),
            sender_s_mean=sum(r.get("sender_s", 0) for r in R) / len(R))
    json.dump(out, open(RES / "summary_e1.json", "w"), indent=1, default=str)
    print(json.dumps({"gate_test": {k: v for k, v in out["gate_test"].items() if k != "scores"},
                      "main": {m: {"acc": {c: round(v["acc"], 3) for c, v in out["main"][m]["conditions"].items()}, "paired": out["main"][m]["paired"]} for m in out["main"]}}, indent=1, default=str))
if __name__ == "__main__": main()
