# v6 PREREG: DRAFT, rev 2 (NOT FROZEN; waiting on Claude round 3)

Sources:
- Round 2: [Grok](round2/grok.md), [Claude](round2/claude.md), [GPT](round2/gpt.md).
- Round 3: [Grok](round3/grok.md), [GPT](round3/gpt.md).
- [Round-2 checks](round2/checks.md).

Rev 2 resolves the four former [DIFFERS] items using Grok's and GPT's round-3 positions, which agree on all four, and adopts GPT's numbers wherever they tighten the draft. Every threshold below is an engineering target, to be frozen before any results are seen. Items that remain open are marked **[OPEN]**.

Settled background (round-2 checks, reproduced by GPT/Claude):
- Cross-model nulls sit at no-message level, and the real adapter beats them **cross-model**.
- At emb with the last token, "not approved" and "approved" give identical vectors.

## 0. Structure
Run three separate experiments, each with its own primary comparison:
- **E1:** the text repository (expanded IDs).
- **E2:** the snapped lookup.
- **E3:** the unsnapped contextual channel.

No DEV argmax chooses between channels or depths. Freeze all of the following before TEST: layer indices, hooks, token positions, the coverage definition, the LOO procedure, aggregation, sample sizes and statistics.

## 1. Channels and depths
- **Layers:** ~40% depth is **primary**, ~60% is **secondary**, and emb is the baseline. The exact layer indices for each 7B model are frozen before TEST. The hooks are block outputs. A good 60% result stays labelled secondary.
- **Read position:** specify both the token position (the state after the full slot value) and the contextual hook. The v5 problem was reading *before context*, not the choice of token.
- **Basis:** PCA vs random of the same size.
- **J-lens:**
  - Run a 7B feasibility check with a numeric memory/time budget. **[OPEN]**: exact budget numbers to be set before freezing.
  - If it passes, J-lens is a separate arm, compared against PCA and random.
  - If it fails, record the omission before TEST.
  - Sparse NNLS alone does not prove J-space.
- **Raw residual** (unsnapped) is its own condition, compared with snapped, expanded-ID and prose.
- Every channel gets identical source information.

## 2. Tasks
- Include tasks that need context: negation, paraphrase, and definitions of 200+ tokens.
- **Prose baselines must not contain the gold string.** In v5, place prose used the gold name, which acted as an oracle on 14 Qwen / 30 Smol rows.

## 3. LOO / transfer
- Remove the held-out entry from the receiver's book, prototypes, dictionaries and adapters, so the receiver has no fallback.
- **Baselines:** slot-ablated is primary, with no-message alongside. Both use identical context.
- Use 3+ balanced candidate entities with forced choice.
- Report answer-held-out, other-held-out, slot-ablated and no-message separately.
- **LOO win:** answer-held-out accuracy beats **both** baselines in **each cross-model direction**. The transfer rate that counts as success is defined in advance.

## 4. Gate for the text repository
- **Behaviour-based:** 100 fresh calibration cases per entry. An entry passes if each model is **≥95% correct** (the external correctness check) and the two models agree **≥95%**.
- **Targets:** accept ≥90% of valid entries (the false-reject rate is reported) and reject ≥95% of planted corruptions.
- Use 10+ independent planted bad entries covering named corruption types. The old 6 (2 designs × 3 depths) are re-run for continuity only.

## 5. Logging
- Log coverage on every row.
- Keep separate fields for coverage, selection (which ID was snapped to) and decoding, because the snap silently maps rejected meanings to neighbours.
- Report both end-to-end and covered-only results.
- **Unknown-ID:** keep it as a deterministic **parser test**, labelled as such. Add an **optional model-abstention test** (the model is called and abstention is logged).
  - Grok wanted a model call; GPT accepts the parser test, with a model test only if an abstention claim is made.
  - Rule: any claim about abstention requires the model test.

## 6. Efficiency
- No 64-token padding. Report receiver tokens/FLOPs and latency.
- Compare against uncached expansion **and** a valid cached KV expansion. The cache must use an identical prefix only (no concatenating independent KV). Report cache construction cost, storage, hit rates, and cold and warm timing.
- On the wire, glyph_id and id_text_expanded are both 9 B, so injection can only win on compute.

## 7. Statistics and win criteria
- **Accuracy win:** paired 95% CI entirely above zero vs ID-expanded text.
- **Efficiency win:** accuracy within ±5 points of ID-expanded text **and** ≥20% lower receiver latency.
- **LOO win:** as defined in §3.
- Count message groups and semantic items separately. Declare aggregation and sample sizes in advance.
- Use a ±0.05 equivalence margin. Record **inconclusive** separately from **equivalent**.
- Run seeds only if they vary something real.

## 8. Stop rule (GPT round-3 wording, pre-registered)
If this 7B implementation shows **neither an accuracy nor an efficiency advantage** (as defined in §7), stop expanding it and prioritise the text repository with the behaviour gate. Record inconclusive separately from equivalence.

(Claude's round-2 version, kept for reference: "if the contextual channel does not beat emb and cached expansion at equal accuracy on 7B, retire injection.")
