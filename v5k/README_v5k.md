# Glyph v5k: the v5 pipeline on a Kaggle GPU at 7B scale

Same experiment as `v5/` (unchanged on `main`), with these changes:

* Models (spec5.py): **Qwen/Qwen2.5-7B** @ `d149729398750b98c0af14eb82c78cfe92750796` and **allenai/OLMo-2-1124-7B** @ `7df9a82518afdecae4e8c026b27adccc8c1f0032`.
  Both are Apache-2.0 and ungated (checked 2026-10-11 on the HF API). `GLYPH_MODELS` (JSON) overrides them, for smoke tests only.
* common5.py: `GLYPH_DEVICE` (default cuda if available) and `GLYPH_DTYPE` (default float16 on cuda, float32 on cpu). On cuda the
  weights are split across GPUs with `device_map="auto"`, because a 7B model in fp16 (~15 GB) does not fit on one 16 GB card.
  The forward pass runs in fp16. Every recorded state is cast to fp32 on the CPU, and all adapters, books, decoders and analysis stay fp32 on the CPU.
  Patched states are cast to the activation dtype only at injection. Non-finite logits or states raise `FloatingPointError`, so an fp16 overflow can never pass silently.
  States are stored in fp16 as in v5. The J-gram is accumulated in fp64 on the CPU.
* det5.py: the fixed directions are 8192-dimensional. Each one is truncated to the model width d and renormalised. Kaggle is one host,
  so `compare` reports the within-machine checks (repeat, reload, batch4 vs batch1) and records the cross-machine part as "only one machine".
* jgram5.py: split-half (even/odd batch) subspace overlap. The driver uses JPROMPTS=32 and JPROBES=8 (v5: 8 and 4).
* jlens_compare5k.py (new): per layer, J split-half stability, overlap of the J subspace with the PCA subspace against chance (KP/d),
  spectrum concentration, and test glyph_id accuracy by basis (pca / jlens / random).
* run_kaggle5k.py (new): a resumable stage driver. Each step runs in its own process (one model in memory) and leaves a marker in `.stages/`.
  It also has a session-budget guard.
* package5k.py (new): writes MANIFEST.txt (sha256 + bytes for every file) and zips it to glyph_v5k_results.zip (+ .sha256).
* smoke/mk_tiny_olmo.py: a random-weight 8-layer OLMo-2 with the real OLMo-2 tokenizer, used for the CPU smoke test.

Pre-registration (PREREG.md, prereg5.py) is unchanged: prose gate 0.9 on dev, depth frozen on dev, then test.
The notebook is `kaggle/glyph_7b_kaggle.ipynb`.
