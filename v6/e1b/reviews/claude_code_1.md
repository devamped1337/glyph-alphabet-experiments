# Code review claude_code_1: E1b implementation at `6e2636d` (summary relayed by the user)

Relayed 2026-10-12 (AEDT). This is a summary relayed by the user, not a verbatim transcript.

> **Scope:** Claude read `CODE_REVIEW_GUIDE.md`, `e1b/backends.py`, `e1b/cachediag.py`, `e1b/cases.py` and `README.md` at `6e2636d`. It **ran nothing**.

**Major corrections requested:**
1. Add an order-aware regex number-matching selection baseline. Labels carry the constants, so number matching alone may solve the selection task.
2. Make the original messages harder for ≥1/3 of entries (spelled-out numbers, reordered clauses, derived forms), pre-registered by a frozen seed.
3. Report selection accuracy by neighbour type (swap, shift, swap+shift).
4. Set the probe leak flag against each probe kind's measured no-text baseline instead of a flat 0.40. Use plausible distractors, including some honest "not stated" probes.
5. Add a cold-split cache arm (prefix and suffix as two evaluations) to separate state restore from batch split.
6. Smoke-test the HF cache path on CPU with a tiny model (configurable device, no nf4).
7. Rename the "hard" set to "multi-step stress prompts".
8. Reconcile the cache bound (n and %), worded per prompt, with a clustering caveat.
9. Log the rendered prompts plus a system-turn hash per backend.

**Smaller items:**
- An invalid-reply rate >5% should trigger a prompt fix before B1.
- State the number of selection trials per family.
- Choose the manipulation-check model by B0 score.
- Add an answer_gap source flag.
- Note the mk_case substring skew.
- Re-record the code hash.
