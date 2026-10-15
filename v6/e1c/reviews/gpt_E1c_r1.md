# GPT review r1: E1c draft pre-registration (via the Codex CLI, 2026-10-15)

*Verbatim reply to REVIEW_ROUND.md r1 (pinned f9c5c54), sent with `codex exec -s read-only`; the PREREG, config and e1c code were pasted into the prompt.*

Verdict: CHANGE.

1. [blocking] Validate the complete assigned TEST dataset before computing any result. entry_diffs checks only equal arm lengths; direction_result derives its denominator from observed rows. Missing entries, duplicated cases or equally truncated arms can therefore produce a successful verdict. Require exactly 240 assigned entries per direction, 120 per family, four specified cases per entry, both arms exactly once, and matching case identities. Incomplete data must produce INCOMPLETE, never SUCCESS.

2. [blocking] Enforce the D1 eligibility rule at T1 start. start currently requires only D1 .done, not a passing wrong-pick-accepted rate or timing projection. Bind T1 authorization to the recorded D1 summary and final frozen configuration, and refuse T1 when either condition fails without a documented amendment. Also specify revalidation after dev-driven verifier or batch-size changes: measurements from the old implementation do not qualify the revised implementation.

3. [blocking] Make retry eligibility enforceable. e1c_state.json counts starts but records no failure classification or permitted retry reason. Any unfinished run without a terminal marker currently qualifies for another start. Persist attempt outcomes and allow the second start only for the registered infrastructure failures. Clarify the apparent conflict between “no GPU” permitting a retry and GPU_PREFLIGHT_FAIL being terminal. Preserve one cumulative stage budget across attempts.

4. [blocking] Supply a regression demonstrating that an accepted wrong pick is scored against the TRUE entry’s gold answers. exchange passes the picked entry into ask_arith_many and subsequently overwrites the entry metadata; the pasted code does not establish which gold that helper uses. Include a deliberately wrong accepted neighbour whose answers differ from the true rule, and verify that both arms use the identical true cases and gold. Otherwise the primary accuracy difference is not auditable.

5. [blocking] Align the verifier parser with the registered strict format. parse_spec accepts multiline explanations, extra keys, and trailing material such as “10 credits …”, selecting the first qualifying line. This contradicts “one strict line” and “a format error causes fallback.” Either enforce the entire response grammar or register the actual permissive grammar before D1. Test contradictory lines, extra keys, duplicate keys and trailing explanations.

6. [blocking] Complete the compute-cap and conformance rules. verifier_b1_check performs model calls without budget checks and calls generate_batch on 16 jobs without explicitly establishing batch 8. Use the production batching path with explicit batch sizes and budget checks. Predeclare what happens when batch-1 and batch-8 disagree; merely logging disagreement does not resolve the stated rationale for deterministic execution order. Account for maximum in-flight work when enforcing the hard cap.

7. [blocking] Define the communication boundary for byte accounting. Every bytes_record call leaves sender_wire_bytes at zero, despite sender candidate preparation and verifier traffic. State explicitly whether these are local computation or transmitted communication. If local, label the reported quantity as receiver payload plus case bytes; if transmitted, include the applicable traffic. Define a “message” as one case exchange or one four-case entry, and make dictionary amortization use that same unit. The 30% and 1,000-message criteria need an unambiguous interpretation.

8. [non-blocking] Correct the freshness specification. check_fresh permits new neighbours to reuse old non-neighbour text and new cores to reuse old neighbour text. The prose describes the relaxation as neighbour-to-neighbour reuse. Align the implementation, builder constraints and registration, with cross-kind regression cases. Explain the consequences for task freshness.

9. [non-blocking] Make freeze artifacts unambiguous. “Tag again” leaves unclear whether prereg-e1c is moved after adding the TEST-book hash. Specify immutable registration and execution commits/tags, with the execution commit binding the frozen configuration, book hash and code hash. Replace “nothing on the TEST book is looked at” with an explicit allowance for automated construction, integrity and freshness checks.

Optional suggestions:

- The paired, family-stratified entry bootstrap and requirement to pass both directions are appropriate. Specify the percentile-index convention used by the code.
- Report the wrong-pass numerator and denominator plus an uncertainty interval. With 80 entries, the ≤2% gate permits at most one wrong acceptance; it does not establish a population rate ≤2%.
- Treat same-model verifier dependence as a limitation throughout reporting. Neighbour-rejection unit tests establish deterministic matching behavior, not independent semantic verification.
- The sizing arithmetic is consistent if rv means seconds per case across both arms; correct its misleading “item pair” comment. The projection should also disclose its dependence on dev coverage and prompt-length mix.
