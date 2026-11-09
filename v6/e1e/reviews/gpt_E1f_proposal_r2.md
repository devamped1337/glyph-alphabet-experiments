# GPT review of E1f proposal, round 2 (verbatim, at 549eab4)

CHANGES REQUESTED

Round 2 of 2, reviewed at 549eab4. No files modified. The remaining required changes below affect correctness or whether the experiment has a determinate interpretation.

Q1. Yes. Section 2 correctly limits full-rebuild sync claims and adds the relevant 4b-delta comparator. Section 6 gives arm 7 an explicit primary scenario and retirement rule. These resolve my Q1 changes.

Q2. Not yet. The byte examples are substantially correct, but the snapshot barrier cannot detect the stale frames it says to reject, and the framing limits are inconsistent.

Byte examples in §3.5:
- Literal-only correctly reconstructs “abc”.
- Reference-only correctly names ordinal 0 with no parameters.
- Mixed correctly reconstructs “hi” followed by ordinal 5’s output, provided ordinal 5 exists and has no parameters. State that fixture explicitly.
- The malformed examples are invalid as intended: empty segment list, truncated literal, over-width ordinal, noncanonical ordinal, unknown opcode, unknown discriminator.

Q3. Partly. Dev-only curation, provenance, the parameter grid, coverage floor and reporting commitments improve the design. The claimed optimistic bound is not established, and several choices still prevent deterministic reproduction.

Q4. Substantially yes. Skipping oversized entries, explicit provenance, preserving baseline 6 and freezing the fold hash match my preferred resolutions. The oversized-message policy is acceptable in principle, subject to the framing correction below and clarification of how the hash folds relate to the chronological split.

Required changes

1. Replace §3.3’s barrier with an observable synchronization protocol.

Ordered delivery in each direction does not order events across both directions. Counterexample: the sender emits an old-snapshot compact frame; the receiver sends a new declaration; the old frame arrives before that declaration reaches the sender. The receiver decodes using its new snapshot. If ordinal 0 exists in both snapshots but names different content, the frame can silently decode incorrectly.

Nothing in the frame identifies which snapshot the sender used, so the receiver cannot implement the specified E_STALE rejection. The offline oracle does not repair this protocol defect.

Either carry a charged epoch identifier or specify a drain/acknowledgment barrier: the sender stops old-snapshot sends and places an acknowledgment after all old frames on the ordered forward stream; the receiver retains the old decoding snapshot until that acknowledgment arrives. Specify the transition and charge its control bytes.

2. Make framing representable and unambiguous (§§3.1, 5.1).

A two-byte unsigned length cannot represent 65,536. Moreover, an eligible input of at most 65,536 bytes can produce a much larger raw envelope through JSON escaping or base64. Thus the oversized-input exception does not cover every oversized wire frame.

Define the length encoding, maximum wire size and prefix-width selection from the actual encoded frame length. If widths vary on one stream, define how the receiver recognizes the width before reading the payload. Apply the rule consistently to fallbacks and control traffic.

3. Remove or justify §7’s purported mathematical lower bound.

A measured compression ratio does not establish a universal 0.25-byte floor for uncovered bytes. Also, the text does not establish that its chosen covered spans and reference count lower-bound every encoding available to arm 7.

The simplest resolution is to retain this calculation as a dev heuristic and remove the statement that failure proves refs lose. Alternatively, supply a bound valid for every permitted compact segmentation and the raw-envelope alternative. A proven bound may relax costs downward; it cannot depend on an empirically assumed compression floor.

4. Finish the deterministic curation, matching and replay definitions (§§3.5, 4–6).

These are material unresolved choices:
- Section 4 lists P ∈ {2, 5, 20}; §6 lists {1, 5, 20}. Define one schedule, exact prefix boundaries, and which held-out message indices trigger each version.
- Define template grouping and parameter precedence. Digit runs also match the word pattern; “positions that vary” does not specify alignment or grouping.
- Define segmented template endpoints. The inherited matcher matches a whole message; invoking it at a start offset does not define which substring endpoints are tested or how ambiguity across endpoints is handled.
- Freeze candidate enumeration and comparison-step counting before applying work budgets; otherwise budget exhaustion depends on implementation order.
- Reconcile leave-one-prefix-out tuning in §4 with leave-one-fold-out tuning in §5.5, and state how chronological splitting and the held-out candidate pool interact.

These can be resolved by precise pseudocode or a fixed deterministic reference algorithm. I am not requiring a different mining strategy.

Suggestions

Include exact decoded outputs and expected error codes with the byte fixtures. For the over-width varint fixture, explicitly state that width overflow takes precedence over later ordinal lookup.

Clarify that §3.2’s 16-argument wire limit does not expand E1E-REPO/1’s existing eight-parameter entry limit.

I cannot approve this revision as written. The 4b-delta change resolves the central comparison concern; the remaining blockers are the undetectable snapshot race, inconsistent framing, unsupported bound and unresolved deterministic procedures.
