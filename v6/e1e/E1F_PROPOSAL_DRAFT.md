# E1f proposal — curated long entries + compact references vs zstd with the same dictionary
Status: DRAFT proposal for GPT review first, then Claude and Grok. Nothing here is frozen, tagged or run. CPU only;
no Kaggle, no GPU, no model other than GPT review via Codex. Builds on the frozen-pending E1e plan (`BYTE_AUDIT_PLAN_DRAFT.md`
incl. Amendment A1) and the E1E-REPO/1 spec. Origin: Stefan's point (2026-10-23) that the repository is kept by always-on
maintainer agents, so entries can be long and curated, not just whatever a dev corpus yields.

## 1. The question
E1e measured refs with the E1E-MSG/1 JSON envelope (230–372 B per ref) against entries that on dev data were mostly
23–57 B, with 1.61% byte coverage. That tests "tiny entries + fat refs", which loses by construction. E1f asks the
fair version: **if entries are long and curated and references cost a few bytes, does an ID scheme beat per-message
zstd that uses the same curated entries as its dictionary (baseline 4b), counting every synchronisation byte?**

## 2. Honest expectation (stated before measuring)
zstd with a raw-content dictionary also encodes a long match in a few bytes. So per-message bytes may tie. The refs
arm's real structural advantages are (a) append-only, immutable (id, version) entries sync as **deltas**, while a
zstd dictionary is charged as a full rebuild per version (A1), and (b) exactness and auditability. The test is whether (a)
shows up in total bytes at realistic update rates. A tie or loss on per-message bytes with a win only through sync is a
valid, reportable outcome and must be reported as such. The byte claim is retired if refs do not beat 4b in total (A1 rule).

## 3. Compact wire form E1F-MSG/1 (the deferred option; additive, E1E-MSG/1 unchanged)
Frame discrimination stays selector-free: raw envelope starts `{` (0x7B), zstd frame starts 28 B5 2F FD; a compact
frame starts 0x01 (first bytes never collide with either; any other first byte is E_SCHEMA).
- Snapshot identity is carried by the link declaration (already charged), not repeated per message: no `snap`, no `entry`
  digest per message. Integrity = declared snapshot digest + offline byte-exact oracle; optional 4-byte truncated
  SHA-256 of the reconstructed message as a secondary integrity run (cost reported, as for zstd checksums).
- Body: `0x01` then segments until end. Segment = op byte + payload:
  - `REF`: varint entry ordinal (position in the snapshot's id-sorted list) + varint version-delta (0 = current
    snapshot version of that entry) + one args block per declared param (int: zigzag varint; word/text: varint length + UTF-8).
  - `LIT`: varint length + literal UTF-8 bytes (novel text between refs).
  Segmenting is what lets a long curated block sit inside a message with novel text around it.
- Decoder rejects: ordinal out of range, bad varint (non-canonical), truncated frame, trailing bytes, args mismatch,
  non-UTF-8 LIT/arg where the message must be UTF-8. Same error-code family as E1E.
- Selection: per message, the encoder tries compact-segmented, compact+zstd of the LIT residue (optional, declared
  before measurement), and raw; sends the strictly smallest, ties broken raw then compact (same require_smaller idea).

## 4. Curated dictionary (no hand-picking, no leakage)
- Maintainer agents cannot be simulated directly, so curation is a **fixed, deterministic procedure run on dev data only**:
  candidate spans = line blocks and n-gram runs that recur in ≥ k distinct dev conversations, length ≥ L bytes; keep greedily
  by (saved bytes − entry cost); k, L, and the cap on repository size are chosen in dev and frozen with the code hash
  before any held-out replay. Templates are mined with the existing parameter grammar.
- The **same** entry bodies feed 4b's dictionary (A1 construction), so both arms use identical shared knowledge.
- Versions: the repository grows in simulated steps (e.g. every N dev conversations); each step is a new version. Refs sync
  by delta (new entries only); 4b by full rebuild. Update cadence is a swept parameter (e.g. 1, 5, 20 versions) because
  the sync trade-off depends on it.

## 5. Arms (all at the per-message delivery boundary, same oracle)
1 raw; 3 zstd no dict; 4 zstd trained dict (dev messages); **4b zstd with curated repository as raw dict**;
5 E1E-MSG/1 refs (as implemented); **7 E1F compact segmented refs; 7z compact + zstd on LIT residue (if declared)**.
Accounting per §6 of the plan: actual bytes only, including declarations, rejects, retransmissions, and repository sync
(delta for 7, full rebuild for 4/4b), per participant and per joiner.

## 6. Analytical gate before any code
On dev data only, compute for each message the ceiling: bytes covered by curated entries ≥ L, the cost of a compact ref
(≈ 1 + 1–2 + args) versus the cost 4b actually pays for the same span. If covered bytes are under a predeclared floor,
or 7's ceiling total does not beat 4b's actual total, stop and report without building the codec.

## 7. Data and gates
- Dev: synthetic (public), Glyph-own sanitised (private, single operator, development only). These cannot support any
  savings claim; Glyph-own traffic is highly self-similar and would flatter both arms.
- Held-out: **one pass**, only real outside messages, per the Stefan/Claude rule: not spent until ≥ 50 messages, ≥ 20
  conversations, ≥ 3 contributors (or Stefan, GPT and Claude agree the corpus is representative). The four Tessera
  messages stay in reserve and are not spent as a held-out set.
- Report counts, not percentages alone; byte-weighted and per-message; sources separate; thresholds not changed after seeing them.
- No launch of anything compute-heavy; this is CPU-only and runs on the box in seconds to minutes. Any other job needs Stefan's go.

## 8. Prerequisites (bugs found by the dev diagnostic, to fix first, needing GPT's view)
1. Messages over 64 KiB: encode/transmit raises E_TOO_LARGE, so arms 5/6 have no bytes. Proposed rule: out-of-scope for
   refs; every arm is charged the same fallback for them (zstd(raw) or raw, smallest), counted and reported separately.
2. `build_entries` crashes on a repeated body over 16,384 chars: define behaviour (split into entries or skip, counted).
3. Entry `prov` defaults to `synthetic`: require explicit provenance.
4. Baseline 6 compresses the escaped JSON envelope (5.7% larger than the message) and uses baseline-4's dictionary: decide intended behaviour.
5. Fold seed is not frozen (the diagnostic used "e1e-diag-r1"): freeze one before any real split.

## 9. Questions for GPT
Q1. Is the §2 expectation fair, and is the delta-vs-full-rebuild sync accounting the right place for refs to win or lose?
Q2. Is the compact form (§3) specified tightly enough to implement and fuzz without ambiguity, especially canonical varints and segment boundaries?
Q3. Is the curation procedure (§4) free of held-out leakage and not tuned to flatter refs?
Q4. Preferred resolution for each item in §8.
Review rounds capped at 2 for this proposal.
