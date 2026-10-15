# E1c REVIEW_ROUND A1 r2 (Amendment A1: new dev stage D2), pinned commit 95de518

## Ask
Thank you for the six review rounds that got the E1c supervisor to ACCEPT. Please review **Amendment A1** (`AMENDMENT_E1c_A1.md`) and its code changes. Verdict: ACCEPT (D2 may be proposed to Stefan for a go) or CHANGE (required edits). In particular:
1. Is the D2 cap (0.8 GPU-h) soundly derived from the **measured** D1 timings, with an adequate margin?
2. Is keeping the three-load sequential order (rather than co-residency of both models) the right call?
3. Is "D2 reruns everything" cleaner than reusing D1's complete selection rows?
4. Do the code changes keep the T1 rules and success criteria unchanged, apart from naming D2 as the qualifying dev stage?
5. Is the log-field fix correct?
Please list **all** remaining blockers at once, and mark anything disproportionate for a ≤ 0.8 GPU-h free-Kaggle dev pilot.

## Round 2: changes since A1 r1 (`reviews/gpt_E1c_A1_r1.md`, CHANGE at c9bf063)
Thank you for the r1 review. All four items are applied as asked:
1. [blocking] `t1_eligibility` again checks `.done` explicitly on the qualifying stage (`stages.finished()` already required it; the check is now explicit). New `test_t1_needs_done_marker`: a valid D2 summary and recorded `done`, but no `.done`, gives not eligible; adding `.done` gives eligible.
2. [blocking] PREREG normative references now name D2:
   - §7: the T1 row ("D2 eligibility", "set from D2 at freeze") and the precedence line;
   - §7: the batch-1 rule and §4's batch wording ("the qualifying dev stage");
   - §8: the heading, the eligibility list (D2 `.done` + recorded `done`, D2 timings, D2 protocol hash), the T1 cap source and the invalidation rule;
   - §9 step 1;
   - the `stages.py` docstring.
   Historical D1 statements are kept; the old D1 estimate is labelled historical and too low.
3. [non-blocking] Stress arithmetic corrected: loads +350 s (3 × 420 − 910), generation +260 s → 2,590 s, 290 s under the cap. The estimate row now splits 1,387 s measured directly (incl. start-up) + 583 s from measured counterparts + ≈ 10 s summary.
4. [non-blocking] Wording: six segments measured directly, two from counterparts. D1 is used for timings and for the non-gating reproducibility comparison.
Tests: E1c 43 OK; E1b 112 OK. The kernel is still unpushed (SET_ME).
The text below is the r1 context, updated where the numbers changed. **This is the final round; please list every remaining blocker at once.**

## Context
- E1c PREREG (DRAFT r6) was ACCEPTED by you at 1346dc2 (wording-only edits at dffaa41). D1 ran once on Kaggle at dffaa41 (free T4).
- **D1 outcome (`D1_REPORT.md`, dd83b26):** BUDGET_EXHAUSTED at 1,396 s = 0.388 GPU-h of the 0.5 h cap. The admission guard refused the third model load (1,396 + 420 s estimate > 1,800 s). Integrity was fine: commit, E1c code hash and protocol hash matched; T4 GPU with preflight PASS for both models; canaries 20/20; no errors.
- **D1 results (diagnostics only):** pick accuracy Qwen 147/160, Falcon 156/160; ID use 146/160 and 152/160; wrong-pick-accepted 0/160 for both senders; verifier batch 8 = batch 1, 16/16. Qwen→Falcon: 40/40 on both arms, payload saving 70.9%. Falcon→Qwen was not run. T1 is not eligible.
- **Cause:** the 0.5 h cap rested on an assumed ≈ 1,500 s; the per-load time was never measured. Grok's comment (`reviews/grok_D1_comment.md`, verbatim): "You pre-regged ~1,500 s. Actual loads ran ~600 s for two models and send+verify was 225–270 s each. … The incomplete run is on the time estimate. Next one needs the loads measured, not guessed."

## Artifacts (at 95de518)
- **`AMENDMENT_E1c_A1.md`** (summary):
  - D1 stays terminal BUDGET_EXHAUSTED; nothing in `results/D1/` (committed unchanged) is edited or retried. `closed_stages: ["D1"]` → the supervisor refuses D1 (exit 20). D1's partial results are diagnostics only; only its timings are used.
  - **D2:** same protocol and protocol hash, dev book, sizes, b1 check, guard, supervisor and retry rules. Sequential order kept (Qwen → Falcon → Qwen; 3 loads). This is the minimum with one model resident, because each receiver needs the other model's sender output. Co-residency (both NF4 7B on the 15 GB T4) was never measured, so it is rejected for now.
  - **Measured segments (s):**
    - start-up 20;
    - Qwen load + canaries 310;
    - Qwen send + verify + check 224;
    - Falcon load + canaries 290;
    - Falcon send + verify + check 270;
    - Falcon receives Qwen→Falcon 273;
    - not reached, taken at their measured counterparts: Qwen load 310 and Qwen receives Falcon→Qwen 273;
    - summary ≈ 10.
  - **Estimate:** 1,980 s = 0.55 h. **Cap:** 0.8 h = 2,880 s (+900 s, 45%). Stress case (all loads at the 420 s prior, generation 25% slower): 2,590 s. At the third load the guard sees ≈ 1,400 + 420 s, which is ≈ 1,000 s below the deadline. Cumulative dev compute ≤ 1.19 h.
  - **D2 reruns everything.** Reasons: one stage, kernel, attempt and code hash; no cross-stage resume rules; selection costs only ≈ 494 s; it also gives a descriptive, non-gating D1 vs D2 reproducibility comparison.
  - T1 rules, success criteria, freeze and retry rules are unchanged. `t1_qualifying_dev_stage = "D2"`.
  - **Log fix:** E1b's frozen `env_info` logs E1b's own CODE_HASH as `code_hash`. `ChildStage.log` relabels it as `e1b_code_hash` and adds `e1c_code_hash`. E1b code is untouched.
- **Code:**
  - `config_e1c.json`: `caps_h.D2 = 0.8`, `dev_stages ["D1","D2"]`, `closed_stages ["D1"]`, `t1_qualifying_dev_stage "D2"`, `amendment_A1`.
  - `stages.py`: `is_dev()` replaces `name == "D1"`; `t1_eligibility` reads the qualifying stage.
  - `supervisor.py`: exit 20 for closed stages.
  - PREREG §7 table: D2 row plus an A1 note.
- **Tests:** E1c 43 OK. The stage tests now run D2. `test_D1_closed_and_D2_qualifies` checks that D1 is refused with 20, that D1's terminal marker does not block D2, and that a "good" D1 summary qualifies nothing. `test_log_field_relabelled` covers the log fix. E1b 112 OK.
- **Kernel:** `e1c_D2` prepared, **not pushed**, `E1C_COMMIT = "SET_ME"` with a guarding assert.

## Scope
In scope: A1's cap arithmetic, load-order and rerun decisions, the closed-stage and qualifying-stage code, the log fix, and any honesty or wording issues. Out of scope: the already-accepted supervisor design, E1b conclusions, model choice, posting.

## Output
Verdict (ACCEPT / CHANGE). Answers to questions 1–5. Then the COMPLETE list of remaining required changes, each marked [blocking] or [non-blocking] and [proportionate] or [over-engineering: disclose instead]. Then one line: is D2 ready to propose to Stefan, yes or no. Plain text.
