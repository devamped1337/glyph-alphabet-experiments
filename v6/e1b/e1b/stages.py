"""Per-stage entrypoints (PREREG_E1b §2, §7, §9 + A1). Each stage writes v6/e1b/results/<stage>/*.jsonl,
summary.json and a .done marker; it is resumable (rows already written are skipped by key) and stops on
its wall-clock budget (writes BUDGET_EXHAUSTED, exit 3) — never shrinks N or drops conditions."""
import json, os, sys, time, random, platform, subprocess
from pathlib import Path
from . import HERE, load_cfg, sha256_text

def seed_of(*parts):
    """Process-independent seed (Python's hash() is randomised per process)."""
    return int(sha256_text('|'.join(map(str, parts)))[:8], 16)
from .cases import build, verify, entries_for_config, templates, reserve_templates, make_probes
from .parsing import parse_answer, parse_letter, score_answer
from .protocol import (SYS_ARITH, SYS_PROBE, SYS_SENDER, Dictionary, receiver_parts, probe_parts, sender_view, sender_parts, framed_id, bytes_record)
from . import cachediag, projection, retrieval

RES = HERE / "results"; DATA = HERE / "data"

class BudgetExhausted(SystemExit): pass

class Stage:
    def __init__(self, name, budget_h, cfg, alloc=None):
        """GPT code r1: budgets persist CUMULATIVELY across restarts in results/budget_ledger.json, keyed by the
        allocation (B0b shares B0's allocation)."""
        self.name, self.cfg = name, cfg; self.dir = RES / name; self.dir.mkdir(parents=True, exist_ok=True)
        self.res = RES; self.alloc = alloc or name; self.t0 = time.time(); self.budget_s = budget_h * 3600; _PROMPT_DIR["d"] = self.dir; self._done = {}
        self.prior_s = self._ledger().get(self.alloc, 0.0); self._last_save = 0.0
        import atexit; atexit.register(self.save_ledger)
        self.log("start", env=env_info(cfg), alloc=self.alloc, prior_used_s=self.prior_s)
    def _ledger(self):
        p = self.res / "budget_ledger.json"
        return json.load(open(p)) if p.exists() else {}
    def used_s(self): return self.prior_s + (time.time() - self.t0)
    def save_ledger(self):
        L = self._ledger(); L[self.alloc] = self.used_s(); self.res.mkdir(parents=True, exist_ok=True)
        tmp = self.res / "budget_ledger.json.tmp"; json.dump(L, open(tmp, "w")); tmp.replace(self.res / "budget_ledger.json")
        self.prior_s, self.t0 = L[self.alloc], time.time()
    def log(self, ev, **kw):
        with open(self.dir / "stage_log.jsonl", "a") as f: f.write(json.dumps(dict(t=time.time(), ev=ev, **kw)) + "\n")
    def check_budget(self):
        if time.time() - self._last_save > 30: self.save_ledger(); self._last_save = time.time()
        if self.used_s() > self.budget_s:
            (self.dir / "BUDGET_EXHAUSTED").write_text(f"{self.name} exceeded {self.budget_s/3600:.2f} h; stopped, not shrunk\n")
            self.log("budget_exhausted"); print(f"[{self.name}] BUDGET EXHAUSTED -> stop and report"); sys.exit(3)
    def done_keys(self, fname):
        if fname not in self._done:
            p = self.dir / fname; self._done[fname] = set()
            if p.exists():
                for l in open(p): self._done[fname].add(json.loads(l)["key"])
        return self._done[fname]
    def write(self, fname, row):
        with open(self.dir / fname, "a") as f: f.write(json.dumps(row) + "\n")
        self._done.setdefault(fname, set()).add(row["key"])
    def finish(self, summary):
        json.dump(summary, open(self.dir / "summary.json", "w"), indent=1)
        (self.dir / ".done").write_text(time.strftime("%Y-%m-%d %H:%M:%S %Z") + "\n"); self.log("done")

def env_info(cfg):
    def sh(c):
        try: return subprocess.check_output(c, shell=True, text=True, stderr=subprocess.DEVNULL).strip()
        except Exception: return None
    vers = {}
    for m in ("llama_cpp", "transformers", "bitsandbytes", "torch", "numpy"):
        try: vers[m] = __import__(m).__version__
        except Exception: vers[m] = None
    return dict(commit=sh(f"git -C {HERE} rev-parse HEAD"), code_hash=(HERE / "CODE_HASH.txt").read_text().strip() if (HERE / "CODE_HASH.txt").exists() else None,
                config_sha256=sha256_text(open(HERE / "config_e1b.json").read()), seeds=cfg["seeds"], python=platform.python_version(),
                host=platform.node(), cpu=platform.processor(), versions=vers, gpu=sh("nvidia-smi --query-gpu=name,memory.total --format=csv,noheader"))

def get_book(cfg):
    p = DATA / "cases_e1b.json"
    if p.exists():
        B = json.load(open(p)); verify(B, cfg); return B
    B = build(cfg); DATA.mkdir(exist_ok=True); json.dump(B, open(p, "w"))
    (DATA / "cases_e1b.sha256").write_text(sha256_text(open(p).read()) + "\n"); return B

def bs(cfg): return int(cfg.get("stageB_batch_size", 1))
def chunks(xs, n):
    for i in range(0, len(xs), n): yield xs[i:i + n]

SYSTEMS = dict(arith=SYS_ARITH, probe=SYS_PROBE, sender=SYS_SENDER)
def rec(model, stage, step, key, **kw): return dict(model=model, stage=stage, step=step, key=key, **kw)

_PROMPT_DIR = {"d": None}; _seen_prompts = set()
def log_prompt(r, model):
    """A2: every rendered prompt is logged once per (stage dir, model) in prompts_<model>.jsonl, keyed by sha;
    rows carry prompt_sha + system_turn_sha."""
    d = _PROMPT_DIR["d"]
    if d is None or "rendered_prompt" not in r: return
    k = (str(d), model, r["prompt_sha"])
    if k not in _seen_prompts:
        _seen_prompts.add(k)
        Path(d).mkdir(parents=True, exist_ok=True)
    with open(d / f"prompts_{model}.jsonl", "a") as f:
            f.write(json.dumps(dict(prompt_sha=r["prompt_sha"], system_turn_sha=r["system_turn_sha"], prompt=r["rendered_prompt"])) + "\n")

# ------------------------------------------------------------------ generic calls
def ask_arith(be, model, cond, entry, case, cfg, msg=None, ablate=False, warm=False, extra=None):
    sysm, pre, suf, payload = receiver_parts(cond, entry, case, msg=msg, ablate_answer=ablate)
    r = be.generate(sysm, pre, suf, cfg["max_new_tokens"], warm=warm)
    return _arith_row(r, model, cond, entry, case, sysm, pre, suf, payload, extra)

def _job_len(be, job):
    """Sort key for batch composition: prompt length in tokens when the backend can tokenize, else characters."""
    if hasattr(be, "split_render") and hasattr(be, "tok"):
        try:
            pt, st = be.split_render(*job); return len(be.tok(pt, True)) + len(be.tok(st, False))
        except Exception: pass
    return len("".join(job))

def batched_generate(be, jobs, max_new, cfg):
    """Claude A5 review, code hygiene (no rule change). (a) Compute once: byte-identical (system, prefix, suffix) jobs
    are generated once and the result reused (e.g. B2 id_oracle vs direct_text); reused rows carry shared_n > 1.
    (b) Deterministic batch composition: unique jobs sorted by (prompt length, content sha), chunked by
    stageB_batch_size; rows log batch_index (per backend, monotonic), batch_pos and batch_n. Output order = input order."""
    import copy
    uniq, where = [], {}
    for j in jobs:
        k = sha256_text("\x1f".join(j))
        if k not in where: where[k] = len(uniq); uniq.append((k, j))
    order = sorted(range(len(uniq)), key=lambda i: (_job_len(be, uniq[i][1]), uniq[i][0]))
    res = [None] * len(uniq); n = max(1, bs(cfg))
    for ch in chunks(order, n):
        bi = getattr(be, "_batch_counter", 0); be._batch_counter = bi + 1
        out = be.generate_batch([uniq[i][1] for i in ch], max_new)
        assert len(out) == len(ch), "generate_batch returned the wrong number of rows"
        for pos, (i, r) in enumerate(zip(ch, out)):
            r = dict(r); r.update(batch_index=bi, batch_pos=pos, batch_n=len(ch)); res[i] = r
    cnt = {}
    for j in jobs:
        k = sha256_text("\x1f".join(j)); cnt[k] = cnt.get(k, 0) + 1
    outs = []
    for j in jobs:
        k = sha256_text("\x1f".join(j)); r = copy.deepcopy(res[where[k]]); r["shared_n"] = cnt[k]; outs.append(r)
    return outs

def ask_arith_many(be, model, reqs, cfg):
    """Batched receiver calls (PREREG §9; A5). reqs = [(cond, entry, case, extra)]; same prompts/parser as ask_arith."""
    parts = [receiver_parts(c, e, k) for c, e, k, _ in reqs]
    rs = batched_generate(be, [(s, p, u) for s, p, u, _ in parts], cfg["max_new_tokens"], cfg)
    return [_arith_row(r, model, c, e, k, *parts[i], x) for i, (r, (c, e, k, x)) in enumerate(zip(rs, reqs))]

def _arith_row(r, model, cond, entry, case, sysm, pre, suf, payload, extra):
    p = parse_answer(r["text"]); log_prompt(r, model)
    out = dict(cond=cond, entry=entry["id"], fam=entry["fam"], case=case["text"], gold=case["gold"], raw=r["text"],
               pred=p["pred"], abstained=p["abstained"], parse_path=p["path"], conflict=p["conflict"],
               correct=score_answer(p, case["gold"]), content_sha=sha256_text(sysm + pre + suf), model_called=True,
               **{k: r[k] for k in ("prompt_tokens", "new_prompt_tokens", "gen_tokens", "latency_s", "first_gap", "answer_gap",
                                    "answer_gap_source", "warm", "batch", "mode", "prompt_sha", "system_turn_sha")},
               **{k: r[k] for k in ("batch_index", "batch_pos", "batch_n", "shared_n") if k in r},
               **bytes_record(cond, payload, case))
    out.update(extra or {}); return out

def ask_probe(be, entry_text, probe, cfg, with_text=True):
    sysm, pre, suf = probe_parts(entry_text, probe, with_text)
    return _probe_row(be, be.generate(sysm, pre, suf, cfg["probe_max_new_tokens"]), probe, with_text)

def ask_probe_many(be, reqs, cfg):
    """Batched probe calls. reqs = [(entry_text, probe)] with entry text shown."""
    rs = batched_generate(be, [probe_parts(t, p, True) for t, p in reqs], cfg["probe_max_new_tokens"], cfg)
    return [_probe_row(be, r, p, True) for r, (_, p) in zip(rs, reqs)]

def _probe_row(be, r, probe, with_text):
    L, path = parse_letter(r["text"]); log_prompt(r, getattr(be, "name", "model"))
    return dict(template=probe["template"], kind=probe["kind"], with_text=with_text, raw=r["text"], letter=L, parse_path=path,
                gold=probe["gold"], honest_gold=probe["honest_gold"], correct=(L == probe["gold"]),
                honest_correct=(L == probe["honest_gold"]),   # GPT code r1: the GATE scores this; `correct` (shown text) is for diagnostics
                latency_s=r["latency_s"], gen_tokens=r["gen_tokens"], new_prompt_tokens=r["new_prompt_tokens"], first_gap=r["first_gap"], batch=r.get("batch", 1),
                prompt_sha=r.get("prompt_sha"), system_turn_sha=r.get("system_turn_sha"),
                **{k: r[k] for k in ("batch_index", "batch_pos", "batch_n", "shared_n") if k in r})

# ------------------------------------------------------------------ Stage A (box CPU, diagnostic only)
def stage_A(cfg):
    from .backends import LlamaCppBackend
    B = get_book(cfg); E = B["entries"]; A = cfg["stageA"]; S = Stage("A", A["budget_h"], cfg)
    models = cfg["models"]["stageA"]; loaded = {}
    def be(m):
        if m not in loaded:
            loaded.clear(); t = time.time()
            from .backends import verify_gguf
            if models[m].get("gguf_sha256"): verify_gguf(models[m]["gguf"], models[m]["gguf_sha256"])   # A2 pin check
            loaded[m] = LlamaCppBackend(m, models[m]["gguf"], cfg["n_ctx"], cfg["n_threads"])
            S.log("load", model=m, s=time.time() - t, info=loaded[m].info, system_turn_sha={kk: loaded[m].system_turn_sha(v) for kk, v in SYSTEMS.items()})
        return loaded[m]
    def A1(m, ablate, fname):
        for c in B["cases"]["stageA_A1"]:
            k = f"{c['entry']}|{c['text']}"
            if k in S.done_keys(fname): continue
            S.check_budget(); S.write(fname, rec(m, "A", fname[:2], k, **ask_arith(be(m), m, "direct_text", E[c["entry"]], c, cfg, ablate=ablate)))
    for m in models: A1(m, False, f"A1_{m}.jsonl")
    # projection after A1 (PREREG §7): measured per-call time x remaining calls
    lat = {}
    for m in models:
        R = [json.loads(l) for l in open(S.dir / f"A1_{m}.jsonl")]; lat[m] = sum(r["latency_s"] for r in R) / len(R)
    n_probe = sum(len(B["probes"]["calib"][e]) for g in ["A2_F1", "A2_F2", "A2_F3s", "A2_planted"] for e in B["groups"][g]) * 2
    remaining = sum(lat[m] * (len(B["cases"]["stageA_A1"]) + 5 * (cfg["cache"]["fixed_per_model"] + cfg["cache"]["stress_per_model"])
                              + 4 * len(B["cases"]["stageA_A6"])) + 0.25 * lat[m] * n_probe for m in models) + lat["qwen3b"] * len(B["cases"]["stageA_A4"])
    proj_h = (time.time() - S.t0 + remaining) / 3600
    S.log("projection", per_call_s=lat, projected_total_h=proj_h)
    if proj_h > A["budget_h"]:
        (S.dir / "PROJECTION_EXCEEDS_BUDGET").write_text(json.dumps(dict(projected_h=proj_h, budget_h=A["budget_h"])) + "\n")
        print(f"[A] projection {proj_h:.2f} h > {A['budget_h']} h -> stop and report (no shrinking)"); sys.exit(3)
    # A2 probes with and without entry text
    for m in models:
        f = f"A2_{m}.jsonl"
        for g in ["A2_F1", "A2_F2", "A2_F3s", "A2_planted"]:
            for eid in B["groups"][g]:
                for i, pr in enumerate(B["probes"]["calib"][eid]):
                    for wt in (True, False):
                        k = f"{eid}|{i}|{wt}"
                        if k in S.done_keys(f): continue
                        S.check_budget(); S.write(f, rec(m, "A", "A2", k, entry=eid, group=g, **ask_probe(be(m), E[eid]["text"], pr, cfg, wt)))
    for m in models: A1(m, True, f"A3_{m}.jsonl")
    # A4 manipulation check (Qwen-3B), planted text shown; scored only where planted gold != honest gold
    f = "A4_qwen3b.jsonl"
    for c in B["cases"]["stageA_A4"]:
        k = f"{c['entry']}|{c['text']}"
        if k in S.done_keys(f): continue
        S.check_budget(); e = E[c["entry"]]
        r = ask_arith(be("qwen3b"), "qwen3b", "direct_text", e, c, cfg)
        r.update(planted_gold=c["planted_gold"], follows_planted=(r["pred"] == c["planted_gold"]) or (c["planted_gold"] == "UNKNOWN" and r["abstained"]),
                 gold_changes=(c["planted_gold"] != c["gold"]), corruption=e["corruption"])
        S.write(f, rec("qwen3b", "A", "A4", k, **r))
    # A5 CPU cache determinism (batch 1)
    for m in models:
        f = f"A5_{m}.jsonl"
        for st in ("fixed", "stress"):
            for c in B["cases"][f"cache_{st}"]:
                k = f"{st}|{c['text']}"
                if k in S.done_keys(f): continue
                S.check_budget(); r = cachediag.run_prompt(be(m), E[c["entry"]], c, cfg["max_new_tokens"]); r["set"] = st
                S.write(f, rec(m, "A", "A5", k, **r))
    # A6 CPU prefix-cache timing: per entry cache prefix once, 10 different cases; prose gets equivalent prefix
    for m in models:
        f = f"A6_{m}.jsonl"; b = be(m)
        for eid in B["groups"]["A2_F1"] + B["groups"]["A2_F2"]:
            e = E[eid]; cs = [c for c in B["cases"]["stageA_A6"] if c["entry"] == eid]
            for cond in ("direct_text", "prose"):
                sysm, pre, _, _ = receiver_parts(cond, e, cs[0]); setup = None
                for c in cs:
                    for warm in (False, True):
                        k = f"{eid}|{cond}|{c['text']}|{warm}"
                        if k in S.done_keys(f): continue
                        S.check_budget()
                        if warm and setup is None: setup = b.cache_prefix(sysm, pre)
                        S.write(f, rec(m, "A", "A6", k, prefix_setup=setup if warm else None, **ask_arith(b, m, cond, e, c, cfg, warm=warm)))
                b.drop_cache()
    from .analysis import summarize_A
    S.finish(summarize_A(S.dir, cfg, B)); print("[A] done")

# ------------------------------------------------------------------ Stage B (Kaggle GPU)
def _B_backend_kind():
    p = RES / "B0" / "backend.json"
    return json.load(open(p)) if p.exists() else None

def load_B(name, cfg, S):
    from .backends import load_stageB, LlamaCppBackend
    kind = _B_backend_kind(); gg = os.environ.get("E1B_GGUF_DIR", "/kaggle/working/gguf")
    m = cfg["models"]["stageB"][name]; t = time.time()
    if kind and kind["kind"] == "gguf_cuda":
        from .backends import verify_gguf_set
        S.log("gguf_verified", model=name, sha256=verify_gguf_set(gg, m["gguf_sha256"]))   # A2: before any GPU use
        b = LlamaCppBackend(name, f"{gg}/{m['gguf_file']}", cfg["n_ctx"], n_gpu_layers=-1); k = "gguf_cuda"
    else:
        if not os.path.exists(f"{gg}/{m['gguf_file']}"):
            try:
                from .backends import HFBackend
                b = HFBackend(name, m["hf"], cfg["models"]["nf4"], m.get("revision"))
                r = b.generate("Reply with one word.", "", "Say OK.", 4)
                if not r["text"]: raise RuntimeError("empty output on 4-bit load check")
                k = "nf4"
            except Exception as ex:
                if kind and kind["kind"] == "nf4":
                    raise RuntimeError(f"nf4 failed for {name} after nf4 was fixed for Stage B: {ex!r}")
                (RES / "B0").mkdir(parents=True, exist_ok=True)
                json.dump(dict(kind="gguf_cuda", decided_by=name, reason=repr(ex)), open(RES / "B0" / "backend.json", "w"))
                S.log("nf4_failed_fallback", model=name, error=repr(ex))
                print("nf4 load test failed -> pre-registered GGUF/llama.cpp CUDA fallback; fetch GGUF files and re-run B0"); sys.exit(7)
            S.log("load", model=name, kind=k, s=time.time() - t, info=b.info, system_turn_sha={kk: b.system_turn_sha(v) for kk, v in SYSTEMS.items()}); return b, k
        b, k = load_stageB(name, cfg, prefer="nf4", gguf_path=f"{gg}/{m['gguf_file']}")
        if kind and k != kind["kind"]:
            raise RuntimeError(f"backend kind changed ({kind['kind']} -> {k}); must be identical for all Stage B models/stages")
    S.log("load", model=name, kind=k, s=time.time() - t, info=b.info, system_turn_sha={kk: b.system_turn_sha(v) for kk, v in SYSTEMS.items()}); return b, k

def canaries(b, name, cfg, B, S):
    """Returns {case text: dict(pred, correct)} per canary RECORD (GPT code r1)."""
    E = B["entries"]; f = f"canary_{name}.jsonl"; out = {}
    for c in B["cases"]["canary"][:cfg["canaries_per_model"]]:
        r = ask_arith(b, name, "direct_text", E[c["entry"]], c, cfg); out[c["text"]] = dict(pred=r["pred"], correct=bool(r["correct"]))
        S.write(f, rec(name, S.name, "canary", f"{c['text']}|{time.time()}", **r))
    S.log("canaries", model=name, correct=sum(v["correct"] for v in out.values()), n=len(out)); return out

def canary_regressions(ref, now):
    """Per record: any canary that was correct in B0 and is now wrong, or whose prediction changed."""
    return sorted(k for k, v in ref.items() if k not in now or now[k]["pred"] != v["pred"] or (v["correct"] and not now[k]["correct"]))

def require_canaries(b, name, cfg, B, S):
    ref = json.load(open(RES / "B0" / "canaries_ref.json")).get(name)
    now = canaries(b, name, cfg, B, S)
    bad = canary_regressions(ref, now) if ref is not None else []
    if bad:
        (S.dir / "CANARY_FAIL").write_text(json.dumps(dict(model=name, changed=bad)) + "\n"); print("canary failure -> abort stage"); sys.exit(4)

def stage_B0(cfg):
    B = get_book(cfg); E = B["entries"]; S = Stage("B0", cfg["budgets_gpu_h"]["B0"], cfg); Q = cfg["qualification"]
    # access check
    try:
        from huggingface_hub import model_info
        acc = {}
        for n in cfg["models"]["stageB_order"]:
            try: model_info(cfg["models"]["stageB"][n]["hf"]); acc[n] = True
            except Exception as ex: acc[n] = repr(ex)
        S.log("access", result=acc)
    except ImportError: acc = {}
    qualified, kinds, can_ref = [], {}, {}
    for name in cfg["models"]["stageB_order"]:
        if len({cfg["models"]["stageB"][q]["lab"] for q in qualified}) >= 2: break
        if acc.get(name, True) is not True: S.log("skip_no_access", model=name); continue
        b, k = load_B(name, cfg, S); kinds[name] = k
        if not (RES / "B0" / "backend.json").exists():
            json.dump(dict(kind=k, decided_by=name), open(RES / "B0" / "backend.json", "w"))
        can_ref[name] = canaries(b, name, cfg, B, S)
        fam_ok = {}
        for fam in cfg["families_core"] + ["F3L"]:
            pr_c = pr_n = ar_c = ar_n = 0
            for eid in B["groups"][f"qual_{fam}"]:
                for p in B["probes"]["calib"][eid]:
                    S.check_budget(); r = ask_probe(b, E[eid]["text"], p, cfg); pr_c += r["correct"]; pr_n += 1
                    S.write(f"qual_{name}.jsonl", rec(name, "B0", "qual_probe", f"{eid}|{p['template']}", entry=eid, fam=fam, **r))
            for c in [c for c in B["cases"]["qualification"] if c["fam"] == fam]:
                S.check_budget(); r = ask_arith(b, name, "direct_text", E[c["entry"]], c, cfg); ar_c += r["correct"]; ar_n += 1
                S.write(f"qual_{name}.jsonl", rec(name, "B0", "qual_arith", c["text"], **r))
            fam_ok[fam] = dict(probe=pr_c / pr_n, arith=ar_c / ar_n, ok=(pr_c / pr_n >= Q["probe_bar"] and ar_c / ar_n >= Q["arith_bar"]))
        Rq = [json.loads(l) for l in open(S.dir / f"qual_{name}.jsonl")]
        npb = max(1, sum(x["step"] == "qual_probe" for x in Rq)); nar = max(1, sum(x["step"] == "qual_arith" for x in Rq))
        fam_ok["_invalid_rate"] = dict(probe=sum(x["step"] == "qual_probe" and x.get("letter") is None for x in Rq) / npb,
                                       arith=sum(x["step"] == "qual_arith" and x.get("parse_path") == "invalid" for x in Rq) / nar)
        fam_ok["_score"] = sum(fam_ok[f]["probe"] + fam_ok[f]["arith"] for f in cfg["families_core"])   # A2: manip-check model choice
        S.log("qualification", model=name, families=fam_ok)
        core_ok = all(fam_ok[f]["ok"] for f in cfg["families_core"])
        any_core = any(fam_ok[f]["ok"] for f in cfg["families_core"])
        if any_core and cfg["models"]["stageB"][name]["lab"] not in {cfg["models"]["stageB"][q]["lab"] for q in qualified}:
            qualified.append(name)
        json.dump(dict(model=name, families=fam_ok, core_all_ok=core_ok), open(S.dir / f"qualification_{name}.json", "w"), indent=1)
        # probe-diagnostic pool (no entry text) for the leak flag, then pilot timings
        for fam in cfg["families_core"] + ["F3L"]:
            for eid in B["groups"][f"probediag_{fam}"]:
                for p in B["probes"]["calib"][eid]:
                    S.check_budget(); S.write(f"probediag_{name}.jsonl", rec(name, "B0", "probediag", f"{eid}|{p['template']}", entry=eid, fam=fam,
                                                                         **ask_probe(b, E[eid]["text"], p, cfg, with_text=False)))
        pilot_timing(b, name, cfg, B, S)
        del b
        try:
            import torch, gc; gc.collect(); torch.cuda.empty_cache()
        except Exception: pass
    json.dump(can_ref, open(S.dir / "canaries_ref.json", "w"))
    pair = qualified[:2]
    if len(pair) < 2:
        (S.dir / "NO_QUALIFYING_PAIR").write_text(json.dumps(qualified) + "\n"); S.finish(dict(pair=None, qualified=qualified)); sys.exit(5)
    leak = leak_flags(S.dir, pair, cfg)
    qd = {m: json.load(open(S.dir / f"qualification_{m}.json"))["families"] for m in pair}
    strong = max(pair, key=lambda m: qd[m]["_score"])   # A2: manipulation-check model = higher B0 qualification score
    bad = {m: qd[m]["_invalid_rate"] for m in pair if max(qd[m]["_invalid_rate"].values()) > cfg["invalid_reply_max"]}
    if bad:   # A2: invalid-reply rate > 5% -> prompt fix + dated amendment before B1
        (S.dir / "PROMPT_FIX_REQUIRED").write_text(json.dumps(bad) + "\n")
    timings = json.load(open(S.dir / "pilot_timings.json"))
    t = {ct: {m: timings[m][ct] for m in pair} for ct in ("receiver", "receiver_warm", "probe", "sender")}; t["setup_s"] = {m: timings[m]["setup_s"] for m in pair}
    choice = projection.choose(cfg, t)
    json.dump(dict(pair=pair, strong_model=strong, invalid_rates={m: qd[m]["_invalid_rate"] for m in pair}, choice=choice, leak=leak, note="freeze this in a dated PREREG amendment BEFORE B1"),
              open(S.dir / "config_choice.json", "w"), indent=1)
    S.finish(dict(pair=pair, kinds=kinds, choice=choice["choice"], leak_flagged=leak["flagged"]))
    if choice["choice"] == "INSUFFICIENT_BUDGET": print("insufficient budget -> stop and report"); sys.exit(6)

def pilot_timing(b, name, cfg, B, S):
    E = B["entries"]; tm = {"receiver": [], "receiver_warm": [], "probe": [], "sender": []}; t0 = time.time()
    rng = random.Random(0)
    # batched per-call time at the batch size actually used for B1-B3 (A1.1 + A5); warm stays batch-1
    pc = B["cases"]["pilot"]
    for ch in chunks(pc, bs(cfg)):
        S.check_budget()
        tm["receiver"] += [r["latency_s"] for r in ask_arith_many(b, name, [("direct_text", E[c["entry"]], c, None) for c in ch], cfg)]
        qp = [(E[c["entry"]]["text"], B["probes"]["calib"][B["groups"][f"qual_{E[c['entry']]['fam']}"][0]][0]) for c in ch]
        tm["probe"] += [r["latency_s"] for r in ask_probe_many(b, qp, cfg)]
    for c in pc:
        e = E[c["entry"]]; S.check_budget()
        sysm, pre, _, _ = receiver_parts("direct_text", e, c); b.cache_prefix(sysm, pre)
        tm["receiver_warm"].append(ask_arith(b, name, "direct_text", e, c, cfg, warm=True)["latency_s"]); b.drop_cache()
    for fam in cfg["families_core"]:
        for eid in B["groups"][f"pilot_{fam}"][:3]:   # GPT code r1: pilot entries (with their own neighbours), never TEST
            v = sender_view(B, eid, rng); s, p, u = sender_parts(v); t = time.time()
            b.generate(s, p, u, cfg["sender_max_new_tokens"]); tm["sender"].append(time.time() - t)
    p = S.dir / "pilot_timings.json"; d = json.load(open(p)) if p.exists() else {}
    d[name] = {k: sum(v) / len(v) for k, v in tm.items()}
    lg = [json.loads(l) for l in open(S.dir / "stage_log.jsonl") if '"load"' in l]
    can = [json.loads(l)["latency_s"] for l in open(S.dir / f"canary_{name}.jsonl")]
    d[name]["setup_s"] = max([x["s"] for x in lg if x.get("model") == name] + [0]) + sum(can)   # measured load + canary time
    json.dump(d, open(p, "w"), indent=1)

def leak_flags(d, pair, cfg):
    """A1.5: per template, pooled across entries and pair models, >= min obs; flag if no-text acc > threshold.
    Flagged templates are replaced by the next reserve of the same kind; replacements are re-checked once on the
    same pool (stage B0b) and dropped if flagged again. All before any B1 data."""
    obs = {}
    for m in pair:
        for l in open(d / f"probediag_{m}.jsonl"):
            r = json.loads(l); obs.setdefault(r["template"], []).append(r["correct"])
    return leak_rule(obs, cfg)

def _kk(t): return "-".join(t.split("-")[:2])

def leak_rule(obs, cfg):
    """A2 (replaces A1.5's flat 0.40): each probe KIND's no-text baseline is measured, pooled over its templates
    and the pair. A template is flagged if its no-text accuracy > max(kind baseline, 0.25) + 0.15, with >= 50
    no-text observations. A kind whose own baseline > 0.40 is reported as a kind-level leak and all of its
    templates are flagged."""
    # A5 (2026-10-12): the dedicated *-unstated probes are excluded from the leak rule and reported as an
    # abstention diagnostic (their no-text "Not stated" rate by kind). Ordinary probes whose gold becomes
    # "Not stated" through a corruption are unaffected (they are not of kind 'unstated').
    diag = {t: v for t, v in obs.items() if _kk(t).endswith("unstated")}
    obs = {t: v for t, v in obs.items() if t not in diag}
    kinds = {}
    for t, v in obs.items(): kinds.setdefault(_kk(t), []).extend(v)
    kb = {k: sum(v) / len(v) for k, v in kinds.items()}
    kind_leak = sorted(k for k, b in kb.items() if b > cfg["probe_leak_flag"])
    flagged = sorted(t for t, v in obs.items() if len(v) >= cfg["probe_leak_min_obs"] and (
        sum(v) / len(v) > max(kb[_kk(t)], 0.25) + cfg["probe_leak_margin_over_kind"] or _kk(t) in kind_leak))
    under = sorted(t for t, v in obs.items() if len(v) < cfg["probe_leak_min_obs"])
    return dict(flagged=flagged, kind_baseline=kb, kind_level_leak=kind_leak, insufficient_obs=under,
                acc={t: sum(v) / len(v) for t, v in obs.items()}, n={t: len(v) for t, v in obs.items()},
                abstention_diagnostic={t: dict(no_text_not_stated_rate=sum(v) / len(v), n=len(v)) for t, v in diag.items() if v})

def replacement_leaks(v, kind_baseline, cfg):
    """A3 (gpt_code_2 #2): a replacement template is dropped if its no-text accuracy exceeds the kind-relative
    threshold OR the absolute kind-level leak bar (0.40). The old rule alone allowed thresholds above 100% when
    the kind baseline was itself high; no observations counts as a leak (cannot be cleared)."""
    if not v: return True
    acc = sum(v) / len(v)
    return acc > cfg["probe_leak_flag"] or acc > max(kind_baseline, 0.25) + cfg["probe_leak_margin_over_kind"]

def stage_B0b(cfg):
    """Re-check of replacement templates for flagged ones (A1.5), on the same probe-diagnostic pool, pair only."""
    B = get_book(cfg); E = B["entries"]; S = Stage("B0b", cfg["budgets_gpu_h"]["B0"], cfg, alloc="B0")   # counts against the B0 allocation (not a reserve use)
    ch = json.load(open(RES / "B0" / "config_choice.json")); pair = ch["pair"]; flagged = ch["leak"]["flagged"]
    repl = {}
    for t in flagged:
        fam, kind = t.split("-")[0], t.split("-")[1]
        res = [r for r in reserve_templates(fam) if r[1] == kind and r[0] not in repl.values()]
        repl[t] = res[0][0] if res else None
    for m in pair:
        b, _ = load_B(m, cfg, S)
        for t, r in repl.items():
            if r is None: continue
            fam = t.split("-")[0]; tpl = [x for x in reserve_templates(fam) if x[0] == r]
            for eid in B["groups"][f"probediag_{fam}"]:
                if f"{eid}|{r}" in S.done_keys(f"recheck_{m}.jsonl"): continue
                S.check_budget()   # A3 (gpt_code_2 #2): budget checked inside the inference loop
                e = E[eid]; p = make_probes(e, e, random.Random(seed_of('recheck', r)), tpl=tpl)[0]
                S.write(f"recheck_{m}.jsonl", rec(m, "B0b", "recheck", f"{eid}|{r}", entry=eid, **ask_probe(b, e["text"], p, cfg, with_text=False)))
        del b
    obs = {}
    for m in pair:
        p = S.dir / f"recheck_{m}.jsonl"
        if p.exists():
            for l in open(p): x = json.loads(l); obs.setdefault(x["template"], []).append(x["correct"])
    kb = ch["leak"].get("kind_baseline", {})   # A2: re-check against the measured kind baseline, same rule as B0
    def leaks(t, r): return replacement_leaks(obs.get(r, []), kb.get(_kk(t), 0.25), cfg)
    final = {t: (r if r and not leaks(t, r) else None) for t, r in repl.items()}
    json.dump(dict(replacements=final, recheck_acc={k: sum(v) / len(v) for k, v in obs.items()}), open(S.dir / "template_replacements.json", "w"), indent=1)
    S.finish(dict(replacements=final))

def probe_set(B, eid, kind, cfg):
    """Probes for an entry after A1.5 replacements (dropped templates removed)."""
    rp = RES / "B0b" / "template_replacements.json"; repl = json.load(open(rp))["replacements"] if rp.exists() else {}
    ps = [p for p in B["probes"][kind][eid] if p["template"] not in repl]
    E = B["entries"]; e = E[eid]; ref = E[e["honest_id"]] if e["kind"] == "planted" else e
    for t, r in repl.items():
        if r is None or not t.startswith(ref["fam"] + "-"): continue
        tpl = [x for x in reserve_templates(ref["fam"]) if x[0] == r]
        ps += make_probes(e, ref, random.Random(seed_of('repl', eid, r, kind)), tpl=tpl)
    return ps

def _ctx(cfg):
    ch = json.load(open(RES / "B0" / "config_choice.json")); return ch["pair"], ch["choice"]["choice"]

def stage_B1(cfg):
    if (RES / "B0" / "PROMPT_FIX_REQUIRED").exists() and not (RES / "B0" / "PROMPT_FIX_AMENDED").exists():
        print("B0 invalid-reply rate > 5%: a prompt fix and dated amendment are required before B1 (A2)"); sys.exit(8)
    strong = json.load(open(RES / "B0" / "config_choice.json")).get("strong_model")
    B = get_book(cfg); E = B["entries"]; S = Stage("B1", cfg["budgets_gpu_h"]["B1"], cfg); pair, cname = _ctx(cfg)
    core = entries_for_config(B, cfg, cname); P = cfg["configs"][cname]["planted_calib"]
    calib_ids = [x for f in core for x in core[f]] + B["groups"]["planted_calib"][:P]
    calib_ids += [n for f in core for x in core[f] for n in B["neighbours"][x]] + [x for e in B["groups"]["F3L"] for x in [e] + B["neighbours"][e]]   # GPT code r1
    tg_ids = [x for f in core for x in core[f]] + B["groups"]["planted_testgate"]
    for m in pair:
        b, _ = load_B(m, cfg, S); require_canaries(b, m, cfg, B, S)
        for kind, ids in (("calib", calib_ids), ("testgate", tg_ids)):
            f = f"{kind}_{m}.jsonl"
            todo = [(eid, p) for eid in ids for p in probe_set(B, eid, kind, cfg) if f"{eid}|{p['template']}" not in S.done_keys(f)]
            for ch in chunks(todo, bs(cfg)):   # batched generation (PREREG §9; A5)
                S.check_budget()
                for (eid, p), r in zip(ch, ask_probe_many(b, [(E[eid]["text"], p) for eid, p in ch], cfg)):
                    S.write(f, rec(m, "B1", kind, f"{eid}|{p['template']}", entry=eid, planted=E[eid]["kind"] == "planted", **r))
        if m == (strong or pair[0]):   # A2: manipulation check on the model with the higher B0 qualification score
            for c in [c for c in B["cases"]["manip_B1"] if c["entry"] in set(B["groups"]["planted_calib"][:P])]:
                k = c["text"]
                if k in S.done_keys("manip.jsonl"): continue
                S.check_budget(); e = E[c["entry"]]; r = ask_arith(b, m, "direct_text", e, c, cfg)
                r.update(planted_gold=c["planted_gold"], gold_changes=c["planted_gold"] != c["gold"], corruption=e["corruption"],
                         follows_planted=(r["pred"] == c["planted_gold"]) or (c["planted_gold"] == "UNKNOWN" and r["abstained"]))
                S.write("manip.jsonl", rec(m, "B1", "manip", k, **r))
        del b
    from .analysis import gate_decision
    g = gate_decision(S.dir, pair, cfg, E)
    json.dump(dict(accepted=g["accepted"], eligible=g["eligible"], frozen_at=time.strftime("%Y-%m-%d %H:%M:%S")),
              open(S.dir / "accepted.json", "w"), indent=1)
    S.finish(g)

def accepted_set(B, cfg):
    g = json.load(open(RES / "B1" / "accepted.json"))
    return (set(g["accepted"]), True) if g["eligible"] else (None, False)

def stage_B2(cfg):
    B = get_book(cfg); E = B["entries"]; S = Stage("B2", cfg["budgets_gpu_h"]["B2"], cfg); pair, cname = _ctx(cfg)
    core = entries_for_config(B, cfg, cname); ids = set(x for f in core for x in core[f]) | set(B["groups"]["F3L"])
    items = [c for c in B["cases"]["test"] if c["entry"] in ids]; sanity = set(B["groups"]["sanity"])
    D = Dictionary(B)
    # byte identity assertion on ALL items (sha256 per item), before any model call
    ident = []
    for c in items:
        e = E[c["entry"]]; ent, why = D.resolve(framed_id(e)); assert why == "ok"
        a = receiver_parts("id_oracle", ent, c); d = receiver_parts("direct_text", e, c)
        ha, hd = sha256_text("".join(a[:3])), sha256_text("".join(d[:3])); assert ha == hd, f"byte identity failed {c['text']}"
        ident.append(dict(key=c["text"], sha=ha))
    json.dump(dict(n=len(ident), all_identical=True), open(S.dir / "byte_identity.json", "w"))
    paired = random.Random(cfg["seeds"]["sanity_subset"] + 7).sample(items, cfg["byte_identity_paired_items"])
    # unknown-ID: deterministic UNKNOWN, no model call
    for u in B["unknown_msgs"]:
        ent, why = D.resolve(u["msg"])
        S.write("unknown.jsonl", rec("delegate", "B2", "unknown", u["msg"], kind=u["kind"], resolved=ent is not None, reason=why,
                                     pred="UNKNOWN", model_called=False))
    for m in pair:
        b, _ = load_B(m, cfg, S); require_canaries(b, m, cfg, B, S); f = f"main_{m}.jsonl"
        todo = [(cond, c) for c in items for cond in ["direct_text", "prose"] + (["id_raw", "placebo"] if c["entry"] in sanity else [])
                if f"{cond}|{c['text']}" not in S.done_keys(f)]
        for ch in chunks(todo, bs(cfg)):   # batched generation (PREREG §9; A5)
            S.check_budget()
            for (cond, c), r in zip(ch, ask_arith_many(b, m, [(cond, E[c["entry"]], c, None) for cond, c in ch], cfg)):
                S.write(f, rec(m, "B2", "main", f"{cond}|{c['text']}", sanity=c["entry"] in sanity, **r))
        for c in paired:
            k = f"id_oracle|{c['text']}"
            if k in S.done_keys(f): continue
            S.check_budget(); ent, _ = D.resolve(framed_id(E[c["entry"]]))
            S.write(f, rec(m, "B2", "id_oracle_paired", k, **ask_arith(b, m, "id_oracle", ent, c, cfg)))
        # GPU cache test (batch 1) then prefix-cached timing only if the claim is allowed
        fc = f"cache_{m}.jsonl"
        for st in ("fixed", "stress"):
            for c in B["cases"][f"cache_{st}"]:
                k = f"{st}|{c['text']}"
                if k in S.done_keys(fc): continue
                S.check_budget(); r = cachediag.run_prompt(b, E[c["entry"]], c, cfg["max_new_tokens"]); r["set"] = st
                S.write(fc, rec(m, "B2", "cache", k, **r))
        cs = cachediag.summarize([json.loads(l) for l in open(S.dir / fc)])
        json.dump(cs, open(S.dir / f"cache_summary_{m}.json", "w"), indent=1)
        if cs["claim_allowed"]:
            fw = f"prefix_{m}.jsonl"
            for eid in sorted(ids):
                e = E[eid]; ecs = [c for c in items if c["entry"] == eid]
                for cond in ("direct_text", "prose"):
                    sysm, pre, _, _ = receiver_parts(cond, e, ecs[0]); setup = b.cache_prefix(sysm, pre)
                    for c in ecs:
                        k = f"{cond}|{c['text']}"
                        if k in S.done_keys(fw): continue
                        S.check_budget(); S.write(fw, rec(m, "B2", "prefix_warm", k, prefix_setup=setup, **ask_arith(b, m, cond, e, c, cfg, warm=True)))
                    b.drop_cache()
        else:
            S.log("prefix_cache_skipped_by_rule", model=m, reason=cs["wording"])
        del b
    from .analysis import summarize_B2
    S.finish(summarize_B2(S.dir, pair, cfg, B))

def b3_view(B, eid, cfg):
    """The frozen per-entry B3 sender view (candidate order from the generator seed). Used by B3 AND by the
    pre-run regex report, so both use the identical permutation (A3, gpt_code_2 #3)."""
    return sender_view(B, eid, random.Random(seed_of(cfg["seeds"]["generator"], 'sender', eid)))

def regex_report(B, cfg, ids=None):
    """Regex baseline on the frozen B3 views, by message style; ties among top scores are resolved by the
    first-listed candidate, i.e. a guess, and are counted separately (A3)."""
    E = B["entries"]; ids = ids or [x for g in ("core_F1", "core_F2", "F3L") for x in B["groups"][g]]; out = {}
    for eid in ids:
        v = b3_view(B, eid, cfg); i, sc = retrieval.regex_pick(v["message"], v["labels"])
        d = out.setdefault(E[eid].get("msg_style", "plain"), dict(n=0, correct=0, tie_guess=0, tie_guess_correct=0))
        tie = sum(s == max(sc) for s in sc) > 1; ok = v["candidates"][i] == eid
        d["n"] += 1; d["correct"] += ok; d["tie_guess"] += tie; d["tie_guess_correct"] += tie and ok
    return out

def stage_B3(cfg):
    B = get_book(cfg); E = B["entries"]; S = Stage("B3", cfg["budgets_gpu_h"]["B3"], cfg); pair, cname = _ctx(cfg)
    core = entries_for_config(B, cfg, cname); ids = [x for f in core for x in core[f]] + B["groups"]["F3L"]
    items = [c for c in B["cases"]["test"] if c["entry"] in set(ids)]
    acc, gated = accepted_set(B, cfg); D = Dictionary(B, accepted=acc if gated else None)   # recorded gate decision (GPT code r1)
    # 1. selection: each pair model as sender, once per entry (message is entry-level); view logged in full
    for m in pair:
        b, _ = load_B(m, cfg, S); require_canaries(b, m, cfg, B, S); f = f"select_{m}.jsonl"
        for eid in ids:
            if eid in S.done_keys(f): continue
            S.check_budget(); v = b3_view(B, eid, cfg)
            s, p, u = sender_parts(v); t = time.time(); r = b.generate(s, p, u, cfg["sender_max_new_tokens"])
            L, path = parse_letter(r["text"]); pick = v["candidates"]["ABCD".index(L)] if L else None
            ri, rs = retrieval.regex_pick(v["message"], v["labels"])
            bl = {"regex": v["candidates"][ri], "regex_tie": sum(s == max(rs) for s in rs) > 1,
                  "tfidf": v["candidates"][retrieval.tfidf_pick(v["message"], v["labels"])[0]],
                  "bm25": v["candidates"][retrieval.bm25_pick(v["message"], v["labels"])[0]]}
            try: bl["minilm"] = v["candidates"][retrieval.embed_pick(v["message"], v["labels"], cfg["models"]["embedding_baseline"])[0]]
            except Exception as ex: bl["minilm"] = None; bl["minilm_error"] = repr(ex)
            S.write(f, rec(m, "B3", "select", eid, entry=eid, fam=E[eid]["fam"], sender_view=v, raw=r["text"], letter=L, parse_path=path,
                           pick=pick, correct=pick == eid, msg_style=E[eid].get("msg_style", "plain"),
                           picked_ntype=(E[pick].get("ntype") if pick and pick != eid else None), latency_s=r["latency_s"], new_prompt_tokens=r["new_prompt_tokens"],
                           gen_tokens=r["gen_tokens"], baselines=bl, prep_bytes=v["prep_bytes"]))
        del b
    picks = {m: {json.loads(l)["entry"]: json.loads(l) for l in open(S.dir / f"select_{m}.jsonl")} for m in pair}
    # 2. receiver = the OTHER model: id_selected (pipeline) vs prose (same original message)
    for snd, rcv in ((pair[0], pair[1]), (pair[1], pair[0])):
        b, _ = load_B(rcv, cfg, S); f = f"exchange_{snd}_to_{rcv}.jsonl"
        model_jobs = []   # (key, cond, entry_for_prompt, case, extra) for batched receiver calls
        for c in items:
            e = E[c["entry"]]; sel = picks[snd][c["entry"]]
            k = f"id_selected|{c['text']}"
            if k not in S.done_keys(f):
                if sel["pick"] is None:
                    r = dict(cond="id_selected", entry=e["id"], fam=e["fam"], case=c["text"], gold=c["gold"], pred=None, correct=False,
                             abstained=False, model_called=False, reason="sender_invalid", **bytes_record("id_selected", "", c))
                else:
                    msg = framed_id(E[sel["pick"]]); ent, why = D.resolve(msg)
                    if ent is None:
                        r = dict(cond="id_selected", entry=e["id"], fam=e["fam"], case=c["text"], gold=c["gold"], pred="UNKNOWN",
                                 abstained=True, correct=False, model_called=False, reason=why, **bytes_record("id_selected", msg, c))
                    else:
                        model_jobs.append((k, "id_selected", ent, c, dict(selected=ent["id"], selection_correct=ent["id"] == e["id"],
                                                                           sender=snd, receiver=rcv, gated=gated, entry=e["id"], fam=e["fam"])))
                        r = None
                if r is not None: r.update(sender=snd, receiver=rcv, gated=gated); S.write(f, rec(rcv, "B3", "exchange", k, **r))
            k = f"prose|{c['text']}"
            if k not in S.done_keys(f): model_jobs.append((k, "prose", e, c, dict(sender=snd, receiver=rcv)))
        for ch in chunks(model_jobs, bs(cfg)):   # batched generation (PREREG §9; A5)
            S.check_budget()
            for (k, cond, ent, c, x), r in zip(ch, ask_arith_many(b, rcv, [(cond, ent, c, None) for k, cond, ent, c, x in ch], cfg)):
                r.update(x); S.write(f, rec(rcv, "B3", "exchange", k, **r))
        del b
    from .analysis import summarize_B3
    S.finish(summarize_B3(S.dir, pair, cfg, B, gated))

def stage_build(cfg):
    B = get_book(cfg); print(json.dumps({k: len(v) for k, v in B["cases"].items()}), "entries", len(B["entries"]))

STAGES = dict(build=stage_build, A=stage_A, B0=stage_B0, B0b=stage_B0b, B1=stage_B1, B2=stage_B2, B3=stage_B3)
