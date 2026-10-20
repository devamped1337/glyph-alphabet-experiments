"""E1d lifetime byte accounting (DRAFT_PLAN §3, §4, §5). Pure functions; no model."""
import math, random, gzip, json
from e1b.stages import seed_of
from measure_dict_artifact import serialize, MAGIC   # frozen serializer + format (v6/e1d/tools)

def gz9(b): return len(gzip.compress(b, compresslevel=9, mtime=0))

def manifest_len(kind, v, base, n):
    """Exact manifest length (§4.2) for a version and entry count (digest is always 64 hex)."""
    return len(f"{MAGIC} kind={kind} dict_ver={v} base={'-' if base is None else base} n={n} sha256={'0' * 64}\n".encode())

class Lifecycle:
    """Derived artifact sizes from the MEASURED v1 artifact (§5.2): body_v1, n_entries_v1, n_core_v1."""
    def __init__(self, body_v1, n_entries_v1, n_core_v1, n_core_v1_per_family, families, r):
        self.body_v1, self.n1, self.c1 = body_v1, n_entries_v1, n_core_v1
        self.L_rule = body_v1 / n_core_v1; self.per_rule = n_entries_v1 / n_core_v1
        self.rules = families * math.ceil(round(r * n_core_v1_per_family, 9))          # added rules per delta (all families)
        self.delta_body = math.ceil(self.rules * self.L_rule); self.delta_n = round(self.rules * self.per_rule)
    def A(self, v): return manifest_len("full", v, None, self.n1 + (v - 1) * self.delta_n) + self.body_v1 + (v - 1) * self.delta_body
    def D(self, v): return manifest_len("delta", v, v - 1, self.delta_n) + self.delta_body

def events(w, LC):
    """Frozen event order (§5.2): per day, the delta first (to participants present immediately before, + 1 maintainer
    upload), then joiners get the then-current full version. replace=True: a joiner replaces a holder (count fixed).
    -> dict(F_total, full=[(day, v, count)], deltas=[(day, v, recipients)])."""
    P = w["P0"]; v = 1; F = P * LC.A(1); full = [(0, 1, P)]; dl = []; joins = {int(k): n for k, n in w["joins"].items()}
    for day in range(0, 90):
        if day in w["delta_days"]:
            v += 1; F += (P + 1) * LC.D(v); dl.append((day, v, P + 1))
        if day in joins:
            n = joins[day]; F += n * LC.A(v); full.append((day, v, n))
            if not w["replace"]: P += n
    return dict(F_total=F, full=full, deltas=dl, final_version=v, final_participants=P)

def F_d(w, LC): return events(w, LC)["F_total"] * w["alloc"]

def entry_bytes(rows, key="wire_bytes"):
    """-> {fam: [(h_e, p_e)]}: per entry, mean serialized bytes over its cases, hybrid and prose (paired)."""
    acc = {}
    for r in rows: acc.setdefault((r["fam"], r["entry"]), {}).setdefault(r["cond"], []).append(r[key])
    out = {}
    for (f, e), d in sorted(acc.items()):
        assert len(d.get("hybrid", [])) == len(d.get("prose", [])) > 0, f"unpaired entry {e}"
        out.setdefault(f, []).append((sum(d["hybrid"]) / len(d["hybrid"]), sum(d["prose"]) / len(d["prose"])))
    return out

def S_of(H, P, F, M, a): return 1 - (F + M * (a * H + (1 - a) * P)) / (M * P)

def fam_mean(by, i): fs = sorted(by); return sum(sum(x[i] for x in by[f]) / len(by[f]) for f in fs) / len(fs)

def lifetime_boot(by, F, M, a, seed, n=10000, idx=500):
    """§3.1: resample entries within each family (family sizes kept); H*, P* = equal-weight family means; F (fixed,
    derived) is added in EVERY replicate, never resampled. -> (point, s[idx], replicates sorted)."""
    rng = random.Random(seed); fs = sorted(by); st = []
    for _ in range(n):
        H = P = 0.0
        for f in fs:
            v = by[f]; d = [v[rng.randrange(len(v))] for _ in v]; H += sum(x[0] for x in d) / len(d); P += sum(x[1] for x in d) / len(d)
        H /= len(fs); P /= len(fs); st.append(S_of(H, P, F, M, a))
    st.sort(); return S_of(fam_mean(by, 0), fam_mean(by, 1), F, M, a), st[idx], st

def lifetime_seed(direction): return seed_of(95066, direction, "lifetime")

def min_traffic(by, F_per_M, w, seed, step, thr=0.20, n=10000, idx=500, max_steps=2000):
    """Secondary: smallest aggregate traffic (multiples of `step`) with s[idx] > thr, all else as w. F_per_M(M) -> F_d."""
    for k in range(1, max_steps + 1):
        M = k * step / 2; _, lo, _ = lifetime_boot(by, F_per_M(M), M, w["a"], seed, n, idx)
        if lo > thr: return k * step
    return None
