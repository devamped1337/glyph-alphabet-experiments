# GPT (Codex CLI, read-only) code re-check r4 of E1e mechanics draft

Reviewed checkout: commit 20bb2e8. Date: 2026-10-21 (AEDT). Verbatim response below. The finding (unvalidated mutable RepoState constructor metadata) was fixed in the following commit: the constructor now requires an int version (non-bool, 0..2^31), validated entries keyed by id, and a seen map of (str, int) -> str; Holder rejects non-RepoState state. Regression test: test_constructor_rejects_malformed_metadata.

Read all seven files in full at `20bb2e8` and swept the public API. The r3 reassignment fix is correct; **all 33 tests pass**.

One **medium** issue remains: [RepoState’s public constructor](/workspace/e1e-gpt/v6/e1e/e1e/repo.py:25) accepts unvalidated mutable metadata:

```python
s = RepoState(version=[])
r = Receiver(s)
before, digest = s.full_bytes(), s.digest
s.version.append(99)
assert r.state.full_bytes() != before
assert s.digest == digest
```

Also reproduced `s = RepoState(seen={('a', 1): []})`: mutating `s.seen[('a', 1)]` or the corresponding `fingerprint()` value changes internal history because both expose that list. Reject malformed constructor metadata, including noninteger versions and nonstring history digests.

These require malformed constructor inputs; no remaining mutation escape was found for snapshots produced through validated loading/publishing, publisher history, or accounting logs.

**Verdict: needs fixes.**
