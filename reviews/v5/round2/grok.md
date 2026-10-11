# Grok v5 review, round 2 (relayed by the user; summary, not verbatim)

- Grok agrees with all of Grok Bot's self-identified mistakes and with GPT's points.
- On Claude, Grok agrees and adds that answer-held-out accuracy is about 0, which is the stronger claim.
- It found no material disagreement.
- It could not recount t4 or the 23 rejections, because its fetcher returned only t1 rows.
- Missed by all four reviews: glyph_raw_unsnapped was never compared systematically with snapped glyph_id, to see whether the snap discarded sender-specific signal.
- Grok's v6 PREREG proposal:
  1. One mid-depth layer fixed in advance (not a DEV argmax) against an emb baseline, plus J-lens/sparse as a third arm or a pre-registered omission. Report both end-to-end and covered-only results.
  2. LOO with the entry removed from the receiver's book, comparing answer-held-out vs other-held-out vs no-message.
  3. A behaviour gate on the expanded definitions, re-running the planted entries.
  4. Coverage logged for every condition.
  5. Raw residual as its own condition, compared with snapped, expanded-ID and prose.
  6. Receiver compute measured without 64-token padding, in tokens/FLOPs.

  Freeze the layer, the coverage definition and the LOO procedure before TEST.
