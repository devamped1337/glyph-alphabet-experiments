"""E1c stages (PREREG_E1c §7). D1 = dev pilot (allowed while DRAFT; dev book only, never TEST). T1 = TEST (needs
e1c.status == frozen and the pinned TEST book). Both need E1C_GO == <stage> (set only on Stefan's explicit go), at
most one start plus one infrastructure retry, and room in the stage cap. Model calls reuse the frozen E1b paths."""
import os, sys, json, time, random
from statistics import mean
from . import RES, HERE, E1B
from .book import load_book, core_ids, cases_for
from .verifier import verifier_parts, parse_spec, matches
from .analysis import direction_result
from e1b import stages as ES
from e1b.stages import (seed_of, rec, load_B, canaries, canary_regressions, _require_gpu, ask_arith_many,
                        batched_generate, log_prompt, chunks)
from e1b.protocol import sender_view, sender_parts, framed_id, bytes_record, Dictionary, render_message
from e1b.parsing import parse_letter_a10

TERMINAL = ("BUDGET_EXHAUSTED", "CANARY_FAIL", "GPU_PREFLIGHT_FAIL", "ATTEMPT_INCOMPLETE")

def code_hash():
    sys.path.insert(0, str(HERE / "tools")); import code_hash as H; return H.compute()

def _stage(name, cap, cfg):
    """E1b Stage with its directory and budget ledger under v6/e1c/results (E1b's RES restored afterwards)."""
    old = ES.RES; ES.RES = RES
    try: S = ES.Stage(name, cap, cfg, alloc=f"E1C_{name}")
    finally: ES.RES = old
    return S

def start(cfg, name):
    X = cfg["e1c"]
    if name not in X["caps_h"]: print(f"unknown E1c stage {name}"); sys.exit(2)
    if os.environ.get("E1C_GO") != name: print(f"{name} refused: no explicit go (E1C_GO must equal '{name}')"); sys.exit(14)
    if name == "T1":
        if X["status"] != "frozen": print("T1 refused: E1c is not frozen"); sys.exit(13)
        if not (RES / "D1" / ".done").exists(): print("T1 refused: dev pilot D1 not finished"); sys.exit(19)
    p = HERE / "CODE_HASH.txt"; pin = p.read_text().strip() if p.exists() else None
    if pin != code_hash(): print(f"{name} refused: code hash != CODE_HASH.txt"); sys.exit(16)
    kind = "dev" if name == "D1" else "test"; B = load_book(cfg, kind)
    d = RES / name
    if (d / ".done").exists(): print(f"{name} already finished"); sys.exit(0)
    term = [m for m in TERMINAL if (d / m).exists()]
    if term: print(f"{name}: terminal marker {term} -> stop and report"); sys.exit(18)
    d.mkdir(parents=True, exist_ok=True); stp = d / "e1c_state.json"
    st = json.load(open(stp)) if stp.exists() else dict(starts=0, cap_h=X["caps_h"][name])
    if st["starts"] >= X["max_starts"]:
        (d / "ATTEMPT_INCOMPLETE").write_text(f"{name}: start + one infra retry used; INCOMPLETE\n"); sys.exit(17)
    st["starts"] += 1; json.dump(st, open(stp, "w"), indent=1)
    c = dict(cfg); c["stageB_batch_size"] = X["batch_size"]; ES._A9.clear()
    S = _stage(name, st["cap_h"], c); _require_gpu(S)
    S.log("e1c", stage=name, status=X["status"], starts=st["starts"], cap_h=st["cap_h"], book=kind,
          book_sha256=X[f"{kind}_book_sha256"], code_hash=code_hash())
    return X, B, S, c

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

def send_and_verify(b, m, B, ids, cfg, X, S):
    """Sender (batch 1, frozen E1b sender prompt and 4-token limit, A10 parser), then the stateless verifier
    (batched) on the prose message alone. accepted = valid pick AND dictionary resolve ok AND spec == picked entry."""
    E = B["entries"]; D = Dictionary(B); fs = f"select_{m}.jsonl"; rows = {}
    for eid in ids:
        if eid in S.done_keys(fs): continue
        S.check_budget(); v = view_for(B, eid, X); s, p, u = sender_parts(v); t = time.time()
        r = b.generate(s, p, u, cfg["sender_max_new_tokens"]); log_prompt(r, m); L, path = parse_letter_a10(r["text"])
        pick = v["candidates"]["ABCD".index(L)] if L else None
        rows[eid] = dict(entry=eid, fam=E[eid]["fam"], sender_view=v, raw=r["text"], letter=L, parse_path=path, pick=pick,
                         correct=pick == eid, picked_ntype=(E[pick].get("ntype") if pick and pick != eid else None),
                         sender_latency_s=time.time() - t, sender_gen_tokens=r.get("gen_tokens"))
    keys = list(rows); jobs = [verifier_parts(E[e]["fam"], render_message(E[e])) for e in keys]; out = []
    for ch in chunks(jobs, 64):
        S.check_budget(); out += batched_generate(b, ch, X["verifier_max_new_tokens"], cfg)
    for eid, r in zip(keys, out):
        x = rows[eid]; log_prompt(r, m); spec, why = parse_spec(x["fam"], r["text"])
        ok, how = matches(spec, E[x["pick"]]) if x["pick"] else (False, "sender_invalid")
        ent, res = D.resolve(framed_id(E[x["pick"]])) if x["pick"] else (None, "sender_invalid")
        x.update(verifier_raw=r["text"], verifier_parse=why, spec=spec, verified=ok, verify_reason=how, resolve=res,
                 accepted=bool(ok and ent is not None), verifier_latency_s=r.get("latency_s"), verifier_batch_n=r.get("batch_n"))
        S.write(fs, rec(m, S.name, "select", eid, **x))
    return {json.loads(l)["entry"]: json.loads(l) for l in open(S.dir / fs)}

def verifier_b1_check(b, m, B, ids, X, S):
    """Dev only: batch-1 vs batched verifier replies on a fixed subset (conformance of the new prompt)."""
    E = B["entries"]; n = X["verifier_b1_check_n"]; sub = ids[:: max(1, len(ids) // n)][:n]
    jobs = [verifier_parts(E[e]["fam"], render_message(E[e])) for e in sub]
    bt = b.generate_batch(jobs, X["verifier_max_new_tokens"]); same = 0
    for i, j in enumerate(jobs): same += int(bt[i]["text"] == b.generate(*j, X["verifier_max_new_tokens"])["text"])
    S.log("verifier_b1_check", model=m, n=len(sub), identical=same); return dict(n=len(sub), identical=same)

def exchange(b, snd, rcv, B, ids, sel, cfg, S):
    """Receiver, per entry and case: prose arm = the true entry's prose; hybrid arm = the accepted ID (expanded by the
    delegate to the dictionary text) or, if not accepted, the SAME prose (identical prompt, generated once,
    shared_n = 2; the fallback's prose bytes are counted in the hybrid arm)."""
    E = B["entries"]; fx = f"exchange_{snd}_to_{rcv}.jsonl"; by = {}
    for c in cases_for(B, ids): by.setdefault(c["entry"], []).append(c)
    for ech in chunks(ids, 8):       # all jobs of an entry in one call, so fallback == prose is generated once
        S.check_budget(); jobs = []
        for eid in ech:
            e = E[eid]; s = sel[eid]
            for c in by[eid]:
                for cond in ("prose", "hybrid"):
                    k = f"{eid}|{c['text']}|{cond}"
                    if k in S.done_keys(fx): continue
                    if cond == "prose" or not s["accepted"]: jobs.append((k, cond, ("prose", e, c, None), "prose", render_message(e)))
                    else: jobs.append((k, cond, ("id_selected", E[s["pick"]], c, None), "id", framed_id(E[s["pick"]])))
        if not jobs: continue
        for (k, cond, (_, ent, c, _x), sent, payload), r in zip(jobs, ask_arith_many(b, rcv, [j[2] for j in jobs], cfg)):
            eid = k.split("|")[0]
            r.update(cond=cond, entry=eid, fam=E[eid]["fam"], sent=sent, selected=sel[eid]["pick"], accepted=sel[eid]["accepted"],
                     selection_correct=sel[eid]["correct"], sender=snd, receiver=rcv, **bytes_record(cond, payload, c))
            S.write(fx, rec(rcv, S.name, "exchange", k, **r))
    return [json.loads(l) for l in open(S.dir / fx)]

def run(cfg, name):
    X, B, S, cfg = start(cfg, name); X = dict(X, _kind="dev" if name == "D1" else "test")
    kind = X["_kind"]; n = X["sizes"][kind]["core_per_family"]; nr = X["sizes"][kind]["receiver_entries_per_family"]
    ids = core_ids(B, n); rids = core_ids(B, nr); q, f = X["pair"]; sel, t, vb = {}, {}, {}
    # load order: q (send+verify) -> f (send+verify; receive q->f) -> q (receive f->q)
    t0 = time.time(); b, _ = load_B(q, cfg, S); require_canaries(b, q, cfg, B, S); t["load1"] = time.time() - t0
    t0 = time.time(); sel[q] = send_and_verify(b, q, B, ids, cfg, X, S); t[f"send_verify_{q}"] = time.time() - t0
    if name == "D1": vb[q] = verifier_b1_check(b, q, B, ids, X, S)
    del b; free()
    t0 = time.time(); b, _ = load_B(f, cfg, S); require_canaries(b, f, cfg, B, S); t["load2"] = time.time() - t0
    t0 = time.time(); sel[f] = send_and_verify(b, f, B, ids, cfg, X, S); t[f"send_verify_{f}"] = time.time() - t0
    if name == "D1": vb[f] = verifier_b1_check(b, f, B, ids, X, S)
    t0 = time.time(); ex = {f"{q}_to_{f}": exchange(b, q, f, B, rids, sel[q], cfg, S)}; t[f"recv_{f}"] = time.time() - t0
    del b; free()
    t0 = time.time(); b, _ = load_B(q, cfg, S); require_canaries(b, q, cfg, B, S); t["load3"] = time.time() - t0
    t0 = time.time(); ex[f"{f}_to_{q}"] = exchange(b, f, q, B, rids, sel[f], cfg, S); t[f"recv_{q}"] = time.time() - t0
    del b; free(); S.save_ledger()
    S.finish(summarize(name, X, B, sel, ex, t, vb, S.used_s() / 3600))

def selection_stats(sel):
    v = list(sel.values()); N = len(v)
    return dict(n=N, pick_acc=mean(r["correct"] for r in v), sender_invalid=sum(r["pick"] is None for r in v),
                verifier_format_ok=mean(r["verifier_parse"] == "ok" for r in v), coverage=mean(r["accepted"] for r in v),
                wrong_pick_accepted=sum(r["accepted"] and not r["correct"] for r in v),
                wrong_pick_accepted_rate=sum(r["accepted"] and not r["correct"] for r in v) / N,
                correct_pick_rejected=sum(r["correct"] and not r["accepted"] for r in v),
                wrong_pick_caught=sum((r["pick"] is not None) and not r["correct"] and not r["accepted"] for r in v),
                parse_paths={p: sum(r["parse_path"] == p for r in v) for p in sorted({r["parse_path"] for r in v})})

def summarize(name, X, B, sel, ex, t, vb, gpu_h):
    out = dict(stage=name, status=X["status"], gpu_h=gpu_h, timing_s=t, verifier_b1_check=vb,
               selection={m: selection_stats(s) for m, s in sel.items()}, directions={})
    for d, rows in ex.items():
        out["directions"][d] = direction_result(rows, sel[d.split("_to_")[0]], B, X["criteria"], seed_of(X["seeds"][X["_kind"]]["bootstrap"], d))
    if name == "D1":
        out["note"] = "DEV pilot: descriptive only; no E1c verdict. Feeds the TEST sizing rule (PREREG_E1c §8)."
        out["sizing"] = sizing(out, X, t)
    else:
        out["verdict"] = "SUCCESS" if all(v["success"] for v in out["directions"].values()) else "NOT MET"
    return out

def sizing(out, X, t):
    """Pre-declared TEST sizing from dev (PREREG_E1c §8)."""
    nT = X["sizes"]["test"]["core_per_family"] * 2; nD = out["selection"][X["pair"][0]]["n"]; K = X["cases_per_entry"]
    sv = sum(v for k, v in t.items() if k.startswith("send_verify")) / nD
    rv = sum(v for k, v in t.items() if k.startswith("recv")) / max(1, sum(d["n_items"] for d in out["directions"].values()))
    loads = sum(t.get(k, 0) for k in ("load1", "load2", "load3"))
    proj_h = (loads + sv * nT + rv * nT * K * 2) / 3600 * 1.25   # rv per (hybrid, prose) item pair; 2 directions; 25% margin
    wp = max(s["wrong_pick_accepted_rate"] for s in out["selection"].values())
    ok = wp <= X["criteria"]["wrong_pass_max_dev"] and proj_h <= X["caps_h"]["T1"]
    return dict(test_entries_per_direction=nT if ok else None, projected_T1_gpu_h=proj_h, max_wrong_pick_accepted_rate=wp,
                go_to_test=ok, rule="240/direction if wrong-pick-accepted <= 2% for both senders and projection <= T1 cap; otherwise no TEST until an amendment")
