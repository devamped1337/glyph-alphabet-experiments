"""EXPLORATORY (approved 2026-10-12; Claude stageA proposal P2). NOT part of the frozen PREREG, no claims, no
frozen settings changed. Qwen2.5-3B Q4_K_M on the box CPU (llama.cpp, same n_ctx/threads/max_new_tokens/parser as
Stage A). Items: the 40 gold-changing A4 manipulation cases (23 planted-gold UNKNOWN + 17 planted-gold numeric).
Baseline arm = the logged Stage A A4 rows (current frozen system prompt, same cold one-chunk path, greedy).
Variant arm = the same prompts with a more explicit abstention instruction appended to the system prompt."""
import sys, json, time
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parent.parent; sys.path.insert(0, str(ROOT))
from e1b import load_cfg
from e1b.protocol import receiver_parts
from e1b.parsing import parse_answer
from e1b.backends import LlamaCppBackend, verify_gguf
VARIANT = (" If the rule does not state what is needed for this case (for example, it does not say what applies to this "
           "person or situation), do not guess or assume: finish with 'Answer: UNKNOWN'.")
cfg = load_cfg(); B = json.load(open(ROOT / "data" / "cases_e1b.json")); E = B["entries"]
base = [json.loads(l) for l in open(ROOT / "results" / "A" / "A4_qwen3b.jsonl")]
items = [r for r in base if r["gold_changes"]]
m = cfg["models"]["stageA"]["qwen3b"]; verify_gguf(m["gguf"], m["gguf_sha256"])
be = LlamaCppBackend("qwen3b", m["gguf"], cfg["n_ctx"], cfg["n_threads"])
out = HERE / "variant_qwen3b.jsonl"; done = {json.loads(l)["key"] for l in open(out)} if out.exists() else set()
cases = {c["text"]: c for c in B["cases"]["stageA_A4"]}
for r in items:
    if r["key"] in done: continue
    c = cases[r["case"]]; e = E[r["entry"]]
    s, p, u, _ = receiver_parts("direct_text", e, c)
    g = be.generate(s + VARIANT, p, u, cfg["max_new_tokens"]); pa = parse_answer(g["text"])
    row = dict(key=r["key"], entry=r["entry"], corruption=r["corruption"], case=r["case"], honest_gold=r["gold"], planted_gold=r["planted_gold"],
               raw=g["text"], pred=pa["pred"], parse_path=pa["path"], prompt_tokens=g["prompt_tokens"], gen_tokens=g["gen_tokens"],
               latency_s=g["latency_s"], system=s + VARIANT, base_pred=r["pred"], base_follows=r["follows_planted"], exploratory=True)
    row["follows_planted"] = pa["pred"] == r["planted_gold"]
    open(out, "a").write(json.dumps(row) + "\n"); print(len(done) + 1, row["corruption"], row["planted_gold"], row["pred"], flush=True); done.add(r["key"])
print("done", time.strftime("%H:%M"))
