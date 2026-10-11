"""Cache determinism diagnostic (PREREG_E1b §8 + A1.4). Batch size 1. Per independent prompt:
cold1, cold2 (fresh context each), then the prefix is cached once, warm1, warm2 (restored prefix).
Pairings: cold1-cold2 (noise floor), warm1-warm2, cold1-warm1 and cold2-warm2 (both must agree).
Claim allowed only if ZERO changed predictions (and token sequences are reported) in all comparisons on the
sampled fixed set AND the hard set; the rule-of-three bound is computed on the sampled fixed set only."""
from .parsing import parse_answer
from .protocol import receiver_parts

def run_prompt(be, entry, case, max_new):
    sysm, pre, suf, _ = receiver_parts("direct_text", entry, case)
    c1 = be.generate(sysm, pre, suf, max_new, warm=False)
    c2 = be.generate(sysm, pre, suf, max_new, warm=False)
    setup = be.cache_prefix(sysm, pre)
    w1 = be.generate(sysm, pre, suf, max_new, warm=True)
    w2 = be.generate(sysm, pre, suf, max_new, warm=True)
    be.drop_cache()
    runs = dict(cold1=c1, cold2=c2, warm1=w1, warm2=w2)
    for r in runs.values(): r["pred"] = parse_answer(r["text"])["pred"]
    def same(a, b): return dict(pred=runs[a]["pred"] == runs[b]["pred"], tokens=runs[a]["out_ids"] == runs[b]["out_ids"])
    return dict(entry=entry["id"], case=case["text"], gold=case["gold"], setup=setup,
                runs={k: {kk: v[kk] for kk in ("text", "pred", "out_ids", "first_gap", "answer_gap", "new_prompt_tokens",
                                                  "prompt_tokens", "gen_tokens", "latency_s", "warm", "batch")} for k, v in runs.items()},
                cmp={"cold_cold": same("cold1", "cold2"), "warm_warm": same("warm1", "warm2"),
                     "cold_warm_1": same("cold1", "warm1"), "cold_warm_2": same("cold2", "warm2")})

def summarize(rows):
    """rows: dicts from run_prompt with a 'set' field ('fixed'|'hard')."""
    out = {}
    for st in ("fixed", "hard"):
        R = [r for r in rows if r["set"] == st]; n = len(R)
        d = {}
        for k in ("cold_cold", "warm_warm", "cold_warm_1", "cold_warm_2"):
            d[k] = dict(pred_changed=sum(not r["cmp"][k]["pred"] for r in R), token_changed=sum(not r["cmp"][k]["tokens"] for r in R))
        out[st] = dict(n=n, **d)
    fx = out["fixed"]; n = fx["n"]
    zero = all(out[s][k]["pred_changed"] == 0 for s in ("fixed", "hard") for k in ("cold_cold", "warm_warm", "cold_warm_1", "cold_warm_2"))
    out["claim_allowed"] = bool(zero and n > 0)
    out["rule_of_three_upper_95"] = round(3.0 / n, 4) if n else None
    out["wording"] = (f"no discrepancy observed in n={n} sampled prompts (95% upper bound ~{3.0/n:.1%}, rule of three); "
                      f"batch-1 cached measurements only" if out["claim_allowed"] else
                      "cache claim WITHHELD: changed predictions observed; all claims in this runtime use uncached runs")
    return out
