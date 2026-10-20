# E1d T1-E1d TEST stage: report

Kernel `devamped13/e1d-stage-t1` v1, code `4bcb1db` (tag `e1d-test-exec`; plan tag `prereg-e1d`), pushed once on 2026-10-20 at 20:23 AEDT. Status COMPLETE; supervisor outcome `done` (**rc 0**, log ends `exit 0`), 1 attempt, no terminal marker. Code hash `98a61092…` OK in the kernel; protocol hash `11d7af03…`.

## Verdict (frozen `analysis.verdict`, DRAFT_PLAN §9): **SUCCESS**
All three gates pass in both directions. Independent re-run of the frozen `stages.summarize_test` on the saved raw rows on the box (no GPU) reproduces `summary.json` **identically** (every key), verdict SUCCESS.

| Gate | What it counts | Qwen→Falcon | Falcon→Qwen | Bar |
|---|---|---|---|---|
| C completeness | 160 selection rows per sender; 160 entries × 4 cases = 640 messages per arm per direction | complete | complete | exact |
| G1 accuracy | receiver correct, hybrid − prose, over 640 paired messages; E1c paired bootstrap (family-stratified, entry-clustered), lower bound s[50] of 2,000 | 639/640 vs 636/640, **+0.47 pt**, 95% CI [0.00, +1.09] → non-inferior | 639/640 vs 629/640, **+1.56 pt**, CI [+0.63, +2.66] → non-inferior | lower > −5 pt |
| G2 coverage | entries whose ID the sender picked correctly *and* the verifier accepted, / 160 assigned | **139/160 = 86.9%** | **151/160 = 94.4%** | ≥ 85% |
| G3 total bytes vs prose, W_base | S = 1 − (F + M·(a·H + (1−a)·P)) / (M·P): share of total direction bytes (messages + this direction's share of dictionary sync) saved vs all-prose; one-sided 95% lower bound s[500] of 10,000 entry bootstraps, F fixed | point **35.6%**, lower **33.3%** | point **39.6%**, lower **38.3%** | lower > 20% |

G3 inputs (W_base): M = 90,000 messages per direction over 90 days; a = 0.89 (share of messages that may use an ID); P = 279.7 B, mean serialized prose message (case + payload, frozen serializer, family-weighted); H = 144.1 B (Q→F) / 131.5 B (F→Q), mean hybrid message incl. fallback prose; F = 1,903,172 B (half of 3,806,343 B total sync: initial full copies to 20 + 6 joiners and 12 weekly deltas of 2,764 B, from the measured v1 artifact). Q→F is the weaker direction because its coverage is lower (more fallback prose in H).

## Compute
- Charged (supervised stage): **8,420 s = 2.34 GPU-h** of the 4.0 cap (ledger `results/budget_ledger.json`). Pre-launch projection 2.97 h. Kernel wall time ≈ 8,454 s incl. clone/pip/zip.
- Loads 241 / 275 / 117 s; send+verify 184 s (Qwen) / 223 s (Falcon); receivers 4,413 s (Falcon) / 2,874 s (Qwen).
- Canaries 20/20 for every load; GPU preflight passed (T4, nf4, 196 4-bit layers) each time. Log: one benign pip resolver warning, no tracebacks.

## Dictionary artifact v1 (measured in the run; equals the pin)
110,651 B (117 B manifest + 110,534 B body), 640 entries, 160 core; sha256 `eb83e299…`. gzip-9: 9,986 B (ratio 0.0902).

## Sender side (selection; reported)
| | Qwen sender | Falcon sender |
|---|---|---|
| Pick accuracy (correct entry chosen) | 139/160 = 86.9% | 153/160 = 95.6% |
| Coverage (correct and accepted) | 139/160 = 86.9% | 151/160 = 94.4% |
| **Wrong IDs accepted** (reported only, no gate) | **0/160** (CP95 upper 1.85%) | **0/160** (CP95 upper 1.85%) |
| Wrong picks caught by verifier | 21 | 7 |
| Correct picks rejected | 0 | 2 |
| Sender invalid / verifier format OK | 0 / 100% | 0 / 99.4% |

No wrong ID reached a receiver in either direction.

## Sensitivity scenarios (reported, not gated; S lower bound / point)
| Scenario | What changes vs W_base | Q→F | F→Q |
|---|---|---|---|
| W_base (gate) | — | 33.3% / 35.6% | 38.3% / 39.6% |
| W_copy | 6 agents; full copies for initial holders and replacement joiners plus two incremental deltas (11,054 B body + manifest each), F counted fully: F = 1,185,415 B | 36.2% / 38.4% | 41.2% / 42.5% |
| W_low | traffic ÷ 4 (M = 22,500) | **10.6% / 12.9%** | **15.6% / 16.9%** |
| W_churn | twice the joiners, 29 deltas every 3 days, a = 0.88 | 30.6% / 32.8% | 35.5% / 36.8% |
| W_low_churn | both | **1.0% / 3.3%** | **6.0% / 7.3%** |

Minimum traffic (W_base shape) at which the lower bound clears 20%: **33,300** messages per direction (Q→F) and **27,000** per direction (F→Q) over 90 days (aggregate 66,600 and 54,000 across both directions; minima on the planned 1,800-message aggregate grid). Below roughly that, sync cost erases the bar; W_low and W_low_churn would not meet it.

## Compressed baseline (gzip-9, secondary, §11)
Primary claim is limited to plain, uncompressed prose. With both arms gzip-9 per message (mtime 0), mean P = 190.1 B, H = 139.1 / 134.5 B.
| | Q→F lower / point | F→Q lower / point |
|---|---|---|
| Frozen secondary (`lifetime_gzip9_secondary`; sync F **uncompressed**) | 11.5% / 12.7% | 14.1% / 14.9% |
| Reporting-only: sync F × measured v1 gzip ratio 0.0902 (GPT note 1; `results/T1-E1d/gzip_sync_reporting.json`; later full copies and deltas are assumed to compress like v1, not individually measured) | **21.6% / 22.9%** | **24.3% / 25.0%** |

W_low with compressed sync: 18.6% / 21.2% lower bounds; W_low_churn 17.1% / 19.7%. Against a gzip baseline the dictionary still saves bytes at W_base, but the margin over 20% is thin (Q→F 1.6 pt) and depends on also compressing sync traffic, under the assumption that later full copies and deltas compress like v1 (ratio 0.0902); that was estimated, not measured.

## Per role pair (§10; reported, not gated; small denominators)
Coverage = correct-and-accepted / entries; correct = receiver answers, hybrid vs prose, of 4 cases per entry.
| Group | Q→F coverage | Q→F hybrid vs prose | F→Q coverage | F→Q hybrid vs prose | Bytes hyb / prose (Q→F; F→Q) | Wrong IDs accepted (Q→F; F→Q), CP95 upper |
|---|---|---|---|---|---|---|
| baker/porter (new) | 21/26 | 103/104 vs 102/104 | 26/26 | 104/104 vs 102/104 | 163/305; 129/305 | 0; 0 (10.9%) |
| **potter/bearer (new)** | **28/30 = 93.3%** | **120/120 vs 119/120** | **30/30** | **120/120 vs 119/120** | 141/306; 130/306 | 0; 0 (9.5%) |
| tanner/loader (new) | 21/24 | 96/96 vs 95/96 | 24/24 | 96/96 vs 89/96 | 151/307; 130/307 | 0; 0 (11.7%) |
| F2 new pooled | 70/80 = 87.5% | 319/320 vs 316/320 | 80/80 | 320/320 vs 310/320 | 151/306; 129/306 | 0; 0 |
| F1 | 69/80 = 86.3% | 320/320 vs 320/320 | 71/80 = 88.8% | 319/320 vs 319/320 | 137/254; 134/254 | 0; 0 |
| F2 old pairs, **from E1c T1** (`v6/e1c/T1_REPORT.md` §3; 120 entries, 480 messages; different book and artifact) | 114/120 = 95.0% | 480/480 vs 477/480 | 117/120 = 97.5% | 478/480 vs 470/480 | n/a | n/a |

Potter/bearer, the dev weak spot (Qwen coverage 2/4 in D1), is fine on TEST: 28/30 coverage for Qwen and 30/30 for Falcon. The in-run `F2_old_pairs` field is `n/a` by design (E1d TEST has only new F2 pairs); the old-pair row above is the E1c T1 reference.

## Other secondary
- E1c-style secondary (reported only): payload saving 77.7% (Q→F) / 84.9% (F→Q); break-even 815 / 746 messages against the 110,534 B body (E1c T1 failed its 1,000-message bar with 166 kB; here it would pass).
- Message saving (payload + case): 51.2% / 56.0%.
- Speed (shared T4, batch-level, descriptive): receiver latency hybrid vs prose 3.43 vs 3.78 s (Falcon receiving), 2.19 vs 2.28 s (Qwen receiving); sender 0.49 / 0.70 s, verifier 0.64 / 0.67 s per entry.

## Things to note honestly
- Q→F coverage 86.9% is only 1.9 points above the 85% G2 bar (Qwen pick accuracy 86.9%, below E1c T1's 94.2%). The gate passes, but this is the closest margin of the run.
- G3 is conditional on the W scenario; at a quarter of the traffic (W_low) it would fail in both directions. The interval covers entry sampling only and does not validate W.
- The claim is against plain prose. Against gzip-9 prose the saving is ~12–15% with uncompressed sync, ~22–25% with gzip'd sync (reporting only).
- Wrong IDs: 0 accepted in 320 selections; no gate (Stefan's decision).

## Files
`results/T1-E1d/` = the full Kaggle output (summary.json, raw select/exchange rows, artifact `dict_v1.e1d`, logs; `kaggle_log.json` = kernel log) + `gzip_sync_reporting.json` (box, reporting only).
