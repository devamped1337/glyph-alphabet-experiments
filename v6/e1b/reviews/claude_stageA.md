# Review claude_stageA: E1b Stage A results at `73a528b` (summary relayed by the user)

Relayed 2026-10-12 (AEDT). This is a summary relayed by the user, not a verbatim transcript.

1. **A4 by corruption type:** changed_constant 4/4, swapped_roles 10/10 and inverted_comparison 3/3 were followed; deleted_negation 0/10, mismatched_definition 0/10 and near_miss_polarity 0/3 were not. This is **gap-filling, not ignoring**. Proposals:
   - raise the builder guarantee to a gap-filling reader (one who guesses among non-abstain options), with rejection required by a margin, e.g. ≥8 of 24 probes flipped;
   - run an exploratory abstention-instruction prompt test on Qwen-3B CPU (~40 calls, logged as exploratory, no claims), with the chosen prompt frozen by a dated amendment before B;
   - report B1 planted rejection per corruption type.
2. **The entry bar is inconsistent with qualification:** at 24 probes, 0.90 means ≥22/24, and a model with p = 0.90 per-probe accuracy clears only ~56% of entries (binomial). Options: more probes, a binomial entry test, or a higher qualification bar, decided together with (1).
3. **Cache:** use warm vs cold-split as the primary state-restore check and report cold vs split as chunking sensitivity, keeping the strict rule alongside, by dated amendment. Note the 6–16% chunking noise floor.
- **Smaller points:**
  - treat the *-unstated no-text "leaks" as an abstention diagnostic, excluded from the leak rule;
  - report the share of rows whose first and last integers after `Answer:` differ, with >2% as a prompt-fix trigger in B0.
