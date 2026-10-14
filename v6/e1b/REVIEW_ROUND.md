# E1b review round 4 (A9 draft: B1–B3 for the post-hoc pair)

- **Pinned commit:** `c714453e52f0ae897861b576f8d98e3da274f997` (code hash `783e9a3d…`)
- **Scope:** approve or reject **Amendment A9 (DRAFT)**. Nothing has run. Stages B1c/B1/B2/B3 refuse while A9 is a draft (exit 13), and also refuse without Stefan's per-stage go (`E1B_GO`, exit 14). No Kaggle kernel has been pushed.

## Context
- **Primary B0 result (unchanged):** NO QUALIFYING PAIR (`7873596`).
- **Post-hoc A8 extension:** `e1b-stage-b0` v3 at `e258b45` ([B0_REPORT.md](https://github.com/devamped1337/glyph-alphabet-experiments/blob/c714453e52f0ae897861b576f8d98e3da274f997/v6/e1b/B0_REPORT.md)). All checks passed and the validator passed.
  - Falcon3-7B: F1 0.958 / 1.000, F2 0.972 / 1.000, F3L (exploratory) 0.979 / 0.650.
  - Qwen (reused): F1 0.924 / 1.000, F2 0.924 / 1.000.
  - The pair qualifies; B0x used 0.81 of its 1.2 GPU-h.
- **Duplicate kernel excluded:** `e1b-stage-b0x`, pushed by an automation on 2026-10-14. Its output is excluded and has not been looked at.

## A9 in one screen ([PREREG_E1b.md §A9](https://github.com/devamped1337/glyph-alphabet-experiments/blob/c714453e52f0ae897861b576f8d98e3da274f997/v6/e1b/PREREG_E1b.md), [config](https://github.com/devamped1337/glyph-alphabet-experiments/blob/c714453e52f0ae897861b576f8d98e3da274f997/v6/e1b/config_e1b.json), [a9.py](https://github.com/devamped1337/glyph-alphabet-experiments/blob/c714453e52f0ae897861b576f8d98e3da274f997/v6/e1b/e1b/a9.py), [tests](https://github.com/devamped1337/glyph-alphabet-experiments/blob/c714453e52f0ae897861b576f8d98e3da274f997/v6/e1b/tests/test_a9.py))
- **Labels:**
  - Every B result is a POST-HOC follow-up (A8 pair); B0's primary result stays NO QUALIFYING PAIR.
  - The TII attribution line goes on every Falcon result.
- **Fresh book:**
  - Rebuilt with new seeds 81062–81067; sha `bc0df849…`, pinned and committed before any run.
  - Asserted disjoint from the frozen book: no case text, entry text or id is shared.
  - Only the 20 canary prompts are copied, to keep the B0x canary references.
- **Both models fresh:** no reuse. Same nf4/fp16 backend, A7 pins, prompts and batch rule. The manipulation check runs on Falcon (higher B0x score).
- **Budget:** total ≤ 12.0 of about 16 GPU-h. Cap = projection / 0.8, from B0x pilot timings. The first ladder level that fits wins:

  | level | config | cases/entry | F3L | Σ projected | Σ caps |
  |---|---|---|---|---|---|
  | L0 | C100 | 10 | yes | 23.93 | 30.00 |
  | L1 | C60 | 10 | yes | 16.58 | 20.80 |
  | L2 | C60 | 5 | yes | 10.71 | 13.45 |
  | L3 | C60 | 5 | no | 9.73 | 12.20 |
  | **L4** | **C60** | **4** | **no** | **8.70** | **10.95** |

  L4 caps: B1c 0.60, B1 3.10, B2 5.70, B3 1.55 GPU-h. B2 dominates: 2 × 600 receiver calls plus the cache test and warm-prefix timing.
- **Stops:**
  - Fixed per-stage caps in `a9_state.json`, never recomputed; hitting a cap means INCOMPLETE.
  - At most 1 start + 1 infra retry per stage, resumed by key under the same cap.
  - Access errors are not retried.
- **Deferred items:**
  - (a) The per-entry bar is kept at ≥ 22/24, with a pre-stated binomial expectation (Qwen 0.73 per entry), so honest acceptance below 0.80 is the expected outcome. The binomial test is reported descriptively only.
  - (b) Reserve templates: deferred, because only F3L-waive was flagged and F3L is not run at L4.
  - (c) Batch rule: new B1c compares batch 8 with batch 1 on 60 non-TEST items per model. Pass needs ≥ 99% (60/60); a fail means a stop-and-report for this budget period.
- **Launch:** no default stage, no automation. Each push needs Stefan's explicit go for that stage. No Mistral.

## Questions
1. Approve A9 as drafted (yes / no / yes-with-changes)?
2. **Ladder:** is reaching L4 by first cutting cases per entry 10 → 5, then dropping the exploratory F3L arm, then going 5 → 4 the right order? Or should F3L be dropped before any case cut? (L2 with F3L needs 13.45 h of caps.) Is 4 cases per entry acceptable?
3. **(a) Per-entry bar:** keep ≥ 22/24 unchanged (the gate will likely be ineligible, so B2/B3 run ungated)? Or is a change justified even though it would be made after the qualification accuracies were seen?
4. **(c) B1c:** is 60 items with an exact-match requirement (60/60) right, or should it be 100 items (≥ 99/100, about +0.3 GPU-h)? Should it compare parsed answers or full token sequences?
5. **Fresh book:** is copying only the canary pool acceptable? Should the qualification, pilot and probe-diagnostic pools also be kept from the frozen book (they are rebuilt now but unused by B1–B3)?
6. **Retry rule:** is 1 start + 1 infra retry with resume-by-key right for multi-hour checkpointed stages (unlike A8's single-attempt rule)?

## Settled (don't reopen here)
- B0 primary result: no qualifying pair. Mistral and other European models are excluded. Llama is excluded (gated). The A8 selection and license resolution stand.
