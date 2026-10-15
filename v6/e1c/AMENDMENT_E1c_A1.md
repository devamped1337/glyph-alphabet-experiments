# E1c Amendment A1: new dev stage D2 after D1 ran out of budget

Date: 2026-10-15. Status: DRAFT (needs review, then Stefan's explicit go before any D2 push).
Applies to: `PREREG_E1c.md` (DRAFT, r6). Evidence: `D1_REPORT.md` (commit dd83b26); D1 outputs committed unchanged in `results/D1/`; Grok's comment on D1, `reviews/grok_D1_comment.md`.

## 1. What went wrong
The D1 cap (0.5 GPU-h) rested on an **assumed** time of about 0.42 h (≈ 1,500 s). I did not measure the per-load time first; I extrapolated from E1b logs. The registered load order needs three model loads (Qwen, Falcon, Qwen), each with canaries. On the T4 they took 310 s (Qwen) and 290 s (Falcon), so three loads plus the work between them did not fit. After 1,396 s the admission guard refused the third load (420 s estimate would cross the 1,800 s deadline) and the stage ended **BUDGET_EXHAUSTED**, exactly as registered. The mistake is mine: the cap was set from an estimate, not a measurement. Grok's review of D1 (`reviews/grok_D1_comment.md`) says the same: "The incomplete run is on the time estimate. Next one needs the loads measured, not guessed."

## 2. D1 stays as recorded
- D1 is **terminal BUDGET_EXHAUSTED** (attempt 1, outcome `budget_admission`, 0.388 GPU-h). Nothing in `results/D1/` is edited, re-run, retried or reinterpreted. `closed_stages: ["D1"]` makes the supervisor refuse any further D1 start (exit 20).
- D1's partial results (both selection sets complete; Qwen→Falcon exchange; no Falcon→Qwen) are **diagnostics only**. They gate nothing, are not pooled with D2, and are not used for T1 eligibility or sizing. The only use of D1 in this amendment is its **timings**, to set D2's cap.

## 3. D2: a dev stage that uses measured times
**Same as D1:** protocol and protocol hash, dev book (sha pinned), sizes (160 selection entries per sender, 10 receiver entries per direction × 4 cases × 2 arms), verifier batch-1 check, admission guard, supervisor, retry rules, outputs. Only the name, the cap and the load-order rationale change.

**Load order.** D2 keeps the registered sequential order Qwen (send + verify + check) → Falcon (send + verify + check, receive Qwen→Falcon) → Qwen (receive Falcon→Qwen). Three loads is the **minimum for one model on the GPU at a time**: each model's receiver role depends on the *other* model's sender output, so "each model loaded once" requires both 7B models resident together on the 15 GB T4. Two NF4 7B models (≈ 5–6 GB each plus KV cache and batch-8 activations) might fit, but that was **never measured**, and an OOM would be a new failure mode. Taking the lesson of D1 ("measure, don't assume"), D2 uses the order whose every segment was measured in D1. Co-residency is noted as a possible later saving, only after it has been measured.

**Measured D1 segments**, the figures Grok cites (loads ≈ 600 s for two models: 310 + 290; send + verify 224–270 s per model) (seconds from the attempt start, `results/D1/stage_log.jsonl`):

| Segment | Measured |
|---|---|
| Child start-up | 20 |
| Qwen load + canaries | 310 |
| Qwen send + verify + batch-1 check | 224 |
| Free + Falcon load + canaries | 290 |
| Falcon send + verify + batch-1 check | 270 |
| Falcon receives Qwen→Falcon (40 msgs × 2 arms) | 273 |
| *not reached:* Qwen load + canaries | 310 (= the measured Qwen load) |
| *not reached:* Qwen receives Falcon→Qwen | 273 (= the measured mirror segment) |
| Summary and finalisation | ≈ 10 |
| **Estimate** | **1,980 s = 0.55 GPU-h** |

**Cap: 0.8 GPU-h = 2,880 s**, i.e. 900 s (45%) above the estimate. Checks:
- if all three loads take the 420 s admission prior instead of ≈ 300 s (+330 s) **and** all generation is 25% slower (+260 s): 2,570 s, still under 2,880 s;
- at the third load the admission guard would see ≈ 1,400 s used + 420 s, about 1,000 s below the deadline;
- two of the eight segments are not measured directly (the third Qwen load, likely faster with a warm cache, and the Qwen receiver); both are taken at their measured counterparts.

Cumulative dev compute: D1 0.388 h + D2 ≤ 0.8 h ≤ 1.19 GPU-h, all on the free T4 tier. Kaggle set-up time (clone + pip, ≈ 30 s in D1) is outside the stage ledger, as before.

## 4. Reuse D1 data, or rerun? D2 reruns everything
D2 reruns all units, including selection. Reasons:
1. **Cleaner.** Every D2 number comes from one stage, one kernel, one attempt record and one code hash. Pooling rows from a terminal stage would need new cross-stage resume rules. That is exactly the kind of machinery the review rounds showed is easy to get wrong.
2. **No rewritten history.** D1 stays a closed, terminal record; nothing from it flows into a gate.
3. **Cheap.** Selection plus the batch-1 check cost ≈ 494 s of the 1,980 s, and the loads they share are needed anyway.
4. **Free reproducibility check.** Decoding is greedy with the same protocol and book. A **descriptive, non-gating** comparison of D2's selection rows with D1's will be reported (agreement of picks and of accept/reject decisions).

## 5. Unchanged
- T1 rules (§8: exact structure, conformance, current protocol hash, wrong-pick-accepted screen ≤ 2% for both senders, projection ≤ T1 cap), TEST sizes, success criteria (§6), freeze procedure (§9), retry rules, the supervisor design. The only change: the **qualifying dev stage for T1 is D2** (`t1_qualifying_dev_stage`), because D1 can no longer be `.done`.
- T1 cap stays the 6.0 h placeholder, set from D2 at freeze.

## 6. Logging fix
D1's `start` log line showed `code_hash 77eceb53…`. That field comes from the frozen E1b `env_info`, which reads **E1b's** `CODE_HASH.txt`. It is not the E1c hash, and it looked like a mismatch. The E1c child now relabels it as `e1b_code_hash` and adds `e1c_code_hash`. The E1b code is not changed. Test: `test_log_field_relabelled`.

## 7. Code and tests
- `config_e1c.json`: `caps_h.D2 = 0.8`, `dev_stages`, `closed_stages = ["D1"]`, `t1_qualifying_dev_stage = "D2"`, `amendment_A1`.
- `stages.py`: `is_dev()` replaces `name == "D1"`; `t1_eligibility` reads the qualifying stage; `ChildStage.log` relabels the hash. `supervisor.py`: closed-stage refusal (exit 20).
- Tests (42 OK, from 40): the stage tests now run D2. `test_D1_closed_and_D2_qualifies`: D1 start refused (20); D1's terminal marker does not block D2; a "good" D1 summary qualifies nothing. Plus `test_log_field_relabelled`. E1b suite unchanged (112 OK).
- Kernel `glyph-kaggle/e1c_D2` prepared, **not pushed**, `E1C_COMMIT = "SET_ME"` with a guarding assert.
