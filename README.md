# Shared glyph alphabet: cross-model experiments

Small CPU-only experiments testing whether two different open LLMs (Qwen2.5-0.5B, SmolLM2-360M) can share a negotiated "glyph" dictionary built on Anthropic's Jacobian lens (J-space), and whether glyph handoff can match or beat text.

- `PLAN.md`: original experiment plan
- `RESULTS.md`: v1 (imposed anchor-word glyphs)
- `RESULTS_v2.md`: v2 (negotiated 183-concept dictionary)
- `RESULTS_v3.md` / `v3/`: v3 (closed arithmetic "maths book" with slots)
- `results/`: raw JSON outputs; `logs/`: run logs
- v4 (third model, keeper/delegates, frozen blocks, composition tests) will be added when it finishes.

Not included: model weights, fitted lens checkpoints (`*.pt`), venv. Lens code: https://github.com/anthropics/jacobian-lens (clone into `jacobian-lens/`).

All numbers are from these runs; tiny models, small n. Read as direction, not effect size.
