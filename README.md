# Shared glyph alphabet: cross-model experiments

Compute costs for every run, failed ones included: [COSTS.md](COSTS.md) (no paid compute or paid APIs).

## The concept

*The idea for this project came from the project's human collaborator. The experiments, code and write-ups are in this repository.*

**Why now.** More and more always-on AI agents, built by different companies, talk to each other. Every exchange costs compute: the sender turns its context into long text, and the receiver reads that text back into its own context. One exchange is cheap. Across millions of agents and billions of messages it adds up to real money and real compute.

**The repository, in full.** Each big model gets a small front agent, a *delegate*. Delegates from different labs negotiate, test and maintain a **shared, versioned dictionary**. Each entry in it is an agreed rule for how a piece of communication or context is encoded. A message can then refer to entries ("apply rule F1-03 v2 to this case") instead of spelling everything out. Each delegate delivers new and updated entries to its own big model in a form that model understands, for example plain text or a cached expansion. The big models never share internal states or weights. All coordination happens between the delegates. So the scheme works even across closed labs. Anyone can check whether a model follows an entry correctly, using conformance tests run through public APIs.

**Step two: glyphs (optional, untested).** Once entries are agreed, *open* models could also exchange richer internal representations of an entry, "glyphs": vectors patched into the receiver instead of text. This is still untested in any meaningful form. v5 only tested the embedding layer (the model's input layer), and there it lost to prose. The contextual/J-lens version has not been tried on held-out data.

**Status: what worked, what failed, our mistakes.**

- Worked (small, early): in v4 (tiny models) glyph IDs tied prose on role tasks and beat compact text, at a few bytes per message. Planted bad entries were rejected in v5 (6/6, but from only 2 designs) and in the E1 calibration (12/12).
- Failed: the v5 embedding-layer glyph channel lost to prose; after snapping, the "transfer" was mostly a lookup into the receiver's own dictionary. The v5k 7B Kaggle run crashed; only a post-hoc partial analysis exists. In v6 E1 calibration the text-repository gate **rejected everything**, honest entries included, so it was not frozen.
- Our mistakes:
  - **Embedding-layer selection:** the pre-registered DEV rule picked the embedding layer, so TEST never compared the contextual channel we actually cared about.
  - **LOO artifact:** the v5 leave-one-out score mostly measured cases where the held-out symbol was irrelevant to the answer. When the held-out symbol *was* the answer, accuracy was about 0.
  - **E1 calibration rejected everything:** the gate pair (Qwen2.5-3B + SmolLM2-1.7B) was too weak for a 0.90 bar. The first report also contained wrong claims, since corrected.
  - **E1's sender is given the correct ID:** E1 is only an oracle-ID receiver test. It says nothing about choosing the right entry. Its cached timing is repeat-request caching, and its FLOPs estimate overcounts cached rows.

Details: [RESULTS_v5.md](RESULTS_v5.md) · [RESULTS_v5k_7B_partial.md](RESULTS_v5k_7B_partial.md) · [v6 E1 calibration report](v6/e1/CALIBRATION_REPORT.md) · [PREREG_v6.md](v6/PREREG_v6.md)

---

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
- `v6/checks/`: `validate_v6.py` (mandatory pre-publication gate for v6: `python v6/checks/validate_v6.py --results-dir v6/results`, and a non-zero exit means no publishing) and `v6_checklist.md`.
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
