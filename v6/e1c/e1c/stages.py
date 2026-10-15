"""E1c stages (PREREG_E1c §7). D1 = dev pilot (allowed while DRAFT; dev book only, never TEST). T1 = TEST (needs
e1c.status == frozen, the pinned TEST book, and a qualifying D1 summary for the SAME protocol). Both need
E1C_GO == <stage> (set only on Stefan's explicit go), one start plus at most one AUTHORISED infrastructure retry,
and room in the cumulative stage cap. Model calls reuse the frozen E1b code paths."""
import os, sys, json, time, random, hashlib, inspect, math, threading
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

LEDGER_LOCK = threading.Lock()

class E1cStage(ES.Stage):
    """r4 (GPT r3): ledger writes are serialised by one process-wide lock and are atomic (unique temp file +
    os.replace), so the watchdog thread and the main thread (incl. atexit) cannot collide. timeout=None blocks
    (main thread); the watchdog passes a short timeout and never waits indefinitely."""
    def save_ledger(self, timeout=None):
        if not LEDGER_LOCK.acquire(timeout=-1 if timeout is None else timeout): raise TimeoutError("ledger lock busy")
        try:
            L = self._ledger(); L[self.alloc] = self.used_s(); self.res.mkdir(parents=True, exist_ok=True)
            tmp = self.res / f"budget_ledger.json.{os.getpid()}.{threading.get_ident()}.tmp"
            with open(tmp, "w") as fh: json.dump(L, fh); fh.flush(); os.fsync(fh.fileno())
            os.replace(tmp, self.res / "budget_ledger.json")
            self.prior_s, self.t0 = L[self.alloc], time.time()
        finally: LEDGER_LOCK.release()

def _stage(name, cap, cfg):
    """E1c Stage (E1b Stage + safe ledger) with its directory and ledger under v6/e1c/results (E1b's RES restored)."""
    old = ES.RES; ES.RES = RES
    try: S = E1cStage(name, cap, cfg, alloc=f"E1C_{name}")
    finally: ES.RES = old
    return S

def guard(S, est_s, what):
    """Hard cap incl. in-flight work (GPT r1 #6): never START a unit whose estimated duration would cross the cap."""
    S.check_budget()
    if S.used_s() + est_s > S.budget_s:
        (S.dir / "BUDGET_EXHAUSTED").write_text(f"{S.name}: next unit '{what}' (~{est_s:.0f}s) would exceed the cap; stopped, not shrunk\n")
        S.log("budget_exhausted", next=what, est_s=est_s); S.save_ledger(); print(f"[{S.name}] BUDGET EXHAUSTED (in-flight guard)"); sys.exit(3)

class Watchdog:
    """r3/r4 (GPT r2 #6, r3): enforceable deadline covering the WHOLE stage, through summary and finalisation (it is
    cancelled only in run()'s finally, after .done or an exit). On firing: a killer timer is armed FIRST, so the hard
    exit (code 3) happens within `grace` seconds even if bookkeeping blocks; then, each best-effort and isolated:
    BUDGET_EXHAUSTED marker (written first), ledger save with a lock timeout, log line; then exit. The exit never
    depends on bookkeeping succeeding. Terminality does not depend on it either: start() refuses when the ledger
    shows the cap used, and a retry cannot be authorised for a charge >= the cap."""
    def __init__(self, S, exit_fn=None, grace=5.0, lock_timeout=2.0):
        self.S = S; self.exit_fn = exit_fn or (lambda: os._exit(3)); self.grace, self.lock_timeout = grace, lock_timeout
        self.fired = self.cancelled = self.exited = False; self.done_steps = []; self._elock = threading.Lock()
        self.t = threading.Timer(max(0.0, S.budget_s - S.used_s()), self.fire); self.t.daemon = True; self.t.start()
    def _exit(self):
        with self._elock:
            if self.exited: return
            self.exited = True
        self.exit_fn()
    def fire(self):
        if self.cancelled: return
        self.fired = True
        k = threading.Timer(self.grace, self._exit); k.daemon = True; k.start()
        try:
            fd = os.open(str(self.S.dir / "BUDGET_EXHAUSTED"), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
            try: os.write(fd, f"{self.S.name}: deadline reached at the cap ({self.S.budget_s/3600:.3f} h); in-flight work killed\n".encode())
            finally: os.close(fd)
            self.done_steps.append("marker")
        except Exception: pass
        try:
            sv = self.S.save_ledger
            try: sv(timeout=self.lock_timeout)
            except TypeError: sv()
            self.done_steps.append("ledger")
        except Exception: pass
        try: self.S.log("budget_deadline", used_s=self.S.used_s()); self.done_steps.append("log")
        except Exception: pass
        self._exit()
    def cancel(self): self.cancelled = True; self.t.cancel()

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
    """GPT r1 #2 / r2 #2 / r2 new #2: T1 needs a structurally complete D1 summary qualifying the CURRENT protocol."""
    p = RES / "D1" / "summary.json"
    if not (RES / "D1" / ".done").exists() or not p.exists(): return False, "D1 not finished"
    S = json.load(open(p)); ok, why = check_d1_summary(S, X, cfg)
    if not ok: return False, why
    z = S.get("sizing", {})
    if not z.get("wrong_pass_ok"): return False, f"D1 wrong-pick-accepted rate {z.get('max_wrong_pick_accepted_rate')} > {X['criteria']['wrong_pass_max_dev']}"
    ph = z.get("projected_T1_gpu_h")
    if not isinstance(ph, (int, float)) or not math.isfinite(ph) or ph > X["caps_h"]["T1"]: return False, f"projected T1 {ph} h > T1 cap {X['caps_h']['T1']}"
    return True, "ok"

def start(cfg, name):
    X = cfg["e1c"]
    if name not in X["caps_h"]: print(f"unknown E1c stage {name}"); sys.exit(2)
    if os.environ.get("E1C_GO") != name: print(f"{name} refused: no explicit go (E1C_GO must equal '{name}')"); sys.exit(14)
    if name == "T1":
        if X["status"] != "frozen": print("T1 refused: E1c is not frozen"); sys.exit(13)
        ok, why = t1_eligibility(X, cfg)
        if not ok: print(f"T1 refused: {why}"); sys.exit(19)
    p = HERE / "CODE_HASH.txt"; pin = p.read_text().strip() if p.exists() else None
    if pin != code_hash(): print(f"{name} refused: code hash != CODE_HASH.txt"); sys.exit(16)
    kind = "dev" if name == "D1" else "test"; B = load_book(cfg, kind)
    d = RES / name
    if (d / ".done").exists(): print(f"{name} already finished"); sys.exit(0)
    term = [m for m in TERMINAL if (d / m).exists()]
    if term: print(f"{name}: terminal marker {term} -> stop and report"); sys.exit(18)
    d.mkdir(parents=True, exist_ok=True); stp = d / "e1c_state.json"
    Lp = RES / "budget_ledger.json"; used = (json.load(open(Lp)) if Lp.exists() else {}).get(f"E1C_{name}", 0.0)
    if used >= X["caps_h"][name] * 3600:   # r4: deadline stays terminal even if the marker write failed
        (d / "BUDGET_EXHAUSTED").write_text(f"{name}: ledger shows the cap used ({used/3600:.3f} h)\n"); print(f"{name}: cap already used"); sys.exit(3)
    st = json.load(open(stp)) if stp.exists() else dict(attempts=[], retry=None, cap_h=X["caps_h"][name])
    A = st["attempts"]; R = st.get("retry")
    if len(A) == 0: kind_a = "first"
    elif len(A) == 1 and R and R.get("for_attempt") == 1 and R.get("reason") in X["infra_retry_reasons"]:
        kind_a = "infra_retry"
        old = A[0]   # r3 (GPT r2 #3): results kept from attempt 1 must come from the SAME code and protocol
        rows_exist = any(d.glob("select_*.jsonl")) or any(d.glob("exchange_*.jsonl"))
        if rows_exist and (old.get("code_hash") != code_hash() or old.get("protocol_hash") != protocol_hash(X, cfg)):
            (d / "ATTEMPT_INCOMPLETE").write_text(f"{name}: attempt-1 rows exist from a different code/protocol; cannot resume\n"); sys.exit(17)
        if (d / "GPU_PREFLIGHT_FAIL").exists(): (d / "GPU_PREFLIGHT_FAIL").rename(d / "GPU_PREFLIGHT_FAIL.attempt1")
        L = RES / "budget_ledger.json"; led = json.load(open(L)) if L.exists() else {}
        led[f"E1C_{name}"] = max(led.get(f"E1C_{name}", 0.0), float(R["charged_h"]) * 3600)   # cumulative across attempts
        json.dump(led, open(L, "w"))
    else:
        (d / "ATTEMPT_INCOMPLETE").write_text(f"{name}: no further start allowed (attempts={len(A)}, retry={R}); INCOMPLETE\n"); sys.exit(17)
    A.append(dict(n=len(A) + 1, kind=kind_a, t=time.time(), code_hash=code_hash(), protocol_hash=protocol_hash(X, cfg), outcome="running"))
    json.dump(st, open(stp, "w"), indent=1)
    c = dict(cfg); c["stageB_batch_size"] = X["batch_size"]; ES._A9.clear()
    S = _stage(name, st["cap_h"], c); S.state_path = stp
    _require_gpu(S); S.watchdog = Watchdog(S)
    S.log("e1c", stage=name, status=X["status"], attempt=A[-1], cap_h=st["cap_h"], book=kind,
          book_sha256=X[f"{kind}_book_sha256"], code_hash=code_hash(), protocol_hash=protocol_hash(X, cfg))
    return X, B, S, c

def _mark(S, outcome):
    st = json.load(open(S.state_path)); st["attempts"][-1]["outcome"] = outcome; json.dump(st, open(S.state_path, "w"), indent=1)

def require_canaries(b, name, cfg, B, S):
    ref = json.load(open(E1B / "results" / "B0x" / "canaries_ref.json")).get(name)
    now = canaries(b, name, cfg, B, S); bad = canary_regressions(ref, now) if ref is not None else ["no_ref"]
    if bad:
        (S.dir / "CANARY_FAIL").write_text(f"{name}: {bad}\n"); S.log("canary_fail", model=name, bad=bad); sys.exit(8)

def free():
    try:
        import torch, gc; gc.collect(); torch.cuda.empty_cache()
    except Exception: pass

def view_for(B, eid, X):
    return sender_view(B, eid, random.Random(seed_of(X["seeds"][X["_kind"]]["generator"], "e1c_sender", eid)))

def _record_load(S, m, secs):
    """r4 (optional): persist load(+canary) timings in the attempt record, so sizing sees every attempt's loads."""
    st = json.load(open(S.state_path)); st["attempts"][-1].setdefault("loads", []).append(dict(model=m, s=secs))
    json.dump(st, open(S.state_path, "w"), indent=1)

def all_loads(state_path):
    st = json.load(open(state_path)); return [x["s"] for a in st["attempts"] for x in a.get("loads", [])]

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

def run(cfg, name):
    X, B, S, cfg = start(cfg, name); X = dict(X, _kind="dev" if name == "D1" else "test")
    try: _run(cfg, name, X, B, S)
    except SystemExit as e: _mark(S, f"exit {e.code}"); raise
    except Exception as e: _mark(S, f"crash {type(e).__name__}"); raise
    finally:
        if getattr(S, "watchdog", None): S.watchdog.cancel()

def _run(cfg, name, X, B, S):
    kind = X["_kind"]; n = X["sizes"][kind]["core_per_family"]; nr = X["sizes"][kind]["receiver_entries_per_family"]
    ids = core_ids(B, n); rids = core_ids(B, nr); q, f = X["pair"]; sel, t, vb = {}, {}, {}; est = Est(X); vbatch = X["batch_size"]   # r3: T1 uses the D1-qualified batch; a batch-1 change needs a new dev stage
    # load order: q (send+verify) -> f (send+verify; receive q->f) -> q (receive f->q)
    b, t["load1"] = load(q, cfg, B, S, est)
    t0 = time.time(); sel[q] = send_and_verify(b, q, B, ids, cfg, X, S, est, vbatch); t[f"send_verify_{q}"] = time.time() - t0
    if name == "D1": vb[q] = verifier_b1_check(b, q, B, ids, cfg, X, S, est)
    del b; free()
    b, t["load2"] = load(f, cfg, B, S, est)
    t0 = time.time(); sel[f] = send_and_verify(b, f, B, ids, cfg, X, S, est, vbatch); t[f"send_verify_{f}"] = time.time() - t0
    if name == "D1": vb[f] = verifier_b1_check(b, f, B, ids, cfg, X, S, est)
    t0 = time.time(); ex = {f"{q}_to_{f}": exchange(b, q, f, B, rids, sel[q], cfg, S, est)}; t[f"recv_{f}"] = time.time() - t0
    del b; free()
    b, t["load3"] = load(q, cfg, B, S, est)
    t0 = time.time(); ex[f"{f}_to_{q}"] = exchange(b, f, q, B, rids, sel[f], cfg, S, est); t[f"recv_{q}"] = time.time() - t0
    del b; free(); S.save_ledger()
    cases = {}
    for c in cases_for(B, rids): cases.setdefault(c["entry"], []).append(c)
    sel_rows = {m: [json.loads(l) for l in open(S.dir / f"select_{m}.jsonl")] for m in (q, f)}
    # r4: the watchdog stays armed through summary + finish; run()'s finally cancels it
    S.finish(summarize(name, X, cfg, B, sel_rows, ex, t, vb, S.used_s() / 3600, ids, rids, cases, vbatch, all_loads(S.state_path))); _mark(S, "done")

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
    if name == "D1":
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
