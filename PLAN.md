# Experiment plan: testing a shared glyph alphabet between two open models (a = a)

*Follow-up to forum post #8126. Goal: turn the "shared glyph alphabet" idea into something a small lab or a skilled hobbyist can run in a few weeks on modest GPUs, with clear ways for it to fail.*

## The idea in one paragraph
Agents from different labs exchange dense "glyphs" instead of text. A glyph is a point (or a small sparse bundle) in one canonical shared space. Each model has one adapter in and one adapter out (hub and spoke, not N² pairwise translators). A glyph can have depth (core concepts, context, confidence) and time (a short sequence of glyphs for a process). No trust is needed, only consistency: a glyph must decode to the same meaning through every adapter (a = a), checked by round trips. The dictionary grows only from definitions every party can reproduce. Each glyph also carries a plain-language audit receipt. Inside one lab's fleet on the same base model, cache-to-cache (KV) sharing is the faster option. Glyphs are for traffic between vendors.

## Prior work this builds on (checked)
- **Global workspace / Jacobian lens.** "Verbalizable Representations Form a Global Workspace in Language Models" (Anthropic, July 2026; arXiv 2607.15495; transformer-circuits.pub/2026/workspace). The J-lens maps a residual vector at layer l through the corpus-averaged Jacobian J_l = E[dh_final/dh_l] and decodes it with the model's own unembedding, giving token-anchored directions ("J-space"). The paper reports that J-space carries coherent content only in an intermediate band of layers, holds on the order of tens of concepts at a time, and that its contents can be summoned, held and passed to downstream computation. Code: github.com/anthropics/jacobian-lens (Apache 2.0). It fits lenses on HF decoders (examples use Qwen). The paper used 1000 sequences of 128 tokens, and the README says about 100 prompts is usable.
- **Cache-to-Cache (C2C).** Fu et al., arXiv 2510.03215 (ICLR 2026; code at github.com/thu-nics/C2C). A small learned fuser projects one model's KV cache into another's, with gates that pick which layers to use. It reports gains over text-to-text communication and lower latency. It's the obvious strong baseline for "beyond text" handoff, but it is pairwise and opaque by design.
- **Representation convergence.** Huh et al., "The Platonic Representation Hypothesis" (ICML 2024, arXiv 2405.07987) argues that representations across models and modalities are converging. Moschella et al., "Relative representations enable zero-shot latent space communication" (arXiv 2209.15430) shows that describing each sample by its similarity to a fixed set of anchors allows zero-shot stitching across models. That is the conceptual basis for the v0 anchor-based glyph space below.

## 1. Models
- **Model A:** Qwen2.5-7B-Instruct (the J-lens reference code targets Qwen).
- **Model B:** Llama-3.1-8B-Instruct, or Mistral-7B-Instruct, or Gemma-2-9B-it.
- Different tokenizers, training data and architectures are a **feature**, because this is a cross-vendor test. If it only works within one family, KV sharing already does that better.
- Hardware: one 48-80 GB GPU, or two 24 GB cards with bf16 and gradient checkpointing for the lens fit. Everything after the lens fit is inference plus small adapter training.

## 2. Step 1: fit J-lenses and extract workspace states
1. Fit a J-lens on each model with the reference code: about 500-1000 generic web-text prompts of 128 tokens, all middle layers as source layers. Parallelise with `fit()` on disjoint prompt slices plus `JacobianLens.merge()`.
2. Pick a **workspace band** per model: the layers where lens readouts are most coherent (for example, top-k lens tokens agree with a held-out "what are you thinking about?" probe). Record the band. Don't assume it's the same relative depth in both models.
3. For each prompt and position, define the **workspace state** as a sparse bundle: the top-k (k ≈ 32-64) J-space token directions with their lens weights, averaged over the band.
4. Sanity checks: the bundles should be stable under paraphrase and should change under concept swaps.

## 3. Step 2: build the canonical glyph space
**v0: shared-vocabulary anchors (no training).**
- Build a shared concept list C of about 2-5k words that both tokenizers represent as a single token, or as an unambiguous first token (nouns, verbs, numbers, relations, logic words).
- Encoder E_m: map model m's J-space bundle to a weight vector over C, by restricting lens logits to C's token ids and renormalising (sparse, top-k).
- Decoder D_m: turn a weight vector over C back into a residual-stream steering vector for model m, as a weighted sum of the residual directions whose J-lens readout is each concept (solve via the pseudo-inverse of J_l restricted to the concept unembedding rows).
- This is the relative-representation idea with words as anchors. It's interpretable by construction.

**v1: learned adapters into a shared latent.**
- Build parallel prompts: the same content shown to both models (the same text works because each model tokenises it itself), plus paraphrase and translation pairs.
- Per model, train a small MLP or linear adapter E_m: bundle → z in R^256 and D_m: z → steering vector, using an InfoNCE contrastive loss across models on parallel items plus a reconstruction loss (D_m(E_m(x)) ≈ x in lens space).
- Keep the v0 anchor head as an auxiliary readout so that z always has a word-level receipt.

**Glyph definition.** A glyph is a vector or sparse bundle in the canonical space with optional channels:
- `core`: the main concept weights
- `context`: secondary concepts or framing
- `confidence`: a scalar or per-concept certainty
- optional `time`: a short sequence of T ≤ 8 glyphs for steps of a process
- **receipt**: the top concepts rendered in plain language. It is generated by the decoder, not stored, so it can be checked.

## 4. Step 3: the a = a tests
(a) **Within-model round trip.** For A and for B: x → glyph → steer the model → re-read the bundle → glyph'. Measure cosine drift and top-k concept overlap (Jaccard).
(b) **Cross-model.** A encodes the glyph for a task state, then B decodes it by injecting the steering vector into its workspace band (residual addition at the last prompt positions, with a swept scale). Check B's answer or behaviour against A's intent, using task labels or a judge.
(c) **Receipt consistency.** Decode the same glyph through D_A and D_B and have each model verbalise it ("what concept are you holding?"). The two receipts must agree, measured by concept overlap and an NLI/judge check.

**Metrics:** round-trip error, cross-model task accuracy vs a text-handoff baseline, bandwidth (glyph bytes vs text tokens × bytes), end-to-end latency, and receipt agreement rate.

## 5. Step 4: downstream handoff tasks
- Partially solved multi-step arithmetic (A computes intermediate values, B finishes).
- Two-hop QA (A resolves hop 1, for example a bridge entity, and B answers hop 2).
- Context handoff (A reads a long passage, B answers questions about it).

Compare the glyph handoff against (i) full text handoff, (ii) a compressed text summary capped at the glyph's byte budget, (iii) no handoff (B alone), and optionally (iv) a C2C fuser where one exists for the pair. Run with at least 3 seeds and report confidence intervals.

## 6. Step 5: dialect drift and minimal pairs
- **Drift.** LoRA fine-tune model B slightly (for example a few hundred steps on a domain corpus), re-fit or keep its lens, and rerun the round-trip tests. Success means drift shows up as rising round-trip and receipt-disagreement error, ideally before downstream accuracy collapses. Also sweep fine-tune size to get a dose-response curve.
- **Minimal pairs.** Build glyph pairs that differ in one concept (cat/dog, increase/decrease, true/false, 7/8). Each pair must stay distinguishable through both adapters, and through A→B, above a set margin. Report the fraction of pairs that collapse.

## 7. Step 6 (optional): toy consortium
- Two "steward" agents, one per model, propose new glyph definitions (a composite concept plus a receipt).
- Accept a definition only if it round-trips within tolerance through both adapters and both receipts agree.
- Log dictionary growth, acceptance rate, rejection reasons, and whether accepted glyphs still pass the minimal-pair tests later.

## 8. Success criteria and falsifiers
**Success:** on at least one handoff task, the glyph handoff matches text handoff accuracy (within CI) at ≤ 10-20% of the bandwidth. Cross-model receipt agreement is high, and drift is detectable.
**Kills the idea (or v0/v1 of it):**
- B ignores injected bundles: cross-model accuracy stays at the no-handoff baseline at every injection scale. That would mean the workspace isn't a usable input channel across models.
- Round trips work within a model but not across: the canonical space isn't shared.
- Receipts agree while behaviour diverges: then receipts aren't a valid audit.
- A compressed text summary at the same byte budget does as well. Then glyphs add nothing over terse English.

## 9. Risks and open questions
- The workspace is only coherent in a middle band, so the choice of injection layer may dominate the results.
- Injection might change lens readouts without being causally used (a readout artefact rather than a channel). Check with causal ablations.
- Tokenizer mismatch shrinks the shared concept list, and multi-token concepts are hard for v0.
- Steering can also push models off-distribution, so watch fluency and refusal rates.
- **Safety and audit:** a dense channel between models is also a covert-channel risk. Receipts have to be checked independently, not just trusted, and glyph traffic should be loggable and replayable.
- Open question: does this scale to more than two models without the canonical space drifting towards whichever model dominates training?

## Suggested timeline (~4-6 weeks)
Week 1: lens fits and workspace bands. Week 2: v0 space and round-trip tests. Week 3: v1 adapters and cross-model injection. Week 4: handoff tasks and baselines. Week 5: drift and minimal pairs. Week 6: consortium toy and write-up.
