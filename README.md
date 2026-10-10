# Shared glyph alphabet: cross-model experiments

Small CPU-only experiments asking whether different open LLMs can share a negotiated **model-neutral codebook over early-layer states**
(the "glyph book", inspired by Anthropic's Jacobian lens / J-lens), and whether handing off glyphs can match or beat text.
The book is a set of verified entries (task, slot, symbol). Each model reaches the shared canonical space through its own linear adapter (PCA + generalized Procrustes).
A message is either a short list of entry IDs or the canonical vectors, patched into the receiver at a placeholder position.

**v4 headline (Qwen2.5-0.5B, SmolLM2-360M, Pythia-410m; unseen role-swapped messages):** on roles the glyph **ties prose** (glyph 0.94-0.98 vs prose 0.92-1.00)
and **beats compact structured text** (0.65-0.89), at 4 bytes as an ID against 30 bytes for compact text and ~44 bytes for prose.
Slot swaps flip the answer as predicted. On negation it ties or loses. Uncertainty, event order and signed maths were not carried by any channel, *text included*,
so they show nothing either way. The glyph does no better than the receiver's own word state at the same layer. Its value is cheap, verified addressing, not extra meaning.
See `RESULTS_v4.md` for CIs and caveats.

- `PLAN.md`: original experiment plan
- `RESULTS.md`: v1 (imposed anchor-word glyphs)
- `RESULTS_v2.md`: v2 (negotiated 183-concept dictionary)
- `RESULTS_v3.md` / `v3/`: v3 (closed arithmetic "maths book" with slots)
- `RESULTS_v4.md` / `v4/`: v4 (three-party book, keeper/delegates, frozen blocks, composition tests, ID vs vector delivery, ablations)
- `v5/`: v5 code and pre-registration (SmolLM2-1.7B on one machine, Qwen2.5-3B on another; determinism check, ID-as-text control, LOO + planted entries, embedding vs layer patching, null adapters, J-subspace vs PCA vs random, confusable-entry selection). Not run yet.
- `results/`: raw JSON outputs; `logs/`: run logs

Not included: model weights, fitted lens checkpoints (`*.pt`), venv. Lens code: https://github.com/anthropics/jacobian-lens (clone into `jacobian-lens/`).
The J-lens is an inspiration and, in v1-v3, a basis for reading states. The codebook itself is plain linear algebra over early-layer residual states and does not depend on the lens.

All numbers are from these runs: tiny models, small n. Read them as direction, not effect size.

## Related work

- **Soft prompts and prompt tuning:** Lester et al., "The Power of Scale for Parameter-Efficient Prompt Tuning" (2021); Li & Liang, "Prefix-Tuning" (2021). Learned continuous vectors stand in for text tokens. Here the vectors are not trained by gradient descent; they are averaged, aligned states with a verification gate.
- **Gist tokens / context compression:** Mu et al., "Learning to Compress Prompts with Gist Tokens" (2023). These compress a prompt into a few activations inside one model. The glyph book instead addresses a small fixed vocabulary across models.
- **Activation passing between models:** Ramesh & Li, "Communicating Activations Between Language Model Agents" (2025). One model's hidden states are injected into another model in place of natural-language messages. v5's raw unsnapped transfer and null adapters are the closest analogue. The book adds discrete, checkable IDs on top.
- **Relative representations:** Moschella et al., "Relative Representations Enable Zero-Shot Latent Space Communication" (ICLR 2023). This aligns latent spaces through similarities to shared anchors. The book's shared entries play the anchor role, and v5's leave-one-entry-out test asks whether an entry absent from the alignment still transfers.
- **Jacobian lens:** "Verbalizable Representations Form a Global Workspace in Language Models" (Anthropic, 2026) and https://github.com/anthropics/jacobian-lens. v5 compares a J-lens-inspired subspace with raw PCA and a random subspace as the codebook basis.
