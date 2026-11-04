# GPT code review of E1f build, round 1 (verbatim, at 5539d39)

CHANGES REQUESTED

Reviewed local HEAD 5539d391e286d8dee55653f95093bf56c7ec1491, with the expected repository remote. The reviewed source files have no working-tree differences from that commit. No files were modified.

I reproduced 86 passing compact/curation tests using unittest. I could not independently reproduce all 171 tests: this environment lacks pytest and zstandard.

The dev failures are not review blockers. They remain in-sample screening results, not held-out evidence, and do not trigger the held-out retirement rule.

Blocking items

1. The lazy greedy implementation is not generally equivalent to §4.

curation.py:499–552 assumes gains only decrease after overlap removal. That is false when an occurrence contributes negatively; the implementation explicitly retains negative contributions.

A concrete arithmetic example using _gain: two occurrences contributing +1 each and one contributing −1 give G=1 before entry cost. Blocking the negative occurrence raises that to G=2. These contributions are possible for word templates because argument-length varints grow with argument size.

Consequently, initially discarded candidates can become profitable, and heap scores can cease to be upper bounds. Recompute all remaining marginal gains after each selection, or supply a valid equivalent algorithm. Add a regression comparing the selection sequence with full recomputation.

2. Append-only publication and epoch scheduling require a normative amendment.

build_repository_chain does not publish the independently selected repository specified for each scheduled version. It retains previously selected entries, can exceed C in the published union, suppresses unchanged/empty publications, skips unused schedule versions, and renumbers published snapshots.

These are material changes to dictionary contents, sync costs, ordinal assignments, retention transitions, and the meaning of V. Equal treatment across arms does not make them equivalent to the approved procedure.

I accept append-only publication as a reasonable resolution of the deletion conflict, but it must be specified explicitly, including stable IDs, union limits, overflow order, scheduled-to-published version mapping, and unchanged/empty snapshots.

3. The candidate cap does not bound candidate-generation resources.

compact.py:401–418 materializes and sorts every prefiltered pair before enforcing the 4,096-candidate cap. A valid snapshot containing 4,096 literal entries matching a 65,536-character message can create roughly 268 million pairs before the cap takes effect.

Template lookahead/fullmatch also runs outside the E1E matcher’s 20,000-step budget; ambiguous-looking word patterns can incur substantial backtracking before that bounded matcher runs.

Preserve the specified enumeration and endpoint results while generating pairs incrementally and using a bounded necessary-condition prefilter. The existing output cap alone is insufficient.

4. Joiner accounting omits subsequent updates.

repo_artifact_sync charges each joiner its joining snapshot but no later deltas. dict_rebuild_sync likewise omits later dictionary downloads for joiners. Participants remain a fixed multiplier throughout.

For joiners who remain participants, charge every subsequent publication. Apply the same lifecycle to repository artifacts and rebuilt dictionaries. If joiners are intentionally one-shot snapshot downloads, that needs an explicit scenario amendment.

This does not affect the zero-joiner primary scenario.

5. The oversized fallback runner has an unstated 1 MiB ceiling.

replay_arms verifies oversized zstd fallback with codec3.decompress(data), whose default maximum output is 1 MiB. A compressible message larger than that selects zstd and then fails verification, despite §5.1 providing fallback for oversized messages without that ceiling.

Verify against an appropriate bound derived from the original message length. Also replace the unconditional success for raw fallback with an actual byte-exact check.

6. Required reporting is incomplete.

The screening report does not persist the required per-entry source-conversation lineage manifest. Picks contain conversation indexes internally, but the output retains only aggregate chain information.

Encoder cap statistics are also dropped before reporting. The claimed break-even ingredients are not exposed by scenario_totals or the screening report, and actual break-even results are absent. Trailing skipped schedule versions disappear from build_repository_chain’s returned records.

Provide the lineage manifest privately, aggregate cap/verification/fallback statistics, preserve all schedule metadata, and report break-even results or explicit undefined cases.

7. Eligible-message baseline selection has changed.

zstd_or_raw adds raw-envelope selection to native arms 3/4/4b/4b-delta for eligible messages. §5.1 specifies that selection for oversized fallback; it does not redefine those native baselines.

Either restore the named baseline behavior or explicitly amend their eligible-message send rule. “Usually zstd wins” is not sufficient for conformance.

Checks that passed inspection

Canonical unsigned LEB128 widths, shortest-form checks, u32/u64 limits, zigzag mapping and integer-domain checks are consistent with the specified wire rules.

Ordinals follow sorted IDs. CompactReceiver retains current and previous snapshots, and stale epochs cannot silently resolve against the current ordinal table. Decoder verification protects encoder output.

Message/control framing prefixes are charged across arms. Arms 4b and 4b-delta share message encoding; 4b-delta and arm 7 share artifact serialization and sync accounting. Arm 6 additionally pays for its trained dictionary.

Declarations are charged consistently across repository arms in the runner, including the empty repository.

I found no held-out/incoming data read in the reviewed screening path. It reads only the two configured dev corpora and guards incoming path components. This establishes what the code does, not a historical audit of earlier executions. Prefix occurrence caches scan later dev text and subsequently filter by prefix; I found no resulting future-prefix contribution to the selected occurrences.

Build-note rulings

1. ACCEPT. Empty payload → E_SCHEMA is reasonable; document it.

2. REQUIRED CHANGE. Amend precedence to sequential parsing, with structural limits and reconstructed-size precedence stated explicitly. I accept the implemented sequential interpretation; the current wording is too broad.

3. ACCEPT. Add the listed error-code assignments to the normative text.

4. REQUIRED CHANGE to the note. All-LIT compact is not always available: a 65,536-byte unmatched message produces an oversized compact frame and falls back to raw. I reproduced this. Qualify the claimed universal saving. The framing-only saving itself needs no algorithm amendment.

5. REQUIRED CHANGE. Explicitly authorize whole-message matching for int/word templates ending in a parameter. The draft explicitly grants that exception to text templates only.

6. REQUIRED CHANGE. Resolve blocker 3 and report the statistics. Define “unconsidered pairs” precisely; it is not a count of proven additional candidates.

7. ACCEPT. Ignoring LIT overhead follows the specified greedy score. Comparing against all-LIT would be an optional algorithm amendment, not a conformance fix.

8. ACCEPT. State that epoch zero is invalid and the empty repository is not retained as a usable compact epoch.

9. ACCEPT the missing-timestamp/hash-order convention. Document the corpus-wide rule for partially missing timestamps.

10. REQUIRED CHANGE. Freeze the intended definition/orientation of maximal common substrings and whether L applies before or after UTF-8 trimming. The current implementation can retain a result below L after trimming.

11. REQUIRED CHANGE. Fix blocker 1. Also specify occurrence enumeration and self-overlap handling; the present “gains only shrink” justification is invalid.

12. ACCEPT. Excluding oversized messages from mining is sensible; make that exclusion explicit.

13. REQUIRED CHANGE. Amend §4 as described in blocker 2. Accept the stable-ID and append-only choices once specified.

14. ACCEPT. Freeze the six-character provisional ID, v=1 record calculation and comma exclusion as the exact entrycost definition.

15a. ACCEPT. Leading/trailing empty separator positions distinguish layouts correctly.
15b. REQUIRED CHANGE to wording. Replace the ineffective boundary sentence with an actionable rule or remove it.
15c. ACCEPT.
15d. ACCEPT. Mining a template that scores poorly under actual encoder eligibility is not inherently inconsistent. No additional amendment is needed beyond resolving note 5.

16. REQUIRED CHANGE. Specify tuning participants=2, joiners=0 and eligible-only scoring. These affect the frozen objective and must be normative.

17. ACCEPT. An E1f-specific strict constructor preserves E1E compatibility. Clarify that the explicit-provenance requirement applies to E1f construction paths.

18. ACCEPT. This follows the positive-epoch rule; disclose the empty-repository discontinuity.

19. REQUIRED CHANGE. Resolve blocker 7.

20. ACCEPT the conversation/direction link model and equal repository-arm declarations; the inherited audit plan already requires conversation-start links. Shared receiver state is an acceptable synchronized-replay model. Joiner lifecycle accounting still needs blocker 4 resolved.

21. REQUIRED CHANGE. Resolve scheduled versus published versions in the amendment for blocker 2.

22. REQUIRED CHANGE. Charge subsequent updates to continuing joiners. The distinct-artifact upload policy and quartile indexes are otherwise acceptable.

23. REQUIRED CHANGE. Undefined break-even against identical sync policies is acceptable, but the required report cannot be replaced by ingredients that are not actually emitted.

24. ACCEPT as a disclosed dev-only convention. Include framing bytes when selecting by charged traffic, and freeze the dictionary-selection rule before held-out use.

25. ACCEPT. Add the V=1, all-dev, zero-joiner repository and actual REF-span coverage definition to §7.

26. REQUIRED CHANGE. Specify the heuristic exactly and qualify its assumptions: two bytes per message assumes a one-byte epoch and compact encoding; two bytes per LIT understates longer length varints. Keep it explicitly approximate, including empty-repository/raw cases.

27. ACCEPT. The in-sample replay is clearly labelled and supplies no held-out evidence.

28a. ACCEPT. Literal residue is uncompressed by design; 7z remains deferred.
28b. ACCEPT. Equal declaration charges cancel in the principal repository-arm comparisons. This is a declared topology cost, not an entry benefit. No separate amendment is needed beyond making the accounting model explicit.
28c. ACCEPT as a dev observation.
28d. ACCEPT as a dev observation.

Suggestions, nonblocking

Add an optional all-LIT comparator only through a separately reviewed encoder amendment. Keep framing-only savings distinct from savings attributable to entries.

After the blockers and amendments are resolved, regenerate the dev reports with the revised code hash. Do not treat the present screening failure as a reason to relax the coverage threshold, change the grid, or introduce 7z into this experiment.
