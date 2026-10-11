"""Cache determinism diagnostic (PREREG_E1b §8 + A1.4 + A2). Batch size 1. Per independent prompt:
cold1, cold2 (fresh context, prefix+suffix in ONE evaluation), coldsplit (fresh context, prefix then suffix as
TWO evaluations, no state save/restore; A2), then the prefix is cached once, warm1, warm2 (restored prefix
state, suffix only).
Required for a cache claim (A1.4): ZERO changed predictions in cold1-cold2, warm1-warm2, cold1-warm1 and
cold2-warm2, on the sampled fixed set AND the multi-step stress set. coldsplit comparisons are diagnostic
(they separate "batch split" from "state restore" as the source of a change) and are always reported.
Bound (A2): rule of three on the sampled fixed set only, stated PER PROMPT; prompts are clustered within
entries (10 entries per family), so the bound assumes independence and is optimistic."""
from .parsing import parse_answer
from .protocol import receiver_parts

KEEP = ("text", "pred", "out_ids", "first_gap", "answer_gap", "answer_gap_source", "new_prompt_tokens", "prompt_tokens",
        "gen_tokens", "latency_s", "mode", "batch", "prompt_sha", "system_turn_sha")
REQUIRED = ("cold_cold", "warm_warm", "cold_warm_1", "cold_warm_2")
DIAGNOSTIC = ("cold_coldsplit", "coldsplit_warm")

def run_prompt(be, entry, case, max_new):
    sysm, pre, suf, _ = receiver_parts("direct_text", entry, case)
    c1 = be.generate(sysm, pre, suf, max_new, mode="cold")
    c2 = be.generate(sysm, pre, suf, max_new, mode="cold")
    cs = be.generate(sysm, pre, suf, max_new, mode="coldsplit")
    setup = be.cache_prefix(sysm, pre)
    w1 = be.generate(sysm, pre, suf, max_new, mode="warm")
    w2 = be.generate(sysm, pre, suf, max_new, mode="warm")
    be.drop_cache()
    runs = dict(cold1=c1, cold2=c2, coldsplit=cs, warm1=w1, warm2=w2)
    for r in runs.values(): r["pred"] = parse_answer(r["text"])["pred"]
    def same(a, b):   # GPT code r1: None == None is NOT agreement; an invalid parse counts as a change
        pa, pb = runs[a]["pred"], runs[b]["pred"]
        return dict(pred=(pa is not None and pb is not None and pa == pb), tokens=runs[a]["out_ids"] == runs[b]["out_ids"])
    return dict(entry=entry["id"], case=case["text"], gold=case["gold"], setup=setup,
                runs={k: {kk: v.get(kk) for kk in KEEP} for k, v in runs.items()},
                cmp={"cold_cold": same("cold1", "cold2"), "warm_warm": same("warm1", "warm2"),
                     "cold_warm_1": same("cold1", "warm1"), "cold_warm_2": same("cold2", "warm2"),
                     "cold_coldsplit": same("cold1", "coldsplit"), "coldsplit_warm": same("coldsplit", "warm1")})

def summarize(rows):
    """rows: dicts from run_prompt with a 'set' field ('fixed'|'stress')."""
    out = {}
    for st in ("fixed", "stress"):
        R = [r for r in rows if r["set"] == st]; d = {}
        for k in REQUIRED + DIAGNOSTIC:
            d[k] = dict(pred_changed=sum(not r["cmp"][k]["pred"] for r in R if k in r["cmp"]),
                        token_changed=sum(not r["cmp"][k]["tokens"] for r in R if k in r["cmp"]))
        out[st] = dict(n_prompts=len(R), invalid_runs=sum(v["pred"] is None for r in R for v in r["runs"].values()), **d)
    n = out["fixed"]["n_prompts"]
    zero = all(out[s][k]["pred_changed"] == 0 for s in ("fixed", "stress") for k in REQUIRED) and all(out[s]["invalid_runs"] == 0 for s in ("fixed", "stress"))
    out["claim_allowed"] = bool(zero and n > 0)
    out["rule_of_three_upper_95_per_prompt"] = round(3.0 / n, 4) if n else None
    out["wording"] = (f"no changed prediction observed in n={n} sampled prompts (plus {out['stress']['n_prompts']} multi-step stress prompts); "
                      f"95% upper bound on the per-prompt change probability ~{3.0/n:.1%} (rule of three, sampled set only; prompts are "
                      f"clustered within entries, so the bound assumes independence and is optimistic); batch-1 cached measurements only"
                      if out["claim_allowed"] else
                      "cache claim WITHHELD: changed or invalid predictions observed; all claims in this runtime use uncached runs")
    return out
