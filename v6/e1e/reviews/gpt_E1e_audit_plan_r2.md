# GPT (Codex CLI, read-only) re-check r2 of E1e byte-audit plan draft

Reviewed checkout: commit 5518bd4. Date: 2026-10-21 (AEDT). Verbatim response below. The remaining sanitiser gap (quoted credential keys) was fixed in the following commit: quoted/colon credential keys are redacted and the enforced scan now rejects any surviving credential-context value; the rebuilt corpus texts are unchanged (the only difference is the newly committed review file gpt_E1e_audit_plan_r1.md, now 188 msgs / 98 convs). This fix has not been re-reviewed by GPT (one re-check only).

Read all eight files in full at `5518bd4`.

1. **Confirmed:** diagnostic reproduces exactly: 9/19 exceed raw envelopes without digest values; 2,432/3,719-byte breakdown and §8 wording corrected.
2. **Confirmed:** §7 specifies eligibility, conversation-grouped folds, failure handling, dictionary-inclusive scoring, tie-break and final-training failure.
3. **Confirmed:** topology, control traffic, missing declaration accounting and stream termination are explicit.
4. **Confirmed:** offline byte-exact verification is separated from runtime detection, with a checksum/dictionary-ID secondary run.
5. **Confirmed:** SPEC/schema accept all three provenance classes; build-manifest lineage is required.
6. **Partially fixed:** the named examples are redacted and the scan runs before writing. The rebuilt corpus has 187 messages/97 conversations and passes that scan. **Remaining reproducible gap:** `{"token": "abcdefgh", "password": "hunter2"}` survives sanitisation unchanged and passes `scan()`. Support quoted credential keys and reject surviving credential-context values.

**Verdict: needs fixes before Grok review toward a freeze.**
