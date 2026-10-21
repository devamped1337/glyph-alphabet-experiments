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
  300 msgs / 30 convs) and `data/glyph_own_dev_r1.jsonl` (sanitised Glyph-own traffic, 187 msgs / 97 convs,
  single-operator). Measurements on these describe those corpora only (sanitisation changes compressibility).
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
  epoch/index negotiation if a compact wire form is adopted (§8), reject frames, and fallback retransmissions. The
  current `Link.totals()` counts message, reject and fallback frames only; the measurement code must add declaration
  frames (one per receiver per snapshot change, plus one per conversation start) before it is used.
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
the escaped-JSON envelope also matter. **Decision required before the held-out audit** (from dev data only): (a) a
compact length-prefixed wire form for refs and raw (e.g. a short snapshot epoch negotiated at sync instead of a
per-message 64-hex snapshot digest, a short entry handle instead of id+digest, raw bytes un-escaped), keeping full
digests in artifacts and declarations, with its negotiation bytes charged (§6); and (b) a send-ref-only-if-smaller
policy (`require_smaller=True`). Any new wire form needs a spec revision and re-review.

## 9. Test cases to add with the measurement code
- zstd failure: `train_dictionary` raising → "not trainable" path (§7); zstd version recorded and a mismatch flagged;
  truncated frame → decode error or byte mismatch, both caught by the offline oracle and charged as raw re-send;
  with `write_checksum=True`, a corrupted frame is detected at runtime; with `write_dict_id=True`, a wrong dictionary
  is detected at runtime; with the headline settings these are detected only by the offline oracle (asserted as such).
- inflation: a message where the ref is larger than raw → raw under `require_smaller=True`; empty message; 1-byte
  message; non-ASCII-heavy message (escape blow-up); ref exactly equal to raw size (tie → raw).
- gzip determinism (`mtime=0`) and byte-exact decompression for every baseline.

## 10. Open items (not Stefan decisions)
- Choose and spec the compact wire form (§8) on dev data; GPT and Grok review of this plan; then freeze with code hash.
- Real evaluation data collection remains the blocker for any savings claim.
