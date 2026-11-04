# GPT (Codex CLI, read-only) review r1 of E1e byte-audit plan draft, inflation tool and dev corpus builder

Reviewed checkout: commit 7cff8c3. Date: 2026-10-21 (AEDT). Verbatim response below. All six findings were addressed in the following commit (plan sections 2, 4-9, inflation tool, SPEC/schema prov values, sanitiser with enforced scan, corpus rebuilt).

Reviewed `7cff8c3`; read all requested files and reproduced the diagnostic JSON exactly. **Fixes are needed before freeze review.**

1. **Inflation interpretation needs correction.** In [plan §8](/workspace/e1e-gpt/v6/e1e/BYTE_AUDIT_PLAN_DRAFT.md:67), the 12-hex and 8-hex arithmetic is correct. The “0-hex” calculation removes 128 hex characters but retains both `sha256:` prefixes: 14 bytes remain. Removing those too gives **19/19 larger than message bytes, but 9/19 larger than raw envelopes**, rather than 13/19. Also, “escaped-JSON framing dominates” overstates the evidence: hex digits account for **2,432 of the 3,719 excess reference bytes** at full length. Remaining metadata still causes inflation, but the diagnostic does not isolate escaping from keys, IDs, versions and args. The +46% raw-envelope figure is correct.

2. **Dictionary-failure rule contradicts itself.** [§7](/workspace/e1e-gpt/v6/e1e/BYTE_AUDIT_PLAN_DRAFT.md:60) says any training exception makes baseline 4 “not trainable,” then says this happens if *every size* fails. Specify candidate/fold failure handling, eligibility, scoring and tie-breaking, then final full-dev training failure. These choices must be fixed before held-out use.

3. **Accounting omits control traffic and stream completion.** [§§5–6](/workspace/e1e-gpt/v6/e1e/BYTE_AUDIT_PLAN_DRAFT.md:41) charge artifacts and message frames, but omit receiver declarations and the proposed epoch/index negotiation. `Link.totals()` does not count declarations. Persistent streams also need a termination rule: charge final frame-closing bytes when finishing, or explicitly declare abandonment without completion. Define the distribution topology so sender provisioning and maintainer upload are counted consistently.

4. **Compression failure tests promise detection the settings do not guarantee.** [§9](/workspace/e1e-gpt/v6/e1e/BYTE_AUDIT_PLAN_DRAFT.md:82) expects corrupt/truncated frames to cause decode errors, while checksums are disabled; corruption can decode successfully to wrong bytes. With dictionary IDs suppressed, wrong-dictionary detection is likewise not guaranteed. Specify dictionary identity negotiation and frame-completion/integrity checks, and distinguish runtime detection from the audit’s offline byte-exact oracle.

5. **Provenance rules need an implementation bridge.** Source-based exclusion and whole-workflow splitting are sound. However, [the spec](/workspace/e1e-gpt/v6/e1e/SPEC_E1E_REPO_1.md:24) and schema currently accept only `prov="synthetic"`. Entries derived from Glyph-own or real development messages cannot truthfully use that value. Revise the accepted provenance schema and preserve source lineage before building those artifacts.

6. **The sanitiser has reproducible gaps.** [Its substitutions](/workspace/e1e-gpt/v6/e1e/tools/build_glyph_own_dev.py:35) leave generic `Authorization: Bearer …` credentials and `token=…` values unchanged unless they match a listed prefix. Operator-name matching is case-sensitive; uppercase hashes and `/Users/...` paths also survive. There is no enforced post-build scan before writing records marked `sanitised=True`. Add credential-context redaction and a failing validation step. My targeted checks found no corresponding leaks in the committed corpus; this is a demonstrated builder gap, not a confirmed disclosure.

The raw/gzip/zstd/reference baseline selection and the development-only exclusion are otherwise reasonable. No independent numerical error surfaced in the inflation tool’s current-corpus results.

**Verdict: needs fixes first, then Grok review toward a freeze.**
