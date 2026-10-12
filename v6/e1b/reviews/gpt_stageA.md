# Review gpt_stageA: E1b Stage A results at `73a528b` (summary relayed by the user)

Relayed 2026-10-12 (AEDT). This is a summary relayed by the user, not a verbatim transcript.

1. **A4's 43% follow rate is an abstention failure.** Qwen got 17/17 right where the changed rule required a different numeric answer, and 0/23 where it required UNKNOWN. It followed numeric changes and failed to abstain; it did not simply "ignore the corruption".
2. **The A2 corrupted-entry percentages are scored against the corrupted (shown) text.** Accuracy above zero there does not show that the corruption was ignored.
3. **Cache:** cold/cold and warm/warm show zero changes, and cold/warm shows 6/100 (Qwen) and 16/100 (Smol). Cold-split vs cached gives identical tokens on all 120 prompts. That localises the divergence to one-chunk vs prefix/suffix-chunk prompt processing, not state restore. Keep the claim withheld.
4. **Do not rerun A6.**
- **Recommendation:** proceed to B0 uncached, keep the leak checks, and test the GPU cache path separately.
