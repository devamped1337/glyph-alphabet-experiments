# GPT review r4: E1c draft pre-registration (via the Codex CLI, 2026-10-15)

*Verbatim reply to REVIEW_ROUND.md r4 (pinned b0c288a), sent with `codex exec -s read-only`. The PREREG, config, e1c stages/analysis, retry tool, tests, the frozen E1b Stage class and GPT's r3 review were pasted into the prompt.*

Verdict: CHANGE.

6. not resolved. Coverage is extended, but budget accounting and deadline/completion races remain.

W1. not resolved. The watchdog stays armed through summary and finalisation, resolving the early cancellation. However, fire() runs concurrently with finish(): the main thread can still write .done and mark the attempt done after expiry. start() checks .done before terminal markers, and t1_eligibility() ignores BUDGET_EXHAUSTED. The test calls fire() synchronously with a substitute that raises SystemExit; real os._exit(3) neither unwinds run() nor records “exit 3”.

W2. not resolved. Concurrent ledger writes are serialised and atomic, and the killer timer provides an independent exit for bookkeeping that blocks while releasing the GIL. Remaining accounting, terminality and timer limitations require changes below.

N. resolved.

Optional. Load persistence across attempts is resolved. The interrupted/resumed fixture is only partly resolved: crashing on the fifth sender call leaves no persisted selection rows, because selection rows are written after verification. It tests restarting and retaining loads, but does not exercise reuse of partial selection data.

New required changes:

[blocking] Fix elapsed-time accounting. save_ledger() samples used_s() before persistence, then resets t0 after fsync/replace, permanently excluding persistence time on every save. Preserve one monotonic stage origin and cumulative baseline, or otherwise retain that elapsed time. Synchronise used_s() snapshots with any updates to prior_s/t0; the writer lock alone does not protect readers. Test elapsed-time conservation with deliberately slow saves and concurrent reads.

[blocking] Make expiry and successful completion mutually exclusive. Coordinate the watchdog and finalisation so an expired stage cannot acquire a usable completion marker. Check terminal failure before .done in start(), and reject terminal D1 stages in t1_eligibility(). Add a real concurrent expiry/finalisation test and a subprocess test of the production os._exit path; do not require a Python exception outcome from a hard exit.

[blocking] Close the bookkeeping-independent terminality gap. If marker creation and ledger persistence both fail, os._exit leaves a stale ledger and an outcome of “running”; authorise_retry() can then accept a below-cap charge as kernel_crash. Existing tests cover successful persistence or an already exhausted ledger, not this combination. Provide a fail-closed recovery rule using durable pre-recorded deadline information or required external exit evidence, and test simultaneous marker/ledger failure.

[non-blocking] Qualify the five-second guarantee. Both timers are Python threads and need scheduling and the GIL; they cannot guarantee termination within five seconds during a native call that retains the GIL or process suspension. Either state this limitation and describe five seconds as the intended bookkeeping grace, or use an independently scheduled process supervisor if a hard bound is required.

Optional suggestions:

Move the interruption to after some selection or exchange rows have been persisted. Assert that the retry reuses those rows without regenerating them, then verify sizing across both attempts.

Report final elapsed stage time separately from the pre-summary gpu_h snapshot, which currently excludes summary and finalisation.

This review uses only the pasted artifacts; reported tests were not independently executed.
