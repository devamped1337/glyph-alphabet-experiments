# GPT review r3: E1c draft pre-registration (via the Codex CLI, 2026-10-15)

*Verbatim reply to REVIEW_ROUND.md r3 (pinned cf9723d), sent with `codex exec -s read-only`. The PREREG, config, e1c code, tools, tests and GPT's r2 review were pasted into the prompt.*

Verdict: CHANGE.

1. resolved. Raw selection rows are checked for duplicates and exact assignment membership before direction results; receiver assignments must also be subsets of sender assignments.

2. resolved. The hash includes the actual sender token limit and effective batches. Conformance disagreement prevents T1 eligibility instead of silently changing its execution path.

3. resolved. Retry authorisation checks failure/reason consistency, finite positive charges and log notes. Reused rows require matching code and protocol hashes.

5. resolved. The grammar uses ASCII [0-9], with Unicode-digit rejection tests.

6. not resolved. The watchdog is cancelled before summarize() and S.finish(), leaving analysis and finalisation outside deadline enforcement. Its ledger writes also race with main-thread ledger writes, and required bookkeeping precedes termination without a time limit.

A. resolved. Sender, verifier and receiver unit estimates now use persisted row timings rather than current-attempt elapsed time divided by resumed totals. Fallback generation is counted once for the projected execution path.

B. resolved. Eligibility and TEST verdicts require both registered directions, both senders and their expected sizes; eligibility additionally requires complete conformance records and the current protocol hash.

C. resolved. The freshness wording distinguishes excluded earlier true-rule texts from potentially repeated distractor texts.

D. resolved. The sampling assumption, “can lower” wording and approximately 1.86% bound are stated.

New required changes:

[blocking] Make deadline enforcement cover the entire budgeted stage through summary writing and finalisation. Remove the early cancellation before summarize(); cancel only after completion or exit. Test expiry during analysis/finalisation.

[blocking] Remove the watchdog/main-thread ledger race and make deadline termination independent of successful bookkeeping. Both threads can call Stage.save_ledger(), mutate prior_s/t0 and use the same budget_ledger.json.tmp. A collision can raise before BUDGET_EXHAUSTED is written, after which the watchdog still hard-exits. Blocking ledger or log I/O can also delay the exit indefinitely. Use coordinated, atomic persistence and a termination mechanism that cannot wait indefinitely for bookkeeping. Ensure deadline expiry reliably remains terminal. Add concurrent-save and bookkeeping-failure tests.

[non-blocking] Update config_e1c.json’s verifier_batch_rule and PREREG §4’s remaining batch-switch wording. Both still describe switching T1 to batch 1 after disagreement, contradicting the implemented ineligibility-and-amendment rule.

Optional suggestions:

Persist load timings across attempts too: sizing currently uses the longest load only from the final attempt. State that narrower rule explicitly if retained.

Replace the resumed-sizing test’s list-copy comparison with a genuine interrupted/resumed fixture, and verify latency accounting against the actual batched-generation records.

This review uses only the pasted artifacts; the reported test results were not independently executed.
