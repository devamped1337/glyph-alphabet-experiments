# E1c REVIEW_ROUND r6 (draft pre-registration after GPT r5), pinned commit 1346dc2

## Ask
Re-review the E1c **DRAFT** after the r6 fixes. Verdict: ACCEPT (D1 may be proposed to Stefan for a go) or CHANGE.
1. For each r5 item say resolved / not resolved: (B1) monotonic clock; (B2) completion needs a recorded `done` outcome; (B3) directory fsync; (N1) kill wording; (N2) process tree; (N3) ledger scope; (N4) manual-route labelling.
2. **List ALL remaining blockers at once, in this round.** Please do not hold any back for a later round.
3. **Proportionality:** this governs a 0.5 GPU-h dev pilot on free Kaggle (one T4, no paid resources, results descriptive only, no claim). For every remaining item, say whether it is proportionate to that risk, or whether it is over-engineering that should be accepted as a disclosed limitation instead. Stefan considers over-engineering a real risk at this point.

## Context
- r5 (`reviews/gpt_E1c_r5.md`, at 6080fdc) returned CHANGE: 3 blocking + 3 non-blocking items + 1 operational note. Items 1 and 2 from r4 were resolved.
- Unchanged: protocol, books, criteria, models (Qwen2.5-7B, Falcon3-7B), D1 cap 0.5 GPU-h, protocol hash, supervisor/child split.

## Artifacts (at 1346dc2)
- **B1.** The supervisor uses `time.monotonic()` for `started_mono`, `deadline_mono`, the `wait` timeout, `end`, the elapsed charge and `decide()`. The child's admission guard compares `time.monotonic() + est` with the recorded `deadline_mono` (CLOCK_MONOTONIC is system-wide on Linux). Wall times are recorded for audit only; `deadline_wall` is gone. Test: the supervisor runs in-process with `time.time()` jumping +10 days and −10 days after the first call; both runs end `done` with 0 < elapsed < 60 s and ledger = elapsed.
- **B2.** `stages.finished(d)` = `.done` AND last attempt outcome `done` AND no attempt `running`. Start order: terminal markers → any `running` attempt (17, ATTEMPT_INCOMPLETE) → `finished` (0) → `.done` without a recorded `done` (17). `t1_eligibility` requires `finished(D1)`. `authorise_retry` refuses `.done` and `running`. Test: a test-only fault fails the final state write after `summary.json` + `.done` were written → exit 70; state `running`; `finished` False; T1 ineligible ("no recorded 'done'"); retry refused; restart 17, then 18. Second test: `.done` with outcome `crash rc=1` → 17.
- **B3.** `atomic()`: write tmp, fsync, `os.replace`, then fsync the containing directory. `mkdir_durable()` fsyncs the parent of new directories (results/, results/<stage>). Test: fsync targets are recorded via /proc/self/fd and include the tmp file, the new directory's parent and the containing directory (last).
- **N1.** PREREG §7 and the supervisor docstring: a deadline-triggered SIGKILL issued by a running supervisor, not a hard real-time bound; the tests show observed behaviour only.
- **N2.** After any child exit the supervisor also SIGKILLs the process group. The child starts with `PR_SET_PDEATHSIG=SIGKILL` (prctl in `preexec_fn`). Disclosed: a descendant that creates its own session escapes; the E1c path creates none. Tests: an ordinary `sleep 120` grandchild is dead after a normal `done`; SIGKILLing the supervisor mid-run kills the child within 5 s, and the attempt stays `running` (next start 17).
- **N3.** Ledger = monotonic time from the pre-launch record to child exit. Post-run bookkeeping is reported as `finalise_s` and not charged (stated in PREREG).
- **N4.** `authorise_retry` doc and PREREG: the "no results returned" route is external-log adjudication; fail-closed cannot be checked there.
- **Tests:** E1c 40 OK (from 33); E1b 112 OK. Kernel `e1c_D1` prepared, **not pushed**.

## Scope
In scope: items B1–B3 and N1–N4, any new defect they introduced, the complete list of remaining blockers, and proportionality. Out of scope: E1b conclusions, model choice, posting.

## Output
Verdict (ACCEPT / CHANGE). Items B1–B3 and N1–N4, each resolved / not resolved, with a reason if not. Then the COMPLETE list of remaining required changes, each marked [blocking] or [non-blocking] and [proportionate] or [over-engineering: disclose instead]. Then one line: is D1 ready to propose to Stefan, yes or no. Plain text.
