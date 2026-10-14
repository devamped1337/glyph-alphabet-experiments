"""A10 offline pilot (no GPU): apply the frozen parse_letter and parse_letter_a10 to every archived letter-parsed
reply of both models (B0x probes, B1c probes, B1 probes, B3 sender). Writes results/../a10_offline_pilot.json."""
import json, sys, hashlib, collections as C
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from e1b.parsing import parse_letter, parse_letter_a10
R = Path(__file__).resolve().parents[1] / "results"
out = {}
for f in sorted(list(R.glob("B0x/*.jsonl")) + list(R.glob("B1c/*.jsonl")) + list(R.glob("B1/*.jsonl")) + list(R.glob("B3/select_*.jsonl"))):
    if f.name.startswith(("prompts_", "stage_log")): continue
    rows = [json.loads(l) for l in open(f)]
    rows = [r for r in rows if "parse_path" in r and isinstance(r.get("raw"), str) and (r.get("parse_path") or "").startswith(("letter", "invalid_"))]
    if not rows: continue
    c = C.Counter(); diff = []
    for r in rows:
        o, n = parse_letter(r["raw"]), parse_letter_a10(r["raw"])
        k = "same" if o == n else ("rescued" if o[0] is None and n[0] is not None else "changed")
        c[k] += 1; c["a10_valid"] += n[0] is not None
        if k != "same" and len(diff) < 5: diff.append(dict(raw=r["raw"], old=o, new=n))
        if k == "changed": c["changed_valid_decision"] += 1
    out[f"{f.parent.name}/{f.name}"] = dict(n=len(rows), sha256=hashlib.sha256(f.read_bytes()).hexdigest(), **c, examples=diff)
tot = C.Counter()
for v in out.values():
    for k in ("n", "same", "rescued", "changed"): tot[k] += v.get(k, 0)
res = dict(files=out, totals=dict(tot), note="raw outputs reused verbatim; no model call. 'changed' = a decision the frozen parser accepted that A10 alters (must be 0).")
json.dump(res, open(Path(__file__).resolve().parents[1] / "a10_offline_pilot.json", "w"), indent=1)
print(json.dumps(dict(tot)))
for k, v in out.items(): print(k, v["n"], "same", v.get("same", 0), "rescued", v.get("rescued", 0), "changed", v.get("changed", 0), "a10_valid", v["a10_valid"])
