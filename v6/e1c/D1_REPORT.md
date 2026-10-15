# E1c D1 dev pilot: report

**Outcome: BUDGET_EXHAUSTED (terminal). D1 is not `.done`; under PREREG_E1c §7–§8, T1 is NOT eligible.**
Descriptive only; DEV book; no E1c verdict. Kaggle kernel `devamped13/e1c-stage-d1`, pushed once at commit `dffaa41`.

## 1. Run integrity
| Check | Result |
|---|---|
| Commit | `dffaa41` checked out (log: "switching to 'dffaa41'") |
| E1c code hash | `--check` printed `5a377730…62fa5d2 OK`; same hash in the attempt record and in `CODE_HASH.txt` at dffaa41 |
| Protocol hash | `6c642581…`, equal to the current `protocol_hash(X, cfg)` |
| GPU | Tesla T4 (cc 7.5); GPU preflight PASS for both models (hf-nf4, 196 4-bit layers, params on cuda). No CPU fallback |
| Models | Qwen/Qwen2.5-7B-Instruct @a09a3545, tiiuae/Falcon3-7B-Instruct @1e57a0ec |
| Canaries | 20/20 both models |
| Errors | none in the stage. Log noise only: pip resolver note (gradio/diffusers vs huggingface-hub 0.36.2, unused packages), bitsandbytes/transformers/nbconvert warnings |
| Attempts | 1 (first), no retry; outcome `budget_admission`, child rc 3, supervisor exit 3; marker BUDGET_EXHAUSTED |
| Stage time (ledger) | **1,396 s = 0.388 GPU-h of the 0.5 h cap** (Kaggle session ≈ 1,430 s incl. clone/pip) |

**Why it stopped.** After Qwen send+verify, Falcon send+verify and the Qwen→Falcon receiver arm, the next unit was the third load (Qwen, to receive Falcon's messages). Its admission estimate (420 s prior; observed loads incl. canaries 310 s and 289 s) would have crossed the 1,800 s deadline (1,396 + 420 > 1,800), so the child exited 3 as registered. Even at the observed load time (~310 s) plus the Qwen-side receiver work (~270 s, same as the Falcon side), the stage would have needed ≈ 1,980 s, over the cap. The PREREG estimate (≈ 1,500 s, 0.42 h) was too low: loads alone took ≈ 600 s for two (estimate 750 s for three), and send+verify+b1 check took ≈ 225 s (Qwen) and ≈ 270 s (Falcon).

**Missing:** the Falcon→Qwen direction (no `exchange_falcon7b_to_qwen7b.jsonl`), and therefore no `summary.json` / sizing record.

## 2. Selection and verifier (complete, 160 entries per sender)
| | Qwen2.5-7B sender | Falcon3-7B sender |
|---|---|---|
| Sender pick accuracy | 147/160 = 91.9% | 156/160 = 97.5% |
| Sender invalid (no letter) | 0 | 0 |
| **ID use rate (accepted = coverage)** | **146/160 = 91.25%** (F1 71/80, F2 75/80) | **152/160 = 95.0%** (F1 73/80, F2 79/80) |
| **Wrong pick accepted** | **0/160** (CP95 upper 1.85%) | **0/160** (CP95 upper 1.85%) |
| Wrong picks caught by the verifier | 13/13 (swap 6, shift 5, swap+shift 2) | 4/4 (swap 2, swap+shift 2) |
| Correct pick rejected (needless fallback) | 1 | 4 (3 of them verifier format failures) |
| Verifier format OK | 160/160 | 157/160 |
| Verifier batch 8 vs batch 1 (16 entries) | 16/16 identical | 16/16 identical |

The wrong-pick-accepted screen (≤ 2%, i.e. ≤ 3 of 160) **passes for both senders**. 0/160 also meets the stronger "demonstrated ≤ 2%" bound (CP95 upper 1.86% ≤ 2%).

## 3. Exchange, Qwen → Falcon (complete; 10 entries × 4 cases = 40 messages)
| | Value |
|---|---|
| Accuracy, hybrid (ID arm with fallback) | 40/40 = 100% |
| Accuracy, prose | 40/40 = 100% |
| Paired difference (bootstrap 95% CI) | 0.0 pts [0, 0], label "non-inferior" |
| ID use rate on these 10 receiver entries | 8/10 = 80% (32 ID messages, 8 fallback) |
| Payload byte saving incl. fallback | 70.9% |
| Message saving (payload + case) | 46.8% |
| Dictionary break-even | ≈ 56 messages (dictionary 6,916 B, 123.8 B saved per message) |
| Success checks (TEST rules, shown for orientation only) | non-inferiority yes, bytes yes, break-even yes, **coverage no (80% < 85%)** |

With only 10 receiver entries, the receiver-side numbers are very noisy: the 80% coverage here sits beside 91.25% on the full 160-entry selection set for the same sender. The receiver is 100% on both arms, so this subset cannot tell the arms apart.

## 4. Falcon → Qwen
Not run (budget stop before the third load). Selection-level data for the Falcon sender are complete (Section 2); there are no receiver results.

## 5. T1 go/no-go (PREREG §8)
| Criterion | Result |
|---|---|
| D1 `.done` with a recorded `done` outcome, no terminal marker | **FAIL**: BUDGET_EXHAUSTED |
| Exact structure: both directions COMPLETE (10 entries, 40 messages each) | **FAIL**: Falcon→Qwen missing |
| Both senders complete, 160 rows | pass |
| Conformance batch 8 = batch 1 (16/16 each) | pass |
| Current protocol hash | pass |
| Wrong-pick-accepted screen ≤ 2% both senders | pass (0/160, 0/160) |
| Projected T1 ≤ T1 cap | not computed by the stage. Informal estimate from the persisted rows (Qwen→Falcon receiver costs only): ≈ 4.9 GPU-h, under the 6.0 h placeholder |

**Verdict: T1 is NOT eligible.** D1 ended BUDGET_EXHAUSTED, which is terminal under §7 (no retry: it is not an infrastructure failure). Every measured screen passed, but the stage did not complete. Proceeding needs an amendment (for example, a new dev stage with a larger cap, or a cheaper load order), with its own review and Stefan's go.

## 6. Notes
- The E1b `start` log line shows `code_hash 77eceb53…`. That field is filled by E1b's `env_info`, which reads E1b's own `CODE_HASH.txt`; it is not the E1c hash. The E1c hash check is the `--check` line and the attempt record (both `5a377730…`).
- Ledger 1,396 s = attempt elapsed (monotonic); `finalise_s` 0.015 s.

Falcon3-7B-Instruct results were produced using artificial intelligence technology from the Technology Innovation Institute (TII Falcon License).
