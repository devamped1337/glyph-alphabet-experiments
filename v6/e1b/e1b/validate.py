"""validate_v6.py --e1b (PREREG_E1b §11): engineering check only; certifies NO scientific claim.
Non-zero exit = nothing is published."""
import json, hashlib
from pathlib import Path
from . import load_cfg, norm, sha256_text
from .cases import verify
from .analysis import jl, flops
from . import cachediag

def run(root):
    root = Path(root); cfg = load_cfg(root / "config_e1b.json"); res = root / "results"; errs, notes = [], []
    def chk(ok, msg):
        (notes if ok else errs).append(("OK   " if ok else "FAIL ") + msg)
    B = json.load(open(root / "data" / "cases_e1b.json"))
    try: verify(B, cfg); chk(True, "builder assertions re-run (disjoint/unique/gold/neighbours/plant flips/unknown)")
    except AssertionError as ex: chk(False, f"builder assertion: {ex}")
    sha = (root / "data" / "cases_e1b.sha256").read_text().strip() if (root / "data" / "cases_e1b.sha256").exists() else None
    chk(sha == sha256_text(open(root / "data" / "cases_e1b.json").read()), "cases_e1b.json sha256 matches")
    pool_of = {norm(c["text"]): p for p, cs in B["cases"].items() for c in cs}
    test_texts = {norm(c["text"]) for c in B["cases"]["test"]}
    # every arithmetic row's case text must exist in a pool; B2/B3 rows must be TEST only; nothing else uses TEST
    for f in sorted(res.rglob("*.jsonl")):
        st = f.parent.name; rows = jl(f)
        if not rows or "stage_log" in f.name: continue
        cases = [norm(r["case"]) for r in rows if isinstance(r.get("case"), str)]
        unknown = [c for c in cases if c not in pool_of]
        chk(not unknown, f"{st}/{f.name}: all {len(cases)} case texts belong to a frozen pool")
        is_test_file = (st == "B3" and f.name.startswith(("exchange_", "select_"))) or (st == "B2" and f.name.startswith(("main_", "prefix_")))
        if is_test_file: chk(all(c in test_texts for c in cases), f"{st}/{f.name}: TEST cases only")
        else: chk(not any(c in test_texts for c in cases), f"{st}/{f.name}: no TEST case used outside B2/B3")
        for r in rows:
            if "new_prompt_tokens" in r and r.get("warm") is False and "prompt_tokens" in r and r["new_prompt_tokens"] != r["prompt_tokens"]:
                chk(False, f"{f.name}: cold row with new_prompt_tokens != prompt_tokens"); break
    # cache consistency: 4 runs per prompt, counts recomputed
    for f in list(res.glob("A/A5_*.jsonl")) + list(res.glob("B2/cache_*.jsonl")):
        rows = jl(f); chk(all(set(r["runs"]) == {"cold1", "cold2", "warm1", "warm2"} for r in rows), f"{f.name}: cold/cold/warm/warm present for every prompt")
        chk(all(r["runs"]["warm1"]["batch"] == 1 for r in rows), f"{f.name}: batch-1")
        for r in rows:
            for a, b, k in (("cold1", "cold2", "cold_cold"), ("warm1", "warm2", "warm_warm"), ("cold1", "warm1", "cold_warm_1"), ("cold2", "warm2", "cold_warm_2")):
                if (r["runs"][a]["pred"] == r["runs"][b]["pred"]) != r["cmp"][k]["pred"]: chk(False, f"{f.name}: cmp {k} inconsistent"); break
        want = {s: len(B["cases"][f"cache_{s}"]) for s in ("fixed", "hard")}
        got = {s: sum(r["set"] == s for r in rows) for s in want}
        chk(got == want, f"{f.name}: prompt counts {got} == {want}")
        sm = res / f.parent.name / f"cache_summary_{f.stem.split('_', 1)[1]}.json"
        if sm.exists(): chk(json.load(open(sm)) == json.loads(json.dumps(cachediag.summarize(rows))), f"{sm.name}: matches recomputation")
    # sender selection logged with full view for every exchange row
    for f in res.glob("B3/select_*.jsonl"):
        rows = jl(f); chk(all({"sender_view", "raw", "pick", "baselines", "prep_bytes"} <= set(r) for r in rows), f"{f.name}: sender view/raw/pick/baselines logged")
        chk(all(len(r["sender_view"]["candidates"]) == 4 and r["entry"] in r["sender_view"]["candidates"] for r in rows), f"{f.name}: 4-way candidates incl. true entry")
    for f in res.glob("B3/exchange_*.jsonl"):
        snd = f.stem.split("_")[1]; sel = {r["entry"] for r in jl(res / "B3" / f"select_{snd}.jsonl")}
        chk(all(r["entry"] in sel for r in jl(f)), f"{f.name}: every exchange row has a logged selection")
    # unknown-ID: 48/48 deterministic, no model call
    U = jl(res / "B2" / "unknown.jsonl")
    if U: chk(len(U) == cfg["unknown_id_messages"] and all(not r["resolved"] and not r["model_called"] for r in U), "unknown-ID 48/48 deterministic UNKNOWN, no model call")
    # byte identity record
    bi = res / "B2" / "byte_identity.json"
    if bi.exists(): chk(json.load(open(bi))["all_identical"], "B2 byte identity asserted on all items")
    # canaries + finite (a NonFinite abort leaves no .done)
    for st in ("B0", "B1", "B2", "B3"):
        d = res / st
        if d.exists():
            chk((d / ".done").exists() or (d / "BUDGET_EXHAUSTED").exists(), f"{st}: finished or budget-stopped (no silent abort)")
            if st != "B0": chk(any(d.glob("canary_*.jsonl")), f"{st}: canaries logged")
    # MANIFEST
    man = res / "MANIFEST.json"
    if man.exists():
        M = json.load(open(man))
        for rel, h in M.items():
            p = res / rel; chk(p.exists() and hashlib.sha256(p.read_bytes()).hexdigest() == h, f"MANIFEST {rel}")
    for n in notes: print(n)
    for e in errs: print(e)
    print("\nE1b VALIDATION " + ("FAILED" if errs else "PASSED") + " (engineering check only; certifies no claim)")
    return 0 if not errs else 1

def write_manifest(root):
    res = Path(root) / "results"
    M = {str(p.relative_to(res)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(res.rglob("*")) if p.is_file() and p.name != "MANIFEST.json"}
    json.dump(M, open(res / "MANIFEST.json", "w"), indent=1); return len(M)
