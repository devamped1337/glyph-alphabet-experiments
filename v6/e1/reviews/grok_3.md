# Review grok_3: v6 E1 results (summary relayed by the user)

Relayed 2026-10-12 (AEDT). This is a summary of Grok's points as relayed by the user, not a verbatim transcript.

- The write-up matches the plan and does not over-claim.
- The gate failed on both calibration and TEST.
- The oracle-ID scope is stated. Caching is labelled repeat-request only, and the FLOPs problem is flagged.
- Qwen 0.640 vs prose 0.642: inconclusive.
- Smol: id_expanded is ahead of prose, with a CI that excludes zero.
- Both models do far better than compact, id_raw and placebo.
- Unknown-ID abstention is uneven between the models.
- The tasks are hard for models of this size.
- "Can be left as the locked E1 result."

## Note (added when saving)

Some of Grok's wording conflicts with GPT's review (`gpt_2.md`):
- "End-to-end": GPT says these are oracle-ID receiver accuracies with the gate bypassed.
- "No worse than prose for Qwen": GPT says the CI crosses the ±5 margin, so it's inconclusive.

Grok also did not address GPT's new findings: the overlap with calibration questions, the cache nondeterminism and the presentation confound. GPT's corrections take precedence where they have been verified against the data. See the CORRECTIONS section in `RESULTS_E1.md`.
