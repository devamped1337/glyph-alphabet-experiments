# GPT review: A10 plan (summary, relayed by Stefan, 2026-10-15)

*Summary of GPT's points as relayed; not a verbatim transcript.*

1. Keep the A9 results and the FAILED verdict. Label A10 as a post-hoc diagnostic completion on an already-seen TEST set; it cannot overturn the two-direction claim.
2. Correct B3_REPORT: wrong selections caused 36 of the 37 errors, and 1 error happened despite a correct selection. Verify this from the raw results at 3973107.
3. Parser fix: don't treat the F in F1/F2 as a standalone choice. Keep rejecting genuinely conflicting choices, and don't broadly accept the first letter. Keep the prompt, generation settings, candidate order, cases and scoring unchanged. This replaces the earlier idea of raising max tokens or changing the prompt.
4. Prefer re-parsing all 60 archived Falcon sender outputs under the frozen corrected parser, then running only the missing Qwen receiver comparison. State explicitly whether the prose arm is rerun or reused. Pin fingerprints for every reused input and result. Don't choose a more favourable sender attempt. Drop the optional symmetric Qwen-sends rerun.
5. Unit tests for unambiguous replies, candidate-ID fragments and conflicting choices. Check both models' sender formatting on non-TEST examples before freezing.
6. A separate results directory, one authorised attempt, a persistent GPU cap of at most 1 h, and cumulative accounting within the existing 12 h allowance. Freeze only after review; launch only on Stefan's explicit go.
