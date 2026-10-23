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
