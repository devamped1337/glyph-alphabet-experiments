# GPT code review r1 of E1d dev-stage code (commit f092214, tag e1d-dev-exec), 2026-10-20 18:04 AEDT

codex
GO — for D1-E1d dev only at `f092214`.

Blocking bugs: none found.

Non-blocking notes:

- `v6/e1d/e1d/stages.py:152`: saved eligibility uses `done_ok=None`, so `eligible_for_freeze` remains false after successful completion. Add a post-run evaluator before freeze; the documented `--eligibility` option is also missing.
- `v6/e1d/e1d/supervisor.py:69`: admission passes at **0.846 h including 25% margin**. Stress timing is **0.853 h raw / 1.066 h with margin**; code checks stress raw, despite config wording implying margin on stress too. Align the wording.
- `v6/e1d/kaggle/e1d_kaggle.py:8`: cloning, installation, and final packaging fall outside the supervisor deadline. The 1.0-hour cap covers the supervised stage, not the entire Kaggle session.

Verified: code hash and book pins match; assignments match §8; **17 read-only CPU tests passed**. The write-producing supervisor dry run was inspected but not rerun. Nothing launched.
