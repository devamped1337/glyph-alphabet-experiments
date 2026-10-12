# Claude review of AMENDMENT_A5_DRAFT (summary relayed by the user, 2026-10-12)

*This is a summary relayed by the user, not Claude's verbatim text.*

1. Rebuild the 16 weak planted calibration entries with a fractional rule: flipped probes f/n >= 0.30 (8/24, or 6/20), with >=3 entries per calibration corruption type. TEST plants stay untouched. This is a builder-only property, so a dated amendment before B1 is enough.
2. Withdraws P6: keep the leak rule as frozen. Add reporting only: the no-text "Not stated" rate by kind, and with-text abstention on deleted-info plants.
3. Settle P1 and P4 after B0 and before B1.
4. Batching needs its own review: left padding with attention mask and positions, per-row stop, the pad token, and deterministic batch composition (sorted by length, fixed seed) with the batch index logged. Compute byte-identical prompts once and reuse the result for both B2 arms (id_oracle and direct_text).
5. Add reserve probe templates for the other kinds, since 20 probes is exactly the minimum.
6. The B0 pilot should test several batch sizes and freeze the largest one that matches batch-1 on >=99% of non-TEST items.
7. P4 table at n=20 (>=18/20 needed): p=0.90 gives 68%, 0.93 gives 84%, 0.95 gives 93%, 0.97 gives 98%.

**Verification (2026-10-12):**
- (7) The arithmetic checks out: 0.677 / 0.839 / 0.925 / 0.979. Note that entries currently have 24 probes (>=22/24 needed), which gives 0.564 / 0.766 / 0.884 / 0.966. n=20 applies only if B0b drops the unstated kind.
- (1) "16" is right on the full `calib` probe split, which is 46 planted entries: the 40 `planted_calib` entries plus the 6 A2 plants. On the 40-entry calibration book alone it is 13 (11 changed_constant, 2 deleted_negation). See GPT's A5 review.
