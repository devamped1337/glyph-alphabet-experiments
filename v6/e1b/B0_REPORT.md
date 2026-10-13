# E1b Stage B0 report

## Run 2 (A7, kernel v2, commit `2ccd289`, 2026-10-12, Tesla T4): **valid, complete. NO QUALIFYING PAIR. Stage B stops.**

Allocation: reserve use (c), 4968.9 s = **1.38 GPU-h** of the 3 GPU-h reserve. No budget exhaustion. Markers: `.done` and `NO_QUALIFYING_PAIR` (`["qwen7b"]`), exit 5. Raw output: `results/B0/`; kernel log: `results/B0/kaggle_kernel.log`.

### Validity
| check | result |
|---|---|
| GPU preflight | **PASSED** for both models: hf-nf4, Tesla T4 (cc 7.5), all tensors on cuda, Linear4bit layers 196 (qwen) / 224 (olmo). No `GPU_PREFLIGHT_FAIL` |
| backend | `backend.json = nf4` (decided by qwen7b); both models nf4, not mixed |
| truncation | prompts ≤ 298 tokens (n_ctx 2048). Qwen max gen 120/192. **OLMo: 2/180 arithmetic replies hit the 192-token cap** (parsed via `last_integer`); this does not change any decision (see below) |
| parsing | probes 432/432 `letter` per model; arithmetic `answer_line` 180/180 (qwen), 178/180 (olmo); invalid-reply rate 0% for both (A2.12 not triggered) |
| gold labels | 612/612 per model match the frozen book; no duplicate keys |
| canaries | 20/20 for both (now the reference, `canaries_ref.json`) |
| validator | **E1b VALIDATION PASSED** on Kaggle and locally |

### Qualification (bars: probes ≥ 0.90 AND direct-text arithmetic ≥ 0.80 per family; a model qualifies if ≥ 1 core family (F1, F2) passes)
| model | F1 probe / arith | F2 probe / arith | F3L probe / arith (not core) | result |
|---|---|---|---|---|
| qwen7b | 0.924 / 1.000 ✔ | 0.924 / 1.000 ✔ | 0.965 / 0.800 ✔ | **QUALIFIED** (all families; score 3.847) |
| olmo7b | **0.840** / 1.000 ✘ | **0.736** / 0.883 ✘ | 0.882 / **0.483** ✘ | **FAILED** (no family passes) |

**Pair: none.** Only one lab qualified. Under A7 §7 there is no further substitute (Llama is gated per A6, Mistral is forbidden per A7). §2/§3 then apply: **no qualifying two-lab pair → stop Stage B and report.**

Where OLMo fails (probes correct per kind, F1 / F2):
- higher 24/30 / 19/30;
- lower 26/30 / 18/30;
- **unstated 11/24 / 9/24**;
- mem, non, xr, yr ≥ 30/30.

Qwen: unstated 24/24 in every family.

**Sensitivity (descriptive only, not the frozen rule):**
- Without the A5 `*-unstated` probes, OLMo F1 probes would be 110/120 = 0.917 (passing), and F2 would be 97/120 = 0.808 (still failing).
- A5 excluded `unstated` from the **leak rule only**, not from qualification. The frozen decision therefore stands: OLMo fails.
- Any change here would be a new amendment made after seeing the data, so it would have to be reported as post hoc.

The two truncated OLMo replies cannot change anything. Even if both were correct, F3L arithmetic would be at most 31/60, and F1/F2 already fail on probes.

### Probe diagnostics (no entry text; reached and computed descriptively, since leak flags formally apply only to a qualifying pair)
- No-text accuracy: qwen 0.233, olmo 0.355 (chance 0.25).
- Pooled leak rule: **F3L-waive is a kind-level leak** (baseline 0.46 > 0.40), so all 4 waive templates are flagged.
- higher/lower kinds have no-text baselines of 0.21–0.39 (under 0.40). No other templates are flagged.
- Abstention diagnostic: see `probediag_*.jsonl`.

### Pilot timings (reached; s per item, batched)
| model | receiver | receiver warm | probe | sender | setup s |
|---|---|---|---|---|---|
| qwen7b | 2.81 | 4.29 | 0.365 | 0.477 | 247 |
| olmo7b | 4.76 | 8.55 | 0.379 | 0.485 | 256 |

No C60/C100 choice was made (no pair).

### GPU-hours used in B0
| run | GPU-h |
|---|---|
| Run 1 (B0 allocation) | 2.005 (GGUF on CPU, see below) |
| Run 2 (reserve) | 1.380 |
| **Total** | **3.385** |

Reserve remaining: 1.62 GPU-h.

### What comes next (prereg)
- **Stage B stops here.** B1–B3 do not run (B1 needs `config_choice.json` and a pair).
- E1b reports **Stage A plus B0: no qualifying two-lab 7B pair under free-access constraints**.
- Any attempt with a different second model would be a new, separately pre-registered experiment or amendment. It would have to state that these B0 results were seen.

---

## Run 1 (kernel v1, `fb423f0`): archived, superseded by A7
Kernel `devamped13/e1b-stage-b0` v1, Tesla T4 (cc 7.5), code at `fb423f0` (tag `prereg-e1b-a6`), code hash `2f8d428e…79a6` OK, config sha256 `c0404fe2…aa09`.
B0 ran from 17:17 to 19:18 AEDT (06:17 to 08:18 UTC). Raw output is in `results/B0_run1_gguf_cpu/` and the kernel log in `results/B0_run1_gguf_cpu/kaggle_kernel.log`.

### Outcome: INCOMPLETE. The budget ran out (`BUDGET_EXHAUSTED`). No pair qualified, and no model was disqualified.

Following §2's budget rule, the run **stopped and reports**. N was not shrunk and nothing was dropped. B0 used 7217.6 s (2.005 GPU-h) of its 2.0 GPU-h.

### What happened (failure published openly)
1. **The 4-bit nf4 path failed to load on Kaggle's current image.** The image now runs Python 3.13 / CUDA 12.8. `bitsandbytes==0.44.1` has no `libbitsandbytes_cuda128.so` and fails with `No module named 'triton.ops'`. Under the pre-registered §9 B0 fallback, B0 wrote `backend.json = gguf_cuda` (decided by qwen7b, exit 7) and re-ran B0 on GGUF Q4_K_M via llama.cpp.
2. **In practice llama.cpp ran on the CPU, not the GPU.** The log has no CUDA or offload lines. Latency was about 18–20 s for a **1-token** probe reply (~115 prompt tokens) and about 32 s for an arithmetic item (~50 tokens), which matches CPU speed and not a T4. The likely cause is that the pinned `llama-cpp-python==0.3.2` cu121 wheel has no build for cp313, so a CPU build was used. As a result, the "GGUF **with CUDA**" fallback was not actually realised.
3. At that speed the 2 GPU-h budget covered **qwen7b only**: canaries, F1 in full, and F2 probes on 4 of 6 entries. **OLMo-2 (A6) and Mistral were never loaded.** Throughput, the probe-diagnostic pool and pilot timings were not reached.

### Validity checks
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

### Qualification numbers (descriptive and partial; bars: probes ≥ 0.90 and arithmetic ≥ 0.80 per family)
| model | family | probes | arithmetic | status |
|---|---|---|---|---|
| qwen7b | F1 | 137/144 = 0.951 | 60/60 = 1.000 | meets both bars (family complete) |
| qwen7b | F2 | 89/96 = 0.927 (4/6 entries) | not run | incomplete |
| qwen7b | F3 / F3L | not run | not run | incomplete |
| olmo7b | all | not run | not run | not loaded |
| mistral7b | all | not run | not run | not loaded |

Invalid-reply rate is 0% (rule A2.12 not triggered). All errors are on higher/lower/yr probes.

### What the prereg said next (run 1; resolved by A7)
- §2 budget rule: **stop and report** (done here). Do not shrink N or drop conditions.
- A re-run or completion can only come from the **3 GPU-h reserve**, under (a) re-run after an infrastructure failure or (c) completing an interrupted checkpointed stage. Results are resumable by key. Partial F1/F2 numbers have now been seen, so (c) is the honest fit rather than (a).
- First, the compute path has to be fixed, which needs a dated amendment (A7). Options: a CUDA build of llama-cpp-python for py3.13, or a bitsandbytes version with CUDA 12.8 support (this would also restore the pre-registered nf4 primary path). `backend.json` currently fixes `gguf_cuda` for all of Stage B ("never mixed"). Whether that decision stands or is reset, given that it was caused by an environment failure, has to be decided in A7 before any re-run.
- B1 must not start: B0 has no `.done` and no qualifying pair.

---

## Addendum (2026-10-13): POST-HOC DIAGNOSTIC, invalid replies and letter choice on probes (requested by the Claude B0 review)

This addendum is computed from the run-2 records already committed (`7873596`). Nothing was re-run, and it **does not change the B0 decision**.

**Invalid-reply rate by probe kind** (n / invalid / correct):

| kind | qwen7b | olmo7b |
|---|---|---|
| mem | 30 / 0 / 30 | 30 / 0 / 30 |
| non | 30 / 0 / 30 | 30 / 0 / 30 |
| higher | 60 / 0 / 53 | 60 / 0 / 43 |
| lower | 60 / 0 / 46 | 60 / 0 / 44 |
| xr | 30 / 0 / 29 | 30 / 0 / 30 |
| yr | 30 / 0 / 30 | 30 / 0 / 30 |
| a | 24 / 0 / 24 | 24 / 0 / 23 |
| c | 24 / 0 / 24 | 24 / 0 / 22 |
| s | 24 / 0 / 19 | 24 / 0 / 24 |
| t | 24 / 0 / 24 | 24 / 0 / 23 |
| waive | 24 / 0 / 24 | 24 / 0 / 24 |
| **unstated** | **72 / 0 / 72** | **72 / 0 / 31** |

- **Invalid replies are 0/432 for both models in every kind.** Every reply was a single valid letter token (A–D).
- The frozen A2.12 rule (invalid > 5% → `PROMPT_FIX_REQUIRED`) **did not apply** for either model; the arithmetic invalid rate was also 0%.

**OLMo on the 72 `unstated` probes** (gold option = "Not stated by the rule"):
- Its first token is always a letter: D 28, C 18, B 13, A 13. The gold letters are spread A 20, B 15, C 19, D 18.
- **All 41 of its wrong answers chose a numeric option. It never chose a non-numeric wrong option.** Wrong letters: D 15, C 11, B 8, A 7, so there is a mild lean to D but no single-position habit.
- 30 of the 41 chosen numbers appear elsewhere in the rule text (one of the rule's other constants). The other 11 do not.
- By family, wrong answers split F1 13, F2 15, F3L 13.
- Mean top-2 logit gap on the wrong answers is 1.23, so the model chose them with low confidence.

**Interpretation:** this is **not a formatting failure**. OLMo answers in the correct format and fills in a plausible number (often a constant from the same rule) instead of abstaining. The Stage A small models showed the same gap-filling pattern; Qwen-7B shows none of it (72/72).

This supports the review's reading that the 3B abstention failure is partly a size or model effect. The OLMo failure also does not depend on `unstated`: its F2 probes are 0.808 without them.
