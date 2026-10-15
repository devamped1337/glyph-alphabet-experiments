"""E1c analysis (PREREG_E1c §5-§6). Paired per-entry differences (hybrid - prose), bootstrap stratified by family
and clustered by entry; label rule = E1b A1.2 (CI only, mutually exclusive)."""
import random
from statistics import mean

def entry_diffs(rows):
    """rows: exchange rows with cond in {hybrid, prose}, keyed by entry (the TRUE entry). -> {fam: [d_entry]}."""
    acc = {}
    for r in rows: acc.setdefault((r["fam"], r["entry"]), {}).setdefault(r["cond"], []).append(bool(r["correct"]))
    out = {}
    for (f, e), d in sorted(acc.items()):
        if "hybrid" not in d or "prose" not in d: raise ValueError(f"entry {e} lacks an arm")
        if len(d["hybrid"]) != len(d["prose"]): raise ValueError(f"entry {e}: unpaired cases")
        out.setdefault(f, []).append(mean(d["hybrid"]) - mean(d["prose"]))
    return out

def point(by_fam):
    xs = [x for f in sorted(by_fam) for x in by_fam[f]]; return mean(xs)

def strat_boot(by_fam, n, seed, ci=0.95):
    """Resample entries with replacement WITHIN each family (sizes kept); statistic = mean over all entries."""
    rng = random.Random(seed); fams = sorted(by_fam); st = []
    for _ in range(n):
        xs = []
        for f in fams:
            v = by_fam[f]; xs += [v[rng.randrange(len(v))] for _ in v]
        st.append(mean(xs))
    st.sort(); a = (1 - ci) / 2
    lo = st[int(a * n)]; hi = st[min(n - 1, int((1 - a) * n) - 1)]
    return lo, hi

def label(lo, hi, margin):
    """E1b A1.2: lower > -m -> non-inferior; upper < -m -> inferior; else inconclusive."""
    if lo > -margin: return "non-inferior"
    if hi < -margin: return "inferior"
    return "inconclusive"

def dict_bytes(B, eids):
    """One-off dictionary cost: every entry the receiver must hold to resolve an ID (true entries + their
    neighbours): UTF-8 bytes of framed ID + entry text, one line each."""
    from e1b.protocol import framed_id
    E = B["entries"]; ks = sorted({k for e in eids for k in [e] + B["neighbours"][e]})
    return sum(len((framed_id(E[k]) + " " + E[k]["text"] + "\n").encode("utf-8")) for k in ks)

def direction_result(rows, sel, B, crit, seed):
    """rows: exchange rows of one direction; sel: {entry: selection row} for the sender. Returns the criteria."""
    by = entry_diffs(rows); lo, hi = strat_boot(by, crit["bootstrap_resamples"], seed, crit["ci"])
    ents = sorted({r["entry"] for r in rows})
    cov = mean(bool(sel[e]["accepted"]) for e in ents)
    hy = [r for r in rows if r["cond"] == "hybrid"]; pr = [r for r in rows if r["cond"] == "prose"]
    hb, pb = sum(r["payload_bytes"] for r in hy), sum(r["payload_bytes"] for r in pr)
    hw, pw = sum(r["whole_exchange_bytes"] for r in hy), sum(r["whole_exchange_bytes"] for r in pr)
    saving = 1 - hb / pb; per_msg = (pb - hb) / len(hy); db = dict_bytes(B, ents)
    be = db / per_msg if per_msg > 0 else float("inf")
    acc_h, acc_p = mean(bool(r["correct"]) for r in hy), mean(bool(r["correct"]) for r in pr)
    lab = label(lo, hi, crit["margin"])
    ok = dict(noninferior=lo > -crit["margin"], coverage=cov >= crit["coverage_min"],
              bytes=saving >= crit["byte_saving_min"], breakeven=be <= crit["breakeven_max_messages"])
    return dict(n_entries=len(ents), n_items=len(hy), acc_hybrid=acc_h, acc_prose=acc_p, diff=point(by), ci=[lo, hi],
                label=lab, coverage=cov, payload_saving=saving, whole_exchange_saving=1 - hw / pw,
                dict_bytes=db, saving_per_msg=per_msg, breakeven_msgs=be, checks=ok, success=all(ok.values()),
                wrong_pick_accepted=sum(1 for e in ents if sel[e]["accepted"] and not sel[e]["correct"]))
