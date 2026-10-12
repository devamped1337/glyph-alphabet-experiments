# E1b Stage B0 report (Kaggle run, 2026-10-12)

Kernel `devamped13/e1b-stage-b0` v1, Tesla T4 (cc 7.5), code at `fb423f0` (tag `prereg-e1b-a6`), code hash `2f8d428e…79a6` OK, config sha256 `c0404fe2…aa09`.
B0 ran from 17:17 to 19:18 AEDT (06:17 to 08:18 UTC). Raw output is in `results/B0/` and the kernel log in `results/B0/kaggle_kernel.log`.

## Outcome: INCOMPLETE. The budget ran out (`BUDGET_EXHAUSTED`). No pair qualified, and no model was disqualified.

Following §2's budget rule, the run **stopped and reports**. N was not shrunk and nothing was dropped. B0 used 7217.6 s (2.005 GPU-h) of its 2.0 GPU-h.

## What happened (failure published openly)
1. **The 4-bit nf4 path failed to load on Kaggle's current image.** The image now runs Python 3.13 / CUDA 12.8. `bitsandbytes==0.44.1` has no `libbitsandbytes_cuda128.so` and fails with `No module named 'triton.ops'`. Under the pre-registered §9 B0 fallback, B0 wrote `backend.json = gguf_cuda` (decided by qwen7b, exit 7) and re-ran B0 on GGUF Q4_K_M via llama.cpp.
2. **In practice llama.cpp ran on the CPU, not the GPU.** The log has no CUDA or offload lines. Latency was about 18–20 s for a **1-token** probe reply (~115 prompt tokens) and about 32 s for an arithmetic item (~50 tokens), which matches CPU speed and not a T4. The likely cause is that the pinned `llama-cpp-python==0.3.2` cu121 wheel has no build for cp313, so a CPU build was used. As a result, the "GGUF **with CUDA**" fallback was not actually realised.
3. At that speed the 2 GPU-h budget covered **qwen7b only**: canaries, F1 in full, and F2 probes on 4 of 6 entries. **OLMo-2 (A6) and Mistral were never loaded.** Throughput, the probe-diagnostic pool and pilot timings were not reached.

## Validity checks
| check | result |
|---|---|
| truncation | none: prompts ≤ ~120 tokens (n_ctx 2048); max generated 69 for arithmetic (cap 192) and 1 for probes (cap 4) |
| answer parsing | 144+96 probes parsed by `letter`, 60/60 arithmetic by `answer_line`; 0 invalid |
| gold labels | 300/300 records match the frozen book (`data/cases_e1b.json`); probe golds are balanced across A–D |
| canaries | qwen7b 20/20 correct (these become the reference) |
| backend | `gguf_cuda` recorded, but it executed on the CPU (see 2); no model loaded in 4-bit nf4 |
| stop markers | `B0/BUDGET_EXHAUSTED`; A's earlier `A/BUDGET_EXHAUSTED` is unchanged (A files byte-identical) |
| validator | `run.sh validate`: **E1b VALIDATION PASSED** (engineering check only), both on Kaggle and locally |

The records that exist are valid measurements. The stage as a whole is **not a valid B0 qualification**. It is incomplete, and it ran on a different compute path from the one pre-registered.

## Qualification numbers (descriptive and partial; bars: probes ≥ 0.90 and arithmetic ≥ 0.80 per family)
| model | family | probes | arithmetic | status |
|---|---|---|---|---|
| qwen7b | F1 | 137/144 = 0.951 | 60/60 = 1.000 | meets both bars (family complete) |
| qwen7b | F2 | 89/96 = 0.927 (4/6 entries) | not run | incomplete |
| qwen7b | F3 / F3L | not run | not run | incomplete |
| olmo7b | all | not run | not run | not loaded |
| mistral7b | all | not run | not run | not loaded |

Invalid-reply rate is 0% (rule A2.12 not triggered). All errors are on higher/lower/yr probes.

## What the prereg says next
- §2 budget rule: **stop and report** (done here). Do not shrink N or drop conditions.
- A re-run or completion can only come from the **3 GPU-h reserve**, under (a) re-run after an infrastructure failure or (c) completing an interrupted checkpointed stage. Results are resumable by key. Partial F1/F2 numbers have now been seen, so (c) is the honest fit rather than (a).
- First, the compute path has to be fixed, which needs a dated amendment (A7). Options: a CUDA build of llama-cpp-python for py3.13, or a bitsandbytes version with CUDA 12.8 support (this would also restore the pre-registered nf4 primary path). `backend.json` currently fixes `gguf_cuda` for all of Stage B ("never mixed"). Whether that decision stands or is reset, given that it was caused by an environment failure, has to be decided in A7 before any re-run.
- B1 must not start: B0 has no `.done` and no qualifying pair.
