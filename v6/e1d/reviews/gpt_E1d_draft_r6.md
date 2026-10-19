# GPT review of E1d DRAFT_PLAN v5, round 6 (final pre-freeze check, real files, commit 631ff32), 2026-10-19

Verbatim final message from `codex exec` (read-only sandbox). Prompt: final pre-freeze check of v5.

---

**Verdict: READY TO FREEZE — as plan text.** V5 resolves both r5 issues; I found no remaining design blocker. Implementation, dev qualification, and Stefan’s authorization remain later steps, as the plan specifies.

**Must-fix before freeze:** None.

**Optional correction**

- [DRAFT_PLAN.md:103](/workspace/glyph-repo/v6/e1d/DRAFT_PLAN.md:103): change the all-loads-at-420-seconds dev estimate from **≈0.76 h to ≈0.85 h**. Replacing D2’s measured 628 seconds of loads with 1,260 seconds gives approximately 3,070 seconds overall. This remains below the declared 1.0-hour cap and does not change the readiness assessment.

**Status of r5 issues**

1. **Resolved.** [Lines 149–162](/workspace/glyph-repo/v6/e1d/DRAFT_PLAN.md:149) define separate D7 screens, case-level receiver counts, numerical pair and pooled D8 thresholds, and deterministic replacement/stop outcomes. [Line 120](/workspace/glyph-repo/v6/e1d/DRAFT_PLAN.md:120) excludes earlier dev exposure, including replacement books and replaced pairs.
2. **Resolved.** A0 is the sole arm; A1 is explicitly deferred. No operative A1 selection or qualification dependency remains.

**Independent checks**

- Re-ran all four CPU-only tools without output paths and with bytecode writing disabled. Outputs matched the committed measurements, excluding builder elapsed-time fields.
- Reproduced **10/10 successful builder trials**.
- Verified D7’s **4 entry observations and 16 prose receiver observations per pair per direction**, and D8’s **16k pooled messages**, with thresholds **36 correct and difference ≥−4** at k=3. The outcome rules cover all stated combinations of failures and remaining replacements.
- Independently enumerated lifecycle events: W_base join versions **3/7/11**, delta multipliers **21/23/25/27** repeated **2/4/4/2** times; W_churn versions **6/16/26**, multipliers **21/25/29/33** repeated **5/10/10/4** times. Both match the plan.
- Recomputed TEST estimate: **2.03 GPU-h raw; 2.53 h with 25% margin**. Dev estimate: **0.68 h**, or **0.85 h** with all loads at the prior.
- Reproduced sizing distances **1.652/1.356 percentage points**, artifact sizes **166,086/374,054 bytes**, and **15-byte** framing.
- No files were written and no model, GPU, or Kaggle runs were launched. Git status retained the pre-existing deleted bytecode file.

**Files actually opened**

Paths are relative to `/workspace/glyph-repo`; source reads included excerpts where relevant.

- `v6/e1d/DRAFT_PLAN.md`
- `v6/e1d/reviews/gpt_E1d_draft_r5.md`
- `v6/e1d/reviews/grok_E1d_draft_v4.md`
- All four `v6/e1d/tools/` files: `builder_trials.py`, `size_byte_bound.py`, `count_f2_fresh.py`, `measure_dict_artifact.py`
- All four `v6/e1d/measurements/` files: `builder_trials.json`, `byte_bound_sizing.json`, `f2_fresh_counts.json`, `dict_artifact_e1c_t1.json`
- `v6/e1c/PREREG_E1c.md`, `D2_REPORT.md`, `T1_REPORT.md`
- `v6/e1c/e1c/__init__.py`, `analysis.py`, `book.py`, `stages.py`, `verifier.py`
- `v6/e1b/e1b/__init__.py`, `protocol.py`, `cases.py`
- `v6/e1c/results/D2/summary.json`
- `v6/e1c/results/T1/summary.json`
- Script-read inputs: `v6/e1c/config_e1c.json`, `v6/e1b/config_e1b.json`; both E1b books (`cases_e1b.json`, `cases_e1b_a9.json`); both E1c books (`book_dev.json`, `book_test.json`); both T1 `exchange_*.jsonl` files.

---

tokens used: 64,272
