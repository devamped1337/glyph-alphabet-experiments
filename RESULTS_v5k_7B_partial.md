# v5k (7B) results: PARTIAL, the run FAILED

**Status: FAILED.** Kaggle kernel `devamped13/notebook83b9a1ff44` version 3 (Qwen2.5-7B × OLMo-2-1124-7B, run code `bf8d79f`) ended in `KernelWorkerStatus.ERROR`. The user stopped further runs: no relaunch and no fix-and-rerun on Kaggle. Everything below was computed **on the box from the v3 output**, after the results were seen. It is exploratory and NOT a pre-registered confirmatory result.

Scope: this covers only the **EMBEDDING-LAYER (li=0, `embed_tokens` output) channel at 7B**. frozen5.json froze li=0 (pipeline DEV glyph_id: 0.850 / 0.802 / 0.774 for li 0/1/2). The contextual and J-lens channels were not tested on TEST.

Note: an old hourly watch that was already running relaunched the kernel as version 4 against the user's order. The Kaggle CLI has no cancel command, and the API cancel needs a session id that the public API does not expose, so v4 could not be stopped from the box. Nothing from v4 is used here.

## Where and why it failed
- **v2** (out_v2_error) died in the OLMo-7B TEST stage with `non-finite logits in float16 forward (olmo7)`. OLMo-2-7B overflows in fp16 on a T4.
- **v3** (`bf8d79f`) added an fp16 overflow fallback that writes those rows as `pred="__OVERFLOW__"`. **Every pipeline stage finished**: extract, J-gram, det, negotiate/gate, DEV, TEST Qwen7 and TEST OLMo7, all with `.done` markers. The run then failed in the final **analyze** step: `v5k/analyze5.py` line 73 runs the LOO-by-gate bootstrap inside the per-receiver loop. On the second receiver it bootstrapped the first receiver's buckets again (already lists of floats), giving `TypeError: 'float' object is not a mapping`. The notebook raised `RuntimeError: a pipeline step FAILED`, about 4.8 h in. The fix (`a0cbe06`, kaggle branch) bootstraps once after all receivers and skips `__OVERFLOW__` rows. It was run only locally.
- **Data integrity:** all 16 artifacts in MANIFEST_kaggle.json pass the sha256 check (commit bf8d79f). See `v5k/results_7b_partial/SHA256SUMS_v3_kaggle.txt`. The states `.pt` files (~0.6 GB each) are not committed; only their hashes are.

## Overflow: OLMo receiver results are censored on t4/t5
4,914 of 45,912 OLMo-receiver TEST rows (10.7%) are `__OVERFLOW__`. All of them are t4 (4,482) and t5 (432). There are 0 such rows on the Qwen receiver. **The overflow is not random.** It falls almost entirely on the places that negotiation *rejected* (Germany, Munich, Berlin, France, Italy, Rome, Barcelona: all 14 messages each) and on the status "requested". Dropping those rows leaves only covered places, so **OLMo t4 = 1.000 and t5 = 0.857 are selection artifacts. Do not read them as results.** OLMo t1 (no overflow) is usable.

## Headline (e2e accuracy, glyph_id = pca seed 0; overflow rows excluded)
Full tables: `v5k/results_7b_partial/partial7b_tables.md` (script `partial7b.py`, cluster bootstrap 2000, ±0.05 margin).

Qwen2.5-7B receiver (clean):

| task | glyph | prose | id_expanded | compact | recv_word_state | none |
|---|---|---|---|---|---|---|
| t1 agent | 0.832 | 0.980 | 0.980 | 0.832 | 0.832 | 0.164 |
| t1 mod | 0.992 | 1.000 | 1.000 | 0.480 | 0.996 | 0.504 |
| t1 patient | 0.784 | 0.916 | 0.916 | 0.808 | 0.788 | 0.156 |
| t1 pol | 0.984 | 1.000 | 1.000 | 1.000 | 0.992 | 0.504 |
| t2 first | 0.888 | 0.960 | 0.960 | 0.480 | 0.888 | 0.120 |
| t4 where | 0.476 | 1.000 | 0.476 | 1.000 | 0.476 | 0.067 |
| t5 status | 0.625 | 1.000 | 0.750 | 1.000 | 0.625 | 0.125 |

OLMo-2-7B receiver (t1 only is clean): agent 0.836 vs prose 0.992; patient 0.804 vs 0.976; pol 0.876 vs 0.956.

1. **The glyph still never beats prose.** It is worse on agent, patient and first (Qwen, e.g. agent −0.148 [−0.215, −0.084]) and on all three OLMo t1 tasks. It is *equivalent* only on Qwen t1|mod and t1|pol, where everything is near ceiling. It ties id_text_expanded wherever prose does. t5 and t4 lose to prose.
2. **Glyph vs compact text:** better where compact is weak (Qwen mod +0.51, first +0.41; OLMo agent +0.52), worse on OLMo pol and t4/t5, and inconclusive on the rest.
3. **It is still a lookup.** glyph_id equals receiver_word_state, with a paired difference of 0.000 on nearly every cell. Results are identical for both senders on every cell. After snapping, the answer is the receiver's own dictionary entry.
4. **Nulls (cross-model sender only; same-model nulls are not nulls):** on Qwen with the OLMo sender, null_randorth/shufpair/samenorm fall to about the none level on agent/patient/first (for example agent 0.124/0.044/0.140 against none 0.164). One exception: null_shufpair on t1|mod scores 0.724, above none (0.504). The real adapter does work.
5. **LOO split by answer-held-out:** on every multi-way slot, answer-held-out ≈ 0 (Qwen agent 0.000/0.012, patient 0.000, first 0.000/0.016; OLMo agent/patient 0.000–0.004). Other-held-out is 0.80–0.90. The receiver does not recover a held-out symbol. The 3B LOO artifact is reproduced.
6. **Coverage (reconstructed: gold entry in the final 72-entry book `0|pca|0`):** the Qwen receiver covered 224/420 t4 places (0.533), with 0.893 accuracy among covered. t5 was 144/192 (0.750), with 0.833 among covered. 21 of 93 entries were rejected (19 in round 0 including 7 places, then Germany and France). 7B kept many more places than 3B, where only Lyon and Spain survived.
7. **DEV by depth** (glyph_id, counted tasks, recomputed with uncovered = 0): Qwen7 li0 0.874 / li1 0.756 / li2 0.744 (n=508). OLMo7 0.816 / 0.592 / 0.552 (n=348). Emb wins clearly, as at 3B.

## Did size change anything? (vs 3B v5, RESULTS_v5.md)
- Same qualitative picture: glyph < prose, glyph = receiver_word_state, sender-invariant, LOO answer-held-out ≈ 0.
- **t4 improved** (Qwen receiver 0.118 at 3B → 0.476 at 7B). This comes from **dictionary coverage**: 7B negotiation rejected fewer places. Accuracy among covered places is about the same (0.93 → 0.89). The channel itself did not get better.
- Agent/patient/first are similar (3B Qwen agent 0.855, first 0.945; 7B 0.832, 0.888). t5 is unchanged at 0.625 (same 5/8 statuses).

## What was not done / caveats
- Exploratory, post-hoc, local. The pre-registered analyze step never ran on Kaggle. `a0cbe06`'s analyze5.py is being run locally for the generated TABLES; see the end note.
- OLMo t4/t5 cannot be interpreted (censored). There are no other-receiver comparisons for t1|mod and t2 (not counted for OLMo by the prose gate).
- **v6 validator:** `v6/checks/validate_v6.py --results-dir …/glyph_results` → exit 1, `No predictions_*.jsonl found`. That is expected: this is the v5-style schema and not a v6 result.
