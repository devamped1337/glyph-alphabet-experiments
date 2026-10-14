# E1b review round 5b: A10 draft after GPT r1 (Grok + GPT)

- **Pinned commit:** `bd218c89bdd58e78efd444abb06849379c583a6b` (draft code hash `c484991e…`). A10 is still a **draft**: not frozen, no tag. B3r has not been pushed.
- **Text:** [PREREG_E1b.md §A10, including "A10 round 5"](https://github.com/devamped1337/glyph-alphabet-experiments/blob/bd218c89bdd58e78efd444abb06849379c583a6b/v6/e1b/PREREG_E1b.md). Reviews: [gpt_A10.md](https://github.com/devamped1337/glyph-alphabet-experiments/blob/bd218c89bdd58e78efd444abb06849379c583a6b/v6/e1b/reviews/gpt_A10.md), [gpt_A10_r1.md](https://github.com/devamped1337/glyph-alphabet-experiments/blob/bd218c89bdd58e78efd444abb06849379c583a6b/v6/e1b/reviews/gpt_A10_r1.md). Validator: [validate.py](https://github.com/devamped1337/glyph-alphabet-experiments/blob/bd218c89bdd58e78efd444abb06849379c583a6b/v6/e1b/e1b/validate.py). Tests: [test_a10.py](https://github.com/devamped1337/glyph-alphabet-experiments/blob/bd218c89bdd58e78efd444abb06849379c583a6b/v6/e1b/tests/test_a10.py). B3f results: [results/B3f](https://github.com/devamped1337/glyph-alphabet-experiments/blob/bd218c89bdd58e78efd444abb06849379c583a6b/v6/e1b/results/B3f).
- **Framing (unchanged):** A10 is a post-hoc diagnostic completion on an already-seen TEST set. **A9 B3: POC FAILED stays primary.**

## Changes since round 5 (`6a60c8d`)
1. **Validator defect fixed (GPT r1).** Before the fix, a B3r run with one copied prose row deleted still validated. The validator now enforces:
   - exactly 60 unique archived selections, with the same entries as A9;
   - exactly 240 rows per condition, with unique (entry, case) keys covering exactly the scheduled cases;
   - every prose row equal to its pinned source row, with only `reused_from` added;
   - exactly 24 scheduled non-TEST views per model in B3f.
2. **Regression tests.** A missing prose row, a missing id_selected row, an altered prose row, an extra field on a copied prose row, a missing selection and a missing format view now all fail validation; a clean run passes. **112 tests run, all pass, 1 skipped.** The validator passes on the real results.
3. **Text changes.**
   - **Q1:** the reuse checks "provide supporting checks but do not quantify or eliminate cross-session effects", and the CI does not cover cross-session bias.
   - **Q2:** the bar is kept (≥22/24 and 0 changed accepted decisions). The views cover 4 entries, with **19** distinct entry/order combinations (counted on the results; the review estimated 20), so they are not independent tests.
   - **Q4:** B3r goes in a separate secondary section, with the A9 FAILED verdict prominent. The original Falcon direction is described as a frozen-parser failure with zero ID receiver calls.
   - **Q3:** unchanged.
4. **B3f ran** on Stefan's go (09:07 AEDT): 0.153 of 0.25 GPU-h, T4 nf4, canaries 20/20 for both models, validator passed.

| Model | Frozen valid | A10 valid | Changed accepted decisions | Bar |
| --- | --- | --- | --- | --- |
| qwen7b | 24/24 | 24/24 | 0 | PASS |
| falcon7b | 0/24 (`X) Fn`) | 24/24 | 0 | PASS |

   Cumulative GPU-h: A9 + A10 = 6.30 / 12.0, and A10 so far is 0.15 / 1.0.

## Questions
1. Are the validator checks and regression tests sufficient? (yes / change)
2. **Freeze A10 now?** (yes / no) If yes: set `a10.status=frozen`, record the hash, tag `prereg-e1b-a10`, set B3r's `RESULTS_COMMIT` to `bd218c89bdd58e78efd444abb06849379c583a6b`, and launch only on Stefan's explicit go.
