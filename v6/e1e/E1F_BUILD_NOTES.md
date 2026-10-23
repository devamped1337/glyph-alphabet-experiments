# E1f build notes (implementation of E1F_PROPOSAL_DRAFT.md; not frozen, not tagged)

Ambiguities and possible spec bugs found while implementing. The spec text is unchanged; each item gives the section,
what is unclear, what was implemented (always the most literal reading) and a proposed fix. Numbered in order found.

## Compact codec (e1e/compact.py)
1. **§3.1/§3.2, empty frame (zero-length payload).** No first byte exists; the spec lists only "any other first byte:
   E_SCHEMA". Implemented: E_SCHEMA (same as an unknown discriminator). Proposed fix: state it.
2. **§3.2 error precedence, "varint checks ... then epoch (E_STALE), then ordinal lookup ...".** A frame cannot be
   parsed past the epoch without a snapshot (ordinal lookup and the number of args depend on it), so a literal
   multi-pass reading is not implementable. Implemented: one sequential pass in byte order: first byte, epoch varint
   checks, E_STALE, then per segment (opcode E_SCHEMA, varint checks, ordinal E_UNKNOWN_REF, args E_PARAM/E_TRUNCATED),
   then the reconstructed-size check (E_TOO_LARGE) last, after the whole frame has parsed. Consequence: a bad varint in
   segment 3 does not outrank E_STALE on the epoch, and E_UNKNOWN_REF on segment 1 outranks a bad opcode in segment 2.
   Proposed fix: say "sequential in byte order" in §3.2.
3. **Error codes not given in the spec.** Segment count > 256 and compact frame > 65,536 B: E_TOO_LARGE. LIT with n = 0:
   E_SCHEMA. LIT bytes that are not valid UTF-8: E_SCHEMA. Argument errors: empty word/text or bad characters/UTF-8
   = E_PARAM; argument length longer than the remaining frame = E_TRUNCATED; zigzag varint over 10 bytes or over
   2^64-1 = E_RANGE; decoded int outside |n| < 10^18 = E_PARAM. Proposed fix: list them.
4. **§3.5 encoder always has a compact form for non-empty UTF-8 messages.** When no candidate saves bytes, the frame is
   a single LIT (n + 3..6 bytes), which is always strictly smaller than the JSON raw envelope (>= n + 46 bytes), so the
   send rule sends it. This is a large saving that comes from the un-escaped framing alone, not from any entry (the
   plan's §8 decision (a) anticipates it). It also means arm 7 beats arm 1/5 on every message regardless of curation;
   comparisons that matter are against 4b-delta and arm 6. Implemented literally; flagged so nobody reads it as an entry effect.
5. **§3.5, templates that are not "eligible for segmented matching".** The text says text-param templates stay
   whole-message only "as E1E" but says nothing about int/word templates whose body ends in a param. Implemented: every
   template that is not eligible (has a text param, or ends in a param) is tested only at s = 0 with e = len(message),
   exactly one parse under the E1E matcher, and takes its place in the (offset, ordinal) enumeration. Proposed fix: state it.
6. **§3.5 candidate cap "at most 4,096 (offset, entry) candidates are produced ... counted and reported".** Implemented:
   a candidate is a (start, entry) pair that passes the literal / template-end test (so a start where a template has
   no unique parse is not a candidate); after 4,096 are produced the rest are not evaluated; the stats report
   `cap_hit` and `unconsidered_pairs` (starts that passed a cheap prefilter but were not evaluated). Template starts are
   found with a lookahead regex (a necessary condition), so no start that the spec's test would accept is missed.
7. **§3.5 greedy: LIT overhead is ignored in "bytes saved".** Per the text, a REF is taken if covered - REF bytes > 0
   even though the two gaps it creates each cost opcode + length (>= 2 bytes). Implemented literally; the compact frame
   can therefore be larger than the all-LIT frame for the same message. Proposed fix (not applied): compare the
   built frame with the all-LIT frame too, or include the extra LIT overhead.
8. **§3.3 retention with a version-0 (empty) receiver.** The empty repository is version 0 and epochs are >= 1, so it is
   never retained as "previous"; epoch 0 is E_STALE. Proposed fix: state it.

## Curation (e1e/curation.py)
9. **§4 order for corpora without timestamps.** "Synthetic and Glyph-own dev corpora ... ordered the same way" has no
   first-message time to order by (neither corpus carries timestamps). Implemented: every conversation ties, so the
   order is ascending SHA-256 of `"e1e-fold-1" + NUL + conv_id`. Same rule when any message of a corpus lacks `ts`.
10. **§4 common substrings: orientation and length test.** "all maximal common substrings >= L bytes for each pair" does
    not fix which string drives the automaton, nor whether L is tested before or after trimming. Implemented: for a
    pair (a, b) with a earlier than b in dev order, the automaton is built on a and b is walked (matching statistics);
    (i, ms[i]) is reported when b[i+1] does not extend it; the >= L test is on the untrimmed byte length, then the
    string is trimmed to code-point boundaries (it can end up a few bytes below L). Proposed fix: state both.
11. **§4 objective: what an "occurrence" is.** Implemented: every substring occurrence of the body in the eligible dev
    messages of the prefix (not only line-aligned ones), taken left to right without self-overlap among occurrences
    not blocked by already chosen entries; template occurrences are exactly the §3.5 encoder's candidates (segmented
    when eligible, whole-message otherwise), so G agrees with what the encoder can use. Per-occurrence terms
    `len(o) - (1 + 2 + arg bytes)` are summed as written (negative terms are not clamped). Gains only shrink after a pick,
    so a lazy greedy (stale upper bounds in a heap) gives exactly the same sequence as full recomputation; the
    sequence does not depend on C (C only truncates it), so C in the grid is a prefix of one run.
12. **Oversized messages (> 65,536 B) in curation.** The spec says denominators exclude them but not whether they feed
    mining. Implemented: excluded from mining, occurrence counting and G (the encoder never encodes them); counted and
    reported (`oversized_messages_excluded`, `oversized_bytes_excluded`). Bodies > 16,384 code points: skipped and
    counted (line blocks: distinct repeated blocks at the first level that exceeds the limit; common substrings: per pair result).
13. **Entry ids are not specified, and E1E-REPO/1 defers deletion.** Ordinals follow ids, so ids matter for the 1-byte vs
    2-byte ordinal split, and snapshot j+1 cannot drop an entry of snapshot j (E_DELETION_DEFERRED) although §4 builds each
    version independently from a longer prefix. Implemented: the §4 algorithm runs independently per version exactly as
    written; ids are `e{counter:05d}` assigned in pick order, an identical (kind, body, params) already in the previous
    snapshot keeps its id; the published snapshot is **append-only**: S_j = S_(j-1) plus the newly picked entries (dropped
    entries stay as dead weight in every arm's dictionary and in the deltas). MAX_ENTRIES (4096) caps the union; overflow
    is counted. Proposed fix: state append-only publication (or allow deletion) and the id rule in §4.
14. **§4 entrycost.** "serialized artifact record bytes" implemented as `len(canonical(entry))` with a 6-character id and
    v = 1 (the separating comma is not counted), times (1 + joiners).
15. **§4 template rules.** (a) Group key = (separator runs including the possibly empty leading and trailing ones, token
    count); the spec's "separator sequences identical and token counts equal" would otherwise merge `"a "` with `" a"`.
    (b) The sentence "the first and last token of the template must not both be params adjacent to a separator-free
    boundary" cannot be implemented as written (adjacent params are impossible by tokenisation) and is a no-op here.
    (c) More than 4 params: the group is discarded. (d) A line-mined template whose block ends in a token that became a
    param is whole-message-only under §3.5, so it matches almost nothing in the encoder although curation mined it: a
    possible spec inconsistency (curation mines templates the segmented encoder is not allowed to use). G counts only
    what the encoder can use, so such templates simply do not get picked.
16. **§4 tuning parameters not fixed by the text.** Tuning's "arm 7's total (messages + sync, V = 1 static)" does not give
    participants or joiners. Implemented: the primary scenario's participants (2) and joiners (0); sync = full artifact
    uploaded once + downloaded by each participant; declarations and length prefixes charged as in the scenario runner;
    oversized messages are not part of the score.
17. **§5.3 provenance.** `make_entry`'s default `prov="synthetic"` is part of the existing E1E code and its 69 tests, so it
    is not changed; E1f constructs entries only through `curation.make_entry_strict` (keyword-only `prov`, no default, must
    be one of the three values; `Miner` also refuses a missing prov). Proposed fix: say E1f call sites, as done here.
