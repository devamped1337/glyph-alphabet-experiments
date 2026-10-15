# GPT review: E1c T1 result r1

Pinned commit 8a9a819 (REVIEW_ROUND at 9b3c260). Reply verbatim:

Verdict on the report: ACCEPT.

Based on the pasted code, artifacts and recomputation output, the analysis and frozen verdict are correct. This is a review of that evidence, not an independent execution against the raw files.

1. NOT MET is correct.

Both directions pass criteria 1–3 and fail criterion 4. The unrounded break-even values are 1,142.0213 and 1,113.8236 messages, both above 1,000. Completeness passes under the frozen checks, so NOT MET, rather than INCOMPLETE, is the appropriate verdict.

2. The computations follow §5–§6.

The bootstrap pairs outcomes within entries, resamples entries within each family, preserves family sizes, and averages over entries. The frozen implementation uses 2,000 resamples and the specified order statistics s[50] and s[1949]. Both lower bounds exceed −0.05.

Coverage uses accepted entries divided by 240. Payload saving includes fallback prose. Dictionary cost counts the unique union of assigned entries and neighbours, using the frozen UTF-8 framing. Break-even divides that cost by mean payload saving per case exchange. Payload-plus-case saving is correctly reported separately.

The displayed break-even integers are rounded continuous ratios. They do not affect the verdict.

3. The recomputation is adequate, with a limited qualification.

Exact reproduction using the frozen function checks reproducibility; the separate arithmetic and numpy bootstrap provide useful corroboration. The different bootstrap RNG, resample count and percentile convention mean its intervals are a sensitivity check, not an exact replication of the registered CI. The report treats them appropriately.

The separate completeness check is weaker than the frozen check: total unique-row counts and valid gold values alone do not establish the exact assignment, cases and arms. However, the frozen function explicitly checks that exact set and reports COMPLETE. This limits the independence of the completeness corroboration; it does not undermine the reported result.

4. The wording is fair overall.

The report leads with failure, identifies the failed criterion, and does not substitute favourable subsets for the registered verdict.

“Dictionary cost” is reasonable shorthand for the failed amortization criterion, although break-even depends jointly on dictionary size and per-message saving. The D2 caveat and acknowledgment of the earlier reporting omission are fair: a dictionary for 10 receiver entries supports a different amortization calculation from TEST’s 240-entry dictionary. The pasted evidence does not independently establish the historical D2 figures or forum wording, but the explanation is internally coherent.

“At least as accurate” is supported descriptively by the observed results; it should not be read as a population-level superiority claim.

5. Nothing required by the supplied §5–§6 is missing.

The report includes the verdict, per-criterion results in both directions, CI method and labels, completeness evidence, and every listed secondary measure. Requirements elsewhere in the unpasted PREREG cannot be assessed here.

Complete list of required changes: None.

Optional improvements:

[non-blocking] Describe the separate completeness check as corroboration, or strengthen it to assert the exact expected row set and family labels.

[non-blocking] Replace “The ID arm was at least as accurate” with “Observed hybrid accuracy was at least as high as prose accuracy” to identify the evaluated arm and keep the claim explicitly descriptive.
