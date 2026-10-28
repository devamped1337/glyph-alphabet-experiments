# E1e byte-audit plan — DRAFT, NOT FROZEN

Status: draft for GPT and Grok review. Not frozen, not tagged, PR #2 not merged. A freeze requires GPT and Grok
review of this plan first. CPU only; no models other than GPT review via the Codex CLI.
Builds on: `SPEC_E1E_REPO_1.md`, `README_MECHANICS.md` (fixture-tested mechanics draft), `reviews/gpt_E1e_pilot_r1.md`,
`reviews/gpt_E1e_code_r1..r5.md`, `reviews/grok_E1e_code_r1.md`.

## Freeze record
Freeze pending GPT review of this amendment (2026-10-23). Approvals so far: GPT round 6 at `76ea550`; Grok r1 GO
recorded at `6889a53` (`reviews/grok_E1e_audit_plan_r1.md`). Stefan's decisions: 2026-10-21 — per-message primary,
Glyph-own traffic development-only; 2026-10-23 — `require_smaller` (§8). Once frozen, any later change needs a dated
amendment.

## 1. Decisions recorded
- **2026-10-21 21:08 AEDT — Stefan:** per-message compression is the **primary** comparison; a persistent stream is
  **secondary**.
- **2026-10-21 21:08 AEDT — Stefan:** cleaned-up copies of Glyph's own agent-to-agent traffic (executor handoff prompts
  and reports, GPT/Codex review requests) may be used as **development-only** data.

## 2. Data and provenance rules
- Evaluation data must be **real, permitted agent-to-agent messages from outside the single operator**. None are
  collected yet (`COLLECTION_LOG.md`). **No savings claim of any kind without real evaluation data.**
- Development-only sources, never evaluation or held-out: `data/synthetic_gpt_r1.jsonl` (GPT-generated synthetic,
  300 msgs / 30 convs, public) and the **private, box-only** sanitised Glyph-own corpus (188 msgs / 98 convs,
  single-operator; only `data/glyph_own_dev_r1_stats.json` aggregates and its sha256 are committed). Measurements on these describe those corpora only (sanitisation changes compressibility).
- **Privacy:** Glyph-own dev data and all real messages are kept private on the box and never committed; results
  report aggregates only (counts, byte totals, per-baseline totals, rates), unless a contributor explicitly allows
  publication of their messages. The regex sanitiser is defence in depth, not the privacy guarantee.
- Each record carries provenance; dev records are excluded from evaluation by source, not by sampling.
- Entries carry `prov` (`synthetic`, `glyph_own_dev`, `real_dev`; SPEC §3); source conv_id lineage for every (id, v)
  is kept in a build manifest. No entry is ever derived from evaluation data.

## 3. Split
- Split by **whole conversation/workflow**, chronologically where timestamps exist (earliest → dev, latest → held out);
  otherwise by a seeded hash of conv_id declared before the data is seen. Proposed: 60% dev / 40% held-out of the
  real corpus, by conversation count.
- Dev only: building literal/template entries, tuning candidate rules, choosing compression levels, training zstd
  dictionaries. Freeze all of these (with code hash) before the held-out replay. Held-out data is touched once.
- Retrieval never receives the correct entry at evaluation; the codec's own bounded candidate rule is used.

## 4. Baselines (all at the same per-message delivery boundary)
1. raw message bytes (no envelope);
2. per-message gzip level 9 (`gzip.compress(m, 9, mtime=0)`, stdlib; also report raw deflate without header);
3. per-message zstd, no dictionary (`zstandard==0.23.0`, libzstd 1.5.6, level fixed in dev, default 19 proposed).
   Frame parameters for the headline numbers: `write_content_size=False, write_checksum=False, write_dict_id=False`
   (smallest frames). Because these settings cannot guarantee runtime detection of corruption or a wrong dictionary,
   correctness in the audit is established by the **offline byte-exact oracle** (every decoded message compared with
   the original). A secondary run with `write_checksum=True, write_dict_id=True` reports the cost of runtime
   integrity (+4 bytes checksum, + dict-id bytes per frame);
4. per-message zstd with a dictionary trained only on dev messages (`zstandard.train_dictionary`, size and level fixed
   in dev; dictionary bytes charged, §6);
5. repository refs + params + raw fallback (E1E-MSG/1 wire, as implemented);
6. refs + per-message zstd on the wire bytes, if tested (declared before held-out replay).
Each baseline reports the actual serialized bytes of every message; every result is a reconstruction checked byte-exact.

## 5. Compression mode
- **Primary (Stefan, §1): per-message.** Codec state is reset for every message; each message must decode alone.
- **Secondary: persistent stream** per directed sender→receiver link. Endpoints: one zstd compression context per
  directed link, created at first message. Flush point: `COMPRESSOBJ_FLUSH_BLOCK` after every message (each message
  decodable on arrival = its delivery boundary); bytes charged per message are the bytes emitted up to that flush.
  Reset: a new context (and its frame header) at each conversation start, link reconnect or receiver rejoin; a joiner
  always starts a fresh context and cannot use prior stream state. Termination: at conversation end the frame is
  finished (`COMPRESSOBJ_FLUSH_FINISH`) and the closing bytes are charged to that link. Reset/reconnect events are
  predeclared by the replay script and charged. Whole-transcript compression is not a baseline.

## 6. Accounting (actual artifacts only, no scaled ratios)
- Topology: one maintainer publishes to a hub; every participant (senders and receivers) downloads from the hub.
  Charged: maintainer upload of every artifact once; one download per participant per artifact (initial full sync,
  each delta, each joiner's full sync). Senders are participants and are charged like receivers. The same topology
  and rules apply to zstd dictionaries (baseline 4) and to repository artifacts (baselines 5–6).
- Storage per participant: full snapshot bytes; dictionary bytes.
- Control traffic: every receiver snapshot declaration (canonical bytes of its declaration message), any snapshot
  epoch/index negotiation if a compact wire form is adopted (§8), reject frames, and fallback retransmissions. `Link.totals()`
  now counts declaration frames (`declare`, whenever the declaration used on a link changes); the replay must also
  open a new link (hence a new declaration) at each conversation start.
- Messages: forward bytes in both directions.
- CPU time: indexing, encoding, decoding, replay; hardware recorded. Zero new model inference in the audit.
- Report coverage, fallback causes and exact-reconstruction failures; total traffic; break-even on the observed
  replay. Lifecycle scenarios (updates/joins) are declared in advance and reported separately from measured traffic.

## 7. Predeclared rule: dictionary training and an insufficient dev corpus
- Eligibility: baseline 4 is attempted only if the dev split has ≥ 50 messages and ≥ 8 conversations; otherwise it is
  reported as **"not trainable (insufficient dev corpus)"** and baseline 3 is the strongest zstd baseline.
- Size selection (dev only): candidate sizes {1024, 2048, 4096, 8192} bytes; 4-fold cross-validation grouped by
  conversation (folds by seeded hash of conv_id, seed fixed in the freeze). For each size and fold, train on 3 folds and
  score the 4th by total per-message compressed bytes **plus the dictionary bytes charged per §6**. A fold where
  training raises counts that size as failed for that fold. A size is eligible only if it trains in all 4 folds.
  Choose the eligible size with the lowest mean score; ties go to the smaller size. If no size is eligible:
  "not trainable".
- Final: train once on the full dev split at the chosen size. If that raises: "not trainable". No retries, no other
  sizes, nothing tuned on held-out data.
- If the real corpus has < 20 conversations in total, the audit is reported as descriptive only.

## 8. Short-message inflation decision point
Measurement `measurements/dev_inflation_synthetic.json` (tool `tools/dev_inflation.py`; development diagnostic on the
synthetic set, in-sample dictionary of 8 entries by a deterministic rule; **not a savings claim**):
- 300 messages; 19 encoded as refs, 281 sent raw; all 300 round trips exact.
- Refs larger than the raw message bytes: **19/19** with full 64-hex digests, **19/19** with hypothetical 12-hex,
  **19/19** with hypothetical 8-hex (sha256: prefixes kept), and **19/19** even with both digest values removed
  entirely. Refs larger than the raw envelope: 19/19, 19/19, 19/19 and **9/19** respectively.
- Of the 3,719 bytes by which the 19 refs exceed their raw messages, 2,432 are digest hex digits; the remainder
  (keys, prefixes, ids, versions, args, quoting/escaping) is not separated by this diagnostic.
- The raw envelope adds 47,194 − 32,225 bytes (+46%) over the message bytes (JSON framing and `\u`/control escaping).
Consequence: shorter digests reduce but do not remove inflation on short messages; the remaining reference metadata and
the escaped-JSON envelope also matter.

*[Superseded by the 2026-10-23 decision below; kept as the historical record.]*
**Decision required before the held-out audit** (from dev data only): (a) a
compact length-prefixed wire form for refs and raw (e.g. a short snapshot epoch negotiated at sync instead of a
per-message 64-hex snapshot digest, a short entry handle instead of id+digest, raw bytes un-escaped), keeping full
digests in artifacts and declarations, with its negotiation bytes charged (§6); and (b) a send-ref-only-if-smaller
policy (`require_smaller=True`). Any new wire form needs a spec revision and re-review.

**Decision (2026-10-23 08:57 AEDT — Stefan): `require_smaller`.** For each message, if the E1E reference encoding (and
refs+zstd where applicable) is not strictly smaller in bytes than the raw/plain fallback form at the per-message
delivery boundary, the sender sends the plain fallback instead, and the measurement charges the fallback bytes. The
compact wire form (a) is deferred to a possible later experiment (E1f); E1E-REPO/1 is unchanged.
Implementation item (GPT review before measurement): `e1e/codec.py` `encode()` already has a `require_smaller`
parameter (compares the ref against the raw envelope, reason `ref_not_smaller`) but defaults to `False`; the
measurement code must pass `require_smaller=True`, and the refs+zstd comparison at the delivery boundary is not yet
implemented.

### Exact selection rule
- **Baseline 5 (refs, uncompressed):** send the ref envelope only if it is strictly smaller than `raw_wire(msg)`; ties
  go to raw.
- **Baseline 6 (refs + per-message zstd):** three candidates: (i) zstd(ref envelope); (ii) zstd(raw envelope) at the
  same level and §4 frame settings, using the baseline-4 dictionary if §7 permits one (otherwise no dictionary); and
  (iii) the uncompressed raw envelope. Send the smallest. Ties are broken in favour of (iii), then (ii), then (i). If
  there is no ref match, only (ii) and (iii) compete.
- **Framing:** no selector byte. An uncompressed envelope is canonical JSON starting with `{` (0x7B); every zstd frame
  starts with the magic bytes `28 B5 2F FD`; after decoding, the envelope's `type` field distinguishes ref from raw.
  The magic number and frame header are counted. Any transport length prefix is counted identically for all candidates.
- **Charging:** exactly the bytes of the selected first send, plus any reject or retransmit bytes. Declarations,
  artifacts, dictionaries and lifecycle traffic are charged separately as in §6. Candidates that are not sent are not
  charged.

### Pre-measurement implementation items (GPT review required before measurement)
- Wire `Link.transmit()` to `encode(..., require_smaller=True)`.
- Implement the baseline-6 three-way selection above.
- Billing as above.
- Tests: ties; Unicode/base64 envelope overhead; compressed-size flips in both directions; byte-exact round trips
  through the real send path.

## 9. Test cases to add with the measurement code
- zstd failure: `train_dictionary` raising → "not trainable" path (§7); zstd version recorded and a mismatch flagged;
  truncated frame → decode error or byte mismatch, both caught by the offline oracle and charged as raw re-send;
  with `write_checksum=True`, a corrupted frame is detected at runtime; with `write_dict_id=True`, a wrong dictionary
  is detected at runtime; with the headline settings these are detected only by the offline oracle (asserted as such).
- inflation: a message where the ref is larger than raw → raw under `require_smaller=True`; empty message; 1-byte
  message; non-ASCII-heavy message (escape blow-up); ref exactly equal to raw size (tie → raw).
- gzip determinism (`mtime=0`) and byte-exact decompression for every baseline.

## 10. Open items (not Stefan decisions)
- GPT review of the 2026-10-23 amendment; then freeze with code hash. (Compact wire form deferred to E1f, §8.)
- Real evaluation data collection remains the blocker for any savings claim.

## Amendment A1 (2026-10-23): baseline 4b
Dated amendment, approved by Stefan on 2026-10-23 after Claude's review noted the gap. It adds one baseline and one
decision rule; nothing else in §§1–10 changes. Implemented in `e1e/baselines.py` (tests: `tests/test_baselines.py`).

**Baseline 4b — per-message zstd with the repository as a raw-content dictionary.** Purpose: the same shared knowledge
the refs arm uses, with no per-message reference overhead.
- **Source:** only the repository artifact the refs arm uses, at the **same snapshot version** the refs arm uses for
  the message being measured (the snapshot the receiver declared). No dev messages, no other data.
- **Dictionary bytes (deterministic):** take the snapshot's current entries sorted by `id` (ascending, by Unicode code
  point, the same order as `full_bytes()`); for each, the UTF-8 encoding of its `body` field exactly as stored
  (templates keep their `{name}` placeholders and `{{`/`}}` escapes); join with the single separator byte `0x0A` (LF);
  no leading or trailing separator. Built as `zstandard.ZstdCompressionDict(data, dict_type=DICT_TYPE_RAWCONTENT)`;
  no training, no other content. Function: `repo_dict_bytes(state)`.
- **Compression:** the message bytes (same input as baselines 3 and 4), at the **same zstd level and §4 frame settings
  as baseline 4** (headline: `write_content_size=False, write_checksum=False, write_dict_id=False`; the secondary
  integrity run uses the same settings as baseline 4's secondary run). A fresh compressor per message.
- **Decoding** is independent per message: each frame is decompressed alone with the dictionary of the declared
  snapshot; no stream state. Every message is checked byte-exact by the offline oracle (§4).
- **Empty repository** (no entries → zero dictionary bytes): no dictionary is used; 4b is then identical to baseline 3
  and its sync cost is 0. A tiny repository is used as is (no minimum size); no fallback to other content.
- **Sync cost (charged as repository artifact sync, §6):** the maintainer uploads each version's dictionary once;
  every participant downloads it once per version (initial full sync, each new version, each joiner's full sync).
  zstd dictionaries have no delta form, so every new version is charged as a **full rebuild** (the new version's full
  dictionary bytes), never as a delta. Storage per participant: the current dictionary bytes. Function:
  `sync_cost(dict_sizes_by_version, participants, joiners)`.
- **Reporting:** 4b is reported alongside baselines 3, 4, 5 and 6 with the same per-message delivery boundary and
  totals, including the sync cost.

**Decision rule (proposed by Claude, adopted):** if neither baseline 5 nor baseline 6 has a total (messages plus all
charged sync and control bytes, §6) strictly smaller than baseline 4b's total on the held-out real data, the
byte-saving claim for repository IDs is **retired**, and the report states so explicitly. Repository IDs may still be
reported for non-byte properties (exactness, auditability), but not as a byte saving.
