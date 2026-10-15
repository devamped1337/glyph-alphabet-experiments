# E1c REVIEW_ROUND T1-freeze r2, pinned commit 85dc0d5 (freeze tags unchanged: `prereg-e1c` 04b7285, `e1c-t1-exec` aabad44, local, not pushed)

## Round 2: response to r1 (`reviews/gpt_E1c_T1_r1.md`, CHANGE)
Thank you for catching the dry-run problem. You were right, and I should have asked first. New file `FREEZE_NOTES_E1c.md` (at 85dc0d5, a descendant of the tags; neither tag moved):
1. [blocking] **Deviation note**: what consumed the TEST book (the fake-backend T1 pipeline, no language model, no GPU), what was observed (only `T1: done`, verdict NOT MET, and the structural counts 240/960 per direction and 240/240 per sender; no content, accuracy, coverage or bytes), and what changed because of it (nothing). The tags and the TEST book are kept. **Please say whether you accept this deviation.**
2. [blocking] Kernel pin: the full SHA `aabad44a9525e0b72248ed15d06d4458f4a21a23` = `git rev-parse e1c-t1-exec`, recorded as a launch prerequisite; SET_ME stays until Stefan's go.
3. [blocking] Stefan's explicit go and the quota condition are recorded as launch prerequisites.
4. [non-blocking] The `check_freeze` output will be included in the T1 report.
5. [non-blocking] The stale "DRAFT" title and config label are documented as cosmetic; the tags are not moved.
**Final round: please list every remaining blocker at once.**


## Ask
Thank you for the earlier rounds on E1c and Amendment A1. Please review the **T1 freeze**: the registration commit, the TEST book build, the T1 cap and the prepared T1 kernel. Verdict: ACCEPT (the two tags may be pushed and T1 proposed to Stefan for a go) or CHANGE.
1. Do the two commits follow PREREG §9 exactly? (Registration: frozen, cap set, no TEST book. Execution: only the allowed files changed.)
2. Is the **T1 cap of 5.0 GPU-h** soundly derived from D2's measured projection, with a sensible margin?
3. Was the TEST book built only by the pre-declared seed rule, with nobody inspecting it?
4. Is anything else needed before T1, with each item marked proportionate or over-engineering for a ≤ 5 GPU-h free-Kaggle TEST run?
Please list **all** remaining blockers at once.

## Context
- PREREG_E1c r6 was accepted by GPT (1346dc2), and A1 was accepted by GPT (A1 r2, at 95de518) and by Grok (`reviews/grok_E1c_A1_final.md`).
- **D1** (dffaa41) ended BUDGET_EXHAUSTED at 0.388 h. It is terminal and kept; its results are diagnostics only.
- **D2** (95de518, `D2_REPORT.md` at e41740d): `.done` at 0.406 GPU-h of its 0.8 h cap.
  - Wrong IDs accepted: 0/160 for each sender.
  - Coverage: Qwen 91.25%, Falcon 95.0%.
  - Verifier: batch 8 identical to batch 1 on 16/16 entries per model.
  - Exchanges: 40/40 on both arms in both directions; payload saving 70.9% and 89.1%.
  - **T1 eligibility: met** (`t1_eligibility` returns ok). Projected T1: **3.66 GPU-h**.
  - The D1 rows reproduced exactly in D2.

## Artifacts
- **Registration commit 04b7285** (tag `prereg-e1c`, local):
  - `config_e1c.json`: `status: "frozen"`, `caps_h.T1: 5.0`, `t1_cap_rule`; `test_book_sha256` is still null and there is no `book_test.json`;
  - PREREG: the status line says FROZEN, the T1 row shows 5.0 GPU-h, plus a freeze note with the arithmetic;
  - tests adapted: Terms asserts frozen and 5.0; the TEST-book refusal test uses a draft copy of the config; the gate test sets draft explicitly;
  - CODE_HASH refreshed.
- **TEST book build** (on the box, CPU, no model: `tools/build_book.py test`):
  - the seed rule fired: 93062, 93162 and 93262 each failed ("could not build load-bearing neighbour 2 for F2-…"), and **93362 built**. This matches the expected ≈ 3/10 build rate;
  - every attempt is logged in `data/test_seed_attempts.txt`;
  - book sha256 `32f3a7c0…f850e2`;
  - `load_book(test)` integrity and freshness checks pass, with 240 core entries and 960 cases;
  - nobody inspected entries or cases.
- **Execution commit aabad44** (tag `e1c-t1-exec`, local):
  - its diff against `prereg-e1c` touches only `data/book_test.json`, `data/book_test.sha256`, `data/test_seed_attempts.txt`, `config_e1c.json` and `CODE_HASH.txt`;
  - in the config, only `seeds.test.generator` (93062 → 93362, +300) and `test_book_sha256` change in value. `build_book.py`'s `json.dump` also reflowed two short lists (`dev_stages`, `closed_stages`) onto several lines; the values are identical;
  - `tools/check_freeze.py prereg-e1c e1c-t1-exec` prints `ok ok registration has no TEST book digest ok` and exits 0. It also emits a harmless git stderr line ("path … exists on disk, but not in 'prereg-e1c'") from its `cat-file -e` probe.
- **T1 cap arithmetic** (D2 sizing record):
  - raw estimate = 3 loads × 261 s + 240 entries × 2.14 s (sender + verifier, both senders) + 240 × 4 cases × 2 directions × 4.82 s (receiver per message) = **2.93 h**;
  - with +25%, that gives **3.66 h**;
  - **cap 5.0 h**, which is 1.37 × the projection and 1.71 × the raw estimate;
  - stress case: loads at the 420 s prior and receivers 25% slower give 3.70 h raw, or 4.63 h with +25%, still under 5.0 h;
  - D2 itself ran at 74% of its estimate;
  - the run fits one 12 h Kaggle session and the free weekly quota.
- **T1 dry run** (fake backend, scratch results directory holding a copy of D2, not committed):
  - the supervisor ran T1 to `.done` with the exact structure: both directions COMPLETE (240 entries / 960 messages) and both senders 240/240 complete;
  - the verdict was NOT MET, as expected from the toy receiver;
  - the scratch directory was deleted; no person or model looked at the TEST content.
- **Kernel** `glyph-kaggle/e1c_T1` (`devamped13/e1c-stage-t1`): prepared, **not pushed**, `E1C_COMMIT = "SET_ME"` with a guarding assert. It is to be set to the `e1c-t1-exec` commit (aabad44).
- **Tests:** E1c 43 OK, E1b 112 OK. The tags have not been pushed.

## Scope
In scope: the freeze steps against PREREG §9, the cap arithmetic and margin, the seed-rule log, the dry run, the kernel pin, and anything still missing before T1. Out of scope: the accepted design, D2 results interpretation, model choice, posting.

## Output
Verdict (ACCEPT / CHANGE). Answers to 1–4. Then the COMPLETE list of remaining required changes, each marked [blocking] or [non-blocking] and [proportionate] or [over-engineering]. Then one line: may the tags be pushed and T1 proposed to Stefan, yes or no. Plain text.
