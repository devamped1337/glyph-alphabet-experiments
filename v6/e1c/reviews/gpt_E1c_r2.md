# GPT review r2: E1c draft pre-registration (via the Codex CLI, 2026-10-15)

*Verbatim reply to REVIEW_ROUND.md r2 (pinned c6ffaa2), sent with `codex exec -s read-only`. The PREREG, config, e1c code, tools, tests and GPT's own r1 review were pasted into the prompt.*

Verdict: CHANGE.

1. not resolved. Receiver-row completeness is substantially fixed, but selection JSONL rows are collapsed into a dictionary before validation. Duplicate selections disappear, extra selections are ignored, and direction_result does not validate selection completeness. Require exactly one selection row per assigned entry, no extras, before computing results; failures must yield INCOMPLETE.

2. not resolved. The protocol hash hardcodes sender_max_new=4 while generation uses cfg["sender_max_new_tokens"]; changing the actual limit need not invalidate D1. It also omits the effective verifier batch size. When conformance fails, T1 switches to batch 1 although D1’s acceptance screen was measured at batch 8. Qualify the actual configuration and recompute the screen under the batch-1 reference path before authorising T1.

3. not resolved. Authorisation accepts any listed reason without checking its consistency with the recorded outcome; GPU_PREFLIGHT_FAIL can receive reasons other than no_gpu. More materially, resumed selections can combine attempts with different protocols because stored code hashes are never checked for compatibility. Validate failure/reason consistency, reject non-finite charged_h, and bind reused results to the qualifying protocol. Manual log-based classification of an otherwise unrecorded infrastructure failure is reasonable if explicitly recorded.

4. resolved.

5. not resolved. Full-response matching fixes the main issue, but Python \d accepts Unicode decimal digits whereas the registered grammar specifies [0-9]. Replace \d with [0-9] and add a Unicode-digit rejection test.

6. not resolved. Explicit batching and the disagreement rule improve conformance, but a prior or 1.2 × observed maximum is an estimate, not an upper bound. A slow first load or chunk can exceed the purported hard cap after passing the guard. Either implement an enforceable deadline that accounts for termination, or register the guard honestly as estimated admission control with possible overrun and an explicit overrun outcome.

7. resolved.

8. resolved. The cross-kind relaxation and dev-core-only exclusion are now explicit and tested. The freshness claim still needs the wording correction below.

9. resolved. The two immutable tags and permitted execution diff resolve the original ambiguity.

New required changes:

[blocking] Make sizing valid after a retry. Resumed send_and_verify skips completed entries, but sizing divides the current attempt’s elapsed time by all dev entries. Completed receiver work is likewise omitted from timing while its rows remain in the denominator. This can materially underproject T1. Persist work counts and timings across attempts, or estimate from measured completed units with explicit denominators.

[blocking] Validate the exact expected summary structure for eligibility and verdicts. all(...) over supplied dictionaries accepts missing directions/models, including empty dictionaries. The eligibility test even treats a one-direction, one-model summary as qualifying. Require both registered directions, both senders, expected sample sizes, and complete conformance records before accepting D1.

[non-blocking] Correct §3’s statement that every TEST true rule is “new to E1c and E1b.” A true rule may repeat an earlier distractor’s text. Say that true rules exclude the specified prior true-rule texts, while cases are fresh under the registered checks. Stateless inference prevents retained conversational context; it does not make previously presented text historically unseen.

[non-blocking] Qualify the dev-power language. The 0/160 one-sided Clopper–Pearson calculation is correct, and the observed ≤2% screen correctly permits at most three events. However, the population-rate interpretation assumes an appropriate binomial sampling model; these are generated, family-balanced entries. Also replace “an accepted wrong pick lowers hybrid accuracy” with “can lower hybrid accuracy”: differing rules need not change a particular scored answer.

Optional suggestions:

- Extend freeze checking to verify that the registration commit contains no TEST book and that the execution book’s actual digest matches its pins.
- Add focused regressions for duplicate selections, missing summary components, resumed-run sizing, batch disagreement with changed acceptance decisions, and actual sender-token-limit changes.
- Report the bound as approximately 1.86% for 0/160, with its sampling assumptions stated.
