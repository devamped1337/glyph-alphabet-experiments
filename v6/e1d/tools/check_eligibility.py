"""Post-run D1-D8 + outcome rule for a finished E1d dev stage (closes GPT code r1 note 1).
  python v6/e1d/tools/check_eligibility.py <results/D1-E1d dir> [out.json]"""
import sys, json
from pathlib import Path
HERE = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(HERE))
from e1d import load_cfg
from e1d.book import load_dev
from e1d import eligibility as EL
from e1d.stages import TERMINAL
d = Path(sys.argv[1]); cfg = load_cfg(); X = cfg["e1d"]; B = load_dev(cfg); q, f = X["pair"]
st = json.load(open(d / "e1d_state.json")); A = st["attempts"]
done_ok = (d / ".done").exists() and bool(A) and A[-1]["outcome"] == "done" and not any(a["outcome"] == "running" for a in A) \
          and not any((d / m).exists() for m in TERMINAL)
S = json.load(open(d / "summary.json"))
sel = {m: [json.loads(l) for l in open(d / f"select_{m}.jsonl")] for m in (q, f)}
ex = {k: [json.loads(l) for l in open(d / f"exchange_{k}.jsonl")] for k in (f"{q}_to_{f}", f"{f}_to_{q}")}
E = EL.evaluate(S, X, cfg, B, sel, ex, done_ok=done_ok); E["D1"]["detail"] = dict(dot_done=(d / ".done").exists(), attempts=[a["outcome"] for a in A])
out = json.dumps(E, indent=1, default=str); print(out)
if len(sys.argv) > 2: open(sys.argv[2], "w").write(out)
