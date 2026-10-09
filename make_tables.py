"""Render markdown tables from results/*.json (so RESULTS.md numbers are copied, not retyped)."""
import json, glob, os
M = json.load(open("results/metrics.json"))
f = lambda x: f"{x:.3f}"
print("### Lens sanity: bridge/concept rank metrics per layer (J-lens vs logit lens)\n")
for k in ("qwen", "smol"):
    E = json.load(open(f"results/extract_{k}.json"))
    print(f"**{E['model']}** ({E['n_layers']} layers, fitted source layers {E['src_layers'][0]}-{E['src_layers'][-1]}, chosen band {E['band']}, extraction {E['runtime_s']:.0f}s)\n")
    print("| layer | multihop J pass@10 | multihop logit pass@10 | assoc J pass@10 | assoc logit pass@10 | multihop J median rank |")
    print("|---|---|---|---|---|---|")
    for i, l in enumerate(E["src_layers"]):
        print(f"| {l} | {f(E['multihop']['jlens_pass10'][i])} | {f(E['multihop']['logit_pass10'][i])} | {f(E['association']['jlens_pass10'][i])} | {f(E['association']['logit_pass10'][i])} | {E['multihop']['jlens_median_rank'][i]:.0f} |")
    print(f"\nAny-layer pass@10: multihop J={f(E['multihop']['jlens_any_layer_pass10'])}, logit={f(E['multihop']['logit_any_layer_pass10'])}; association J={f(E['association']['jlens_any_layer_pass10'])}, logit={f(E['association']['logit_any_layer_pass10'])}\n")
print("### (a) Within-model paraphrase consistency (40 pairs; random = all cross-pair combinations)\n")
print("| model | glyph variant | paraphrase cos | random cos | partner retrieval @1 (chance 0.013) |")
print("|---|---|---|---|---|")
for k, r in M["a_within"].items():
    m, v = k.split("|"); print(f"| {m} | {v} | {f(r['para_cos'])} ± {r['para_cos_sd']:.3f} | {f(r['random_cos'])} ± {r['random_cos_sd']:.3f} | {f(r['partner_retrieval_top1'])} |")
print("\n### (b) Cross-model retrieval (A = Qwen, B = SmolLM2)\n")
print("| prompt set | glyph variant | N | A→B @1 | B→A @1 | A→B @5 | chance @1 | shuffled-anchor ctrl @1 (mean / max of 20) | matched cos | mismatched cos |")
print("|---|---|---|---|---|---|---|---|---|---|")
for k, r in M["b_cross"].items():
    s, v = k.split("|"); print(f"| {s} | {v} | {r['N']} | {f(r['A2B_top1'])} | {f(r['B2A_top1'])} | {f(r['A2B_top5'])} | {f(r['chance_top1'])} | {f(r['shuffled_anchor_A2B_top1_mean'])} / {f(r['shuffled_anchor_A2B_top1_max'])} | {f(r['matched_cos'])} | {f(r['mismatched_cos'])} |")
print("\n### (c) Minimal pairs (30 pairs, 29 scored for direction; dense centred glyph)\n")
print("| glyph | model | mean pair cos | frac pairs cos<0.9 | w1 in top10 of diff | w2 in top10 of -diff | both top10 | both top50 | median rank w1 / w2 |")
print("|---|---|---|---|---|---|---|---|---|")
for kind, r in M["c_minimal"].items():
    for mk in ("qwen", "smol"):
        s = r["summary"][mk]
        print(f"| {kind} | {mk} | {f(s['mean_pair_cos'])} | {f(s['frac_pairs_cos_below_0.9'])} | {f(s['frac_w1_top10'])} | {f(s['frac_w2_top10'])} | {f(s['frac_both_top10'])} | {f(s['frac_both_top50'])} | {s['median_rank_w1']:.0f} / {s['median_rank_w2']:.0f} |")
print("\n| glyph | cross-model diff-vector cos, matched pair | mismatched pairs | diff retrieval A→B @1 (chance 0.033) |\n|---|---|---|---|")
for kind, r in M["c_minimal"].items():
    s = r["summary"]; print(f"| {kind} | {f(s['cross_diff_matched_cos'])} | {f(s['cross_diff_mismatched_cos'])} | {f(s['cross_diff_A2B_top1'])} |")
for p in sorted(glob.glob("results/inject_*.json")):
    I = json.load(open(p))
    print(f"\n### Injection: bundle from {I['bundle_source']} → into {I['target']} (layer {I['layer']}, band {I['band']}, k={I['k']}, runtime {I['runtime_s']:.0f}s)\n")
    print("| condition | acc (both) | acc capital | acc language | mean log-prob margin vs other candidates | n |\n|---|---|---|---|---|---|")
    for c, s in I["summary"].items():
        print(f"| {c} | {f(s['acc'])} | {f(s['acc_capital'])} | {f(s['acc_language'])} | {s['mean_margin']:+.2f} | {s['n']} |")
    print("\nBridge rank in source glyph:", I["bridge_rank_in_source_glyph"])
