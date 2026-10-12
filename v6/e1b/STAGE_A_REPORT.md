# E1b Stage A report: stopped on BUDGET_EXHAUSTED (diagnostic only, no claims)

**Run:** 2026-10-12, 09:56–15:31 AEDT, on the box CPU (8 threads, llama.cpp, Q4_K_M GGUFs). Detached job with per-row checkpoints. **No Kaggle, no paid APIs, no Stage B started.**

| Field | Value |
|---|---|
| First attempt commit / code hash | `931b3df` / `682b727b…` (stopped by projection after A1) |
| Resume commit / code hash | `aa9ef296…` / `4611e220…` (Amendment A4: 5.5 h box-CPU) |
| Config sha256 | `9de5200297dbf289a96326029c2c8e7bf4b9bf47f18b76fb3810b93b641cd06f` |
| Models | qwen3b = Qwen2.5-3B-Instruct Q4_K_M; smol17 = SmolLM2-1.7B-Instruct Q4_K_M |
| Budget | Amendment A4: **5.5 h** box-CPU (`stageA.budget_h`) |
| Ledger | `results/budget_ledger.json` → **19807.5 s ≈ 5.502 h** |
| Stop marker | `results/A/BUDGET_EXHAUSTED` — *A exceeded 5.50 h; stopped, not shrunk* |
| Process | PID 2521170 confirmed **dead** after exit |

Wall-clock: first start 09:56 AEDT → stop 15:31 AEDT (~5.58 h calendar, including the projection stop / A4 resume). Cumulative charged time is the ledger (5.502 h).


## CORRECTIONS (2026-10-12 AEDT, after GPT's review [gpt_stageA](reviews/gpt_stageA.md); every point re-verified against the raw rows)

1. **A4: the 0.425 follow rate is an abstention failure, not "ignoring the corruption".** Of the 40 gold-changing cases:
   - **17/17 followed the plant** where the corrupted rule implied a *different number* (swapped_roles 10, changed_constant 4, inverted_comparison 3).
   - **0/23 abstained** where it implied **UNKNOWN** (deleted_negation 10, mismatched_definition 10, near_miss_polarity 3).
   - Verification nuance GPT did not state: in 10 of those 23 cases, Qwen gave the *honest* (pre-corruption) answer; the other 13 gave some other number. So Qwen tracks numeric changes but never abstains, and sometimes falls back on the uncorrupted reading.
   - The "By corruption" line in §A4 above is correct; earlier wording implying general ignoring of corruption is withdrawn.
2. **A2 "Planted" accuracy (Qwen 0.674, Smol 0.347) is scored against the corrupted text shown** (`correct = letter == gold`), so a value above zero does **not** show the corruption was ignored.
   - Against the honest meaning (`honest_correct`), Qwen scores 0.542.
   - On the 75 Qwen probes whose answer the corruption flips, Qwen chose the shown-text answer 37 times and the honest answer 18 times.
3. **A5 cache: the divergence is localised to chunking, not state restore.** For both models, cold/cold and warm/warm show 0 changed predictions and 0 token changes. Cold/warm shows **6/100 (Qwen) and 16/100 (Smol)** changed predictions on the fixed set, with token changes on 46 and 85 of 120 prompts.
   - **Coldsplit vs warm is token-identical on all 120/120 prompts for both models**, and cold vs coldsplit reproduces exactly the cold/warm changes.
   - So the change comes from processing the prompt in one chunk vs as prefix + suffix chunks (a numerics difference in llama.cpp batching), **not** from saving and restoring the cache state.
   - **The cache claim stays withheld** (frozen rule: any cold/warm change withholds it).
4. **A6 is not re-run.** It stays partial (qwen3b 218/480, smol17 none). No cost claim.
5. **Claude's review ([claude_stageA](reviews/claude_stageA.md)), verified:**
   - **A4 by corruption type checks out** (followed: changed_constant 4/4, swapped_roles 10/10, inverted_comparison 3/3; not followed: deleted_negation 0/10, mismatched_definition 0/10, near_miss_polarity 0/3). It is the same split as point 1. The not-followed types are exactly the ones whose corrupted gold is UNKNOWN, so "gap-filling" (answering numerically where the rule no longer determines a number) is the accurate description.
   - **The binomial arithmetic checks out:** P(≥22/24 | p = 0.90) = **0.564**. At p = 0.95 it is 0.884. With two independent models at p = 0.90 both passing, it is 0.318, before the agreement bar.
   - **The chunking noise floor checks out:** cold vs cold-split changes predictions on 6% (Qwen) and 16% (Smol) of the fixed prompts.
   - **First vs last integer after `Answer:` differ** on 1/114 Smol A1 rows (0.9%) and 0/116, 0/118, 0/119 and 0/216 on the other files, all below Claude's proposed 2% trigger.
   - **The *-unstated no-text answers** were "correct" (Not stated) on 119/192 runs across both models.
   - Claude's proposals are recorded as reviewer proposals in [AMENDMENT_A5_DRAFT.md](AMENDMENT_A5_DRAFT.md); none is adopted yet.


## Outcome

Stage A completed **A1–A5 for both models**, **A4 for qwen3b only** (by design), and **partial A6 for qwen3b only (218/480)**. It did **not** finish A6 smol17, did not write `.done`, and stopped with `BUDGET_EXHAUSTED`.

| Step | qwen3b | smol17 |
|---|---|---|
| A1 capability | 120/120 | 120/120 |
| A2 probes | 1152/1152 | 1152/1152 |
| A3 prompt ablation | 120/120 | 120/120 |
| A4 manipulation | 60/60 | n/a (Qwen only) |
| A5 CPU cache | 120/120 | 120/120 |
| A6 cost | **218/480 partial** | **missing** |
| `summary.json` | written post-hoc from `summarize_A` | (same file) |

**Exit rule (§7 / `analysis.summarize_A`):** small pair may calibrate only if honest probe pass-share ≥ 0.80 **and** A4 follow ≥ 0.70. Measured: **honest_pass_share = 0/18 = 0.00**, **a4_follow = 0.425**. → **`small_pair_may_calibrate = false`**. Per the prereg: **go to Stage B (7B)**; do not calibrate the 3B/1.7B pair. **This publish task did not start Stage B.**

Stage A remains **diagnostic only**: no repository, ID-channel, or efficiency claims.

## A1 capability smoke (direct text, 40 cases per family per model)

| Family | Qwen2.5-3B | SmolLM2-1.7B |
|---|---|---|
| F1 negation | **40/40** (1.00) | 37/40 (0.925) |
| F2 roles | 29/40 (0.725) | 20/40 (0.50) |
| F3s short schedule | 33/40 (0.825) | 13/40 (0.325) |
| **All** | 102/120 (0.85) | 70/120 (0.583) |

Against the §7 capability floor of 0.70: Qwen clears every family; Smol fails F2 and F3s. Reported only.

## A2 probes (24 entries × 24 probes × with/without text; bar 0.90 acc + 0.90 agree per honest entry)

With-text accuracy (pooled):

| Slice | Qwen2.5-3B | SmolLM2-1.7B |
|---|---|---|
| Honest (432 probes) | 0.863 | 0.477 |
| Planted (144 probes) | 0.674 | 0.347 |
| F1 / F2 / F3s (with-text) | 0.810 / 0.769 / 0.896 | 0.440 / 0.412 / 0.500 |

**Honest entry exit (need each model ≥0.90 and agree ≥0.90):** **0/18 pass** (share 0.00; need ≥0.80).

Qwen is often 21/24 = 0.875 (just under the bar). Highest Qwen honest entries: F3s-9760 1.00, F1-9694 / F2-5247 0.917. Smol never reaches 0.90 on any honest entry (max ≈0.583). Agreement on honest entries ranges ≈0.25–0.625.

Invalid letter rate: **0** for both models (all 1152+1152 parse_path=`letter`).

### A2 no-text / leak flags (`stages.leak_rule`)

- **Template-level flagged list:** empty (most templates have &lt;50 no-text observations → listed under `insufficient_obs`).
- **Kind-level leaks** (pooled no-text baseline &gt; 0.40): **`F1-unstated` (0.625), `F2-unstated` (0.542), `F3s-unstated` (0.729)**.
- Other kind baselines are near chance (~0.10–0.29). Full structure in `results/A/summary.json` → `A2_no_text`.

## A3 prompt ablation (trailing Answer line)

| Model | F1 | F2 | F3s | paired Δ (A1−A3) | missing Answer-line rate (A1 fixed → A3 trailing) |
|---|---|---|---|---|---|
| Qwen | 40/40 | 32/40 | 33/40 | −0.025 | 0.017 → 0.000 |
| Smol | 25/40 | 17/40 | 12/40 | +0.133 | 0.050 → 0.008 |

## A4 manipulation (Qwen only; scored on gold-changing cases)

- Rows: 60; **gold_changes = 40**; **follows_planted = 17/40 = 0.425** (need ≥0.70 for the Stage A exit conjunction).
- By corruption (follow / gold-changing): changed_constant 4/4, swapped_roles 10/10, inverted_comparison 3/3, deleted_negation 0/10, mismatched_definition 0/10, near_miss_polarity 0/3.

## A5 CPU cache diagnostic

`cachediag.summarize` on both models:

| Model | claim_allowed | fixed cold↔cold predΔ | fixed warm↔warm predΔ | fixed cold↔warm predΔ | stress cold↔warm predΔ | invalid_runs |
|---|---|---|---|---|---|---|
| Qwen | **false** | 0/100 | 0/100 | **6/100** | 0/20 (1 tokenΔ) | 0 |
| Smol | **false** | 0/100 | 0/100 | **16/100** | **4/20** | 0 |

Pattern: cold/cold and warm/warm are stable; cold vs warm (and cold vs coldsplit) diverge, while coldsplit matches warm → prefix/suffix split vs one-shot cold is the change source, not warm restore vs warm. **Cache claim WITHHELD** for both; wording in summary: use uncached runs for any later claim in this runtime.

Logit gaps (all A5 runs, `first_gap`): Qwen mean ≈1.90 (min≈0.062); Smol mean ≈0.46 (min≈0.004); Smol has many near-ties (100/600 runs with first_gap &lt; 0.1). Stress set = the 20 hand-chosen near-tie prompts (reported separately from the rule-of-three bound on the 100 fixed prompts).

E1 cache baseline (recorded in summary for comparison): Qwen changed 45 / flipped 21 of 480; Smol changed 104 / flipped 33 of 480.

## A6 cost (partial — no cost claim)

- **qwen3b:** 218 rows (direct_text cold/warm 59+59; prose cold/warm 50+50). Incomplete vs scheduled 480.
- **smol17:** file absent.
- **No A6 cost / efficiency claim.** `A6_valid` follows A5 `claim_allowed` → false for both in summary.

## Exit verdict

```
honest_pass_share = 0.00   (need >= 0.80)
a4_follow         = 0.425  (need >= 0.70)
small_pair_may_calibrate = false
```

**Verdict: go to Stage B (7B).** The small pair does not clear the Stage A exit bar. Stage A results are published either way. **Stage B / Kaggle were not started by this report.**

## Was the run real? Verification before reporting

| Check | Result |
|---|---|
| Process dead | PID 2521170 not running; stage_log ends with `budget_exhausted` at 15:31 AEDT |
| BUDGET_EXHAUSTED | Present; text matches ledger stop; ledger 19807.5 s ≥ 5.5 h |
| Prompt truncation | **0** rows with `prompt_tokens >= n_ctx` (2048). Max prompt_tokens observed: **161** (A3_smol17) |
| Gen hitting 192-token cap | A1 Qwen 3/120 (1 correct); A3 Qwen 3/120 (3 correct); others 0 |
| Parser (arithmetic) | Re-parse of `raw` via frozen `parse_answer` matches logged `pred`/`parse_path` on all A1/A3/A4/A6 rows. Paths mostly `answer_line`; A1 Qwen 2× `last_integer`, A1 Smol 6×, A3 Smol 1× |
| A1.5 first-integer quirk | **1** Smol A1 row: `Answer: 12 * 3 = 36 credits` → pred=12 (frozen rule), gold=36, scored wrong. Known frozen behaviour, not a parser bug |
| Parser (A2) | 100% `letter`; 0 invalid |
| Gold recompute | `gold_from_text(entry, case)` on all non-planted A1/A3/A6 rows: **0 mismatches** (240+240+218). A4 is all planted (skipped by design). A2 `correct` ↔ `letter==gold`: 0 mismatches |
| Validator | `python validate_v6.py --e1b --results-dir v6/e1b` → **PASSED**, status `incomplete:BUDGET_EXHAUSTED`. Marker was already in `INCOMPLETE_MARKERS` (no validate fix this round; code hash unchanged `4611e220…`) |
| Leak / cache | From helpers above; claim_allowed false both models; kind-level unstated leaks flagged |

## Files

`results/A/A1_*.jsonl`, `A2_*.jsonl`, `A3_*.jsonl`, `A4_qwen3b.jsonl`, `A5_*.jsonl`, `A6_qwen3b.jsonl` (partial), `prompts_*.jsonl`, `stage_log.jsonl`, `BUDGET_EXHAUSTED`, `summary.json` (from `e1b.analysis.summarize_A`), `results/budget_ledger.json`, `logs/A.log`, this report.

## Failures / incompleteness (published openly)

- Budget exhausted before A6 finished; no A6_smol17; no `.done`.
- Small-pair Stage A exit **failed** (0/18 honest entries; A4 follow 0.425).
- Smol below capability floor on F2/F3s.
- Cache claim withheld (cold↔warm prediction changes).
- Kind-level no-text leaks on all three `*-unstated` probe kinds.
- One known A1.5 Answer-line multi-integer scoring quirk (Smol).
