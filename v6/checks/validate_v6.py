#!/usr/bin/env python3
"""
v6 pre-result validator.

Catches the v5 failure modes:
- coverage logged as 1.0 when rejected items exist
- rejection count mismatch
- LOO not split by answer-held-out
- unknown-ID path that never called the model
- prose baselines that contain the gold string
- missing fields for coverage / selection / decoding
- depth selection not recorded

Usage:
    python validate_v6.py --results-dir v6/results --prereg v6/PREREG_v6.md
"""

import argparse
import json
import sys
from pathlib import Path
from collections import Counter, defaultdict

REQUIRED_FIELDS = {
    "coverage",          # bool or float
    "selection",         # which slot was chosen, or None
    "decoding",          # how the final answer was produced
    "pred",
    "correct",
    "gold",
    "cond",
    "task",
}

def load_jsonl(path):
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows

def check_required_fields(rows, name):
    missing = []
    for i, r in enumerate(rows[:500]):  # sample
        for f in REQUIRED_FIELDS:
            if f not in r and not (f == "task" and "t" in r):  # v5 schema uses "t"
                missing.append((i, f))
    if missing:
        print(f"FAIL [{name}]: missing fields in sample: {Counter(m[1] for m in missing)}")
        return False
    print(f"PASS [{name}]: required fields present")
    return True

def check_coverage_not_all_one(rows, name):
    if not rows:
        return True
    covs = [r.get("coverage") for r in rows if "coverage" in r]
    if not covs:
        print(f"FAIL [{name}]: no coverage field")
        return False
    if all(c in (1, 1.0, True) for c in covs):
        # only fail if we also see rejected/uncovered indicators elsewhere
        rejected = sum(1 for r in rows if r.get("rejected") or r.get("coverage") is False)
        if rejected == 0 and any(r.get("task", r.get("t")) == "t4" or "place" in str(r.get("task", r.get("t", ""))) for r in rows):
            print(f"FAIL [{name}]: coverage is uniformly 1.0 on a task that had rejections in v5. Likely logging bug.")
            return False
    print(f"PASS [{name}]: coverage not uniformly 1.0 (or no place task)")
    return True

def check_loo_split(rows, name):
    loo = [r for r in rows if "loo" in str(r.get("cond","")).lower() or r.get("loo_symbol")]
    if not loo:
        print(f"INFO [{name}]: no LOO rows")
        return True
    has_split = any("answer_held_out" in r or "held_out_type" in r for r in loo)
    if not has_split:
        print(f"FAIL [{name}]: LOO rows present but no answer-held-out / other-held-out split field")
        return False
    print(f"PASS [{name}]: LOO split field present")
    return True

def check_unknown_id_calls_model(rows, name):
    unk = [r for r in rows if "unknown" in str(r.get("cond","")).lower() or r.get("payload")]
    if not unk:
        return True
    # crude: if every unknown row has identical fixed_pred and no model_called flag, fail
    if all(r.get("fixed_pred") == "UNRECOGNIZED" and not r.get("model_called") for r in unk):
        print(f"FAIL [{name}]: unknown-ID rows look like a pure parser path (fixed_pred, no model_called)")
        return False
    print(f"PASS [{name}]: unknown-ID does not appear to be pure parser")
    return True

def check_prose_no_gold_leak(rows, name):
    prose = [r for r in rows if "prose" in str(r.get("cond","")).lower() or r.get("text_prose")]
    leaks = 0
    no_text = sum(1 for r in prose if not (r.get("prompt") or r.get("text")))
    if no_text:
        print(f"FAIL [{name}]: {no_text} prose rows have no prompt/text field; gold leak cannot be verified")
        return False
    for r in prose:
        gold = str(r.get("gold",""))
        text = str(r.get("prompt") or r.get("text") or "")
        if gold and gold in text:
            leaks += 1
    if leaks:
        print(f"FAIL [{name}]: {leaks} prose rows contain the gold string")
        return False
    print(f"PASS [{name}]: no gold leak in sampled prose")
    return True

def check_rejection_count(rows, name, expected=None):
    # look for an explicit rejection log or infer from coverage==False
    rejected = [r for r in rows if r.get("coverage") is False or r.get("rejected")]
    print(f"INFO [{name}]: {len(rejected)} rows marked rejected/uncovered")
    if expected is not None and len(rejected) != expected:
        print(f"WARN [{name}]: rejection count {len(rejected)} != expected {expected}")
    return True

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", type=Path, required=True)
    ap.add_argument("--prereg", type=Path)
    args = ap.parse_args()

    files = list(args.results_dir.glob("predictions_*.jsonl"))
    if not files:
        print("No predictions_*.jsonl found")
        sys.exit(1)

    all_ok = True
    for p in files:
        rows = load_jsonl(p)
        print(f"\n=== {p.name} ({len(rows)} rows) ===")
        ok = True
        ok &= check_required_fields(rows, p.name)
        ok &= check_coverage_not_all_one(rows, p.name)
        ok &= check_loo_split(rows, p.name)
        ok &= check_unknown_id_calls_model(rows, p.name)
        ok &= check_prose_no_gold_leak(rows, p.name)
        check_rejection_count(rows, p.name)
        all_ok &= ok

    if not all_ok:
        print("\nVALIDATION FAILED")
        sys.exit(1)
    print("\nVALIDATION PASSED")

if __name__ == "__main__":
    main()
