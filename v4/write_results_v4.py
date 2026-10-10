"""Render RESULTS_v4.md from results/v4/tables_v4.json + frozen.json + test_*.json metadata."""
import json, os, time
os.chdir("/workspace/glyph-exp")
T = json.load(open("results/v4/tables_v4.json"))
FZ = json.load(open("results/v4/frozen.json"))
KEYS = ["qwen", "smol", "pythia"]
NAMES = {"qwen": "Qwen2.5-0.5B", "smol": "SmolLM2-360M", "pythia": "pythia-410m"}
TASKS = ["role", "negation", "uncertainty", "order", "maths_signed"]
CONDS = [
    ("none", "no injection"),
    ("text_prose", "prose text"),
    ("text_compact", "compact text"),
    ("text_bag", "bag-of-words text"),
    ("text_compact_of_choice", "compact of chosen slots"),
    ("glyph_id", "glyph ID path"),
    ("glyph_vec", "glyph vector path"),
    ("glyph_raw_unsnapped", "raw unsnapped"),
    ("receiver_word_state", "receiver word-state oracle"),
    ("glyph_slot_shuffled", "slot-shuffled glyph"),
    ("glyph_samenorm_shuffled", "same-norm shuffled"),
    ("ablation_nofilter_vec", "ablation: nofilter book"),
    ("ablation_twomodel_vec", "ablation: two-model book"),
]

def cell(key):
    x = T["acc"].get(key)
    if not x: return "-"
    return f"{x[0]:.3f}"

def pooled(rk, sk, c):
    x = T["acc_pooled"].get(f"{rk}|{sk}|{c}")
    if not x: return None
    return x  # [mean, lo, hi, n]

lines = []
a = lines.append
a("# Glyph experiment v4: three-party repository (composition, deliveries, costs)")
a("")
a(f"**Run:** {time.strftime('%d %b %Y, %Z')} (Australia/Sydney box clock).")
a("- Models: Qwen2.5-0.5B, SmolLM2-360M, EleutherAI/pythia-410m. One model loaded at a time.")
a("- Pythia used raw mid-layer states (no J-lens). Qwen and Smol reused the v1 fitted lenses.")
a(f"- Frozen layer fraction: FRACS[{FZ['li']}] (see `results/v4/frozen.json`). Layer map: {json.dumps(T.get('layer'))}.")
a(f"- Book version: {T.get('book_version')}, entries: {T.get('n_entries')}.")
a(f"- Dev note (layer pick): {FZ.get('note', '')}")
a("")
a("Every number below is in `results/v4/*.json`. Tables JSON: `results/v4/tables_v4.json`.")
a("")
a("## What v4 measures")
a("- Three-party negotiated book (all three models agree on entries).")
a("- Unseen compositions and signed subtraction order (7−2 vs 2−7).")
a("- Separate sender selection (snap) accuracy, transfer fidelity, and ID vs float32 vector delivery.")
a("- Cost vs terse text (`text_compact` / prose / bag).")
a("- Slot-shuffle and same-norm shuffle controls; nofilter and two-model ablations.")
a("")
a("## Pooled accuracy (all tasks, mean [95% bootstrap CI])")
a("")
a("| receiver | sender | condition | mean | lo | hi | n |")
a("|---|---|---|---|---|---|---|")
for rk in KEYS:
    for sk in ["-"] + KEYS:
        for c, _ in CONDS:
            x = pooled(rk, sk, c)
            if not x: continue
            a(f"| {NAMES[rk]} | {sk if sk!='-' else '-'} | {c} | {x[0]:.3f} | {x[1]:.3f} | {x[2]:.3f} | {x[3]} |")
a("")
a("## Accuracy by task (glyph_vec and text_compact)")
a("")
a("| receiver | sender | condition | " + " | ".join(TASKS) + " |")
a("|---|---|---|" + "|".join(["---"] * len(TASKS)) + "|")
for rk in KEYS:
    for sk in KEYS:
        for c in ("glyph_vec", "glyph_id", "text_compact", "text_prose", "none"):
            cells = [cell(f"{rk}|{sk}|{c}|{t}") for t in TASKS]
            if all(x == "-" for x in cells): continue
            a(f"| {rk} | {sk} | {c} | " + " | ".join(cells) + " |")
    # text/none often have sender "-"
    for c in ("text_compact", "text_prose", "text_bag", "none"):
        cells = [cell(f"{rk}|-|{c}|{t}") for t in TASKS]
        if all(x == "-" for x in cells): continue
        a(f"| {rk} | - | {c} | " + " | ".join(cells) + " |")
a("")
a("## Snap accuracy (sender selection into the book)")
a("```")
a(json.dumps(T.get("snap_acc"), indent=1)[:4000])
a("```")
a("")
a("## ID vs vector delivery")
a("```")
a(json.dumps(T.get("id_vs_vec"), indent=1)[:3000])
a("```")
a("")
a("## Maths swap pairs (both 7−2 and 2−7 correct)")
a("```")
a(json.dumps(T.get("maths_swap_pair_both_correct"), indent=1)[:4000])
a("```")
a("")
a("## Slot-shuffled follows (answer changes only)")
a("```")
a(json.dumps(T.get("slot_shuffled_follows"), indent=1)[:4000])
a("```")
a("")
a("## Bytes / bits vs text")
a("```")
a(json.dumps(T.get("bytes"), indent=1)[:4000])
a("```")
a("")
a("## Runtime")
a("```")
a(json.dumps({"setup_s": T.get("setup_s"), "runtime_test_s": T.get("runtime_test_s"), "compute_median_ms": T.get("compute_median_ms")}, indent=1)[:5000])
a("```")
a("")
a("## Files")
a("- Code: `v4/`")
a("- Book + states: `results/v4/book.pt`, `states_*.pt` (in the release tarball, not the git tree)")
a("- Per-receiver tests: `results/v4/test_{qwen,smol,pythia}.json`")
a("- Aggregates: `results/v4/tables_v4.json`")
a("- Frozen layer choice: `results/v4/frozen.json`")
path = "RESULTS_v4.md"
open(path, "w").write("\n".join(lines) + "\n")
print("wrote", path, "lines", len(lines))
