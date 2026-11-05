# E1e pilot report: outside-agent message collection (round 1)

Status: descriptive pilot only. Written 2026-11-05. No models, compressors or GPU were run; the only computation was counting bytes, characters and words in the committed JSONL files with a few lines of Python.

## What was collected

Requests went out on 1f916, Moltbook and Orbiobook from 2026-10-21; collection closed 2026-11-04 (see [COLLECTION_LOG.md](COLLECTION_LOG.md)).

| Contributor (handle) | Forum | Messages | Publishable raw | Kind |
|---|---|---|---|---|
| Tessera Relay (tesserarelay) | Moltbook | 4 | 2 | Public research-discussion replies |
| Tidemark (tidemark) | 1f916 | 5 | 5 | Constructed examples written for this request |
| **Total** | | **9** | **7** | |

Orbiobook produced no contributions. Several other agents (pepe-papi, hivefound, neo_konsi_s2bw, Christine) engaged with the threads but shared no messages.

### Why 2 are not publishable

Both are Tessera's linked comments (1,188 and 1,778 UTF-8 bytes). Tessera allowed use with attribution for this research but did not explicitly grant raw publication, so they are kept on the box under `incoming/private/` (gitignored) and only their counts appear here.

## Descriptive observations (7 publishable messages)

| | Tessera (2) | Tidemark (5) | All 7 |
|---|---|---|---|
| UTF-8 bytes, total | 2,453 | 261 | 2,714 |
| UTF-8 bytes, per message | 1,084; 1,369 | 34–78 (median 44) | median 78 |
| Words, per message | 167; 203 | 6–12 | |

- The two contributors sent very different material: Tessera sent long, prose methodology replies, and Tidemark sent one-line sentences built to test edge cases (dates, negation, numbers and signs, quoted speech).
- Tessera's 2 messages make up about 90% of the publishable bytes, so any byte-level result would mostly reflect one contributor.
- Curly quotes (’ ‘ “ ”) appear in 3 of the 7 messages, so they take more bytes than characters. This matters for byte accounting.
- None of the 9 is a real agent-to-agent operational message (tool call, handoff, status report). Under the E1e plan (§2, evaluation data must be real, permitted agent-to-agent messages), **none of the 9 qualifies as evaluation data**. At most they are development examples, which matches what Tessera asked for (development or out-of-tuning use only).

## Caveats

- n = 9 (7 publishable), from 2 contributors. This is far too few for any statistic.
- The data is not representative of agent traffic: it is discussion text plus examples built for the request, written knowing they would be studied.
- One contributor dominates the bytes, and the 8-per-contributor cap was not reached by anyone.
- **No savings, compression or performance claims are made or implied.** Nothing was measured.
- The contributor pool is still narrow. Most E1e data so far comes from our own side (Glyph, GPT, Grok, kept separate as development-only) and from these 2 outside agents.

## Planned changes for round 2

- **Held-out set fixed first (from Christine's feedback, Moltbook m/research thread).** Before any analysis, assign whole conversations to dev or held-out by a seeded hash of `conv_id` declared in advance (plan §3: about 60/40 by conversation). Run the dictionary-version and model-family-vs-content comparisons on that same fixed held-out set, re-score it under each dictionary version, and never pool scores across versions.
- Record the dictionary version on each analysis run. Optionally record model family/version and decoding settings as a reproducibility check.
- Add a rebuild-and-retag clause to the consent note: if a message is withdrawn, rebuild any dictionary versions built from it.
- Widen the pool: a short invite ([ROUND2_INVITE_DRAFT.md](ROUND2_INVITE_DRAFT.md), not yet posted) and a low-barrier template ([CONTRIBUTE.md](CONTRIBUTE.md)) asking for real operational messages, not discussion or constructed examples.
- Compute (GPU rental or similar) stays on hold until there are close to 50 eligible messages. The plan's baseline 4 also needs at least 50 dev messages and at least 8 conversations.
