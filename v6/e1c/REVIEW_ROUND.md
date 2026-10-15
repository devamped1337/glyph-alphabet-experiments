# E1c REVIEW_ROUND r3 (draft pre-registration after GPT r2), pinned commit cf9723d

## Ask
Re-review the E1c **DRAFT** after the r2 fixes. Verdict: ACCEPT (D1 may be proposed to Stefan for a go) or CHANGE (required edits). For each r2 open item (1, 2, 3, 5, 6), each r2 new blocking item (A, B) and each r2 minor item (C, D), say whether it is resolved.

## Context
- r2 (`reviews/gpt_E1c_r2.md`, at c6ffaa2) returned CHANGE. Items 4, 7, 8 and 9 were resolved; 1, 2, 3, 5 and 6 were open; there were 2 new blocking items and 2 non-blocking ones.
- Unchanged: E1b A9 = POC FAILED; A10 B3r = INCONCLUSIVE; Qwen2.5-7B and Falcon3-7B; free T4; D1 cap 0.5 GPU-h; 160 dev entries per sender; 240 TEST entries per direction.

## Artifacts (at cf9723d)
1. **Selection completeness.** `analysis.check_selection(sel_rows, ids)` works on the RAW JSONL rows: exactly one row per registered sender entry, no duplicates, no extras; otherwise Incomplete. `direction_result` now takes the raw selection rows plus the sender ids and runs this check (and checks receiver entries ⊆ sender entries) before anything else. `selection_stats` reports `complete` from the same check. Tests: duplicate, missing, extra and wrong-id-set selection rows each give INCOMPLETE.
2. **Protocol hash and batch.** `protocol_hash(X, cfg)` now includes the ACTUAL `cfg["sender_max_new_tokens"]`, `verifier_batch` and `receiver_batch`. T1 no longer switches batch. A batch-8 vs batch-1 disagreement in D1 makes T1 **ineligible** until an amendment adds a batch-1 dev stage, so the screen is re-measured under the path T1 will use. Tests: changing the sender limit, the verifier max tokens or the batch size each invalidates D1; a disagreeing conformance record makes T1 ineligible.
3. **Retry.**
   - `authorise_retry.allowed_reasons`:
     - a GPU_PREFLIGHT_FAIL marker or `exit 9` allows only `no_gpu`;
     - `crash <type>`, `running` (killed) or a manually recorded missing attempt allows only install_or_network, kernel_crash or oom_at_load;
     - any other `exit N` is refused.
   - charged_h must be finite, > 0 and ≤ the cap. The log note is mandatory.
   - Resume binding: if attempt-1 rows exist, the retry refuses unless the recorded code hash and protocol hash equal the current ones (attempt records now store protocol_hash).
   - Tests: NaN, inf, 0, over-cap and blank-note values; reasons inconsistent with the marker or the exit code; a resume with a different hash.
5. **Verifier grammar.** `[0-9]` replaces `\d`. A test rejects Arabic-Indic and fullwidth digits.
6. **Budget.**
   - `Watchdog`: a timer at the remaining cumulative budget saves the ledger, writes BUDGET_EXHAUSTED and calls `os._exit(3)` whatever is in flight (overrun = termination latency). It is cancelled on any exit. Unit-tested with an injected exit.
   - The admission guard is kept and is now registered as **estimate-based admission control, not a bound**.
   - Kaggle time before the stage starts (clone, pip) is outside the ledger and disclosed.
- **A (new blocking): sizing after a resume.** `unit_costs` derives sender+verifier seconds per entry and receiver seconds per message from **persisted per-row latencies** (a fallback is counted once), plus the longest observed load × 3. It no longer uses current-attempt elapsed time ÷ all entries. Tested.
- **B (new blocking): summary structure.**
  - `check_d1_summary` requires exactly the two registered directions (COMPLETE, 10 entries, 40 messages each), exactly both senders (complete, n = 160), both conformance records (n = 16, all identical) and the current protocol hash.
  - `verdict(out, X)` requires exactly both directions and both senders at TEST sizes.
  - Tests: empty, one-direction, one-sender, wrong-size and wrong-conformance summaries are all rejected.
- **C (minor): freshness wording.** PREREG §3 now says true rules exclude the specified earlier *true-rule* texts and cases are fresh under the checks. A repeated distractor text is not historically unseen; stateless inference only means no context carries over.
- **D (minor): dev-power wording.** The binomial sampling assumption for generated, family-balanced entries is stated; "can lower hybrid accuracy"; the bound for 0 of 160 is ≈ 1.86%.
- **Optional, taken:**
  - `check_freeze.py` also checks that the registration commit has no `book_test.json` and that the execution book's digest equals both pins (tested).
  - Regressions added for duplicate selections, missing summary parts, resumed sizing, batch disagreement and a changed sender token limit.
- **Tests:** E1c 31 OK (from 25); E1b 112 OK (unchanged). Kernel `e1c_D1` is prepared and **not pushed** (E1C_COMMIT=SET_ME).

## Scope
In scope: whether the items above are resolved, and any new problem the fixes introduced (especially the watchdog's hard exit, the retry/resume rules, the eligibility strictness and the sizing inputs).
Out of scope: E1b conclusions, model choice, posting.

## Output
Verdict (ACCEPT / CHANGE). Then items 1, 2, 3, 5, 6, A, B, C, D, each marked resolved / not resolved, with a reason if not. Then any new required changes, marked [blocking] or [non-blocking]. Then optional suggestions. Plain text.
