# E1f proposal, revision 3 — curated long entries + compact references vs zstd with the same dictionary
Revision 3 (2026-10-23), answering `reviews/gpt_E1f_proposal_r1.md` (r1 text of this file: 1a7323f) and
`reviews/gpt_E1f_proposal_r2.md` (r2 text: 549eab4). §10 (round 1) and §11 (round 2 and 3) map every GPT required change to where it is resolved. Round 3 is one
extra round granted by Stefan beyond the agreed cap of 2; GPT reviews before Claude or Grok see anything (Stefan, 2026-10-23). Status: DRAFT, not frozen, not tagged, nothing run. CPU only; no Kaggle/GPU;
no model other than GPT review via Codex. Builds on `BYTE_AUDIT_PLAN_DRAFT.md` (incl. Amendment A1) and `SPEC_E1E_REPO_1.md`.
Origin: Stefan's point (2026-10-23) that the repository is kept by always-on maintainer agents, so entries could be long and
curated. This experiment tests a **deterministic dev-derived curation procedure** as a proxy; it does not test whether
always-on agents can curate well.

## 1. The question
E1e dev diagnostic (private data, aggregates only): byte coverage 1.61%; ref envelopes 230–372 B against entries mostly 23–57 B;
4b beat refs on dev data. Those are observed results for tiny entries with large envelopes; they do not prove every
design loses. E1f asks: **with long curated entries and few-byte references, does a reference scheme beat per-message zstd
that uses the same entries as its dictionary, with all synchronisation bytes counted under stated distribution policies?**

## 2. Expectation, and what a sync win would mean
zstd with a raw-content dictionary also encodes a long match in a few bytes, so per-message bytes may tie; templates with
parameters may behave differently from literal matches. Sync: A1 charges 4b a **full dictionary rebuild per version** as a
stipulated distribution policy. That is not inherent to zstd: a receiver can rebuild the identical raw-content dictionary
locally from an entry delta. Therefore:
- Any sync-only win of refs is reported as **a win against A1's full-rebuild policy only**, never as a structural advantage of IDs.
- New arm **4b-delta**: identical to 4b (same dictionary bytes, same level/frame settings, same per-message bytes) but its
  dictionary is distributed as the same entry deltas the refs arm receives; the receiver reconstructs A1's dictionary locally
  by the A1 construction. Charged: the deltas, declarations, initial syncs, joiner syncs (artifact serialization identical to arm 7).
  Because 4b-delta's message bytes equal 4b's, only its sync bytes differ.
- Claims about "IDs beat zstd" are made only against 4b-delta. Claims against 4b are labelled "under A1's full-rebuild policy".

## 3. Compact wire form E1F-MSG/1 (additive; E1E-MSG/1 unchanged)
### 3.1 Framing and discrimination
- Every message and every control message (declare, reject, ack) travels in one frame preceded by a **length prefix: unsigned LEB128
  varint of the frame's byte length**, canonical (shortest), at most 5 bytes, value ≤ 2^32−1. The receiver reads the varint first,
  so the width is always recognisable before the payload; a non-canonical or over-width prefix is E_NONCANONICAL / E_RANGE. The
  prefix is charged identically to every arm and every frame (message, declare, reject, retransmission, fallback) and reported
  as its own line. For eligible messages (≤ 65,536 B) every wire frame is ≤ 524,288 B (worst case: every byte an ASCII control
  character escaped to 6 bytes, plus envelope), so prefixes are 1–3 bytes; oversized-message fallback frames may need up to 5.
- First byte of the frame: `0x7B` `{` = existing E1E-MSG/1 JSON envelope ("raw" here always means the JSON raw envelope, never bare
  message bytes); `0x28 0xB5 0x2F 0xFD` = zstd frame (baselines 3/4/4b/6); `0x01` = E1F compact. Any other first byte: E_SCHEMA.
- Limits: compact frame ≤ 65,536 B; decoded message ≤ 65,536 B (`MAX_MESSAGE_BYTES`); ≤ 256 segments; ≤ 8 args per REF (E1E-REPO/1's
  `MAX_PARAMS` = 8 is unchanged; E1f does not expand it); every declared length is checked against the remaining frame bytes and the
  limits **before** allocation.

### 3.2 Compact body (opcodes numeric)
`0x01`, then `varint epoch` (§3.3), then 1..256 segments, then the frame ends. The segment list is exactly the bytes after the epoch;
an incomplete segment is E_TRUNCATED; there is no end marker: bytes that parse as a further valid segment ARE a further segment;
bytes that do not parse are E_TRUNCATED. A frame with no segments is E_SCHEMA; the empty message is sent as the raw envelope.
Error precedence within a frame: first byte, then varint width/overflow/canonical checks in byte order, then epoch (E_STALE), then ordinal
lookup (E_UNKNOWN_REF), then args (E_PARAM), then reconstructed size.
- `0x01 REF` : `varint ordinal` `args…`. **Version is always the entry's version in the snapshot named by the frame's epoch** (no version delta in E1f; no historical bodies beyond §3.3's retained snapshots).
- `0x02 LIT` : `varint n` (1 ≤ n) then n bytes, which MUST be valid UTF-8 on their own. A message that is not valid UTF-8 or whose literal split cannot be made on UTF-8 boundaries is sent raw/zstd, never compact.
- Any other opcode: E_SCHEMA.
- **varint**: unsigned LEB128 (7 bits per byte, little-endian groups, high bit = continuation), **shortest encoding required** (a final 0x00 continuation group is E_NONCANONICAL), maximum 5 bytes and value ≤ 2^32−1 (overflow/over-width = E_RANGE).
- **zigzag** for `int` args: n ↦ (n<<1) xor (n>>63) over the existing `int` domain `-?(0|[1-9][0-9]{0,17})` (|n| < 10^18), carried as varint with the same limits widened to 10 bytes / 2^64−1; values outside the domain = E_PARAM.
- **Arguments** appear in the order of the entry's declared `params`, one per param, no names, none omitted: `int` → zigzag varint; `word` → varint byte length + bytes matching `[A-Za-z0-9_.-]+` (length ≥ 1); `text` → varint byte length (≥ 1) + valid UTF-8 bytes (may contain newlines and braces). Lengths are in bytes.
- **Ordinal** = zero-based index into the declared snapshot's entry list sorted by `id` ascending by Unicode code point (the order of `full_bytes()`). Out of range = E_UNKNOWN_REF. Literal entries have no params; template entries are filled exactly as E1E-REPO/1 (placeholder grammar, `{{`/`}}` escapes). Entries with a body > 16,384 code points do not exist (§5.3).
- Reconstruction = concatenation of segment outputs; the result must be ≤ 65,536 B.
### 3.3 Snapshot binding: charged epoch (replaces the r2 barrier)
Ordering across the two directions cannot be assumed, so the frame itself names the snapshot.
- **Epoch** = the repository version number (integer ≥ 1, strictly increasing along the maintainer's linear history, one digest per number on a link; a different digest for the same number is E_FORK, existing code). Each compact frame carries `varint epoch` (1 byte for versions < 128): **+1 byte per compact message, charged in arm 7.**
- The receiver declares (as in E1E, charged) `(version, digest)`. A sender may encode only against a snapshot `(version, digest)` it holds and that the receiver has declared at some point; it puts that version in the frame.
- **Retention policy (bounded, not a delivery guarantee):** the receiver keeps its current snapshot and the immediately previous one (2 retained). Traffic can lag across more transitions than that; frames with older epochs are handled by the charged fallback below. A frame whose epoch names a retained snapshot is decoded against that snapshot, regardless of cross-direction arrival order; any other epoch is rejected with E_STALE (charged `reject`), and the sender re-sends the original as the raw envelope (charged), exactly as E1E accounting.
- Ordinals therefore always resolve against the snapshot the sender used, and a stale frame cannot silently name a different entry: either its epoch is retained and it decodes against the right snapshot, or it is rejected. Tested with injected races (old-snapshot frame arriving after a new declaration; epoch two versions old; epoch never declared).
- The replay script predeclares every snapshot-change event; transitions are event-driven by held-out message index (§4).

### 3.4 Deferred: the 7z variant (compact + zstd on the literal residue)
Not part of E1f. If arm 7 shows promise, 7z is specified in a separate amendment with its full grammar and re-reviewed. Arm list below omits it.
### 3.5 Deterministic segmented encoder
- **Enumeration (fixed order, structural bounds, no global step counters):** for offset s = 0..len−1 ascending, for entries in ascending ordinal, test the entry at s. At most **4,096 (offset, entry) candidates** are produced per message, in this order; further candidates are not considered (counted and reported).
  - *Literal entry:* a candidate iff the body occurs at s (exact byte match).
  - *Template entry:* only templates whose body **ends in a literal character** and whose params are all `int` or `word` are eligible for segmented matching (`text` templates stay whole-message only, as E1E). Compile the body to an anchored regex (int → `-?(0|[1-9][0-9]{0,17})`, word → `[A-Za-z0-9_.-]+`, literals escaped, `{{`/`}}` → `{`/`}`). Candidate end positions e are the positions after an occurrence of the template's last literal character, tried in **descending** e from min(len, s + 65,536), **at most 64 tries per (s, entry)**; the first e (largest) at which the substring [s, e) has **exactly one parse** under E1E-REPO/1's matcher (step budget 20,000 per call as in the spec; exhaustion or ambiguity at that e → try the next smaller e; the 64-try cap ends the search → no candidate) is the candidate's end.
- Selection: left-to-right greedy over candidates in enumeration order at the earliest uncovered offset: among candidates starting at the earliest offset s ≥ current position, take the one with greatest bytes saved = covered bytes − REF bytes (REF bytes include ordinal and arg bytes), ties by longer span, then lower ordinal; only candidates with bytes saved > 0; the chosen span consumes [s, e); gaps become LIT. Overlapping candidates are never both taken.
- Every compact frame is decoded by the real decoder (including the epoch rule) and must equal the original; otherwise it is discarded (same verification rule as E1E).
- **Send rule:** among {compact, raw envelope} send the strictly smaller; ties → raw envelope.
- **Normative byte examples** (fixture: epoch 1 snapshot S1 with ordinal 0 = literal `"OK"`, ordinal 5 = literal `"done."`, both no params, plus an unrelated epoch-2 snapshot S2 whose ordinal 0 = literal `"NO"`); frames shown without the length prefix:
  - `01 01 02 03 61 62 63` → epoch 1, LIT "abc" → `abc`.
  - `01 01 01 00` → epoch 1, REF ordinal 0 → `OK`.
  - `01 01 02 02 68 69 01 05` → LIT "hi" + REF 5 → `hidone.`
  - `01 02 01 00` (receiver retains S1 and S2) → decoded against S2 → `NO`; replacing the epoch byte `02` with `03` (not retained) → E_STALE.
  - Fixtures with expected errors after epoch validation assume S1 is retained; S1 has no ordinal 127 (so `01 01 01 7F` → E_UNKNOWN_REF). Length-prefix boundary fixtures (message frames of 127 and 128 bytes: prefixes `7F` and `80 01`) are added.
  - Malformed: `01` alone → E_TRUNCATED; `01 01` → E_SCHEMA (no segments); `01 01 02 05 61` → E_TRUNCATED; `01 01 01 FF FF FF FF FF 01` → E_RANGE (width overflow, takes precedence over ordinal lookup); `01 01 01 80 00` → E_NONCANONICAL; `01 01 03 00` → E_SCHEMA (unknown opcode); `00` → E_SCHEMA (unknown discriminator); `01 01 01 7F` → E_UNKNOWN_REF.


## 4. Curation (deterministic, dev-only, fully specified before data)
- **Source:** dev messages only. Held-out and outside real messages are never read by curation.
- **Dev/held-out split (one rule, replaces r2's two):** real corpus: if timestamps exist, conversations ordered by first-message time (ties: SHA-256 of `"e1e-fold-1" + "\x00" + conv_id` as UTF-8); earliest 60% (rounded down) of conversations = dev, the rest = held-out. If timestamps are missing, fold = first 8 bytes big-endian of that SHA-256, mod 5; folds 0–2 = dev, 3–4 = held-out. Synthetic and Glyph-own dev corpora are all dev, ordered the same way. The hash is used only for ties and for the no-timestamp case; no other tuning folds exist.
- **Version schedule (one schedule, frozen):** V ∈ {1, 5, 20}; dev conversations (n of them, in the order above) form cumulative prefixes: version j (1 ≤ j ≤ V) is built from the first ceil(j·n/V) dev conversations only (V = 1: all dev). Held-out messages (M of them, ordered by timestamp, ties by SHA-256 of conv_id + message index) are replayed in that order; the message with 0-based rank r uses version 1 + floor(r·V/M); the snapshot transition is triggered by that message index. Held-out messages never feed any snapshot. No snapshot contains material from a later prefix.
- **Candidate generation (all over dev text of prefixes ≤ the version being built; "occurrence count" counts conversations, once each):**
  - *Line blocks:* every maximal-or-sub run of ≥ 1 consecutive `\n`-separated lines taken from dev messages (including joining `\n`), length ≥ L bytes, ≤ 16,384 code points.
  - *Common substrings:* for each pair of dev messages from different conversations, all maximal common substrings ≥ L bytes (suffix automaton), trimmed to code-point boundaries.
  - *Literal candidates* = the above, kept iff they occur in ≥ k distinct conversations.
  - *Template candidates (fixed algorithm):* take literal-candidate line blocks. Tokenise a block into maximal runs of `[A-Za-z0-9_.-]` ("tokens") and separators (everything else). Two blocks are in the same group iff their separator sequences are identical and their token counts are equal. Within a group, a token position is a **param** iff its values differ across at least two occurrences; other token positions stay literal. A param is `int` iff every observed value matches `-?(0|[1-9][0-9]{0,17})`, else `word` (every observed value must match `[A-Za-z0-9_.-]+`); `text` is never mined. Params are named p1, p2, … in order of position; ≤ 4 params; the first and last token of the template must not both be params adjacent to a separator-free boundary (adjacent params are impossible by maximal-run tokenisation); the template must have ≥ 1 literal character, be unambiguous under the E1E-REPO/1 matcher on all its source occurrences (else discarded) and its group must have ≥ k conversations. `{` and `}` in source text are escaped `{{`/`}}`.
- **Objective and selection:** greedy by net gain `G(c) = Σ_{occurrences o in the version's dev messages} (len(o) − refcost(o)) − entrycost(c)`, where `len(o)` is the byte length of the **matched occurrence o** (for templates it varies with the args), `refcost(o)` = 1 (opcode) + provisional ordinal bytes **fixed at 2** (a deliberately conservative constant, so the cost does not depend on the final list) + the arg bytes of o as encoded; the 1-byte epoch is per message, not per occurrence, and is excluded from G (it is charged in the final accounting). `entrycost(c)` = serialized artifact record bytes × (1 + joiners in the scenario). After each pick, occurrences overlapped by already-chosen entries are removed and G recomputed (marginal overlap). Pick max G; ties by longer total matched length, then lexicographically smaller body bytes; stop when G ≤ 0 or C entries are chosen. After selection, entries are sorted by `id` and ordinals follow (actual ordinal bytes appear only in the real encoder). The same entries feed arms 4b, 4b-delta and 7.
- **Parameter grid (declared now):** L ∈ {32, 64, 128, 256}, k ∈ {2, 3}, C ∈ {50, 200, 1000}. Tuning (forward-only, no overlap leakage): the dev conversations are split into five **disjoint consecutive blocks** B1..B5 (sizes ceil/floor of n/5, in the §4 order). For each grid point, for t = 2..5: build the repository from blocks B1..B(t−1) only (all their conversations, the §4 curation algorithm) and measure arm 7's total (messages + sync, V = 1 static) on block Bt as pseudo-held-out; the score is the mean over t = 2..5. Lowest mean wins; ties by smaller L, then k, then C. Held-out data is never touched. The chosen triple is frozen with the code hash before any held-out replay; no value outside the grid is considered.
- Provenance: every entry is constructed with an explicit `prov` (`synthetic`, `glyph_own_dev`, `real_dev`); construction without one raises. Each entry keeps its source-conversation lineage in the build manifest. Candidates are mined per source; mixed-source candidates are not allowed.

## 5. Fixing the prerequisites (GPT r1 §Q4)
1. **> 64 KiB messages:** reported as an explicit eligible-message comparison (messages ≤ 65,536 B) plus an all-message total. Oversized messages get one common fallback in **every** arm: the smaller of the baseline-3 zstd frame and the raw envelope, ties to the raw envelope. Every such frame carries the §3.1 canonical LEB128 length prefix of its actual encoded length (up to 5 bytes), identically in every arm; there is no fixed-width prefix. Reported separately: count, input bytes, fallback bytes, all-message totals. This is a fallback policy, distinct from each named baseline's native behaviour (refs refuse with E_TOO_LARGE).
2. **Bodies > 16,384 code points:** skipped at candidate generation and counted/reported (entries and covered bytes excluded). E1E-REPO/1 is unchanged; no splitting algorithm.
3. **Provenance:** see §4 (explicit at every construction call; missing raises).
4. **Baseline 6:** unchanged: the exact three-candidate selection of the plan §8; its escaped-envelope compression and baseline-4 dictionary are as already specified; **baseline 4's trained dictionary distribution is charged in addition to repository distribution**. Changing the payload would be a new arm, so none is made.
5. **Fold seed:** frozen as seed `"e1e-fold-1"`, hash SHA-256, key = UTF-8 bytes of `seed + "\x00" + conv_id` (§4). Chosen now, before any outside data is split and without inspecting results under other seeds; `e1e-diag-r1` is retired for E1f. The hash only breaks timestamp ties or splits timestamp-less data; the final held-out split is separate from tuning (forward-only block validation inside dev only, §4).

## 6. Arms, lifecycle scenarios, retirement rule
- **Arms** (per-message delivery boundary, same byte-exact oracle): 1 raw (envelope); 3 zstd; 4 zstd trained dict (dict distribution charged); 4b (A1, full rebuild per version); **4b-delta** (§2); 5 E1E-MSG/1 refs; 6 (plan §8); **7 E1F compact**.
- **Lifecycle scenarios (all reported, primary fixed now):** versions V ∈ {1 (static), 5, 20} (§4 schedule); participants 2 (primary), 10; joiners 0 (primary), 3 (one joiner at each of the first three quartiles of the held-out replay). **Primary scenario: V = 5, 2 participants, 0 joiners.** The held-out message set and order are identical in every scenario. All scenarios are reported; none is selected afterward.
- **Reporting:** message bytes and sync/control bytes separately, plus totals, byte-weighted and per message, counts alongside percentages, break-even update and join counts, sources separate.
- **Retirement rule (E1f, in addition to A1):** the byte-saving claim for compact refs (arm 7) is **retired** unless, in the primary scenario on the held-out real data, arm 7's total (messages + framing + declarations/rejects/retransmits + sync) is **strictly smaller than the totals of both 4b-delta and arm 6**. A win over 4b but not over 4b-delta is reported as "wins only against A1's full-rebuild policy". Failures in non-primary scenarios are reported but do not change the primary decision.

## 7. Dev screening (a heuristic, not a proof)
- **Stage 1 (coverage):** covered bytes by curated entries ÷ total bytes of eligible dev messages (denominator frozen: eligible = ≤ 65,536 B; oversized and skipped entries counted separately) must be ≥ **20%**. Below it, report as a **dev-screening result**, not held-out evidence.
- **Stage 2 (rough estimate):** estimate arm 7's dev total assuming each covered span costs the average ref cost measured in dev, and compare with the measured 4b-delta dev total. This is a **heuristic**: it relies on measured, not proven, costs and does not bound what any compact segmentation could achieve. A failing estimate is reported as such and does **not** prove refs lose; whether to build the codec then is a decision for Stefan with GPT's view. The gate licenses nothing about held-out performance.

## 8. Data and gates (unchanged in substance)
- Dev: synthetic (public) and Glyph-own sanitised (private; single-operator; development only). No savings claim from these.
- Held-out: one pass, outside real messages only, not spent until ≥ 50 messages, ≥ 20 conversations, ≥ 3 contributors (or Stefan, GPT and Claude agree the corpus is representative). The four Tessera messages stay in reserve.
- No compute-heavy job without Stefan's go; E1f runs on the box CPU in seconds to minutes. Counts, not percentages alone; thresholds not changed after results.

## 9. Questions for GPT (extra round 3)
Q1. Does §3.3 (charged epoch, two retained snapshots, E_STALE reject) fix the cross-direction race? Anything it still lets through?
Q2. Do §3.1 (varint length prefix, widths, limits) and the byte fixtures in §3.5 (with expected decoded outputs and error codes) remove the framing inconsistency?
Q3. Is §7 acceptable as a heuristic with the proof language removed?
Q4. Do §3.5 (enumeration, template endpoints, tries and caps) and §4 (one split/schedule rule, template grouping and precedence, leave-one-prefix-out only) resolve your four curation/matching blockers? Please flag only truly blocking issues.
If APPROVE: freeze only after Stefan, and Claude and Grok have seen it; no tag now.

## 10. Change map (GPT r1 required changes → resolution)
Q1: sync wording §2; 4b-delta §2/§6; retirement rule §6; "by construction" replaced §1.
Q2: opcodes, varint, zigzag §3.2; version-delta removed §3.2; arg order/limits/ordinals §3.2; framing & trailing-bytes semantics §3.1–3.2; limits & empty/non-UTF-8 §3.1–3.2; ordinal binding & snapshot barrier §3.3; 7z deferred §3.4; segmented search/tie-break §3.5; "raw" = JSON envelope §3.1; byte examples §3.5.
Q3: mining definitions, objective, grid §4; prefix schedule §4; scenarios §6; ceiling defined §7; floor & denominator §7; wording "proxy" header.
Q4: §5.1–5.5.

## 11. Change map, GPT r2 required changes → resolution
1 snapshot race: §3.3 (charged epoch + retained snapshots), §3.2 (epoch in frame), §3.5 fixtures.
2 framing: §3.1 (varint length prefix, widths, max sizes), §5.1 consistent.
3 bound: §7 (heuristic only, proof claim removed).
4 determinism: one schedule §4/§6; template grouping and precedence §4; segmented template endpoints §3.5; candidate enumeration order and counting §3.5; split vs tuning reconciled §4/§5.5.
Suggestions taken: decoded outputs and error codes with fixtures, width-overflow precedence (§3.2/§3.5); 8-param limit unchanged (§3.1).

## 12. Change map, GPT r3 required changes → resolution
1 §5.1 now uses the §3.1 varint prefix of the actual length everywhere. 2 §4 tuning is forward-only over disjoint blocks. 3 §4 uses a fixed provisional ordinal cost of 2 bytes and per-occurrence matched length `len(o)`. Suggestions taken: retention wording, epoch-byte fixture wording, S1/ordinal-127 statement, 127/128 prefix fixture, header pointer.
