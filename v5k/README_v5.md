# Glyph experiment v5: two machines, two larger models

Sender/receiver pair: **SmolLM2-1.7B** (box, rev effd688a) and **Qwen2.5-3B** (laptop/WSL, rev 3aab1f19). Both run in float32, one model per process.
Each machine extracts its own states to files. Files move with CopyToBox/CopyFromBox. Negotiation and adapter fitting run on the box,
and each receiver's tests run on its own machine. Every output is listed with its sha256 in `results/MANIFEST_<host>.json`, and `load()` refuses
any file whose hash is not in a manifest. Every output also records the code commit (`COMMIT` is filled in by `git archive`) and the sha256 of the code.

Pre-registered rules: `PREREG.md`.

| file | role |
|---|---|
| spec5.py | models/revisions, vocabulary (incl. confusable places + clue phrases), splits, 64-token prompts, scoring (maths exact/magnitude/sign), string-match baseline |
| common5.py | pinned loading, batched 64-token forwards, per-row patching at `emb` or a block output, J-gram (random-cotangent VJPs), RAM guard, manifests, commit pinning |
| det5.py | (0) determinism check: a fixed saved state injected on each machine; repeat, reload and cross-machine logits compared to a tolerance |
| extract5.py | book-format and sender-reading slot states at {emb, 0.25, 0.33}, plus the top-64 J-subspace per layer |
| negotiate5.py | books for depth x {pca, jlens, random} x seeds {0,1,2}; gate; LOO books (8 people + 15 places); planted Zed/Noise; null adapters; selection test; per-receiver deliveries |
| run5.py | receiver tests: text (none/prose/compact/bag), id_text_expanded / id_text_raw (same ID bytes), glyph_id per basis x seed, glyph_emb, raw, nulls, slot swap, operand change, same-norm shuffle, receiver word state, LOO |
| prereg5.py | applies rule A (prose >= 0.9 task gate) and rule B (depth) to dev only, writes frozen5.json |
| analyze5.py | cluster-bootstrap tables, seeds per-seed and pooled |
| box.sh / laptop.sh | staged drivers |
| smoke_fake_partner.py | smoke test only: a rotated copy of the Smol states stands in for Qwen |

Order: box 1 -> laptop 1 -> box 2 -> laptop 2 -> box 3 -> laptop 3 -> box 4.
