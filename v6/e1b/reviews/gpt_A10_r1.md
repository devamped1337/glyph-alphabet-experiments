# GPT review: A10 draft r1 (summary, relayed by Stefan, 2026-10-15). Verdict: CHANGE before freeze

*Summary as relayed; not verbatim.*

**Defect:** after a successful fake-backend B3f→B3r run, removing one copied prose row and regenerating the manifest still passes `validate.run` (240 id_selected vs 239 prose, return code 0, no FAIL lines).

**Enforce in the validator:**
- exactly 60 unique archived selections;
- exactly 240 rows per exchange condition, with matching (entry, case) keys and complete coverage of the scheduled cases;
- copied prose rows equal their pinned source rows, with only the added `reused_from` field allowed;
- exactly 24 scheduled format views per model in B3f.

Add regression tests showing that missing rows and altered copied prose fail validation.

**Text edits:**
- **Q1:** replace "bound that risk" with "provide supporting checks but do not quantify or eliminate cross-session effects"; note that the bootstrap CI doesn't account for possible cross-session bias.
- **Q2:** keep the bar at ≥22/24 plus zero changed previously-accepted decisions. Note the views cover 4 entries (≈20 distinct entry/permutation combinations across 24 views), so they aren't independent semantic tests.
- **Q3:** OK as is.
- **Q4:** put B3r in a separate secondary section, with A9's FAILED verdict prominent; describe the original Falcon direction as a frozen-parser failure with zero ID receiver calls.
- **Q5:** don't freeze yet.
