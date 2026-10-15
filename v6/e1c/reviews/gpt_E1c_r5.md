# GPT review of E1c r5 (REVIEW_ROUND r5, pinned 6080fdc), via Codex

Verdict: CHANGE.

The supervisor redesign removes the main thread races, but wall-clock accounting and publication of completion still leave blocking gaps.

Items 1–4:

1. Resolved for the original defect. One supervisor interval replaces repeated save/reset accounting, and there are no concurrent used_s reads or ledger writers within a run. Clock-source problems remain below.

2. Resolved for the original mechanism. One supervisor decides deadline versus completion; terminal markers precede .done; T1 rejects BUDGET_EXHAUSTED. Real subprocess SIGKILL tests appropriately replace testing the removed os._exit path. Completion publication has a separate failure gap below.

3. Not resolved completely. Failure before .done leaves a running attempt that is refused, as the new test demonstrates. However, failure of the final state write after successful summary.json and .done writes leaves outcome=running alongside usable completion artifacts. supervise() checks .done before checking running attempts, and t1_eligibility() never checks attempt state. That contradicts the stated fail-closed rule.

4. Not resolved as a guarantee. A separate process removes dependence on the child’s GIL, but supervisor suspension, scheduling delays and uninterruptible kernel waits still prevent an unconditional deadline bound. SIGKILL issuance and confirmed process termination are different events.

New required changes:

[blocking] Use a monotonic clock for enforcement, elapsed accounting and completion decisions. Currently the timeout is computed from time.time(), while wait’s timeout and the final wall-clock sample can disagree after clock adjustments. A backward jump can reduce or even make the ledger increment negative, or accept completion after the intended elapsed budget; a forward jump can spuriously exhaust the stage. Keep wall timestamps for audit, but derive the supervisor timeout, child admission deadline and elapsed charge from a shared monotonic clock. Test forward and backward wall-clock changes.

[blocking] Require committed successful attempt state wherever completion is consumed. Both start and T1 eligibility must reject a running attempt even when .done exists, and accept completion only with the corresponding recorded done outcome. Inject failure specifically at the final e1c_state.json write after .done succeeds; verify that restart, retry authorization and T1 all refuse it.

[blocking] Complete the claimed durable-write protocol. atomic() fsyncs the temporary file but does not fsync its parent directory after os.replace(). The pre-launch record therefore lacks the claimed durability across filesystem or host failure. Sync the containing directory before launch, account for newly created directories, and apply the same durability discipline to terminal state.

[non-blocking] Qualify the hard-bound wording. Describe deadline-triggered SIGKILL under a running supervisor, with operating-system scheduling and termination limitations. The wall < 30 s test establishes observed behavior, not a universal bound.

[non-blocking] Document and test process-tree assumptions. The timeout path kills the child’s process group, but normal child exit does not clean up surviving grandchildren. Descendants that create another session escape killpg, and supervisor-only death leaves the child running. Either establish that the execution path creates no surviving GPU workers, or provide suitable lifecycle containment. Add a subprocess test with an ordinary grandchild.

[non-blocking] Clarify ledger scope. The snapshot includes pre-launch record persistence and child execution, but excludes supervisor finalization after end. If “elapsed stage time” includes that work, report it separately or extend accounting.

Operational observations:

Making a whole-kernel death terminal is a defensible conservative tradeoff, although it sacrifices retries for otherwise recoverable infrastructure failures. The manual “no results returned” route cannot enforce that rule when the durable state itself is unavailable; explicitly identify it as external-log adjudication.

The test hooks are explicitly enabled arbitrary-code injection, not an authentication boundary. Their two-variable gate and absence from the prepared kernel are reasonable for the stated setup.

The revised partial-selection resume test addresses the previous optional coverage request.

This review uses only the pasted artifacts; tests were not independently executed.
