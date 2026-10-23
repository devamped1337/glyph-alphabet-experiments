# E1f amendment A1 (DRAFT) — to `E1F_PROPOSAL_DRAFT.md` revision 3

Dated 2026-10-23 (Australia/Sydney). Status: **draft for GPT review; not frozen, not tagged.** It amends and clarifies the approved
proposal after GPT's code review r1 (`reviews/gpt_E1f_code_r1.md`, build commit `5539d39`). `E1F_PROPOSAL_DRAFT.md` is **not edited**;
where this amendment is silent the proposal governs. **Unchanged by this amendment:** the tuning grid (L ∈ {32,64,128,256},
k ∈ {2,3}, C ∈ {50,200,1000}), the 20 % Stage 1 coverage floor, the retirement rule and every threshold. The failed dev screening is
not a reason to change any of them. The implementation matches this text exactly (commit map in §9); items marked **[CHOICE]** are
design choices made by the implementer where the review asked for a decision, listed again in §8 so GPT can overrule them.

Nothing here is a savings claim. Dev numbers are in-sample, DEV ONLY, and are not held-out evidence; the Glyph-own corpus is
single-operator and self-similar.

## A1.1 §3.2 Compact body — precedence, limits, error codes (notes 1, 2, 3, 8)

**Empty payload (note 1).** A zero-length payload has no discriminator byte: E_SCHEMA.

**Error precedence is sequential in byte order (note 2).** A frame cannot be parsed past the epoch without the snapshot it names
(ordinal lookup and the argument layout depend on it), so the proposal's list "varint checks … then epoch … then ordinal … then
args … then size" is replaced by one pass, and the first failing check in this order is the reported error:
1. first byte ≠ 0x01 → E_SCHEMA;
2. whole frame longer than 65,536 bytes → E_TOO_LARGE (a structural limit, checked before the epoch is read);
3. epoch varint: out of bytes E_TRUNCATED; wider than 5 bytes or > 2³²−1 E_RANGE; non-shortest E_NONCANONICAL (in byte order);
4. epoch not 0 < epoch ∈ {current, previous retained} → E_STALE;
5. no byte after the epoch → E_SCHEMA;
6. for each segment in order: a 257th segment → E_TOO_LARGE; then the opcode (unknown → E_SCHEMA); then, for LIT, the length varint
   (checks as step 3; n = 0 → E_SCHEMA; n larger than the bytes remaining → E_TRUNCATED; bytes not valid UTF-8 on their own →
   E_SCHEMA); for REF, the ordinal varint (checks as step 3; ordinal ≥ entry count → E_UNKNOWN_REF) and then each argument in
   declared order (int: zigzag varint ≤ 10 bytes / ≤ 2⁶⁴−1 else E_RANGE, decoded |n| ≥ 10¹⁸ → E_PARAM; word/text: length varint,
   length 0 → E_PARAM, length beyond the remaining bytes → E_TRUNCATED, then word not `[A-Za-z0-9_.-]+` or text not valid UTF-8 →
   E_PARAM);
7. only after the whole frame has parsed: reconstructed size > 65,536 bytes → E_TOO_LARGE (the rest of the frame is still validated
   first; output is no longer retained once the limit is passed).
Consequences: a bad varint in segment 3 does not outrank E_STALE on the epoch; E_UNKNOWN_REF in segment 1 outranks a bad opcode in
segment 2.

**Error codes (note 3).** E_TRUNCATED and E_RANGE are new codes (never raised by the E1E-MSG/1 decoder). E_NONCANONICAL, E_SCHEMA,
E_STALE, E_UNKNOWN_REF, E_PARAM, E_TOO_LARGE, E_FORK are existing codes reused with the assignments above.

**Epoch zero (note 8).** Epoch 0 is invalid (E_STALE): the empty repository (version 0) is never a usable compact epoch and is never
retained as the "previous" snapshot. With no published snapshot arm 7 cannot form even an all-LIT frame and sends the raw envelope
(arms 5/6 likewise); arm 4b then equals baseline 3 (note 18, disclosed as a discontinuity, not fixed).

## A1.2 §3.5 Deterministic segmented encoder (notes 4, 5, 6, 7)

**Candidate generation is incremental and bounded (blocker 3).** For a snapshot and a message of `n` code points the encoder
produces candidates `(start, end, ordinal, ref bytes)` in the order **ascending start offset (code points), then ascending
ordinal**, by merging one start-iterator per entry; it never materialises or sorts all (offset, entry) pairs. Per entry the starts are:
- literal entry: every offset (overlapping included) where the body occurs; a candidate is produced at each (the body is the span);
- template entry *eligible for segmented matching* (body ends in a literal, all params int/word): ascending offsets that pass a
  **necessary-condition prefilter** (linear, no backtracking, no regular expression): if the body starts with a literal, the offset is an
  occurrence of that leading literal; if it starts with a param, the character at the offset is in the param's first-character class
  (int: `-0-9`; word: `[A-Za-z0-9_.-]`) and the literal that follows that param still occurs at some later offset;
- every other template (a `text` param, or a body ending in a param) is **whole-message only** (note 5, below): one start, offset 0, and
  only if the message begins with the template's leading literal and ends with its trailing literal (empty literals always satisfy this).
The pair is *evaluated* when it is reached in the merged order. Eligible-template evaluation: ends are the offsets just after
occurrences of the body's last character that are ≥ start, tried in **descending** order, **at most 64 tries** (a try is counted whether
or not it passes); a try is skipped without calling the matcher unless the span ends with the template's trailing literal (necessary
condition); otherwise the E1E-REPO/1 matcher (`match_template`, its own 20,000-step budget) decides, and the first try with
**exactly one parse** is the candidate's end. A start where no try succeeds produces no candidate. Enumeration stops as soon as
**4,096 candidates** exist. The prefilters only skip pairs the spec's test could not accept, so outputs are identical to evaluating
every pair (regression-tested against the pre-amendment implementation on made-up inputs below the cap).

**Work bounds on non-candidate evaluations (blocker 3) [CHOICE].** The proposal bounds produced candidates, not evaluations. Per
message: at most `EVAL_CAP` = 65,536 template (offset, entry) evaluations, at most `MATCH_CALL_CAP` = 4,096 matcher invocations, and at
most `MATCH_WORK_CAP` = 2²⁰ characters summed over the spans handed to the matcher. (The E1E matcher's 20,000-step budget is not a time
bound — each step slices and regex-matches the remaining span, so one call on a ~40,000-character span costs ≈ 0.3 s — hence the
character budget.) When any of these is exhausted all remaining template pairs of that message are dropped; literal candidates are
unaffected; the outcome is deterministic and reported (`eval_cap_hit`, `match_cap_hit`).

**Reported statistics (note 6).** Per message: `candidates`, `cap_hit` (the 4,096 limit was reached with at least one entry still
having an unexamined start), `entries_pending` (the number of entries whose start iterator was not exhausted when enumeration stopped —
**not** a count of additional candidates and not a count of proven pairs; the earlier name "unconsidered pairs" is withdrawn),
`template_evaluations`, `eval_cap_hit`, `matcher_calls`, `match_cap_hit`. The screening report aggregates, per arm 7 and scenario: messages,
enumerated messages, summed candidates / entries_pending / template_evaluations / matcher_calls, number of messages hitting each cap,
send reasons (`compact`, `compact_not_smaller`, `verify_failed`, `unknown_declared_snapshot`, `empty_message`, `not_utf8`), decoder
verification failures by error code, receiver rejects after a send, and raw-envelope sends.

**Segmentation selection and the send rule** are as in the proposal (earliest start; saved = covered bytes − REF bytes; ties by longer
span then lower ordinal; verification by the real decoder; strictly smaller wins, ties to the raw envelope).

**All-LIT is not always available (note 4).** For a non-empty UTF-8 message that fits, an all-LIT frame is `n + 3…6` bytes and is
smaller than the JSON envelope (≥ n + 46 bytes), so the framing-only saving is real and is **not an entry effect**; arm 7 therefore beats
arms 1 and 5 on nearly every message regardless of curation, and the comparisons that matter are against 4b-delta and arm 6. It is not
universal: a 65,536-byte message with no useful candidate yields a 65,540-byte compact frame, which exceeds the 65,536-byte frame limit;
the real decoder rejects it (E_TOO_LARGE), verification fails and the raw envelope is sent (tested). The same holds for the empty
repository (A1.1).

**Whole-message int/word templates ending in a parameter (note 5).** The proposal grants whole-message matching explicitly to `text`
templates. It is extended to every template that is not eligible for segmented matching: a template with a `text` param **or whose body
ends in a param** (including int/word-only templates) is a candidate only at offset 0 with end = n, exactly one parse under the E1E matcher,
and takes its place in the (offset, ordinal) enumeration.

**LIT overhead is ignored by the greedy score (note 7, accepted).** A REF is taken when covered bytes − REF bytes > 0 although the two
gaps it creates each cost ≥ 2 bytes of LIT framing; the compact frame can therefore be larger than the all-LIT frame. This follows the
specified score. An all-LIT comparator would be an encoder amendment needing separate review; none is made here.

## A1.3 §4 Curation (notes 9–17)

**Order (note 9).** Without timestamps, and for a whole corpus in which any message lacks `ts`, the corpus-wide conversation order is
ascending SHA-256 of `"e1e-fold-1" NUL conv_id`.

**Oversized messages (note 12).** Messages > 65,536 B are excluded from mining, occurrence counting and every curation denominator, and
are counted (`oversized_messages_excluded`, `oversized_bytes_excluded`). Candidate bodies > 16,384 code points are skipped and counted.

**Maximal common substrings (note 10) [CHOICE].** For a pair of messages (a, b) from different conversations, both inside the prefix,
with a earlier than b in dev order, the suffix automaton is built over the **bytes of a** and b is walked (matching statistics); a result
is a (start-in-b, length) pair that is left- and right-maximal over bytes. It is then trimmed to UTF-8 code-point boundaries (taken from b's
bytes) and **L applies to the trimmed byte length** (a result below L after trimming is discarded). The minimum is also used as an
untrimmed pre-filter (trimming only shortens).

**Objective and greedy (note 11, blocker 1).** Candidates: repeated line blocks, maximal common substrings, templates (below); a
literal candidate must occur in ≥ k distinct dev conversations of the prefix. **Occurrence:** every occurrence of the body as a substring of
an eligible dev message of the prefix (not only line-aligned), starts overlapping allowed; templates: exactly the §3.5 encoder's candidates
for that message (segmented when eligible, whole-message otherwise). Occurrences are listed in ascending (message index, start). Given the
set of already covered characters (the **mask**), a candidate's gain is

 G(c | mask) = Σ over its *used* occurrences o of (len_bytes(o) − (1 + 2 + arg_bytes(o))) − entrycost(c) × (1 + joiners),

where an occurrence is *used* iff it does not touch a masked character and it starts at or after the end of the previous *used*
occurrence of the same candidate in the same message (an unused occurrence does not extend that boundary). Per-occurrence terms may be
negative and are not clamped. **Selection:** repeat — compute G(c | mask) for every remaining candidate; take the candidate with the
largest G, ties by larger total used bytes, then lexicographically smaller UTF-8 body bytes, then lower index in the fixed candidate
order (sorted by body, then params); stop when C picks exist or the largest G ≤ 0; mask the used occurrences of the pick. G is **exact
after every pick**: because masking a negative-contribution occurrence can raise a candidate's G, the earlier "gains only shrink"
argument (and any lazy bound) is withdrawn. The implementation recomputes exactly the candidates that have an occurrence in a message the
pick touched (all others are provably unchanged), which equals a full recomputation; it is regression-tested against a naive
full-recompute reference on randomised data with negative contributions, including the +1, +1, −1 case. C is only a prefix of the pick
sequence; the sequence does not depend on C.

**Entry cost (note 14).** entrycost = `len(canonical(entry))` with a six-character provisional id and v = 1 (the separating comma is not
counted); the provisional ordinal cost in the per-occurrence term is 2 bytes.

**Template mining (note 15).** (a) Group key = (separator runs including the possibly empty leading and trailing ones, token count);
(b) the sentence "the first and last token of the template must not both be params adjacent to a separator-free boundary" is **removed**
**[CHOICE]**: adjacent params cannot occur after tokenisation, so it never had an effect; (c) a group that would need more than 4 params is
discarded; (d) a mined template that §3.5 treats as whole-message only simply matches little and is not picked (no further amendment
beyond note 5).

**Tuning (note 16).** The forward-only validation score is arm 7's total on the pseudo-held-out block with **participants = 2,
joiners = 0, V = 1 static**, **eligible messages only** (oversized messages are not scored), including declarations, length prefixes and
sync as in the scenario runner. Ties: smaller L, then smaller k, then smaller C.

**Provenance (note 17).** The explicit-`prov` requirement applies to every E1f construction path (`curation.make_entry_strict`,
keyword-only, no default, one of the three values; `Miner` refuses a missing prov). The E1E `make_entry` default is unchanged for E1E.

### A1.3.1 Append-only publication (note 13, 21; blocker 2) — normative

1. **Schedule.** Scheduled version j ∈ 1..V is curated from the first `ceil(j·n_dev/V)` dev conversations; message rank r of M uses
   scheduled version 1 + floor(rV/M). **V counts scheduled curation points, not repository versions.**
2. **Which versions are curated.** Every j ≤ Vmax, where Vmax is the highest scheduled version any replayed message uses; j > Vmax cannot
   affect a message and is not curated (status `unused`). Intermediate versions that no message uses are still curated, because the union
   at j builds on all earlier versions.
3. **Union (append-only).** The repository is the union of everything published so far. The picks of version j (in pick order) whose
   (kind, body, params) are not already in the repository are its *new entries*. An existing entry keeps its id and v = 1 forever
   (no update or deletion; E1E-REPO/1 defers deletion). A new entry gets id `e{N:05d}`, N = 1 + the largest numeric id so far, in pick order.
4. **Limit and overflow.** The union (not C) is limited by MAX_ENTRIES = 4,096. If the new entries do not fit, the **last** new entries in
   pick order are dropped and counted (`overflow`).
5. **Publication.** A scheduled version with no new entry (unchanged or empty) publishes nothing: the previous snapshot stays current and
   the version is recorded as `empty`. Published repository versions are numbered 1..P **consecutively over non-empty publications only**
   (E1E-REPO/1 requires target = base + 1); the first is a full snapshot, later ones deltas.
6. **Mapping.** A message scheduled at version s uses the latest published snapshot with scheduled version ≤ s (repository version 0, the
   empty repository, if none).
7. **Metadata is preserved.** The result carries, for every scheduled version 1..V, `{sched_version, n_convs, status
   (published|empty|unused), published_index, new_entries, overflow, picks}`; each published record lists the scheduled versions skipped
   since the previous publication; the trailing skipped versions after the last publication are retained. The screening report emits all of it.
8. **Lineage (private).** Each new entry's source-conversation lineage is the conversations of the pick that first introduced it. It is
   written only to `/workspace/e1e-private/e1f_*/<corpus>_lineage_manifest.json` (conversation ids, entry id, kind, G, occurrences, body
   SHA-256); the committed aggregates carry only a histogram of "entries by number of source conversations".

## A1.4 §5.1 Oversized fallback; native baselines (blocker 5, 7; note 19)

The fallback for messages > 65,536 B is unchanged: in every arm the smaller of the baseline-3 zstd frame and the raw envelope, ties to the
raw envelope, carrying its §3.1 length prefix. **Verification [new]:** the chosen frame is checked byte-exactly against the original message
in every run: a zstd frame must be exactly one complete frame whose decompressed output, **bounded by the original message length** (no
fixed ceiling), equals the message; a raw envelope must be the canonical E1E-MSG/1 raw encoding (parsed with the size limit set to its own
length, because the E1E-MSG/1 decoder's wire/size limits are for ≤ 65,536-byte messages) and decode to the message. A failure is an error,
not a count. Counts of fallback kinds and of byte-exactly verified frames are reported.

**Named baselines keep their native rule.** For eligible messages (≤ 65,536 B) arms 3, 4, 4b and 4b-delta send **the zstd frame only**
(arm 1 the raw envelope). The raw-or-zstd selection is used **only** for the oversized fallback above. (The previous build applied it to
eligible messages; the effect on totals is in the regenerated report; on the dev corpora it changes nothing unless a message's zstd frame
is not smaller than its envelope.)

## A1.5 §6 Arms, links, joiners, break-even (notes 20, 22, 23; blocker 4)

**Link model (note 20).** A link is (conv_id, sender role, receiver role) and a conversation start opens it; a declaration is charged when the
declaration in force on a link changes, first use included, for the repository arms (4b, 4b-delta, 5, 6, 7; the empty repository declares the
empty digest) and not for arms 1, 3, 4. All participants hold identical snapshots applied at the same message index (one shared receiver per arm);
participants multiply sync downloads. Joiners are charged their sync downloads only (no separate declaration). Equal declaration charges
cancel in the repository-arm comparisons; they are a declared topology cost, not an entry benefit.

**Sync and joiner lifecycle (blocker 4, note 22).** The maintainer uploads each artifact once; every participant downloads each artifact once
(first the full snapshot, then each delta; for arm 4b each version's rebuilt dictionary; arm 4/6's trained dictionary once). One joiner joins
at message index floor(M·q/4), q = 1, 2, 3 (joiners 3) at the published version current for that message (0 if before the first publication).
**A joiner is a participant from then on:** it downloads the full snapshot (arm 4b: dictionary) of its joined version **and every later
publication** — each later delta for arms 4b-delta/5/6/7, each later rebuilt dictionary for arm 4b; a joiner at version 0 downloads the
initial snapshot (no extra upload) and everything after. A joined version's full snapshot is uploaded once per distinct joined version other
than the initial one (arms 4b-delta/5/6/7); under A1 the joined version's dictionary was already uploaded when published. The joiner's trained
baseline-4 dictionary is downloaded once. With zero joiners the totals are exactly the pre-amendment formula (tested).

**Break-even (note 23).** For each scenario the report emits, for X = arm 7 against Y ∈ {3, 4, 4b, 4b-delta, 5, 6}: the ingredients
(`initial_sync`, `per_update_sync` = (sync without joiners − initial) / U over the U = P − 1 observed publications after the first,
`per_join_sync` = (sync with joiners − sync without) / J, message+control bytes), the observed advantage (= total_Y − total_X), and the
advantage A(u, j) = (msg_Y − msg_X) + (initial_Y − initial_X) − u·(pu_X − pu_Y) − j·(pj_X − pj_Y). **Break-even update count** = the u where
A = 0 with j at its observed J; **break-even join count** = the j where A = 0 with u at its observed U. A count is a number only when defined,
positive and finite; otherwise an explicit string: `undefined: no update observed`, `undefined: no join observed`,
`undefined: identical per-update/per-join cost (X ahead|behind|tie at every count)` (always the case against 4b-delta, which distributes the
same artifacts), `X ahead at every count`, `X behind at every count`.

## A1.6 §7 Dev screening (notes 24, 25, 26, 27)

**Baseline 4 dictionary selection (note 24; frozen rule).** Eligible only with ≥ 50 messages and ≥ 8 conversations. Sizes {1024, 2048, 4096,
8192}; 4-fold cross-validation grouped by conversation, fold = first 8 bytes big-endian of SHA-256(`"e1e-fold-1"` NUL conv_id) mod 4. A size's
score for a fold = total of (zstd frame bytes **+ the frame's canonical length prefix**) over the held-out fold's messages + dictionary bytes ×
(1 + 2 participants); a size is eligible iff training succeeds in all four folds; the chosen size minimises the mean fold score, ties to the smaller
size; the final dictionary is trained on all dev messages. On dev corpora arms 4/6 are trained and replayed on the same messages (in-sample).

**Stage 1 (note 25).** Coverage = bytes covered by the REF spans of the arm-7 encoder ÷ total bytes of eligible (≤ 65,536 B) dev messages,
using the **V = 1 static repository curated from all dev conversations, joiners 0**, at the grid point chosen by the forward-only tuning;
oversized messages and skipped entries are counted separately. In-sample, hence optimistic. Floor 20 % (unchanged).

**Stage 2 (note 26) [CHOICE], approximate.** Primary scenario, in-sample dev replay:
 estimate = (eligible input bytes − covered bytes) + R × a + 2 × N + measured message-prefix bytes + measured control bytes (incl. their
prefixes) + measured arm-7 sync total,
with R = REFs, a = measured average REF bytes, N = eligible messages. Assumptions, stated: the "2 × N" assumes every message is sent compact with
a one-byte epoch (versions < 128) and the 0x01 discriminator; it ignores raw-envelope sends. A second figure adds 2 bytes per measured LIT
segment (opcode + a one-byte length), which understates LIT longer than 127 bytes. Both are compared with the measured 4b-delta total (strictly
smaller = "estimate below"). If the primary repository is empty the estimate is **undefined** (every message is a raw envelope) and none is made.
Because a is measured from the same in-sample encoding the estimate is close to the measured arm-7 total; it is a weak test by construction and
a failing estimate does not prove refs lose.

**In-sample replay (note 27).** There is no held-out data in dev screening; every dev conversation is in some version's prefix. All dev numbers
are DEV ONLY.

**Accepted observations (note 28).** (a) Arm 7's literal residue is uncompressed by design (7z deferred), so arm 7 wins only with very high
coverage; (b) declarations are the largest control charge for every repository arm and arms 1/3/4 do not pay them by construction; (c) with
joiners = 3 the entry-cost multiplier can make every candidate G ≤ 0 (no repository); (d) tuning on small dev corpora can select the strictest grid
point because earlier-block entries rarely recur in the next block. These are dev observations, not deviations.

## A1.7 Tests added with this amendment
Greedy regression vs. a naive full-recompute reference (incl. +1, +1, −1 and 400 randomised cases; the pre-amendment lazy greedy fails them);
candidate generation vs. a frozen copy of the pre-amendment code (`tests/old_compact_ref.py`) on random inputs below the cap; a 4,096-entry ×
65,536-character stress test (< 5 s; the old code materialised ≈ 2.7×10⁸ pairs); matcher call/character caps; append-only chain rule (stable ids,
union, overflow order, unchanged/empty snapshots, `unused` versions, trailing skipped); joiner lifecycle incl. version 0 and zero-joiner invariance;
byte-exact oversized verification for a > 1 MiB compressible message and raw envelopes; native zstd rule for arms 3/4/4b/4b-delta; encoder
statistics; break-even incl. undefined cases; the 65,536-byte all-LIT fallback; L-after-trimming and automaton orientation.

## 8. Choices made (for GPT to overrule)
| # | Note/blocker | Choice |
|---|---|---|
| C1 | 10 | Automaton on the earlier message a, walk the later b; maximal over bytes; L on the trimmed byte length. |
| C2 | 15b | The ineffective boundary sentence is removed. |
| C3 | 26 | Stage 2 formula exactly as in A1.6; undefined when the primary repository is empty. |
| C4 | 3 | Caps `EVAL_CAP` 65,536, `MATCH_CALL_CAP` 4,096, `MATCH_WORK_CAP` 2²⁰ chars per message; when exhausted, template pairs are dropped, literals continue. |
| C5 | 6 | `entries_pending` / `cap_hit` definitions (A1.2); "unconsidered pairs" withdrawn. |
| C6 | 13/21 | Curate every scheduled version ≤ Vmax (not only used ones); versions > Vmax `unused`. |
| C7 | 13 | Overflow drops the last new entries in pick order; first-publication lineage. |
| C8 | 23 | Break-even definitions (per-update/per-join from emitted sync totals; X = arm 7 vs each other arm). |
| C9 | 24 | CV score includes length prefixes; selection rule frozen as in A1.6. |
| C10 | 2 | The frame-size limit (E_TOO_LARGE) is checked before the epoch; reconstructed size last. |
| C11 | 22 | A joiner at version 0 downloads the initial snapshot with no extra upload and then every later publication. |
| C12 | 5 (blocker) | Raw-envelope verification for oversized messages uses an E1E canonical parse with the limit set to the frame length. |
| C13 | 3 | No regular expressions in candidate generation: linear necessary-condition prefilters, the E1E matcher decides. |
| C14 | 5 | Whole-message start condition: leading and trailing literals of the template must prefix/suffix the message. |

## 9. Resolution map
See `E1F_BUILD_NOTES.md` (each note marked resolved/accepted with its commit) and the final report; blockers: 1 → A1.3 (greedy), 2 → A1.3.1,
3 → A1.2, 4 → A1.5, 5 → A1.4, 6 → A1.2/A1.5/A1.3.1(8), 7 → A1.4.

## 10. Unresolved / possible spec issues
- A full repository can exceed E1E-REPO/1's 1 MiB artifact limit before 4,096 entries (4,096 × up to 16,384-character bodies); curation checks
  only the entry-count limit, so `publish` would raise. Cannot occur on the dev corpora; needs a ruling (size-aware overflow).
- The E1E matcher's step budget does not bound time (A1.2); the character-work cap is this amendment's guard.
- Per-link declarations are the largest control charge; they are a topology cost in the proposal's link model.
