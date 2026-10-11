"""Analysis (PREREG_E1b §9, §10 + A1.2, A1.3, A1.6). Paired cluster bootstrap over entries; mutually
exclusive labels; payload vs whole-exchange bytes; costs with FLOPs on newly processed tokens only."""
import json, math, random
from pathlib import Path
from . import cachediag

def jl(p):
    if not Path(p).exists(): return []
    with open(p) as f: return [json.loads(l) for l in f]

def label(lo, hi, margin):
    """A1.2 (mutually exclusive): lower CI > -margin -> non-inferior; upper CI < -margin -> inferior; else inconclusive."""
    if lo > -margin: return "non-inferior"
    if hi < -margin: return "inferior"
    return "inconclusive"

def bar_verdict(k, n, bar):
    """'met in sample' (point >= bar) vs 'met at 95% confidence' (Wilson lower bound >= bar)."""
    if n == 0: return dict(point=None, lower95=None, verdict="no data")
    p = k / n; z = 1.96; d = 1 + z * z / n; c = p + z * z / (2 * n); r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    lo = (c - r) / d
    v = "met at 95% confidence" if lo >= bar else ("met in sample" if p >= bar else "not met")
    return dict(point=round(p, 4), lower95=round(lo, 4), k=k, n=n, verdict=v)

def cluster_boot(pairs, n_boot, seed):
    """pairs: {entry: [(a_correct, b_correct), ...]} -> mean diff (a-b) and 95% percentile CI over entries."""
    keys = sorted(pairs); rng = random.Random(seed)
    def stat(ks):
        s = n = 0
        for k in ks:
            for a, b in pairs[k]: s += a - b; n += 1
        return s / n if n else float("nan")
    est = stat(keys); bs = sorted(stat([keys[rng.randrange(len(keys))] for _ in keys]) for _ in range(n_boot))
    return est, bs[int(0.025 * n_boot)], bs[int(0.975 * n_boot) - 1]

def boot_mean(vals_by_entry, n_boot, seed):
    keys = sorted(vals_by_entry); rng = random.Random(seed)
    def stat(ks):
        v = [x for k in ks for x in vals_by_entry[k]]; return sum(v) / len(v)
    bs = sorted(stat([keys[rng.randrange(len(keys))] for _ in keys]) for _ in range(n_boot))
    return stat(keys), bs[int(0.025 * n_boot)], bs[int(0.975 * n_boot) - 1]

def flops(rows, params):
    return 2 * params * sum((r.get("new_prompt_tokens") or 0) + (r.get("gen_tokens") or 0) for r in rows) / max(1, len(rows))

def cost_table(rows, params):
    out = {}
    for cond in sorted({r["cond"] for r in rows}):
        R = [r for r in rows if r["cond"] == cond and r.get("model_called", True)]
        if not R: continue
        out[cond] = dict(n=len(R), latency_s=sum(r["latency_s"] for r in R) / len(R),
                         prompt_tokens=sum(r["prompt_tokens"] for r in R) / len(R),
                         new_prompt_tokens=sum(r["new_prompt_tokens"] for r in R) / len(R),
                         gen_tokens=sum(r["gen_tokens"] for r in R) / len(R), flops_new_tokens=flops(R, params),
                         batch="batch-1" if all(r.get("batch") == 1 for r in R) else "mixed",
                         cached=any(r.get("warm") for r in R))
    return out

def by_fam_acc(rows):
    d = {}
    for r in rows: d.setdefault(r["fam"], []).append(r["correct"])
    return {f: dict(acc=sum(v) / len(v), n=len(v)) for f, v in d.items()}

# ------------------------------------------------------------------ Stage A
def summarize_A(d, cfg, B):
    d = Path(d); A = cfg["stageA"]; out = {"claims": "Stage A is diagnostic only: NO repository, ID-channel or efficiency claims"}
    models = list(cfg["models"]["stageA"])
    for m in models:
        a1 = jl(d / f"A1_{m}.jsonl"); a3 = jl(d / f"A3_{m}.jsonl"); a2 = jl(d / f"A2_{m}.jsonl")
        fam = by_fam_acc(a1)
        out[m] = dict(A1=fam, A1_has_family={f: v["acc"] >= A["a1_family_floor"] for f, v in fam.items()},
                      A3=dict(with_trailing_answer=by_fam_acc(a3), missing_answer_line_rate=dict(
                          fixed=sum(r["parse_path"] != "answer_line" for r in a1) / max(1, len(a1)),
                          trailing=sum(r["parse_path"] != "answer_line" for r in a3) / max(1, len(a3))),
                          paired_diff=(sum(r["correct"] for r in a1) - sum(r["correct"] for r in a3)) / max(1, len(a1))))
        ent = {}
        for r in a2:
            if r["with_text"]: ent.setdefault(r["entry"], []).append(r)
        out[m]["A2_entry_acc"] = {e: sum(x["correct"] for x in v) / len(v) for e, v in ent.items()}
        out[m]["A2_invalid_rate"] = sum(r["letter"] is None for r in a2) / max(1, len(a2))
    # agreement + exit rule
    a2s = {m: {(r["entry"], r["template"]): r["letter"] for r in jl(d / f"A2_{m}.jsonl") if r["with_text"]} for m in models}
    honest = [e for g in ("A2_F1", "A2_F2", "A2_F3s") for e in B["groups"][g]]
    passes = 0; per = {}
    for e in honest:
        ks = [k for k in a2s[models[0]] if k[0] == e]
        agree = sum(a2s[models[0]][k] == a2s[models[1]].get(k) and a2s[models[0]][k] is not None for k in ks) / max(1, len(ks))
        ok = all(out[m]["A2_entry_acc"].get(e, 0) >= cfg["gate"]["probe_bar"] for m in models) and agree >= cfg["gate"]["agree_bar"]
        per[e] = dict(agree=agree, passes=ok); passes += ok
    out["A2_per_entry"] = per
    nt = {}
    for m in models:
        for r in jl(d / f"A2_{m}.jsonl"):
            if not r["with_text"]: nt.setdefault(r["template"], []).append(r["correct"])
    out["A2_no_text"] = {t: dict(acc=sum(v) / len(v), n=len(v), flagged=(len(v) >= cfg["probe_leak_min_obs"] and sum(v) / len(v) > cfg["probe_leak_flag"]),
                                 insufficient_obs=len(v) < cfg["probe_leak_min_obs"]) for t, v in nt.items()}
    a4 = [r for r in jl(d / "A4_qwen3b.jsonl") if r["gold_changes"]]
    follow = sum(r["follows_planted"] for r in a4) / max(1, len(a4))
    out["A4"] = dict(n_gold_changing=len(a4), follow_rate=follow)
    for m in models:
        out[m]["A5_cache"] = cachediag.summarize(jl(d / f"A5_{m}.jsonl"))
        a6 = jl(d / f"A6_{m}.jsonl")
        out[m]["A6_cost"] = {f"{c}|{'warm' if w else 'cold'}": cost_table([r for r in a6 if r["cond"] == c and r["warm"] == w], cfg["models"]["stageA"][m]["params"]).get(c)
                             for c in ("direct_text", "prose") for w in (False, True)}
        out[m]["A6_valid"] = out[m]["A5_cache"]["claim_allowed"]
    share = passes / max(1, len(honest))
    out["exit"] = dict(honest_pass_share=share, a4_follow=follow,
                       small_pair_may_calibrate=(share >= A["exit_entry_share"] and follow >= A["a4_follow_min"]),
                       rule="clears 0.90 on >=80% of honest entries AND A4 follow >= 0.70; otherwise go to Stage B (7B)")
    out["E1_cache_baseline"] = dict(qwen3b=dict(changed=45, flipped=21, n=480), smol17=dict(changed=104, flipped=33, n=480))
    return out

# ------------------------------------------------------------------ B1 gate
def gate_decision(d, pair, cfg, E):
    d = Path(d); G = cfg["gate"]; res = {}
    for kind in ("calib", "testgate"):
        rows = {m: jl(d / f"{kind}_{m}.jsonl") for m in pair}; ents = sorted({r["entry"] for r in rows[pair[0]]})
        dec = {}
        for e in ents:
            accs = {}; lets = {}
            for m in pair:
                R = [r for r in rows[m] if r["entry"] == e]; accs[m] = sum(r["correct"] for r in R) / len(R)
                lets[m] = {r["template"]: r["letter"] for r in R}
            ks = lets[pair[0]].keys(); agree = sum(lets[pair[0]][k] is not None and lets[pair[0]][k] == lets[pair[1]].get(k) for k in ks) / len(ks)
            dec[e] = dict(acc=accs, agree=agree, accepted=all(a >= G["probe_bar"] for a in accs.values()) and agree >= G["agree_bar"],
                          planted=E[e]["kind"] == "planted")
        H = [v for v in dec.values() if not v["planted"]]; P = [v for v in dec.values() if v["planted"]]
        ha = sum(v["accepted"] for v in H); pr = sum(not v["accepted"] for v in P)
        res[kind] = dict(per_entry=dec, honest_accept=bar_verdict(ha, len(H), G["calib_eligibility" if kind == "calib" else "repo_target"]["honest_accept"]),
                         planted_reject=bar_verdict(pr, len(P), G["calib_eligibility" if kind == "calib" else "repo_target"]["planted_reject"]))
    c = res["calib"]; elig = (c["honest_accept"]["point"] or 0) >= G["calib_eligibility"]["honest_accept"] and (c["planted_reject"]["point"] or 0) >= G["calib_eligibility"]["planted_reject"]
    accepted = sorted(e for e, v in c["per_entry"].items() if v["accepted"] and not v["planted"])
    manip = [r for r in jl(d / "manip.jsonl") if r["gold_changes"]]
    return dict(eligible=elig, accepted=accepted, calib=c, testgate_vs_repo_target=res["testgate"],
                manipulation=dict(n=len(manip), follow_rate=sum(r["follows_planted"] for r in manip) / max(1, len(manip))),
                note=("Accepted list FIXED from calibration (A1.3); TEST-gate only evaluates it. 'met in sample' != 'met at 95% confidence'. "
                      "None of these bars is the POC success criterion."),
                not_checked_repository=None if elig else "B1 failed: B2/B3 still run, but the combined pipeline is NOT a checked repository; gate acceptance, coverage and abstentions are reported with every number")

# ------------------------------------------------------------------ B2
def summarize_B2(d, pair, cfg, B):
    d = Path(d); out = dict(byte_identity=json.load(open(d / "byte_identity.json")),
                            note="id_oracle vs direct_text is ZERO BY CONSTRUCTION (byte-identical prompts); B2 content = prose comparison + cost table")
    U = jl(d / "unknown.jsonl"); out["unknown_id"] = dict(n=len(U), deterministic_unknown=sum((not r["resolved"]) and not r["model_called"] for r in U))
    for m in pair:
        R = jl(d / f"main_{m}.jsonl"); params = cfg["models"]["stageB"][m]["params"]
        main = [r for r in R if r["step"] == "main"]
        pr = {}
        for r in main:
            if r["cond"] in ("direct_text", "prose"): pr.setdefault((r["entry"], r["case"]), {})[r["cond"]] = r["correct"]
        pairs = {}
        for (e, _), v in pr.items():
            if len(v) == 2: pairs.setdefault(e, []).append((v["direct_text"], v["prose"]))
        core_pairs = {e: v for e, v in pairs.items() if B["entries"][e]["fam"] in cfg["families_core"]}
        est, lo, hi = cluster_boot(core_pairs, cfg["bootstrap_resamples"], cfg["seeds"]["bootstrap"]) if core_pairs else (None,) * 3
        idp = [r for r in R if r["step"] == "id_oracle_paired"]
        dt = {r["case"]: r for r in main if r["cond"] == "direct_text"}
        out[m] = dict(acc_by_cond_fam={c: by_fam_acc([r for r in main if r["cond"] == c]) for c in sorted({r["cond"] for r in main})},
                      direct_minus_prose_core=dict(est=est, ci=[lo, hi], label=label(lo, hi, cfg["ni_margin"]) if lo is not None else None),
                      id_oracle_paired=dict(n=len(idp), identical_outputs=sum(r["raw"] == dt.get(r["case"], {}).get("raw") for r in idp)),
                      cost_cold=cost_table(main, params), cost_prefix_cached=cost_table(jl(d / f"prefix_{m}.jsonl"), params),
                      cache=json.load(open(d / f"cache_summary_{m}.json")) if (d / f"cache_summary_{m}.json").exists() else None)
        out[m]["cost_note"] = "cached timing is batch-1 only; FLOPs = 2*params*(newly processed + generated tokens); uncached always shown"
    return out

# ------------------------------------------------------------------ B3 headline
def summarize_B3(d, pair, cfg, B, gated):
    d = Path(d); E = B["entries"]; out = dict(gated=gated, framing="communication proof of concept; 4-way selection, not repository search")
    if not gated: out["not_checked_repository"] = "B1 failed or not eligible: combined pipeline is NOT a checked repository"
    excluded = []
    for m in pair:
        q = Path(d).parent / "B0" / f"qualification_{m}.json"
        if q.exists():
            excluded += [f for f, v in json.load(open(q))["families"].items() if f in cfg["families_core"] and not v["ok"]]
    excluded = sorted(set(excluded)); out["excluded_families"] = excluded
    core = [f for f in cfg["families_core"] if f not in excluded]
    if not core:
        out["headline"] = "NO non-excluded core family (all failed B0 qualification): no headline comparison possible"
        out["poc_success"] = dict(both_directions_non_inferior=False, payload_target_met_both=False, note=out["headline"])
        return out
    for snd, rcv in ((pair[0], pair[1]), (pair[1], pair[0])):
        R = jl(d / f"exchange_{snd}_to_{rcv}.jsonl"); S = {r["entry"]: r for r in jl(d / f"select_{snd}.jsonl")}
        cell = {}
        for r in R: cell.setdefault((r["entry"], r["case"]), {})[r["cond"]] = r
        pairs = {}; fam_pairs = {}
        for (e, _), v in cell.items():
            if len(v) < 2: continue
            t = (bool(v["id_selected"]["correct"]), bool(v["prose"]["correct"]))
            fam_pairs.setdefault(E[e]["fam"], {}).setdefault(e, []).append(t)
            if E[e]["fam"] in core: pairs.setdefault(e, []).append(t)
        est, lo, hi = cluster_boot(pairs, cfg["bootstrap_resamples"], cfg["seeds"]["bootstrap"])
        per_fam = {}
        for f, pp in fam_pairs.items():
            fe, fl, fh = cluster_boot(pp, cfg["bootstrap_resamples"], cfg["seeds"]["bootstrap"])
            per_fam[f] = dict(diff=fe, ci=[fl, fh], label=label(fl, fh, cfg["ni_margin"]), descriptive=f not in core or True)
        ids = [v["id_selected"] for v in cell.values() if "id_selected" in v and E[v["id_selected"]["entry"]]["fam"] in core]
        pro = [v["prose"] for v in cell.values() if "prose" in v and E[v["prose"]["entry"]]["fam"] in core]
        pay = 1 - (sum(r["payload_bytes"] for r in ids) / len(ids)) / (sum(r["payload_bytes"] for r in pro) / len(pro))
        whole = 1 - (sum(r["whole_exchange_bytes"] for r in ids) / len(ids)) / (sum(r["whole_exchange_bytes"] for r in pro) / len(pro))
        sel = {e: [s["correct"]] for e, s in S.items() if E[e]["fam"] in core}
        sm, sl, sh = boot_mean(sel, cfg["bootstrap_resamples"], cfg["seeds"]["bootstrap"])
        base = {}
        for bn in ("tfidf", "bm25", "minilm"):
            v = {e: [s["baselines"].get(bn) == e] for e, s in S.items() if E[e]["fam"] in core and s["baselines"].get(bn) is not None}
            if v: base[bn] = boot_mean(v, cfg["bootstrap_resamples"], cfg["seeds"]["bootstrap"])[0]
        best = max(base, key=base.get) if base else None
        diffp = {e: [(int(S[e]["correct"]), int(S[e]["baselines"].get(best) == e))] for e in sel} if best else {}
        be, bl, bh = cluster_boot(diffp, cfg["bootstrap_resamples"], cfg["seeds"]["bootstrap"]) if diffp else (None,) * 3
        params_s, params_r = cfg["models"]["stageB"][snd]["params"], cfg["models"]["stageB"][rcv]["params"]
        sender_rows = list(S.values())
        n_msgs = len(ids)
        setup_bytes = sum(len(E[x]["text"].encode()) for x in {r.get("selected") for r in ids if r.get("selected")})
        out[f"{snd}->{rcv}"] = dict(
            headline=dict(diff_id_selected_minus_prose=est, ci95=[lo, hi], label=label(lo, hi, cfg["ni_margin"]), margin=-cfg["ni_margin"],
                          n_entries=len(pairs), n_items=sum(len(v) for v in pairs.values()),
                          acc_id_selected=sum(r["correct"] for r in ids) / len(ids), acc_prose=sum(r["correct"] for r in pro) / len(pro)),
            bytes=dict(payload_saving=pay, whole_exchange_saving=whole, target_payload_saving=cfg["bytes_target_payload_saving"],
                       payload_target_met=pay >= cfg["bytes_target_payload_saving"],
                       note="reported separately from the accuracy label (A1.2); saving is near-guaranteed by design"),
            per_family_descriptive=per_fam,
            denominators=dict(all_scheduled_items=len(ids), abstentions=sum(bool(r.get("abstained")) for r in ids),
                              rejected_by_gate=sum(r.get("reason") == "rejected_by_gate" for r in ids),
                              unresolved=sum(r.get("model_called") is False for r in ids), sender_invalid=sum(r.get("reason") == "sender_invalid" for r in ids)),
            selection=dict(acc=sm, ci95=[sl, sh], chance=0.25, above_chance=sl > 0.25, baselines=base, best_baseline=best,
                           sender_minus_best_baseline=dict(est=be, ci=[bl, bh], beats=(bl is not None and bl > 0)),
                           note="separate secondary claim; not part of the headline"),
            costs=dict(sender=dict(latency_s=sum(r["latency_s"] for r in sender_rows) / len(sender_rows),
                                   flops=flops(sender_rows, params_s), candidate_prep_bytes=sum(r["prep_bytes"] for r in sender_rows) / len(sender_rows)),
                       receiver=cost_table([v["id_selected"] for v in cell.values() if "id_selected" in v] + [v["prose"] for v in cell.values() if "prose" in v], params_r),
                       dictionary_setup=dict(bytes_once=setup_bytes, messages=n_msgs, amortised_bytes_per_message=setup_bytes / max(1, n_msgs),
                                             break_even_messages=None)))
        o = out[f"{snd}->{rcv}"]; per_msg_saving = (sum(r["payload_bytes"] for r in pro) - sum(r["payload_bytes"] for r in ids)) / max(1, len(ids))
        o["costs"]["dictionary_setup"]["break_even_messages"] = (setup_bytes / per_msg_saving) if per_msg_saving > 0 else None
    heads = [out[k]["headline"]["label"] for k in out if "->" in k]
    out["poc_success"] = dict(both_directions_non_inferior=all(h == "non-inferior" for h in heads),
                              payload_target_met_both=all(out[k]["bytes"]["payload_target_met"] for k in out if "->" in k),
                              note="success = both directions non-inferior AND payload bytes >=30% fewer AND costs reported; byte miss reported separately")
    return out
