# GPT (Codex CLI, read-only) code review r1 of E1e mechanics draft

Reviewed checkout: commit ad77d0c. Date: 2026-10-21 (AEDT). Verbatim response below. All four findings were fixed in the following commit, with regression tests (class ReviewR1Regressions).

Reviewed HEAD `ad77d0c` and all requested files in full. All **25 tests pass**, run with bytecode writing disabled.

**Verdict: needs fixes first**, primarily the full-load deletion path.

1. **High — full sync permits deletion.** [repo.py:82](/workspace/e1e-gpt/v6/e1e/e1e/repo.py:82) checks history only when an ID remains present. Reproduction: load a valid v1 containing `a`, then load a correctly digested v2 with `entries: []`. It succeeds and removes `a`, contradicting §3’s additions/revisions-only rule. Reject full artifacts that omit held entries.

2. **Medium — snapshots are mutable and share entry objects.** [repo.py:24](/workspace/e1e-gpt/v6/e1e/e1e/repo.py:24), [repo.py:134](/workspace/e1e-gpt/v6/e1e/e1e/repo.py:134). Reproduction: publish `a`, retain `old = pub.state`, publish `b`, then assign `old.entries["a"]["body"] = "changed"`. The current snapshot also changes while its stored digest remains unchanged. This breaks the advertised immutable, digest-keyed snapshot boundary. Use immutable nested structures or defensive copies at exposure boundaries.

3. **Medium — malformed reference version accepted.** [codec.py:50](/workspace/e1e-gpt/v6/e1e/e1e/codec.py:50) compares versions without validating their type. A canonical reference to a v1 entry with `"v": true` and otherwise correct fields decodes successfully because `True == 1`. Require an integer version explicitly, excluding booleans.

4. **Low — oversized sends produce an undeliverable fallback.** [codec.py:87](/workspace/e1e-gpt/v6/e1e/e1e/codec.py:87). `encode(..., b"a"*65537)` returns a raw frame marked `too_large`; `Link.transmit` sends it, records rejection, then sends the same invalid payload as fallback and raises `E_TOO_LARGE`. Reject oversized input before serialization or recording traffic.

Against §4, the main package is present: protocol, transactional validation, typed codec, actual-decoder byte verification, receiver declarations, fallback accounting, and deterministic synthetic evidence. Missing regression coverage includes the findings above, full-load fork/history conflicts, and explicit matching-budget/candidate-limit boundaries.

I found **no rejected repository operation that mutates state through the normal validated API**, and **no accepted non-identical byte round trip**. The snapshot-aliasing finding requires direct mutation of an exposed object; it is distinct from rejection atomicity. The synthetic-only labeling and absence of savings claims are appropriate.
