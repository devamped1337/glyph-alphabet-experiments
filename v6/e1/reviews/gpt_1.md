# Review gpt_1: v6 E1 calibration (relayed summary)

Relayed 2026-10-11 (AEDT). This is a summary of the reviewer's points, not a verbatim transcript.

1. **Reproduced honest-entry accuracy** (mean over 8 entries, %): F1 Qwen 98.6 / Smol 40.1; F2 74.0 / 46.6; F3 19.1 / 10.8.
2. **Scope of E1:** the sender is given the correct ID. E1 is therefore an **oracle-ID receiver test** and says nothing about selection. The "sender time" it reports is only string formatting.
3. That the trailing `Answer:` causes the F3 failures is a **hypothesis**, not a finding.
4. **The "~25-token" claim is wrong.** Qwen: 295/800 F3 replies are longer than 25 tokens (max 100). Smol: 212/800 (max 96).
5. **Fee omission explains 141 of 647 Qwen F3 failures (~22%)**, not the bulk of them.
6. Calling anything "coin-flip" is unjustified for integer answers.
7. **The cached condition repeats the identical prompt.** That is repeat-request caching, not prefix reuse. FLOPs are computed from total tokens even when the prompt is cached. A fair comparison would need prose with matching caching.
8. Qwen also fails F2 and F3, so the limit is not purely SmolLM2.
9. **Agreement is not capped by the weaker model's accuracy:** the models can agree on wrong answers.
10. Add diagnostic checks that skip the arithmetic (e.g. ask only which rule applies).
11. Let the run finish. Pre-register repairs separately.
