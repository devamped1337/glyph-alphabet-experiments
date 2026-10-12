"""A5 regression test (code testing, not a stage): HFBackend.generate_batch vs batch-1 generate on a tiny CPU
model (fp32, no nf4). Prompts: 8 receiver prompts + 8 probe prompts from non-TEST pools (pilot/qualification).
Pass = identical output tokens and identical parsed predictions on every prompt. Differences, if any, are listed.
Usage: python tools/smoke_hf_batch.py [--repo HuggingFaceTB/SmolLM2-135M-Instruct] [--device cpu] [--bs 8]"""
import sys, json, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from e1b import load_cfg
from e1b.cases import build
from e1b.backends import HFBackend
from e1b.protocol import receiver_parts, probe_parts
from e1b.parsing import parse_answer, parse_letter
ap = argparse.ArgumentParser(); ap.add_argument("--repo", default="HuggingFaceTB/SmolLM2-135M-Instruct")
ap.add_argument("--device", default="cpu"); ap.add_argument("--bs", type=int, default=8); ap.add_argument("--max_new", type=int, default=48)
a = ap.parse_args(); cfg = load_cfg(); B = build(cfg); E = B["entries"]
be = HFBackend("smoke", a.repo, None, device=a.device)
rec = [receiver_parts("direct_text", E[c["entry"]], c)[:3] for c in B["cases"]["pilot"][:a.bs]]
prb = [probe_parts(E[e]["text"], B["probes"]["calib"][e][i], True) for i, e in enumerate(B["groups"]["qual_F1"][:a.bs])]
res = {}
for name, jobs, mx, parse in (("receiver", rec, a.max_new, lambda t: parse_answer(t)["pred"]), ("probe", prb, 4, lambda t: parse_letter(t)[0])):
    one = [be.generate(s, p, u, mx) for s, p, u in jobs]; bat = be.generate_batch(jobs, mx)
    diff = [i for i, (x, y) in enumerate(zip(one, bat)) if x["out_ids"] != y["out_ids"]]
    pdiff = [i for i, (x, y) in enumerate(zip(one, bat)) if parse(x["text"]) != parse(y["text"])]
    res[name] = dict(n=len(jobs), token_identical=len(jobs) - len(diff), pred_identical=len(jobs) - len(pdiff), token_diff_idx=diff,
                     batch_reported=bat[0]["batch"], s_per_call_b1=round(sum(x["latency_s"] for x in one) / len(one), 3),
                     s_per_call_batched=round(bat[0]["latency_s"], 3))
print(json.dumps(dict(info=be.info, results=res), indent=1))
sys.exit(0 if all(v["token_identical"] == v["n"] for v in res.values()) else 1)
