# GPT review of E1f proposal, round 1 (verbatim, at 1a7323f)

CHANGES REQUESTED

Review round 1 of 2, for v6/e1e/E1F_PROPOSAL_DRAFT.md at 1a7323f. No files modified. The experiment is worth pursuing, but the wire specification and interpretation of sync savings need tightening before implementation or freeze.

Q1 — Expectation and sync accounting (§§1–2, 4–5)

The expectation of similar per-message costs is reasonable, although templates with parameters may behave differently from literal dictionary matches.

Delta-versus-full-rebuild is a valid comparison under Amendment A1’s stipulated distribution policy. It is not an inherent advantage of repository IDs: a receiver can reconstruct a new raw-content zstd dictionary locally after receiving an entry delta. A1’s statement that zstd dictionaries “have no delta form” does not establish that full dictionary transmission is necessary.

Required changes:
- Describe any sync-only win explicitly as a win against A1’s full-rebuild distribution policy. Remove the claim that this is a structural advantage of refs.
- To support a broader claim about IDs, add a baseline where 4b receives the same repository deltas and constructs A1’s exact dictionary locally. Charge actual artifacts, declarations, initial syncs and joiner syncs. Alternatively, restrict the conclusion to A1 throughout.
- Specify the E1f retirement rule explicitly: which of 7/7z must beat which comparator, on which predeclared lifecycle scenario. The inherited A1 rule names only 5/6.
- Replace “loses by construction” (§1) with the observed result. Low coverage and expensive envelopes explain the loss but do not prove every possible result.

Q2 — Compact form (§3)

No: it is not yet precise enough for interoperable implementation or fuzzing.

Required changes:
- Assign numeric opcodes. Define unsigned varints exactly, including byte order, continuation bits, shortest encoding, maximum width/value and overflow rejection. Define zigzag and the permitted integer range.
- Prefer requiring version-delta = 0 for E1f. Otherwise define its sign, arithmetic, historical-body retention and how a joiner obtains older versions. The current snapshot contains current bodies, not historical bodies.
- Define argument order as entry.params order; inherit the existing template value constraints explicitly. Define lengths in bytes and ordinal indexing, including whether it starts at zero.
- Specify the transport frame boundary and charge its bytes consistently. “Segments until end” cannot distinguish a valid additional segment from “trailing bytes”; state exactly what is invalid.
- Set encoded-frame, decoded-message, segment-count and argument limits; reject excessive declared lengths before allocation. Define empty-message and non-UTF-8 fallback behavior.
- Bind ordinals to the declared snapshot and specify snapshot-change behavior. Without a per-message epoch, a stale ordinal can silently name a different valid entry. Require an ordered snapshot transition barrier or a charged epoch identifier.
- Either defer 7z or specify its complete grammar: compressed region, length boundaries, decompression settings, limits and discrimination from ordinary compact frames.
- Define deterministic segmented candidate search, overlap handling, budgets and tie-breaking. The existing whole-message prefix matcher does not specify this.
- Clarify that “raw” means the existing JSON raw envelope. Bare arbitrary message bytes cannot use the proposed first-byte discriminator safely.

The optional checksum run is useful, but neither an offline oracle nor a truncated checksum supplies snapshot synchronization.

Q3 — Curation and leakage (§§4, 6–7)

Dev-only mining and a frozen held-out pass are sound foundations. The procedure is not yet specified enough to establish reproducibility or freedom from favorable tuning.

Required changes:
- Define line blocks, n-gram runs, parameter mining, overlap counting, candidate ordering and deterministic ties.
- Define “saved bytes − entry cost”: reference costs, argument costs, marginal overlap savings, artifact serialization and lifecycle multiplicities all affect it. State the tuning objective and candidate parameter grid.
- Freeze the chronological dev-prefix schedule and the exact snapshot available at every replay event. No snapshot may contain material from a later prefix. Keep the held-out message set and order fixed across cadence scenarios.
- Predeclare cadence scenarios, participant/joiner schedules and the primary scenario; report every swept scenario rather than selecting the winner afterward.
- Define §6’s “ceiling” mathematically. A stop decision requires an optimistic upper bound on attainable savings, equivalently a lower bound on refs’ total cost, including sync. Approximate span costs do not establish that bound, and 4b’s cost is not uniquely attributable to individual spans.
- Freeze the coverage floor and its denominator before computing the gate. Report a failed gate as a dev-screening result, not evidence of held-out performance.

Describe this as deterministic dev-derived curation. It tests a useful proxy for maintainer curation, but does not directly test always-on agents’ ability to curate.

Q4 — Preferred resolutions for §8

1. Messages over 64 KiB: approve the proposed common fallback for an explicitly defined eligible-message comparison. Freeze its exact codec, settings, framing and tie rule. Report oversized counts, input bytes, fallback bytes and all-message totals separately. Distinguish this fallback policy from each named baseline’s native behavior.

2. Bodies over 16,384 code points: skip oversized candidates and count them for E1f. This preserves E1E-REPO/1 and avoids introducing an additional splitting algorithm. Enforce the limit during candidate generation and report excluded candidate coverage.

3. Provenance: require an explicit valid provenance value at every entry-construction call. Reject missing provenance. Preserve source-conversation lineage; mixed-source candidates need a declared policy rather than an arbitrary single-source label.

4. Baseline 6: retain BYTE_AUDIT_PLAN_DRAFT.md §8’s exact three-candidate selection. Its compression of the escaped envelope and use of baseline 4’s dictionary are already specified. Charge that dictionary’s distribution in addition to repository distribution. Keep 7z separately specified; changing baseline 6’s payload would create a new arm.

5. Fold seed: freeze the seed, hash algorithm, conversation-key encoding and fold assignment before splitting outside data. “e1e-diag-r1” is acceptable if chosen without inspecting alternative seeds’ results. Keep tuning folds and the final held-out split explicitly separate.

Required changes are listed above. They should be resolved in the revised draft for round 2.

Suggestions:
- Add tiny normative byte examples for literal-only, reference-only, mixed and malformed compact frames.
- Report message bytes and sync/control bytes separately, alongside totals and break-even update/join counts.
- Include a static-dictionary scenario to expose codec differences independently of update policy.

I do not approve freezing or running E1f as currently specified.
