# E1b Stage A report: stopped by the pre-registered runtime projection (diagnostic only, no claims)

**Run:** 2026-10-12, 09:56–10:20 AEDT, on the box CPU (8 threads, llama.cpp, Q4_K_M GGUFs, sha256-verified against the pins). Detached job with per-row checkpoints. Commit `931b3df`, **code hash `682b727b…`** (PREREG_E1b + A1–A3). No Kaggle, no paid APIs, no Stage B.

## Outcome
Stage A ran **A1** (capability smoke, 120 cases per model). It then **stopped at the pre-registered projection check (§7): projected 4.99 h > the 2 h cap → "stop and report, no shrinking"** (marker `results/A/PROJECTION_EXCEEDS_BUDGET`, exit 3). Nothing after A1 ran: A2 probes, A3 prompt ablation, A4 manipulation check, A5 cache, A6 cost.

- **Measured per-call time:** Qwen2.5-3B **7.68 s**, SmolLM2-1.7B **4.08 s**. E1 measured 2.25 s and 1.31 s, but E1 replies were much shorter. With `max_new_tokens = 192` and no 3-line cap (the A1 prompt fix), mean generation is 99 and 76 tokens.
- **The stop is robust, not a projection artefact.** The remaining arithmetic calls alone are 120 (A3) + 600 (A5: 5 runs × 120 prompts) + 480 (A6) per model. That is ≈3.9 h before any probes, on top of the 0.4 h already used.
- **Consequences under the frozen plan:**
  - **The A exit rule was not evaluated** (no A2 probes), so there is **no "go to B" from Stage A**.
  - **The A5 cache diagnostic did not run**, so no CPU cache claim is possible.
  - Continuing would need a dated amendment: either a larger Stage A budget or a smaller pre-registered workload. That is the user's call; per §2, budgets are not raised silently.

## A1 capability smoke (direct text, 40 cases per family per model)
| Family | Qwen2.5-3B | SmolLM2-1.7B |
|---|---|---|
| F1 negation | **40/40** (1.00) | 37/40 (0.93) |
| F2 roles | 29/40 (0.73) | 20/40 (0.50) |
| F3s short schedule | 33/40 (0.83) | 13/40 (0.33) |
| **All** | 102/120 (0.85) | 70/120 (0.58) |

Against the §7 capability floor of 0.70 (Grok r1), Qwen clears it on every family. Smol fails it on F2 and F3s. This is reported only; there are no repository claims in Stage A.

## Was the run real? Checks done before reporting
- **No truncated prompts:** the longest prompt is 158 tokens (n_ctx 2048).
- **Replies hitting the 192-token limit:** 3 (Qwen; 1 correct, 2 wrong), 0 for Smol.
- **Parser:** 232/240 replies parsed from the `Answer:` line, 8 by the last-integer fallback. No mismatch between the parsed prediction and the final `Answer:` value.
  - **Parser note:** one Smol reply wrote `Answer: 12 * 3 = 36 credits`. The frozen rule (A1.5) takes the first integer after `Answer:`, which is 12, so it was scored wrong even though the final number is right. This is the frozen rule working as written, not a bug; it affects 1/240.
- **Gold:** all 240 golds were recomputed from the entry text and question text alone (role-bound parser, A2.18). 0 mismatches.
- **Validator** (`validate_v6.py --e1b`): PASSED for Stage A, status `incomplete:PROJECTION_EXCEEDS_BUDGET`.
  - **Code bug fixed after the run:** the validator did not list Stage A's own stop marker `PROJECTION_EXCEEDS_BUDGET` as an explicit stop, so it would have called the stage "broken". The marker was added, with a regression test.
  - The fix touches only `e1b/validate.py`, not any code used by the run. The code hash is re-recorded (see `CODE_HASH.txt`); the run itself used `682b727b`.

## Files
`results/A/A1_qwen3b.jsonl`, `A1_smol17.jsonl` (per-case rows with raw replies, parse path, tokens, latency, logit gaps, prompt sha), `prompts_*.jsonl` (rendered prompts), `stage_log.jsonl` (environment, loads, system-turn hashes, projection), `PROJECTION_EXCEEDS_BUDGET`, `logs/A.log`.
