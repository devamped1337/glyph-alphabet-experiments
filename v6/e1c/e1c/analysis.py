"""E1c analysis (PREREG_E1c §5-§6). Paired per-entry differences (hybrid - prose), bootstrap stratified by family and
clustered by entry; label rule = E1b A1.2 (CI only, mutually exclusive).

Communication boundary (r2, GPT r1 #7): the channel is sender -> receiver. Candidate preparation and the verifier
run locally at the sender (the sender holds the dictionary), so they are local computation, not transmitted bytes.
A *message* is one receiver request = one case exchange. payload bytes = rule part of that message (framed ID or
prose); message bytes = payload + case text. The 30% criterion uses payload bytes; break-even is in messages
(case exchanges), the same unit."""
import math, random
from statistics import mean

class Incomplete(Exception): pass

def check_complete(rows, assigned, cases_by_entry, fams):
    """GPT r1 #1: the assigned set must be exactly present before any result: every assigned entry, exactly its
    registered cases (by text), each case in both arms exactly once, gold equal to the registered case gold, no
    extra entries/rows, family counts as assigned. Raises Incomplete(reason)."""
    seen = {}
    for r in rows:
        k = (r["entry"], r["case"], r["cond"])
        if r["cond"] not in ("hybrid", "prose"): raise Incomplete(f"unknown arm {r['cond']}")
        if k in seen: raise Incomplete(f"duplicate row {k}")
        seen[k] = r
    want = {(e, c["text"], a) for e in assigned for c in cases_by_entry[e] for a in ("hybrid", "prose")}
    if set(seen) != want:
        miss, extra = want - set(seen), set(seen) - want
        raise Incomplete(f"rows != assignment: {len(miss)} missing, {len(extra)} extra")
    gold = {(e, c["text"]): c["gold"] for e in assigned for c in cases_by_entry[e]}
    for (e, t, a), r in seen.items():
        if r["gold"] != gold[(e, t)]: raise Incomplete(f"gold mismatch {e}|{t}|{a}")
        if r["fam"] != fams[e]: raise Incomplete(f"family mismatch {e}")
    return True

def check_selection(sel_rows, ids):
    """r3 (GPT r2 #1): exactly one selection row per registered sender entry, no duplicates, no extras.
    sel_rows = the raw JSONL rows (never a collapsed dict). Returns {entry: row}; raises Incomplete."""
    out = {}
    for r in sel_rows:
        if r["entry"] in out: raise Incomplete(f"duplicate selection row {r['entry']}")
        out[r["entry"]] = r
    if set(out) != set(ids):
        raise Incomplete(f"selection rows != sender assignment: {len(set(ids) - set(out))} missing, {len(set(out) - set(ids))} extra")
    return out

def entry_diffs(rows):
    """-> {fam: [d_entry]} with d = mean hybrid correct - mean prose correct over the entry's cases."""
    acc = {}
    for r in rows: acc.setdefault((r["fam"], r["entry"]), {}).setdefault(r["cond"], []).append(bool(r["correct"]))
    out = {}
    for (f, e), d in sorted(acc.items()):
        if "hybrid" not in d or "prose" not in d: raise ValueError(f"entry {e} lacks an arm")
        if len(d["hybrid"]) != len(d["prose"]): raise ValueError(f"entry {e}: unpaired cases")
        out.setdefault(f, []).append(mean(d["hybrid"]) - mean(d["prose"]))
    return out

def point(by_fam): return mean([x for f in sorted(by_fam) for x in by_fam[f]])

def strat_boot(by_fam, n, seed, ci=0.95):
    """Resample entries with replacement WITHIN each family (family sizes kept); statistic = mean over all entries.
    Percentile convention: sorted statistics s[0..n-1]; lower = s[floor(a*n)], upper = s[ceil((1-a)*n) - 1],
    a = (1-ci)/2 (n = 2000: s[50] and s[1949])."""
    rng = random.Random(seed); fams = sorted(by_fam); st = []
    for _ in range(n):
        xs = []
        for f in fams:
            v = by_fam[f]; xs += [v[rng.randrange(len(v))] for _ in v]
        st.append(mean(xs))
    st.sort(); a = (1 - ci) / 2
    return st[int(math.floor(a * n + 1e-9))], st[int(math.ceil((1 - a) * n - 1e-9)) - 1]

def label(lo, hi, margin):
    """E1b A1.2: lower > -m -> non-inferior; upper < -m -> inferior; else inconclusive."""
    if lo > -margin: return "non-inferior"
    if hi < -margin: return "inferior"
    return "inconclusive"

def cp_upper(k, n, conf=0.95):
    """One-sided Clopper-Pearson upper bound for a binomial rate (bisection; no scipy)."""
    if k >= n: return 1.0
    def tail(p):   # P(X <= k | n, p)
        return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1))
    lo, hi = k / n, 1.0
    for _ in range(100):
        mid = (lo + hi) / 2
        if tail(mid) > 1 - conf: lo = mid
        else: hi = mid
    return hi

def dict_bytes(B, eids):
    """One-off dictionary cost: every entry the receiver must hold to resolve an ID (assigned entries + their
    neighbours): UTF-8 bytes of 'framed ID + space + entry text + newline', one line each."""
    from e1b.protocol import framed_id
    E = B["entries"]; ks = sorted({k for e in eids for k in [e] + B["neighbours"][e]})
    return sum(len((framed_id(E[k]) + " " + E[k]["text"] + "\n").encode("utf-8")) for k in ks)

def direction_result(rows, sel_rows, B, crit, seed, assigned, cases_by_entry, sender_ids):
    """One direction. Completeness (receiver rows AND sender selection rows) is checked first; incomplete data ->
    status INCOMPLETE, never SUCCESS."""
    fams = {e: B["entries"][e]["fam"] for e in assigned}
    try:
        sel = check_selection(sel_rows, sender_ids)
        if not set(assigned) <= set(sender_ids): raise Incomplete("receiver entries not a subset of sender entries")
        check_complete(rows, assigned, cases_by_entry, fams)
    except Incomplete as ex: return dict(status="INCOMPLETE", reason=str(ex), success=False, n_assigned=len(assigned))
    by = entry_diffs(rows); lo, hi = strat_boot(by, crit["bootstrap_resamples"], seed, crit["ci"])
    cov = sum(bool(sel[e]["accepted"]) for e in assigned) / len(assigned)          # denominator = ASSIGNED entries
    hy = [r for r in rows if r["cond"] == "hybrid"]; pr = [r for r in rows if r["cond"] == "prose"]
    hb, pb = sum(r["payload_bytes"] for r in hy), sum(r["payload_bytes"] for r in pr)
    hw, pw = sum(r["whole_exchange_bytes"] for r in hy), sum(r["whole_exchange_bytes"] for r in pr)
    saving = 1 - hb / pb; per_msg = (pb - hb) / len(hy); db = dict_bytes(B, assigned)
    be = db / per_msg if per_msg > 0 else float("inf")
    lab = label(lo, hi, crit["margin"])
    ok = dict(noninferior=lo > -crit["margin"], coverage=cov >= crit["coverage_min"],
              bytes=saving >= crit["byte_saving_min"], breakeven=be <= crit["breakeven_max_messages"])
    wp = sum(1 for e in assigned if sel[e]["accepted"] and not sel[e]["correct"])
    return dict(status="COMPLETE", n_entries=len(assigned), n_messages=len(hy),
                acc_hybrid=mean(bool(r["correct"]) for r in hy), acc_prose=mean(bool(r["correct"]) for r in pr),
                diff=point(by), ci=[lo, hi], label=lab, coverage=cov, payload_saving=saving,
                message_saving_payload_plus_case=1 - hw / pw, dict_bytes=db, payload_saving_per_message=per_msg,
                breakeven_messages=be, checks=ok, success=all(ok.values()),
                wrong_pick_accepted=wp, wrong_pick_accepted_cp95_upper=cp_upper(wp, len(assigned)),
                byte_boundary="sender->receiver channel only; candidate prep and verifier are sender-local")
