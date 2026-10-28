# E1e repository pilot: Codex–Glyph/Cursor proposal

Status: **DRAFT FOR DISCUSSION.** This is a design handoff, not a preregistration, reviewer acceptance, benchmark result or launch instruction. The existing E1e collection log remains the data intake record. No existing frozen protocol or result is amended.

Prepared 2026-10-21 from public repository snapshot bcea33755101f7f7bf31bf709b16b28d79901e63, following Stefan's request for Codex and Glyph's Cursor workflow to develop the next step together.

## Ask

Agree on the smallest implementation that measures whether a shared, versioned repository reduces communication cost on actual agent messages. Start with an offline CPU replay. Separate repository mechanics, retrieval, model interpretation and adaptive coordination so that a result in one does not stand in for another.

Glyph/Cursor: inspect this proposal against the code and available data, suggest corrections, and reply with the implementation plan and cost estimate. Codex: review the agreed design and implementation, then independently check reported measurements.

## Context and evidence

- E1d T1 succeeded under its frozen criteria in both directions. Hybrid receiver accuracy was 639/640 in each; coverage was 139/160 and 151/160. Lifetime byte-saving points were 35.6% and 39.6%, conditional on W_base.
- W_base was a declared scenario, not observed deployment traffic. Lower traffic reduced the savings substantially.
- The E1d sender received the true entry plus three neighbours. End-to-end candidate retrieval from a large repository remains a gap.
- IDs were expanded to text before receiver inference. The result establishes a bandwidth claim under that setup, not a demonstrated reduction in receiver inference compute.
- E1d's reporting-only compressed-sync calculation used v1's compression ratio for future artifacts. This pilot should measure the actual bytes of every generated artifact instead.
- E1e currently contains a collection log, with no responses recorded at the snapshot above.

Sources:
- ../e1d/T1_E1d_REPORT.md
- ../e1d/DRAFT_PLAN.md, sections 2, 4, 5 and 12
- ../e1d/reviews/gpt_E1d_T1_r1.md
- COLLECTION_LOG.md

## Deliverable 1: a small repository and offline replay

Use ordinary files and local processes first. One host holds published entries; at least three simulated delegates maintain separate local copies. No hosted service, GPU, model download or paid API is needed to validate these mechanics.

Minimum entry fields:
- stable ID, entry version, full content digest and format version;
- literal content, or a precisely specified template with typed parameters;
- source/provenance category sufficient to distinguish synthetic examples from permitted real messages.

Minimum operations:
- initial full sync;
- publish an added or revised entry and generate a delta;
- apply a delta only to its matching base version;
- retrieve a bounded candidate set using a CPU index;
- encode a message using a locally available entry;
- decode at a receiver with its own versioned copy;
- fall back to prose for missing, stale, ambiguous or non-matching entries.

Specify the wire schema before comparing bytes. Include identifiers, versions, digests, parameter payloads and framing. Use one deterministic serializer consistently.

For this first transport pilot, require **byte-for-byte reconstruction** of every encoded original message. Literal template matching and deterministic checking are sufficient. Approximate retrieval can propose candidates, but a reference is sent only if exact reconstruction is verified. This establishes transport behaviour; it does not establish semantic negotiation by models.

Tests should exercise the actual failure boundaries: incorrect delta base, corrupt digest, missing version, changed template meaning, ambiguous match, escaping/Unicode and fallback. Include a joiner and an intentionally stale receiver in the replay.

## Deliverable 2: a real-message byte audit

### Corpus and split

Use permitted, sanitised messages from recurring tool calls, handoffs or status exchanges. Keep raw messages private unless publication is expressly permitted. Publish aggregate results and synthetic fixtures sufficient to exercise the implementation.

Split by whole conversations/workflows, preferably in chronological order. Build entries, tune retrieval and train compression dictionaries only on the development portion. Freeze those choices before held-out replay. Do not supply the correct entry to retrieval at evaluation time.

The collection request's 20–500 messages is an intake target, not a sample-size justification. Report conversation counts, message counts, duplication and sources. A small corpus supports a descriptive pilot; it does not establish a population-wide saving.

First replay can keep the repository fixed. A separately reported lifecycle replay can introduce predetermined updates and joins, charging the bytes they actually produce. New entry bodies must come from development data or an explicit prior update source, not future test messages.

### Baselines

At the same declared message boundary compare:
1. original uncompressed messages;
2. per-message gzip;
3. per-message zstd without a trained dictionary;
4. zstd with a shared dictionary trained only on development data;
5. repository references, parameters and fallback messages, with the chosen compression policy specified.

Include repository references plus ordinary compression if that combination is tested. Pin codec versions/settings. Charge initial distribution, joiner copies, updates and metadata for every shared dictionary, including the compression baseline.

Decide in advance whether the comparison resets codec state for every message or permits a persistent stream. If persistent streams match the intended deployment, include a separately specified stream baseline with connection setup/reset costs. Per-message gzip alone is not enough to establish an advantage over persistent compression.

### Accounting

Report separately:
- storage per participant;
- measured full and delta sync bytes, including the maintainer upload;
- actual serialized message bytes in both directions;
- CPU indexing, encoding, decoding and replay time;
- retrieval coverage, fallback causes and exact reconstruction failures;
- total traffic and break-even on the observed replay.

Use actual generated artifacts, not scaled compression ratios. Keep declared lifecycle scenarios separate from measured traffic. Extrapolations must show their assumptions.

CPU pilot model/API calls: **zero**. Record runtime and hardware; call this zero new model inference, not zero computational work.

A useful transport result requires correct reconstruction and a measurable advantage against the relevant compressed baseline after setup costs. Report ties or losses as such; do not choose the best workflow or change the accounting after seeing held-out results.

## Deliverable 3: bounded live-model follow-up, if justified

After the CPU audit, choose one recurring workflow and write a separate reviewable plan for genuine model selection and use of entries.

Measure the whole path: retrieval, sender selection, verification, fallback, receiver inference and repository maintenance. Count every model call, input/output token, wall time and synchronization cost. Distinguish receiver-only timings from end-to-end timings, and cold setup from amortized repeated use.

Do a small timed development probe before proposing a GPU cap. Use current quota and observed timings; do not reuse old quota estimates. Existing stage-specific authorization requirements still apply.

This is where model-generated proposals and meaning-preserving conformance checks can be tested. Those capabilities are not established by a lossless template codec.

## Later hypothesis: adaptive coordination

Once a useful fixed-repository baseline exists, test slow changes in routing/relationship weights while keeping the model weights and entry meanings fixed.

Controls: frozen relationships, shuffled experience and simple frequency-based routing. Evaluate new combinations, retention and adaptation after traffic changes; count the adaptation overhead. Specify the local update rule and permitted information before evaluation.

This would be a test of adaptive coordination inspired by the discussion of natural induction. It should not be labelled a demonstration of that specific mechanism merely because something changes over time.

## Collaboration and reply format

This originating GPT conversation reads GitHub. Glyph's Cursor/Codex sessions are separate processes; project files carry context between them. No automatic wake-up, shared live session or access to Glyph's local Cursor is implied.

Glyph's reply should contain:
1. the commit reviewed and actual session/tool used;
2. corrections to the scope or assumptions above;
3. relevant existing modules to reuse, and proposed new files;
4. available corpus counts and permission status, without raw private messages;
5. a CPU-only implementation/replay estimate, with unknowns identified;
6. the next concrete deliverable and any genuine blocker.

Use a commit-linked reply on this draft branch/PR or a committed response file. Keep credentials, CLI session IDs, raw private logs and private context packets out of the public repository. Clearly distinguish a draft, a fixture, an executed test and an actual reviewer response.

Proposed order: agree scope → implement CPU mechanics → verify replay → freeze data split and measurement choices → held-out byte audit → decide whether a live-model stage merits compute.
