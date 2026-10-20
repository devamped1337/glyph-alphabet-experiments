"""E1d dev eligibility for freeze, D1-D8 + the deterministic outcome rule (DRAFT_PLAN §8). Checked in code."""
import json, math
from . import HERE
from .book import pair_of

def d7_d8(X, B, sel_rows, ex):
    """Per adopted pair: D7 (a,b per sender over its 4 entries; c = prose receiver parses in that sender's direction,
    16 case-level) and D8 (per direction, 16 messages per arm). Pooled D8c/D8d over all k pairs."""
    R = X["dev_rules"]; q, f = X["pair"]; E = B["entries"]; new = B["e1d_ids"]["dev_new"]; pairs = [f"{a}/{b}" for a, b in X["roles_adopted"]]
    k = len(pairs); res = {}; pooled = {}
    for p in pairs:
        ids = [e for e in new if pair_of(E[e]) == p]; r = dict(n_entries=len(ids), D7={}, D8={})
        for m in (q, f):
            o = f if m == q else q; d = f"{m}_to_{o}"; sel = {x["entry"]: x for x in sel_rows[m] if x["entry"] in set(ids)}
            rows = [x for x in ex.get(d, []) if x["entry"] in set(ids)]; pr = [x for x in rows if x["cond"] == "prose"]; hy = [x for x in rows if x["cond"] == "hybrid"]
            a = sum(sel[e]["verifier_parse"] == "ok" for e in ids if e in sel); b = sum(sel[e]["pick"] is not None for e in ids if e in sel)
            c = sum(x["pred"] is not None for x in pr)
            r["D7"][m] = dict(D7a=a, D7b=b, D7c=c, n_sel=len(sel), n_prose=len(pr),
                              ok=len(sel) == 4 and len(pr) == 16 and a >= R["D7a_min"] and b >= R["D7b_min"] and c >= R["D7c_min"])
            pc, hc = sum(bool(x["correct"]) for x in pr), sum(bool(x["correct"]) for x in hy)
            r["D8"][d] = dict(prose_correct=pc, hybrid_correct=hc, n=len(pr), ok=len(pr) == len(hy) == 16 and pc >= R["D8a_min"] and hc - pc >= R["D8b_min"])
        r["D7_pass"] = all(v["ok"] for v in r["D7"].values()); r["D8_pass"] = all(v["ok"] for v in r["D8"].values())
        r["pass"] = r["D7_pass"] and r["D8_pass"]; res[p] = r
    for d in (f"{q}_to_{f}", f"{f}_to_{q}"):
        rows = [x for x in ex.get(d, []) if x["entry"] in set(new)]; pr = [x for x in rows if x["cond"] == "prose"]; hy = [x for x in rows if x["cond"] == "hybrid"]
        pc, hc = sum(bool(x["correct"]) for x in pr), sum(bool(x["correct"]) for x in hy)
        pooled[d] = dict(prose_correct=pc, hybrid_correct=hc, n=len(pr),
                         ok=len(pr) == len(hy) == 16 * k and pc >= R["D8c_per_k"] * k and hc - pc >= -math.floor(R["D8d_per_k"] * k))
    return res, pooled

def outcome_rule(X, pair_res, pooled):
    k = len(X["roles_adopted"]); failed = [p for p, r in pair_res.items() if not r["pass"]]; f = len(failed)
    used = {tuple(p) for p in X["roles_adopted"]}; u = len([p for p in X["roles_step_up"] if tuple(p) not in used])
    pooled_ok = all(v["ok"] for v in pooled.values())
    if f == 0 and pooled_ok: return dict(rule=1, outcome="qualified", failed=[])
    if f == 0: return dict(rule=2, outcome="stop: pooled D8 failed; back to Stefan", failed=[])
    if f < k and f <= u:
        nxt = [p for p in X["roles_step_up"] if tuple(p) not in used][:f]
        return dict(rule=3, outcome="replace failed pairs (builder trials rerun; replacement dev-new stage needs Stefan's go)", failed=failed, replacements=nxt)
    return dict(rule=4, outcome="stop: every pair failed or too few step-up pairs; back to Stefan", failed=failed)

def builder_feasibility(X):
    p = HERE / "measurements" / "builder_trials.json"; T = json.load(open(p))
    trials = T["trials"] if isinstance(T, dict) and "trials" in T else T
    ok = sum(1 for t in trials if t.get("built") is True)
    roles = T.get("new_roles") if isinstance(T, dict) else None
    return dict(builds=ok, of=len(trials), roles_match=(roles is None or [list(r) for r in roles] == [list(r) for r in X["roles_adopted"]]),
                ok=ok >= X["dev_rules"]["D6_min_builds"])

def evaluate(S, X, cfg, B, sel_rows, ex, done_ok):
    """S = the dev summary. done_ok: D1 from the supervisor state (None while the child runs)."""
    from .stages import protocol_hash
    q, f = X["pair"]; I = B["e1d_ids"]; n_sel = len(I["e1c_dev_sel"]) + len(I["dev_new"]); k = len(X["roles_adopted"])
    D = {}
    D["D1"] = dict(ok=done_ok, note="from .done + recorded 'done', no terminal marker")
    st_ok = set(S["selection"]) == {q, f} and set(S["directions"]) == {f"{q}_to_{f}", f"{f}_to_{q}"}
    for m, s in S["selection"].items():
        st_ok &= s["all"]["complete"] and s["e1c_dev"]["n"] == 2 * X["sizes"]["e1c_dev"]["core_per_family"] and s["dev_new"]["n"] == 4 * k and s["all"]["n"] == n_sel
    for d, v in S["directions"].items():
        st_ok &= v["e1c_dev"]["status"] == "COMPLETE" and v["e1c_dev"]["n_entries"] == 2 * X["sizes"]["e1c_dev"]["receiver_entries_per_family"]
        st_ok &= v["dev_new"]["status"] == "COMPLETE" and v["dev_new"]["n_entries"] == 4 * k and v["dev_new"]["n_messages"] == 16 * k
    D["D2"] = dict(ok=bool(st_ok))
    vb = S.get("verifier_b1_check", {})
    D["D3"] = dict(ok=set(vb) == {q, f} and all(v["n"] == X["verifier_b1_check_n"] and v["identical"] == v["n"] for v in vb.values()), detail=vb)
    D["D4"] = dict(ok=S.get("protocol_hash") == protocol_hash(X, cfg))
    ph = S["sizing"]["projected_T1_gpu_h"]
    D["D5"] = dict(ok=isinstance(ph, (int, float)) and math.isfinite(ph) and ph <= X["caps_h"]["T1-E1d"], projected_T1_gpu_h=ph, cap=X["caps_h"]["T1-E1d"])
    D["D6"] = builder_feasibility(X); D["D6"]["ok"] = D["D6"]["ok"] and D["D6"]["roles_match"]
    pr, po = d7_d8(X, B, sel_rows, ex)
    D["D7"] = dict(ok=all(r["D7_pass"] for r in pr.values()), per_pair={p: r["D7"] for p, r in pr.items()})
    D["D8"] = dict(ok=all(r["D8_pass"] for r in pr.values()) and all(v["ok"] for v in po.values()), per_pair={p: r["D8"] for p, r in pr.items()}, pooled=po)
    D["wrong_pick_screen_reported_only"] = {m: s["all"]["wrong_pick_accepted_rate"] for m, s in S["selection"].items()}
    D["outcome_rule"] = outcome_rule(X, pr, po)
    D["eligible_for_freeze"] = bool(done_ok) and all(D[c]["ok"] for c in ("D2", "D3", "D4", "D5", "D6", "D7", "D8")) and D["outcome_rule"]["rule"] == 1
    return D
