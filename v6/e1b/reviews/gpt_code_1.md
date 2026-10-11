# Code review gpt_code_1: E1b implementation at `6e2636d` (summary relayed by the user)

Relayed 2026-10-12 (AEDT). This is a summary relayed by the user, not a verbatim transcript. GPT read the code at `6e2636d`, ran the 21 unit tests, and built counterexamples.

**Bugs found:**
1. **CRITICAL: the gate scored against `gold`.** `gold` comes from the shown text, which may be corrupted. The gate should score against `honest_gold`. A simulated perfect reader was accepted on 100/100 honest entries and 40/40 planted entries. Fix: keep separate fields. The gate uses `honest_gold`; the comprehension and manipulation diagnostics use `gold`.
2. **Seeds were not reproducible across processes.** A set was sorted with random keys, so outputs differed between PYTHONHASHSEED=1 and 2. Fix: sort deterministically first, and add a cross-process test.
3. **`verify()` did not check role/number binding.** Swapping the member and non-member rates still passed. Fix: parse which rate belongs to which role, and read the quantities from the question.
4. **The validator passed an empty results dir.** Fix: make it stage-aware (valid inputs, explicitly incomplete, or a complete stage with the expected files, row counts and unique keys).
5. **Cache agreement counted pred=None==None as a match.** Fix: require valid parsed predictions; report invalid ones and withhold the claim.

**Also to fix:**
- `pilot_timing` used core TEST entries; it should use separate pilot entries.
- Neighbours were absent from calibration, so a gated B3 would reject every neighbour. Include the candidates consistently.
- `Dictionary.resolve` used the hidden `kind=='planted'` label; it must use the recorded gate decision.
- Budgets must persist cumulatively across restarts, with B0b sharing B0's allocation.
- Compare canaries record by record, not by total.
- Count dictionary setup as the full predefined dictionary, including candidates.
- Finish the HF revision pins and GGUF verification before any GPU use.
