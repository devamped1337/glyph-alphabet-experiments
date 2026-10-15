# GPT design memo: E1c (via the Codex CLI, 2026-10-15)

*Verbatim reply to a self-contained Ask / Context / Artifacts / Scope / Output prompt (`codex exec -s read-only`). This is a design input only: nothing is pre-registered or launched.*

## Summary recommendation

Pre-register E1c as a test of **verified ID communication with prose fallback**, with both sending directions required to pass. Use **240 fresh entries per direction, four TEST cases per entry**.

This offers a credible proof of concept within the remaining budget **if development data show an entry-level harmful-selection rate around 2% or less**. It supports a claim about the hybrid protocol, not unconditional ID-only communication.

Do not reduce candidate difficulty or choose the better direction after seeing TEST results.

## Design

### Arms and pairing

For each entry, evaluate:

1. **Prose:** receiver gets the original rule message.
2. **Hybrid:** receiver gets the selected ID expanded through the shared dictionary if verification passes; otherwise, it gets the identical original prose message.

Run both directions:

- Qwen sender → Falcon receiver.
- Falcon sender → Qwen receiver.

Use the same four arithmetic questions across arms. Keep calls stateless, freeze decoding settings, and randomize execution order. Reuse a single prose response when fallback produces an exactly identical receiver request; pre-register this identity-based reuse.

An always-ID arm is optional development work, **not a confirmatory endpoint** unless separately budgeted and frozen before TEST.

### Sender procedure

Use a fixed, bounded procedure:

1. Sender receives the prose and four candidates, and returns one candidate label in a strict schema.
2. A separate, stateless verifier sees the original prose **without the selected candidate or candidate list** and extracts a canonical rule specification: operations, constants, signs, variable roles and evaluation order.
3. Deterministic code compares that specification with the selected dictionary entry.
4. Send the ID only if parsing succeeds, the specifications match exactly, and the dictionary hash matches. Otherwise, fall back to prose.

No retries, majority voting, confidence thresholds fitted on TEST, or receiver-informed selection. A format error triggers fallback rather than silently dropping the entry.

This verification scheme must first demonstrate feasibility on development data. If it cannot represent the rule families unambiguously, revise it before freezing E1c.

### Candidate sets

Retain the four-candidate challenge:

- One true entry.
- Three neighbours produced by frozen swapped/shifted-constant transformations.
- Exactly one semantically correct candidate.
- Balanced, randomized candidate positions and opaque IDs.

Generate a fresh dictionary and fresh rule instances. Keep the two established families, balanced at 120 entries each. Do not remove difficult examples based on sender performance.

## Answers to 1–5

### 1. How should selection improve?

Prioritize **independent structured extraction plus deterministic verification**. It targets the observed selection bottleneck and provides an explicit fallback condition.

Keep retrieval difficulty fixed so an improvement has a clear interpretation. Better retrieval can be a later experiment. Top-k and self-consistency add computation and tuning opportunities; self-reported confidence is a weak acceptance rule.

The verifier can still reproduce the sender’s semantic mistake. Hiding candidates reduces anchoring but does not establish independence.

### 2. Is a hybrid arm legitimate?

**Yes, provided fallback is part of the treatment and every assigned entry remains in the analysis.**

The supported claim is:

> On the registered task distribution, a verified ID/prose protocol preserves accuracy within five percentage points while meeting registered ID-use and communication-saving requirements.

It does **not** establish non-inferiority of always sending an ID.

Freeze these additional requirements, separately for each direction:

- **ID coverage ≥85%**; fallback ≤15%.
- **Steady-state transmitted-byte saving ≥30%** against prose.
- Positive net byte savings after dictionary setup at a registered deployment horizon of **1,000 messages**.

Count all protocol-required transmitted content, including IDs, hashes and fallback messages. Report model prompt/completion tokens and GPU time separately. If verification requires another communicating party, its traffic belongs in the byte accounting.

### 3. What sample size and power are needed?

The independent unit is the **entry**, not each arithmetic question. Four questions help characterize an entry’s outcome but do not create four independent selection decisions.

Use **240 entries per direction** as the budget-conscious recommendation. It has approximately 91% power per direction if the true hybrid deficit is 2 percentage points under the simplified clustered-error model below. Requiring both directions lowers joint power.

If development results suggest a 3-point deficit, plan approximately **600 entries per direction across weeks**. More sampling cannot make a true deficit exceeding five points non-inferior.

### 4. What should count as success?

For each direction, define:

\[
D_i=\text{mean hybrid accuracy on entry }i-
\text{mean prose accuracy on entry }i.
\]

Primary endpoint: mean \(D_i\), with equal weight per entry.

Use a paired, family-stratified cluster bootstrap over entries, retaining all four questions and both arms together. Freeze **2,000 resamples**, the bootstrap seed and the percentile-CI implementation.

E1c succeeds only if **both directions** meet:

- Lower bound of the two-sided 95% CI **strictly greater than −0.05**.
- ID coverage ≥85%.
- Registered byte-saving requirements.

Requiring both directions is an intersection–union decision; no multiplicity adjustment is needed for this conjunctive success claim. Label each direction using the existing mutually exclusive rules. A single passing direction is a secondary finding, not overall success.

Accuracy on accepted-ID entries, selection accuracy, verifier rejection rate, latency and family-specific results are secondary diagnostics. Accepted-ID accuracy alone is subject to selection bias.

### 5. How do we avoid overfitting?

Use separate development and TEST generation seeds and artifacts. Freeze the protocol before generating or revealing TEST outcomes.

Adapting to known failure modes is legitimate prospective development. The safeguards are fresh evaluation data, a bounded development process, and no further adaptation after TEST begins.

Use fresh constants, paraphrases, candidate positions and arithmetic inputs; exclude exact and semantic duplicates of development and E1b instances. Keep TEST answer keys inaccessible to sender and receiver prompts.

## Power and budget table

Power approximations assume prose is perfect and each harmful entry loses all four answers. If the harmful-entry probability is \(q\), then:

\[
n \approx
\frac{(1.96+0.84)^2q(1-q)}{(0.05-q)^2}.
\]

These are planning approximations, not guarantees. Replace them with frozen simulations using development estimates of the complete paired entry outcomes.

| True hybrid deficit | Entries/direction for ≈80% power | Power at 240/direction | Power that both pass* |
|---|---:|---:|---:|
| 1 percentage point | 49 | >99% | >99% |
| 2 percentage points | 171 | ≈91% | ≈83% |
| 3 percentage points | 571 | ≈44% | ≈20% |
| 4 percentage points | 3,011 | ≈12% | ≈1% |

\*Approximate product assuming independent directional outcomes. Small-error normal approximations can be inaccurate.

| Budget component | GPU-hours |
|---|---:|
| Bounded development pilot, parser and timing validation | 0.5 |
| 240 entries/direction, scaled from the measured 0.9 h per 60 | 3.6 |
| Additional verification inference allowance | 0.4 |
| Load, restart and runtime contingency | 1.0 |
| **Total reservation** | **5.5** |

The 3.6-hour estimate is a linear extrapolation, not a measured E1c runtime. Time the exact pipeline during the pilot. Prose-response reuse on fallback may save time, but do not depend on it.

Before TEST, choose and register one fixed sample size:

- **240/direction** if the pipeline fits and development supports a roughly ≤2-point deficit.
- **600/direction across weeks** if a roughly 3-point deficit is plausible.

Do not inspect TEST results at 240 and then extend to 600 under the same fixed-sample analysis.

## Pre-registration checklist

- [ ] State the hybrid claim and require success in both directions.
- [ ] Freeze model revisions, quantization, prompts, decoding and context settings.
- [ ] Freeze dictionary schema, canonicalization, parser, verifier and fallback logic.
- [ ] Validate parsers with malformed-output fixtures, including the archived formatting failure.
- [ ] Freeze family allocation, candidate-generation rules, seeds and deduplication checks.
- [ ] Freeze four-question generation and scoring rules.
- [ ] Fix sample size using development data and timing only.
- [ ] Freeze bootstrap implementation, seed, CI and strict decision inequalities.
- [ ] Freeze coverage, byte accounting and setup-amortization requirements.
- [ ] Specify handling of missing responses, timeouts and interrupted runs; never discard model failures.
- [ ] Archive every raw response, selected ID, verification result, fallback reason and dictionary hash.
- [ ] Allow infrastructure-only resumption; prohibit outcome-driven prompt changes or sample extension.

## Risks

- **Correlated errors:** selection and verification can agree on the same wrong interpretation.
- **Insufficient coverage:** accuracy may pass because fallback is frequent; the coverage gate prevents that claim.
- **Limited power:** 240 entries is persuasive only if residual errors are rare.
- **Runtime uncertainty:** verification prompts may exceed the reserved allowance.
- **Narrow generalization:** success covers these models, two rule families and this candidate regime.
- **Cost trade-off:** communication savings may coexist with higher inference cost; report both.
