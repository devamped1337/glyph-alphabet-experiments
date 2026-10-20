# E1d D1-E1d dev stage: report

Kernel `devamped13/e1d-stage-d1` v1, code `f092214` (tag `e1d-dev-exec`), pushed once on 2026-10-20 at about 18:00 AEDT. Status COMPLETE; supervisor outcome `done` (rc 0), 1 attempt, no terminal marker.

## Compute
- Charged: **2,246 s = 0.624 GPU-h** of the 1.0 cap (supervised stage only; clone, pip and zip on Kaggle are outside it, as GPT noted).
- Loads (incl. canaries): qwen 246 s, falcon 268 s, qwen 137 s. Send+verify: 205 s / 250 s. Receivers: 566 s (Falcon) / 474 s (Qwen).
- Per unit: 2.60 s per entry for sender+verifier (summed over both senders), 5.74 s per receiver message (both arms); verifier batch-1 1.4 s per call.
- Pre-launch projection was 0.846 h; the actual 0.624 h is below it.

## Eligibility (tools/check_eligibility.py, post-run; results/D1-E1d/eligibility.json)
| Check | Value | Threshold | Pass |
|---|---|---|---|
| D1 completion | .done + recorded `done`, no marker | yes | yes |
| D2 structure | 172 selection rows per sender (160 + 12); receivers 40 + 48 messages per direction, both arms | exact | yes |
| D3 verifier batch 8 vs 1 | 16/16 identical (both models) | all | yes |
| D4 protocol hash | dev = current config | equal | yes |
| D5 TEST projection (+25%) | **2.97 GPU-h** | ≤ 4.0 | yes |
| D6 builder trials | 10/10 | ≥ 8 | yes |
| D7 (per pair, per sender) | D7a 4/4, D7b 4/4, D7c 16/16 for every pair and sender | 3, 3, 14 | yes |
| D8 per pair (prose ≥ 12/16; hyb − prose ≥ −2) | Q→F: 16/16, 16/16, 15/16 (diff 0, 0, +1); F→Q: 14, 16, 14 (diff +2, 0, +2) | | yes |
| D8 pooled (prose ≥ 36/48; diff ≥ −4) | Q→F 47 vs 48 hybrid; F→Q 44 vs 48 | | yes |
| Wrong-pick screen (reported only) | 0 accepted, both senders | n/a | n/a |

Outcome rule: **rule 1, dev-new qualified** (f = 0, pooled D8 passes). **Eligible for freeze: yes.** TEST still needs the freeze step, the TEST book built from seeds 95061–95066, and Stefan's go.

## Headline numbers (descriptive, dev)
- Selection accuracy (E1c dev 160 / dev-new 12): Qwen 91.9% / 75%; Falcon 97.5% / 100%. ID coverage: Qwen 91.3% / 75%; Falcon 95.0% / 100%.
- Wrong picks accepted: **0** in all groups. Caught by the verifier: Qwen 13 + 3, Falcon 4 + 0. Correct picks rejected: Qwen 1, Falcon 4.
- Receiver accuracy, hybrid vs prose: Q→F E1c subset 40/40 vs 40/40, dev-new 48/48 vs 47/48; F→Q E1c 40/40 vs 40/40, dev-new 48/48 vs 44/48.
- Per pair, dev-new (coverage; hybrid/prose correct of 16): Q→F baker/porter 0.75, 16/16; potter/bearer 0.50, 16/16; tanner/loader 1.0, 16/15. F→Q all 1.0; 16/14, 16/16, 16/14.
- Bytes (frozen serializer, case included): Q→F 166 vs 294 B per message (dev-new 174 vs 306); F→Q 127 vs 294 B. Payload-only saving: E1c subset 70.9% / 89.1%, dev-new 67.4% / 90.3%.
- Speed: receiver latency, hybrid vs prose: 3.31 vs 3.75 s (Falcon receiving), 2.60 vs 2.62 s (Qwen receiving); prompt tokens nearly equal, as expected.
- Illustrative only (dev artifact 120,030 B; TEST measures v1 at 80/family): S(W_base) lower bound on dev-new 0.183 (Q→F) and 0.437 (F→Q). This is not a gate.

## Things to note honestly
- Qwen as sender is the weak spot on the new pairs: potter/bearer coverage 2/4 and dev-new coverage 75%. On dev-new the Q→F illustrative G2 (75%) and G3 (0.183) would fail. The dev-new data are 12 entries (smoke test), so this is a warning for TEST G2/G3 in the Q→F direction, not a result.
- The in-child `eligibility_D2_D8` in summary.json shows `eligible_for_freeze: false` only because D1 is unknown inside the child (GPT note 1). The post-run evaluation above is authoritative.
- The kernel log has one benign pip dependency-resolver warning; no tracebacks.
