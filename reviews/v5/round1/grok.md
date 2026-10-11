# Grok v5 review, round 1 (SUMMARY relayed from Grok, not verbatim)

These points were relayed as a summary and are quoted as faithfully as that allows:

- glyph_id matches receiver_word_state (638/646 Qwen, 1040/1056 Smol), so it is a lookup, not a transfer.
- id_text_expanded matched or beat the glyph.
- Prose won every counted comparison.
- Compact text only lost where it was already broken.
- The place collapse is coverage. Grok says 22/93 entries were rejected, including most places plus Paris. (Editor's note: the corrected count is 23/93; see RESULTS_v5.md ERRATA 2.)
- The gate caught 6/6 planted entries, but the LOO pass rate was 2.8%.
- The real adapter beat random.
- Determinism held on Smol.
- J-lens never ran.
- In the raw rows: the random basis collapses to a frequent default name (Bob/Alice); the snap discards any residual sender structure; id_text_raw often defaults to Bob.
- Recommendation: to test real transfer, remove the receiver's fallback. Either hold the test entry out of the receiver's book, or force readout from the raw residual instead of the snapped ID. Otherwise the 7B will repeat the pattern.
