# GPT review of E1d DRAFT_PLAN v3, round 4 (real files, commit da0fe97), 2026-10-19

Codex exec, read-only sandbox, prompt pinned to commit `da0fe97` (DRAFT_PLAN.md v3, both measurement scripts and outputs, all reviews in v6/e1d/reviews/). Final message saved verbatim.

**Verdict: NEEDS CHANGES.** V3 is substantially closer to freeze: the original F2 impossibility is removed, the artifact measurements reproduce, and the revised claim is appropriately conditional on a declared scenario. Before freezing, tighten the F2 feasibility/qualification procedure and resolve the remaining lifecycle-accounting ambiguities; I found no new High-severity issue.

Reviewed repository HEAD **`da0fe97`**.

1. **Medium — the F2 simulation does not simulate the declared dev procedure.**  
   References: [count_f2_fresh.py:24](/workspace/glyph-repo/v6/e1d/tools/count_f2_fresh.py:24), [DRAFT_PLAN.md:105](/workspace/glyph-repo/v6/e1d/DRAFT_PLAN.md:105), [DRAFT_PLAN.md:118](/workspace/glyph-repo/v6/e1d/DRAFT_PLAN.md:118).

   The simulation draws dev cores uniformly from the entire fresh pool, including old pairs. The plan instead requires **four cores per new pair**. It also generates each neighbour once, whereas the real builder rejects/regenerates neighbours for label uniqueness, load-bearing gold changes and forbidden texts. Consequently, “99.95–100% fill” is evidence from a simplified occupancy model, not the stated full-builder feasibility rate.

   **Fix:** label the current numbers as an approximate pool simulation. Make the promised ten actual builder trials the authoritative feasibility check, using the exact per-pair dev allocation, neighbour checks and historical exclusions. If the ladder adds pairs, explicitly change dev size to **4 × adopted new pairs**, and qualify every adopted pair.

2. **Medium — dev-new execution is specified, but qualification is not.**  
   References: [DRAFT_PLAN.md:118](/workspace/glyph-repo/v6/e1d/DRAFT_PLAN.md:118), [DRAFT_PLAN.md:135](/workspace/glyph-repo/v6/e1d/DRAFT_PLAN.md:135), [DRAFT_PLAN.md:140](/workspace/glyph-repo/v6/e1d/DRAFT_PLAN.md:140).

   “Run the new vocabulary through both models” does not say what permits freezing afterward. The inherited E1c eligibility code expects a different assignment shape and an observed wrong-accept screen; §8 identifies gate-code adaptations but does not explicitly replace that dev eligibility contract. A1 selection also leaves unclear whether its dev statistics use reused E1c dev, dev-new, or both.

   **Fix:** define one E1d dev assignment and eligibility table: exact sender/receiver counts, completeness, conformance checks, timing/cap rule, any performance screens, and the response to failure. Explicitly state which E1c dev screens survive. For A1, specify the evaluation data and dictionary size used for dev lifetime-cost selection.

   Twelve entries are reasonable as a **vocabulary smoke test**, provided that limited role is stated; they do not establish new-pair reliability precisely.

3. **Medium — participant accounting still has inconsistent interpretations.**  
   References: [DRAFT_PLAN.md:61](/workspace/glyph-repo/v6/e1d/DRAFT_PLAN.md:61), [DRAFT_PLAN.md:75](/workspace/glyph-repo/v6/e1d/DRAFT_PLAN.md:75), [DRAFT_PLAN.md:80](/workspace/glyph-repo/v6/e1d/DRAFT_PLAN.md:80), [DRAFT_PLAN.md:87](/workspace/glyph-repo/v6/e1d/DRAFT_PLAN.md:87).

   The base formula accumulates participants from 20 to 26, while traffic remains 180,000 despite being described as 100 messages **per agent per day**. In W_churn, joins coincide with deltas on days 15, 45 and 75. “Delta first” implies joiners receive the updated full artifact only, but “participants at that day” could also charge them that day’s delta.

   **Fix:** explicitly hold aggregate traffic fixed despite joins, or derive traffic from active participant-days. Define delta recipients as participants present **immediately before** the event; then process joins. Also state whether W_copy includes the maintainer upload under the same accounting boundary.

4. **Low — the byte-precision justification needs a reproducible calculation and slightly revised figures.**  
   Reference: [DRAFT_PLAN.md:97](/workspace/glyph-repo/v6/e1d/DRAFT_PLAN.md:97).

   My independent 10,000-replicate calculation, resampling 80 entries per family and including the 15-byte framing, found ratio SDs approximately **0.0108 / 0.0088**. The one-sided upper-ratio distances were approximately **1.85 / 1.53 percentage points**; multiplying by `a=0.89` gives lifetime-saving bound distances around **1.64 / 1.36 points**. The stated 1.2–1.5 range is somewhat optimistic, particularly for Qwen→Falcon.

   **Fix:** commit the sizing calculation with its seed, serializer and transformation to S. This correction does not materially undermine choosing 80 per family.

5. **Low — “per-pair” reporting currently means two pooled groups in §7.**  
   References: [DRAFT_PLAN.md:121](/workspace/glyph-repo/v6/e1d/DRAFT_PLAN.md:121), [DRAFT_PLAN.md:133](/workspace/glyph-repo/v6/e1d/DRAFT_PLAN.md:133).

   The specified split is new-pair versus old-pair F2, which can hide differences among baker/porter, potter/bearer and tanner/loader.

   **Fix:** report counts, coverage, accuracy, wrong accepts and bytes for **each adopted new pair**, alongside the pooled comparison. Show denominators and mark empty groups as unavailable.

**Status of previous issues and F2 risks**

| Point | Status |
|---|---|
| r3 #1: impossible fresh F2 TEST | **Partly resolved:** 173 available texts removes the cardinality obstruction; actual full-builder feasibility remains to be demonstrated. |
| r3 #2: lifecycle costs mislabelled as measured | **Resolved at design level:** measured v1 inputs and derived future costs are clearly distinguished. |
| r3 #3: reproducible churn sensitivities | **Partly resolved:** versions, dates and rounding are specified; participant timing/accounting needs issue 3’s clarification. |
| F2 risk: available pool versus distinct sampled cores | **Partly resolved:** useful simulation and mandatory builder trials, but the simulation differs from the declared procedure. |
| F2 risk: vocabulary, token length and semantic cues | **Partly resolved:** disclosed words and collision checks help; model qualification and individual-pair reporting remain pending. |
| F2 risk: E1c dev cannot qualify unseen roles | **Partly resolved:** dev-new addresses exposure, but its qualification rule is unspecified. |
| F2 risk: preserve parsing, gold, freshness and branch checks | **Resolved in the proposed procedure; execution pending.** |
| F2 risk: remeasure serialized costs | **Resolved in the proposed procedure; E1d artifact measurement remains pending.** |

**Independent checks**

- Re-ran both CPU scripts with bytecode writing disabled and no output path. **Both parsed outputs equal their committed JSON exactly.**
- Reproduced minimal/full published artifacts of **166,086 / 374,054 bytes**, gzip sizes **15,746 / 31,295 bytes**, the delta checks, and **15-byte** message framing.
- Reproduced **5** strictly fresh old-pair F2 texts, **173** with three new pairs, and **14,919** fresh F1 texts.
- Checked the actual sender-local verifier, acceptance/fallback path and dictionary resolution against the implementation.
- Recomputed T1 per-entry accuracy-difference SDs: **0.0360 / 0.0505**, with **2 / 10** nonzero entries.
- Recomputed coverage shortfall probabilities at 160 entries: **0.0163% / 0.0000090%** at the observed T1 rates, and **1.67%** at true coverage 90%. These support §6.
- Recomputed zero-error CP95 at 160 picks: **1.8549%**, consistent with the stated 1.86%.
- Confirmed the proposed timing estimate is consistent with scaling T1 sender/receiver work to two-thirds while retaining model loads: approximately **2.2 GPU-hours raw**.
- No files were written and no model, GPU, Kaggle or heavy run was launched.

**Files actually opened**

Paths below are relative to `/workspace/glyph-repo`; JSON books read by the CPU scripts are included.

- `v6/e1d/DRAFT_PLAN.md`
- `v6/e1d/tools/measure_dict_artifact.py`
- `v6/e1d/tools/count_f2_fresh.py`
- `v6/e1d/measurements/dict_artifact_e1c_t1.json`
- `v6/e1d/measurements/f2_fresh_counts.json`
- `v6/e1d/reviews/gpt_E1d_draft_r1.md`
- `v6/e1d/reviews/gpt_E1d_draft_r2.md`
- `v6/e1d/reviews/gpt_E1d_draft_r3.md`
- `v6/e1d/reviews/grok_E1d_draft_r1.md`
- `v6/e1d/reviews/grok_E1d_F2_fix.md`
- `v6/e1d/reviews/gpt_E1d_F2_fix.md`
- `v6/e1c/PREREG_E1c.md`
- `v6/e1c/T1_REPORT.md`
- `v6/e1c/e1c/analysis.py`
- `v6/e1c/e1c/stages.py`
- `v6/e1c/e1c/book.py`
- `v6/e1c/e1c/verifier.py`
- `v6/e1c/tools/check_freeze.py`
- `v6/e1c/tools/code_hash.py`
- `v6/e1c/data/book_dev.json`
- `v6/e1c/data/book_test.json`
- `v6/e1c/results/T1/summary.json`
- `v6/e1c/results/T1/exchange_qwen7b_to_falcon7b.jsonl`
- `v6/e1c/results/T1/exchange_falcon7b_to_qwen7b.jsonl`
- `v6/e1c/results/T1/select_qwen7b.jsonl` — excerpt
- `v6/e1c/results/T1/select_falcon7b.jsonl` — excerpt
- `v6/e1b/e1b/cases.py`
- `v6/e1b/e1b/protocol.py`
- `v6/e1b/data/cases_e1b.json`
- `v6/e1b/data/cases_e1b_a9.json`

tokens used: 73,303
