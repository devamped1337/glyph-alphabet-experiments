"""E1c stages (PREREG_E1c §7). D1 = dev pilot (allowed while DRAFT; dev book only, never TEST). T1 = TEST (needs
e1c.status == frozen, the pinned TEST book, and a qualifying D1 summary for the SAME protocol). Both need
E1C_GO == <stage> (set only on Stefan's explicit go), one start plus at most one AUTHORISED infrastructure retry,
and room in the cumulative stage cap. Model calls reuse the frozen E1b code paths."""
import os, sys, json, time, random, hashlib, inspect
from statistics import mean
from . import RES, HERE, E1B
from .book import load_book, core_ids, cases_for
from . import verifier as VF
from .verifier import verifier_parts, parse_spec, matches
from .analysis import direction_result, cp_upper
from e1b import stages as ES
from e1b.stages import (seed_of, rec, load_B, canaries, canary_regressions, _require_gpu, ask_arith_many,
                        batched_generate, log_prompt, chunks)
from e1b.protocol import sender_view, sender_parts, framed_id, bytes_record, Dictionary, render_message, SYS_SENDER
from e1b import parsing as EP
from e1b.parsing import parse_letter_a10

TERMINAL = ("BUDGET_EXHAUSTED", "CANARY_FAIL", "ATTEMPT_INCOMPLETE")   # GPU_PREFLIGHT_FAIL = infra (retry may be authorised)

def code_hash():
    sys.path.insert(0, str(HERE / "tools")); import code_hash as H; return H.compute()

def protocol_hash(X):
    """What D1 qualifies (GPT r1 #2): sender prompt + token limit + A10 parser, verifier prompt/format/grammar and
    token limit, receiver batch size. Any change invalidates D1 for T1 (a new dev stage is required)."""
    parts = [SYS_SENDER, inspect.getsource(EP.parse_letter), inspect.getsource(parse_letter_a10), EP._ID_FRAG.pattern,
             VF.SYS_VERIFY, json.dumps(VF.FMT, sort_keys=True), json.dumps({k: g.pattern for k, g in VF.GRAMMAR.items()}, sort_keys=True),
             str(X["verifier_max_new_tokens"]), str(X["batch_size"]), "sender_max_new=4"]
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()

def _stage(name, cap, cfg):
    """E1b Stage with its directory and budget ledger under v6/e1c/results (E1b's RES restored afterwards)."""
    old = ES.RES; ES.RES = RES
    try: S = ES.Stage(name, cap, cfg, alloc=f"E1C_{name}")
    finally: ES.RES = old
    return S

def guard(S, est_s, what):
    """Hard cap incl. in-flight work (GPT r1 #6): never START a unit whose estimated duration would cross the cap."""
    S.check_budget()
    if S.used_s() + est_s > S.budget_s:
        (S.dir / "BUDGET_EXHAUSTED").write_text(f"{S.name}: next unit '{what}' (~{est_s:.0f}s) would exceed the cap; stopped, not shrunk\n")
        S.log("budget_exhausted", next=what, est_s=est_s); S.save_ledger(); print(f"[{S.name}] BUDGET EXHAUSTED (in-flight guard)"); sys.exit(3)

class Est:
    """Per-unit duration estimate = max(configured prior, 1.2 x longest observed)."""
    def __init__(self, X): self.v = dict(X["inflight_est_s"])
    def __call__(self, k): return self.v[k]
    def seen(self, k, s): self.v[k] = max(self.v[k], 1.2 * s)

def t1_eligibility(X):
    """GPT r1 #2: T1 needs the recorded D1 summary to qualify the CURRENT protocol and the frozen T1 cap."""
    p = RES / "D1" / "summary.json"
    if not (RES / "D1" / ".done").exists() or not p.exists(): return False, "D1 not finished"
    S = json.load(open(p)); z = S.get("sizing", {})
    if S.get("protocol_hash") != protocol_hash(X): return False, "protocol changed since D1 (a new dev stage is required)"
    if not all(d.get("status") == "COMPLETE" for d in S["directions"].values()): return False, "D1 incomplete"
    if not all(s.get("complete") for s in S["selection"].values()): return False, "D1 selection incomplete"
    if not z.get("wrong_pass_ok"): return False, f"D1 wrong-pick-accepted rate {z.get('max_wrong_pick_accepted_rate')} > {X['criteria']['wrong_pass_max_dev']}"
    if z.get("projected_T1_gpu_h", 1e9) > X["caps_h"]["T1"]: return False, f"projected T1 {z.get('projected_T1_gpu_h'):.2f} h > T1 cap {X['caps_h']['T1']}"
    return True, "ok"

def start(cfg, name):
    X = cfg["e1c"]
    if name not in X["caps_h"]: print(f"unknown E1c stage {name}"); sys.exit(2)
    if os.environ.get("E1C_GO") != name: print(f"{name} refused: no explicit go (E1C_GO must equal '{name}')"); sys.exit(14)
    if name == "T1":
        if X["status"] != "frozen": print("T1 refused: E1c is not frozen"); sys.exit(13)
        ok, why = t1_eligibility(X)
        if not ok: print(f"T1 refused: {why}"); sys.exit(19)
    p = HERE / "CODE_HASH.txt"; pin = p.read_text().strip() if p.exists() else None
    if pin != code_hash(): print(f"{name} refused: code hash != CODE_HASH.txt"); sys.exit(16)
    kind = "dev" if name == "D1" else "test"; B = load_book(cfg, kind)
    d = RES / name
    if (d / ".done").exists(): print(f"{name} already finished"); sys.exit(0)
    term = [m for m in TERMINAL if (d / m).exists()]
    if term: print(f"{name}: terminal marker {term} -> stop and report"); sys.exit(18)
    d.mkdir(parents=True, exist_ok=True); stp = d / "e1c_state.json"
    st = json.load(open(stp)) if stp.exists() else dict(attempts=[], retry=None, cap_h=X["caps_h"][name])
    A = st["attempts"]; R = st.get("retry")
    if len(A) == 0: kind_a = "first"
    elif len(A) == 1 and R and R.get("for_attempt") == 1 and R.get("reason") in X["infra_retry_reasons"]:
        kind_a = "infra_retry"
        if (d / "GPU_PREFLIGHT_FAIL").exists(): (d / "GPU_PREFLIGHT_FAIL").rename(d / "GPU_PREFLIGHT_FAIL.attempt1")
        L = RES / "budget_ledger.json"; led = json.load(open(L)) if L.exists() else {}
        led[f"E1C_{name}"] = max(led.get(f"E1C_{name}", 0.0), float(R["charged_h"]) * 3600)   # cumulative across attempts
        json.dump(led, open(L, "w"))
    else:
        (d / "ATTEMPT_INCOMPLETE").write_text(f"{name}: no further start allowed (attempts={len(A)}, retry={R}); INCOMPLETE\n"); sys.exit(17)
    A.append(dict(n=len(A) + 1, kind=kind_a, t=time.time(), code_hash=code_hash(), outcome="running"))
    json.dump(st, open(stp, "w"), indent=1)
    c = dict(cfg); c["stageB_batch_size"] = X["batch_size"]; ES._A9.clear()
    S = _stage(name, st["cap_h"], c); S.state_path = stp
    _require_gpu(S)
    S.log("e1c", stage=name, status=X["status"], attempt=A[-1], cap_h=st["cap_h"], book=kind,
          book_sha256=X[f"{kind}_book_sha256"], code_hash=code_hash(), protocol_hash=protocol_hash(X))
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

def load(m, cfg, B, S, est):
    guard(S, est("load"), f"load {m}"); t = time.time(); b, _ = load_B(m, cfg, S); require_canaries(b, m, cfg, B, S)
    est.seen("load", time.time() - t); return b, time.time() - t

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
    """D1 only: production batch-8 path vs the batch-1 reference on a fixed subset (16 entries). Pre-declared rule:
    any difference for either model -> the T1 verifier runs at batch 1."""
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

def t1_verifier_batch(X):
    if X["_kind"] != "test": return X["batch_size"]
    vb = json.load(open(RES / "D1" / "summary.json"))["verifier_b1_check"]
    return X["batch_size"] if all(v["identical"] == v["n"] for v in vb.values()) else 1

def run(cfg, name):
    X, B, S, cfg = start(cfg, name); X = dict(X, _kind="dev" if name == "D1" else "test")
    try: _run(cfg, name, X, B, S)
    except SystemExit as e: _mark(S, f"exit {e.code}"); raise
    except Exception as e: _mark(S, f"crash {type(e).__name__}"); raise

def _run(cfg, name, X, B, S):
    kind = X["_kind"]; n = X["sizes"][kind]["core_per_family"]; nr = X["sizes"][kind]["receiver_entries_per_family"]
    ids = core_ids(B, n); rids = core_ids(B, nr); q, f = X["pair"]; sel, t, vb = {}, {}, {}; est = Est(X); vbatch = t1_verifier_batch(X)
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
    S.finish(summarize(name, X, B, sel, ex, t, vb, S.used_s() / 3600, rids, cases, vbatch)); _mark(S, "done")

def selection_stats(sel, ids):
    v = [sel[e] for e in ids if e in sel]; N = len(ids); wp = sum(r["accepted"] and not r["correct"] for r in v)
    return dict(n=N, complete=len(v) == N, pick_acc=sum(r["correct"] for r in v) / N, sender_invalid=sum(r["pick"] is None for r in v),
                verifier_format_ok=sum(r["verifier_parse"] == "ok" for r in v) / N, coverage=sum(r["accepted"] for r in v) / N,
                wrong_pick_accepted=wp, wrong_pick_accepted_rate=wp / N, wrong_pick_accepted_cp95_upper=cp_upper(wp, N),
                correct_pick_rejected=sum(r["correct"] and not r["accepted"] for r in v),
                wrong_pick_caught=sum((r["pick"] is not None) and not r["correct"] and not r["accepted"] for r in v),
                parse_paths={p: sum(r["parse_path"] == p for r in v) for p in sorted({r["parse_path"] for r in v})})

def summarize(name, X, B, sel, ex, t, vb, gpu_h, rids, cases, vbatch):
    n = X["sizes"][X["_kind"]]["core_per_family"]; ids = core_ids(B, n)
    out = dict(stage=name, status=X["status"], gpu_h=gpu_h, timing_s=t, verifier_b1_check=vb, verifier_batch_size=vbatch,
               protocol_hash=protocol_hash(X), selection={m: selection_stats(s, ids) for m, s in sel.items()}, directions={})
    for d, rows in ex.items():
        out["directions"][d] = direction_result(rows, sel[d.split("_to_")[0]], B, X["criteria"],
                                                seed_of(X["seeds"][X["_kind"]]["bootstrap"], d), rids, cases)
    if name == "D1":
        out["note"] = "DEV pilot: descriptive only; no E1c verdict. Feeds the TEST eligibility and sizing rules (PREREG_E1c §8)."
        out["sizing"] = sizing(out, X, t, vb)
    else: out["verdict"] = verdict(out)
    return out

def verdict(out):
    if any(v["status"] != "COMPLETE" for v in out["directions"].values()) or not all(s["complete"] for s in out["selection"].values()):
        return "INCOMPLETE"
    return "SUCCESS" if all(v["success"] for v in out["directions"].values()) else "NOT MET"

def sizing(out, X, t, vb):
    """Pre-declared TEST eligibility + sizing from dev (PREREG_E1c §8). rv = receiver seconds per case (both arms)."""
    nT = X["sizes"]["test"]["core_per_family"] * 2; nD = out["selection"][X["pair"][0]]["n"]; K = X["cases_per_entry"]
    b1 = all(v["identical"] == v["n"] for v in vb.values())
    sv = sum(v for k, v in t.items() if k.startswith("send_verify")) / nD
    if not b1: sv += sum(v["batch1_s_per_call"] or 0 for v in vb.values())   # T1 verifier at batch 1
    nm = sum(d.get("n_messages", 0) for d in out["directions"].values())
    rv = sum(v for k, v in t.items() if k.startswith("recv")) / max(1, nm)
    loads = sum(t.get(k, 0) for k in ("load1", "load2", "load3"))
    proj_h = (loads + sv * nT + rv * nT * K * 2) / 3600 * 1.25     # 2 directions x nT entries x K cases; 25% margin
    S = out["selection"]; wp = max(s["wrong_pick_accepted_rate"] for s in S.values())
    ok_wp = wp <= X["criteria"]["wrong_pass_max_dev"]
    return dict(test_entries_per_direction=nT if (ok_wp and proj_h <= X["caps_h"]["T1"]) else None,
                projected_T1_gpu_h=proj_h, max_wrong_pick_accepted_rate=wp, wrong_pass_ok=ok_wp,
                wrong_pick_accepted_cp95_upper={m: s["wrong_pick_accepted_cp95_upper"] for m, s in S.items()},
                demonstrated_le_2pct={m: s["wrong_pick_accepted_cp95_upper"] <= 0.02 for m, s in S.items()},
                t1_verifier_batch=X["batch_size"] if b1 else 1,
                projection_depends_on="dev coverage (fallback reuse), dev prompt-length mix, dev timing",
                rule="screen: observed wrong-pick-accepted <= 2% for both senders AND projection <= T1 cap. The screen does not show the rate is <= 2%; that needs the CP95 upper bound <= 2% (0 of 160).")
