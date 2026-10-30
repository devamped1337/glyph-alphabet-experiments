# Kaggle 7B failed-run archive (release `kaggle-7b-fails-archive`)

Raw Kaggle outputs from the v5k 7B run (Qwen2.5-7B × OLMo-2-1124-7B, kernel
`devamped13/notebook83b9a1ff44`). They are too large for git, so they live as
release assets: https://github.com/devamped1337/glyph-alphabet-experiments/releases/tag/kaggle-7b-fails-archive
Analysis and failure details: `RESULTS_v5k_7B_partial.md`.

| asset | what it is |
|---|---|
| `glyph-kaggle-out_v3_fail.tar` | Kernel version 3 (run code `bf8d79f`). Every pipeline stage finished, then the final analyze step failed (`TypeError` in `v5k/analyze5.py`). Contains the states/deliveries/det `.pt` files whose hashes are in `v5k/results_7b_partial/SHA256SUMS_v3_kaggle.txt`, plus the kernel log. |
| `glyph-kaggle-out_v2_error.tar` | Kernel version 2, the earlier errored run. It died in the OLMo-7B TEST stage with `non-finite logits in float16 forward (olmo7)` (fp16 overflow on a T4). |
| `glyph-kaggle-misc.tar` | The rest of the local `glyph-kaggle` working folder: kernel scripts and metadata for the E1b/E1c/E1d kernels, `e1b_*_out` outputs (manifests, ledgers, `validate_out.txt`), `smoke/` logs and `glyph_v5k_results.zip`, the notebook and helper scripts. Excludes the Hugging Face cache `hf/` and the tiny-OLMo2 `model.safetensors`. |

Files were scanned for secrets before upload; none found. Verify with `sha256sum -c SHA256SUMS`.
