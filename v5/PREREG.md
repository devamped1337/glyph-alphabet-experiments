# v5 pre-registration (written before any v5 dev or test run)

Fixed in code before running: models and revisions (spec5.MODELS), 64-token prompts (spec5.fit64), splits (spec5.messages, seeded),
candidate depths {emb, 0.25, 0.33 of depth}, KP=64, KC=32, seeds {0,1,2}, bases {pca, jlens, random}, gate checks and thresholds (negotiate5.check).

1. **Task gate (rule A).** A task|question counts on a receiver only if `text_prose` >= 0.90 on that receiver's DEV split and `none` (no message) < 0.90.
   Tasks that fail are dropped from that receiver's test run and listed as dropped. They are not reported as glyph wins or losses.
2. **Depth (rule B).** One depth index is frozen from DEV only: the argmax of mean `glyph_id` (pca, seed 0) accuracy, pooled over both receivers,
   both senders and all counted task|questions. Ties go to the shallower depth. Every other test condition uses this depth, except `glyph_emb`, which is the embedding-level comparison.
3. **Primary comparison.** `glyph_id` (pca, seed 0) vs `id_text_expanded` (the same ID bytes, expanded to a prose sentence by the receiver) vs `text_prose` and `text_compact`.
   Report: per receiver x sender x task|question, mean and 95% cluster bootstrap CI (clusters = message groups, 2000 resamples).
   "Ties" means the CIs overlap. "Beats" means the lower CI bound is above the other condition's upper bound.
4. **Maths.** Exact answer, magnitude (|pred| = |gold|) and sign (sign(pred) = sign(gold), with 0 as its own sign) are scored separately.
   The maths task is limited by its 100 digit pairs (47 test pairs x 4 sender frames = 188 deliveries). That is under n=200, so it is reported with clustered CIs.
5. **Controls are reported, never tuned on:** null adapters (random orthogonal sender Q; shuffled-pair Procrustes), slot/operand-order swap (follow rate),
   operand change (follow rate), same-norm shuffled code, receiver's own word state, raw unsnapped transfer, LOO books, planted entries.
6. **Gate test.** Success means every planted bad entry (Zed: mismatched cross-model labels; Noise: random vector) is rejected and LOO entries pass at a reported rate.
   LOO receiver accuracy is reported separately for held-out entries that passed the gate and those that failed it.
7. **Determinism (0).** Same model on two machines (SmolLM2-1.7B on box and laptop): max |dlogit| <= 1e-2 with identical top-1 and top-10 sets for the fixed injected state.
   Within each machine, a repeat run and a reload from disk must be bitwise equal. If the cross-machine check fails, cross-machine results are flagged, not discarded.
8. **Selection test.** Confusable places (countries, capitals and other cities in the same slot), name frames and clue phrases:
   top-1/3/5, confusion matrix, same-country rate and a string-match baseline, on the sender's own gallery and the other model's gallery.
