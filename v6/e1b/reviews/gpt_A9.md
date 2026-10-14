# GPT, review of A9 (round 4): SUMMARY

*This is a summary of GPT's round-4 review (key points as relayed by Stefan; the details are in Stefan's paste), not the full text.*

**Verdict: yes-with-changes.**
1. **Projection errors.**
   - Batch-8 latency was used for batch-1 operations: the B1 manipulation check, the B2 paired oracle checks and the cache diagnostic.
   - B3 loads each model twice but budgets only one setup.
   - Illustrative corrections: B1 2.55, B2 5.10, B3 1.31; caps 3.20 / 6.40 / 1.65; total about 11.85 with the B1c cap. Recompute the full projection properly.
2. **Ladder and branch balance.**
   - Prefer dropping F3L before reducing cases.
   - Keep both answer branches within each entry, ideally 2 cases each. At present 3 F1 and 5 F2 entries test only one branch.
   - A rebuild needs a new pinned book hash and renewed freshness and neighbour asserts.
3. **Per-entry bar.**
   - Keep ≥ 22/24 unchanged. Report the eligibility failure and run the predefined ungated comparisons.
   - Ungated results cannot establish a checked repository or corruption protection.
   - The binomial figure is descriptive only, not a forecast.
4. **B1c.**
   - Stratify across both core families and the paths actually batched downstream, especially probes.
   - Describe sender selection accurately as a single run.
   - Parsed decisions are primary; full-token agreement is a diagnostic.
   - Require the expected models, counts and paired keys.
   - **BUG:** `batch_rule` passes 60 × (None, None) and an empty model mapping. Both must fail, with regression tests.
5. **Fresh book:** copying only the canary pool is OK.
6. **Retry rule:** OK.
   - **BUG:** if B2 aborts at the first model load and then resumes, `unknown.jsonl` goes from 48 to 96 rows with only 48 unique keys, and the validator fails. Skip completed keys on resume, and test interrupt → resume → validate.
   - Check prerequisites before consuming an attempt.
   - Enforce stage order.
   - Make access failures and exhausted budgets terminal.
