# Grok review: E1c T1 results (relayed verbatim by Stefan, 2026-10-16)

Verdict: ACCEPT

The T1 report is correct as written.

1. NOT MET under PREREG §6: Yes. Criteria 1–3 pass in both directions. Criterion 4 (break-even ≤ 1,000) fails in both (1,142 and 1,114). The pre-reg requires all four in both directions. No subset, no direction choice. NOT MET is the right call.

2. Computations faithful to frozen rules: Yes. Bootstrap intervals, coverage, byte savings, and break-even all follow §5–§6. Dictionary is the full 240-entry receiver book plus neighbours (165,969 B). Mean payload saving ~145–149 B. Arithmetic matches the frozen definitions.

3. Independent recomputation: Adequate. Frozen script reproduces the published numbers. Independent script confirms completeness, accuracies, coverage, bytes, dictionary size, and break-even. Bootstrap intervals consistent.

4. Wording free of spin: Yes. Report states the failure is the dictionary cost, not accuracy or coverage. Correctly notes that D2's 10-entry break-even is not comparable, and owns the earlier reporting mistake of citing those D2 numbers without the caveat. No post-hoc reframing.

5. Anything missing that the pre-reg requires: Nothing. Completeness, hashes, TEST book pin, canaries, freeze check, and the four criteria are all reported. Dry-run deviation was already disclosed and accepted earlier.

Blockers: none.

The numbers that matter are clean: hybrid matched or slightly beat prose, zero wrong IDs accepted (verifier caught the 24 wrong picks), coverage above the bar, and real payload savings. The only miss is the dictionary amortisation threshold on a 240-entry book. That is what the pre-reg measured, and the report states it plainly.
