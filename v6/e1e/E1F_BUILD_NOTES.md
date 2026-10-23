# E1f build notes (implementation of E1F_PROPOSAL_DRAFT.md; not frozen, not tagged)

Ambiguities and possible spec bugs found while implementing. The spec text is unchanged; each item gives the section,
what is unclear, what was implemented (always the most literal reading) and a proposed fix. Numbered in order found.


## Resolution status after GPT code review r1 (2026-10-23, Australia/Sydney)

Normative text: `E1F_AMENDMENT_A1_DRAFT.md` (commit `ddcf798`; draft, not frozen). Code commits: A3 `1048952` (candidate generation),
A1 `a8961d3` (exact greedy), A2 `a7c4838` (append-only chain), A4 `49bcc09` (joiner lifecycle), A5/A7/A6-library `00c30c0` (oversized
verification, native baseline rule, encoder stats, break-even, CV framing), A6-tool/note 10/note 26 `a327dcd` (report, lineage, L after
trimming, Stage 2). Each item below carries its status tag; where the item text describes behaviour that has since changed, the tag says
"text below superseded". GPT blockers: 1 `a8961d3`; 2 `a7c4838`; 3 `1048952`; 4 `49bcc09`; 5 `00c30c0`; 6 `00c30c0` + `a327dcd` + `a7c4838`;
7 `00c30c0`.

| Notes | GPT ruling | Status |
|---|---|---|
| 1, 3, 8, 9, 12, 14, 15a/c/d, 17, 18, 20, 24, 25, 27, 28a-d, 7 | ACCEPT | accepted and documented in the amendment (24: framing bytes added to the CV score, rule frozen) |
| 2, 4, 5, 6, 11, 13, 16, 19, 21, 22, 23 | REQUIRED CHANGE | resolved (see tags) |
| 10, 15b, 26 | REQUIRED CHANGE (design choice) | resolved with a [CHOICE] listed in the amendment section 8 for GPT to overrule |

## Resolution status after GPT code review r2 (2026-10-23, Australia/Sydney)

GPT r2 (`reviews/gpt_E1f_code_r2.md`) resolved blockers 1-5 and 7 and accepted choices C1-C14, and required three fixes (all in the
amendment, `E1F_AMENDMENT_A1_DRAFT.md`, revised):
- **r2-1 size-aware publication overflow** (note 13 / C7): `c80559a`; A1.3.1 item 4. Longest prefix of new entries in pick order whose exact canonical full
  snapshot AND delta are <= 1,048,576 bytes; count-limit and byte-limit overflow reported separately; the E1E limit is unchanged.
- **r2-2 break-even sign error** (note 23 / C8): `b145d0a`; A1.5. Crossover = A0/step for either slope sign; numeric only when positive and finite;
  explicit statuses otherwise; stated as a frozen observed-cost extrapolation. Affected reports regenerated.
- **r2-3 whole-message character-budget suppression unreported** (note 6 / C4): `9f9162e` + `8110b24`; A1.2. The flag is set at rejection;
  `matcher_span_chars` is emitted; the A1.2 equivalence claim is qualified; C4 is a deterministic work guard, not a latency guarantee.
The earlier "possible spec issue" about the 1 MiB artifact limit (amendment section 10) is resolved by r2-1.

## Compact codec (e1e/compact.py)
1. **§3.1/§3.2, empty frame (zero-length payload).** *[accepted (A1.1, ddcf798)]* No first byte exists; the spec lists only "any other first byte:
   E_SCHEMA". Implemented: E_SCHEMA (same as an unknown discriminator). Proposed fix: state it.
2. **§3.2 error precedence, "varint checks ... then epoch (E_STALE), then ordinal lookup ...".** *[RESOLVED (A1.1, ddcf798)]* A frame cannot be
   parsed past the epoch without a snapshot (ordinal lookup and the number of args depend on it), so a literal
   multi-pass reading is not implementable. Implemented: one sequential pass in byte order: first byte, epoch varint
   checks, E_STALE, then per segment (opcode E_SCHEMA, varint checks, ordinal E_UNKNOWN_REF, args E_PARAM/E_TRUNCATED),
   then the reconstructed-size check (E_TOO_LARGE) last, after the whole frame has parsed. Consequence: a bad varint in
   segment 3 does not outrank E_STALE on the epoch, and E_UNKNOWN_REF on segment 1 outranks a bad opcode in segment 2.
   Proposed fix: say "sequential in byte order" in §3.2.
3. **Error codes not given in the spec.** *[accepted (A1.1, ddcf798)]* Segment count > 256 and compact frame > 65,536 B: E_TOO_LARGE. LIT with n = 0:
   E_SCHEMA. LIT bytes that are not valid UTF-8: E_SCHEMA. Argument errors: empty word/text or bad characters/UTF-8
   = E_PARAM; argument length longer than the remaining frame = E_TRUNCATED; zigzag varint over 10 bytes or over
   2^64-1 = E_RANGE; decoded int outside |n| < 10^18 = E_PARAM. Proposed fix: list them.
4. **§3.5 encoder always has a compact form for non-empty UTF-8 messages.** *[RESOLVED: qualified (A1.2, ddcf798)]* When no candidate saves bytes, the frame is
   a single LIT (n + 3..6 bytes), which is always strictly smaller than the JSON raw envelope (>= n + 46 bytes), so the
   send rule sends it. This is a large saving that comes from the un-escaped framing alone, not from any entry (the
   plan's §8 decision (a) anticipates it). It also means arm 7 beats arm 1/5 on every message regardless of curation;
   comparisons that matter are against 4b-delta and arm 6. Implemented literally; flagged so nobody reads it as an entry effect.
5. **§3.5, templates that are not "eligible for segmented matching".** *[RESOLVED (A1.2, ddcf798)]* The text says text-param templates stay
   whole-message only "as E1E" but says nothing about int/word templates whose body ends in a param. Implemented: every
   template that is not eligible (has a text param, or ends in a param) is tested only at s = 0 with e = len(message),
   exactly one parse under the E1E matcher, and takes its place in the (offset, ordinal) enumeration. Proposed fix: state it.
6. **§3.5 candidate cap "at most 4,096 (offset, entry) candidates are produced ... counted and reported".** *[RESOLVED, text below superseded: incremental enumeration, `entries_pending` (1048952, A1.2)]* Implemented:
   a candidate is a (start, entry) pair that passes the literal / template-end test (so a start where a template has
   no unique parse is not a candidate); after 4,096 are produced the rest are not evaluated; the stats report
   `cap_hit` and `unconsidered_pairs` (starts that passed a cheap prefilter but were not evaluated). Template starts are
   found with a lookahead regex (a necessary condition), so no start that the spec's test would accept is missed.
7. **§3.5 greedy: LIT overhead is ignored in "bytes saved".** *[accepted (A1.2)]* Per the text, a REF is taken if covered - REF bytes > 0
   even though the two gaps it creates each cost opcode + length (>= 2 bytes). Implemented literally; the compact frame
   can therefore be larger than the all-LIT frame for the same message. Proposed fix (not applied): compare the
   built frame with the all-LIT frame too, or include the extra LIT overhead.
8. **§3.3 retention with a version-0 (empty) receiver.** *[accepted (A1.1)]* The empty repository is version 0 and epochs are >= 1, so it is
   never retained as "previous"; epoch 0 is E_STALE. Proposed fix: state it.

## Curation (e1e/curation.py)
9. **§4 order for corpora without timestamps.** *[accepted (A1.3)]* "Synthetic and Glyph-own dev corpora ... ordered the same way" has no
   first-message time to order by (neither corpus carries timestamps). Implemented: every conversation ties, so the
   order is ascending SHA-256 of `"e1e-fold-1" + NUL + conv_id`. Same rule when any message of a corpus lacks `ts`.
10. **§4 common substrings: orientation and length test.** *[RESOLVED, text below superseded: L applies after trimming (a327dcd, A1.3)]* "all maximal common substrings >= L bytes for each pair" does
    not fix which string drives the automaton, nor whether L is tested before or after trimming. Implemented: for a
    pair (a, b) with a earlier than b in dev order, the automaton is built on a and b is walked (matching statistics);
    (i, ms[i]) is reported when b[i+1] does not extend it; the >= L test is on the untrimmed byte length, then the
    string is trimmed to code-point boundaries (it can end up a few bytes below L). Proposed fix: state both.
11. **§4 objective: what an "occurrence" is.** *[RESOLVED, 'gains only shrink' withdrawn: exact greedy (a8961d3, A1.3)]* Implemented: every substring occurrence of the body in the eligible dev
    messages of the prefix (not only line-aligned ones), taken left to right without self-overlap among occurrences
    not blocked by already chosen entries; template occurrences are exactly the §3.5 encoder's candidates (segmented
    when eligible, whole-message otherwise), so G agrees with what the encoder can use. Per-occurrence terms
    `len(o) - (1 + 2 + arg bytes)` are summed as written (negative terms are not clamped). Gains only shrink after a pick,
    so a lazy greedy (stale upper bounds in a heap) gives exactly the same sequence as full recomputation; the
    sequence does not depend on C (C only truncates it), so C in the grid is a prefix of one run.
12. **Oversized messages (> 65,536 B) in curation.** *[accepted (A1.3)]* The spec says denominators exclude them but not whether they feed
    mining. Implemented: excluded from mining, occurrence counting and G (the encoder never encodes them); counted and
    reported (`oversized_messages_excluded`, `oversized_bytes_excluded`). Bodies > 16,384 code points: skipped and
    counted (line blocks: distinct repeated blocks at the first level that exceeds the limit; common substrings: per pair result).
13. **Entry ids are not specified, and E1E-REPO/1 defers deletion.** *[RESOLVED: append-only rule (a7c4838, A1.3.1)]* Ordinals follow ids, so ids matter for the 1-byte vs
    2-byte ordinal split, and snapshot j+1 cannot drop an entry of snapshot j (E_DELETION_DEFERRED) although §4 builds each
    version independently from a longer prefix. Implemented: the §4 algorithm runs independently per version exactly as
    written; ids are `e{counter:05d}` assigned in pick order, an identical (kind, body, params) already in the previous
    snapshot keeps its id; the published snapshot is **append-only**: S_j = S_(j-1) plus the newly picked entries (dropped
    entries stay as dead weight in every arm's dictionary and in the deltas). MAX_ENTRIES (4096) caps the union; overflow
    is counted. Proposed fix: state append-only publication (or allow deletion) and the id rule in §4.
14. **§4 entrycost.** *[accepted (A1.3)]* "serialized artifact record bytes" implemented as `len(canonical(entry))` with a 6-character id and
    v = 1 (the separating comma is not counted), times (1 + joiners).
15. **§4 template rules.** *[accepted (a,c,d); (b) RESOLVED: sentence removed (A1.3)]* (a) Group key = (separator runs including the possibly empty leading and trailing ones, token
    count); the spec's "separator sequences identical and token counts equal" would otherwise merge `"a "` with `" a"`.
    (b) The sentence "the first and last token of the template must not both be params adjacent to a separator-free
    boundary" cannot be implemented as written (adjacent params are impossible by tokenisation) and is a no-op here.
    (c) More than 4 params: the group is discarded. (d) A line-mined template whose block ends in a token that became a
    param is whole-message-only under §3.5, so it matches almost nothing in the encoder although curation mined it: a
    possible spec inconsistency (curation mines templates the segmented encoder is not allowed to use). G counts only
    what the encoder can use, so such templates simply do not get picked.
16. **§4 tuning parameters not fixed by the text.** *[RESOLVED (A1.3)]* Tuning's "arm 7's total (messages + sync, V = 1 static)" does not give
    participants or joiners. Implemented: the primary scenario's participants (2) and joiners (0); sync = full artifact
    uploaded once + downloaded by each participant; declarations and length prefixes charged as in the scenario runner;
    oversized messages are not part of the score.
17. **§5.3 provenance.** *[accepted (A1.3)]* `make_entry`'s default `prov="synthetic"` is part of the existing E1E code and its 69 tests, so it
    is not changed; E1f constructs entries only through `curation.make_entry_strict` (keyword-only `prov`, no default, must
    be one of the three values; `Miner` also refuses a missing prov). Proposed fix: say E1f call sites, as done here.

## Arms, accounting and scenario runner (e1e/baselines.py, additions only)
18. **Empty repository and arm 7.** *[accepted (A1.1)]* Epochs are >= 1 (build note 8), so with no published snapshot arm 7 cannot form even an
    all-LIT frame and sends the raw envelope; arms 5/6 likewise. Arm 4b equals baseline 3 (A1). Reported, not fixed.
19. **Frame choice in arms 3/4/4b/4b-delta.** *[RESOLVED, text below superseded: native zstd frame only (00c30c0, A1.4)]* The spec does not say whether these may fall back to the envelope. Implemented:
    the zstd frame is sent unless the raw envelope is not larger (ties to the raw envelope), the same rule as §5.1's
    fallback; in practice the zstd frame always wins for eligible messages. Arm 1 sends the envelope.
20. **Links, declarations and receivers.** *[accepted (A1.5)]* §6 does not fix the link model. Implemented: a link is (conv_id, sender_role,
    receiver_role); a declaration is charged when the declaration used on a link changes, first use included; one shared
    receiver state per arm (all participants hold identical snapshots, applied at the same message index);
    participants only multiply sync downloads. Declarations are charged for the repository arms (4b, 4b-delta, 5, 6, 7),
    not for arms 1, 3, 4. Joiners are charged their full-sync download only (no separate declaration).
21. **Which versions are published.** *[RESOLVED, text below superseded: all versions up to the highest used are curated (a7c4838, A1.3.1)]* Held-out/replay messages may skip schedule versions (e.g. V = 20 with few messages).
    Implemented: only schedule versions some message uses are curated and published, as consecutive repository versions
    1, 2, ... (E1E-REPO/1 requires target = base + 1); a version that adds no new entry publishes nothing. `build_repository_chain`
    records the skipped schedule versions. Proposed fix: say so in §4/§6.
22. **Joiner upload and arm 4b.** *[RESOLVED, text below superseded: joiners charged every later publication (49bcc09, A1.5)]* A joiner's full snapshot artifact is uploaded once per distinct joined version other than
    the initial one (arms 4b-delta/5/6/7); under A1 the joined version's dictionary was already uploaded when published.
    Joiners at message indexes floor(M*q/4), q = 1, 2, 3 join at the version current for that message.
23. **Break-even counts (§6).** *[RESOLVED, text below superseded: break-even emitted (00c30c0, a327dcd, A1.5)]* Not collapsed to one number because 4b-delta and arm 7 distribute identical artifacts (per-update
    and per-join costs are equal, so a break-even in updates/joins is undefined/infinite against 4b-delta). The runner reports
    `initial`, `per_update_download` and `per_join` ingredients; break-even against 4b (full rebuild) can be computed from them.
24. **Baseline 4 in dev screening.** *[accepted; framing bytes added to the CV score (00c30c0, A1.6)]* The §7 size selection uses fold = SHA-256("e1e-fold-1" NUL conv_id) mod 4 (seed frozen by
    §5.5; the plan says "seed fixed in the freeze") and charges dictionary bytes x (1 + 2 participants) in the CV score.
    On dev corpora arms 4/6 are trained on and replayed over the same messages (in-sample), so they are optimistic there.

## Dev screening (tools/e1f_dev_screen.py)
25. **§7 Stage 1 repository.** *[accepted (A1.6)]* "covered bytes by curated entries" does not say which repository. Implemented (declared in the
    tool's docstring before any number was seen): the V = 1 static repository from all dev conversations, joiners 0, curated
    with the grid point chosen by the forward-only tuning; coverage = covered bytes of the arm-7 encoder's REF spans / bytes of
    eligible (<= 65,536 B) dev messages. In-sample on dev (the entries are mined from the messages they cover), so it is an
    optimistic number. The report also carries, labelled informational and not used for the gate, in-sample coverage at every
    grid point (nothing was re-chosen).
26. **§7 Stage 2 heuristic.** *[RESOLVED, exact formula (a327dcd, A1.6)]* Not exactly specified. Implemented: estimate = (input bytes - covered bytes) + refs x measured
    average REF bytes + 2 bytes per message (discriminator + epoch) + measured length prefixes + measured control bytes +
    measured arm-7 sync, primary scenario, in-sample dev replay; a second figure adds 2 bytes per LIT segment. Compared with the
    measured 4b-delta total (strictly smaller = "estimate below"). Because the average REF cost is measured from the same
    in-sample encoding, the estimate is nearly the measured arm-7 total; it is a weak test by construction.
27. **Dev scenarios replay the dev messages themselves (in-sample).** *[accepted (A1.6)]* There is no held-out data. Versions follow §4 (message
    rank r uses 1 + floor(r*V/M)); every dev conversation is in some version's prefix, so early messages are in the data their
    snapshot was mined from. Arms 4 and 6 use a baseline-4 dictionary trained on the same messages. All numbers are DEV ONLY.
28. **Observations the main agent should weigh (not deviations).** *[accepted as dev observations (A1.6)]* (a) Arm 7 stores literal residue uncompressed (the 7z variant
    is deferred by §3.4), whereas arms 3/4b/4b-delta compress the residue, so arm 7 can only win through very high coverage;
    on both dev corpora it is far from that. (b) Each declaration is a JSON frame with a 64-hex digest (~110 B) charged once
    per link; with a (conv, sender, receiver) link model it is the single largest control charge for every repository arm
    (equal across 4b, 4b-delta, 5, 6, 7, so the retirement-rule comparisons are unaffected) but it is a penalty arms 1, 3, 4
    do not pay by construction. (c) With joiners = 3 the entry cost multiplier (1 + 3) makes G <= 0 for every candidate on both
    dev corpora, so those scenarios publish no repository at all. (d) Tuning: on the synthetic corpus every C gives the same score (fewer than 50 picks exist), so the tie rule picks C = 50;
    on Glyph-own the forward-only score is lowest for the strictest grid point (L = 256, k = 3; a handful of entries), because entries
    mined from earlier blocks rarely recur in the next block while their sync bill is certain. This is what the frozen procedure
    selects, not a bug; the chosen point then gives very low in-sample coverage (see the informational grid in the reports).
