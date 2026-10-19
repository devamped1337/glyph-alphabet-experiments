"""E1d (DRAFT): sizing for the lifetime byte bound (DRAFT_PLAN §6), from E1c T1 rows. CPU only, read-only.
  python v6/e1d/tools/size_byte_bound.py [out.json]

Per entry e: h_e, p_e = mean serialized message bytes over its 4 cases (payload + case + 15 B frozen framing,
DRAFT_PLAN §4.1), hybrid and prose. Replicate (as §3.1): draw n entries with replacement within F1 and F2,
R* = H*/P* with family weights 0.5. Reported: SD(R*), and the one-sided distance d = q95(R*) - R_hat
(sorted ascending, q95 = s[9499] of 10,000). Since S = 1 - F/(M P) - a H/P - (1 - a), the message part of the S
lower bound sits about a * d below the point (a = 0.89). The F/(M P) term also moves with P*; that second-order
part depends on W and is left to the real bootstrap (no W-level projection is computed here)."""
import sys, json, random, statistics as st
from collections import defaultdict
from pathlib import Path
V6 = Path(__file__).resolve().parents[2]; T1 = V6 / "e1c" / "results" / "T1"
FRAMING, A, REPS, SEED = 15, 0.89, 10000, 95100

def entries(direction):
    hb, pb, fam = defaultdict(list), defaultdict(list), {}
    for l in open(T1 / f"exchange_{direction}.jsonl"):
        r = json.loads(l); b = r["payload_bytes"] + r["case_bytes"] + FRAMING; fam[r["entry"]] = r["fam"]
        (hb if r["cond"] == "hybrid" else pb)[r["entry"]].append(b)
    by = defaultdict(list)
    for e in sorted(fam): by[fam[e]].append((st.mean(hb[e]), st.mean(pb[e])))
    return by

def ratio(by, pick):
    H = sum(0.5 * st.mean(h for h, _ in pick[f]) for f in pick); P = sum(0.5 * st.mean(p for _, p in pick[f]) for f in pick)
    return H / P

def main():
    out = dict(source="v6/e1c/results/T1/exchange_*.jsonl", framing_bytes=FRAMING, a=A, replicates=REPS, seed=SEED, by_direction={})
    for d in ("qwen7b_to_falcon7b", "falcon7b_to_qwen7b"):
        by = entries(d); r_hat = ratio(by, by); res = {}
        for n in (40, 60, 80, 120):
            rng = random.Random(f"{SEED}|{d}|{n}"); v = []
            for _ in range(REPS): v.append(ratio(by, {f: [by[f][rng.randrange(len(by[f]))] for _ in range(n)] for f in sorted(by)}))
            v.sort(); dist = v[int(0.95 * REPS) - 1] - r_hat
            res[n] = dict(sd_ratio=round(st.pstdev(v), 5), one_sided_distance_ratio_pts=round(100 * dist, 3),
                          approx_S_bound_distance_pts=round(100 * A * dist, 3))
        out["by_direction"][d] = dict(n_entries_T1=sum(len(x) for x in by.values()), per_family=res)
    s = json.dumps(out, indent=1)
    if len(sys.argv) > 1: Path(sys.argv[1]).write_text(s + "\n")
    print(s)

if __name__ == "__main__": main()
