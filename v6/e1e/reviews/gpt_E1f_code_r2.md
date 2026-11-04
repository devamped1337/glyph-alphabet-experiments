# GPT code review of E1f build, round 2 (verbatim, at e81208c)

CHANGES REQUESTED

Reviewed e81208c on codex/e1e-repository-pilot, including amendment A1. Independently reproduced 198 passing tests. Both regenerated reports’ source hashes match the reviewed files; both private lineage manifests exist. No files modified.

Original seven blockers

1. RESOLVED. Greedy gains are recomputed exactly for affected candidates, including previously nonpositive candidates. The full-recompute reference regression addresses the invalid monotonicity assumption.
2. RESOLVED. A1.3.1 explicitly authorizes append-only publication, stable IDs, scheduled/published mapping, intermediate curation points and skipped publications. Size overflow remains a separate blocker below.
3. RESOLVED in algorithm structure. Incremental enumeration removes the pair explosion; candidate-generation prefilters no longer use regexes. Accept the additional deterministic work caps, subject to the reporting correction below.
4. RESOLVED. Continuing joiners receive subsequent deltas and rebuilt dictionaries, including joining before the first publication.
5. RESOLVED. Oversized verification uses the original message length and checks raw envelopes byte-exactly.
6. PARTIALLY RESOLVED. Lineage, schedule metadata and encoder statistics are persisted, and break-even reporting exists. Two correctness defects remain below.
7. RESOLVED. Eligible-message native baselines again send their named zstd frames.

Blocking items

1. Size-aware publication overflow is required.

curation.py:build_repository_chain limits only entry count. I reproduced E_TOO_LARGE by publishing 64 valid entries with 16,384-character ASCII bodies: the generated delta was 1,059,355 bytes.

Ruling: preserve existing entries and admit the longest prefix of new entries in pick order for which BOTH the prospective canonical full snapshot and publication artifact fit the existing 1 MiB limit, inclusive. Check exact serialized bytes, including metadata, escaping and the actual publication version. Drop the remaining suffix; do not skip an oversized pick to admit later picks. If no new entry fits, publish nothing and preserve the current snapshot.

Amend A1.3.1 accordingly. Report count-limit and byte-limit overflow separately. Add boundary tests, including a delta exceeding the limit while its full snapshot fits, escaped/non-ASCII bodies, and overflow against an existing repository. Do not raise the E1E artifact limit.

2. Break-even calculation has a sign error and violates C8’s output rule.

baselines.py:break_even.solve returns adv0 / -step when step < 0. For A(u) = -1000 + 100u, the crossover is +10; the implementation reports “update count where X catches up: -10.000”.

Solve adv0 / step for either nonzero sign. Return a numeric result when positive and finite, with explicit statuses otherwise, including equality at zero. Add tests for both slope signs and zero intercept. Regenerate affected reports.

C8’s coefficients are acceptable as a frozen, observed-cost extrapolation. State explicitly that varying joins or updates can change lifecycle costs and shared uploads; this linear model is not a fresh simulation of those scenarios.

3. Whole-message character-cap exhaustion can go unreported.

In compact.py:find_candidates, the whole_only branch sets budget[0] = 0 and continues without setting match_hit. If that was the final pair, match_cap_hit remains false.

Reproduction: template x{w}, word parameter w, message xabcd, work_cap=1 produces no candidate, zero matcher calls and match_cap_hit=false. The budget suppressed matching and must be reported. Set the flag at rejection and add a regression for the final/only whole-message pair.

Choices C1–C14

C1: ACCEPT — orientation and post-trimming L.
C2: ACCEPT — remove the ineffective boundary sentence.
C3: ACCEPT — explicitly approximate Stage 2 formula and empty-repository undefined case.
C4: ACCEPT the constants and deterministic dropping policy; fix blocker 3 above.
C5: ACCEPT — entries_pending is appropriately distinguished from additional candidates.
C6: ACCEPT — curate all scheduled versions through Vmax.
C7: ACCEPT first-publication lineage and suffix overflow; extend overflow to serialized size as ruled above.
C8: ACCEPT the stated mathematical definition; correct its implementation and qualify extrapolation as above.
C9: ACCEPT — framing-aware CV score and fixed selection rule.
C10: ACCEPT — structural frame limit before epoch, reconstructed size last.
C11: ACCEPT — version-zero joiners receive the initial snapshot without another upload.
C12: ACCEPT — canonical raw verification with the frame-length parsing bound.
C13: ACCEPT — necessary-condition prefilters without regexes; E1E matcher remains authoritative.
C14: ACCEPT — leading/trailing literal prefix/suffix conditions.

Second open item: matcher time

Accept C4 as a deterministic work guard, not a latency guarantee. The span-character budget combined with the existing step limit bounds matching work conservatively, but does not establish a wall-clock deadline. No matcher rewrite or wall-clock timeout is required for this amendment. Qualify A1.2’s output-equivalence claim: equivalence applies when the new evaluation/matching caps do not truncate enumeration.

Suggestions, nonblocking

Emit consumed matcher span characters to make the character cap easier to audit.

The unchanged failed dev gate is not a blocker and provides no reason to change the floor, grid or retirement rule. Code and amendment are not yet ready for approval for Grok’s review; the three blocking items above must be resolved.
