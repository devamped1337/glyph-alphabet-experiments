"""A2 smoke test of the HF cache path (no stage, no E1b data claims): tiny model, configurable device, NO nf4.
Checks cold == coldsplit == warm token-for-token on a few E1b cache prompts and that warm processes fewer tokens.
Usage: python tools/smoke_hf_cpu.py [--repo HuggingFaceTB/SmolLM2-135M-Instruct] [--device cpu] [--n 5]"""
import sys, json, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from e1b import load_cfg
from e1b.cases import build
from e1b.backends import HFBackend
from e1b import cachediag
ap = argparse.ArgumentParser(); ap.add_argument("--repo", default="HuggingFaceTB/SmolLM2-135M-Instruct")
ap.add_argument("--device", default="cpu"); ap.add_argument("--n", type=int, default=5); ap.add_argument("--max_new", type=int, default=24)
a = ap.parse_args()
cfg = load_cfg(); B = build(cfg); E = B["entries"]
be = HFBackend("smoke", a.repo, None, device=a.device)
rows = []
for st in ("fixed", "stress"):
    for c in B["cases"][f"cache_{st}"][:a.n]:
        r = cachediag.run_prompt(be, E[c["entry"]], c, a.max_new); r["set"] = st; rows.append(r)
res = dict(info=be.info, n=len(rows),
           token_identical={k: sum(r["cmp"][k]["tokens"] for r in rows) for k in rows[0]["cmp"]},
           warm_fewer_tokens=all(r["runs"]["warm1"]["new_prompt_tokens"] < r["runs"]["cold1"]["new_prompt_tokens"] for r in rows),
           answer_gap_sources=sorted({r["runs"]["cold1"]["answer_gap_source"] for r in rows}),
           system_turn_sha=rows[0]["runs"]["cold1"]["system_turn_sha"][:16], example=rows[0]["runs"]["cold1"]["text"][:120])
print(json.dumps(res, indent=1))
sys.exit(0 if all(v == len(rows) for v in res["token_identical"].values()) and res["warm_fewer_tokens"] else 1)
