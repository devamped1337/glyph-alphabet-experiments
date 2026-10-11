# v6 PREREG: FROZEN 2026-10-11 (AEDT)

**Status:** FROZEN on 2026-10-11. Git tag `prereg-v6`. No v6 run had started when it was frozen. Any later change must be a dated amendment below, stating whether it was made before or after results were seen.

**Review history:** the draft revisions and all reviews are in [reviews/v5/](../reviews/v5/):
- Round 1: the four v5 reviews, plus [ALL_FOUR.md](../reviews/v5/round1/ALL_FOUR.md).
- Round 2: reviews plus [checks](../reviews/v5/round2/checks.md).
- Round 3: feedback on the draft.
- Round 4: sign-off.

Draft revs 1–3 are in the git history of [PREREG_v6_DRAFT.md](../reviews/v5/PREREG_v6_DRAFT.md).

**Sign-off:**
- **Grok:** signed off on all six rev-3 resolutions ([round4/grok.md](../reviews/v5/round4/grok.md)).
- **GPT:** final edits adopted ([round4/gpt.md](../reviews/v5/round4/gpt.md)).
- **Claude:** reviewed rounds 1–3. It **did not review rev 4 / this frozen version**, because its free usage limit was hit. Its round-3 positions are incorporated except where GPT's round-4 edits replaced them, as noted inline.

**Reference facts from v5** (round-2 checks, data commit 48a7a6a5):
- v5 froze the embedding layer.
- At emb with the last token, "not approved" and "approved" give identical vectors.
- Cross-model nulls sit at no-message level, and the real adapter beats them cross-model only.
- Answer-held-out LOO was about 0 (exclusion bias).

---

## 0. Structure
- **E1: the text repository** (IDs expanded into text by the receiver). It is run **first**.
- **E3: the unsnapped contextual channel.** This is the injection test and carries the primary injection claim.
- **E2: the snapped lookup.** A **control inside E3**. It is reported but makes no primary claim.

No DEV argmax chooses between channels or depths, and glyph accuracy is never used to select anything.

## 1. Depths, read position, basis
- **Calibration-selected depths:**
  - Candidates are block outputs at 40%, 50% and 60% of depth, each rounded to the nearest layer index.
  - A neutral probe is trained on a calibration set and evaluated on a **held-out negation calibration set** (negated vs non-negated pairs).
  - **Primary** = the shallowest candidate with ≥95% balanced accuracy. **Secondary** = primary +20 points of depth, rounded to the nearest layer.
  - The emb baseline is always run.
  - The procedure is frozen here. The resulting indices are recorded as an amendment before TEST and labelled "calibration-selected".
  - If no candidate reaches 95%, report that and do not run E3 as a contextual test.
- The secondary depth cannot rescue a failed primary claim.
- **Read position:** the state at the token after the full slot value, at the contextual hook.
- **Nulls** (random-orthogonal, shuffled-pair) are run at the primary depth. Their results are reported **cross-model**.
- **Basis:** PCA vs random of the same size.
- **J-lens:**
  - Feasibility budget on the target hardware: pilot ≤30 min, peak memory ≤80% of RAM/VRAM, full basis ≤2 h. It must also be supported by a reference implementation.
  - If it passes, J-lens is a separate arm in E3 at the primary depth, compared against PCA and random.
  - If it fails, record the omission before TEST, make **no J-space claim**, and call it the "contextual channel".
  - Sparse NNLS alone does not establish J-space.
- **Raw residual** (unsnapped) is its own condition, compared with snapped (control), expanded-ID text and prose.
- Every channel receives identical source information.

## 2. Tasks
- Include tasks that need context: negation, paraphrase, and definitions of 200+ tokens. Group them into 3 task families.
- Prose baselines must not contain the gold string.
- Add a placebo prose baseline with the answer token removed.
- Item counts per task are stated before TEST (see §7).

## 3. LOO / transfer
- LOO uses the **unsnapped contextual readout**.
- Remove the held-out entry from the receiver's book, prototypes, dictionaries and adapters, so the receiver has no fallback.
- Forced choice among ≥3 balanced candidates, none of them named in the message.
- **Baselines (all four, identical context):** zero ablation, mean-of-slot ablation, copy baseline, no-message. The comparison in each cell is against the **best** baseline.
- **Success:** the lower simultaneous paired 95% bound of (answer-held-out minus best baseline) is **≥ +0.10** on **≥2 of 3 task families**, in **both cross-model directions**. The bounds are simultaneous to correct for multiple comparisons.
- Smaller effects are reported, but they are not a success.
- Report answer-held-out and other-held-out separately.

## 4. Gate for the text repository
- **Behaviour-based**, with an external correctness check against gold.
- **Calibration:**
  - **N=40** fresh cases per entry. **N=100 is preferred if the budget allows**; if N=100 is used, this is stated before calibration.
  - An entry passes if each model is ≥0.90 correct vs gold and the two models agree ≥0.90.
  - The threshold is calibrated on honest and planted entries.
- **Confirmatory evaluation:**
  - Run on **separate TEST cases** with **corruption types unseen in calibration**, including near-miss pairs.
  - 10+ independent planted bad entries across named corruption types. The old v5 6 are re-run for continuity only.
- **Pass:** ≥90% acceptance of valid entries **and** ≥95% rejection of planted corruptions.
  - Rejection of 80–95% is reported as a **weaker outcome, not a pass**. (This replaces Claude's round-3 ≥0.80 specificity floor, per GPT round 4.)
  - Report counts plus uncertainty (CIs).
- If nothing separates honest from planted entries in calibration, the gate is not frozen and this is reported.

## 5. Logging
- Log coverage on every row.
- Keep separate fields for coverage, selection (the snapped ID) and decoding.
- Report end-to-end and covered-only results.
- **Unknown-ID:** a deterministic parser test, labelled as such, plus an optional model-abstention test. Any abstention claim requires the model test.

## 6. Efficiency
- No padding. Measure receiver tokens, FLOPs and latency.
- **Sender compute** (estimated at ~170 ms) is **measured**. End-to-end timing includes sender and encoding.
- Report the amortized dictionary cost and the break-even message count.
- **Baselines:** uncached expansion, and a **valid** cached KV expansion (identical prefix only, no concatenated independent KV). Report construction cost, storage, hit rates, and cold and warm timing.

## 7. Statistics and win criteria
- **Accuracy win:** paired 95% CI entirely above zero vs ID-expanded text.
- **Primary efficiency win:** non-inferior within **5 points** of ID-expanded text **and** **≥20% lower receiver latency** vs the valid cached expansion. Tokens and FLOPs are reported.
- **Secondary token claim** (separate): ≥30% fewer **newly processed receiver tokens after the cache**.
- **LOO win:** as in §3.
- **Sample size:** 80% power to detect 5 points needs about **300 pairs at 10% discordance** and **about 600 at 20%**, and more with clustering by message group. (n ≈ 1540 × discordance is a precision target, not power.) Per-task item counts are fixed before TEST, using the clustering-adjusted figure.
- Count message groups and semantic items separately, and declare aggregation in advance.
- Use a ±0.05 equivalence / non-inferiority margin. Record **inconclusive** separately from **equivalent**.
- Run seeds only if they vary something real.

## 8. Stop rule
If this 7B implementation shows **neither an accuracy nor an efficiency advantage** (as defined in §7, where "equal" means within the non-inferiority margin), stop expanding it and prioritise the text repository with the behaviour gate. Record inconclusive separately from equivalence.

---

## Amendments
- **2026-10-11 (before any v6 results were seen; no v6 run has started):** `v6/checks/validate_v6.py` (from Grok's review, with checklist `v6/checks/v6_checklist.md`) is a mandatory pre-publication gate. It must be run on the v6 results directory before any RESULTS are written or published. A non-zero exit code means no publishing until the failures are fixed and the validator passes cleanly.
