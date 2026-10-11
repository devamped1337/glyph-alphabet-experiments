# v6 E1 results: text-repository (oracle-ID receiver test)

## CORRECTIONS (2026-10-12 08:20 AEDT, after reviews `v6/e1/reviews/gpt_2.md` and `grok_3.md`; every figure re-checked against `v6/e1/results/` and `v6/e1/data/cases.json`)

The original text below is kept unchanged. Where it conflicts with this section, this section wins.

1. **Per-task breakdown** (main stage, % correct, n=160 per cell, re-computed from `predictions_main_*.jsonl`):

   | Model | Task | id_expanded | prose | Diff |
   |---|---|---|---|---|
   | Qwen2.5-3B | F1 negation | 98.8 | 99.4 | −0.6 |
   | Qwen2.5-3B | F2 roles | 76.3 (122/160) | 61.9 | +14.4 |
   | Qwen2.5-3B | F3 long definitions | 16.9 | 31.3 (50/160) | −14.4 |
   | SmolLM2-1.7B | F1 | 34.4 | 30.6 | +3.8 |
   | SmolLM2-1.7B | F2 | 41.3 (66/160) | 29.4 | +11.9 |
   | SmolLM2-1.7B | F3 | 10.0 | 5.6 | +4.4 |

   On Qwen, the gain on roles and the loss on long definitions (23 items each way) cancel out, so the pooled tie hides opposite per-task effects.
2. **Qwen vs prose is "inconclusive", not "equivalent" or "no worse".** The CI is [−0.075, +0.079], which crosses the ±0.05 margin. Read any wording below that implies a tie or equivalence as "inconclusive".
3. **Smol's advantage over prose may be a presentation effect.** id_expanded and prose differ in framing as well as in content, so the result does not show that the ID channel helps. It needs a direct-text baseline that uses the exact expanded definition with matched framing.
4. **Cache nondeterminism (observed, unexplained).** Cold `id_expanded` and repeat-request `id_expanded_cached` use byte-identical prompts (0/480 prompt differences) and greedy decoding. Even so, predictions differ on **45/480 (Qwen)** and **104/480 (Smol)**, and correctness flips on **21** and **33** of them. The observations stand as recorded. The cached condition is therefore not a pure timing replay of the cold one, and accuracy differences between them should not be interpreted.
5. **Overlap disclosure.** For the same entry, **97/480** main case texts also appear in calibration (43 F1, 54 F3, 0 F2). There are **9** further duplicates within main. Matching on case text alone, without the entry, 115/480 also appear in calibration. Main accuracy is therefore not on fully fresh cases. Calibration did not tune any receiver, so this is a disclosure, not leakage into training. The effective sample is smaller than 480.
6. **Rename "end-to-end" to "oracle-ID receiver accuracy, gate bypassed"** wherever it appears below (e.g. "Report **end-to-end only**" in the gate summary and the "Main accuracy (end-to-end)" heading). No sender selection and no gate filtering took place.
7. **The gate TEST figures are descriptive only.** The gate was not frozen (calibration failed), so the TEST numbers do not validate any gate.
8. **Validator scope.** `validate_v6.py` PASSED as an engineering check (files, counts, schema, gold). It does not certify any scientific claim in this document.

9. **The Smol win is a floor effect** (Claude, `claude_2.md`). Smol's accuracy is far below the prose ≥0.90 level in every family (F1 ≤34%, F2 ≤41%, F3 ≤10%), so its +0.067 over prose is not counted as evidence for the ID channel. It is reported per family only (see item 1).

### The next run must

Sources: GPT = `v6/e1/reviews/gpt_2.md`, Claude = `claude_2.md`, Grok = `grok_3.md` (and the earlier `grok_1.md`/`grok_2.md`).

1. **Capability precondition** before calibration: a smoke test showing each gate model can do the honest tasks (Claude; cf. Grok 1/2: scale the tasks to the models).
2. **A stronger gate pair:** ≥7B models from two different families if the 0.90 bar is kept (Claude; Grok 1). Grok 2 offers an alternative: a lower, pre-registered bar for small models, with 0.90 as the later target. One option must be chosen and pre-registered.
3. **Gate on rule comprehension, not arithmetic:** small-choice questions that check whether the rule was understood (Claude; GPT round 1).
4. **Manipulation check:** show that planted entries change a strong model's behaviour, and keep the planted corruptions Qwen ignored as a stress test (Claude; Grok 1/2).
5. **Matched direct-text baseline:** the exact expanded definition text with framing identical to id_expanded (GPT).
6. **Enforce disjoint and unique cases:** no main case may match any calibration or TEST-gate case (by entry and by text), and no duplicates within main, asserted in code before the run (GPT).
7. **Investigate cache determinism** with cold/cold, warm/warm and cold/warm repeats on identical prompts, before any cached timing or accuracy is reported (GPT).
8. **Real prefix cache:** a cached definition prefix reused across *different* cases, with prose given an equivalent cached prefix, replacing the repeat-request best case (Claude; GPT round 1).
9. **Fix FLOPs** to count only newly processed tokens (Claude; GPT round 1).
10. **Report per family, with ≥100 entries** (the effective n is message groups, not items) (Claude; GPT per-task table).
11. **Verify unknown-ID handling in code:** check the entry version and hash before the receiver acts. Smol acted on 42/48 unknown IDs (Claude).
12. **Real sender selection, as its own experiment:** the sender picks the entry ID instead of being handed it, and selection accuracy is reported (GPT; Claude).

---

Pre-registration: [v6/PREREG_v6.md](v6/PREREG_v6.md) (frozen 2026-10-11; tag `prereg-v6`).  
Calibration failure detail: [v6/e1/CALIBRATION_REPORT.md](v6/e1/CALIBRATION_REPORT.md) (already reported; not rewritten here).  
Code / data: `v6/e1/` (`e1.py`, `analyze_e1.py`, `config_e1.json`, `data/`, `results/`).  
Models: Qwen2.5-3B-Instruct and SmolLM2-1.7B-Instruct, GGUF Q4_K_M via llama.cpp on CPU.  
Sample: N=100 cases/entry calibration; N=40 TEST gate; 24 message groups × 20 items = **480** paired main items per model per condition.  
Validation: `v6/checks/validate_v6.py` **PASSED** 2026-10-12 00:15 AEDT (`v6/e1/logs/VALIDATED`). Run finished same timestamp (`logs/DONE`, `logs/run.log`).

Sources for every figure below: `v6/e1/results/summary_e1.json`, `v6/e1/results/gate_frozen.json`, `v6/e1/CALIBRATION_REPORT.md`, `v6/PREREG_v6.md`, `v6/e1/logs/run.log`.

---

## Scope (hard rules)

1. **E1 is an oracle-ID receiver test.** The sender is handed the correct entry ID. E1 measures how well the receiver uses a correct ID/expansion. It does **not** test ID selection. `sender_s` is string-formatting time only (~4e−7 s mean) and is **not** reported as sender cost.
2. **Cached timing is repeat-request only.** `id_expanded_cached` re-sends the identical prompt right after the cold `id_expanded` call. Label: **repeat-request cache**, not general prefix reuse. Prose/compact did not get matching caching, so cached-vs-uncached across conditions is not like-for-like.
3. **FLOPs caveat.** `analyze_e1.py` estimates FLOPs as `2·params·(prompt+gen tokens)` even for cached rows. That **overstates** cached cost and makes the FLOPs comparison **invalid as written**. No FLOPs win is claimed from those numbers.
4. Gate calibration fail is already documented in CALIBRATION_REPORT.md — summarised below, not rewritten.

---

## Bottom line (failures stated plainly)

1. **Behaviour gate — calibration:** rejected every honest entry (0/24 accept, 12/12 planted reject at 0.90) → `separates=false`, `gate_frozen=false`. Already documented in [CALIBRATION_REPORT.md](v6/e1/CALIBRATION_REPORT.md).
2. **Behaviour gate — TEST** (unseen corruptions): **FAIL.** Valid accept **0/24** (rate 0.0, CI [0.0, 0.138]); planted reject **16/16** (rate 1.0, CI [0.8064, 1.0]). Outcome **FAIL** per PREREG §4 (≥90% accept **and** ≥95% reject).
3. Because `gate_frozen=false` and zero entries were accepted, `acc_covered_only(gate-accepted entries)` is **null** for every condition. Report **end-to-end only**; no covered-only claim.
4. **Main receiver accuracy** (n=480 paired items, 24 message groups):
   - **Qwen2.5-3B:** prose 0.642, id_expanded 0.640, id_expanded_cached 0.633, compact 0.381, id_raw 0.010, placebo_prose 0.010
   - **SmolLM2-1.7B:** id_expanded 0.285, id_expanded_cached 0.317, prose 0.219, compact 0.098, id_raw 0.023, placebo_prose 0.008
5. **Paired** (id_expanded minus X, cluster bootstrap over message groups):
   - **Qwen:** beats compact (+0.258, CI [0.173, 0.348]), id_raw (+0.629), placebo_prose (+0.629); vs prose **inconclusive** (−0.002, CI [−0.075, 0.079])
   - **Smol:** beats compact (+0.188), id_raw (+0.263), placebo (+0.277), and prose (+0.067, CI [0.015, 0.119])
6. **Repeat-request cache latency:** Qwen id_expanded 2.86 s → cached 1.15 s; Smol 1.94 s → 0.71 s. Repeat-request only.
7. **Unknown-ID model abstention:** Qwen 48/48, Smol 6/48 (parser test 48/48 both).
8. **No accuracy win** for a competing channel over id_expanded on Qwen (prose tied / inconclusive). On Smol, id_expanded beats prose. **Primary efficiency win** (PREREG §7: non-inferior within 5 pts **and** ≥20% lower latency vs the valid cached expansion) is **not claimed**: prose is not a valid like-for-like cached comparison. Stated plainly: **no §7 efficiency win**.

---

## Gate

### Calibration (already reported)

At the pre-registered 0.90 threshold: honest accept **0/24**, planted reject **12/12**. `separates=false`, `gate_frozen=false`. Best grid threshold for information only was 0.50 (not adopted). Full per-entry tables: [CALIBRATION_REPORT.md](v6/e1/CALIBRATION_REPORT.md).

### TEST (unseen corruptions)

| Metric | Count | Rate | 95% CI |
|---|---|---|---|
| Valid accepted | 0 / 24 | 0.0 | [0.0, 0.138] |
| Planted rejected | 16 / 16 | 1.0 | [0.8064, 1.0] |
| **Outcome (PREREG §4)** | | | **FAIL** |

Planted TEST corruptions (all 4/4 rejected each): near_miss_polarity, swapped_roles, inverted_comparison, dropped_clause.

---

## Main accuracy (end-to-end)

n=480 per cell. Coverage=1.0 logged on every main row; covered-only is null because the gate accepted nothing.

| condition | Qwen2.5-3B acc | SmolLM2-1.7B acc | Qwen latency_s | Smol latency_s | Qwen prompt tok | Smol prompt tok |
|---|---|---|---|---|---|---|
| prose | 0.642 | 0.219 | 2.35 | 1.53 | 138.7 | 149.0 |
| id_expanded | 0.640 | 0.285 | 2.86 | 1.94 | 194.4 | 204.6 |
| id_expanded_cached (repeat-request) | 0.633 | 0.317 | 1.15 | 0.71 | 194.4 | 204.6 |
| compact | 0.381 | 0.098 | 2.67 | 1.22 | 114.7 | 124.7 |
| id_raw | 0.010 | 0.023 | 2.36 | 1.16 | 104.7 | 111.1 |
| placebo_prose | 0.010 | 0.008 | 2.22 | 1.31 | 137.1 | 147.4 |

Abstain rates (fraction of rows): Qwen prose 0.002, id_expanded 0.010, cached 0.017, compact 0.038, id_raw 0.177, placebo 0.167. Smol abstain ≈0 on all conditions except placebo 0.006.

### Paired differences (id_expanded − X)

Cluster bootstrap over 24 message groups; 480 pairs.

| contrast | Qwen diff | Qwen 95% CI | Qwen verdict | Smol diff | Smol 95% CI | Smol verdict |
|---|---|---|---|---|---|---|
| vs compact | +0.258 | [0.173, 0.348] | id_expanded better | +0.188 | [0.129, 0.252] | id_expanded better |
| vs id_raw | +0.629 | [0.490, 0.771] | id_expanded better | +0.263 | [0.190, 0.335] | id_expanded better |
| vs placebo_prose | +0.629 | [0.483, 0.760] | id_expanded better | +0.277 | [0.204, 0.346] | id_expanded better |
| vs prose | −0.002 | [−0.075, 0.079] | inconclusive | +0.067 | [0.015, 0.119] | id_expanded better |

Accuracy-win rule (PREREG §7): paired 95% CI entirely above zero vs ID-expanded text. No competing channel meets that against id_expanded on Qwen. On Smol, id_expanded beats prose on that rule.

---

## Latency (repeat-request cache only)

| model | id_expanded (cold) | id_expanded_cached (repeat) | reduction |
|---|---|---|---|
| Qwen2.5-3B | 2.86 s | 1.15 s | ~60% |
| SmolLM2-1.7B | 1.94 s | 0.71 s | ~64% |

Prose/compact were **not** run with matching repeat-request caching. Do not treat prose latency vs `id_expanded_cached` as a like-for-like §7 efficiency comparison. **No §7 primary efficiency win is claimed.**

### FLOPs

`analyze_e1.py` reports `flops_est = 2·params·(prompt+gen tokens)` for every row, including cached. Cached FLOPs are therefore overstated and **not comparable**. Those estimates are left in `summary_e1.json` for audit but are not used for any win claim here.

---

## Unknown-ID

| check | Qwen2.5-3B | SmolLM2-1.7B |
|---|---|---|
| Parser test correct | 48 / 48 | 48 / 48 |
| Model abstained | 48 / 48 | 6 / 48 |

Qwen abstains on every unknown-ID item. Smol mostly does not (6/48); the parser test still passes 48/48.

---

## What this does and does not show

**Shows:** with the correct ID handed to the sender, expanding that ID into text for the receiver (`id_expanded`) matches prose on Qwen within noise, and beats prose on Smol. Compact, raw ID, and placebo collapse. The behaviour gate rejects planted TEST corruptions but also rejects every honest entry, so it does not separate.

**Does not show:** ID *selection* by a sender; a working behaviour gate for the repository; a like-for-like cached-KV efficiency win for prose vs expansion; a valid FLOPs comparison under the current estimator.

---

## Pre-registered decisions (pointer)

See [PREREG_v6.md](v6/PREREG_v6.md) §4 (gate), §6–7 (efficiency / win criteria), and the 2026-10-11 E1 implementation amendment (models, N=100 / N=40 / 480, greedy ≤160 tokens, corruption types, cluster bootstrap).

---

## Validation

```
VALIDATION PASSED
done Mon Oct 12 00:15:10 AEDT 2026
```

Marker files: `v6/e1/logs/DONE`, `v6/e1/logs/VALIDATED`. Full validator transcript: `v6/e1/logs/run.log`.
