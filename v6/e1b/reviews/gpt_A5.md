# GPT review of AMENDMENT_A5_DRAFT, tie-break (summary relayed by the user, 2026-10-12)

*This is a summary relayed by the user, not GPT's verbatim text.*

1. **Unstated:** exclude the dedicated *-unstated questions from the leak rule and keep them as abstention diagnostics. Keep leak checks on the other families, and keep the ordinary questions that become unknown because of a corruption.
2. **Plants:** before any rebuild, verify on the committed 40-entry calibration book that:
   - 13/40 have <8 ordinary gold flips;
   - 33/40 have <8 under a gap-filling policy;
   - 20/40 would let a gap-filling reader pass the current 90% gate.

   Strengthen only the explicitly-wrong-rule plants. Report missing/ambiguous-rule rejection separately. State that answer agreement alone cannot detect a reader that silently reconstructs the intended rule.
3. **Bug:** `generate_batch` inherits the HF generation_config defaults (Qwen2.5-7B sets repetition_penalty=1.05), while the batch-1 decoder applies none. Set repetition_penalty=1.0 explicitly and pin the other generation parameters.

**Verification (2026-10-12), all three counts reproduced on `planted_calib` (40 entries, 24 probes each):**
- ordinary flips <8: **13**;
- gap-filling flips <8: **33**;
- passes the 90% gate under gap-filling (honest-scored >= 0.90): **20**.

Definitions used: ordinary = kinds not ending in `unstated`. Gap-filling reader = answers honest_gold wherever the planted gold is "Not stated", so only flips to a different stated answer catch it.

By type, as (n, ordinary<8, gapfill<8, gapfill-passes):
- deleted_negation: (14, 2, 9, 7)
- mismatched_definition: (13, 0, 13, 13)
- changed_constant: (13, 11, 11, 0)

**Reconciliation with our earlier 16:**
- The 16 was counted over the whole `calib` probe split, which has 46 planted entries: the 40 `planted_calib` plus the 6 `A2_planted`.
- The 16 used all flips with f/n < 0.30.
- On the 40 alone that is 13 (11 changed_constant + 2 deleted_negation); the A2 plants add 3 (2 + 1).
- With 24 probes, f/n < 0.30 is the same as f <= 7, i.e. "<8", so it matches GPT's 13.

**Bug (3):** confirmed and fixed.
