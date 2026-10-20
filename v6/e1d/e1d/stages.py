"""E1d stages. D1-E1d = the only dev stage (DRAFT_PLAN §8; arm A0; E1c dev book + dev-new). Model calls reuse the
E1c stage code (load/canaries, sender + stateless verifier, batch-1 conformance) unchanged; the receiver's
dictionary is loaded ONLY from the E1D-DICT/1 artifact (§4.2) and every message is serialized by the frozen
serializer (§4.1). Needs E1D_GO == <stage> (Stefan's explicit go)."""
import os, sys, json, time, hashlib, inspect, math
from . import RES, HERE
from .book import load_dev, shown_of
from . import analysis as AN, lifetime as LT, eligibility as EL
from e1c import stages as C1
from e1c.stages import guard, Est, free, send_and_verify, verifier_b1_check, selection_stats, unit_costs, all_loads, TERMINAL
from e1b import stages as ES
from e1b.stages import seed_of, rec, ask_arith_many, chunks
from e1b.protocol import framed_id, bytes_record, Dictionary, render_message
import measure_dict_artifact as MA

def finished(d):
    """E1c rule on the E1d state file: .done AND the last attempt recorded 'done' AND none still 'running'."""
    p = d / "e1d_state.json"
    if not (d / ".done").exists() or not p.exists(): return False
    A = json.load(open(p)).get("attempts", [])
    return bool(A) and A[-1].get("outcome") == "done" and not any(a.get("outcome") == "running" for a in A)

def is_dev(X, name): return name in X["dev_stages"]

def code_hash():
    import code_hash as H; return H.compute()

def protocol_hash(X, cfg):
    """E1c protocol hash (sender/verifier/receiver prompts, parsers, grammar, limits, batches) + the E1d role list,
    arm, serializer and artifact loader. Equal at dev and TEST (D4)."""
    parts = [C1.protocol_hash(dict(X), cfg), json.dumps(X["roles_adopted"]), X["arm"], inspect.getsource(MA.serialize),
             inspect.getsource(MA.load), inspect.getsource(MA.build), f"cases_per_entry={X['cases_per_entry']}"]
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()

class ChildStage(C1.ChildStage):
    def log(self, ev, **kw):
        if ev == "start" and isinstance(kw.get("env"), dict) and "code_hash" in kw["env"]:
            env = dict(kw["env"]); env["e1b_code_hash"] = env.pop("code_hash"); env["e1d_code_hash"] = code_hash(); kw["env"] = env
        ES.Stage.log(self, ev, **kw)

def _stage(name, cap, cfg, deadline):
    old = ES.RES; ES.RES = RES
    try: S = ChildStage(name, cap, cfg, alloc=f"E1D_{name}")
    finally: ES.RES = old
    S.deadline = deadline; return S

def artifact_members(B, sel_ids): return sorted(set(shown_of(B, sel_ids)))

def write_artifact(S, B, sel_ids):
    """The v1 repository artifact the receiver loads (A0: cores + 3 neighbours)."""
    raw, hb, bb = MA.build(B["entries"], artifact_members(B, sel_ids)); (S.dir / "dict_v1.e1d").write_bytes(raw)
    return dict(artifact_bytes=len(raw), manifest_bytes=hb, body_bytes=bb, n_entries=len(artifact_members(B, sel_ids)),
                n_core=len(sel_ids), gzip9_bytes=LT.gz9(raw), sha256=hashlib.sha256(raw).hexdigest())

def receiver_dictionary(S):
    return Dictionary(MA.load((S.dir / "dict_v1.e1d").read_bytes()))

def wire(case_text, kind, payload):
    b = MA.serialize(case_text, kind, payload); return dict(wire_bytes=len(b), wire_gzip9_bytes=LT.gz9(b))

def exchange(b, snd, rcv, B, ids, sel, cfg, S, est, RD):
    """As E1c exchange, but the ID arm's rule text comes from the receiver's artifact Dictionary RD; every row
    carries the frozen-serializer wire bytes (and gzip-9, secondary)."""
    E = B["entries"]; fx = f"exchange_{snd}_to_{rcv}.jsonl"; by = {}
    from e1c.book import cases_for
    for c in cases_for(B, ids): by.setdefault(c["entry"], []).append(c)
    for ech in chunks(ids, 8):
        jobs = []
        for eid in ech:
            e = E[eid]; s = sel[eid]
            for c in by[eid]:
                for cond in ("prose", "hybrid"):
                    k = f"{eid}|{c['text']}|{cond}"
                    if k in S.done_keys(fx): continue
                    if cond == "prose" or not s["accepted"]: jobs.append((k, cond, ("prose", e, c, None), "prose", render_message(e)))
                    else:
                        ent, why = RD.resolve(framed_id(E[s["pick"]])); assert why == "ok", f"artifact resolve {why} for {s['pick']}"
                        jobs.append((k, cond, ("id_selected", dict(ent, fam=E[s["pick"]]["fam"]), c, None), "id", framed_id(ent)))
        if not jobs: continue
        guard(S, est("receiver_chunk"), "receiver chunk"); t = time.time()
        res = ask_arith_many(b, rcv, [j[2] for j in jobs], cfg); est.seen("receiver_chunk", time.time() - t)
        for (k, cond, (_, ent, c, _x), sent, payload), r in zip(jobs, res):
            eid = k.split("|")[0]
            assert r["gold"] == c["gold"] and r["case"] == c["text"] and c["entry"] == eid
            r.update(cond=cond, entry=eid, fam=E[eid]["fam"], sent=sent, rule_entry=ent["id"], selected=sel[eid]["pick"],
                     accepted=sel[eid]["accepted"], selection_correct=sel[eid]["correct"], sender=snd, receiver=rcv,
                     **bytes_record(cond, payload, c), **wire(c["text"], "i" if sent == "id" else "p", payload))
            S.write(fx, rec(rcv, S.name, "exchange", k, **r))
    return [json.loads(l) for l in open(S.dir / fx)]

def child_main(cfg, name):
    X = cfg["e1d"]; d = RES / name; st = json.load(open(d / "e1d_state.json")); a = st["attempts"][-1]
    if not os.environ.get("E1D_ATTEMPT_TOKEN") or os.environ["E1D_ATTEMPT_TOKEN"] != a.get("token") or a.get("outcome") != "running":
        print("child refused: not launched by the supervisor for the running attempt"); sys.exit(15)
    if not is_dev(X, name): print("only the dev stage is implemented in this execution commit"); sys.exit(13)
    c = dict(cfg); c["stageB_batch_size"] = X["batch_size"]; ES._A9.clear(); B = load_dev(cfg)
    S = _stage(name, st["cap_h"], c, a["deadline_mono"]); S.attempt = a["n"]
    if os.environ.get("E1B_ALLOW_NO_GPU") == "1" and os.environ.get("E1D_TEST_HOOK"):   # test-only fake backend
        import importlib.util as U; sp = U.spec_from_file_location("e1d_test_hook", os.environ["E1D_TEST_HOOK"])
        h = U.module_from_spec(sp); sp.loader.exec_module(h); h.install(C1, B, a)
    ES._require_gpu(S)
    S.log("e1d", stage=name, attempt=a, cap_h=st["cap_h"], code_hash=code_hash(), protocol_hash=protocol_hash(X, cfg))
    out = _run(c, name, dict(X, _kind="dev"), B, S)
    json.dump(out, open(S.dir / "summary.child.json", "w"), indent=1)
    (S.dir / "CHILD_COMPLETE").write_text(f"attempt {S.attempt}\n"); S.log("child_complete")

def _run(cfg, name, X, B, S):
    I = B["e1d_ids"]; sel_ids = I["e1c_dev_sel"] + I["dev_new"]; rids = I["e1c_dev_recv"] + I["dev_new"]
    q, f = X["pair"]; sel, t, vb = {}, {}, {}; est = Est(X); vbatch = X["batch_size"]
    art = write_artifact(S, B, sel_ids); RD = receiver_dictionary(S)
    b, t["load1"] = C1.load(q, cfg, B, S, est)
    t0 = time.time(); sel[q] = send_and_verify(b, q, B, sel_ids, cfg, X, S, est, vbatch); t[f"send_verify_{q}"] = time.time() - t0
    vb[q] = verifier_b1_check(b, q, B, I["e1c_dev_sel"], cfg, X, S, est); del b; free()
    b, t["load2"] = C1.load(f, cfg, B, S, est)
    t0 = time.time(); sel[f] = send_and_verify(b, f, B, sel_ids, cfg, X, S, est, vbatch); t[f"send_verify_{f}"] = time.time() - t0
    vb[f] = verifier_b1_check(b, f, B, I["e1c_dev_sel"], cfg, X, S, est)
    t0 = time.time(); ex = {f"{q}_to_{f}": exchange(b, q, f, B, rids, sel[q], cfg, S, est, RD)}; t[f"recv_{f}"] = time.time() - t0
    del b; free()
    b, t["load3"] = C1.load(q, cfg, B, S, est)
    t0 = time.time(); ex[f"{f}_to_{q}"] = exchange(b, f, q, B, rids, sel[f], cfg, S, est, RD); t[f"recv_{q}"] = time.time() - t0
    del b; free()
    sel_rows = {m: [json.loads(l) for l in open(S.dir / f"select_{m}.jsonl")] for m in (q, f)}
    return summarize(name, X, cfg, B, sel_rows, ex, t, vb, art, all_loads(S.dir))

def lifecycles(W, art, per_family):
    return {s: LT.Lifecycle(art["body_bytes"], art["n_entries"], art["n_core"], per_family, W["families"], W[s]["r"]) for s in AN.SCEN}

def summarize(name, X, cfg, B, sel_rows, ex, t, vb, art, loads=()):
    from e1c.book import cases_for
    I = B["e1d_ids"]; sel_ids = I["e1c_dev_sel"] + I["dev_new"]; W = X["W"]; crit = X["criteria"]
    LCs = lifecycles(W, art, W["n_core_v1_per_family"])
    out = dict(stage=name, gpu_h=None, timing_s=t, verifier_b1_check=vb, verifier_batch_size=X["batch_size"], protocol_hash=protocol_hash(X, cfg),
               code_hash=code_hash(), artifact_v1_dev=art, ids=I, selection={}, directions={},
               note="DEV (D1-E1d): descriptive + eligibility only; no E1d verdict. Lifetime numbers use the DEV artifact and are illustrative.")
    for m, rows in sel_rows.items():
        out["selection"][m] = dict(e1c_dev=selection_stats([r for r in rows if r["entry"] in set(I["e1c_dev_sel"])], I["e1c_dev_sel"]),
                                   dev_new=selection_stats([r for r in rows if r["entry"] in set(I["dev_new"])], I["dev_new"]),
                                   all=selection_stats(rows, sel_ids))
    for d, rows in ex.items():
        m = d.split("_to_")[0]; sr = sel_rows[m]; sel = {r["entry"]: r for r in sr}; o = {}
        for part, rid in (("e1c_dev", I["e1c_dev_recv"]), ("dev_new", I["dev_new"])):
            s = set(rid); R = [r for r in rows if r["entry"] in s]; cs = {}
            for c in cases_for(B, rid): cs.setdefault(c["entry"], []).append(c)
            o[part] = AN.direction_result(R, sr, B, crit, seed_of(X["seeds"]["dev"]["bootstrap"], d, part), rid, cs, sel_ids, W, LCs, d)
        o["per_pair"] = AN.per_pair(rows, sel, B, I["dev_new"] + I["e1c_dev_recv"], [tuple(p) for p in X["roles_adopted"]])
        o["speed"] = AN.speed(rows, sr); out["directions"][d] = o
    sv, rv = unit_costs(sel_rows, ex); load = max(list(loads) + [t.get(k, 0) for k in ("load1", "load2", "load3")] + [0])
    nT = 2 * X["sizes"]["test"]["core_per_family"]; K = X["cases_per_entry"]
    out["sizing"] = dict(sender_verifier_s_per_entry=sv, receiver_s_per_message=rv, load_s=load,
                         projected_T1_gpu_h=(3 * load + sv * nT + rv * nT * K * 2) / 3600 * X["dev_rules"]["D5_margin"],
                         formula="(3 x max load + sv x 160 + rv x 160 x 4 x 2) / 3600 x 1.25")
    out["eligibility_D2_D8"] = EL.evaluate(out, X, cfg, B, sel_rows, ex, done_ok=None)
    return out
