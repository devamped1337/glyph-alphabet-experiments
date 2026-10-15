# GPT review of E1c r6 (REVIEW_ROUND r6, pinned 1346dc2), via Codex

Verdict: ACCEPT.

Review based solely on the pasted code and test reports; tests were not independently executed.

B1 — resolved. Enforcement, admission, elapsed charging and completion decisions use the shared monotonic clock. Wall-clock changes affect audit timestamps only.

B2 — resolved. Completion requires .done plus a recorded final done outcome and no running attempt. Restart, retry authorisation and T1 reject the demonstrated partial-publication case.

B3 — resolved for the execution path. Atomic writes sync the file and containing directory; results/ and results/<stage> are created separately with their parents synced before launch.

N1 — resolved. The preregistration accurately distinguishes deadline-triggered SIGKILL from a guaranteed termination bound.

N2 — resolved for the declared execution path. Normal-exit process-group cleanup and parent-death signalling address the previous concerns, with subprocess coverage. Residual limitations appear below.

N3 — resolved. Charged time and excluded finalisation time are explicitly distinguished.

N4 — resolved. The manual route is clearly labelled external-log adjudication, including its inability to check missing durable state.

Complete list of remaining items:

[non-blocking] [proportionate] Narrow the bookkeeping-failure wording. If the final state os.replace succeeds but the subsequent directory fsync fails, the visible state can already say done despite exit 70. The current fault injection occurs before that write and does not cover this case. State that failures before final-state replacement leave running; failure after replacement can leave visible completion with uncertain crash durability. Additional transactional machinery is over-engineering for this pilot; disclose the limitation.

[non-blocking] [proportionate] Qualify parent-death signalling. _pdeathsig silently ignores exceptions and does not check prctl’s return value. It also lacks a parent-identity check for supervisor death before signal registration. Furthermore, parent-death SIGKILL targets the child, not its surviving descendants. The reported test demonstrates the established-child case. Disclosing these limits is sufficient for the stated path with no multiprocessing workers; stronger containment is [over-engineering: disclose instead].

[non-blocking] [proportionate] Make the remaining descriptions precise: finalise_s excludes the final state write itself; ChildStage’s docstring still says deadline_wall; guard’s docstring still calls the supervisor kill a “hard bound.” These are small documentation corrections, not reasons to delay D1.

No remaining blockers. Further durability or process-containment hardening is disproportionate to this 0.5 GPU-h descriptive pilot once these limitations are disclosed.

D1 ready to propose to Stefan: yes.
