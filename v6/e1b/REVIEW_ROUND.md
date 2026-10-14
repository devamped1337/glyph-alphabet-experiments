# E1b review round 4b (A9 rev 4b: final yes/no)

- **Pinned commit:** `b3edce69ac2e7ca6212bac04f31aa989687718b3` (code hash `0bbc247a…`)
- **Scope:** a final **yes / no** on A9 as revised ([PREREG_E1b.md §A9](https://github.com/devamped1337/glyph-alphabet-experiments/blob/b3edce69ac2e7ca6212bac04f31aa989687718b3/v6/e1b/PREREG_E1b.md)). Nothing has run, and no Kaggle kernel has been pushed.
- **Round-4 reviews (summaries):** [grok_A9](https://github.com/devamped1337/glyph-alphabet-experiments/blob/b3edce69ac2e7ca6212bac04f31aa989687718b3/v6/e1b/reviews/grok_A9.md), [gpt_A9](https://github.com/devamped1337/glyph-alphabet-experiments/blob/b3edce69ac2e7ca6212bac04f31aa989687718b3/v6/e1b/reviews/gpt_A9.md)

## Changes since round 4 (`c714453`)
1. **Projection corrected (GPT #1).**
   - Batch-1 latency is now used for the B1 manipulation check, the B2 paired oracle and the cold cache runs; warm latency for warm runs.
   - B3 is charged two loads per model.
   - Result: L4 caps are **B1c 0.65 / B1 3.20 / B2 6.40 / B3 1.75 = 12.00 ≤ 12.0** GPU-h, with 9.48 GPU-h projected.
2. **Ladder reordered (Grok, GPT #2).** F3L is dropped first, then cases are cut 10 → 6 → 4 → 2, always even. The first level that fits is **L4: C60, 4 cases per entry, no F3L**. Reduced power is flagged in the headline.
3. **Branch balance (GPT #2).** Every TEST entry has 2 cases on each answer branch. The book was rebuilt and its new sha is `19f8d46da3ff…`. The freshness, neighbour and branch asserts pass, and the frozen book is unchanged.
4. **Per-entry gate dropped for B2/B3: a PI decision by Stefan, made after seeing the qualification scores.**
   - B2/B3 run ungated as the pre-declared comparison. There are no checked-repository or corruption-protection claims.
   - B1 and the ≥ 22/24 bar are reported descriptively.
   - Both positions are recorded: GPT (keep the bar) and Grok (change it or drop the gate).
5. **B1c (GPT #4, Grok).**
   - 60 arithmetic + 60 probes per model, 30 per family each, from the non-TEST qualification pool.
   - Parsed decisions must match 60/60 per path. Expected models, counts and keys are required. Full-token agreement is a diagnostic.
   - Sender selection is described as a single batch-1 run.
   - **Bug fixed:** (None, None) pairs and empty mappings now fail, with regression tests.
6. **Robustness (GPT #6).**
   - **Bug fixed:** B2's `unknown.jsonl` resume no longer duplicates rows (tested: interrupt → resume → validate).
   - Prerequisites are checked before a start is consumed, and stage order is enforced.
   - `NO_ACCESS`, `BUDGET_EXHAUSTED`, `CANARY_FAIL` and `ATTEMPT_INCOMPLETE` are terminal.
7. **Tests:** 95 pass (18 A9).

## Question
**Approve A9 rev 4b for freezing (yes / no)?** If no, name the blocking item.
