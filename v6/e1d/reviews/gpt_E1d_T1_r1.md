# GPT review: E1d T1-E1d result, round 1

Reviewed commit `0c6267f` (v6/e1d/T1_E1d_REPORT.md, v6/e1d/results/T1-E1d/), Codex CLI read-only, 2026-10-21 AEDT.

SUCCESS follows from the frozen gates in both directions. I reproduced all derived summary fields from the raw rows; the lifecycle also matches after JSON normalization of Python tuples to arrays. The reporting-only gzip results reproduce exactly. No files were modified.

The gate results are correct:

| Gate | Qwen→Falcon | Falcon→Qwen |
|---|---:|---:|
| Completeness | Pass | Pass |
| G1 accuracy CI lower | 0.00 percentage points | +0.625 percentage points |
| G2 coverage | 139/160 = 86.875% | 151/160 = 94.375% |
| G3 lifetime saving lower | 33.303% | 38.294% |

Receiver counts, selection statistics, per-pair figures, E1c old-pair references, byte counts, artifact measurements, secondary savings, latencies, and charged compute check out. Sensitivity reporting appropriately discloses failures at lower traffic and conditions the claim on W.

1. **Non-blocking — minimum-traffic figures have the wrong unit.** [Report line 46](/workspace/glyph-repo/v6/e1d/T1_E1d_REPORT.md:46) labels 66,600 and 54,000 as messages **per direction**. The frozen function returns **aggregate traffic across both directions**, as specified in §5.3. These correspond to **33,300 and 27,000 per direction**, respectively. Also identify them as minima on the registered 1,800-message aggregate grid.

2. **Non-blocking — W_copy’s mechanism is described incorrectly.** [Report line 41](/workspace/glyph-repo/v6/e1d/T1_E1d_REPORT.md:41) suggests whole-dictionary replacement updates. The calculation uses full copies for initial holders and replacement joiners, plus **two incremental deltas**, each with an 11,054 B body and its manifest. The reported F and savings are correct; revise the description.

3. **Non-blocking — qualify the compressed-sync conclusion explicitly.** The gzip arithmetic is correct and clearly separated from the gates. Add that future full artifacts and deltas are **estimated using v1’s measured compression ratio**, rather than individually compressed and measured. Thus the 21.6%/24.3% lower bounds remain conditional on that scaling assumption.

4. **Non-blocking — complete the requested per-pair safety reporting.** §10 requests wrong accepts and CP95 upper bounds per pair. These exist in `summary.json` but are omitted from the report table. All counts are zero; the upper bounds are **10.88%**, **9.50%**, and **11.73%** for baker/porter, potter/bearer, and tanner/loader, respectively, in either direction. Including them would reinforce the small-denominator caveat.

No blocking concerns. These corrections affect reporting, not the frozen SUCCESS verdict.

**Verdict: ACCEPT WITH CORRECTIONS**
