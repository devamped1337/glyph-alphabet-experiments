# E1c REVIEW_ROUND r2 (draft pre-registration after GPT r1), pinned commit c6ffaa2

## Ask
Re-review the E1c **DRAFT** after the r1 fixes. Verdict: ACCEPT (D1 may be proposed to Stefan for a go) or CHANGE (required edits). For each r1 item (1–9), say whether it is resolved.

## Context
- r1 (`reviews/gpt_E1c_r1.md`, at f9c5c54) returned CHANGE: 7 blocking items and 2 non-blocking.
- Stefan also asked for an honest treatment of the dev power point: enlarge dev if the budget allows, or reword the gate. Both were done: dev went from 80 to **160 entries per sender**, and the 2% gate is now a screen.
- Unchanged: E1b A9 = POC FAILED; A10 B3r = INCONCLUSIVE; models Qwen2.5-7B and Falcon3-7B; free T4; D1 cap 0.5 GPU-h.

## Artifacts (at c6ffaa2), mapped to the r1 items
1. **Completeness.** `analysis.check_complete` and `direction_result` require rows to equal the assignment exactly: entries, cases by text, both arms once, registered gold, no extras or duplicates. Otherwise the status is INCOMPLETE. `stages.verdict` also returns INCOMPLETE if any selection is incomplete. Coverage uses the assigned denominator.
2. **T1 eligibility.** `stages.t1_eligibility`: D1 done and complete, screen passed, projection ≤ T1 cap, and **D1 protocol_hash == current**. The hash covers the sender prompt and token limit, the A10 parser, the verifier prompt, format, grammar and token limit, and the receiver batch size. A change means a new dev stage; there is no override. Exit 19.
3. **Retry.** `e1c_state.json` keeps attempt records with outcomes. A second start needs a retry authorisation (`tools/authorise_retry.py`) with reason ∈ {no_gpu, install_or_network, kernel_crash, oom_at_load} and charged_h > 0. GPU_PREFLIGHT_FAIL is an infrastructure failure, not terminal; BUDGET_EXHAUSTED, CANARY_FAIL and ATTEMPT_INCOMPLETE are terminal. There is no third start. Ledger = max(ledger, charged_h), so the budget is cumulative. The retry kernel overlays results from `E1C_RESULTS_COMMIT`.
4. **True-case scoring.** The receiver row asserts gold == registered case gold, case == true case, and `rule_entry` is logged. A new regression test has the fake sender pick a load-bearing neighbour and the verifier accept it. The test checks:
   - hybrid sends the neighbour's ID;
   - both arms use the true cases and gold;
   - `correct == score(pred, true gold)`;
   - the neighbour changes gold on at least one case.
5. **Strict grammar.** `verifier.GRAMMAR` is a full-response fullmatch, with keys in order, `[A-Za-z]+` names and `-?\d+` integers. The tests cover multiline replies, explanations, duplicate lines, extra keys, duplicate keys, units, trailing punctuation, articles, reordered keys and wrong-family keys. PREREG §4 registers this grammar.
6. **Batching and cap.** `run_verifier` uses the production `batched_generate` with an explicit batch size. The batch-1 check is budget-guarded. Pre-declared rule: any difference in the batch-8 vs batch-1 check means the T1 verifier runs at batch 1, and the projection uses batch-1 timing. An in-flight `guard` runs before every load, call or chunk, using its estimate = max(prior, 1.2 × longest observed). Tests cover the batch size ≤ 8 and the guard (stops before the first load).
7. **Bytes.** The channel is sender → receiver; candidate prep and the verifier are sender-local. Message = one case exchange. Payload saving is the criterion; break-even is counted in the same unit; "message bytes" (payload + case) are reported only. Tested.
8. **Freshness.** The `check_fresh` docstring and PREREG §3 state exactly rules (a)–(d), with cross-kind tests. The dev book's forbid list is limited to its 160 E1c core rules. Feasibility: 3 of 10 throwaway seeds build a TEST-size book, so the seed rule (+100 steps, mechanical, logged) is expected to fire.
9. **Freeze.** Two tags that never move: `prereg-e1c` (registration: frozen, TEST sha null) and `e1c-t1-exec` (execution: a descendant that may touch only the TEST book files, config `test_book_sha256` or the seed-rule generator, and CODE_HASH.txt). The rule is checked by `tools/check_freeze.py` and unit-tested. Only automated construction, integrity and freshness checks may touch the TEST book.
- **Dev power.** Dev went from 40 to 80 per family, i.e. 160 per sender. The 2% rule is a screen (at most 3 of 160). It counts as "shown ≤ 2%" only if the Clopper–Pearson 95% upper bound is ≤ 2% (0 of 160). The summary reports k, n and the bound. The D1 estimate is about 0.42 GPU-h of the 0.5 cap; the guard stops cleanly if it runs over.
- **Optional r1 suggestions taken:** the percentile convention is specified; the sizing comment is fixed (rv = seconds per case, both arms); the projection's dependence on dev coverage, prompt-length mix and timing is disclosed; same-model verifier dependence stays a stated limitation.
- **Tests:** E1c 25 OK (from 14); E1b 112 OK (unchanged). Kernel `e1c_D1` is prepared and **not pushed** (E1C_COMMIT=SET_ME).

## Scope
In scope: whether r1 items 1–9 are resolved; any new problem introduced by the fixes (especially the freshness relaxation, the retry procedure, eligibility, the in-flight guard and the grammar strictness); and the dev-power wording.
Out of scope: E1b conclusions, model choice, posting.

## Output
Verdict (ACCEPT / CHANGE). Then items 1–9, each marked resolved / not resolved, with a reason if not. Then any new required changes, marked [blocking] or [non-blocking]. Then optional suggestions. Plain text.
