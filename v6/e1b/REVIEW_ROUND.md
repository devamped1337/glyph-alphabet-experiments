# E1b review round 5: A10 draft (Grok + GPT)

- **Pinned commit:** `6a60c8d4c84edc75bb40c149580b8667ef740ddc` (draft code hash `543a369c…`). A10 is a **draft**: not frozen, not tagged, and nothing pushed to Kaggle.
- **Text:** [PREREG_E1b.md §A10](https://github.com/devamped1337/glyph-alphabet-experiments/blob/6a60c8d4c84edc75bb40c149580b8667ef740ddc/v6/e1b/PREREG_E1b.md). GPT's plan review (summary): [reviews/gpt_A10.md](https://github.com/devamped1337/glyph-alphabet-experiments/blob/6a60c8d4c84edc75bb40c149580b8667ef740ddc/v6/e1b/reviews/gpt_A10.md). Offline pilot: [a10_offline_pilot.json](https://github.com/devamped1337/glyph-alphabet-experiments/blob/6a60c8d4c84edc75bb40c149580b8667ef740ddc/v6/e1b/a10_offline_pilot.json). Code: [parsing.py](https://github.com/devamped1337/glyph-alphabet-experiments/blob/6a60c8d4c84edc75bb40c149580b8667ef740ddc/v6/e1b/e1b/parsing.py) (`parse_letter_a10`), [stages.py](https://github.com/devamped1337/glyph-alphabet-experiments/blob/6a60c8d4c84edc75bb40c149580b8667ef740ddc/v6/e1b/e1b/stages.py) (`stage_B3f`, `stage_B3r`). Tests: [test_a10.py](https://github.com/devamped1337/glyph-alphabet-experiments/blob/6a60c8d4c84edc75bb40c149580b8667ef740ddc/v6/e1b/tests/test_a10.py).
- **Framing:** A10 is a post-hoc diagnostic completion on an already-seen TEST set (written after the 56/60 exploratory re-parse). **The A9 B3 verdict, POC FAILED, stays primary.** A10 is secondary and cannot overturn it.

## What A10 does (all six GPT points applied)
1. **Parser.** It removes candidate-ID fragments (`F1`, `F2`, `F3L`, with optional `-NNNN@vN#hash`), then applies the frozen `parse_letter` unchanged.
   - A bare `F1` is rejected.
   - Conflicting choices are still rejected.
   - There is no first-letter rule.
   - The prompt, settings (4 tokens, greedy), candidate order, cases, scoring, margin and analysis code are unchanged.
2. **No new sender call.** The 60 archived Falcon replies are re-parsed, and the validator checks the raw replies are byte-identical.
   - **Only the Qwen id_selected arm runs** (240 items).
   - **The prose arm is reused verbatim, not rerun.**
   - Six inputs are pinned by sha256.
   - The symmetric Qwen-sends rerun is dropped.
3. **Offline pilot** over all 22,296 archived letter replies of both models: **0 changed decisions** and 60 rescued (all Falcon B3 sender replies; 56 correct picks, already seen).
4. **B3f**, a non-TEST format check, runs **before the freeze**. Both models get the frozen sender prompt on the pilot entries: 4 entries × 6 orders = 24 views each.
5. **Budget and attempts.**
   - B3f cap 0.25 h and B3r cap 0.50 h: the A10 total is 0.75 h, within the ≤ 1 h cap.
   - Estimates are about 0.15 h for B3f and 0.21 h for B3r.
   - The cumulative A9 + A10 limit is ≤ 12 h; A9 has used 6.15 h, so the worst case is 6.90 h.
   - One start per stage, with separate result directories.
   - B3r needs `a10.status=frozen` plus `E1B_GO=B3r`.
6. **B3_REPORT corrected.** There were 37 Qwen→Falcon id_selected errors: 36 came from wrong selections and 1 happened despite a correct selection (verified at `3973107`).
7. **Tests:** 105 run, all pass, 1 skipped (10 new A10 tests). The validator passes.

## Open questions (please answer yes / no / change)
1. **Is reusing the prose arm acceptable,** given the cross-session batch-neighbour difference (bounded by B1c 120/120 and B2 20/20)? The alternative is rerunning prose too, with both arms in one session; that adds about 0.15 h and creates a second prose measurement.
2. **B3f bar before the freeze:** A10 should give a valid parse on at least 22/24 per model, with 0 changed frozen decisions. Is this the right bar, and is pilot-entry reuse (4 entries × 6 orders) enough as non-TEST material?
3. **Is the ID-fragment regex scoped right?** It covers whole-token `F1`, `F2` and `F3L`, optionally with a truncated `-digits`, `@v` and `#hex`. Should `F3L` be included, since F3L was not run in A9?
4. **Reporting:** should B3R_REPORT show the A10 Falcon→Qwen result next to the A9 one, or only in a separate secondary section?
5. **Freeze:** yes or no on freezing A10 after B3f, if B3f meets the bar.
