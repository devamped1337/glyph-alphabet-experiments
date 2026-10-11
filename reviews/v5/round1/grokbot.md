# Grok Bot's v5 review, round 1 (self-review of my own run and write-up)

What I used: the per-query files predictions_qwen.jsonl and predictions_smol.jsonl, frozen5.json, gate5.json, book5.json, det_report.json, TABLES_v5.md, and the code (common5.py, run5.py, negotiate5.py, prereg5.py, spec5.py), all at data commit 48a7a6a5. I also used the round-1 checks now in RESULTS_v5.md. "Recomputed" means I computed the number from the per-query rows. "Read off" means I took it from a table I did not regenerate.

## My mistakes

(a) **I let the depth rule pick the embedding layer, then reported a "glyph failure" without saying so.** The candidate set included "emb", and frozen5.json chose li=0, which is the `embed_tokens` output for both models. RESULTS_v5 never said that li=0 meant the embedding layer. As a result, the contextual/J-space idea was never tested on TEST. The Kaggle 7B v5k run repeats this: it also froze li=0 (DEV 0.850 / 0.802 / 0.774).
(b) **I got counts wrong.** I wrote 22 rejected entries; the correct number is 23/93 (22 in round 0, then Paris in round 1). I wrote "inconclusive on 4" for glyph vs compact; it is 3 inconclusive and 1 equivalent.
(c) **I reported headline LOO scores without the answer-held-out split.** With that split, answer-held-out accuracy is about 0 (0.002 to 0.018), below the no-message baseline.
(d) **I did not log coverage for glyph rows.** `covered` was recorded only for operand_changed, so the glyph_id coverage column falsely reads 1.000.
(e) **I presented t4 as a glyph failure when it was a coverage failure.** Only Lyon and Spain survived negotiation, and covered place messages were 13/14 and 26/28 correct.

## Verdicts on the pre-registered claims

Each claim gives the verdict and its source.

1. **Rule A, task gate:** HOLDS. Read off frozen5.json. t3 is dropped (prose 0.55). Counted tasks: Qwen has 6 and Smol has 5.
2. **Rule B, depth:** HOLDS AS WRITTEN. Recomputed. Pooled DEV glyph_id gives emb 0.750, ~25% depth 0.716, ~33% depth 0.673 (n=776 each). The rule worked as designed, but the rule itself was the problem (see mistake a).
3. **Primary: glyph_id vs text_prose and id_text_expanded:** HOLDS (glyph is worse). Read off the paired tables, with pooled means recomputed. Glyph is worse on 10/11 counted cells; Smol t1|pol is equivalent. Pooled over counted cells:

   | receiver | glyph_id | id_text_expanded | text_prose |
   |---|---|---|---|
   | Qwen | 0.726 | 0.800 | 0.988 |
   | Smol | 0.632 | 0.759 | 0.955 |

4. **glyph vs text_compact:** MIXED. Read off. A better 3, B better 4, inconclusive 3, equivalent 1. Glyph wins only where compact text is weak (Qwen compact pooled 0.827, Smol 0.784).
5. **glyph vs receiver_word_state:** EQUIVALENT. Recomputed. Qwen 0.726 vs 0.728, Smol 0.632 vs 0.631. This is consistent with a lookup.
6. **Sender independence:** HOLDS, but it is built into the design. Recomputed. Predictions agree across senders on 638/646 (Qwen) and 1040/1056 (Smol) messages. The snapped path fetches one fixed shared vector per ID, so this agreement is expected.
7. **Adapter vs nulls:** HOLDS. Recomputed. Raw unsnapped scores Qwen 0.745 and Smol 0.643, similar to glyph_id. The random-orthogonal null scores 0.211 / 0.210. Same-norm shuffled scores 0.231 / 0.198. No message scores 0.248 / 0.172. The shuffled-pair null is partly above chance (0.486 / 0.403).
8. **Gate:** FAILS the pre-registered success rule as a selective filter. Read off gate5.json. Planted rejections are 6/6, but that is 2 designs (Zed, Noise) × 3 depths. The LOO pass rate is 4/141 = 2.8%.
9. **LOO generalization:** FAILS. Recomputed. Answer-held-out accuracy: Qwen agent 0.005, Qwen t2|first 0.005, Smol agent 0.002, Smol patient 0.018. The matching no-message scores are 0.173, 0.127, 0.060 and 0.056.
10. **Determinism:** HOLDS for Smol across box and laptop (max 5.8e-5). Read off det_report.json. Within each host, repeat and reload are bitwise-identical.
11. **J-lens vs PCA vs random:** CAN'T TELL. It was not run (Qwen J-gram OOM, bf16 run killed).
12. **Receiver compute saving:** CAN'T TELL / not shown. Every prompt is padded to 64 tokens.

## Errors in the write-up's own numbers

The errors were 22→23 rejected, 13→12 places rejected in round 0, and "inconclusive on 4"→3+1. Also, the t4 "fails completely" wording had no coverage caveat, and the glyph coverage column overstated coverage. The t5 interval [-0.375, -0.375] is degenerate because there are only 8 status items. Glyph fails "authorized", "not approved" and "valid now"; id_text_expanded fails only the first two. All of these are corrected in the ERRATA and the Round-1 checks.

## What would change my mind

- A contextual-layer channel, fixed in advance and evaluated on TEST against an embedding baseline, that beats id_text_expanded at equal bytes.
- Answer-held-out LOO clearly above no-message on a multi-way slot, with the entry removed from the receiver's book so it has no fallback.
- Raw-residual readout (no snap) that carries sender-specific information the ID does not.
- A real saving in receiver compute at equal accuracy.
