# GPT review of E1f proposal, round 3 (verbatim, at 8fec213)

CHANGES REQUESTED

Reviewed revision 3 at 8fec213. No files modified. The epoch fix and heuristic revision resolve their central concerns; framing and deterministic curation still need corrections before approval.

Q1. Yes: the charged epoch fixes the cross-direction silent-decoding race, provided each epoch is bound to one digest on the link. An old frame either resolves against its actual snapshot or receives E_STALE and falls back.

Two retained snapshots do not cover every potentially in-flight frame: traffic can lag across multiple transitions. Your rejection/fallback rule handles that safely. Correct the sentence claiming the immediately previous snapshot encompasses every snapshot whose frames could remain in flight; two snapshots are a retention policy, not a delivery guarantee.

Q2. The §3.1 varint framing works, but §5.1 still contradicts it by specifying a four-byte prefix “instead of the two-byte one.” This remains blocking.

The §3.5 fixtures are correct under the stated snapshot conditions. I independently checked the four valid bodies:
- abc: 7-byte body; length prefix 07.
- OK: 4-byte body; length prefix 04.
- hidone.: 8-byte body; length prefix 08.
- NO: 4-byte body; length prefix 04.

All listed malformed fixtures have the stated errors. The six-byte ordinal fixture correctly produces E_RANGE before ordinal lookup. “Same bytes with epoch 3” should say “replace the epoch byte 02 with 03.” Also state that S1 is retained for the fixtures expecting errors after epoch validation, and that ordinal 127 is absent.

Q3. Yes. Section 7 is acceptable as a dev-screening heuristic. Its failure no longer purports to prove that compact references lose.

Q4. Partly. The unified version schedule, template grouping, int precedence, endpoint ordering and structural search caps resolve the corresponding round-2 issues. Two curation definitions still prevent a reproducible implementation.

Blocking required changes

1. Apply §3.1 framing consistently in §5.1.
Every prefix must be canonical unsigned LEB128 of the actual encoded frame length, including oversized-message fallbacks. Remove the fixed two-/four-byte language.

2. Define tuning partitions without cumulative-prefix leakage.
“Train on four prefixes, measure on the fifth” is ambiguous because the prefixes overlap. Training on prefix 5 includes all messages in prefixes 1–4. Specify disjoint dev validation blocks and exactly which conversations enter each training set, or define a forward-only validation procedure. Keep the held-out corpus untouched.

3. Make greedy selection computable before the final list exists.
Section 4 estimates ordinal width using “the index in the final list,” but that list depends on the selections being scored. Define a deterministic provisional ordinal-cost rule, or another explicit procedure that resolves this dependency. Also define len(c) for templates: savings must use the matched occurrence’s byte length, since argument lengths vary.

Suggestions, not blockers

- Describe the two-snapshot policy as bounded retention with charged fallback for older epochs.
- Add a fixture crossing a length-prefix boundary, such as lengths 127 and 128.
- Correct the header’s change-map pointer from §10 to §11 for the round-2 resolutions.

I cannot approve the current text. These remaining changes concern contradictory accounting and undefined selection/tuning procedures; the charged-epoch protocol and removal of the proof claim are accepted.
