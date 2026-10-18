# GPT review of E1d DRAFT_PLAN v2, round 3 (real files, commit 22e4b58), 2026-10-19

Codex exec, read-only sandbox, prompt pinned to commit `22e4b58` (DRAFT_PLAN.md v2, tools/measure_dict_artifact.py, measurements/dict_artifact_e1c_t1.json, GPT r2, Grok r1). Final message saved verbatim.

**Verdict: NEEDS CHANGES.** V2 resolves most of the earlier design concerns, and the committed artifact measurements reproduce exactly. However, the stated freshness exclusions leave only **83 available F2 rules**, making every proposed TEST size impossible; the update-cost and sensitivity specifications also need tightening before freeze.

**Issues, ranked by severity**

1. **High — no proposed TEST size is feasible with the unchanged generator.**  
   [DRAFT_PLAN.md:98](/workspace/glyph-repo/v6/e1d/DRAFT_PLAN.md:98), especially line 99; generator at [cases.py:43](/workspace/glyph-repo/v6/e1b/e1b/cases.py:43).

   F2 has exactly `10 role pairs × 8 × 7 ordered rate pairs = 560` possible honest rule texts. Applying the plan’s historical exclusions leaves:

   | Historical exclusion added | Fresh F2 texts remaining |
   |---|---:|
   | E1b frozen | 414 |
   | E1b A9 | 283 |
   | E1c dev | 203 |
   | E1c TEST | **83** |

   Thus 315, 237 and 150 distinct fresh F2 rules are all impossible. Seed retries cannot overcome this limit. The inherited 120-F2 receiver subset is impossible too.

   **Concrete fix:** revise the data design before feasibility trials. One viable direction is to expand the F2 generator’s rule space, disclose the change and qualify it on development data. Alternatively, redesign the allocation and statistical gate explicitly. Then propagate the chosen sizes through the bootstrap, receiver subset, workload dictionary, update counts and gate table. Do not weaken freshness silently.

2. **Medium — future update costs are modelled, while the bootstrap calls them exactly measured.**  
   [DRAFT_PLAN.md:26](/workspace/glyph-repo/v6/e1d/DRAFT_PLAN.md:26), [DRAFT_PLAN.md:78](/workspace/glyph-repo/v6/e1d/DRAFT_PLAN.md:78).

   The initial artifact is measured, but future delta bodies use added-entry counts multiplied by the initial mean line length. Those are deterministic scenario estimates, not exact serialized artifacts. Future full copies also require their own manifests; the current shorthand does not fully specify how manifest lengths change with version and membership.

   **Concrete fix:** either construct and measure the lifecycle artifacts, or explicitly call F a **fixed, derived scenario cost based on measured v1 bytes**. For the latter, freeze equations for body size, manifest size and rounding at every version. Keeping this cost fixed in every bootstrap replicate remains appropriate, provided the interval’s conditional interpretation includes these assumptions.

3. **Medium — the churn sensitivities do not define a uniquely reproducible lifecycle.**  
   [DRAFT_PLAN.md:84](/workspace/glyph-repo/v6/e1d/DRAFT_PLAN.md:84).

   Fifteen replacements and twelve weekly updates do not specify which version each replacement receives. Also, 2.5% of 630 rules is **15.75 rules**: rounding, family allocation, and whether growth is relative to v1 or the current dictionary are unspecified. These choices affect full-copy costs and compressed-artifact comparisons.

   **Concrete fix:** declare replacement and update days, event ordering on coincident days, integer additions per update, their reference population, and an explicit F formula or event-summing algorithm. Define how gzip update costs are obtained if update artifacts remain hypothetical.

**Status of the previous review points**

“Resolved” here means resolved in the design; it does not certify E1d implementation that has yet to be written.

| Point | Status and reason |
|---|---|
| GPT r2 #1 — byte boundary | **Resolved:** serializer, common bytes, exclusions and setup are explicit. |
| GPT r2 #2 — distribution object | **Resolved:** measured artifact and unchanged-Dictionary round trip close the membership/accounting gap. |
| GPT r2 #3 — bootstrap | **Resolved:** paired, stratified ratio bootstrap is specified; clarify F’s provenance as above. |
| GPT r2 #4 — workload | **Partly resolved:** base scenario is substantially specified; lifecycle pricing and sensitivities need the fixes above. |
| GPT r2 #5 — verifier location | **Resolved:** sender-side verification and zero rejected-ID network bytes match E1c. |
| GPT r2 #6 — wrong-ID gate | **Partly resolved:** denominator and CP arithmetic are correct, but the proposed fresh sample cannot be generated. |
| GPT r2 #7 — freshness/arm selection | **Partly resolved:** historical exclusions and dev-only selection are appropriate; the data-size ladder is impossible. |
| GPT r2 #8 — verdict/freeze machinery | **Resolved at design level:** new gates and required adaptations are explicit; implementation checks remain prerequisites to freeze. |
| Grok #1 — dictionary cost | **Resolved:** actual minimal artifact measured and round-tripped. |
| Grok #2 — total bytes | **Resolved:** primary accounting boundary and serializer specified. |
| Grok #3 — checker | **Resolved:** unchanged sender-side topology. |
| Grok #4 — wrong-ID gate | **Partly resolved:** correct statistics, infeasible proposed fresh sample. |
| Grok #5 — workload | **Partly resolved:** concrete labelled scenario, with remaining lifecycle ambiguities. |

**Independent checks**

- Re-ran the measurement script with bytecode writing disabled and no output path. Its parsed output **equals the committed JSON exactly**.
- Reproduced minimal artifact **166,086 B**, published-membership artifact **374,054 B**, gzip sizes **15,746 B / 31,295 B**, and example delta **18,704 B**.
- Reproduced successful member round trips, non-member rejection, version/hash rejection, tamper rejection and delta reconstruction.
- Reproduced **15 B framing overhead** in both arms across all 960 T1 cases.
- Recomputed CP95 minimum sample sizes: **299 / 473 / 628** for zero / one / two errors. At 630 picks, the upper bounds are **0.4744%, 0.7508%, 0.9959%, 1.2261%** for zero through three errors.
- Exhaustively enumerated F2’s honest rule-text space and applied the actual historical exclusion helper to the four books, obtaining **83 remaining texts**.
- Checked E1c’s sender-local verifier and accepted-ID/fallback paths against `stages.py` and `protocol.py`.
- No files were changed and no model or heavy run was launched. Git status was unchanged from the initial inspection.

**Files actually opened**

All paths below are relative to the repository root:

- `v6/e1d/DRAFT_PLAN.md`
- `v6/e1d/tools/measure_dict_artifact.py`
- `v6/e1d/measurements/dict_artifact_e1c_t1.json`
- `v6/e1d/reviews/gpt_E1d_draft_r2.md`
- `v6/e1d/reviews/grok_E1d_draft_r1.md`
- `v6/e1c/PREREG_E1c.md`
- `v6/e1c/T1_REPORT.md`
- `v6/e1c/e1c/analysis.py`
- `v6/e1c/e1c/stages.py`
- `v6/e1c/e1c/book.py`
- `v6/e1c/tools/build_book.py`
- `v6/e1c/tools/check_freeze.py`
- `v6/e1c/tools/code_hash.py`
- `v6/e1c/data/book_dev.json`
- `v6/e1c/data/book_test.json`
- `v6/e1b/e1b/protocol.py`
- `v6/e1b/e1b/cases.py`
- `v6/e1b/data/cases_e1b.json`
- `v6/e1b/data/cases_e1b_a9.json`

tokens used: 56,083
