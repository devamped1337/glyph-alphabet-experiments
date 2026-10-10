# Glyph experiment v4: three-party repository (composition, deliveries, costs)

## Summary and verdict (hand-written; the tables below are generated from results/v4/tables_v4.json)

**Models:** Qwen/Qwen2.5-0.5B, HuggingFaceTB/SmolLM2-360M, EleutherAI/pythia-410m (third signee; mid-layer states, no new J-lens; readability uses each model's own unembedding of the decoded state). Frozen before test: depth 0.25 (Qwen L6, Smol L8, Pythia L6), replace-mode patching at the placeholder positions, PCA64 half-whitened, 32-d canonical space, book v4.3. Depth was chosen on the dev split with **only the Qwen receiver**, because the Smol and Pythia dev runs stalled.

**Repository (main layer):** 60 base entries were proposed. Rounds 1-3 rejected 9 maths-digit slot entries (t3 left 2/5/7/9, right 2/4/5/7/9) and v4.0 stabilised at 51. Delegate proposals: Oscar (qwen, accepted), Peggy (smol, accepted), Alicia (pythia, rejected), pushed (qwen, accepted), warned (smol, rejected), praised (pythia, rejected). Each accepted proposal caused an adapter refit and a version bump. Final: v4.3, 56 entries plus 6 rules. Each rejection came from a refit breaking an existing entry (t3 right 8 round trip/readability), never from the proposed word itself. The proposal schedule and the check thresholds are scripted rules. Separability, round trips, readability and geometry are measured from the models.

**Composition (test, unseen combinations; glyph_vec, CI ~±0.03-0.13):**
- Role: book glyph 0.94-0.98 for every sender→receiver pair. Compact text reached 0.65 (Qwen), 0.80 (Smol) and 0.89 (Pythia); prose 0.92-1.00; no message 0.07-0.36. Shuffling the role slot drops the glyph to 0.02-0.06, and the answer follows the swap 0.94-0.98 of the time.
- Negation: glyph 1.00 / 0.61 / 0.82 (Qwen/Smol/Pythia receiver), compact 1.00 / 1.00 / 0.73.
- Uncertainty and event order: at chance for every delivery, text included (best is Qwen prose uncertainty at 0.70). These tests cannot discriminate.
- Signed maths (whole answer scored, e.g. 2-7=-5): prose 0.51 (Qwen, Smol) and 0.03 (Pythia); glyph ≤0.15. The pair metric (both 7-2 and 2-7 correct) is **0 for every condition, text included**. Maths snap accuracy is only 0.18, so the maths role-swap is a failure on all sides.

**ID vs vector:** identical predictions on 969/969 queries per receiver. Max injected-state difference is ≤3.8e-6 (float32 rounding from a different summation order), and receipt IDs match 100%.

**Raw-adapter vs book transfer asymmetry:** raw unsnapped Smol→Qwen role is 0.59 and Smol→Pythia 0.48, against 0.94/0.96 through the book. Qwen→Smol and Pythia→Smol raw are 1.00. So the weak raw direction is now *Smol as sender*, the reverse of v3's raw Qwen→Smol failure. Snapping to the book removes the asymmetry entirely.

**Ablations:** the no-filter book (71 entries) performs within the CI of the filtered book (role 0.95-0.98), so the filters did not help accuracy here. The two-model book (no Pythia) is lower on role: 0.84 vs 0.94 with Qwen receiving, 0.95 vs 0.98 with Smol. It scores higher on Smol maths (0.26-0.28), but that is within noise at n=39.

**Equivalent-stage word control:** the receiver's own processed word state at the same layer scores about the same as the book glyph (role 0.87-1.00). The glyph carries essentially what the word state carries, not more.

**Bytes:** event message: ID 11 bits = 4 B with a 2-B version header; compact text 30 B (~11-12 tokens); prose 43.5 B (~9 tokens); vector 642 B. Maths: ID 6 bits = 3 B (8 bits with 4 ops; the reviewer's 4+2+4 = 10-bit scheme would be 2 B + header); text 4 B; vector 514 B. Compute: snap 0.45 s, decode 0.13 s, receipt check 0.27 s per message. One-time setup: about 11-13 min of extraction per model plus 106 s of negotiation.

**Verdict:**
1. Frozen building blocks carried unseen role-swapped messages across all three models (0.94-0.98), and a slot swap predictably flips the answer.
2. On roles, glyphs beat compact structured text for every receiver and roughly matched prose. On negation they tied or lost (Smol 0.61 vs 1.00).
3. Uncertainty, event order and signed maths were not carried by any channel, text included, so they show nothing either way.
4. As an ID, the book message is the cheapest channel (4 B vs 30 B compact), and ID and vector deliveries are bit-for-bit equivalent in effect.
5. The glyph does no better than the receiver's own word state. Its value is a cheap, verified, model-neutral addressing scheme, not extra meaning.
6. The negotiation filters did not measurably help. The third signee helped modestly.

**Caveats:** depth was frozen on the Qwen receiver's dev split only. The t1/t2 test sets were subsampled (323 queries per receiver) to fit the CPU budget. Compact text like `pay(Alice,Bob,known,t1)` may be unfamiliar to tiny base models. The maths entries are fragile (9 digit slots rejected, snap 0.18). The proposal and accept rules are scripted.


**Run:** 10 Oct 2026, AEDT (Australia/Sydney box clock).
- Models: Qwen2.5-0.5B, SmolLM2-360M, EleutherAI/pythia-410m. One model loaded at a time.
- Pythia used raw mid-layer states (no J-lens). Qwen and Smol reused the v1 fitted lenses.
- Frozen layer fraction: FRACS[0] (see `results/v4/frozen.json`). Layer map: {"qwen": 6, "smol": 8, "pythia": 6}.
- Book version: 4.3, entries: 56.
- Dev note (layer pick): Smol and Pythia dev runs were cut (box stalled ~50 min); layer fraction chosen on the Qwen-receiver dev split only (all 3 senders), before any test run.

Every number below is in `results/v4/*.json`. Tables JSON: `results/v4/tables_v4.json`.

## What v4 measures
- Three-party negotiated book (all three models agree on entries).
- Unseen compositions and signed subtraction order (7−2 vs 2−7).
- Separate sender selection (snap) accuracy, transfer fidelity, and ID vs float32 vector delivery.
- Cost vs terse text (`text_compact` / prose / bag).
- Slot-shuffle and same-norm shuffle controls; nofilter and two-model ablations.

## Pooled accuracy (all tasks, mean [95% bootstrap CI])

| receiver | sender | condition | mean | lo | hi | n |
|---|---|---|---|---|---|---|
| Qwen2.5-0.5B | - | none | 0.254 | 0.210 | 0.303 | 323 |
| Qwen2.5-0.5B | - | text_prose | 0.793 | 0.749 | 0.836 | 323 |
| Qwen2.5-0.5B | - | text_compact | 0.591 | 0.539 | 0.647 | 323 |
| Qwen2.5-0.5B | - | text_bag | 0.573 | 0.523 | 0.628 | 323 |
| Qwen2.5-0.5B | qwen | text_compact_of_choice | 0.591 | 0.536 | 0.644 | 323 |
| Qwen2.5-0.5B | qwen | glyph_id | 0.706 | 0.653 | 0.755 | 323 |
| Qwen2.5-0.5B | qwen | glyph_vec | 0.706 | 0.656 | 0.752 | 323 |
| Qwen2.5-0.5B | qwen | glyph_raw_unsnapped | 0.734 | 0.687 | 0.780 | 323 |
| Qwen2.5-0.5B | qwen | receiver_word_state | 0.715 | 0.672 | 0.768 | 323 |
| Qwen2.5-0.5B | qwen | glyph_slot_shuffled | 0.186 | 0.145 | 0.223 | 318 |
| Qwen2.5-0.5B | qwen | glyph_samenorm_shuffled | 0.300 | 0.251 | 0.350 | 323 |
| Qwen2.5-0.5B | qwen | ablation_nofilter_vec | 0.709 | 0.659 | 0.755 | 323 |
| Qwen2.5-0.5B | qwen | ablation_twomodel_vec | 0.675 | 0.622 | 0.724 | 323 |
| Qwen2.5-0.5B | smol | text_compact_of_choice | 0.591 | 0.536 | 0.638 | 323 |
| Qwen2.5-0.5B | smol | glyph_id | 0.706 | 0.659 | 0.755 | 323 |
| Qwen2.5-0.5B | smol | glyph_vec | 0.706 | 0.656 | 0.755 | 323 |
| Qwen2.5-0.5B | smol | glyph_raw_unsnapped | 0.579 | 0.526 | 0.635 | 323 |
| Qwen2.5-0.5B | smol | receiver_word_state | 0.715 | 0.663 | 0.759 | 323 |
| Qwen2.5-0.5B | smol | glyph_slot_shuffled | 0.188 | 0.143 | 0.232 | 314 |
| Qwen2.5-0.5B | smol | glyph_samenorm_shuffled | 0.300 | 0.251 | 0.353 | 323 |
| Qwen2.5-0.5B | smol | ablation_nofilter_vec | 0.709 | 0.656 | 0.759 | 323 |
| Qwen2.5-0.5B | smol | ablation_twomodel_vec | 0.675 | 0.625 | 0.724 | 323 |
| Qwen2.5-0.5B | pythia | text_compact_of_choice | 0.591 | 0.539 | 0.638 | 323 |
| Qwen2.5-0.5B | pythia | glyph_id | 0.709 | 0.663 | 0.759 | 323 |
| Qwen2.5-0.5B | pythia | glyph_vec | 0.709 | 0.656 | 0.759 | 323 |
| Qwen2.5-0.5B | pythia | glyph_raw_unsnapped | 0.728 | 0.681 | 0.780 | 323 |
| Qwen2.5-0.5B | pythia | receiver_word_state | 0.718 | 0.669 | 0.768 | 323 |
| Qwen2.5-0.5B | pythia | glyph_slot_shuffled | 0.189 | 0.148 | 0.236 | 318 |
| Qwen2.5-0.5B | pythia | glyph_samenorm_shuffled | 0.257 | 0.207 | 0.303 | 323 |
| Qwen2.5-0.5B | pythia | ablation_nofilter_vec | 0.712 | 0.659 | 0.762 | 323 |
| SmolLM2-360M | - | none | 0.353 | 0.300 | 0.406 | 323 |
| SmolLM2-360M | - | text_prose | 0.687 | 0.632 | 0.737 | 323 |
| SmolLM2-360M | - | text_compact | 0.650 | 0.601 | 0.703 | 323 |
| SmolLM2-360M | - | text_bag | 0.502 | 0.449 | 0.554 | 323 |
| SmolLM2-360M | qwen | text_compact_of_choice | 0.650 | 0.598 | 0.703 | 323 |
| SmolLM2-360M | qwen | glyph_id | 0.672 | 0.622 | 0.721 | 323 |
| SmolLM2-360M | qwen | glyph_vec | 0.672 | 0.622 | 0.718 | 323 |
| SmolLM2-360M | qwen | glyph_raw_unsnapped | 0.647 | 0.591 | 0.700 | 323 |
| SmolLM2-360M | qwen | receiver_word_state | 0.607 | 0.545 | 0.659 | 323 |
| SmolLM2-360M | qwen | glyph_slot_shuffled | 0.245 | 0.198 | 0.296 | 318 |
| SmolLM2-360M | qwen | glyph_samenorm_shuffled | 0.310 | 0.260 | 0.359 | 323 |
| SmolLM2-360M | qwen | ablation_nofilter_vec | 0.675 | 0.625 | 0.724 | 323 |
| SmolLM2-360M | qwen | ablation_twomodel_vec | 0.666 | 0.613 | 0.715 | 323 |
| SmolLM2-360M | smol | text_compact_of_choice | 0.650 | 0.601 | 0.703 | 323 |
| SmolLM2-360M | smol | glyph_id | 0.669 | 0.613 | 0.718 | 323 |
| SmolLM2-360M | smol | glyph_vec | 0.669 | 0.616 | 0.724 | 323 |
| SmolLM2-360M | smol | glyph_raw_unsnapped | 0.616 | 0.566 | 0.672 | 323 |
| SmolLM2-360M | smol | receiver_word_state | 0.607 | 0.551 | 0.663 | 323 |
| SmolLM2-360M | smol | glyph_slot_shuffled | 0.248 | 0.201 | 0.296 | 314 |
| SmolLM2-360M | smol | glyph_samenorm_shuffled | 0.279 | 0.229 | 0.328 | 323 |
| SmolLM2-360M | smol | ablation_nofilter_vec | 0.678 | 0.628 | 0.728 | 323 |
| SmolLM2-360M | smol | ablation_twomodel_vec | 0.663 | 0.613 | 0.715 | 323 |
| SmolLM2-360M | pythia | text_compact_of_choice | 0.653 | 0.604 | 0.703 | 323 |
| SmolLM2-360M | pythia | glyph_id | 0.672 | 0.616 | 0.721 | 323 |
| SmolLM2-360M | pythia | glyph_vec | 0.672 | 0.628 | 0.728 | 323 |
| SmolLM2-360M | pythia | glyph_raw_unsnapped | 0.656 | 0.601 | 0.706 | 323 |
| SmolLM2-360M | pythia | receiver_word_state | 0.610 | 0.557 | 0.659 | 323 |
| SmolLM2-360M | pythia | glyph_slot_shuffled | 0.242 | 0.198 | 0.289 | 318 |
| SmolLM2-360M | pythia | glyph_samenorm_shuffled | 0.294 | 0.248 | 0.347 | 323 |
| SmolLM2-360M | pythia | ablation_nofilter_vec | 0.678 | 0.628 | 0.728 | 323 |
| pythia-410m | - | none | 0.328 | 0.279 | 0.384 | 323 |
| pythia-410m | - | text_prose | 0.706 | 0.659 | 0.755 | 323 |
| pythia-410m | - | text_compact | 0.619 | 0.560 | 0.669 | 323 |
| pythia-410m | - | text_bag | 0.440 | 0.387 | 0.492 | 323 |
| pythia-410m | qwen | text_compact_of_choice | 0.619 | 0.563 | 0.669 | 323 |
| pythia-410m | qwen | glyph_id | 0.666 | 0.616 | 0.715 | 323 |
| pythia-410m | qwen | glyph_vec | 0.666 | 0.613 | 0.715 | 323 |
| pythia-410m | qwen | glyph_raw_unsnapped | 0.709 | 0.662 | 0.755 | 323 |
| pythia-410m | qwen | receiver_word_state | 0.700 | 0.653 | 0.752 | 323 |
| pythia-410m | qwen | glyph_slot_shuffled | 0.223 | 0.176 | 0.267 | 318 |
| pythia-410m | qwen | glyph_samenorm_shuffled | 0.279 | 0.229 | 0.325 | 323 |
| pythia-410m | qwen | ablation_nofilter_vec | 0.666 | 0.613 | 0.712 | 323 |
| pythia-410m | smol | text_compact_of_choice | 0.619 | 0.567 | 0.678 | 323 |
| pythia-410m | smol | glyph_id | 0.666 | 0.610 | 0.715 | 323 |
| pythia-410m | smol | glyph_vec | 0.666 | 0.616 | 0.715 | 323 |
| pythia-410m | smol | glyph_raw_unsnapped | 0.523 | 0.471 | 0.579 | 323 |
| pythia-410m | smol | receiver_word_state | 0.700 | 0.647 | 0.746 | 323 |
| pythia-410m | smol | glyph_slot_shuffled | 0.226 | 0.182 | 0.268 | 314 |
| pythia-410m | smol | glyph_samenorm_shuffled | 0.254 | 0.211 | 0.297 | 323 |
| pythia-410m | smol | ablation_nofilter_vec | 0.666 | 0.613 | 0.715 | 323 |
| pythia-410m | pythia | text_compact_of_choice | 0.619 | 0.560 | 0.672 | 323 |
| pythia-410m | pythia | glyph_id | 0.669 | 0.616 | 0.721 | 323 |
| pythia-410m | pythia | glyph_vec | 0.669 | 0.613 | 0.721 | 323 |
| pythia-410m | pythia | glyph_raw_unsnapped | 0.703 | 0.653 | 0.752 | 323 |
| pythia-410m | pythia | receiver_word_state | 0.700 | 0.653 | 0.749 | 323 |
| pythia-410m | pythia | glyph_slot_shuffled | 0.223 | 0.179 | 0.270 | 318 |
| pythia-410m | pythia | glyph_samenorm_shuffled | 0.300 | 0.251 | 0.350 | 323 |
| pythia-410m | pythia | ablation_nofilter_vec | 0.666 | 0.610 | 0.709 | 323 |

## Accuracy by task (glyph_vec and text_compact)

| receiver | sender | condition | role | negation | uncertainty | order | maths_signed |
|---|---|---|---|---|---|---|---|
| qwen | qwen | glyph_vec | 0.938 | 1.000 | 0.625 | 0.500 | 0.051 |
| qwen | qwen | glyph_id | 0.938 | 1.000 | 0.625 | 0.500 | 0.051 |
| qwen | smol | glyph_vec | 0.938 | 1.000 | 0.625 | 0.500 | 0.051 |
| qwen | smol | glyph_id | 0.938 | 1.000 | 0.625 | 0.500 | 0.051 |
| qwen | pythia | glyph_vec | 0.938 | 1.000 | 0.625 | 0.500 | 0.077 |
| qwen | pythia | glyph_id | 0.938 | 1.000 | 0.625 | 0.500 | 0.077 |
| qwen | - | text_compact | 0.652 | 1.000 | 0.500 | 0.550 | 0.026 |
| qwen | - | text_prose | 0.982 | 1.000 | 0.696 | 0.517 | 0.513 |
| qwen | - | text_bag | 0.500 | 1.000 | 0.571 | 0.550 | 0.205 |
| qwen | - | none | 0.071 | 0.500 | 0.500 | 0.300 | 0.000 |
| smol | qwen | glyph_vec | 0.982 | 0.607 | 0.500 | 0.650 | 0.154 |
| smol | qwen | glyph_id | 0.982 | 0.607 | 0.500 | 0.650 | 0.154 |
| smol | smol | glyph_vec | 0.982 | 0.607 | 0.500 | 0.650 | 0.128 |
| smol | smol | glyph_id | 0.982 | 0.607 | 0.500 | 0.650 | 0.128 |
| smol | pythia | glyph_vec | 0.982 | 0.607 | 0.500 | 0.650 | 0.154 |
| smol | pythia | glyph_id | 0.982 | 0.607 | 0.500 | 0.650 | 0.154 |
| smol | - | text_compact | 0.804 | 1.000 | 0.500 | 0.583 | 0.026 |
| smol | - | text_prose | 0.920 | 0.607 | 0.500 | 0.617 | 0.513 |
| smol | - | text_bag | 0.500 | 0.589 | 0.500 | 0.583 | 0.256 |
| smol | - | none | 0.357 | 0.500 | 0.500 | 0.300 | 0.000 |
| pythia | qwen | glyph_vec | 0.964 | 0.821 | 0.536 | 0.500 | 0.026 |
| pythia | qwen | glyph_id | 0.964 | 0.821 | 0.536 | 0.500 | 0.026 |
| pythia | smol | glyph_vec | 0.964 | 0.821 | 0.536 | 0.500 | 0.026 |
| pythia | smol | glyph_id | 0.964 | 0.821 | 0.536 | 0.500 | 0.026 |
| pythia | pythia | glyph_vec | 0.964 | 0.821 | 0.536 | 0.500 | 0.051 |
| pythia | pythia | glyph_id | 0.964 | 0.821 | 0.536 | 0.500 | 0.051 |
| pythia | - | text_compact | 0.893 | 0.732 | 0.500 | 0.500 | 0.026 |
| pythia | - | text_prose | 1.000 | 0.982 | 0.571 | 0.467 | 0.026 |
| pythia | - | text_bag | 0.482 | 0.500 | 0.518 | 0.517 | 0.000 |
| pythia | - | none | 0.357 | 0.500 | 0.500 | 0.167 | 0.000 |

## Snap accuracy (sender selection into the book)
```
{
 "qwen|t1": [
  1.0,
  1.0,
  1.0,
  224
 ],
 "smol|t1": [
  1.0,
  1.0,
  1.0,
  224
 ],
 "pythia|t1": [
  1.0,
  1.0,
  1.0,
  224
 ],
 "qwen|t2": [
  1.0,
  1.0,
  1.0,
  60
 ],
 "smol|t2": [
  1.0,
  1.0,
  1.0,
  60
 ],
 "pythia|t2": [
  1.0,
  1.0,
  1.0,
  60
 ],
 "qwen|t3": [
  0.179,
  0.077,
  0.308,
  39
 ],
 "smol|t3": [
  0.179,
  0.077,
  0.308,
  39
 ],
 "pythia|t3": [
  0.179,
  0.077,
  0.308,
  39
 ]
}
```

## ID vs vector delivery
```
{
 "qwen": {
  "n": 969,
  "identical_predictions": 1.0,
  "max_abs_state_diff_float32": 4.76837158203125e-07,
  "receipt_ids_match": 1.0
 },
 "smol": {
  "n": 969,
  "identical_predictions": 1.0,
  "max_abs_state_diff_float32": 3.814697265625e-06,
  "receipt_ids_match": 1.0
 },
 "pythia": {
  "n": 969,
  "identical_predictions": 1.0,
  "max_abs_state_diff_float32": 9.5367431640625e-07,
  "receipt_ids_match": 1.0
 }
}
```

## Maths swap pairs (both 7−2 and 2−7 correct)
```
{
 "qwen|-|text_prose": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "qwen|-|text_compact": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "qwen|-|text_bag": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "qwen|-|none": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "qwen|qwen|glyph_id": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "qwen|qwen|glyph_vec": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "qwen|qwen|glyph_slot_shuffled": [
  0.0,
  0.0,
  0.0,
  14
 ],
 "qwen|qwen|glyph_samenorm_shuffled": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "qwen|qwen|glyph_raw_unsnapped": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "qwen|qwen|receiver_word_state": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "qwen|qwen|ablation_nofilter_vec": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "qwen|qwen|ablation_twomodel_vec": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "qwen|smol|glyph_id": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "qwen|smol|glyph_vec": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "qwen|smol|glyph_slot_shuffled": [
  0.0,
  0.0,
  0.0,
  11
 ],
 "qwen|smol|glyph_samenorm_shuffled": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "qwen|smol|glyph_raw_unsnapped": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "qwen|smol|receiver_word_state": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "qwen|smol|ablation_nofilter_vec": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "qwen|smol|ablation_twomodel_vec": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "qwen|pythia|glyph_id": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "qwen|pythia|glyph_vec": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "qwen|pythia|glyph_slot_shuffled": [
  0.0,
  0.0,
  0.0,
  14
 ],
 "qwen|pythia|glyph_samenorm_shuffled": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "qwen|pythia|glyph_raw_unsnapped": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "qwen|pythia|receiver_word_state": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "qwen|pythia|ablation_nofilter_vec": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "qwen|qwen|text_compact_of_choice": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "qwen|smol|text_compact_of_choice": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "qwen|pythia|text_compact_of_choice": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "qwen|smol|glyph_slot_shuffled_NOT_COVERED": [
  0.0,
  0.0,
  0.0,
  1
 ],
 "smol|-|text_prose": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "smol|-|text_compact": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "smol|-|text_bag": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "smol|-|none": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "smol|qwen|glyph_id": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "smol|qwen|glyph_vec": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "smol|qwen|glyph_slot_shuffled": [
  0.0,
  0.0,
  0.0,
  14
 ],
 "smol|qwen|glyph_samenorm_shuffled": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "smol|qwen|glyph_raw_unsnapped": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "smol|qwen|receiver_word_state": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "smol|qwen|ablation_nofilter_vec": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "smol|qwen|ablation_twomodel_vec": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "smol|smol|glyph_id": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "smol|smol|glyph_vec": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "smol|smol|glyph_slot_shuffled": [
  0.0,
  0.0,
  0.0,
  11
 ],
 "smol|smol|glyph_samenorm_shuffled": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "smol|smol|glyph_raw_unsnapped": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "smol|smol|receiver_word_state": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "smol|smol|ablation_nofilter_vec": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "smol|smol|ablation_twomodel_vec": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "smol|pythia|glyph_id": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "smol|pythia|glyph_vec": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "smol|pythia|glyph_slot_shuffled": [
  0.0,
  0.0,
  0.0,
  14
 ],
 "smol|pythia|glyph_samenorm_shuffled": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "smol|pythia|glyph_raw_unsnapped": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "smol|pythia|receiver_word_state": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "smol|pythia|ablation_nofilter_vec": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "smol|qwen|text_compact_of_choice": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "smol|smol|text_compact_of_choice": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "smol|pythia|text_compact_of_choice": [
  0.0,
  0.0,
  0.0,
  19
 ],
 "smol|smol|glyph_slot_shuffled_NOT_COVERED": [
  0.0,
  0.0,
  0.0,
  1
 ],
 "pythia|-|text_prose": 
```

## Slot-shuffled follows (answer changes only)
```
{
 "qwen|qwen|role": [
  0.938,
  0.893,
  0.982,
  112
 ],
 "qwen|smol|role": [
  0.938,
  0.893,
  0.982,
  112
 ],
 "qwen|pythia|role": [
  0.938,
  0.893,
  0.973,
  112
 ],
 "qwen|qwen|negation": [
  1.0,
  1.0,
  1.0,
  56
 ],
 "qwen|smol|negation": [
  1.0,
  1.0,
  1.0,
  56
 ],
 "qwen|pythia|negation": [
  1.0,
  1.0,
  1.0,
  56
 ],
 "qwen|qwen|uncertainty": [
  0.625,
  0.5,
  0.75,
  56
 ],
 "qwen|smol|uncertainty": [
  0.625,
  0.5,
  0.75,
  56
 ],
 "qwen|pythia|uncertainty": [
  0.625,
  0.5,
  0.75,
  56
 ],
 "qwen|qwen|order": [
  0.5,
  0.383,
  0.633,
  60
 ],
 "qwen|smol|order": [
  0.5,
  0.383,
  0.633,
  60
 ],
 "qwen|pythia|order": [
  0.5,
  0.367,
  0.617,
  60
 ],
 "qwen|qwen|maths_signed": [
  0.059,
  0.0,
  0.147,
  34
 ],
 "qwen|smol|maths_signed": [
  0.033,
  0.0,
  0.1,
  30
 ],
 "qwen|pythia|maths_signed": [
  0.088,
  0.0,
  0.206,
  34
 ],
 "smol|qwen|role": [
  0.982,
  0.955,
  1.0,
  112
 ],
 "smol|smol|role": [
  0.982,
  0.955,
  1.0,
  112
 ],
 "smol|pythia|role": [
  0.982,
  0.955,
  1.0,
  112
 ],
 "smol|qwen|negation": [
  0.607,
  0.482,
  0.733,
  56
 ],
 "smol|smol|negation": [
  0.607,
  0.464,
  0.714,
  56
 ],
 "smol|pythia|negation": [
  0.607,
  0.482,
  0.732,
  56
 ],
 "smol|qwen|uncertainty": [
  0.5,
  0.375,
  0.625,
  56
 ],
 "smol|smol|uncertainty": [
  0.5,
  0.375,
  0.625,
  56
 ],
 "smol|pythia|uncertainty": [
  0.5,
  0.375,
  0.625,
  56
 ],
 "smol|qwen|order": [
  0.65,
  0.517,
  0.767,
  60
 ],
 "smol|smol|order": [
  0.65,
  0.533,
  0.767,
  60
 ],
 "smol|pythia|order": [
  0.65,
  0.517,
  0.767,
  60
 ],
 "smol|qwen|maths_signed": [
  0.118,
  0.029,
  0.235,
  34
 ],
 "smol|smol|maths_signed": [
  0.133,
  0.033,
  0.267,
  30
 ],
 "smol|pythia|maths_signed": [
  0.118,
  0.029,
  0.235,
  34
 ],
 "pythia|qwen|role": [
  0.964,
  0.929,
  0.991,
  112
 ],
 "pythia|smol|role": [
  0.964,
  0.928,
  0.991,
  112
 ],
 "pythia|pythia|role": [
  0.964,
  0.929,
  0.991,
  112
 ],
 "pythia|qwen|negation": [
  0.821,
  0.714,
  0.911,
  56
 ],
 "pythia|smol|negation": [
  0.821,
  0.714,
  0.911,
  56
 ],
 "pythia|pythia|negation": [
  0.821,
  0.714,
  0.911,
  56
 ],
 "pythia|qwen|uncertainty": [
  0.536,
  0.411,
  0.661,
  56
 ],
 "pythia|smol|uncertainty": [
  0.536,
  0.411,
  0.661,
  56
 ],
 "pythia|pythia|uncertainty": [
  0.536,
  0.393,
  0.661,
  56
 ],
 "pythia|qwen|order": [
  0.5,
  0.367,
  0.633,
  60
 ],
 "pythia|smol|order": [
  0.5,
  0.367,
  0.634,
  60
 ],
 "pythia|pythia|order": [
  0.5,
  0.367,
  0.617,
  60
 ],
 "pythia|qwen|maths_signed": [
  0.029,
  0.0,
  0.088,
  34
 ],
 "pythia|smol|maths_signed": [
  0.0,
  0.0,
  0.0,
  30
 ],
 "pythia|pythia|maths_signed": [
  0.059,
  0.0,
  0.147,
  34
 ]
}
```

## Bytes / bits vs text
```
{
 "t1": {
  "prose_utf8_bytes": 43.5,
  "compact_utf8_bytes": 30.0,
  "prose_tokens": {
   "qwen": 9.0,
   "smol": 9.0,
   "pythia": 9.0
  },
  "compact_tokens": {
   "qwen": 11.214285714285714,
   "smol": 12.071428571428571,
   "pythia": 11.928571428571429
  },
  "id_bits": 11,
  "id_bytes_packed_plus_2B_version_header": 4,
  "id_bits_if_maths_had_4_ops": null,
  "vector_float32_bytes": 640,
  "vector_float32_bytes_plus_header": 642
 },
 "t2": {
  "prose_utf8_bytes": 29.766666666666666,
  "compact_utf8_bytes": 29.766666666666666,
  "prose_tokens": {
   "qwen": 6.166666666666667,
   "smol": 6.533333333333333,
   "pythia": 6.333333333333333
  },
  "compact_tokens": {
   "qwen": 9.6,
   "smol": 11.933333333333334,
   "pythia": 11.533333333333333
  },
  "id_bits": 11,
  "id_bytes_packed_plus_2B_version_header": 4,
  "id_bits_if_maths_had_4_ops": null,
  "vector_float32_bytes": 640,
  "vector_float32_bytes_plus_header": 642
 },
 "t3": {
  "prose_utf8_bytes": 4.0,
  "compact_utf8_bytes": 9.0,
  "prose_tokens": {
   "qwen": 4.0,
   "smol": 4.0,
   "pythia": 4.0
  },
  "compact_tokens": {
   "qwen": 6.0,
   "smol": 6.0,
   "pythia": 6.0
  },
  "id_bits": 6,
  "id_bytes_packed_plus_2B_version_header": 3,
  "id_bits_if_maths_had_4_ops": 8,
  "vector_float32_bytes": 512,
  "vector_float32_bytes_plus_header": 514
 }
}
```

## Runtime
```
{
 "setup_s": {
  "extraction_per_model_s(3 models in parallel, 3 threads each)": {
   "qwen": 789.6563129425049,
   "smol": 653.2192673683167,
   "pythia": 670.4058389663696
  },
  "negotiation_all_layers_and_ablation_books_s": 106.3
 },
 "runtime_test_s": {
  "qwen": 2998.3549745082855,
  "smol": 1449.0778455734253,
  "pythia": 1215.355702638626
 },
 "compute_median_ms": {
  "snap_s": 0.448,
  "decode_s": 0.134,
  "receipt_check_s": 0.27,
  "sender_forward_s": 170.24,
  "text_receiver_forward_s|qwen": 233.678,
  "glyph_receiver_forward_s_per_batched_row|qwen": 187.425,
  "text_receiver_forward_s|smol": 176.763,
  "glyph_receiver_forward_s_per_batched_row|smol": 134.039,
  "text_receiver_forward_s|pythia": 169.406,
  "glyph_receiver_forward_s_per_batched_row|pythia": 112.268
 }
}
```

## Files
- Code: `v4/`
- Book + states: `results/v4/book.pt`, `states_*.pt` (in the release tarball, not the git tree)
- Per-receiver tests: `results/v4/test_{qwen,smol,pythia}.json`
- Aggregates: `results/v4/tables_v4.json`
- Frozen layer choice: `results/v4/frozen.json`
