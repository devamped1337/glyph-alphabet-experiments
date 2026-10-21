# SPEC E1E-REPO/1 (repository) and E1E-MSG/1 (messages) — mechanics draft

Status: draft for review. Implemented in `e1e/` and exercised by `tests/` with small synthetic fixtures only.
It makes no corpus measurement and no savings claim. Follows `reviews/gpt_E1e_pilot_r1.md` §3 and §4.

## 1. Message bytes and text encoding
- A message is an arbitrary byte string of at most `MAX_MESSAGE_BYTES` = 65536 bytes. Larger messages are refused
  at the sender (`E_TOO_LARGE`) before any frame is sent or counted.
- Reference encoding applies only to messages that decode as strict UTF-8. A BOM (U+FEFF) is ordinary content.
  Bytes that are not valid UTF-8 are always sent raw (base64).
- No normalisation of any kind: whitespace, CR/LF/CRLF, NFC/NFD and BOMs are preserved exactly. Template literals
  are compared code point by code point, so an NFC entry never matches NFD text and CRLF never matches LF.
- Success means `decode(wire) == original bytes`, byte for byte.

## 2. Serialization (applies to every artifact and message)
- Escaped JSON: `json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)`.
  The bytes are therefore pure ASCII; every non-ASCII code point is a `\uXXXX` escape (surrogate pairs for astral).
- Accepted value types: object (string keys), array, string, integer, true/false/null. Floats, NaN/Infinity and
  strings containing lone surrogates are rejected (`E_SCHEMA`). Maximum nesting depth 8.
- Parsing is strict: non-ASCII bytes or invalid JSON → `E_MALFORMED`; a repeated key in any object → `E_DUP_KEY`;
  input whose bytes differ from the canonical serialization of the parsed value (extra whitespace, other key order,
  unnecessary escapes, trailing bytes) → `E_NONCANONICAL`. Artifact size limit 1 MiB → `E_TOO_LARGE`.
- Digests are `"sha256:" + hex(sha256(canonical bytes))`.

## 3. Entries (immutable ID/version pairs)
```
{"id", "v", "kind", "body", "params", "prov", "digest"}   (exactly these keys)
```
- `id`: `[a-z0-9][a-z0-9._-]{0,63}`, stable across versions. `v`: integer 1..2^31.
- `kind`: `literal` (params must be `[]`) or `template`. `prov`: source class of the material the entry was derived from: `synthetic`, `glyph_own_dev` or `real_dev`
  (entries are never built from evaluation data, so there is no evaluation value). Finer lineage (source conv_ids) is
  kept in a build manifest outside the entry, keyed by (id, v).
- `body`: 1..16384 code points. `params`: list (≤ 8) of `{"name": [a-z][a-z0-9_]{0,31}, "type": int|word|text}`.
- `digest` = sha256 of the canonical object of all other fields — **including `kind` and the parameter schema**,
  so changing a parameter type at the same version is a content change.
- Rule: a new ID starts at `v = 1`; a revision must be exactly current `v + 1`. An `(id, v)` pair, once seen by a
  holder, may never carry a different digest (`E_VERSION_REUSE`). Other version violations → `E_VERSION`.
- Deletion is **deferred** in E1E-REPO/1: entries are only added or revised.

## 4. Snapshot digest
`state_digest = sha256(canonical({"format": "E1E-REPO/1", "version": N, "entries": [full entries sorted by id]}))`.
The empty repository is version 0. Each holder additionally keeps a local `(id, v) → digest` history (not part of the
snapshot digest) used to detect version reuse.

## 5. Artifacts
Full: `{"format":"E1E-REPO/1","type":"full","version":N,"entries":[...sorted by id, unique],"digest":state_digest}`.

Delta: `{"format","type":"delta","base_version","base_digest","target_version","target_digest","entries","digest"}`
- `digest` covers every other delta field (artifact integrity, `E_DIGEST`).
- `base_digest` is the base snapshot's full digest; `target_version = base_version + 1`.
- `entries`: non-empty, sorted by id, no duplicate ids (`E_DUP_ENTRY`; duplicates are never last-wins).

## 6. Transactional operations
All operations validate completely, compute the new state as a separate object, and swap it in only on success.
A rejection leaves the holder's state (version, digest, entries, seen-history) unchanged. Snapshots are
immutable: entries are held privately and only deep copies are exposed, so a published snapshot cannot change under its digest.
- **Full load**: parse, validate every entry, recompute the snapshot digest (`E_DIGEST`). Against a held state: older
  version → `E_STALE`; omitting any held entry → `E_DELETION_DEFERRED`; same version with a different digest → `E_FORK`; content conflicting with held history
  → `E_VERSION_REUSE` / `E_VERSION`. A joiner (version 0) accepts any valid full artifact.
- **Delta apply**: base version must equal held version (`E_STALE` if the delta is ahead, `E_BASE_MISMATCH` if
  behind/replayed); base digest must equal held digest even when versions match (`E_BASE_MISMATCH`); every entry
  obeys §3; the resulting state digest must equal `target_digest` (`E_TARGET_MISMATCH`).
- **Publish**: validates the batch (no duplicate ids), builds the delta, runs the receiver's own `apply_delta` on it,
  then commits and records the snapshot in the publisher's digest-keyed history.

## 7. Templates and matching
- Grammar: literal text with placeholders `{name}`; `{{` and `}}` are literal braces; a stray `}` or an undeclared or
  unterminated placeholder is invalid. Each declared param appears exactly once; adjacent placeholders are forbidden;
  at least one literal character is required.
- Types: `int` = `-?(0|[1-9][0-9]{0,17})`, carried as a JSON integer (so `007` and `-0` never match);
  `word` = `[A-Za-z0-9_.-]+`; `text` = any non-empty string (may contain newlines and braces).
- Matching enumerates parses with a step budget of 20000 and stops at 2. Exactly one parse = match; two or more =
  ambiguous (entry skipped); budget exhaustion = entry skipped.
- Candidate set (bounded, deterministic): entries of the **declared** snapshot whose leading literal is a prefix of the
  message, sorted by (longest leading literal, id), first 8.
- Each surviving candidate is serialized to a wire message and decoded with the real decoder against the declared
  snapshot; only byte-identical results are kept. Choice: shortest wire, then id. If nothing verifies → raw.
  Draft policy sends verified refs even when larger than raw (`require_smaller=False`).

## 8. Messages (E1E-MSG/1) and fallback
- ref: `{"format":"E1E-MSG/1","type":"ref","snap":state_digest,"id","v","entry":entry_digest,"args":{name: value}}`
- raw (fallback envelope): `{"format","type":"raw","text":str}` for UTF-8 messages, else `{"format","type":"raw","b64":str}` (canonical base64).
- reject (receiver → sender): `{"format","type":"reject","code":E_*,"msg":sha256 of rejected wire}`.
- Receiver decoding: `snap` must equal the receiver's current digest (`E_STALE`); the entry must exist with the same
  `v` and digest (`E_UNKNOWN_REF`; `v` must be a JSON integer, not a boolean, else `E_SCHEMA`); args must have exactly the declared names and valid types (`E_PARAM`).
- Senders never assume the receiver's snapshot: they encode against the receiver's declaration, and only if they hold
  that exact snapshot (else raw). A stale copy declared honestly yields raw/older refs; a stale declaration (receiver
  moved on) yields a rejection. On rejection the sender delivers the original bytes in a raw envelope. Accounting
  records every frame: forward ref/raw, reject, and fallback bytes.

## Error codes
`E_MALFORMED E_NONCANONICAL E_DUP_KEY E_SCHEMA E_TOO_LARGE E_DIGEST E_DUP_ENTRY E_VERSION E_VERSION_REUSE
E_BASE_MISMATCH E_TARGET_MISMATCH E_STALE E_FORK E_DELETION_DEFERRED E_UNKNOWN_REF E_PARAM`
