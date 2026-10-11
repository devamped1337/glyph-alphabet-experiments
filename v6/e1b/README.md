# E1b: implementation (code only, NOT RUN)

Implements [`PREREG_E1b.md`](PREREG_E1b.md) (tag `prereg-e1b`) **plus Amendments A1 and A2**. **No stage has been run.** The only checks so far are unit tests and a dry run on synthetic data with a fake backend (no model), plus one trivial llama.cpp load check (SmolLM2: tokenize, a single prefix eval to confirm the logits API, and a state save/restore; no generation), plus the A2 CPU smoke test of the HF cache path with a tiny model (`tools/smoke_hf_cpu.py`, SmolLM2-135M, fp32; code testing, not a stage). Code hash: see `CODE_HASH.txt`; `run.sh` refuses to run a stage if the hash doesn't match.

## Layout
| Path | What |
|---|---|
| `config_e1b.json` | frozen settings: seeds, sizes, bars, budgets, models |
| `e1b/cases.py` | **case/probe generator** with frozen seeds; `verify()` asserts disjoint and unique pools, gold recomputation, neighbours changing gold on ≥80% of TEST cases, every plant flipping ≥1 probe, ≥20 probes, unknown IDs failing |
| `e1b/protocol.py` | dictionary with **version/hash check**, delegate expansion, sender 4-way view, receiver prompts (case text identical in every arm), payload vs whole-exchange bytes |
| `e1b/parsing.py` | **frozen parsing rules** (A1.5) |
| `e1b/backends.py` | llama.cpp (CPU, and the CUDA fallback) and HF nf4 backends; prefix and suffix are tokenized separately so cold and warm see identical tokens; manual greedy loop; top-2 logit gap; fail-loud on non-finite logits |
| `e1b/cachediag.py` | **cache diagnostic**: cold1, cold2, coldsplit (A2), cache prefix, warm1, warm2; pairs cold/cold, warm/warm, cold1–warm1, cold2–warm2 (+ coldsplit diagnostics); invalid parses never count as agreement; batch 1 |
| `e1b/projection.py` | **timing projection** from measured per-call time plus setup; C100 / C60 / INSUFFICIENT_BUDGET selector |
| `e1b/stages.py` | per-stage entrypoints A, B0, B0b (leak-template recheck), B1, B2, B3; budget guard; resumable checkpoints |
| `e1b/analysis.py` | paired cluster bootstrap over entries; **mutually exclusive labels**; "met in sample" vs "met at 95% confidence"; payload vs whole-exchange bytes; cost tables (FLOPs on newly processed tokens, batch-1 labels) |
| `e1b/retrieval.py` | order-aware regex number matching (A2), TF-IDF, BM25 (pure Python) and MiniLM selection baselines |
| `e1b/validate.py` + `../checks/validate_v6.py --e1b` | validator (stage-aware since A2; an empty results dir fails unless `--inputs-only`): re-runs the builder assertions, checks pool membership / TEST-only use, cache record consistency, sender-selection logging, unknown-ID 48/48, byte identity, canaries, MANIFEST |
| `run.sh`, `run_e1b.py` | single entrypoint per stage |
| `kaggle/e1b_kaggle.py` | Kaggle notebook code for Stage B (nf4 → 4-bit load test → GGUF CUDA fallback) |
| `tests/` | unit tests + fake-backend dry run of all stages |
| `data/cases_e1b.json` | generator output (deterministic from the seeds, sha256 in `cases_e1b.sha256`) |

## Running (when approved)
- **Tests:** `bash v6/e1b/run.sh test`
- **Stage A, on the box CPU** (llama.cpp, `/workspace/e1venv`; Qwen2.5-3B + SmolLM2-1.7B Q4_K_M):
  `setsid nohup bash v6/e1b/run.sh A > v6/e1b/logs/A.log 2>&1 &`
  - Box: 8 threads, ~15 GB RAM, one model loaded at a time (~2–2.3 GB).
  - Planned 4,380 calls. At E1's measured rates (Qwen 2.25 s/call, Smol 1.31 s/call, probes ~0.5 s) that is **≈1.5 h**; the cap is 2 h.
  - After A1 the projection is re-measured, and the stage stops if it exceeds 2 h.
- **Stage B, on Kaggle** (T4 or P100, 16 GB): one notebook per sub-stage, `E1B_STAGE=B0|B0b|B1|B2|B3`, using `kaggle/e1b_kaggle.py`.
  - Budgets: B0 2 GPU-h (B0b counts against it), B1 3, B2 2, B3 5, reserve 3.
  - Results of earlier sub-stages must be copied into `results/` first.
  - **After B0, write the C60/C100 choice (`results/B0/config_choice.json`) into a dated PREREG amendment BEFORE B1.**
- **Exit codes:**
  - 3: budget exhausted or projection over the cap (stop and report);
  - 4: canary failure;
  - 5: no qualifying pair;
  - 6: insufficient budget;
  - 7: nf4 failed, so the GGUF fallback was chosen (fetch the GGUF files and re-run B0);
  - 8: B0 invalid-reply rate >5%, so a prompt fix plus a dated amendment is required before B1 (A2.12);
  - 2: code hash mismatch.

## Interpretations and gaps (decisions made while implementing; reviewers please check)
1. **Candidate labels carry the load-bearing constants** (compact form). Labels that hid them would make selection chance-level by construction. The sender never sees the entry text.
2. **The 20 multi-step stress prompts** (formerly "hard") are chosen by a fixed rule (multi-step F3s cases: days beyond the threshold, no permit), not by logit gaps, because no model output may be used before the run. Logit gaps are logged.
3. **The cache claim requires zero changed predictions (and zero invalid parses) on the fixed AND the stress set.** Bound: n=100 sampled prompts, ≈3.0% per prompt (rule of three); prompts are clustered within entries, so the bound is optimistic (A2.8).
4. **Placebo** removes all of the entry's constants, a superset of "the answer-determining constants".
5. **Sender selection runs once per entry per sender**, because the message is entry-level. Every case of that entry uses that pick. The B3 prose arm is run fresh rather than reused from B2.
6. **Leak-flag regeneration (A1.5; threshold per probe kind since A2.5):** the reserve templates are a frozen list (fixed prefixes on the same kind). The recheck (stage B0b) runs on the same B0 probe-diagnostic pool before any B1 data. A template still flagged is dropped.
7. **Probe parsing is strict as frozen:** a standalone capital outside A–D (e.g. "I think B") is invalid and counted wrong.
8. **Setup time in the projection** = measured model load time + canary time.
9. **Not implemented:** the optional higher-precision comparison (§4; optional, reserve-funded).
10. **Pins done in A2:** HF revisions, GGUF revisions and GGUF sha256 are in `config_e1b.json`, and GGUFs are verified before loading. **Still to do before Stage B:**
    - memory-test the pinned Kaggle versions (`transformers 4.46.3`, `bitsandbytes 0.44.1`, `llama-cpp-python 0.3.2` cu121).

    These change config, not logic, but they change the code hash, so re-record it.
11. **B0 qualification is not row-resumable.** A re-run after a crash is a permitted reserve use (a).
12. **The B1 manipulation-check model is the pair model with the higher B0 qualification score (A2.13).** FLOPs use approximate parameter counts.
13. **A2 summary** (see PREREG A2): harder messages for ≥1/3 of TEST entries; regex baseline (it solves 70/70 plain messages by number matching alone, so report it next to the sender); per-neighbour-type and per-style selection; "unstated" probes and plausible distractors; per-kind leak rule; gate scored against `honest_gold`; cross-process reproducibility; role-bound `verify()`; neighbours calibrated in B1 (≈2.5× B1 probes); cumulative budget ledger; per-record canaries; resolve by membership + recorded gate decision.
