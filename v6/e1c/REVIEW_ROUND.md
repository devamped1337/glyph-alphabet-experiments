# E1c REVIEW_ROUND r5 (draft pre-registration after GPT r4), pinned commit 6080fdc

## Ask
Re-review the E1c **DRAFT** after the r5 supervisor-process redesign. Verdict: ACCEPT (D1 may be proposed to Stefan for a go) or CHANGE (required edits). For each r4 blocking item say resolved / not resolved:
- (1) ledger time leak and unprotected `used_s` reads;
- (2) deadline vs completion not mutually exclusive; `.done` checked before terminal markers; `t1_eligibility` ignoring BUDGET_EXHAUSTED; no real `os._exit` test;
- (3) fail-closed gap when both marker and ledger writes fail;
- (4) [non-blocking] 5 s grace not a hard bound.

## Context
- r4 (`reviews/gpt_E1c_r4.md`, at b0c288a) returned CHANGE on the watchdog accounting/terminality. Stefan approved replacing the in-process watchdog with a supervisor process.
- Unchanged: protocol, books, criteria, models (Qwen2.5-7B, Falcon3-7B), free T4, D1 cap 0.5 GPU-h, protocol hash.

## Artifacts (at 6080fdc)
- **`e1c/supervisor.py` (new; `run_e1c.py --stage`).** Sole writer of `e1c_state.json`, `budget_ledger.json`, terminal markers, `summary.json`, `.done`. No threads.
  - Gates (go, frozen, D1 eligibility, code hash, book); then terminal markers **before** `.done`; any attempt still `running` -> ATTEMPT_INCOMPLETE (17).
  - remaining = cap − cumulative ledger (retry: max(ledger, charged_h)); ≤ 0 -> BUDGET_EXHAUSTED (3).
  - Attempt record (uuid token, started_wall, deadline_wall, budget_s, code/protocol hash, outcome=running) written atomically (tmp + fsync + os.replace) **before** `Popen(..., start_new_session=True)`; a failed write raises before launch.
  - `wait(timeout=deadline − now)`; on timeout `killpg(SIGKILL)`.
  - `decide(rc, end, deadline, complete)`: rc None or end > deadline -> deadline/BUDGET_EXHAUSTED; rc 0 + CHILD_COMPLETE -> done; 3 -> BUDGET_EXHAUSTED; 8 -> CANARY_FAIL; 9 -> `no_gpu rc=9` (infra); else `crash rc=N`.
  - Post-run, in order: ledger (+elapsed; deadline charges the full remaining budget), marker, summary.json (from summary.child.json, gpu_h = ledger) + `.done`, and LAST the attempt outcome. Any exception -> exit 70, attempt stays `running` (terminal).
- **Child (`run_e1c.py --child`, `stages.child_main`).** Refuses (15) unless `E1C_ATTEMPT_TOKEN` equals the running attempt's token; deadline read from that record. `ChildStage`: `save_ledger` no-op, `finish` raises. Writes only rows, `loads_attempt<n>.json`, `summary.child.json`, then CHILD_COMPLETE. Admission guard exits 3 without writing; canary failure exits 8 without writing a marker. Watchdog, LEDGER_LOCK, E1cStage removed.
- **`t1_eligibility`:** any TERMINAL marker in D1 -> not eligible, before `.done`.
- **`authorise_retry`:** outcome `running` -> no reason allowed (fail-closed); `no_gpu rc=9`/marker -> no_gpu; `crash rc=N` -> non-GPU reasons; deadline/admission/canary -> refused; charged_h rules unchanged.
- **Test-only hooks** (only with E1B_ALLOW_NO_GPU=1): E1C_RES, E1C_CONFIG, E1C_TEST_HOOK (`tests/e1c_hook.py`: fake backend + faults). The Kaggle kernel sets none of them.
- **Separate-process tests** (each runs a real supervisor process that launches a real child):
  - deadline kill: child sleeps in a sender call, cap 8 s -> exit 3, outcome deadline, rc None, BUDGET_EXHAUSTED, no `.done`, ledger = 8 s, wall < 30 s; rerun 18; retry refused;
  - admission stop (cap 180 s < 420 s load prior): exit 3, no model calls;
  - concurrent finish: child writes CHILD_COMPLETE then sleeps past the 25 s deadline -> deadline, no `.done`, no summary.json; plus pure `decide` cases (exit after deadline with CHILD_COMPLETE -> deadline);
  - both writes failing: child makes results/ and results/D1 read-only then sleeps past the deadline -> supervisor exit 70, no marker, no ledger, attempt `running`; every retry reason refused; next start 17 (ATTEMPT_INCOMPLETE), then 18;
  - resume: crash on sender call 18 (6th Falcon call) after `select_qwen7b.jsonl` (12 rows) is saved, no Falcon file -> `crash rc=1`; no_gpu refused, kernel_crash authorised; retry -> done; Qwen file byte-identical; no Qwen sender calls in attempt 2; ledger = attempt-1 + attempt-2 elapsed; 5 loads across attempts, load_s = max; sizing unit costs = recomputed; a third start -> 17;
  - child without/with wrong token -> 15; full D1 dry run, terminal marker beats `.done` (18); ledger at cap -> 3, no calls.
- PREREG §7 (deadline, fail-closed, precedence) and §11 (r5) updated. **Tests:** E1c 33 OK (consolidated; watchdog/lock tests removed); E1b 112 OK. Kernel `e1c_D1` prepared, **not pushed**.

## Code excerpt: supervise() post-launch (verbatim)
(pasted in the prompt)

## Scope
In scope: whether items 1–4 are resolved; new problems from the redesign (kill/wait race, wall-clock source, clock jumps, orphaned grandchildren, the cost of making a whole-kernel death terminal, test-hook exposure). Out of scope: E1b conclusions, model choice, posting.

## Output
Verdict (ACCEPT / CHANGE). Items 1–4 each resolved / not resolved, with a reason if not. New required changes marked [blocking] or [non-blocking]. Optional suggestions. Plain text.
