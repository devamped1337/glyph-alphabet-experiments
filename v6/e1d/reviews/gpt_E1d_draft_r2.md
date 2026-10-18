# GPT review of E1d DRAFT_PLAN, round 2 (real files, commit d5f4bdb), 2026-10-19

**Verdict: needs changes.** The lifetime criterion is a reasonable next experiment, but its workload, accounting boundary and confidence procedure need precise definitions before freeze.

I reviewed commit `d5f4bdb367222117c7a2372daeea47c327f6b1b5`. The draft correctly states E1c’s outcome: accuracy, coverage and payload-saving gates passed; only break-even failed. Independently reconstructing bytes from the TEST book and raw selection/exchange rows reproduced:

| Direction | Prose payload | Hybrid payload | Dictionary | Break-even |
|---|---:|---:|---:|---:|
| Qwen→Falcon | 167,652 B | 28,136 B | 165,969 B | 1,142.021 messages |
| Falcon→Qwen | 167,652 B | 24,604 B | 165,969 B | 1,113.824 messages |

**I found no arithmetic error in E1c’s payload or break-even calculation under its registered accounting rules.** The issues below concern what E1d would inherit or leave undefined.

1. **High — “total bytes” is not yet a defined endpoint.**  
   References: [DRAFT_PLAN.md:27](/workspace/glyph-repo/v6/e1d/DRAFT_PLAN.md:27), [protocol.py:78](/workspace/glyph-repo/v6/e1b/e1b/protocol.py:78), [PREREG_E1c.md:83](/workspace/glyph-repo/v6/e1c/PREREG_E1c.md:83).

   E1c’s primary byte measure counted only the rule payload. Its separately reported `whole_exchange_bytes` adds case text, but does not represent a complete serialized transport exchange. E1d’s primary formula omits case text and per-conversation setup despite naming setup later. Common bytes cancel from the absolute saving but **do not cancel from its percentage denominator**.

   **Fix:** freeze one primary byte boundary and a serializer. Include case text and applicable framing/setup in both arms, or explicitly call the endpoint “rule-payload plus dictionary bytes.” State whether responses and transport overhead fall within that boundary. Keep disk storage separate from transmitted bytes.

2. **High — dictionary cost is a constructed subset cost, not the size of the dictionary object E1c uses.**  
   References: [analysis.py:89](/workspace/glyph-repo/v6/e1c/e1c/analysis.py:89), [stages.py:151](/workspace/glyph-repo/v6/e1c/e1c/stages.py:151), [protocol.py:19](/workspace/glyph-repo/v6/e1b/e1b/protocol.py:19), [DRAFT_PLAN.md:35](/workspace/glyph-repo/v6/e1d/DRAFT_PLAN.md:35).

   `dict_bytes` deduplicates the assigned entries and their neighbours and charges a hypothetical UTF-8 line representation. For T1 that is **960 entries, 165,969 B**. However, `Dictionary(B)` uses the book’s published membership: **1,960 distinct entries**, whose same line representation costs **373,936 B**.

   The smaller cost matches E1c’s registered definition; it is not an arithmetic bug. But E1d cannot treat it as measured distribution traffic while distributing the larger object or the full book.

   **Fix:** construct the actual minimal distribution artifact, freeze its membership and encoding, round-trip it through the receiver loader, and count its exact bytes. Include whatever manifest or metadata that loader requires. Do not substitute the full research book, which also contains evaluation material.

3. **High — the lifetime bootstrap is underspecified and cannot reuse E1c’s statistic directly.**  
   References: [DRAFT_PLAN.md:30](/workspace/glyph-repo/v6/e1d/DRAFT_PLAN.md:30), [analysis.py:58](/workspace/glyph-repo/v6/e1c/e1c/analysis.py:58), [analysis.py:110](/workspace/glyph-repo/v6/e1c/e1c/analysis.py:110).

   E1c bootstraps a mean accuracy difference and returns a **two-sided** 95% interval. It has no byte-saving bootstrap. E1d needs a ratio of workload totals, with fixed dictionary costs retained in every replicate. Averaging message-level saving percentages would estimate a different quantity.

   **Fix:** specify each replicate as  
   `S* = 1 − (fixed costs under W + weighted hybrid message costs*) / weighted prose message costs*`.  
   Resample paired entry clusters within families, retaining their cases, if that is the declared sampling model. Specify weights, seed, resample count and the one-sided fifth-percentile convention. If W introduces user/conversation dependence, model or resample that dependence too. State that the interval is conditional on W; it does not validate the forecast.

4. **High — W specifies volume, but not enough of the workload distribution or dictionary lifecycle.**  
   References: [DRAFT_PLAN.md:25](/workspace/glyph-repo/v6/e1d/DRAFT_PLAN.md:25), [T1_REPORT.md:73](/workspace/glyph-repo/v6/e1c/T1_REPORT.md:73).

   Counts alone do not determine savings. Family/rule frequencies, repeated-rule reuse, dictionary versions and fallback behaviour matter. E1c’s D2 cost used only ten receiver entries and their neighbours; T1 used 240. That explains why D2 break-even was not predictive.

   **Fix:** declare the horizon, traffic mix, rule reuse, recipient churn, cache assumptions, initial provisioning of senders and receivers, and full-versus-delta updates. Specify version-mismatch behaviour and resulting fallback traffic. Measure distribution/update artifacts at the intended deployment dictionary scale, even if receiver accuracy is piloted on a smaller subset. Add lower-traffic and higher-churn sensitivities. If no independent forecast exists, describe W as a scenario.

5. **High — verifier location is inconsistent with “carried over unchanged”; failed-ID costs depend on that location.**  
   References: [DRAFT_PLAN.md:16](/workspace/glyph-repo/v6/e1d/DRAFT_PLAN.md:16), [DRAFT_PLAN.md:52](/workspace/glyph-repo/v6/e1d/DRAFT_PLAN.md:52), [PREREG_E1c.md:46](/workspace/glyph-repo/v6/e1c/PREREG_E1c.md:46), [stages.py:160](/workspace/glyph-repo/v6/e1c/e1c/stages.py:160).

   E1c’s verifier is a stateless call to the **sender model**, using the original prose locally. Rejected picks never cross the registered sender→receiver boundary; fallback sends prose alone. Thus adding failed-ID traffic to unchanged E1c would overcount. Moving this verifier to the receiver would require conveying the original prose or defining a different verification mechanism.

   **Fix:** freeze the topology. For unchanged E1c, record verification network traffic as zero and compute cost separately. For receiver-side or remote verification, count all required inputs, outputs, failed attempts and fallback, then requalify the changed protocol in development.

6. **High — a 1% CP upper-bound gate is infeasible at the inherited TEST size.**  
   References: [DRAFT_PLAN.md:21](/workspace/glyph-repo/v6/e1d/DRAFT_PLAN.md:21), [DRAFT_PLAN.md:53](/workspace/glyph-repo/v6/e1d/DRAFT_PLAN.md:53), [analysis.py:121](/workspace/glyph-repo/v6/e1c/e1c/analysis.py:121).

   E1c observed zero wrong accepts out of 240 selections per direction, giving a one-sided CP95 upper bound of approximately **1.24%**. Zero events requires at least **299 independent selections per direction** to get below 1%. The 960 case exchanges are not 960 independent selections. “All picks” and “wrong picks” also give very different denominators.

   **Fix:** freeze the denominator and whether the gate concerns the observed rate or its upper bound. If retaining CP95 ≤1%, resize TEST and compute accordingly, with the binomial sampling assumption disclosed. Keep the descriptive 24/24 wrong-picks-caught result separate.

7. **High — TEST reuse and smaller-dictionary selection must be resolved before confirmation.**  
   References: [DRAFT_PLAN.md:50](/workspace/glyph-repo/v6/e1d/DRAFT_PLAN.md:50), [DRAFT_PLAN.md:55](/workspace/glyph-repo/v6/e1d/DRAFT_PLAN.md:55), [book.py:47](/workspace/glyph-repo/v6/e1c/e1c/book.py:47).

   E1c TEST has already informed this experiment. Reusing it can support a disclosed reanalysis, but not a fresh confirmation. The inherited freshness machinery only lists the E1b books and E1c dev; it would not automatically exclude E1c TEST when adapted for E1d.

   **Fix:** use development data for arm selection, freeze the primary arm, then generate fresh confirmation data with explicit historical exclusions. Check generator feasibility first. Specify retrieval and fallback for a smaller dictionary, especially the “no neighbours” arm, which changes the four-candidate setup.

8. **Medium — frozen E1c verdict logic would still enforce the old endpoint.**  
   References: [DRAFT_PLAN.md:22](/workspace/glyph-repo/v6/e1d/DRAFT_PLAN.md:22), [analysis.py:113](/workspace/glyph-repo/v6/e1c/e1c/analysis.py:113), [stages.py:281](/workspace/glyph-repo/v6/e1c/e1c/stages.py:281), [check_freeze.py:9](/workspace/glyph-repo/v6/e1c/tools/check_freeze.py:9).

   Reusing the supervisor is reasonable, but E1c’s success calculation still requires ≥30% payload saving and ≤1,000-message break-even; wrong accepts are descriptive. Freeze tools also hardcode E1c paths. The code hash omits the `tools` scripts themselves.

   **Fix:** implement an explicit E1d gate table and verdict, preserve completeness checks, adapt freeze paths, and pin the workload, analysis and distribution artifacts. Add focused checks for fixed costs in every bootstrap replicate, dictionary-copy counts, updates, and both-direction gate enforcement.

The earlier informal notes remain useful, particularly on workload justification and fixed costs in resampling. Their compressed-prose baseline suggestion is appropriate if the intended claim concerns practical deployment efficiency; otherwise, explicitly limit the comparison to the specified uncompressed prose protocol. This is a claim-scope choice, not an E1c accounting error.

**Files actually opened:** all six named documents/files, including the complete E1d draft and earlier notes; every Python file under `v6/e1c/e1c/` and `v6/e1c/tools/`; the E1c TEST book, T1 summary, both T1 selection files and both exchange files; plus E1b’s `protocol.py` and relevant message-rendering code in `cases.py`. No files were changed, and no model or experimental run was launched.
tokens used
60,171
