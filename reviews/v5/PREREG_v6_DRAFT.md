# v6 PREREG: DRAFT, rev 3 (NOT FROZEN)

Sources:
- Round 2: [Grok](round2/grok.md), [Claude](round2/claude.md), [GPT](round2/gpt.md).
- Round 3: [Grok](round3/grok.md), [GPT](round3/gpt.md), [Claude](round3/claude.md).
- [Round-2 checks](round2/checks.md).

Every numeric threshold is an engineering target, to be frozen before any results. **[CONFLICT]** marks a point where the round-3 numbers disagree. Each one lists the options and a proposed resolution, which needs sign-off before freezing.

## Freeze now (Claude round 3; consistent with Grok/GPT once the conflicts are resolved)
- Structure (§0)
- LOO channel and baselines (§3)
- Gate calibration procedure (§4)
- Statistics and win criteria (§7)
- Stop rule (§8)

## Deferred (frozen before TEST, after these steps)
- **Exact depths:** until the calibration probe has run (§1).
- **J-lens:** until the feasibility check has run (§1).

## Conflict list
1. Depth selection (§1)
2. Role of E2 (§0)
3. LOO baselines (§3)
4. LOO success bar (§3)
5. Gate N and thresholds (§4)
6. Efficiency win (§6/§7)

Settled background:
- Cross-model nulls sit at no-message level, and the real adapter beats them **cross-model**.
- At emb with the last token, "not approved" and "approved" give identical vectors. "authorized" is not a collision.

## 0. Structure
- **E1: the text repository** (expanded IDs). It is **run first** (Claude): API-based, cross-lab, takes days.
- **E3: the unsnapped contextual channel.** This is the main injection test.
- **E2: the snapped lookup.**
  - **[CONFLICT 2]** GPT: E2 is a separate experiment with its own primary comparison. Claude: demote E2 to a control inside E3.
  - *Proposed:* make E2 a control inside E3. It is reported, but it carries no primary claim. v5 already showed that the snapped path is a lookup (glyph ≈ receiver_word_state largely by construction).

No DEV argmax chooses between channels or depths. Glyph accuracy is never used to pick anything.

## 1. Channels and depths
- **Depths:** one primary claim at ~40% and a secondary at ~60%. The secondary cannot rescue the primary (all three agree), and emb is the baseline. The hooks are block outputs.
- **[CONFLICT 1]** How the exact indices are chosen:
  - GPT/Grok: fixed fractions (~40% and ~60%), with indices frozen before TEST.
  - Claude: a neutral calibration probe must separate negated pairs at ≥0.95. Freeze the shallowest qualifying depth and the depth +20 points deeper.
  - *Proposed:* use Claude's probe to qualify. Primary = the shallowest qualifying depth at or above ~40%; secondary = primary + 20 points (≈60%). If no depth reaches 0.95, report that and do not run E3 as a contextual test.
- **Read position:** the state after the full slot value, at the contextual hook. The v5 problem was reading before context.
- **Nulls:** run at the primary depth only (Claude).
- **Basis:** PCA vs random of the same size.
- **J-lens:**
  - Pre-register the feasibility criteria: a memory/time budget **[OPEN: numbers]** and support in a reference implementation.
  - If it passes, J-lens is a separate arm in E3 at the primary depth only, compared against PCA and random.
  - If it fails, record the omission before TEST, make **no J-space claim**, and call it the "contextual channel".
  - Sparse NNLS alone does not prove J-space.
- **Raw residual** (unsnapped) is its own condition, compared with snapped (control), expanded-ID and prose.
- Every channel gets identical source information.

## 2. Tasks
- Include tasks that need context: negation, paraphrase, and definitions of 200+ tokens. Group them into ≥3 task families for the LOO criterion.
- Prose baselines must not contain the gold string.
- Add a **placebo prose baseline with the answer token removed** (Claude).

## 3. LOO / transfer
- LOO uses the **unsnapped contextual readout** (Claude).
- Remove the held-out entry from the receiver's book, prototypes, dictionaries and adapters, so the receiver has no fallback.
- Forced choice among 3+ balanced candidates that are **not named in the message** (Claude, GPT).
- **[CONFLICT 3] Baselines:**
  - GPT/Grok: slot-ablated is primary, with no-message alongside, in identical context.
  - Claude: zero ablation, mean-of-slot ablation and a copy baseline; compare against the best of the three.
  - *Proposed:* run all of them (zero ablation, mean-of-slot ablation, copy, no-message) in identical context. The comparison is against the **best** baseline in each cell. This contains both proposals and is the stricter reading.
- **[CONFLICT 4] Success bar:**
  - GPT: beat both baselines in each cross-model direction, with the transfer rate defined in advance.
  - Claude: the lower 95% bound of (held-out minus best baseline) ≥ +0.10 on ≥2 of 3 task families.
  - *Proposed:* both must hold. Claude's numeric bar (lower bound ≥ +0.10 vs best baseline, ≥2 of 3 families) must be met in **each** cross-model direction.

## 4. Gate for the text repository
- Behaviour-based, with an external correctness check against gold.
- **[CONFLICT 5]:**
  - GPT: 100 fresh cases per entry; each model ≥95% correct and ≥95% agreement; target ≥90% acceptance of valid entries and ≥95% rejection of planted corruptions.
  - Claude: 40 fresh cases per entry; each model ≥0.90 vs gold and ≥0.90 agreement; the threshold is calibrated on honest and planted entries to ≥0.90 sensitivity and ≥0.80 specificity.
  - *Proposed:* use Claude's **calibration procedure**, which sets the threshold empirically, with GPT's targets as the goal (≥0.90 acceptance of valid entries, ≥0.95 rejection of planted). N=40 per entry for calibration. If ≥0.95 rejection cannot be reached while keeping ≥0.90 acceptance, accept Claude's ≥0.80 floor and report the shortfall.
  - Alternative: GPT's fixed N=100 at 95%/95%, if API cost allows. Note that N=40 cannot resolve 95% precisely.
- **Corruptions:**
  - 10+ independent planted bad entries covering named corruption types.
  - TEST corruption types are unseen in calibration and include near-miss pairs (Claude).
  - The old 6 are re-run for continuity only.
- If nothing separates honest from planted entries, don't freeze the gate; report it.

## 5. Logging
- Log coverage on every row.
- Keep separate fields for coverage, selection and decoding, because the snap silently maps rejected meanings to neighbours.
- Report both end-to-end and covered-only results.
- **Unknown-ID:** a deterministic parser test, labelled as such, plus an optional model-abstention test. Any claim about abstention requires the model test.

## 6. Efficiency
- No 64-token padding.
- Report:
  - receiver tokens, FLOPs and latency;
  - sender compute (~170 ms per Claude);
  - amortized dictionary cost and the break-even message count.
- Compare against uncached expansion and a valid cached KV expansion. The cache must use an identical prefix only. Report construction cost, storage, hit rates, and cold and warm timing.

## 7. Statistics and win criteria
- **Accuracy win:** paired 95% CI entirely above zero vs ID-expanded text.
- **[CONFLICT 6] Efficiency win:**
  - GPT: within ±5 points **and** ≥20% lower receiver latency.
  - Claude: non-inferiority **and** a minimum saving such as ≥30% fewer receiver tokens.
  - *Proposed:* non-inferiority margin of 5 points vs ID-expanded text, **and** ≥30% fewer receiver tokens **and** ≥20% lower receiver latency against the cached baseline, both measured. Tokens are deterministic; latency checks that the saving is real.
- **LOO win:** see §3.
- **Power:** n ≈ 1540 × discordance (about 150 items at 10% discordance, 300 at 20%). Item counts are stated per task before TEST. Message groups and semantic items are counted separately, and aggregation is declared in advance.
- Use a ±0.05 equivalence / non-inferiority margin. Record inconclusive separately from equivalent.
- Run seeds only if they vary something real.

## 8. Stop rule (pre-registered)
If this 7B implementation shows **neither an accuracy nor an efficiency advantage** (as defined in §7, where "equal" means within the non-inferiority margin), stop expanding it and prioritise the text repository with the behaviour gate. Record inconclusive separately from equivalence. (GPT wording, with Claude's non-inferiority definition.)
