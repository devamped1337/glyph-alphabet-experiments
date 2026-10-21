# E1e byte-audit plan — DRAFT, NOT FROZEN

Status: draft for GPT and Grok review. Not frozen, not tagged, PR #2 not merged. A freeze requires GPT and Grok
review of this plan first. CPU only; no models other than GPT review via the Codex CLI.
Builds on: `SPEC_E1E_REPO_1.md`, `README_MECHANICS.md` (fixture-tested mechanics draft), `reviews/gpt_E1e_pilot_r1.md`,
`reviews/gpt_E1e_code_r1..r5.md`, `reviews/grok_E1e_code_r1.md`.

## 1. Decisions recorded
- **2026-10-21 21:08 AEDT — Stefan:** per-message compression is the **primary** comparison; a persistent stream is
  **secondary**.
- **2026-10-21 21:08 AEDT — Stefan:** cleaned-up copies of Glyph's own agent-to-agent traffic (executor handoff prompts
  and reports, GPT/Codex review requests) may be used as **development-only** data.

## 2. Data and provenance rules
- Evaluation data must be **real, permitted agent-to-agent messages from outside the single operator**. None are
  collected yet (`COLLECTION_LOG.md`). **No savings claim of any kind without real evaluation data.**
- Development-only sources, never evaluation or held-out: `data/synthetic_gpt_r1.jsonl` (GPT-generated synthetic,
  300 msgs / 30 convs) and `data/glyph_own_dev_r1.jsonl` (sanitised Glyph-own traffic, 186 msgs / 96 convs,
  single-operator). Measurements on these describe those corpora only (sanitisation changes compressibility).
- Each record carries provenance; dev records are excluded from evaluation by source, not by sampling.

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
3. per-message zstd, no dictionary (`zstandard==0.23.0`, libzstd 1.5.6, level fixed in dev, default 19 proposed,
   `write_content_size=False, write_checksum=False, write_dict_id=False`);
4. per-message zstd with a dictionary trained only on dev messages (`zstandard.train_dictionary`, size and level fixed
   in dev; dictionary bytes charged, §6);
5. repository refs + params + raw fallback (E1E-MSG/1 wire, as implemented);
6. refs + per-message zstd on the wire bytes, if tested (declared before held-out replay).
Each baseline reports the actual serialized bytes of every message; every result is a reconstruction checked byte-exact.

## 5. Compression mode
- **Primary (Stefan, §1): per-message.** Codec state is reset for every message; each message must decode alone.
- **Secondary: persistent stream** per directed sender→receiver link. Endpoints: one zstd compression context per
  directed link, created at first message. Flush point: `FLUSH_BLOCK` after every message (each message decodable on
  arrival = its delivery boundary); bytes charged per message are the bytes emitted up to that flush.
  Reset: a new context (and its frame header) on link reconnect or receiver rejoin; a joiner always starts a fresh
  context. Join: a receiver joining mid-conversation cannot use prior stream state; its first message is charged as a
  new stream. Reset/reconnect events are predeclared by the replay script (per conversation start) and charged.
  Whole-transcript compression is not a baseline.

## 6. Accounting (actual artifacts only, no scaled ratios)
- Storage per participant: full snapshot bytes; dictionary bytes.
- Distribution: initial full sync to every receiver; maintainer upload of every published artifact; each delta;
  each joiner's full sync; zstd-dictionary distribution to every participant (same charging rules as the repository).
- Messages: forward bytes; reject frames; fallback retransmissions (as `Link.totals()` records); both directions.
- CPU time: indexing, encoding, decoding, replay; hardware recorded. Zero new model inference in the audit.
- Report coverage, fallback causes and exact-reconstruction failures; total traffic; break-even on the observed
  replay. Lifecycle scenarios (updates/joins) are declared in advance and reported separately from measured traffic.

## 7. Predeclared rule: dictionary-training failure or insufficient dev corpus
- If `train_dictionary` raises, or the dev split has < 50 messages or < 8 conversations, baseline 4 is reported as
  **"not trainable"** and baseline 3 stands as the strongest zstd baseline; no retries with other sizes on held-out
  data. Dictionary size is chosen from {1024, 2048, 4096, 8192} bytes by dev-only cross-validation (by conversation);
  if every size fails, "not trainable". No tuning on held-out results.
- If the real corpus has < 20 conversations in total, the audit is reported as descriptive only.

## 8. Short-message inflation decision point
Measurement `measurements/dev_inflation_synthetic.json` (tool `tools/dev_inflation.py`; development diagnostic on the
synthetic set, in-sample dictionary of 8 entries by a deterministic rule; **not a savings claim**):
- 300 messages; 19 encoded as refs, 281 sent raw; all 300 round trips exact.
- Refs larger than the raw message bytes: **19/19** with full 64-hex digests, **19/19** with hypothetical 12-hex,
  **19/19** with hypothetical 8-hex, **19/19** even with digests removed (hypothetical 0-hex framing only).
  Refs larger than the raw envelope: 19/19, 19/19, 19/19, 13/19 respectively.
- The raw envelope itself adds overhead: 47,194 envelope bytes for 32,225 message bytes (+46%), from JSON framing and
  `\u` escaping of non-ASCII and control characters.
Consequence: shortening digests alone does not fix inflation on short messages; the escaped-JSON framing dominates.
**Decision required before the held-out audit** (from dev data only): (a) a compact binary/length-prefixed wire form for
refs and raw (e.g. a short snapshot epoch negotiated at sync instead of a per-message 64-hex snapshot digest, entry
index instead of id+digest, raw bytes un-escaped), keeping full digests in artifacts and declarations; and (b) a
send-ref-only-if-smaller policy (`require_smaller=True`). Any new wire form needs a spec revision and re-review.

## 9. Test cases to add with the measurement code
- zstd failure: corrupt/truncated zstd frame → decode error, message re-sent raw and charged; dictionary-id mismatch;
  `train_dictionary` failure → "not trainable" path; zstd version recorded and mismatch flagged.
- inflation: a message where the ref is larger than raw → raw under `require_smaller=True`; empty message; 1-byte
  message; non-ASCII-heavy message (escape blow-up); ref exactly equal to raw size (tie → raw).
- gzip determinism (`mtime=0`) and byte-exact decompression for every baseline.

## 10. Open items (not Stefan decisions)
- Choose and spec the compact wire form (§8) on dev data; GPT and Grok review of this plan; then freeze with code hash.
- Real evaluation data collection remains the blocker for any savings claim.
