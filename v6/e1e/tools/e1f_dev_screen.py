"""E1f section 7 dev screening. DEV DATA ONLY; a heuristic, not held-out evidence, no savings claim.

Runs on the public synthetic corpus and/or the private box-only sanitised Glyph-own corpus (both are all-dev). It
never reads held-out data or anything under incoming/ (guarded). Message text of the private corpus never leaves the
box: the full report goes to an e1f_* directory under /workspace/e1e-private; the file written under measurements/
holds aggregates only (counts, byte totals, per-arm totals, gate values), no entry bodies and no conversation ids.

    python3 tools/e1f_dev_screen.py --corpus synthetic --aggregates measurements/e1f_dev_screen_synthetic.json
    python3 tools/e1f_dev_screen.py --corpus glyph_own --out /workspace/e1e-private/e1f_dev_screen_r1 \\
            --aggregates measurements/e1f_dev_screen_glyph_own_aggregates.json
Stage 1 (coverage >= 20%): covered bytes by curated entries / total bytes of eligible (<= 65,536 B) dev messages, with
the V = 1 static repository (all dev, joiners 0) curated with the grid point chosen by forward-only tuning.
Stage 2 (heuristic): estimate of arm 7's dev total (each covered span costs the measured average REF cost) against the
measured 4b-delta dev total, primary scenario (V = 5, 2 participants, 0 joiners), in-sample replay of the dev messages.
"""
import argparse
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from e1e import baselines as B  # noqa: E402
from e1e import curation as K  # noqa: E402
from e1e.canon import E1EError  # noqa: E402
from e1e.repo import Publisher  # noqa: E402

CORPORA = {
    "synthetic": {"path": os.path.join(ROOT, "data", "synthetic_gpt_r1.jsonl"), "prov": "synthetic", "public": True},
    "glyph_own": {"path": "/workspace/e1e-private/glyph_own_dev_r1.jsonl", "prov": "glyph_own_dev", "public": False},
}
COVERAGE_FLOOR = 0.20  # section 7, frozen


def guard_path(p):
    q = os.path.realpath(p)
    if "incoming" in q.split(os.sep):
        raise SystemExit("refusing to read anything under incoming/ (held-out reserve)")
    return q


def load(corpus):
    cfg = CORPORA[corpus]
    path = guard_path(cfg["path"])
    recs = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    order = K.order_conversations(recs)
    by = {}
    for r in sorted(recs, key=lambda r: (r["conv_id"], r["seq"])):
        by.setdefault(r["conv_id"], []).append(r)
    convs = [(c, [r["text"] for r in by[c]]) for c in order]
    replay = []
    for c in order:
        for r in by[c]:
            replay.append({"conv_id": c, "sender": r.get("sender_role"), "receiver": r.get("receiver_role"),
                           "msg": r["text"].encode("utf-8")})
    return cfg, convs, replay, hashlib.sha256(open(path, "rb").read()).hexdigest()


def single_version_chain(picks, prov):
    ents = K.entries_from_picks(picks, prov)
    if not ents:
        return []
    pub = Publisher()
    delta, full = pub.publish(ents)
    return [{"state": pub.state, "full": full, "delta": None}]


def make_evaluator(miner, replay_by_conv, prov, participants=2):
    """Arm 7 total (messages + control + framing + sync, V = 1 static) on the pseudo-held-out block (section 4)."""
    def evaluate(picks, block):
        chain = single_version_chain(picks, prov)
        rep = [m for ci in range(block[0], block[1]) for m in replay_by_conv[ci]]
        elig = [m for m in rep if len(m["msg"]) <= B._compact().MAX_MESSAGE_BYTES]
        res = B.replay_arms(elig, chain, lambda r: 1 if chain else 0, ("7",))
        tot = B.scenario_totals(res, chain, participants, [])
        return tot["7"]["total"]
    return evaluate


def version_map(chain, sched_version):
    """Published index of the latest published snapshot whose schedule version is <= sched_version (0 = none)."""
    idx = 0
    for i, rec in enumerate(chain, 1):
        if rec["sched_version"] <= sched_version:
            idx = i
    return idx


def scenario_message_results(miner, replay, n_dev, params, V, joiners, b4):
    M = len(replay)
    sched = [K.version_for_rank(r, M, V) for r in range(M)]
    chain = K.build_repository_chain(miner, n_dev, V, *params, joiners, max_version=max(sched) if sched else 0)
    vi = [version_map(chain, v) for v in sched]
    res = B.replay_arms(replay, chain, lambda r: vi[r], B.ARMS, b4_codec=b4)
    return chain, vi, res


def lineage_records(chain):
    """PRIVATE per-entry source-conversation lineage (conversation ids): written only under /workspace/e1e-private/e1f_*."""
    return [{"published_index": i, "sched_version": r["sched_version"],
             "entries": [{"id": x["id"], "kind": x["kind"], "G": x["G"], "occurrences": x["occurrences"],
                          "body_sha256": hashlib.sha256(r["state"].entries[x["id"]]["body"].encode()).hexdigest(),
                          "source_conversations": x["convs"]} for x in r["entry_lineage"]]}
            for i, r in enumerate(chain, 1)]


def lineage_aggregate(chain):
    """Aggregate lineage (no ids, no text): how many entries were supported by n distinct dev conversations."""
    hist = {}
    for r in chain:
        for x in r["entry_lineage"]:
            n = len(x["convs"])
            hist[n] = hist.get(n, 0) + 1
    return {"entries_by_number_of_source_conversations": {str(k): v for k, v in sorted(hist.items())}}


def aggregate_chain(chain):
    return {"published_snapshots": len(chain),
            "scheduled_versions": [{k_: v for k_, v in row.items()} for row in getattr(chain, "schedule", ())],
            "trailing_skipped_schedule_versions": list(getattr(chain, "trailing_skipped", ())),
            "max_scheduled_version_curated": getattr(chain, "max_version", None),
            "lineage": lineage_aggregate(chain),
            "entries_final": len(chain[-1]["state"].entries) if chain else 0,
            "entry_body_bytes_final": sum(len(e["body"].encode()) for e in chain[-1]["state"].entries.values()) if chain else 0,
            "full_artifact_bytes_final": len(chain[-1]["full"]) if chain else 0,
            "new_entries_per_snapshot": [r["new_entries"] for r in chain],
            "overflow_entries_dropped": sum(r["overflow"] for r in chain),
            "skipped_schedule_versions": [v for r in chain for v in r["skipped_versions"]],
            "kinds_final": ({k: sum(1 for e in chain[-1]["state"].entries.values() if e["kind"] == k)
                             for k in ("literal", "template")} if chain else {})}


def brief(a):
    keys = ("eligible_messages", "input_bytes", "message_bytes", "message_prefix_bytes", "control_bytes",
            "control_prefix_bytes", "declare_bytes_incl_prefix", "reject_bytes_incl_prefix",
            "retransmit_bytes_incl_prefix", "message_plus_control_total", "sync_upload", "sync_download", "sync_total",
            "total", "all_message_total", "total_per_eligible_message", "total_over_input_bytes", "kinds", "rejected",
            "byte_weighted_message_ratio", "mean_per_message_ratio", "covered_bytes", "refs", "ref_bytes",
            "messages_with_refs", "lit_segments", "oversized", "encoder")
    return {k: a[k] for k in keys if k in a}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True, choices=sorted(CORPORA))
    ap.add_argument("--out", required=True, help="private output dir under /workspace/e1e-private/e1f_*/ (full report + lineage manifest)")
    ap.add_argument("--aggregates", help="aggregates-only JSON to write (safe to commit)")
    a = ap.parse_args()
    t0 = time.time()
    cfg, convs, replay, sha = load(a.corpus)
    if not a.out or not os.path.realpath(a.out).startswith("/workspace/e1e-private/e1f_"):
        raise SystemExit("--out is required for every corpus (private lineage manifest): it must be under /workspace/e1e-private/e1f_*/")
    os.makedirs(a.out, exist_ok=True)
    prov = cfg["prov"]
    miner = K.Miner(convs, prov)
    n_dev = len(convs)
    elig_msgs = [m for m in replay if len(m["msg"]) <= 65536]
    corpus_stats = {"corpus": a.corpus, "prov": prov, "file_sha256": sha, "conversations": n_dev, "messages": len(replay),
                    "eligible_messages": len(elig_msgs), "eligible_bytes": sum(len(m["msg"]) for m in elig_msgs),
                    "oversized_messages": len(replay) - len(elig_msgs),
                    "oversized_bytes": sum(len(m["msg"]) for m in replay if len(m["msg"]) > 65536),
                    "has_timestamps": False}
    # ---- forward-only tuning on dev blocks
    replay_by_conv = []
    for c, _ in convs:
        replay_by_conv.append([m for m in replay if m["conv_id"] == c])
    best, scores = K.tune(miner, make_evaluator(miner, replay_by_conv, prov))
    L, k, C = best
    params = (L, k, C)
    t_tune = time.time() - t0
    # ---- Stage 1: coverage with the V = 1 static repository, joiners 0
    chain1 = K.build_repository_chain(miner, n_dev, 1, L, k, C, 0)
    res1 = B.replay_arms(elig_msgs, chain1, lambda r: 1 if chain1 else 0, ("7",))
    r7 = res1["7"]
    cov = r7["covered_bytes"] / r7["input_bytes"] if r7["input_bytes"] else 0.0
    stage1 = {"definition": "covered bytes by REF spans of the arm-7 encoder / total bytes of eligible dev messages (<= 65,536 B), V=1 static repository from all dev, joiners 0",
              "covered_bytes": r7["covered_bytes"], "eligible_bytes": r7["input_bytes"], "coverage": cov,
              "refs": r7["refs"], "messages_with_refs": r7["messages_with_refs"], "eligible_messages": r7["eligible_messages"],
              "floor": COVERAGE_FLOOR, "passes_floor": cov >= COVERAGE_FLOOR,
              "oversized_excluded": {"messages": corpus_stats["oversized_messages"], "bytes": corpus_stats["oversized_bytes"]},
              "entries": len(chain1[0]["state"].entries) if chain1 else 0,
              "curation": {k_: v for k_, v in (chain1[0]["stats"] if chain1 else {}).items()}}
    # ---- informational only (NOT used for the gate, nothing is re-chosen): in-sample coverage at every grid point, V=1
    sens = {}
    for gL in K.GRID_L:
        for gk in K.GRID_K:
            ch = K.build_repository_chain(miner, n_dev, 1, gL, gk, max(K.GRID_C), 0)
            rr = B.replay_arms(elig_msgs, ch, lambda r: 1 if ch else 0, ("7",))["7"]
            sens[f"L{gL}_k{gk}_Cmax"] = {"entries": len(ch[0]["state"].entries) if ch else 0,
                                         "covered_bytes": rr["covered_bytes"], "refs": rr["refs"],
                                         "coverage": (rr["covered_bytes"] / rr["input_bytes"]) if rr["input_bytes"] else 0.0}
    # ---- baseline 4 (section 7 selection, dev only, in-sample on these dev messages)
    dev_by_conv = [(c, [m["msg"] for m in replay_by_conv[i] if len(m["msg"]) <= 65536]) for i, (c, _) in enumerate(convs)]
    b4, b4rep = B.select_baseline4(dev_by_conv, participants=2)
    # ---- scenarios (message-level cached per (V, joiners); participants only change sync)
    cache, scenarios, lineage = {}, [], {}
    for sc in B.SCENARIO_GRID:
        key = (sc["V"], sc["joiners"])
        if key not in cache:
            cache[key] = scenario_message_results(miner, replay, n_dev, params, sc["V"], sc["joiners"], b4)
        chain, vi, res = cache[key]
        lineage.setdefault(f"V{sc['V']}_joiners{sc['joiners']}", lineage_records(chain))
        M = len(replay)
        jv = [vi[i] for i in B.joiner_indexes(M)] if sc["joiners"] else []
        tot = B.scenario_totals(res, chain, sc["participants"], jv, b4)
        scenarios.append({"scenario": sc, "primary": sc == B.PRIMARY_SCENARIO, "chain": aggregate_chain(chain),
                          "joiner_published_indexes": jv, "break_even": tot["_break_even"],
                          "arms": {arm: brief(tot[arm]) for arm in B.ARMS},
                          "arm7_vs_4b_delta_total": tot["7"]["total"] - tot["4b-delta"]["total"],
                          "arm7_vs_arm6_total": tot["7"]["total"] - tot["6"]["total"],
                          "arm7_vs_4b_total": tot["7"]["total"] - tot["4b"]["total"]})
    prim = [s for s in scenarios if s["primary"]][0]
    p7, pd = prim["arms"]["7"], prim["arms"]["4b-delta"]
    # ---- Stage 2 heuristic (amendment A1 section 7, exact formula; primary scenario, in-sample dev replay)
    avg_ref = p7["ref_bytes"] / p7["refs"] if p7["refs"] else 0.0
    n_el = p7["eligible_messages"]
    prim_entries = prim["chain"]["entries_final"]
    if prim_entries == 0:
        stage2 = {"definition": "undefined: the primary-scenario repository is empty, every arm-7 message is a raw envelope; no estimate is made",
                  "measured_arm7_total": p7["total"], "measured_4b_delta_total": pd["total"],
                  "estimate_total": None, "estimate_below_4b_delta": None, "measured_arm7_below_4b_delta": p7["total"] < pd["total"]}
    else:
        est_core = (p7["input_bytes"] - p7["covered_bytes"]) + p7["refs"] * avg_ref + 2 * n_el
        est = est_core + p7["message_prefix_bytes"] + p7["control_bytes"] + p7["control_prefix_bytes"] + p7["sync_total"]
        est_lit = est + 2 * p7["lit_segments"]
        stage2 = {"definition": "AMENDMENT A1 section 7 Stage 2: estimate = (eligible input bytes - covered bytes) + REFs x measured average REF bytes + 2 x eligible messages (0x01 discriminator + a ONE-byte epoch; assumes every message is sent compact) + measured length prefixes + measured control bytes + measured arm-7 sync; the variant adds 2 bytes per measured LIT segment (opcode + a one-byte length; understates LIT longer than 127 bytes). Approximate: ignores raw-envelope sends and the empty-repository case. Compared with the measured 4b-delta total; primary scenario; in-sample dev replay",
                  "average_ref_bytes_measured": avg_ref, "estimate_total": est, "estimate_total_with_lit_overhead_2_bytes_per_lit_segment": est_lit,
                  "measured_arm7_total": p7["total"], "measured_4b_delta_total": pd["total"],
                  "measured_arm6_total": prim["arms"]["6"]["total"],
                  "estimate_below_4b_delta": est < pd["total"], "estimate_with_lit_overhead_below_4b_delta": est_lit < pd["total"],
                  "measured_arm7_below_4b_delta": p7["total"] < pd["total"]}
    out = {
        "label": "DEV SCREENING ONLY. Heuristic, in-sample on dev corpora; not held-out evidence; no savings claim. "
                 + ("Glyph-own corpus is single-operator and self-similar (sanitised)." if a.corpus == "glyph_own" else "GPT-generated synthetic corpus."),
        "corpus": corpus_stats, "tuning": {"chosen": {"L": L, "k": k, "C": C},
                                           "scores_mean_arm7_total_bytes": {f"L{g[0]}_k{g[1]}_C{g[2]}": s for g, s in sorted(scores.items())},
                                           "seconds": round(t_tune, 1)},
        "stage1": stage1, "stage2": stage2, "spec": "E1F_PROPOSAL_DRAFT.md + E1F_AMENDMENT_A1_DRAFT.md",
        "informational_in_sample_coverage_by_grid_point_not_used_for_the_gate": sens, "baseline4_selection": {k_: v for k_, v in b4rep.items()},
        "scenarios": scenarios, "elapsed_seconds": round(time.time() - t0, 1),
        "code_sha256": {f: hashlib.sha256(open(os.path.join(ROOT, f), "rb").read()).hexdigest()
                        for f in ("e1e/compact.py", "e1e/curation.py", "e1e/baselines.py", "tools/e1f_dev_screen.py")},
    }
    with open(os.path.join(a.out, f"{a.corpus}_report.json"), "w") as f:
        json.dump(out, f, indent=1, sort_keys=True)
    with open(os.path.join(a.out, f"{a.corpus}_lineage_manifest.json"), "w") as f:  # PRIVATE: conversation ids; never committed
        json.dump({"label": "PRIVATE per-entry source-conversation lineage; do not commit", "corpus": a.corpus,
                   "chains": lineage}, f, indent=1, sort_keys=True)
    if a.aggregates:
        with open(a.aggregates, "w") as f:
            json.dump(out, f, indent=1, sort_keys=True)
    print(json.dumps({"corpus": a.corpus, "chosen": [L, k, C], "stage1": {x: stage1[x] for x in ("covered_bytes", "eligible_bytes", "coverage", "passes_floor")},
                      "stage2": {x: stage2[x] for x in ("estimate_total", "measured_arm7_total", "measured_4b_delta_total", "estimate_below_4b_delta")},
                      "seconds": out["elapsed_seconds"]}, indent=1))


if __name__ == "__main__":
    main()
