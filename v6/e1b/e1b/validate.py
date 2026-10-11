"""validate_v6.py --e1b (PREREG_E1b §11): engineering check only; certifies NO scientific claim.
Non-zero exit = nothing is published."""
import json, hashlib
from pathlib import Path
from . import load_cfg, norm, sha256_text
from .cases import verify
from .analysis import jl, flops
from . import cachediag

STAGES = ("A", "B0", "B0b", "B1", "B2", "B3")
INCOMPLETE_MARKERS = ("PROJECTION_EXCEEDS_BUDGET", "BUDGET_EXHAUSTED", "CANARY_FAIL", "NO_QUALIFYING_PAIR", "PROMPT_FIX_REQUIRED")
NO_UNIQUE = ("stage_log", "prompts_", "canary_")

def stage_status(d):
    """GPT code r1: 'complete' (.done), 'incomplete:<marker>' (an explicit stop marker), or 'broken'."""
    if (d / ".done").exists(): return "complete"
    for m in INCOMPLETE_MARKERS:
        if (d / m).exists(): return f"incomplete:{m}"
    return "broken"

def expected_files(st, cfg, res):
    ch = res / "B0" / "config_choice.json"; pair = json.load(open(ch))["pair"] if ch.exists() else None
    mA = list(cfg["models"]["stageA"])
    if st == "A": return [f"{a}_{m}.jsonl" for m in mA for a in ("A1", "A2", "A5", "A6")] + ["A4_qwen3b.jsonl", "summary.json"]
    if st == "B0": return ["canaries_ref.json", "summary.json"] + ([f"{p}_{m}.jsonl" for m in pair for p in ("qual", "probediag")] + ["pilot_timings.json", "config_choice.json"] if pair else [])
    if st == "B0b": return ["template_replacements.json", "summary.json"]
    if not pair: return ["<B0/config_choice.json with a pair>"]
    if st == "B1": return [f"{k}_{m}.jsonl" for m in pair for k in ("calib", "testgate")] + ["manip.jsonl", "accepted.json", "summary.json"]
    if st == "B2": return [f"main_{m}.jsonl" for m in pair] + ["unknown.jsonl", "byte_identity.json", "summary.json"]
    if st == "B3": return [f"select_{m}.jsonl" for m in pair] + [f"exchange_{a}_to_{b}.jsonl" for a, b in (pair, pair[::-1])] + ["summary.json"]
    return []

def run(root, inputs_only=False):
    root = Path(root); cfg = load_cfg(root / "config_e1b.json"); res = root / "results"; errs, notes = [], []
    def chk(ok, msg):
        (notes if ok else errs).append(("OK   " if ok else "FAIL ") + msg)
    B = json.load(open(root / "data" / "cases_e1b.json"))
    try: verify(B, cfg); chk(True, "builder assertions re-run (disjoint/unique/gold/neighbours/plant flips/unknown)")
    except AssertionError as ex: chk(False, f"builder assertion: {ex}")
    sha = (root / "data" / "cases_e1b.sha256").read_text().strip() if (root / "data" / "cases_e1b.sha256").exists() else None
    chk(sha == sha256_text(open(root / "data" / "cases_e1b.json").read()), "cases_e1b.json sha256 matches")
    # GPT code r1: stage-aware. An empty results dir is NOT a pass unless --inputs-only was requested.
    present = [s for s in STAGES if (res / s).is_dir()]
    if not present:
        chk(inputs_only, "no stage results present" + (" (inputs-only validation requested)" if inputs_only else
                                                        " -> nothing validated; use --inputs-only to validate inputs alone"))
    from .cases import entries_for_config
    for s in present:
        d = res / s; status = stage_status(d)
        chk(status != "broken", f"{s}: status {status} (a started stage must be complete or carry an explicit stop marker)")
        if status == "complete":
            miss = [x for x in expected_files(s, cfg, res) if not (d / x).exists()]
            chk(not miss, f"{s}: expected files present" + (f" (missing {miss})" if miss else ""))
        for f in d.glob("*.jsonl"):
            if f.name.startswith(NO_UNIQUE): continue
            ks = [r.get("key") for r in jl(f)]
            chk(len(ks) == len(set(ks)), f"{s}/{f.name}: unique keys ({len(ks)} rows)")
    ch = res / "B0" / "config_choice.json"
    if ch.exists() and json.load(open(ch)).get("pair"):
        C = json.load(open(ch)); pair = C["pair"]; core = entries_for_config(B, cfg, C["choice"]["choice"]) if C["choice"]["choice"] in cfg["configs"] else None
        if core and stage_status(res / "B3") == "complete" if (res / "B3").is_dir() else False:
            ids = [x for f in core for x in core[f]] + B["groups"]["F3L"]; items = [c for c in B["cases"]["test"] if c["entry"] in set(ids)]
            for m in pair: chk(len(jl(res / "B3" / f"select_{m}.jsonl")) == len(ids), f"B3 select_{m}: {len(ids)} rows (one per TEST entry)")
            for a, b in (pair, pair[::-1]): chk(len(jl(res / "B3" / f"exchange_{a}_to_{b}.jsonl")) == 2 * len(items), f"B3 exchange_{a}_to_{b}: {2 * len(items)} rows")
        if core and stage_status(res / "B1") == "complete" if (res / "B1").is_dir() else False:
            rp = res / "B0b" / "template_replacements.json"; repl = json.load(open(rp))["replacements"] if rp.exists() else {}
            P = cfg["configs"][C["choice"]["choice"]]["planted_calib"]
            cal = [x for f in core for x in core[f]] + B["groups"]["planted_calib"][:P] + [n for f in core for x in core[f] for n in B["neighbours"][x]] \
                  + [x for e in B["groups"]["F3L"] for x in [e] + B["neighbours"][e]]
            def n_probes(eid):
                E = B["entries"]; fam = (E[E[eid]["honest_id"]] if E[eid]["kind"] == "planted" else E[eid])["fam"]
                return sum(p["template"] not in repl for p in B["probes"]["calib"][eid]) + sum(1 for t, r in repl.items() if r and t.startswith(fam + "-"))
            want = sum(n_probes(e) for e in cal)
            for m in pair: chk(len(jl(res / "B1" / f"calib_{m}.jsonl")) == want, f"B1 calib_{m}: {want} probe rows")
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
        rows = jl(f); chk(all(set(r["runs"]) == {"cold1", "cold2", "coldsplit", "warm1", "warm2"} for r in rows), f"{f.name}: cold/cold/coldsplit/warm/warm present for every prompt")
        chk(all(r["runs"]["warm1"]["batch"] == 1 for r in rows), f"{f.name}: batch-1")
        for r in rows:
            for a, b, k in (("cold1", "cold2", "cold_cold"), ("warm1", "warm2", "warm_warm"), ("cold1", "warm1", "cold_warm_1"), ("cold2", "warm2", "cold_warm_2"), ("cold1", "coldsplit", "cold_coldsplit"), ("coldsplit", "warm1", "coldsplit_warm")):
                pa, pb = r["runs"][a]["pred"], r["runs"][b]["pred"]
                if (pa is not None and pb is not None and pa == pb) != r["cmp"][k]["pred"]: chk(False, f"{f.name}: cmp {k} inconsistent"); break
        want = {s: len(B["cases"][f"cache_{s}"]) for s in ("fixed", "stress")}
        got = {s: sum(r["set"] == s for r in rows) for s in want}
        chk(got == want, f"{f.name}: prompt counts {got} == {want}")
        sm = res / f.parent.name / f"cache_summary_{f.stem.split('_', 1)[1]}.json"
        if sm.exists(): chk(json.load(open(sm)) == json.loads(json.dumps(cachediag.summarize(rows))), f"{sm.name}: matches recomputation")
    # A2: every logged prompt_sha resolves to a rendered prompt in prompts_<model>.jsonl of the same stage dir
    for f in res.glob("*/*.jsonl"):
        if f.name.startswith("prompts_") or f.name.startswith(("A5_", "cache_")): continue
        rows = [r for r in jl(f) if r.get("prompt_sha") and r.get("model")]
        if not rows: continue
        have = set()
        for m in {r["model"] for r in rows}:
            pf = f.parent / f"prompts_{m}.jsonl"
            if pf.exists(): have |= {x["prompt_sha"] for x in jl(pf)}
        chk(all(r["prompt_sha"] in have for r in rows), f"{f.parent.name}/{f.name}: rendered prompts logged (A2)")
    # sender selection logged with full view for every exchange row
    for f in res.glob("B3/select_*.jsonl"):
        rows = jl(f); chk(all({"sender_view", "raw", "pick", "baselines", "prep_bytes", "picked_ntype", "msg_style"} <= set(r) and "regex" in r["baselines"] for r in rows), f"{f.name}: sender view/raw/pick/baselines logged")
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
            if st != "B0" and (d / ".done").exists(): chk(any(d.glob("canary_*.jsonl")), f"{st}: canaries logged")
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
