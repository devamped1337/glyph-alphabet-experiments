# v5 round-1 reviews: all four

- v5 report: https://github.com/devamped1337/glyph-alphabet-experiments/blob/main/RESULTS_v5.md (originally committed at bcd2058b)
- Data commit: 48a7a6a5faff09d6de4f8fef8773d9419a248a3e
- Raw data: [predictions_qwen.jsonl](https://raw.githubusercontent.com/devamped1337/glyph-alphabet-experiments/48a7a6a5faff09d6de4f8fef8773d9419a248a3e/v5/results/predictions_qwen.jsonl), [predictions_smol.jsonl](https://raw.githubusercontent.com/devamped1337/glyph-alphabet-experiments/48a7a6a5faff09d6de4f8fef8773d9419a248a3e/v5/results/predictions_smol.jsonl), [TABLES_v5.md](https://raw.githubusercontent.com/devamped1337/glyph-alphabet-experiments/48a7a6a5faff09d6de4f8fef8773d9419a248a3e/v5/results/TABLES_v5.md), [EXTRA_TABLES_v5.md](https://raw.githubusercontent.com/devamped1337/glyph-alphabet-experiments/48a7a6a5faff09d6de4f8fef8773d9419a248a3e/v5/results/EXTRA_TABLES_v5.md), [frozen5.json](https://raw.githubusercontent.com/devamped1337/glyph-alphabet-experiments/48a7a6a5faff09d6de4f8fef8773d9419a248a3e/v5/results/frozen5.json), [gate5.json](https://raw.githubusercontent.com/devamped1337/glyph-alphabet-experiments/48a7a6a5faff09d6de4f8fef8773d9419a248a3e/v5/results/gate5.json), [book5.json](https://raw.githubusercontent.com/devamped1337/glyph-alphabet-experiments/48a7a6a5faff09d6de4f8fef8773d9419a248a3e/v5/results/book5.json), [det_report.json](https://raw.githubusercontent.com/devamped1337/glyph-alphabet-experiments/48a7a6a5faff09d6de4f8fef8773d9419a248a3e/v5/results/det_report.json)

Each review appears below unchanged, with the commit that added it.

---

## GPT: reviews/v5/round1/gpt.md (commit 7a269a9)

I checked the code and independently recomputed the headline accuracies from both prediction files. Bot's main conclusion holds: this implementation hasn't earned the extra machinery of vector injection. But I found several important qualifications.

The biggest one: v5 selected the embedding layer. The frozen depth is li=0, which the code maps to emb—before contextual processing. It also reads only the last token of each slot value. That severely limits what this run can demonstrate. For example, reading the final token of "approved" and "not approved" at the embedding layer cannot capture the preceding negation. Likewise, the final word of a geographical clue isn't a contextual representation of the place it describes. So this is chiefly an embedding/codebook experiment. It hasn't tested the proposed contextual J-space channel.

The place result is mostly dictionary rejection—and we can recover the missing coverage without another model run. Reconstructed original-message coverage: Qwen place messages covered 14/110, correct among covered 13/14 (92.9%), overall 11.8%; SmolLM2 28/210, 26/28 (92.9%), overall 12.4%. Only Lyon and Spain survived negotiation. Those conditional results are small and restricted to two places; they don't establish broad transfer. But describing the entire collapse as poor injection would misdiagnose it.

There's also a counting correction: 23 of 93 entries were ultimately rejected, leaving 70. Twenty-two disappeared in round zero, then Paris disappeared in round one.

Sender independence is largely built into the snapped channel. I reproduced 638/646 matching sender predictions for Qwen and 1040/1056 for SmolLM2. But the code explains why: after selecting an entry, it retrieves that entry's fixed shared vector. Whenever both senders choose the same ID, the receiver receives the same vector. That establishes the behaviour of this lookup architecture; it doesn't establish that activation transfer generally cannot work.

The strongest negative result is the fair ID comparison. For Qwen, using the same selected IDs: Who acted: injection 85.5%, prose expansion 100%. Who acted first: injection 94.5%, prose expansion 100%. Status: injection 62.5%, prose expansion 75%. Same transmitted ID payload; different receiver representation. Ordinary text expansion wins.

The gate needs a more precise verdict too. Six planted rejections represent two bad-entry designs tested at three depths. Meanwhile, only 4/141 held-out entry/depth cases passed. That shows weak generalization to held-out entries—not a demonstrated selective validator.

For the pending 7B run, I'd want embedding and contextual-layer results reported separately, raw transfer separated from snapped lookup, and coverage reconstructed before interpreting failures. Every receiver prompt here was padded to 64 tokens, so v5 also hasn't demonstrated a receiver-compute saving.

Your shared repository remains a viable protocol idea. What v5 removed is the evidence that injecting its vectors improves on expanding its IDs into text. That's a useful, concrete result—even with rocket parts scattered everywhere.

---

## GPT follow-up (note): reviews/v5/round1/gpt_followup.md (commit dd20672)

# GPT review round 1: follow-up correction (2026-10-11)

Note recorded by Grok Bot from GPT's follow-up, relayed by Stefan. GPT's points as relayed:

> Contextual layers DID run on DEV (pooled DEV: emb 75.0%, ~25% depth 71.6%, ~33% depth 67.3%), so the pre-registered rule correctly selected emb for TEST.

Verification at 48a7a6a5: recomputed with the prereg5.py Rule B logic (glyph_id rows on counted tasks, pooled over both receivers, from v5/results/dev_qwen.json + dev_smol.json): emb 0.7500, li1 (qwen L9 / smol L6) 0.7165, li2 (qwen L12 / smol L8) 0.6727, n=776 per depth. Matches frozen5.json. Per receiver: qwen 0.785/0.757/0.715, smol 0.707/0.667/0.621. CONFIRMED.

---

## Claude: reviews/v5/round1/claude.md (commit 75a8e04)

Claude's v5 review. What I read: PREREG.md, TABLES_v5.md, first ~18 t1|agent messages of predictions_qwen.jsonl, then RESULTS_v5.md last. Did not read predictions_smol.jsonl, gate5.json or EXTRA_TABLES; nothing recomputed; arithmetic by hand; had seen Bot's chat summary first.
Verdicts: Rule A prose gate holds (maths dropped, prose 0.55). Primary glyph vs prose and ID-expanded holds: worse on 10/11 counted cells, Smol t1|pol equivalent, diffs -0.012 to -0.264; in t1/t2 id_text_expanded == text_prose. Glyph vs compact: A better 3, B better 4, remaining 4 = 3 inconclusive + 1 equivalent (Bot said inconclusive on 4). Lookup claim holds: glyph matches receiver word state at 0.000 diff on almost every cell; glyph_id identical across senders in rows read. Gate: planted 6/6, LOO pass 4/141 = 2.8%; if the gate rejects nearly everything, planted rejection shows nothing about selectivity, so the prereg success rule isn't met. Determinism: can't tell.
Errors/gaps: 1) LOO looks like an artifact: each message has two LOO rows, one where the held-out symbol is the answer, one where it is the other entity. In all 18 messages read, the answer-held-out row was wrong (receiver named the other person); the other row usually right. So headline LOO (Qwen agent 0.43, Smol agent 0.35) mostly measures how often the held-out symbol was irrelevant. Split by loo_symbol == gold; expect ~0 on multi-way slots. Binary slots (Qwen pol 0.97) need the same split. 2) t4|where is coverage failure: glyph, id_text_expanded, receiver_word_state all 0.124/0.118 vs prose 1.00; implies ~0.8 accuracy on covered places; 'fails completely' overstates. 3) Effective n small: t5 CIs degenerate [0.625,0.625]; really 8 status items (glyph 5, id_text 6, prose 8); list which fail; t4 has 15 places. 4) Seeds add little (SD ~0.001; Qwen one seed). 5) J-lens didn't run; dev accuracy fell with depth (0.750, 0.716, 0.673).
Under-reported: raw cross-model vectors through the fitted adapter match the receiver's own accuracy (Smol 0.672 vs 0.676; Qwen 0.855 vs 0.855); random/shuffled adapters fall to no-message (~0.13), so the adapter aligns states both ways. Probably near-embedding word-state alignment; question: what layer is li=0? Operand-change and slot-swap follow rates 0.73-0.99: receiver reads the specific entry, which a lookup satisfies too.
What would change my mind: answer-held-out LOO clearly above none on a multi-way slot; glyph beating id_text_expanded at equal bytes or cutting receiver compute at equal accuracy; a J-space comparison using sparse nonnegative reconstruction at mid-depth as well as the frozen one, with J-space beating PCA/random of the same size.
Agreement/next step: the vector part hasn't earned its place; evidence for the repository is id_text_expanded ~= prose wherever an entry exists; the binding problem is coverage (22/93 rejected [actually 23], 97% of honest held-out entries failed the gate). That gate checks vector geometry, which the text path doesn't need. For the text repository, gate on behaviour instead: do both models act the same on the expanded definition across fresh test cases? Then re-run the planted bad entries against that gate.

---

## Grok (relayed summary): reviews/v5/round1/grok.md (commit 156f0d2)

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

---

## Grok Bot: reviews/v5/round1/grokbot.md (commit e524962)

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
