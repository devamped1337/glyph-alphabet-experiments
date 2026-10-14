# E1b Stage B1 report (A9 post-hoc follow-up)

**Status:** VALID, complete. This run is a gate measurement only; it does not test the POC success criterion.
**Kernel:** `devamped13/e1b-stage-b1` v1 (COMPLETE). Ran 16:57–18:15 AEDT, 2026-10-14. Starts used: 1 of 2.
**Pinned:** tag `prereg-e1b-a9` (`b2ec2f3`), `CODE_HASH` `d0203f22…`. Only `results/` was overlaid from `ad7b313` (B1c PASS), which A9's stage order requires; the code is identical to the tag.
**Pair:** qwen7b + falcon7b (A8 post-hoc). The primary B0 result stays `NO_QUALIFYING_PAIR`.
**Level:** L4 (C60, 4 cases/entry, no F3L), batch 8 (from B1c).

Falcon3-7B-Instruct results were produced using artificial intelligence technology from the Technology Innovation Institute (TII Falcon License).

## Validity

| Check | Result |
| --- | --- |
| GPU preflight | PASS for both models (Tesla T4, `hf-nf4`, params on CUDA; no CPU fallback) |
| Canaries | qwen7b 20/20, falcon7b 20/20 |
| Item counts | 6336 calibration + 2400 TEST-gate probes per model = 8736, which matches the A9 plan (17,472 pair probes); manipulation check 120/120 |
| Uniqueness / missing | all keys unique, nothing missing |
| Parsing | probes 100% `letter` (0 unparsed); manipulation check 119 `answer_line`, 1 `last_integer` |
| Gold labels | every probe row's `gold`/`honest_gold` matches `cases_e1b_a9.json` (0 mismatches) |
| Truncation | probes 1–4 tokens; manipulation check: 1/120 hit the 192-token limit (a gold-unchanged row, not scored; parsed correctly) |
| Budget | cap 3.20 h; used **1.30 h** (`A9_B1` 4682.9 s); A9 total so far 1.74 / 12.0 h |
| Validator | PASSED (0 FAIL / WARN) |

**Why it was fast:** the projection was conservative. Measured probe latency at batch 8 was 0.16 s/call (Qwen) and 0.23 s/call (Falcon), against the projected pilot 0.365 s plus Falcon's B0x figure. The manipulation check took 0.20 h. Nothing was skipped.

## Results (descriptive; gate dropped for B2/B3 per A9)

- **Calibration eligibility (bar: honest ≥ 0.80 and planted rejection ≥ 0.90):** honest acceptance 26/60 = 0.433 (lower 95% bound 0.316), **not met**. Planted rejection 24/24 = 1.000 (lower bound 0.862). So `eligible: false`, as A9 expected; B2/B3 run ungated, with no checked-repository claim. The accepted list has 114 entries in total (calibration plus neighbour entries), and 90/180 neighbours were accepted.
- **TEST-gate vs repository target (honest ≥ 0.90 and planted rejection ≥ 0.95):** honest 32/60 = 0.533, **not met**. Planted rejection 39/40 = 0.975, met in sample (lower bound 0.871). By type: dropped_clause 10/10, inverted_comparison 10/10, swapped_roles 10/10, near_miss_polarity 9/10.
- **Probe accuracy vs `honest_gold`, honest entries** (calibration | TEST-gate):
  - qwen7b F1: mem 1.000 | 1.000, non 0.995 | 1.000, unstated 0.998 | 1.000, higher 0.743 | 0.720, lower 0.623 | 0.520
  - qwen7b F2: xr 0.990 | 1.000, yr 0.915 | 0.960, unstated 1.000 | 1.000, higher 0.835 | 0.907, lower 0.808 | 0.853
  - falcon7b F1: mem 1.000 | 1.000, non 0.997 | 1.000, unstated 0.973 | 0.958, higher 0.797 | 0.733, lower 0.802 | 0.793
  - falcon7b F2: xr 1.000 | 0.987, yr 1.000 | 0.993, unstated 0.879 | 0.925, higher 0.915 | 0.967, lower 0.862 | 0.947
  - Overall with-text (honest + planted): qwen 0.851 / 0.722, falcon 0.888 / 0.744.
  - The comparison probes ("higher" / "lower") are the weak path, mostly in F1, and they drive the honest-acceptance failures.
- **Manipulation check (falcon7b, 111 gold-changing cases):** it follows the planted text 0.378 of the time. By type: changed_constant 40/40, mismatched_definition 1/40, deleted_negation 1/31. Falcon nearly always applies a shown rule that is mismatched or has lost its negation, instead of answering UNKNOWN. This is a diagnostic (A5), not a bar.

## Next
B2 (cap 6.40 GPU-h, ungated). Launch only on Stefan's explicit go (`E1B_GO=B2`).
