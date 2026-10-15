# E1c D2 dev pilot: report (Amendment A1)

**Outcome: D2 `.done` (recorded outcome `done`, attempt 1, no retry) at 0.406 GPU-h of the 0.8 h cap. The T1 eligibility rule (PREREG §8, A1) is MET.**
Descriptive only; DEV book; no E1c verdict. Kaggle kernel `devamped13/e1c-stage-d2`, pushed once at commit `95de518` on Stefan's go. Outputs committed unchanged in `results/D2/` (with `results/budget_ledger.json`).

## 1. Run integrity
| Check | Result |
|---|---|
| Commit | `95de518` checked out (log: "switching to '95de518'"); `start` log `commit 95de5187…` |
| E1c code hash | `--check` printed `ecc8c8fc…428804a97 OK`; same hash in the attempt record and in the relabelled log field `e1c_code_hash` (A1 fix works; `e1b_code_hash 77eceb53…` is E1b's own pin) |
| Protocol hash | `6c642581…`: equal to the current one and to D1's |
| GPU | Tesla T4 (cc 7.5); GPU preflight PASS on all 3 loads (hf-nf4, 196 4-bit layers, params on cuda). No CPU fallback |
| Canaries | 20/20 on all 3 loads |
| Errors | none. Log noise only (pip resolver note for unused packages, library warnings) |
| Completion | child rc 0, CHILD_COMPLETE, exit before the deadline; supervisor wrote `summary.json`, `.done` and outcome `done`; `finished(D2)` = True |
| Stage time (ledger) | **1,461 s = 0.406 GPU-h of the 0.8 h cap** (Kaggle session ≈ 1,490 s incl. clone/pip). D1 + D2 dev total 0.794 GPU-h |
| D1 in the kernel | the `results/D1/` files shipped with the commit came back byte-identical (D1 untouched) |

**Estimate vs actual.** A1 estimated 1,980 s; actual 1,461 s (74%). Loads with canaries: 248 s, 261 s and 119 s (third load, warm cache), against 310 + 290 + 310 s assumed from D1. Send + verify + check: 156 s (Qwen) and 193 s (Falcon). Receivers: 229 s (Falcon) and 169 s (Qwen). The cap's margin was not needed.

## 2. Selection and verifier (160 entries per sender)
| | Qwen2.5-7B sender | Falcon3-7B sender |
|---|---|---|
| Sender pick accuracy | 147/160 = 91.9% | 156/160 = 97.5% |
| Sender invalid | 0 | 0 |
| **ID use rate (coverage)** | **146/160 = 91.25%** (F1 71/80, F2 75/80) | **152/160 = 95.0%** (F1 73/80, F2 79/80) |
| **Wrong pick accepted** | **0/160** (CP95 upper 1.85%) | **0/160** (CP95 upper 1.85%) |
| Wrong picks caught by the verifier | 13/13 | 4/4 |
| Correct pick rejected (needless fallback) | 1 (field mismatch) | 4 (3 verifier format failures, 1 field mismatch) |
| Verifier format OK | 160/160 | 157/160 |
| Verifier batch 8 vs batch 1 (16 entries) | 16/16 identical | 16/16 identical |

The wrong-pick-accepted screen (≤ 2%, i.e. ≤ 3/160) passes for both senders, and 0/160 also meets the "demonstrated ≤ 2%" bound (CP95 upper ≤ 2%) for both.

## 3. Exchanges (10 entries × 4 cases = 40 messages per direction)
| | Qwen → Falcon | Falcon → Qwen |
|---|---|---|
| Accuracy, hybrid (ID with prose fallback) | 40/40 | 40/40 |
| Accuracy, prose | 40/40 | 40/40 |
| Paired difference (95% CI) | 0.0 pts [0, 0], non-inferior | 0.0 pts [0, 0], non-inferior |
| ID use on the receiver entries | 8/10 = 80% (32 ID, 8 fallback) | 10/10 = 100% (40 ID) |
| Payload byte saving incl. fallback | 70.9% | 89.1% |
| Message saving (payload + case) | 46.8% | 58.7% |
| Dictionary break-even | ≈ 56 messages | ≈ 44 messages |
| TEST success checks (orientation only) | coverage fails (80% < 85%); others pass | all pass |

Receiver-side numbers rest on 10 entries per direction and are very noisy: Qwen's 80% receiver-subset coverage sits beside 91.25% on its full 160 selection entries. Both receivers score 100% on both arms, so D2 cannot separate the arms; that is TEST's job.

## 4. T1 eligibility (PREREG §8, qualifying stage D2 per A1)
| Criterion | Result |
|---|---|
| D2 `.done` + recorded `done`, no terminal marker | pass |
| Exact structure: both directions COMPLETE, 10 entries / 40 messages each; both senders 160 rows; conformance 16/16 | pass |
| Wrong-pick-accepted ≤ 2% for both senders | pass (0/160, 0/160) |
| Projected T1 ≤ T1 cap | pass: **3.66 GPU-h** ≤ 6.0 h placeholder (load 261 s; sender+verifier 2.14 s/entry; receiver 4.82 s/message; +25%) |
| Protocol hash = current | pass |

`stages.t1_eligibility` returns `(True, "ok")` on the committed results, and an independent recomputation of both direction results from the raw rows matches `summary.json` exactly.
**Verdict: T1 is ELIGIBLE.** Not yet startable: T1 still needs the freeze (status `frozen`, TEST book built and its sha pinned, the two freeze tags), the T1 cap set from D2 at freeze (projection 3.66 h), review, and Stefan's explicit go.

## 5. D1 vs D2 reproduction check (descriptive, non-gating; A1 §4)
Same protocol, book and greedy decoding, in separate Kaggle sessions:
- selection, both senders: 160/160 identical sender replies, picks, accept decisions and verifier replies (no differences at all);
- Qwen → Falcon exchange (the only direction D1 reached): 80/80 identical receiver replies and scores.
D1's partial results reproduce exactly.

## 6. Notes
- The A1 log-field fix worked (`e1b_code_hash` / `e1c_code_hash`).
- Falcon's 3 needless fallbacks are verifier format failures (`no_spec`), which cost bytes, not accuracy.

Falcon3-7B-Instruct results were produced using artificial intelligence technology from the Technology Innovation Institute (TII Falcon License).
