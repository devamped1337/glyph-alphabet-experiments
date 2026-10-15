"""E1c stages (PREREG_E1c §7). D1/D2 = dev pilots (allowed while DRAFT; dev book only, never TEST; A1: D1 is closed BUDGET_EXHAUSTED, D2 qualifies T1). T1 = TEST (needs
e1c.status == frozen, the pinned TEST book, and a qualifying D2 summary (A1) for the SAME protocol). Both need
E1C_GO == <stage> (set only on Stefan's explicit go), one start plus at most one AUTHORISED infrastructure retry,
and room in the cumulative stage cap. Model calls reuse the frozen E1b code paths."""
import os, sys, json, time, random, hashlib, inspect, math
from statistics import mean
from . import RES, HERE, E1B
from .book import load_book, core_ids, cases_for
from . import verifier as VF
from .verifier import verifier_parts, parse_spec, matches
from .analysis import direction_result, cp_upper, check_selection, Incomplete
from e1b import stages as ES
from e1b.stages import (seed_of, rec, load_B, canaries, canary_regressions, _require_gpu, ask_arith_many,
                        batched_generate, log_prompt, chunks)
from e1b.protocol import sender_view, sender_parts, framed_id, bytes_record, Dictionary, render_message, SYS_SENDER
from e1b import parsing as EP
from e1b.parsing import parse_letter_a10

TERMINAL = ("BUDGET_EXHAUSTED", "CANARY_FAIL", "ATTEMPT_INCOMPLETE")   # GPU_PREFLIGHT_FAIL = infra (retry may be authorised)

def finished(d):
    """r6 (GPT r5): a stage is finished only if .done exists AND the committed attempt state records outcome 'done'
    for the last attempt and no attempt is still 'running'."""
    p = d / "e1c_state.json"
    if not (d / ".done").exists() or not p.exists(): return False
    A = json.load(open(p)).get("attempts", [])
    return bool(A) and A[-1].get("outcome") == "done" and not any(a.get("outcome") == "running" for a in A)

def is_dev(X, name): return name in X["dev_stages"]

def code_hash():
    sys.path.insert(0, str(HERE / "tools")); import code_hash as H; return H.compute()

def protocol_hash(X, cfg):
    """What D1 qualifies (GPT r1 #2, r2 #2): sender prompt + the ACTUAL sender token limit + A10 parser, verifier
    prompt/format/grammar/token limit and the EFFECTIVE verifier batch, receiver batch. Any change invalidates D1
    for T1 (a new dev stage is required)."""
    parts = [SYS_SENDER, inspect.getsource(EP.parse_letter), inspect.getsource(parse_letter_a10), EP._ID_FRAG.pattern,
             VF.SYS_VERIFY, json.dumps(VF.FMT, sort_keys=True), json.dumps({k: g.pattern for k, g in VF.GRAMMAR.items()}, sort_keys=True),
             f"verifier_max_new={X['verifier_max_new_tokens']}", f"verifier_batch={X['batch_size']}", f"receiver_batch={X['batch_size']}",
             f"sender_max_new={cfg['sender_max_new_tokens']}"]
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()

class ChildStage(ES.Stage):
    """r5: the stage CHILD. It never writes the ledger (the supervisor is its only writer), never writes a terminal
    marker or .done; its only deadline is the supervisor's pre-recorded deadline_mono (admission guard below)."""
    def save_ledger(self, *a, **k): pass
    def check_budget(self): pass
    def finish(self, summary): raise RuntimeError("the child never marks a stage done")
    def log(self, ev, **kw):
        """A1: E1b's env_info puts E1b's own CODE_HASH.txt under 'code_hash'; relabel it and add the E1c hash."""
        if ev == "start" and isinstance(kw.get("env"), dict) and "code_hash" in kw["env"]:
            env = dict(kw["env"]); env["e1b_code_hash"] = env.pop("code_hash"); env["e1c_code_hash"] = code_hash(); kw["env"] = env
        super().log(ev, **kw)

def _stage(name, cap, cfg, deadline):
    old = ES.RES; ES.RES = RES
    try: S = ChildStage(name, cap, cfg, alloc=f"E1C_{name}")
    finally: ES.RES = old
    S.deadline = deadline; return S

def guard(S, est_s, what):
    """Admission guard (GPT r1 #6): never START a unit whose estimate would cross the supervisor's deadline. Exits 3
    WITHOUT writing anything; the supervisor records BUDGET_EXHAUSTED. The enforcement is the supervisor's deadline SIGKILL (not a hard real-time bound)."""
    if time.monotonic() + est_s > S.deadline:      # r6: CLOCK_MONOTONIC (system-wide, shared with the supervisor)
        S.log("budget_admission_stop", next=what, est_s=est_s); print(f"[{S.name}] next unit '{what}' would cross the deadline -> exit 3"); sys.exit(3)

class Est:
    """Per-unit duration estimate = max(configured prior, 1.2 x longest observed)."""
    def __init__(self, X): self.v = dict(X["inflight_est_s"])
    def __call__(self, k): return self.v[k]
    def seen(self, k, s): self.v[k] = max(self.v[k], 1.2 * s)

def expected_shape(X):
    q, f = X["pair"]; d = X["sizes"]["dev"]; K = X["cases_per_entry"]
    return dict(directions={f"{q}_to_{f}", f"{f}_to_{q}"}, senders={q, f}, n_sel=2 * d["core_per_family"],
                n_entries=2 * d["receiver_entries_per_family"], n_messages=2 * d["receiver_entries_per_family"] * K,
                b1_n=X["verifier_b1_check_n"])

def check_d1_summary(S, X, cfg):
    """r3 (GPT r2 new #2): exact structure of a qualifying D1 summary (both directions, both senders, sizes,
    conformance records). Returns (ok, reason)."""
    E = expected_shape(X)
    if set(S.get("directions", {})) != E["directions"]: return False, "D1 directions != both registered directions"
    if set(S.get("selection", {})) != E["senders"]: return False, "D1 selection != both senders"
    if set(S.get("verifier_b1_check", {})) != E["senders"]: return False, "D1 conformance records missing"
    for m, s in S["selection"].items():
        if not s.get("complete") or s.get("n") != E["n_sel"]: return False, f"D1 selection {m} incomplete or wrong size"
    for d, r in S["directions"].items():
        if r.get("status") != "COMPLETE" or r.get("n_entries") != E["n_entries"] or r.get("n_messages") != E["n_messages"]:
            return False, f"D1 direction {d} incomplete or wrong size"
    for m, v in S["verifier_b1_check"].items():
        if v.get("n") != E["b1_n"]: return False, f"D1 conformance {m} wrong size"
        if v.get("identical") != v["n"]: return False, f"D1 verifier batch-8 != batch-1 for {m} (a batch-1 dev stage is required)"
    if S.get("protocol_hash") != protocol_hash(X, cfg): return False, "protocol changed since D1 (a new dev stage is required)"
    return True, "ok"

def t1_eligibility(X, cfg):
    """GPT r1 #2 / r2 #2 / r2 new #2: T1 needs a structurally complete summary of the QUALIFYING dev stage (A1: D2;
    D1 is closed BUDGET_EXHAUSTED) for the CURRENT protocol."""
    dv = X["t1_qualifying_dev_stage"]; dd = RES / dv; p = dd / "summary.json"
    term = [m for m in TERMINAL if (dd / m).exists()]
    if term: return False, f"{dv} has terminal marker(s) {term}"     # r5: terminal markers take precedence over .done
    if not finished(dd): return False, f"{dv} has no recorded 'done' outcome"   # r6
    if not (dd / ".done").exists() or not p.exists(): return False, f"{dv} not finished"   # explicit .done (GPT A1 r1)
    S = json.load(open(p)); ok, why = check_d1_summary(S, X, cfg)
    if not ok: return False, why
    z = S.get("sizing", {})
    if not z.get("wrong_pass_ok"): return False, f"D1 wrong-pick-accepted rate {z.get('max_wrong_pick_accepted_rate')} > {X['criteria']['wrong_pass_max_dev']}"
    ph = z.get("projected_T1_gpu_h")
    if not isinstance(ph, (int, float)) or not math.isfinite(ph) or ph > X["caps_h"]["T1"]: return False, f"projected T1 {ph} h > T1 cap {X['caps_h']['T1']}"
    return True, "ok"

def require_canaries(b, name, cfg, B, S):
    ref = json.load(open(E1B / "results" / "B0x" / "canaries_ref.json")).get(name)
    now = canaries(b, name, cfg, B, S); bad = canary_regressions(ref, now) if ref is not None else ["no_ref"]
    if bad:
        S.log("canary_fail", model=name, bad=bad); print(f"CANARY_FAIL {name}: {bad}"); sys.exit(8)   # r5: the supervisor writes the marker

def free():
    try:
        import torch, gc; gc.collect(); torch.cuda.empty_cache()
    except Exception: pass

def view_for(B, eid, X):
    return sender_view(B, eid, random.Random(seed_of(X["seeds"][X["_kind"]]["generator"], "e1c_sender", eid)))

def _record_load(S, m, secs):
    """r4/r5: load(+canary) timings persisted per attempt in a CHILD file (loads_attempt<n>.json), for sizing."""
    p = S.dir / f"loads_attempt{S.attempt}.json"; L = json.load(open(p)) if p.exists() else []
    L.append(dict(model=m, s=secs)); json.dump(L, open(p, "w"))

def all_loads(d):
    return [x["s"] for p in sorted(d.glob("loads_attempt*.json")) for x in json.load(open(p))]

def load(m, cfg, B, S, est):
    guard(S, est("load"), f"load {m}"); t = time.time(); b, _ = load_B(m, cfg, S); require_canaries(b, m, cfg, B, S)
    dt = time.time() - t; est.seen("load", dt); _record_load(S, m, dt); return b, dt

def run_verifier(b, jobs, cfg, X, S, est, batch):
    """Production batching path (batched_generate) at an EXPLICIT batch size; budget-guarded per chunk."""
    c = dict(cfg); c["stageB_batch_size"] = batch; out = []
    for ch in chunks(jobs, 8 * batch):
        guard(S, est("verifier_chunk"), "verifier chunk"); t = time.time()
        out += batched_generate(b, ch, X["verifier_max_new_tokens"], c); est.seen("verifier_chunk", time.time() - t)
    return out

def send_and_verify(b, m, B, ids, cfg, X, S, est, vbatch):
    """Sender (batch 1, frozen E1b sender prompt and 4-token limit, A10 parser), then the stateless verifier on the
    prose alone. accepted = valid pick AND dictionary resolve ok AND strict spec == picked entry."""
    E = B["entries"]; D = Dictionary(B); fs = f"select_{m}.jsonl"; rows = {}
    for eid in ids:
        if eid in S.done_keys(fs): continue
        guard(S, est("sender_call"), "sender call"); v = view_for(B, eid, X); s, p, u = sender_parts(v); t = time.time()
        r = b.generate(s, p, u, cfg["sender_max_new_tokens"]); log_prompt(r, m); L, path = parse_letter_a10(r["text"])
        est.seen("sender_call", time.time() - t); pick = v["candidates"]["ABCD".index(L)] if L else None
        rows[eid] = dict(entry=eid, fam=E[eid]["fam"], sender_view=v, raw=r["text"], letter=L, parse_path=path, pick=pick,
                         correct=pick == eid, picked_ntype=(E[pick].get("ntype") if pick and pick != eid else None),
                         sender_latency_s=time.time() - t, sender_gen_tokens=r.get("gen_tokens"))
    keys = list(rows); out = run_verifier(b, [verifier_parts(E[e]["fam"], render_message(E[e])) for e in keys], cfg, X, S, est, vbatch)
    for eid, r in zip(keys, out):
        x = rows[eid]; log_prompt(r, m); spec, why = parse_spec(x["fam"], r["text"])
        ok, how = matches(spec, E[x["pick"]]) if x["pick"] else (False, "sender_invalid")
        ent, res = D.resolve(framed_id(E[x["pick"]])) if x["pick"] else (None, "sender_invalid")
        x.update(verifier_raw=r["text"], verifier_parse=why, spec=spec, verified=ok, verify_reason=how, resolve=res,
                 accepted=bool(ok and ent is not None), verifier_latency_s=r.get("latency_s"), verifier_batch_n=r.get("batch_n"),
                 verifier_batch_size=vbatch)
        S.write(fs, rec(m, S.name, "select", eid, **x))
    return {json.loads(l)["entry"]: json.loads(l) for l in open(S.dir / fs)}

def verifier_b1_check(b, m, B, ids, cfg, X, S, est):
    """D1 only: production batch-8 path vs the batch-1 reference on a fixed subset (16 entries). Pre-declared rule
    (r3): any difference for either model -> T1 is NOT eligible; a new dev stage at batch 1 (amendment) re-measures
    the acceptance screen under the batch-1 path."""
    E = B["entries"]; n = X["verifier_b1_check_n"]; sub = ids[:: max(1, len(ids) // n)][:n]
    jobs = [verifier_parts(E[e]["fam"], render_message(E[e])) for e in sub]
    b8 = run_verifier(b, jobs, cfg, X, S, est, X["batch_size"]); same = 0; t1 = []
    for i, j in enumerate(jobs):
        guard(S, est("b1_check_call"), "verifier batch-1 check"); t = time.time()
        r1 = b.generate(*j, X["verifier_max_new_tokens"]); t1.append(time.time() - t); est.seen("b1_check_call", t1[-1])
        same += int(b8[i]["text"] == r1["text"])
    S.log("verifier_b1_check", model=m, n=len(sub), identical=same)
    return dict(n=len(sub), identical=same, batch1_s_per_call=mean(t1) if t1 else None)

def exchange(b, snd, rcv, B, ids, sel, cfg, S, est):
    """Receiver, per assigned entry and registered case: prose arm = the TRUE entry's prose; hybrid arm = the accepted
    ID (expanded by the delegate to the PICKED entry's dictionary text) or, if not accepted, the SAME prose
    (identical request, generated once, shared_n = 2; fallback prose bytes counted). Both arms carry the TRUE
    entry's case and are scored against that case's registered gold (asserted per row)."""
    E = B["entries"]; fx = f"exchange_{snd}_to_{rcv}.jsonl"; by = {}
    for c in cases_for(B, ids): by.setdefault(c["entry"], []).append(c)
    for ech in chunks(ids, 8):       # all jobs of an entry in one call, so fallback == prose is generated once
        jobs = []
        for eid in ech:
            e = E[eid]; s = sel[eid]
            for c in by[eid]:
                for cond in ("prose", "hybrid"):
                    k = f"{eid}|{c['text']}|{cond}"
                    if k in S.done_keys(fx): continue
                    if cond == "prose" or not s["accepted"]: jobs.append((k, cond, ("prose", e, c, None), "prose", render_message(e)))
                    else: jobs.append((k, cond, ("id_selected", E[s["pick"]], c, None), "id", framed_id(E[s["pick"]])))
        if not jobs: continue
        guard(S, est("receiver_chunk"), "receiver chunk"); t = time.time()
        res = ask_arith_many(b, rcv, [j[2] for j in jobs], cfg); est.seen("receiver_chunk", time.time() - t)
        for (k, cond, (_, ent, c, _x), sent, payload), r in zip(jobs, res):
            eid = k.split("|")[0]
            assert r["gold"] == c["gold"] and r["case"] == c["text"] and c["entry"] == eid   # scored on the TRUE case
            r.update(cond=cond, entry=eid, fam=E[eid]["fam"], sent=sent, rule_entry=ent["id"], selected=sel[eid]["pick"],
                     accepted=sel[eid]["accepted"], selection_correct=sel[eid]["correct"], sender=snd, receiver=rcv,
                     **bytes_record(cond, payload, c))
            S.write(fx, rec(rcv, S.name, "exchange", k, **r))
    return [json.loads(l) for l in open(S.dir / fx)]

def child_main(cfg, name):
    """r5: entry point of the stage child (run_e1c.py --child). Only the supervisor launches it: the token must
    match the attempt the supervisor durably recorded as running; the deadline is read from that record. Writes rows,
    loads_attempt<n>.json, summary.child.json and, LAST, CHILD_COMPLETE. Nothing else."""
    X = cfg["e1c"]; d = RES / name; st = json.load(open(d / "e1c_state.json")); a = st["attempts"][-1]
    if not os.environ.get("E1C_ATTEMPT_TOKEN") or os.environ["E1C_ATTEMPT_TOKEN"] != a.get("token") or a.get("outcome") != "running":
        print("child refused: not launched by the supervisor for the running attempt"); sys.exit(15)
    c = dict(cfg); c["stageB_batch_size"] = X["batch_size"]; ES._A9.clear()
    B = load_book(cfg, "dev" if is_dev(X, name) else "test")
    S = _stage(name, st["cap_h"], c, a["deadline_mono"]); S.attempt = a["n"]
    if os.environ.get("E1B_ALLOW_NO_GPU") == "1" and os.environ.get("E1C_TEST_HOOK"):   # test-only fake backend / faults
        import importlib.util as U; sp = U.spec_from_file_location("e1c_test_hook", os.environ["E1C_TEST_HOOK"])
        h = U.module_from_spec(sp); sp.loader.exec_module(h); h.install(sys.modules[__name__], B, a)
    _require_gpu(S)
    S.log("e1c", stage=name, status=X["status"], attempt=a, cap_h=st["cap_h"], code_hash=code_hash(), protocol_hash=protocol_hash(X, cfg))
    out = _run(c, name, dict(X, _kind="dev" if is_dev(X, name) else "test"), B, S)
    finish_child(S, out)

def finish_child(S, out):
    json.dump(out, open(S.dir / "summary.child.json", "w"), indent=1)
    (S.dir / "CHILD_COMPLETE").write_text(f"attempt {S.attempt}\n"); S.log("child_complete")

def _run(cfg, name, X, B, S):
    kind = X["_kind"]; n = X["sizes"][kind]["core_per_family"]; nr = X["sizes"][kind]["receiver_entries_per_family"]
    ids = core_ids(B, n); rids = core_ids(B, nr); q, f = X["pair"]; sel, t, vb = {}, {}, {}; est = Est(X); vbatch = X["batch_size"]   # r3: T1 uses the D1-qualified batch; a batch-1 change needs a new dev stage
    # load order: q (send+verify) -> f (send+verify; receive q->f) -> q (receive f->q)
    b, t["load1"] = load(q, cfg, B, S, est)
    t0 = time.time(); sel[q] = send_and_verify(b, q, B, ids, cfg, X, S, est, vbatch); t[f"send_verify_{q}"] = time.time() - t0
    if is_dev(X, name): vb[q] = verifier_b1_check(b, q, B, ids, cfg, X, S, est)
    del b; free()
    b, t["load2"] = load(f, cfg, B, S, est)
    t0 = time.time(); sel[f] = send_and_verify(b, f, B, ids, cfg, X, S, est, vbatch); t[f"send_verify_{f}"] = time.time() - t0
    if is_dev(X, name): vb[f] = verifier_b1_check(b, f, B, ids, cfg, X, S, est)
    t0 = time.time(); ex = {f"{q}_to_{f}": exchange(b, q, f, B, rids, sel[q], cfg, S, est)}; t[f"recv_{f}"] = time.time() - t0
    del b; free()
    b, t["load3"] = load(q, cfg, B, S, est)
    t0 = time.time(); ex[f"{f}_to_{q}"] = exchange(b, f, q, B, rids, sel[f], cfg, S, est); t[f"recv_{q}"] = time.time() - t0
    del b; free()
    cases = {}
    for c in cases_for(B, rids): cases.setdefault(c["entry"], []).append(c)
    sel_rows = {m: [json.loads(l) for l in open(S.dir / f"select_{m}.jsonl")] for m in (q, f)}
    return summarize(name, X, cfg, B, sel_rows, ex, t, vb, None, ids, rids, cases, vbatch, all_loads(S.dir))   # gpu_h set by the supervisor

def selection_stats(sel_rows, ids):
    """From the RAW selection rows (r3): complete = exactly one row per registered entry, no extras."""
    try: sel = check_selection(sel_rows, ids); complete = True; why = "ok"
    except Incomplete as e: sel = {r["entry"]: r for r in sel_rows if r["entry"] in set(ids)}; complete = False; why = str(e)
    v = [sel[e] for e in ids if e in sel]; N = len(ids); wp = sum(r["accepted"] and not r["correct"] for r in v)
    return dict(n=N, complete=complete, completeness=why, pick_acc=sum(r["correct"] for r in v) / N, sender_invalid=sum(r["pick"] is None for r in v),
                verifier_format_ok=sum(r["verifier_parse"] == "ok" for r in v) / N, coverage=sum(r["accepted"] for r in v) / N,
                wrong_pick_accepted=wp, wrong_pick_accepted_rate=wp / N, wrong_pick_accepted_cp95_upper=cp_upper(wp, N),
                correct_pick_rejected=sum(r["correct"] and not r["accepted"] for r in v),
                wrong_pick_caught=sum((r["pick"] is not None) and not r["correct"] and not r["accepted"] for r in v),
                parse_paths={p: sum(r["parse_path"] == p for r in v) for p in sorted({r["parse_path"] for r in v})})

def summarize(name, X, cfg, B, sel_rows, ex, t, vb, gpu_h, ids, rids, cases, vbatch, loads=()):
    out = dict(stage=name, status=X["status"], gpu_h=gpu_h, timing_s=t, verifier_b1_check=vb, verifier_batch_size=vbatch,
               protocol_hash=protocol_hash(X, cfg), selection={m: selection_stats(r, ids) for m, r in sel_rows.items()}, directions={})
    for d, rows in ex.items():
        out["directions"][d] = direction_result(rows, sel_rows[d.split("_to_")[0]], B, X["criteria"],
                                                seed_of(X["seeds"][X["_kind"]]["bootstrap"], d), rids, cases, ids)
    if is_dev(X, name):
        out["note"] = "DEV pilot: descriptive only; no E1c verdict. Feeds the TEST eligibility and sizing rules (PREREG_E1c §8)."
        out["sizing"] = sizing(out, X, t, sel_rows, ex, loads)
    else: out["verdict"] = verdict(out, X)
    return out

def verdict(out, X):
    """r3 (GPT r2 new #2): exact structure required (both registered directions, both senders, registered sizes)."""
    q, f = X["pair"]; n = X["sizes"]["test"]; K = X["cases_per_entry"]
    D, Sl = out.get("directions", {}), out.get("selection", {})
    if set(D) != {f"{q}_to_{f}", f"{f}_to_{q}"} or set(Sl) != {q, f}: return "INCOMPLETE"
    if any(v.get("status") != "COMPLETE" or v.get("n_entries") != 2 * n["receiver_entries_per_family"]
           or v.get("n_messages") != 2 * n["receiver_entries_per_family"] * K for v in D.values()): return "INCOMPLETE"
    if any(not s.get("complete") or s.get("n") != 2 * n["core_per_family"] for s in Sl.values()): return "INCOMPLETE"
    return "SUCCESS" if all(v["success"] for v in D.values()) else "NOT MET"

def unit_costs(sel_rows, ex):
    """r3 (GPT r2 new #1): per-unit costs from PERSISTED per-row latencies (valid across a resumed attempt):
    sender+verifier seconds per entry (summed over both senders) and receiver seconds per message (a fallback
    hybrid row shares its prose twin's generation, so only generated rows are counted)."""
    sv = 0.0
    for rows in sel_rows.values():
        sv += mean(r["sender_latency_s"] for r in rows) + mean((r.get("verifier_latency_s") or 0.0) for r in rows)
    gen, msgs = 0.0, 0
    for rows in ex.values():
        for r in rows:
            if r["cond"] == "hybrid": msgs += 1
            if r["cond"] == "prose" or r.get("sent") == "id": gen += float(r.get("latency_s") or 0.0)
    return sv, gen / max(1, msgs)

def sizing(out, X, t, sel_rows, ex, loads=()):
    """Pre-declared TEST eligibility + sizing from dev (PREREG_E1c §8), from persisted per-row latencies plus the
    longest model load (+ canaries) observed in ANY attempt (r4: loads persisted in the attempt records)."""
    nT = X["sizes"]["test"]["core_per_family"] * 2; K = X["cases_per_entry"]
    sv, rv = unit_costs(sel_rows, ex)
    load = max(list(loads) + [t.get(k, 0) for k in ("load1", "load2", "load3")] + [0])
    proj_h = (3 * load + sv * nT + rv * nT * K * 2) / 3600 * 1.25     # 3 loads; 2 directions x nT entries x K cases; 25% margin
    S = out["selection"]; wp = max(s["wrong_pick_accepted_rate"] for s in S.values())
    ok_wp = wp <= X["criteria"]["wrong_pass_max_dev"]
    return dict(test_entries_per_direction=nT if (ok_wp and proj_h <= X["caps_h"]["T1"]) else None,
                projected_T1_gpu_h=proj_h, sender_verifier_s_per_entry=sv, receiver_s_per_message=rv, load_s=load,
                max_wrong_pick_accepted_rate=wp, wrong_pass_ok=ok_wp,
                wrong_pick_accepted_cp95_upper={m: s["wrong_pick_accepted_cp95_upper"] for m, s in S.items()},
                demonstrated_le_2pct={m: s["wrong_pick_accepted_cp95_upper"] <= 0.02 for m, s in S.items()},
                projection_depends_on="dev coverage (fallback reuse), dev prompt-length mix, dev per-row latencies",
                rule="screen: observed wrong-pick-accepted <= 2% for both senders AND projection <= T1 cap. The screen does not show the rate is <= 2%; under a binomial model of the generated, family-balanced entries that needs the CP95 upper bound <= 2% (0 of 160: about 1.86%).")
