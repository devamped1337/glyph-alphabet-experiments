"""E1d gates and verdict (DRAFT_PLAN §9), per-pair (§10), compressed (§11) and speed (§12) reporting.
Gates per direction: C completeness, G1 accuracy (E1c bootstrap, s[50] of 2,000 > -0.05), G2 coverage >= 85%,
G3 S_d(W_base) lower bound s[500] of 10,000 > 0.20. NO 1,000-message break-even; wrong IDs reported only."""
from statistics import mean
from e1c.analysis import direction_result as e1c_direction_result, cp_upper
from e1b.stages import seed_of
from . import lifetime as LT
from .book import pair_of

SCEN = ("W_base", "W_copy", "W_low", "W_churn", "W_low_churn")

def lifetime_block(rows, W, LCs, direction, crit, key="wire_bytes"):
    """Primary W_base + reported sensitivities, all with F fixed in every replicate."""
    by = LT.entry_bytes(rows, key); out = {}
    for s in SCEN:
        w = W[s]; F = LT.F_d(w, LCs[s]); pt, lo, _ = LT.lifetime_boot(by, F, w["M_d"], w["a"], LT.lifetime_seed(direction),
                                                                     crit["lifetime_resamples"], crit["lifetime_index"])
        out[s] = dict(F_d=F, M_d=w["M_d"], a=w["a"], S_point=pt, S_lower=lo, H=LT.fam_mean(by, 0), P=LT.fam_mean(by, 1))
    return out

def direction_result(rows, sel_rows, B, crit, seed, assigned, cases_by_entry, sender_ids, W, LCs, direction):
    r = e1c_direction_result(rows, sel_rows, B, crit, seed, assigned, cases_by_entry, sender_ids)
    if r["status"] != "COMPLETE": return dict(r, gates=None, success=False)
    sec = {k: r.pop(k) for k in ("payload_saving", "breakeven_messages", "dict_bytes", "checks", "success")}
    lt = lifetime_block(rows, W, LCs, direction, crit); ltz = lifetime_block(rows, W, LCs, direction, crit, key="wire_gzip9_bytes")
    g = dict(G1=r["ci"][0] > -crit["margin"], G2=r["coverage"] >= crit["coverage_min"], G3=lt["W_base"]["S_lower"] > crit["lifetime_saving_min"])
    return dict(r, gates=g, success=all(g.values()), lifetime=lt, lifetime_gzip9_secondary=ltz, e1c_secondary_reported_only=sec)

def verdict(out, X, kind="test"):
    """Exact structure (both directions, both senders, registered sizes); SUCCESS only if every gate passes in BOTH."""
    q, f = X["pair"]; n = X["sizes"][kind]; K = X["cases_per_entry"]; D, Sl = out.get("directions", {}), out.get("selection", {})
    if set(D) != {f"{q}_to_{f}", f"{f}_to_{q}"} or set(Sl) != {q, f}: return "INCOMPLETE"
    for v in D.values():
        if v.get("status") != "COMPLETE" or v.get("n_entries") != 2 * n["receiver_entries_per_family"] \
           or v.get("n_messages") != 2 * n["receiver_entries_per_family"] * K: return "INCOMPLETE"
    if any(not s.get("complete") or s.get("n") != 2 * n["core_per_family"] for s in Sl.values()): return "INCOMPLETE"
    return "SUCCESS" if all(v.get("success") is True for v in D.values()) else "NOT MET"

def group_report(rows, sel, B, eids):
    """Per-group (pair / family) descriptive block with denominators; 'n/a' if empty."""
    eids = [e for e in eids]
    if not eids: return "n/a"
    s = set(eids); R = [r for r in rows if r["entry"] in s]; hy = [r for r in R if r["cond"] == "hybrid"]; pr = [r for r in R if r["cond"] == "prose"]
    wp = sum(1 for e in eids if sel[e]["accepted"] and not sel[e]["correct"])
    return dict(entries=len(eids), picks=len(eids), messages_per_arm=len(hy), coverage=sum(bool(sel[e]["accepted"]) for e in eids) / len(eids),
                acc_hybrid=mean(bool(r["correct"]) for r in hy) if hy else None, acc_prose=mean(bool(r["correct"]) for r in pr) if pr else None,
                correct_hybrid=sum(bool(r["correct"]) for r in hy), correct_prose=sum(bool(r["correct"]) for r in pr),
                wrong_accepted=wp, wrong_accepted_cp95_upper=cp_upper(wp, len(eids)),
                bytes_hybrid=mean(r["wire_bytes"] for r in hy) if hy else None, bytes_prose=mean(r["wire_bytes"] for r in pr) if pr else None)

def per_pair(rows, sel, B, eids, pairs):
    E = B["entries"]; out = {}
    for p in pairs: k = f"{p[0]}/{p[1]}"; out[k] = group_report(rows, sel, B, [e for e in eids if pair_of(E[e]) == k])
    out["F2_new_pooled"] = group_report(rows, sel, B, [e for e in eids if pair_of(E[e]) in {f"{a}/{b}" for a, b in pairs}])
    out["F1"] = group_report(rows, sel, B, [e for e in eids if E[e]["fam"] == "F1"])
    out["F2_old_pairs"] = group_report(rows, sel, B, [e for e in eids if E[e]["fam"] == "F2" and pair_of(E[e]) not in {f"{a}/{b}" for a, b in pairs}])
    out["note"] = "reported, not gated; small denominators (imprecise)"; return out

def speed(rows, sel_rows):
    """§12: descriptive, batch-level latencies on a shared T4."""
    o = {}
    for arm in ("prose", "hybrid"):
        R = [r for r in rows if r["cond"] == arm]
        if not R: continue
        o[arm] = dict(wire_bytes=mean(r["wire_bytes"] for r in R), **{k: mean(float(r.get(k) or 0) for r in R) for k in ("prompt_tokens", "gen_tokens", "latency_s")})
    o["sender"] = {k: mean(float(r.get(k) or 0) for r in sel_rows) for k in ("sender_latency_s", "sender_gen_tokens", "verifier_latency_s")} if sel_rows else None
    return o
