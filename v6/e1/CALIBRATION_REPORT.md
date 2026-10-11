# v6 E1 — Calibration report: the behaviour gate did NOT separate

Written 2026-10-11 (AEDT), after calibration finished and while the E1 TEST/main stages were still running (that run was not stopped, restarted or changed). Source: `results/gate_frozen.json`, `results/predictions_calib_{qwen3b,smol17}.jsonl`, `data/cases.json`, `e1.py`. Calibration only; this is not the E1 RESULTS write-up.

## Headline (failure stated plainly)

At the pre-registered 0.90 threshold the gate **rejected every entry**: honest-entry acceptance **0.00** (0/24), planted-entry rejection **1.00** (12/12). Rejecting everything is not separation, so `separates=false` and `gate_frozen=false`. The best threshold on the grid (0.50, for information only and **not** adopted) was not pre-registered and cannot be used.

## Rule (weakest link)

An entry passes only if **each** gate model scores ≥0.90 against gold **and** the two models agree with each other on ≥0.90 of cases. The entry's gate score is `min(acc_qwen, acc_smol, agreement)`. So the weaker model sets the score. SmolLM2-1.7B never got above 0.61 on any honest entry, which by itself rules out any honest entry passing, even on F1 where Qwen scored 0.94–1.00. Agreement is capped by the weaker model too: two models can't agree on ≥90% of cases if one of them is wrong on ~50% of them.

## Per-family (honest entries, N=100 cases per entry per model)

| Family | Entries | Qwen2.5-3B acc | SmolLM2-1.7B acc | Mean agreement | Max gate score | Pass at 0.90 |
|---|---|---|---|---|---|---|
| F1 | 8 | 0.94–1.00 (mean 0.99) | 0.28–0.58 (mean 0.40) | 0.40 | 0.58 | 0 |
| F2 | 8 | 0.56–0.89 (mean 0.74) | 0.38–0.61 (mean 0.47) | 0.38 | 0.49 | 0 |
| F3 | 8 | 0.02–0.38 (mean 0.19) | 0.03–0.16 (mean 0.11) | 0.14 | 0.16 | 0 |

## Per-entry (honest)

| Entry | Qwen acc | Smol acc | Agreement | Gate score (min) | Pass |
|---|---|---|---|---|---|
| F1-00 | 1.00 | 0.58 | 0.58 | 0.58 | no |
| F1-01 | 0.94 | 0.50 | 0.51 | 0.50 | no |
| F1-02 | 1.00 | 0.28 | 0.28 | 0.28 | no |
| F1-03 | 0.98 | 0.33 | 0.33 | 0.33 | no |
| F1-04 | 1.00 | 0.33 | 0.33 | 0.33 | no |
| F1-05 | 0.97 | 0.47 | 0.48 | 0.47 | no |
| F1-06 | 1.00 | 0.38 | 0.38 | 0.38 | no |
| F1-07 | 1.00 | 0.34 | 0.34 | 0.34 | no |
| F2-00 | 0.85 | 0.50 | 0.43 | 0.43 | no |
| F2-01 | 0.74 | 0.39 | 0.40 | 0.39 | no |
| F2-02 | 0.70 | 0.38 | 0.37 | 0.37 | no |
| F2-03 | 0.65 | 0.50 | 0.23 | 0.23 | no |
| F2-04 | 0.56 | 0.61 | 0.36 | 0.36 | no |
| F2-05 | 0.82 | 0.43 | 0.34 | 0.34 | no |
| F2-06 | 0.71 | 0.49 | 0.58 | 0.49 | no |
| F2-07 | 0.89 | 0.43 | 0.35 | 0.35 | no |
| F3-00 | 0.02 | 0.10 | 0.02 | 0.02 | no |
| F3-01 | 0.38 | 0.10 | 0.24 | 0.10 | no |
| F3-02 | 0.36 | 0.16 | 0.09 | 0.09 | no |
| F3-03 | 0.37 | 0.16 | 0.33 | 0.16 | no |
| F3-04 | 0.12 | 0.12 | 0.14 | 0.12 | no |
| F3-05 | 0.08 | 0.03 | 0.05 | 0.03 | no |
| F3-06 | 0.13 | 0.10 | 0.09 | 0.09 | no |
| F3-07 | 0.07 | 0.09 | 0.15 | 0.07 | no |

## Planted entries (calibration corruptions)

Accuracy here is measured against the gold of the **honest** entry, so a high score means the model answered as if the corruption were absent.

| Planted entry | Corruption | Qwen acc vs honest gold | Smol acc | Agreement | Gate score | Rejected at 0.90 |
|---|---|---|---|---|---|---|
| F1-C00 | deleted_negation | 0.76 **(high)** | 0.13 | 0.11 | 0.11 | yes |
| F2-C01 | deleted_negation | 0.69 **(high)** | 0.46 | 0.50 | 0.46 | yes |
| F3-C02 | deleted_negation | 0.09 | 0.12 | 0.08 | 0.08 | yes |
| F1-C03 | deleted_negation | 0.73 **(high)** | 0.34 | 0.26 | 0.26 | yes |
| F2-C04 | mismatched_definition | 0.17 | 0.20 | 0.55 | 0.17 | yes |
| F3-C05 | mismatched_definition | 0.00 | 0.08 | 0.03 | 0.00 | yes |
| F1-C06 | mismatched_definition | 0.15 | 0.29 | 0.14 | 0.14 | yes |
| F2-C07 | mismatched_definition | 0.00 | 0.00 | 0.49 | 0.00 | yes |
| F3-C08 | changed_constant | 0.19 | 0.00 | 0.01 | 0.00 | yes |
| F1-C09 | changed_constant | 0.56 | 0.17 | 0.34 | 0.17 | yes |
| F2-C10 | changed_constant | 0.43 | 0.07 | 0.44 | 0.07 | yes |
| F3-C11 | changed_constant | 0.07 | 0.04 | 0.13 | 0.04 | yes |

**Note:** on Qwen, three `deleted_negation` entries scored high (F1-C00 0.76, F1-C03 0.73, F2-C01 0.69). Qwen mostly gave the honest answer even though the entry had lost its negation. In other words, it ignored the corruption, probably by falling back on world-knowledge or on the case wording, instead of following the corrupted text. All 12 planted entries were rejected only because SmolLM2 and/or the agreement term were low. With a stronger pair that clears 0.90 on honest entries, `deleted_negation` entries could pass. So "planted rejection = 1.00" here says nothing about whether the gate catches corruptions.

## F3 investigation (long definitions, ~208 words / ~310 prompt tokens): genuine difficulty, not a pipeline bug

Checked read-only:

1. **Gold answers are correct.** I took the four constants (daily rate a, tier threshold t, later rate c, fee s), the stay length and permit status from every F3 calibration prompt text and recomputed `a·min(d,t) + c·max(0,d−t) + (permit ? 0 : s)` independently. Result: **0 mismatches in 1600 rows** (800 per model). This matches `e1.py` line 117.
2. **No truncation of the reasoning.** No F3 row came close to the 160-token cap (`gen_tokens` ≤ ~25; 0 rows ≥158). Replies are short single-line arithmetic.
3. **Prompt not truncated.** F3 prompts are 307–326 tokens against `n_ctx=2048`.
4. **Parsing.** Qwen: 626 rows parsed via the `Answer:` line and 174 via the fallback; accuracy is equally poor on both paths (118/626 vs 35/174). SmolLM2 **never** wrote an `Answer:` line on F3 (800/800 fallback, e.g. "The total charge in credits is 24 credits."). But the fallback (last integer) pulled out the number it intended correctly in the samples I checked. So a missing Answer line costs format compliance, not accuracy. It does not explain the low scores.
5. **The cases are solvable.** Each case is a deterministic two-step tier sum plus a conditional fee. All constants are in the prompt.

**What actually goes wrong** (Qwen, 800 honest F3 rows): correct 153 (143 with a permit, only **10** without); **omitted the service fee** when it applied 141; other arithmetic or tier errors ~500 (e.g. the tier rule applied to days that don't exceed the threshold, or wrong multipliers). The fee is stated through a negation ("Holders of a X permit are **not** charged the s-credit service fee; everyone else pays it"), and it sits among filler text. The models almost never add it. That is the long-definition/negation difficulty the family is meant to probe. It is a real capability limit of 1.7B–3B Q4 models, not a bug.

Examples (Qwen2.5-3B, honest entries):

| Entry | Case | Gold | Raw reply | Parsed | Failure |
|---|---|---|---|---|---|
| F3-00 | 3 days, no permit; 8/day first 3, 2 after, fee 14 | 38 | `3 * 8 + 1 * 2 = 26` | 26 (fallback) | invented an extra tier day; omitted fee |
| F3-01 | 4 days, no permit; 3/day first 5, 6 after, fee 11 | 23 | `4 * 3 + 3 * 6 = 30` / `Answer: 30` | 30 | applied later tier below threshold; omitted fee |
| F3-04 | 2 days, permit; 9/day first 6, 4 after, fee 12 | 18 | `9 (for the first 2 days) - 0 (Ember permit holder) = 9` | 9 (fallback) | didn't multiply by days |
| F3-06 | 5 days, permit; 6/day first 4, 3 after, fee 16 | 27 | `6 + 3*2 = 12` / `Answer: 12` | 12 | wrong multipliers |
| F3-00 (SmolLM2) | as above | 38 | `The total charge in credits is 24 credits.` | 24 (fallback) | no Answer line; omitted fee (24 = 3×8) |

**One design weakness to record (not a bug, and not changed in this run):** the user turn ends with a trailing `Answer:` (`e1.py` line 181), even though the system prompt asks for short worked reasoning. That cue probably pushes the models to answer immediately (replies of ~15–20 tokens) and suppresses the multi-step working F3 needs. **Proposed for a later, separately amended rerun:** drop the trailing `Answer:` from the user turn, ask explicitly for one line per step (base days, extra days, fee), give F3 a larger token budget (e.g. 256), and score the format separately (log the share of rows without an Answer line). These changes must be pre-registered as an amendment before the rerun. The current run stays as frozen.

## What this means under the frozen PREREG

- PREREG §4: "If nothing separates honest from planted entries in calibration, the gate is not frozen and this is reported." This document is that report. **The gate is not frozen and is reported as unable to separate** with Qwen2.5-3B + SmolLM2-1.7B at 0.90. The gate's TEST-stage numbers (unseen corruption types) are descriptive only. They are not a validation of a frozen gate.
- The grid-best threshold (0.50) is not adopted. Adopting it after seeing results would break the prereg.
- **The E1 main comparison still counts.** It (id_expanded vs prose / compact / id_raw / placebo_prose, plus the efficiency comparison against id_expanded_cached) does not depend on the gate and goes ahead as pre-registered. It runs in the same uninterrupted run.
- Before E1 RESULTS are published, the mandatory validator (`v6/checks/validate_v6.py`) must still be run on the finished results directory (amendment 2026-10-11).

## Recommendation

Pre-register separately (new dated amendment, before any of its results are seen) a gate rerun with a **stronger gate pair, e.g. two ~7B instruct models** (such as Qwen2.5-7B-Instruct + a 7–8B model from a different family). Use the prompt fix above, and check that honest F1–F3 entries clear 0.90 on held-out smoke data before calibration. Also report per-corruption-type rejection, especially `deleted_negation`, where Qwen-3B already followed the corrupted text only weakly.
