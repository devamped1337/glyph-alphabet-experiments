# E1f proposal, revision 2 — curated long entries + compact references vs zstd with the same dictionary
Revision 2 (2026-10-23), answering `reviews/gpt_E1f_proposal_r1.md` (r1 text of this file: commit 1a7323f). §10 maps every
GPT required change to where it is resolved. Status: DRAFT, not frozen, not tagged, nothing run. CPU only; no Kaggle/GPU;
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
- Each message is transported in one frame whose length is supplied by the transport and charged as a **2-byte big-endian
  length prefix** for every arm identically (so framing cancels in comparisons; reported separately). The decoder sees exactly the frame bytes.
- First byte: `0x7B` `{` = existing E1E-MSG/1 JSON envelope ("raw" in this document always means the existing JSON raw
  envelope, never bare message bytes); `0x28 0xB5 0x2F 0xFD` = zstd frame (baselines 3/4/4b/6); `0x01` = E1F compact. Any other first byte: E_SCHEMA.
- Limits: encoded frame ≤ 65,536 B; decoded message ≤ 65,536 B (`MAX_MESSAGE_BYTES`); ≤ 256 segments; ≤ 16 args per REF;
  any declared length is checked against the remaining frame bytes and the limits **before** allocation.

### 3.2 Compact body (opcodes numeric)
`0x01`, then 1..256 segments, then the frame ends. The segment list is exactly the bytes after `0x01`; a segment that is
incomplete is E_TRUNCATED; there is no end marker: bytes that parse as a further valid segment ARE a further segment; bytes
that do not parse are E_TRUNCATED (not "trailing bytes"). Empty segment list (frame = `0x01` alone) is invalid (E_SCHEMA);
the empty message is sent as the raw envelope.
- `0x01 REF` : `varint ordinal` `args…`. **Version is always the entry's version in the declared snapshot** (no version delta in E1f; historical bodies are never needed, joiners need only the current snapshot).
- `0x02 LIT` : `varint n` (1 ≤ n) then n bytes, which MUST be valid UTF-8 on their own. A message that is not valid UTF-8 or whose literal split cannot be made on UTF-8 boundaries is sent raw/zstd, never compact.
- Any other opcode: E_SCHEMA.
- **varint**: unsigned LEB128 (7 bits per byte, little-endian groups, high bit = continuation), **shortest encoding required** (a final 0x00 continuation group is E_NONCANONICAL), maximum 5 bytes and value ≤ 2^32−1 (overflow/over-width = E_RANGE).
- **zigzag** for `int` args: n ↦ (n<<1) xor (n>>63) over the existing `int` domain `-?(0|[1-9][0-9]{0,17})` (|n| < 10^18), carried as varint with the same limits widened to 10 bytes / 2^64−1; values outside the domain = E_PARAM.
- **Arguments** appear in the order of the entry's declared `params`, one per param, no names, none omitted: `int` → zigzag varint; `word` → varint byte length + bytes matching `[A-Za-z0-9_.-]+` (length ≥ 1); `text` → varint byte length (≥ 1) + valid UTF-8 bytes (may contain newlines and braces). Lengths are in bytes.
- **Ordinal** = zero-based index into the declared snapshot's entry list sorted by `id` ascending by Unicode code point (the order of `full_bytes()`). Out of range = E_UNKNOWN_REF. Literal entries have no params; template entries are filled exactly as E1E-REPO/1 (placeholder grammar, `{{`/`}}` escapes). Entries with a body > 16,384 code points do not exist (§5.3).
- Reconstruction = concatenation of segment outputs; the result must be ≤ 65,536 B.
### 3.3 Snapshot binding and transitions
- Ordinals mean nothing without the snapshot. A sender encodes only against the snapshot the receiver last declared (E1E rule) and holds that exact snapshot, else sends raw.
- **Ordered snapshot barrier:** a declaration (receiver→sender, charged as in E1E) takes effect for compact frames that the sender emits **after** receiving it; the transport delivers a link's frames in order; a compact frame is decoded against the snapshot declared by the receiver's latest declaration **sent before that frame was received**. A receiver that changes snapshot sends a new declaration and then rejects (E_STALE, charged) any compact frame the sender produced against the old one; the sender re-sends as raw envelope (charged, as E1E). This is the same reject/retransmit accounting as E1E-MSG/1, and the replay script predeclares every snapshot-change event; no per-message epoch is carried, so a stale ordinal cannot be accepted silently only because the barrier and ordered delivery are part of the declared model (tested with injected races).
### 3.4 Deferred: the 7z variant (compact + zstd on the literal residue)
Not part of E1f. If arm 7 shows promise, 7z is specified in a separate amendment with its full grammar and re-reviewed. Arm list below omits it.
### 3.5 Deterministic segmented encoder
- Candidate positions: for each entry (literal or template) in the declared snapshot, every occurrence of a **literal entry body** in the message and every full-match of a template, found by exact search; template matching uses E1E-REPO/1's matcher (step budget 20000, ambiguity skip) at each start offset where the template's leading literal occurs.
- Selection: left-to-right greedy; at each offset take the candidate with the greatest **bytes saved = covered message bytes − REF bytes**, ties by longer span, then lower ordinal; take only candidates with bytes saved > 0; unmatched gaps become LIT. Overlapping candidates are never both taken (greedy consumption). Total work budget: 200,000 comparison steps per message, exhaustion → send non-compact.
- Every compact frame is decoded by the real decoder and must equal the original; otherwise it is discarded (same verification rule as E1E).
- **Send rule:** among {compact, raw envelope} send the strictly smaller; ties → raw envelope.
- Normative byte examples (added to the spec as tests): literal-only (`01 02 03 61 62 63`), reference-only (`01 01 00` for ordinal 0, no params), mixed (`01 02 02 68 69 01 05`), and malformed (`01` alone; `01 02 05 61`; `01 01 FF FF FF FF FF 01`; `01 01 80 00` non-canonical; `01 03 00`; `00`).

## 4. Curation (deterministic, dev-only, fully specified before data)
- **Source:** dev messages only, ordered chronologically by conversation first-message time (ties: sha256 of the conversation key encoded as UTF-8). Held-out and outside real messages are never read.
- **Prefix schedule (frozen):** dev conversations are split in order into P equal-size prefixes (P in {2, 5, 20}, i.e. the cadence scenarios in §6; the last prefix may be smaller). The snapshot used while replaying held-out message i is built **only** from dev prefixes ≤ its scheduled version; no snapshot contains material from a later prefix.
- **Candidate generation:**
  - *Line blocks:* maximal runs of ≥ 1 consecutive `\n`-separated lines (including their joining `\n`), length ≥ L bytes.
  - *Byte n-gram runs:* for each pair of dev messages from different conversations, maximal common substrings ≥ L bytes via suffix-automaton over the UTF-8 text, cut to code-point boundaries.
  - *Templates:* a line block occurring in ≥ k conversations that differs only in maximal digit-runs (`int`), `[A-Za-z0-9_.-]+` runs (`word`) are generalised by a fixed rule: positions that vary across occurrences become params, ≤ 4 params; must satisfy the unique-parse rule of §7 of the spec, else discarded.
  - A candidate must occur in ≥ k distinct conversations (counted per conversation once) and be ≤ 16,384 code points; larger are skipped and counted (reported: number and bytes excluded).
- **Objective and selection:** greedy by estimated net gain `G(c) = Σ_{occurrences in dev prefix messages} (len(c) − refcost(c)) − entrycost(c)` where `refcost` = 1 + ordinal varint bytes + arg bytes (as encoded, averaged over dev occurrences), `entrycost` = bytes of the entry's serialized artifact record × (1 + number of joiners in the scenario); after each pick, occurrences overlapped by already-chosen entries are removed and G recomputed (marginal overlap). Pick max G; ties by longer length, then lexicographically smaller bytes; stop when G ≤ 0 or when the entry count cap C is reached. Same entries feed arms 4b, 4b-delta and 7.
- **Parameter grid (declared now, tuned in dev only by leave-one-prefix-out):** L ∈ {32, 64, 128, 256}, k ∈ {2, 3}, C ∈ {50, 200, 1000}. Tuning criterion: lowest total of arm 7 (messages + sync) on dev leave-one-prefix-out folds; ties by smaller L, then k, then C. The chosen triple is frozen with the code hash before any held-out replay and **no value outside the grid is considered**.
- Provenance: every entry is constructed with an explicit `prov` (`synthetic`, `glyph_own_dev`, `real_dev`), construction without one raises; each entry keeps its source conversation lineage in the build manifest. An entry mined across sources of different `prov` is **not allowed** (candidates occurring across mixed sources are mined per source and kept separate).

## 5. Fixing the prerequisites (GPT r1 §Q4)
1. **> 64 KiB messages:** reported as an explicit eligible-message comparison (messages ≤ 65,536 B) plus an all-message total. Oversized messages get one common fallback in **every** arm: the smaller of the baseline-3 zstd frame and the raw envelope, ties to the raw envelope. Because these frames can exceed the 65,536 B frame limit, a 4-byte length prefix is charged instead of the 2-byte one, identically in every arm. Reported separately: count, input bytes, fallback bytes, all-message totals. This is a fallback policy, distinct from each named baseline's native behaviour (refs refuse with E_TOO_LARGE).
2. **Bodies > 16,384 code points:** skipped at candidate generation and counted/reported (entries and covered bytes excluded). E1E-REPO/1 is unchanged; no splitting algorithm.
3. **Provenance:** see §4 (explicit at every construction call; missing raises).
4. **Baseline 6:** unchanged: the exact three-candidate selection of the plan §8; its escaped-envelope compression and baseline-4 dictionary are as already specified; **baseline 4's trained dictionary distribution is charged in addition to repository distribution**. Changing the payload would be a new arm, so none is made.
5. **Fold seed:** frozen as seed `"e1e-fold-1"`, hash SHA-256, key = UTF-8 bytes of `seed + "\x00" + conv_id`, fold = first 8 bytes big-endian mod 5 (tuning folds 0–3 leave-one-fold-out, fold 4 = held-out candidate pool). Chosen now, before any outside data is split and without inspecting results under other seeds (the dev diagnostic's "e1e-diag-r1" is retired for E1f). Tuning folds and the final held-out split are separate.

## 6. Arms, lifecycle scenarios, retirement rule
- **Arms** (per-message delivery boundary, same byte-exact oracle): 1 raw (envelope); 3 zstd; 4 zstd trained dict (dict distribution charged); 4b (A1, full rebuild per version); **4b-delta** (§2); 5 E1E-MSG/1 refs; 6 (plan §8); **7 E1F compact**.
- **Lifecycle scenarios (all reported, primary fixed now):** versions V ∈ {1 (static), 5, 20} (= prefix schedule P); participants 2 (primary), 10; joiners 0 (primary), 3 (one joiner at each of the first three quartiles of the held-out replay). **Primary scenario: V = 5, 2 participants, 0 joiners.** The held-out message set and order are identical in every scenario. All scenarios are reported; none is selected afterward.
- **Reporting:** message bytes and sync/control bytes separately, plus totals, byte-weighted and per message, counts alongside percentages, break-even update and join counts, sources separate.
- **Retirement rule (E1f, in addition to A1):** the byte-saving claim for compact refs (arm 7) is **retired** unless, in the primary scenario on the held-out real data, arm 7's total (messages + framing + declarations/rejects/retransmits + sync) is **strictly smaller than the totals of both 4b-delta and arm 6**. A win over 4b but not over 4b-delta is reported as "wins only against A1's full-rebuild policy". Failures in non-primary scenarios are reported but do not change the primary decision.

## 7. Analytical gate before building the codec (dev only)
- **Stage 1 (coverage):** frozen coverage floor = **covered bytes by curated entries ÷ all bytes of dev prefix messages ≥ 20%** over eligible messages (denominator = total bytes of eligible dev messages; oversized and skipped counted separately). Below it: stop, report as a **dev-screening result**, not held-out evidence.
- **Stage 2 (optimistic bound):** arm 7's total is lower-bounded by assuming each covered span costs the minimum conceivable (REF = 2 bytes, no args), each uncovered byte costs 0.25 bytes (a 4:1 floor, stricter than any measured ratio), framing and sync at their measured values. If this *lower bound* on arm 7's total is not strictly smaller than the **measured** 4b-delta total on dev, stop (a lower bound that loses proves refs lose in that dev setting). 4b is measured, not span-attributed. If the gate passes it only licenses building the codec.

## 8. Data and gates (unchanged in substance)
- Dev: synthetic (public) and Glyph-own sanitised (private; single-operator; development only). No savings claim from these.
- Held-out: one pass, outside real messages only, not spent until ≥ 50 messages, ≥ 20 conversations, ≥ 3 contributors (or Stefan, GPT and Claude agree the corpus is representative). The four Tessera messages stay in reserve.
- No compute-heavy job without Stefan's go; E1f runs on the box CPU in seconds to minutes. Counts, not percentages alone; thresholds not changed after results.

## 9. Questions for GPT (round 2 of 2)
Q1. Does §2 (4b-delta, wording of sync wins) and §6's retirement rule resolve your Q1 changes?
Q2. Is §3 (3.1–3.3, 3.5) precise enough to implement and fuzz? Is the barrier in §3.3 acceptable without a per-message epoch?
Q3. Do §4 and §7 resolve your Q3 changes (reproducibility, no leakage, a valid optimistic bound)?
Q4. Do §5.1–5.5 match your preferred resolutions?
If APPROVE: freeze only after Stefan, and Claude and Grok have seen it; no tag now.

## 10. Change map (GPT r1 required changes → resolution)
Q1: sync wording §2; 4b-delta §2/§6; retirement rule §6; "by construction" replaced §1.
Q2: opcodes, varint, zigzag §3.2; version-delta removed §3.2; arg order/limits/ordinals §3.2; framing & trailing-bytes semantics §3.1–3.2; limits & empty/non-UTF-8 §3.1–3.2; ordinal binding & snapshot barrier §3.3; 7z deferred §3.4; segmented search/tie-break §3.5; "raw" = JSON envelope §3.1; byte examples §3.5.
Q3: mining definitions, objective, grid §4; prefix schedule §4; scenarios §6; ceiling defined §7; floor & denominator §7; wording "proxy" header.
Q4: §5.1–5.5.
