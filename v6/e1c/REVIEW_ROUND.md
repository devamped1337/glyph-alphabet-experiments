# E1c REVIEW_ROUND r4 (draft pre-registration after GPT r3), pinned commit b0c288a

## Ask
Re-review the E1c **DRAFT** after the r3 fixes. Verdict: ACCEPT (D1 may be proposed to Stefan for a go) or CHANGE (required edits). For each r3 item, say whether it is resolved:
- (6) watchdog coverage;
- (W1) [blocking] deadline enforcement through summary and finalisation;
- (W2) [blocking] ledger race and an exit independent of bookkeeping;
- (N) [non-blocking] batch-rule wording;
- the optional items.

## Context
- r3 (`reviews/gpt_E1c_r3.md`, at cf9723d) returned CHANGE. Items 1, 2, 3, 5, A, B, C and D were resolved; only the watchdog remained (6, W1, W2), plus one wording item and two optional suggestions.
- Unchanged: E1b A9 = POC FAILED; A10 B3r = INCONCLUSIVE; Qwen2.5-7B and Falcon3-7B; free T4; D1 cap 0.5 GPU-h.

## Artifacts (at b0c288a), all in `e1c/stages.py` unless noted
- **W1.** The watchdog is no longer cancelled before `summarize()` and `S.finish()`. It is cancelled only in `run()`'s `finally`, after `.done` and `_mark("done")` or after an exit.
  - Test: the watchdog is alive and not cancelled during `summarize`, and `.done` already exists when it is cancelled.
  - Test: a deadline fired during the summary gives exit 3, BUDGET_EXHAUSTED and no `.done`; the attempt outcome is "exit 3"; a further start gives 18; a retry is refused.
- **W2, ledger.** `E1cStage(ES.Stage)` overrides `save_ledger`. It holds one process-wide `LEDGER_LOCK` (the main thread, the watchdog and atexit all go through it, since atexit binds the subclass method) and writes atomically: a unique temp file per pid and thread, fsync, then `os.replace`. A `timeout` is used for the watchdog.
  - Test: 4 threads × 200 concurrent saves raise no error, leave valid JSON and leave no temp files.
  - Test: a held lock with timeout=0.1 gives TimeoutError.
- **W2, exit.** `Watchdog.fire()` arms a **killer timer first** (grace 5 s → `_exit`, once only). Then, each step isolated in try/except: the BUDGET_EXHAUSTED marker via `os.open` (first), `save_ledger(timeout=2)`, a log line. Then `_exit`.
  - Test: save and log raise and the marker directory is missing; the exit still happens and done_steps is empty.
  - Test: `save_ledger` blocks forever; the exit happens within the grace period, exactly once.
- **Terminality without bookkeeping.**
  - `start()` refuses with exit 3 and writes the marker when the ledger shows the cap used.
  - `authorise_retry` refuses charged_h ≥ cap, and refuses when max(ledger, charged) ≥ cap.
  - Tests cover both.
- **N.** `config_e1c.json` `verifier_batch_rule` and PREREG §4 now say: batch 8 in D1 and T1; a disagreement makes T1 ineligible until an amendment adds a batch-1 dev stage; there is no automatic switch.
- **Optional, both done.**
  - Loads, including canaries, are persisted in each attempt record (`_record_load`), and sizing uses the maximum over all attempts (`all_loads`).
  - A genuine interrupted-then-resumed fixture: attempt 1 raises RuntimeError on the 5th generate call; the retry is authorised as kernel_crash and resumes to completion. The test checks:
    - the selection file holds 12 rows and is complete;
    - sizing's sender+verifier and receiver unit costs equal `unit_costs` recomputed from the persisted rows;
    - there are 4 loads (1 + 3) and load_s = their maximum;
    - each fallback hybrid row has the same `batch_index`, `batch_pos` and `latency_s` as its prose twin, so a fallback's generation is counted once.
- **Tests:** E1c 38 OK (from 31); E1b 112 OK (unchanged). Kernel `e1c_D1` is prepared and **not pushed**.

## Scope
In scope: whether 6, W1, W2, N and the optional items are resolved, and any new problem the fixes introduced (thread safety of `used_s` reads, the `os._exit` path, the grace period, residual non-ledger costs). Out of scope: E1b conclusions, model choice, posting.

## Output
Verdict (ACCEPT / CHANGE). Then items 6, W1, W2, N and optional, each marked resolved / not resolved, with a reason if not. Then any new required changes, marked [blocking] or [non-blocking]. Then optional suggestions. Plain text.
