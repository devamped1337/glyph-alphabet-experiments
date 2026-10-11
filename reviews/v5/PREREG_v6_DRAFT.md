# v6 PREREG: DRAFT (merged from the round-2 proposals; not frozen)

Sources: [Grok](round2/grok.md), [Claude](round2/claude.md), [GPT](round2/gpt.md) round-2 reviews, plus the [round-2 checks](round2/checks.md). Claude's stop rule is included. Where the three proposals differ, the difference is marked **[DIFFERS]** and must be resolved before freezing.

## 0. Structure
Run three separate experiments, each with its own primary comparison (GPT):
- **E1:** the text repository (expanded IDs).
- **E2:** the snapped lookup.
- **E3:** the unsnapped contextual channel.

No DEV argmax chooses between channels or depths (all three agree). The layer, the coverage definition, the LOO procedure and the statistics are frozen before TEST (Grok, GPT).

## 1. Channels and depths
- An emb baseline is always included (all three).
- Fixed contextual hooks:
  - **[DIFFERS]** Grok: one mid-depth layer. GPT: one fixed mid-depth hook. Claude: two layers, at ~40% and ~60%.
  - Proposed: ~40% and ~60%, with ~40% as the primary arm and ~60% as secondary.
- Read the state **after the full slot value** (Claude). In v5, "not approved" and "approved" share a last token and give identical emb vectors (see checks).
- Basis:
  - PCA vs random of the same size.
  - J-space / sparse NNLS:
    - **[DIFFERS]** Grok: a third arm or a pre-registered omission. Claude: 7B only. GPT: only if a feasibility check passes.
    - Proposed: run a feasibility check first (memory and time on the target box). If it passes, run sparse NNLS on 7B. If not, record the omission in the prereg before TEST.
- Report raw residual (unsnapped) as its own condition, compared with snapped, expanded-ID and prose (all three).
- Give every channel identical source information (GPT).

## 2. Tasks
Include tasks that need context: negation, paraphrase, and definitions of 200+ tokens (Claude). Prose baselines must not leak the literal gold answer. In v5, the place prose used the gold name, which acted as an oracle on 14 Qwen / 30 Smol rows (GPT).

## 3. LOO / transfer
- Remove the held-out entry from the receiver's book, prototypes, dictionaries and adapters, so the receiver has no fallback (all three; GPT adds adapters and prototypes).
- Report answer-held-out, other-held-out and baseline separately (Grok, Claude).
- Use 3+ candidate entities with forced choice. The baseline is **slot-ablated**, not just no-message (Claude, because of the v5 copy/exclusion bias: answer-held-out was 1/220 vs no-message 38 on Qwen).
  - **[DIFFERS]** Grok kept no-message as the comparison. Proposed: report both, with slot-ablated as primary.
- State the transfer rate that counts as success in advance (Claude).

## 4. Gate for the text repository
- Behaviour-based: an entry passes if both models act the same on its expanded definition across fresh cases (all three).
- Set a numeric threshold (GPT; v5 had none).
- Add an external correctness check, not just agreement between the two models (GPT).
- Use 10+ independent planted bad entries covering named corruption types, and report a false-reject rate (Claude, GPT). v5 had 2 designs × 3 depths.

## 5. Logging
- Log coverage on every row (all three).
- Keep separate fields for coverage, selection (which ID was snapped to) and decoding, because the snap silently maps rejected meanings to neighbours (GPT).
- Log abstention (GPT).
- Report both end-to-end and covered-only results (Grok).
- The unknown-ID condition must call the model; in v5 it was only a parser test (GPT).

## 6. Efficiency
- No 64-token padding.
- Measure receiver compute in tokens/FLOPs (Grok, GPT), compared with uncached expansion **and pre-cached KV expansion** (Claude). On the wire, glyph_id and id_text_expanded are both 9 B, so injection can only win on compute.

## 7. Statistics
- Count distinct items for the effective n (v5's t5 had only 8 items).
- Use a ±0.05 equivalence margin (Claude).
- A win requires a frozen statistic with a CI entirely above zero (GPT).
- Run seeds only if they vary something real (Claude).

## 8. Stop rule (Claude)
If the contextual channel does not beat **both** emb and cached expansion at equal accuracy on 7B, retire injection and keep the text repository with the behaviour gate.
