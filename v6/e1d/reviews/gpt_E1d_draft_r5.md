# GPT review of E1d DRAFT_PLAN v4, round 5 (real files, commit 4ffdc76), 2026-10-19

Codex exec, read-only sandbox, prompt pinned to commit `4ffdc76` (DRAFT_PLAN.md v4, all four tools and measurements, all reviews in v6/e1d/reviews/ incl. gpt_E1d_draft_r4.md and grok_E1d_draft_v3.md). Final message saved verbatim.

**Verdict: NEEDS CHANGES.** V4 resolves the feasibility evidence, traffic accounting, sizing and reporting concerns from r4. It is close to moving toward freeze, but the dev failure rules and optional A1 path still need deterministic definitions before model runs.

Reviewed HEAD **`4ffdc76`**. No High-severity issue found.

**Issues, ranked by severity**

1. **Medium — D7/D8 still leave qualification decisions open to interpretation.**  
   References: [DRAFT_PLAN.md:144](/workspace/glyph-repo/v6/e1d/DRAFT_PLAN.md:144), [DRAFT_PLAN.md:145](/workspace/glyph-repo/v6/e1d/DRAFT_PLAN.md:145), [DRAFT_PLAN.md:117](/workspace/glyph-repo/v6/e1d/DRAFT_PLAN.md:117).

   D7 applies “≥3 of 4 each” to verifier format, sender validity and receiver parseability. The first two have four entry-level observations per pair; receiver parseability has **16 case-level observations**. The plan does not define how those become four observations, or whether the three checks pass separately or jointly.

   D8 specifies pooled thresholds, but “any pair at fault” has no numerical definition. Its failure action also says “all three fail,” although the ladder permits a different number of adopted pairs.

   **Concrete fix:** define D7’s aggregation explicitly—for example, an entry passes receiver parseability only if all four prose answers parse, with each of the three screens separately requiring ≥3/4. For D8, either declare pair-level thresholds and a mechanical replacement rule, or make any pooled failure stop qualification pending amendment. Express counts as functions of the adopted-pair count, and explicitly retain all material shown in earlier dev stages in TEST’s exclusions.

2. **Medium — A1 has pricing data, but no complete protocol or selection contract.**  
   References: [DRAFT_PLAN.md:129](/workspace/glyph-repo/v6/e1d/DRAFT_PLAN.md:129), [DRAFT_PLAN.md:148](/workspace/glyph-repo/v6/e1d/DRAFT_PLAN.md:148), [DRAFT_PLAN.md:181](/workspace/glyph-repo/v6/e1d/DRAFT_PLAN.md:181).

   V4 specifies A1’s core-only dictionary and evaluation data. It does not specify its sender task, candidate construction/retrieval, handling of picks absent from that dictionary, or the rule selecting A0 versus A1. There is also no tie rule or rule combining the two directions. Dev-new qualification is not explicitly tied to the ultimately selected arm.

   **Concrete fix:** the shortest route is to declare **A0 the sole E1d arm** and defer A1. If retaining A1, define its complete sender/acceptance/fallback path, deterministic dev selection statistic and eligibility conditions, both-direction aggregation and tie rule; qualify the chosen protocol on dev-new before freeze.

**Status of r4 issues 1–5**

1. **Resolved:** approximate simulation is labelled; actual builder trials reproduce with the stated allocation and neighbour checks.
2. **Partly resolved:** D1–D8 and A1’s data source are substantial improvements; the two issues above remain.
3. **Resolved:** fixed aggregate traffic, update recipients, join versions and maintainer uploads are explicit and consistent.
4. **Resolved:** committed sizing calculation reproduces **1.652 / 1.356 percentage points** at 80 entries per family.
5. **Resolved:** §10 requires separate reporting for every adopted new pair, with denominators.

“Resolved” describes the design and supporting checks; E1d implementation and model qualification remain pending.

**Independent checks**

- Re-ran all four authorized scripts using `python3`, bytecode writing disabled, and **no output paths**. All parsed outputs match the committed JSON; builder elapsed-time fields were excluded from comparison.
- Reproduced **10/10 successful builder trials**, all recorded checks passing, with **21–33 TEST cores per new pair**.
- Reproduced **5** strictly fresh old-pair F2 texts, **56** texts per new pair, and **14,919** fresh F1 texts.
- Reproduced artifacts of **166,086 / 374,054 B**, gzip sizes **15,746 / 31,295 B**, loader checks, delta reconstruction and **15 B** serializer framing.
- Independently enumerated lifecycle events:
  - W_base: upload-inclusive delta multipliers **21/23/25/27**, applied **2/4/4/2** times; join versions **3/7/11**.
  - W_churn: multipliers **21/25/29/33**, applied **5/10/10/4** times; join versions **6/16/26**.
  - These match the written formulas.
- Checked the sender-local verifier, acceptance/fallback path, dictionary resolution, completeness checks and inherited dev eligibility against source.
- No files were written and no model, GPU or Kaggle run was launched. Git status remained unchanged, including the pre-existing deleted bytecode file.

**Files actually opened**

Paths below are relative to `/workspace/glyph-repo`. Source excerpts are identified; data files read by the scripts are included.

- `v6/e1d/DRAFT_PLAN.md`
- All four files in `v6/e1d/tools/`: `builder_trials.py`, `size_byte_bound.py`, `count_f2_fresh.py`, `measure_dict_artifact.py`
- All four files in `v6/e1d/measurements/`: `builder_trials.json`, `byte_bound_sizing.json`, `f2_fresh_counts.json`, `dict_artifact_e1c_t1.json`
- All eight reviews in `v6/e1d/reviews/`: `gpt_E1d_draft_r1.md`, `gpt_E1d_draft_r2.md`, `gpt_E1d_draft_r3.md`, `gpt_E1d_draft_r4.md`, `grok_E1d_draft_r1.md`, `grok_E1d_draft_v3.md`, `gpt_E1d_F2_fix.md`, `grok_E1d_F2_fix.md`
- `v6/e1c/PREREG_E1c.md`
- `v6/e1c/T1_REPORT.md`
- `v6/e1c/e1c/book.py`
- `v6/e1c/e1c/analysis.py`
- `v6/e1c/e1c/stages.py` — excerpts
- `v6/e1c/e1c/verifier.py`
- `v6/e1c/tools/check_freeze.py`
- `v6/e1c/tools/code_hash.py`
- `v6/e1b/e1b/protocol.py`
- `v6/e1b/e1b/cases.py` — excerpts and execution through builder
- `v6/e1b/e1b/a9.py` — excerpt and branch-check execution
- Script-read data: `v6/e1b/data/cases_e1b.json`, `v6/e1b/data/cases_e1b_a9.json`, `v6/e1c/data/book_dev.json`, `v6/e1c/data/book_test.json`
- Sizing inputs: `v6/e1c/results/T1/exchange_qwen7b_to_falcon7b.jsonl`, `v6/e1c/results/T1/exchange_falcon7b_to_qwen7b.jsonl`

tokens used: 83,389
