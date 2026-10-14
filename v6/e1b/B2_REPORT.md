# E1b Stage B2 report (A9 post-hoc follow-up)

**Status:** VALID, complete. B2 is the oracle-ID receiver comparison + GPU cache check + cost table (PREREG §9). It does **not** decide the POC success criterion (that is B3).
**Kernel:** `devamped13/e1b-stage-b2` v1 (COMPLETE). Ran 18:52–22:24 AEDT, 2026-10-14 (07:52–11:24 UTC). Starts used: 1 of 2.
**Pinned:** tag `prereg-e1b-a9` (`b2ec2f3`), `CODE_HASH` `d0203f22…`. Results overlay includes prior A9 stages (B1c/B1) required by stage order; the code is identical to the tag.
**Pair:** qwen7b + falcon7b (A8 post-hoc). The primary B0 result stays `NO_QUALIFYING_PAIR`. Label: POST-HOC follow-up (A8 pair).
**Level:** L4 (C60, 4 cases/entry, no F3L), batch 8 (from B1c). Ungated per A9 (gate dropped for B2/B3; reported descriptively).

Falcon3-7B-Instruct results were produced using artificial intelligence technology from the Technology Innovation Institute (TII Falcon License).

## Validity

| Check | Result |
| --- | --- |
| GPU preflight | PASS for both models (Tesla T4, `hf-nf4`, params on CUDA; no CPU fallback) |
| Canaries | qwen7b 20/20, falcon7b 20/20 |
| Item counts | main 740/model (direct_text 240 + prose 240 + id_raw 120 + placebo 120 + id_oracle_paired 20); unknown 48; cache 120/model (100 fixed + 20 stress). Matches L4 plan (60 core TEST entries × 4; sanity 30 × 4; paired check 20; unknown 48) |
| Uniqueness / missing | all keys unique; no missing expected files |
| Parsing | qwen7b main 740/740 `answer_line` (0 unparsed); falcon7b 735 `answer_line`, 5 `last_integer` (0 unparsed) |
| Gold labels | every main/canary row's `gold` matches `cases_e1b_a9.json` (0 mismatches; book sha `19f8d46d…`) |
| Truncation | qwen7b none at the 192-token cap; falcon7b 4/740 hit 192 (all `id_raw` sanity controls, all incorrect as expected for that arm; parsed via `last_integer`) |
| Byte identity | 240/240 id_oracle vs direct_text prompts byte-identical (`all_identical: true`) |
| Unknown-ID delegate | 48/48 → `UNKNOWN` with `model_called: false` (16 unknown_id + 16 stale_version + 16 hash_mismatch) |
| Budget | cap 6.40 h; used **3.53 h** (`A9_B2` 12718.8 s); A9 total so far **5.28 / 12.0 h** (B1c 0.44 + B1 1.30 + B2 3.53) |
| Validator | PASSED (0 FAIL / WARN), including recomputed cache summaries and MANIFEST |

## Results (descriptive; ungated; id_oracle vs direct_text is zero by construction)

Per PREREG: given byte identity, the id_oracle vs direct_text difference is a check, not a finding. B2's content is the **prose comparison** and the **cost table**.

### id_oracle check
- Byte-identical prompts on all 240 TEST items.
- Paired output check (20 items): qwen7b **20/20** identical raw outputs; falcon7b **19/20** identical raw (one case: both predicted gold `35` correctly, wording differed slightly — "Gus is an Iselin member" vs "Iselin member", and multiply order). Predicates matched on all 20 for both models.

### Prose comparison (direct_text − prose, core; non-inferiority)
| Model | direct_text (F1 / F2 / overall) | prose (F1 / F2 / overall) | direct − prose est | 95% CI | label |
| --- | --- | --- | --- | --- | --- |
| qwen7b | 1.000 / 0.992 / 0.996 (n=240) | 1.000 / 0.983 / 0.992 (n=240) | +0.0042 | [−0.0083, +0.0208] | non-inferior |
| falcon7b | 1.000 / 0.992 / 0.996 (n=240) | 1.000 / 1.000 / 1.000 (n=240) | −0.0042 | [−0.0125, 0.0000] | non-inferior |

### Sanity controls
- **id_raw** (ID only, no expansion): 0.000 accuracy both models (n=120).
- **placebo** (answer-determining constants removed): 0.000 accuracy both models (n=120).

### GPU cache check (§8)
- Fixed set (n=100) and stress (n=20) per model; 0 invalid runs.
- **Claim WITHHELD** for both models (cold/warm and cold/coldsplit prediction changes observed on the fixed set: qwen 1 pred-changed on cold_warm / cold_coldsplit; falcon 2). Stress set: 0 changes.
- Rule-of-three upper 95% ≈ 0.03/prompt. Wording: *"cache claim WITHHELD: changed or invalid predictions observed; all claims in this runtime use uncached runs."*
- Prefix-cached timing was skipped by rule for both models.

### Cost table (uncached / cold; batch mixed from batch-8 main; FLOPs = 2·params·(newly processed + generated))

| Model | condition | n | latency_s | prompt tok | gen tok | FLOPs (new) |
| --- | --- | --- | --- | --- | --- | --- |
| qwen7b | direct_text | 240 | 2.125 | 123.8 | 54.3 | 2.71e12 |
| qwen7b | prose | 240 | 2.125 | 127.1 | 54.0 | 2.75e12 |
| qwen7b | id_raw | 120 | 2.129 | 105.0 | 41.7 | 2.23e12 |
| qwen7b | placebo | 120 | 2.129 | 121.8 | 56.6 | 2.71e12 |
| falcon7b | direct_text | 240 | 3.445 | 132.7 | 77.8 | 3.14e12 |
| falcon7b | prose | 240 | 3.445 | 138.0 | 74.3 | 3.17e12 |
| falcon7b | id_raw | 120 | 3.649 | 113.8 | 61.9 | 2.62e12 |
| falcon7b | placebo | 120 | 3.649 | 132.4 | 71.2 | 3.04e12 |

Cached cost columns are empty (claim withheld). Uncached cost is always shown.

## Problems / notes to disclose
1. **Cache claim withheld** (expected-possible under §8): cold vs warm / coldsplit prediction drift on the fixed set for both models; all accuracy and cost claims use uncached runs.
2. **Falcon paired raw 19/20**: one byte-identical prompt pair produced slightly different reasoning text with the same correct answer — reported honestly; not a gold or parse failure.
3. **Falcon 4× hit the 192-token cap** on `id_raw` sanity rows only (still 0% correct on that arm).
4. No CPU fallback; no incomplete marker; validator and independent gold/count/parse checks agree.

## Next
B3 (cap 1.75 GPU-h, ungated headline). Launch only on Stefan's explicit go (`E1B_GO=B3`). Remaining A9 budget ≈ 6.72 GPU-h of the 12.0 h total.
