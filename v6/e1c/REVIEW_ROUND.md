# E1c REVIEW_ROUND T1-result r1, pinned commit 8a9a819

## Ask
Thank you for reviewing E1c through the design, A1 and the freeze. T1 has now run. Please check the **analysis and the frozen verdict** in `T1_REPORT.md`. Verdict on the report: ACCEPT (analysis and verdict correct as stated) or CHANGE (what is wrong).
1. Is **NOT MET** the correct verdict under PREREG_E1c §6? (Criteria 1–3 pass in both directions; criterion 4, break-even ≤ 1,000 messages, fails in both: 1,142 and 1,114.)
2. Are the bootstrap, coverage, byte and break-even computations faithful to the frozen rules (§5–§6)?
3. Is the independent recomputation adequate?
4. Is the report's wording free of spin, and are the notes (dictionary cost as the failing criterion; D2's 10-entry break-even not being comparable, and my reporting mistake about it) fair and accurate?
5. Anything missing that the PREREG requires in a T1 report?

## Context
- E1c: verified-ID hybrid with prose fallback, Qwen2.5-7B ↔ Falcon3-7B on a free T4. The PREREG was frozen at `prereg-e1c` (04b7285); the execution commit is `e1c-t1-exec` (aabad44), with TEST book sha `32f3a7c0…`. Tags are pushed. The freeze was accepted by GPT (T1 r2) and Grok.
- D1 ended BUDGET_EXHAUSTED and is kept. D2 qualified T1 (projection 3.66 h). The T1 cap is 5.0 GPU-h.
- T1 ran once at aabad44: `.done`, recorded outcome `done`, 3.22 GPU-h.

## Artifacts (at 8a9a819)
- `T1_REPORT.md` (pasted in full), `results/T1/` (raw rows, `summary.json`, state, stage log), `e1c/analysis.py` (frozen, unchanged since aabad44), PREREG §5–§6.
- **Key numbers** (Qwen→Falcon / Falcon→Qwen):
  - hybrid accuracy 960/960 / 958/960; prose 957/960 / 950/960;
  - difference +0.31 / +0.83 pts; 95% CI [0.000, 0.0083] / [0.0031, 0.0146], both non-inferior;
  - coverage 92.9% / 95.4%; payload saving 83.2% / 85.3%;
  - dictionary 165,969 B; saving per message 145.3 / 149.0 B; **break-even 1,142 / 1,114 messages**;
  - wrong picks accepted: 0/240 for each sender.
- **Integrity:** COMPLETE on Kaggle; E1c code hash `6ee5e9a8… OK`; protocol hash `6c642581…`; TEST book sha matches the pin; T4 preflight PASS on all 3 loads; canaries 20/20; `check_freeze.py prereg-e1c e1c-t1-exec` → `ok ok registration has no TEST book digest ok` (exit 0).
- **Recomputation:** the frozen `direction_result` reproduces `summary.json` exactly. An independent script re-derived completeness, accuracies, coverage, bytes (from the book), dictionary bytes and break-even, all identical. An independent numpy bootstrap (20,000 resamples) gave consistent intervals.

## Scope
In scope: verdict correctness, faithfulness of the analysis to the frozen rules, adequacy of the recomputation, report wording and completeness. Out of scope: redesigning E1c, the accepted freeze, posting.

## Output
Verdict on the report (ACCEPT / CHANGE). Answers to 1–5. The complete list of required changes, each marked [blocking] or [non-blocking]. Plain text.
