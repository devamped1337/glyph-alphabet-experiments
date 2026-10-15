# E1c T1 (TEST): report

**Frozen verdict: NOT MET.** Three of the four criteria pass in both directions. Criterion 4 (dictionary break-even ≤ 1,000 messages) **fails in both directions**: 1,142 messages (Qwen→Falcon) and 1,114 messages (Falcon→Qwen). Under PREREG_E1c §6, E1c succeeds only if all four pass in both directions, so the result is NOT MET. There is no choosing a direction and no post-hoc subset.

Kaggle kernel `devamped13/e1c-stage-t1`, pushed once on Stefan's explicit go at the frozen execution commit `aabad44` (tag `e1c-t1-exec`; registration tag `prereg-e1c` = 04b7285). Outputs are committed unchanged in `results/T1/`.

## 1. Run integrity
| Check | Result |
|---|---|
| Kaggle status | `KernelWorkerStatus.COMPLETE` |
| Commit | log: "HEAD is now at aabad44 … E1c EXECUTION"; `start` log `commit aabad44a95…` |
| E1c code hash | `--check` printed `6ee5e9a8…929f98ea OK`; same in the attempt record and in `e1c_code_hash` (E1b's own pin `77eceb53…` is logged separately as `e1b_code_hash`) |
| Protocol hash | `6c642581…` = the frozen protocol, = D2's |
| TEST book | sha256 of `data/book_test.json` = config pin = `32f3a7c0…f850e2` |
| GPU | Tesla T4 (cc 7.5); GPU preflight PASS on all 3 loads (hf-nf4, 196 4-bit layers, params on cuda); no CPU fallback |
| Canaries | 20/20 on all 3 loads |
| Errors | none (pip resolver note for unused packages; library warnings) |
| Completion | attempt 1, no retry; child rc 0 before the deadline; `summary.json`, `.done` and recorded outcome `done` (`finished(T1)` = True) |
| GPU time (ledger) | **11,604 s = 3.22 GPU-h of the 5.0 h cap** (D2 projection 3.66 h). Loads with canaries 240 s / 272 s / 128 s; send+verify 253 s (Qwen) and 311 s (Falcon); receivers 6,389 s (Falcon) and 3,982 s (Qwen) |
| Prior stages | `results/D1/` and `results/D2/` came back byte-identical |

**check_freeze** (run on the box against the pushed tags):
```
$ python tools/check_freeze.py prereg-e1c e1c-t1-exec
ok ok registration has no TEST book digest ok
(exit 0; prereg-e1c = 04b7285a6bd3f7c0ae2faff49e8b79e8f457611d, e1c-t1-exec = aabad44a9525e0b72248ed15d06d4458f4a21a23)
```
Disclosed earlier and accepted by GPT: a fake-backend dry run touched the TEST book before T1 (`FREEZE_NOTES_E1c.md`).

## 2. Primary results (240 entries × 4 cases = 960 messages per direction)
Paired bootstrap stratified by family and clustered by entry, 2,000 resamples, frozen seed (`seed_of(bootstrap seed, direction)`), percentiles s[50] and s[1949]; label rule A1.2, margin 0.05.

| Criterion | Qwen → Falcon | Falcon → Qwen | Threshold |
|---|---|---|---|
| Accuracy, hybrid (ID + fallback) | 960/960 = 100.0% | 958/960 = 99.79% | n/a |
| Accuracy, prose | 957/960 = 99.69% | 950/960 = 98.96% | n/a |
| Difference hybrid − prose (point) | +0.31 pts | +0.83 pts | n/a |
| **1. Lower 95% bound** | **0.000** (CI [0.000, +0.0083]), non-inferior: **pass** | **+0.0031** (CI [+0.0031, +0.0146]), non-inferior: **pass** | > −0.05 |
| **2. ID coverage** (accepted ÷ 240) | **223/240 = 92.9%**: **pass** | **229/240 = 95.4%**: **pass** | ≥ 85% |
| **3. Payload saving incl. fallback** | **83.2%**: **pass** | **85.3%**: **pass** | ≥ 30% |
| **4. Dictionary break-even** | **1,142 messages**: **FAIL** | **1,114 messages**: **FAIL** | ≤ 1,000 |
| All four | no | no | both directions |

Break-even inputs: dictionary 165,969 B (the 240 entries plus their neighbours, framed ID + text); mean payload saving per message 145.3 B (Qwen→Falcon) and 149.0 B (Falcon→Qwen). Message saving (payload + case, not a criterion): 54.9% and 56.3%.

## 3. Secondary (descriptive)
| | Qwen sender | Falcon sender |
|---|---|---|
| Pick accuracy | 226/240 = 94.2% | 230/240 = 95.8% |
| Sender invalid | 0 | 0 |
| Verifier format OK | 240/240 | 239/240 |
| **Wrong pick accepted** | **0/240** (CP95 upper 1.24%) | **0/240** (CP95 upper 1.24%) |
| Wrong picks caught | 14/14 (swap 10, shift 2, swap+shift 2) | 10/10 (swap 5, shift 5) |
| Correct pick rejected | 3 | 1 |
| Coverage by family | F1 109/120, F2 114/120 | F1 112/120, F2 117/120 |

- **Per family** (hybrid vs prose correct): Qwen→Falcon F1 480/480 vs 480/480, F2 480/480 vs 477/480. Falcon→Qwen F1 480/480 vs 480/480, F2 478/480 vs 470/480.
- **ID-sent subset** (accepted, all correct picks): Qwen→Falcon 892/892 hybrid vs 889/892 prose; Falcon→Qwen 915/916 vs 907/916. **Fallback subset:** 68/68 and 43/44, identical to prose by construction.
- No accepted wrong pick reached a receiver in either direction.

## 4. Independent recomputation
From the raw rows (`select_*.jsonl`, `exchange_*.jsonl`) and the TEST book:
- the frozen `direction_result` reproduces `summary.json` exactly for both directions, and `verdict()` returns NOT MET;
- a separate implementation re-checked:
  - completeness: 240 selection rows per sender, 1,920 exchange rows per direction, no duplicates, gold equal to the registered cases;
  - accuracies, coverage and wrong-pick counts;
  - payload bytes, re-derived from the book (framed ID of the picked entry, or prose of the true entry);
  - dictionary bytes and break-even, all identical;
- an independent bootstrap (numpy, 20,000 resamples, different RNG) gives 95% intervals [0.000, 0.0083] and [0.0021, 0.0146], consistent with the frozen [0.000, 0.0083] and [0.0031, 0.0146].

## 5. Notes
- **What fails is the dictionary cost, not accuracy or coverage.** Pre-registered break-even divides the bytes of the whole receiver dictionary (240 entries plus neighbours, 166 kB) by the per-message saving (≈ 146–149 B). The ID arm was at least as accurate as prose in both directions, with no accepted wrong IDs.
- **D2's break-even figures (56 and 44 messages) did not predict this.** The D2 dictionary held only its 10 receiver entries plus their neighbours (6.9 kB), so its break-even was not comparable to TEST's 240-entry dictionary. I reported those D2 figures, including in the forum update, without that caveat. That was a mistake in the reporting, not in the frozen rules.
- Receivers took longer than projected (Falcon side 6,389 s against ≈ 4,600 s); the total still came in under the projection and cap.

Falcon3-7B-Instruct results were produced using artificial intelligence technology from the Technology Innovation Institute (TII Falcon License).
