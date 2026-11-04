# Grok code review r1 of E1e mechanics draft

Reviewed commit: 6ca7770. Date: 2026-10-21 (AEDT). Source: relayed via Stefan. Verbatim review below.

---
Review of commit 6ca7770 complete.
Verdict: GO as a fixture-tested mechanics draft. No blocking bugs found. Not yet freeze-ready.
1. Spec matches code. Fingerprints cover the template schema (entry digest includes params). Full copy + sequence of deltas reconstructs the target full state byte-identical (test_full_plus_deltas_equals_target_full and related).
2. Rejected operations do not change state. load_full and apply_delta (via Holder) only assign the new RepoState after every check including the final target-digest match succeeds. Tests explicitly assert fingerprint unchanged after rejection.
3. Full 64-hex fingerprints are acceptable for the mechanics draft and match the spec. They do make some short messages larger than raw. Recommend measuring the inflation rate on the synthetic set and deciding whether to add a shorter reference form before the real-message byte audit. Not a blocker.
4. Per-message compression as primary. Persistent stream as secondary, with endpoints, reset/join, and flush points specified and charged at delivery boundaries.
5. Failure tests are sufficient for the mechanics draft. Add zstd-failure and short-message-inflation cases when the measurement protocol is written.
Residual notes (non-blocking): underscore-prefixed attributes reachable by deliberate callers; deletion deferred (E_DELETION_DEFERRED); no zstd baseline yet; synthetic data only, real messages required before any savings claim.
Compression choice (per-message primary) is my recommendation; Stefan still needs to confirm that and the dev-data okay. Proceed with the parallel CPU-only work (byte-audit plan draft + pin zstd). Do not freeze or merge until the two Stefan calls are done.
---
