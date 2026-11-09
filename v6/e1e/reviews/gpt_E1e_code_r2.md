# GPT (Codex CLI, read-only) code re-check r2 of E1e mechanics draft

Reviewed checkout: commit e9acb32. Date: 2026-10-21 (AEDT). Verbatim response below. The remaining finding (candidates() returned private entry dicts) was fixed in the following commit by returning deep copies, with regression test test_candidates_do_not_alias; that fix has not been re-reviewed by GPT (one re-check only, per instructions).

Read all nine files in full at `e9acb32`. **All 31 tests pass.**

1. **Deletion: fixed.** Full loads cannot omit held entries.
2. **Snapshot exposure: partially fixed.** Constructor inputs and `entries`/`seen`/`entry()` are defensively copied, but the fix leaves another exposure below.
3. **Reference version: fixed.** Non-integers, including booleans, are rejected.
4. **Oversized sends: fixed.** `E_TOO_LARGE` occurs before serialization or frame accounting.

**Medium — mutable candidates escape the snapshot boundary:** [codec.py:81](/workspace/e1e-gpt/v6/e1e/e1e/codec.py:81) now returns private entry dictionaries. Reproduced with `candidates(state, "hello")[0]["body"] = "changed"`: snapshot bytes change while the stored digest stays unchanged. Return defensive copies and add regression coverage for this path.

**Verdict: needs this fix before acceptance as a fixture-tested mechanics draft.** No other new bug found in this re-check.
