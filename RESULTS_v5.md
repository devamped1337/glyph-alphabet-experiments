# v5 results: glyph codebook transfer between SmolLM2-1.7B and Qwen2.5-3B

## ERRATA (2026-10-11, from GPT review round 1, reviews/v5/round1/gpt.md)

1. **The frozen depth is the embedding layer.** frozen5.json has li=0. In common5.py, `layer_keys()` returns `["emb", ...]`, and "emb" is the output of `embed_tokens`, before any transformer block. The layer keys in book5.json are qwen `['emb', 9, 12]` and smol `['emb', 6, 8]`. States are read at the last token of each slot value (`Runtime.positions`). So v5 tested a **word-embedding codebook**, not a contextual/J-space channel. For example, the last token of "not approved" at the embedding layer cannot carry the negation. Nothing below shows anything about contextual-layer transfer.
2. **Rejection count was wrong.** It was **23 of 93** entries, not 22, leaving 70 (gate5.json, book `0|pca|0`). Round 0 rejected 22: 8 t3 operands, **12** places (not 13) and 2 t5 statuses ("authorized", "not approved"). Round 1 rejected Paris, so 13 places were rejected in total. Round 2 rejected none.
3. **Place (t4) coverage, rebuilt from the predictions plus the book.** Only `t4|place|Lyon` and `t4|place|Spain` survived. Counts are per sender (glyph_id, pca seed 0, li=0), and both senders give identical numbers:
   - Qwen receiver: 14/110 covered, 13/14 correct among covered (92.9%), 11.8% overall.
   - SmolLM2 receiver: 28/210 covered, 26/28 correct among covered (92.9%), 12.4% overall.
   Every correct t4 answer was a covered one. The t4 collapse comes mainly from dictionary rejection, not bad injection. The conditional accuracy covers only two places, so it does not show broad transfer.
4. **Sender independence is built into the snapped path.** `run5.py:shared()` looks up a fixed shared vector for each chosen book ID (`b["shared"][k]`). When both senders pick the same ID, the receiver gets the identical vector. Matching predictions across senders therefore describe the lookup design. They are not evidence about activation transfer in general.
5. Also worth knowing: every prompt is padded to exactly 64 tokens (`spec5.CTX = 64`, asserted in `ids64`), so v5 shows no saving in receiver compute. The 6/6 planted rejections are 2 designs (Zed, Noise) × 3 depths. They are not 6 independent bad entries.


Data commit: **`48a7a6a5faff09d6de4f8fef8773d9419a248a3e`**. Run code: v5.4 `6e3f6a2`, plus the analysis fix in `48a7a6a5faff09d6de4f8fef8773d9419a248a3e` (see deviation 7).
Receivers: SmolLM2-1.7B (box, N_TEST=250, seeds 0/1/2) and Qwen2.5-3B (laptop i5-8350U, N_TEST=110, seed 0). Qwen TEST took 43,260 s (12.0 h) and finished cleanly at 14:34 AEDT on 2026-10-11.

## Bottom line
1. **The glyph never beats prose.** On every counted task the glyph is worse than plain prose (paired 95% CI entirely below 0), except one: SmolLM2 t1|pol, where it is *equivalent*. It is also worse than the same ID expanded to a prose sentence (`id_text_expanded`) on every task except t4, where both fail.
2. **The glyph beats compact text only where compact text is weak**: Qwen t1|mod +0.19 and t2|first +0.39, SmolLM2 t1|agent +0.19. It is inconclusive on 4 cells and loses badly on t4|where (-0.88) and t5|status (-0.38).
3. **The "transfer" is a lookup.** The snapped `glyph_id` matches `receiver_word_state` (the receiver's own word state) exactly: paired difference 0.000 on almost every cell. It is also the same for both senders (638/646 identical predictions on Qwen, 1040/1056 on SmolLM2), and the 3 seeds agree to within SD 0.001. After snapping, the result reflects the receiver's dictionary, not information carried from the sender.
4. **t4|where (places) fails completely**: 0.12 end-to-end on both receivers, against 1.00 for prose. 23 of the 93 entries were rejected in book negotiation, mostly places (round 0 rejected 12 place entries plus 8 t3 operands and 2 t5 statuses; round 1 rejected Paris). [corrected, see ERRATA]
5. **The gate rejects planted bad entries (6/6), but it rejects almost every honest held-out entry too.** The LOO gate pass rate is **4/141 = 2.8%**. Pre-registered success required planted rejection *and* LOO passing at a reported rate, so the gate does not work as a selective filter.
6. Determinism passed: SmolLM2 box vs laptop max |dlogit| 5.8e-5, identical top-1 and top-10, bitwise repeat and reload.

## End-to-end accuracy (seed 0, pca, sender = smol; uncovered = failure)
| receiver | task | glyph_id | text_prose | id_text_expanded | text_compact | receiver_word_state | none |
|---|---|---|---|---|---|---|---|
| smol | t1\|agent | 0.676 | 0.940 | 0.940 | 0.488 | 0.676 | 0.060 |
| smol | t1\|patient | 0.660 | 0.872 | 0.872 | 0.600 | 0.648 | 0.056 |
| smol | t1\|pol | 0.988 | 1.000 | 1.000 | 1.000 | 0.996 | 0.508 |
| smol | t4\|where | 0.124 | 1.000 | 0.124 | 1.000 | 0.124 | 0.067 |
| smol | t5\|status | 0.625 | 1.000 | 0.750 | 1.000 | 0.625 | 0.125 |
| qwen | t1\|agent | 0.855 | 1.000 | 1.000 | 0.827 | 0.855 | 0.173 |
| qwen | t1\|mod | 0.855 | 0.927 | 0.927 | 0.664 | 0.864 | 0.482 |
| qwen | t1\|pol | 0.945 | 1.000 | 1.000 | 0.936 | 0.945 | 0.473 |
| qwen | t2\|first | 0.945 | 1.000 | 1.000 | 0.555 | 0.945 | 0.127 |
| qwen | t4\|where | 0.118 | 1.000 | 0.118 | 1.000 | 0.118 | 0.091 |
| qwen | t5\|status | 0.625 | 1.000 | 0.750 | 1.000 | 0.625 | 0.125 |

The paired verdicts (margin ±0.05, cluster bootstrap) are in [TABLES_v5.md](https://raw.githubusercontent.com/devamped1337/glyph-alphabet-experiments/48a7a6a5faff09d6de4f8fef8773d9419a248a3e/v5/results/TABLES_v5.md). Qwen receiver, glyph vs prose: agent -0.145, mod -0.073, pol -0.055, first -0.055, where -0.882, status -0.375. All are "B better".

## Coverage
In the test rows, `covered` is recorded only for `glyph_operand_changed` (186/440 uncovered on Qwen, 356/960 on SmolLM2). For `glyph_id`, coverage is therefore reported as 1.000, which **overstates** it. The rejected place entries are not flagged as uncovered, so the t4 collapse shows up as low accuracy instead. Treat the coverage columns in TABLES_v5.md as unreliable for every condition except operand_changed. This is a v5 logging gap.

## Controls (Qwen receiver, smol sender, e2e)
| control | agent | mod | pol | first | where | status |
|---|---|---|---|---|---|---|
| glyph_id (real adapter) | 0.855 | 0.855 | 0.945 | 0.945 | 0.118 | 0.625 |
| null_randorth | 0.136 | 0.464 | 0.445 | 0.218 | 0.109 | 0.125 |
| null_shufpair | 0.127 | 0.482 | 0.445 | 0.127 | 0.045 | 0.125 |
| samenorm_shuffled | 0.136 | 0.473 | 0.400 | 0.145 | 0.091 | 0.125 |
| random basis | 0.309 | 0.518 | 0.545 | 0.227 | 0.091 | 0.125 |
| raw unsnapped | 0.855 | 0.864 | 0.945 | 0.945 | 0.218 | 0.625 |
| LOO (held-out symbol) | 0.427 | 0.895 | 0.964 | 0.473 | 0.018 | - |
On Qwen, the null adapters fall to the no-message level, so the real adapter is doing work. On the SmolLM2 receiver with the SmolLM2 sender (same model), null_shufpair equals the real adapter (0.676/0.648/0.996). That null is not null when the sender and receiver are the same model. Slot-swap follow rate and operand-change results are in TABLES_v5.md. The UNRECOGNIZED fallback was correct on 646/646 (Qwen) and 1056/1056 (SmolLM2).

## Reviewer tables
[EXTRA_TABLES_v5.md](https://raw.githubusercontent.com/devamped1337/glyph-alphabet-experiments/48a7a6a5faff09d6de4f8fef8773d9419a248a3e/v5/results/EXTRA_TABLES_v5.md) contains: the prose gate per task, the planted bad entries and which checks rejected each, LOO per entry (failed checks and collateral rejections), all conditions by task for both receivers, and the J-lens status.

## Pre-registered decision rules (written before any results)
See [PREREG.md](https://raw.githubusercontent.com/devamped1337/glyph-alphabet-experiments/48a7a6a5faff09d6de4f8fef8773d9419a248a3e/v5/PREREG.md). Rule A: a task counts if prose ≥ 0.90 and none < 0.90 on DEV. Rule B: depth frozen from DEV glyph_id (frozen li=0; 0.750/0.716/0.673). Primary comparison: glyph_id (pca, seed 0) vs text_prose, id_text_expanded, text_compact and receiver_word_state, by paired cluster bootstrap with ±0.05 equivalence (v5.2). Headline numbers are end-to-end. Controls are reported, never tuned on. Gate success means all planted entries are rejected and LOO pass rate is reported.

Dropped by rule A: SmolLM2 t1|mod (0.775), t2|first (0.825), t3|result (0.55). Qwen t1|patient (0.825), t3|result (0.55). **The maths task t3 is not counted on either receiver.**

## Deviations (everything that stalled, was cut or was rerun)
1. **J-lens basis DROPPED (v5.5).** Qwen J-gram fp32 OOM (17.5 GB peak); bf16 run killed after 98 min with no batch done. No jlens books or rows exist. The pre-registered jlens vs pca vs random comparison was not run.
2. Qwen test size cut: N_TEST 250 → 80 (v5.1) → 110 (v5.5, sized to ~8 h from a DEV rate of 43.4 s/query). Seed 0 only. The run actually took 12.0 h.
3. Qwen extraction was restarted: v5.3 run stopped by a watcher after the fp32 states were saved (v5.4). The in-process bf16 reload leaked memory.
4. Orchestrator J-gram wait removed by hand (sed) after the J-gram was abandoned.
5. Qwen cross-machine determinism not checked (only the laptop ran Qwen); the check was on SmolLM2 only.
6. Large .pt files were transferred in split parts with sha256 checks (states_qwen 3fe4df7d, deliveries_qwen 79330801). test_qwen.json sha256 cdc4523d…, matching the laptop.
7. **analyze5 crashed on first run** (TypeError: the LOO dict was re-bootstrapped when it reached the second receiver). Fixed in `48a7a6a5faff09d6de4f8fef8773d9419a248a3e` with a one-line guard and rerun. Numbers are unaffected.
8. Coverage is not logged for glyph_id (see Coverage above).

## Raw files (pinned to 48a7a6a5faff09d6de4f8fef8773d9419a248a3e)
- Per-query predictions: [predictions_qwen.jsonl](https://raw.githubusercontent.com/devamped1337/glyph-alphabet-experiments/48a7a6a5faff09d6de4f8fef8773d9419a248a3e/v5/results/predictions_qwen.jsonl), [predictions_smol.jsonl](https://raw.githubusercontent.com/devamped1337/glyph-alphabet-experiments/48a7a6a5faff09d6de4f8fef8773d9419a248a3e/v5/results/predictions_smol.jsonl)
- Test outputs: [test_qwen.json](https://raw.githubusercontent.com/devamped1337/glyph-alphabet-experiments/48a7a6a5faff09d6de4f8fef8773d9419a248a3e/v5/results/test_qwen.json), [test_smol.json](https://raw.githubusercontent.com/devamped1337/glyph-alphabet-experiments/48a7a6a5faff09d6de4f8fef8773d9419a248a3e/v5/results/test_smol.json)
- Tables: [tables5.json](https://raw.githubusercontent.com/devamped1337/glyph-alphabet-experiments/48a7a6a5faff09d6de4f8fef8773d9419a248a3e/v5/results/tables5.json), [TABLES_v5.md](https://raw.githubusercontent.com/devamped1337/glyph-alphabet-experiments/48a7a6a5faff09d6de4f8fef8773d9419a248a3e/v5/results/TABLES_v5.md), [EXTRA_TABLES_v5.md](https://raw.githubusercontent.com/devamped1337/glyph-alphabet-experiments/48a7a6a5faff09d6de4f8fef8773d9419a248a3e/v5/results/EXTRA_TABLES_v5.md)
- Gate/LOO/planted: [gate5.json](https://raw.githubusercontent.com/devamped1337/glyph-alphabet-experiments/48a7a6a5faff09d6de4f8fef8773d9419a248a3e/v5/results/gate5.json). Frozen rules: [frozen5.json](https://raw.githubusercontent.com/devamped1337/glyph-alphabet-experiments/48a7a6a5faff09d6de4f8fef8773d9419a248a3e/v5/results/frozen5.json). Determinism: [det_report.json](https://raw.githubusercontent.com/devamped1337/glyph-alphabet-experiments/48a7a6a5faff09d6de4f8fef8773d9419a248a3e/v5/results/det_report.json)
- Checksums: [SHA256SUMS_v5_results.txt](https://raw.githubusercontent.com/devamped1337/glyph-alphabet-experiments/48a7a6a5faff09d6de4f8fef8773d9419a248a3e/v5/results/SHA256SUMS_v5_results.txt). Qwen log: [test_qwen.log](https://raw.githubusercontent.com/devamped1337/glyph-alphabet-experiments/48a7a6a5faff09d6de4f8fef8773d9419a248a3e/v5/logs/test_qwen.log)
- Recompute: `python v5/analyze5.py && python v5/extra5.py` (reads v5/results/).
