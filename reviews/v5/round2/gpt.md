# GPT v5 review, round 2 (relayed by the user; summary, not verbatim)

- **Confirmed pooled counts (correct answers):** Qwen prose 638/646, ID expanded 517, glyph 469, word state 470. Smol 1009/1056, 801, 667, 666.
- Against ID-expanded prose, the glyph loses 8/11 cells and is equivalent on 3. Covered places are 92.9% correct.
- Glyph vs word-state agreement is 642/646 and 1048/1056.
- The gate rule was underspecified (it set no numeric minimum), so "fails the prereg rule" is too definite.
- DEV: 582, 556, 522 of 776.
- **Answer-held-out LOO:** Qwen 1/220 vs no-message 38, and 1/220 vs 28. Smol 1/500 vs 30, and 9/500 vs 28.
- **Shuffled-pair null by direction:** Smol→Qwen 22.76%, Qwen→Qwen 74.46%, Qwen→Smol 16.19%, Smol→Smol 64.49%.
- **Missed by all four:**
  1. The place prose baseline uses the literal gold name, which acts as an oracle for 14 Qwen / 30 Smol rows.
  2. Unknown-ID success is a parser test that never calls the model.
  3. The snap silently maps rejected meanings to neighbours, so coverage, selection and decoding need separate fields.
  4. The behaviour gate needs an external correctness check.
- **8-point v6 PREREG:**
  1. Three separate experiments (text repository, snapped lookup, unsnapped contextual) with a fixed mid-depth hook and no DEV argmax between channels.
  2. PCA vs random basis; J-lens only if a feasibility check passes.
  3. Contextual LOO, with the held-out item excluded from dictionaries, prototypes and adapters.
  4. Identical source information for every channel.
  5. A numeric behaviour gate with corruption types.
  6. The whole chain logged, with abstention.
  7. Frozen statistics, and a CI entirely above zero for any win.
  8. Real efficiency accounting, with no padding.
