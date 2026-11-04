# Glyph / GPT project continuity

Updated 2026-10-15. This file contains experiment facts already recorded in this
public repository. It is not a private chat transcript or a merged GPT session.

## Sources

Repository: https://github.com/devamped1337/glyph-alphabet-experiments

The latest project snapshot read while this handoff was prepared was
`1896085e898c09dbf5ba45bb9e83b2f9c3a23990`. Its round-6b artifacts were pinned to
`6c51e411816a2c5a9a5a6abd4c24d68bc018c6dc`.

Read the current pinned request before a review. Sources under `v6/e1b/` include
`REVIEW_ROUND.md`, `PREREG_E1b.md`, `B3R_REPORT.md`, `results/B3r/summary.json`,
and `reviews/gpt_B3r_r2.md`.

## Primary outcome

**A9 B3: POC FAILED.** Both directions failed the frozen A9 success criterion.

- Qwen sender to Falcon receiver: selection 51/60, end-to-end ID answers
  203/240 versus prose 240/240. With correct picks, 203/204 were correct.
  Nine wrong picks explain 36 of 37 errors, not every error.
- Falcon sender to Qwen receiver: the frozen parser rejected all sender replies.
  There were zero ID receiver calls. This is a pipeline failure, not a
  measurement of receiver accuracy given valid IDs.

## Secondary A10 diagnostic

- The revised parser reuses 60 archived Falcon replies. No new sender call was
  made. The earlier exploratory re-parse and the TEST data had already been seen.
- B3f format smoke: 24/24 valid replies per model; previous accepted answers
  unchanged. These views are not 24 independent entries.
- B3r: selection 56/60; Qwen ID answers 223/240 versus reused prose 238/240.
- ID minus prose: -0.0625, 95% CI [-0.13333, -0.00417].
- **INCONCLUSIVE** under frozen A1.2: the CI crosses the -0.05 margin.
  Non-inferiority was not established; the point estimate alone does not decide
  the label. A9 remains the primary failure result.
- Bootstrap clusters over 60 entries, not 240 independent items. Correct-pick
  and family analyses are descriptive. Reused prose introduces a cross-session
  qualification not captured by the CI.
- Reported savings for this direction are ~89% payload, ~59% whole exchange,
  with dictionary setup separate and break-even ~235 messages.
- Reported total GPU use is ~6.52 of 12 hours. This file authorizes no new run.
- The recorded CLI GPT round-6b r2 verdict is ACCEPT, no required edits. Importing
  it does not constitute a fresh independent review or require agreement.

## Review discipline

Send the exact question, pinned commit, relevant files, frozen rules, prior
objections, current primary/secondary status, and requested verdict format.
Verify fingerprints and complete row coverage where relevant. Distinguish
pipeline failure from model-conditional accuracy. Keep the TII credit line on
published Falcon results.

Do not treat quoted old approvals as new launch authorization. Each experiment
stage retains its existing owner-approval requirements. This bridge changes no
experimental protocol, frozen artifact, result, or approval.

## Continuity boundaries

Glyph's CLI reviewer and the originating ChatGPT conversation are separate
sessions. An imported context packet and an explicit saved session UUID provide
working continuity; they do not make either surface able to read the other
surface's complete transcript automatically.

Keep private context, CLI state, credentials, and detailed event logs outside
this public repository. Use a private repository for broader conversation
handoffs. No automatic polling or background chat wake-up is configured here.
