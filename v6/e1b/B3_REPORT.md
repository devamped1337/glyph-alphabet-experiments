# E1b Stage B3 report (A9 post-hoc follow-up)

**Status:** VALID execution, complete. **Pre-registered verdict (§10): POC FAILED.** The point estimate is below −0.05 in both receiver directions. A caveat on the Falcon→Qwen direction follows below; it does not change the verdict.
**Kernel:** `devamped13/e1b-stage-b3` v1 (COMPLETE). Ran 05:21–06:13 AEDT, 2026-10-15. Starts used: 1 of 2.
**Pinned:** tag `prereg-e1b-a9` (`b2ec2f3`), `CODE_HASH` `d0203f22…`. The `results/` overlay came from `4cbce67`; the code is identical to the tag.
**Pair:** qwen7b + falcon7b (A8 post-hoc). The primary B0 result stays `NO_QUALIFYING_PAIR`. Ungated (gate dropped post hoc by the PI; this is not a checked repository).
**Level:** L4 (C60: 60 core TEST entries, 4 cases each, no F3L), batch 8.

Falcon3-7B-Instruct results were produced using artificial intelligence technology from the Technology Innovation Institute (TII Falcon License).

## Validity

| Check | Result |
| --- | --- |
| GPU preflight | PASS on all 4 model loads (Tesla T4, `hf-nf4`, CUDA; no CPU fallback) |
| Canaries | qwen7b 20/20, falcon7b 20/20 |
| Item counts | sender selection 60 per model (120, matching the A9 plan); exchanges 480 per direction (240 id_selected + 240 prose; 960, matching the plan) |
| Gold labels | all 960 exchange rows match `cases_e1b_a9.json` (0 mismatches, 0 not in book) |
| Parsing (receivers) | all called rows `answer_line`; 0 unparsed |
| Truncation | 0 receiver rows at the 192-token cap |
| Budget | cap 1.75 h; used **0.87 h** (`A9_B3` 3138.3 s) |
| Validator | PASSED (0 FAIL / WARN) on Kaggle and locally |

## Results (pre-registered)

**Qwen sends → Falcon receives**
- Sender selection 51/60 = **0.85** (CI 0.75–0.93). Chance is 0.25 and the best baseline (regex) scores 0.75; the sender beats it by +0.10 (CI 0.02–0.18), so the secondary claim is **met**.
- Avoidance of neighbour candidates: 0.90 for swapped, 0.98 for shifted, 0.97 for both. Selection was weak on derived (0.50) and spelled (0.63) message styles.
- Pipeline accuracy: id_selected **0.846** vs prose **1.000**. The difference is **−0.154 (CI −0.25 to −0.07): inferior**. By family (descriptive): F1 −0.23, F2 −0.08.
- When the selection was correct, the receiver was right on 203/204 items. Every loss comes from the 9 wrong selections (0/36 items correct).
- Bytes: payload −89%, whole exchange −59%. The ≥30% target is met; that saving is near-guaranteed by design.

**Falcon sends → Qwen receives**
- Under the frozen parser (§6, A1.5), sender selection is **0/60**: all 60 replies were `invalid_multiple`. So id_selected scores **0.000** vs prose **0.992**, a difference of **−0.99: inferior**.
- **Caveat (exploratory, post hoc, not a result):** Falcon answered every item as "X) F1" or "X) F2". It echoes the start of the candidate ID and is then cut off at the 4-token sender limit.
  - The frozen rule rejects the reply because it treats the standalone "F" in "F1" as a second letter.
  - Re-parsed by first letter, Falcon's picks would be 56/60 = 0.93 correct.
  - Because no Falcon pick was valid, the receiver was never called on id_selected, so this direction tests nothing about communication.
  - The sender format was pilot-tested on Qwen only. Neither B0x nor B1c exercised Falcon on the sender prompt. That gap is ours.
  - The pre-registered verdict stands. Any re-run with a fixed parser needs a new amendment.

**POC success (§10) needs (i) non-inferiority in both directions, (ii) ≥30% byte saving and (iii) all costs reported.** (ii) and (iii) are met. (i) fails in both directions, so the verdict is **FAILED**.

## E1b A9 GPU-h
B1c 0.44 + B1 1.30 + B2 3.53 + B3 0.87 = **6.15 / 12.0 GPU-h**.
