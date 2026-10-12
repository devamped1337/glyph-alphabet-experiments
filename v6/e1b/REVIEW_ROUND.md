# E1b review round 2 (B0)

- **Pinned commit:** `7873596fdc127486d83c90baa65d1718585dec39` (code hash `ee9439a3…`)
- **Scope:** B0 run 2 results only. Stage B has stopped under the frozen prereg. No new run is proposed here.

## What ran
- [B0_REPORT.md](https://github.com/devamped1337/glyph-alphabet-experiments/blob/7873596fdc127486d83c90baa65d1718585dec39/v6/e1b/B0_REPORT.md) at the pinned commit.
- Amendment A7 (GPU preflight, bitsandbytes 0.47, Mistral removed, nf4 on T4). Run 1 (CPU GGUF fallback) is archived and superseded.
- Validity: GPU preflight PASSED for both models; backend `nf4`; E1b VALIDATION PASSED on Kaggle and locally; markers `.done` and `NO_QUALIFYING_PAIR`.

## Headline numbers (frozen bars)
| model | F1 probe / arith | F2 probe / arith | result |
|---|---|---|---|
| qwen7b | 0.924 / 1.000 | 0.924 / 1.000 | **QUALIFIED** |
| olmo7b | 0.840 / 1.000 | 0.736 / 0.883 | **FAILED** (no family passes) |

Pair: none. Only one lab qualified → Stage B stops (A7 §2/§3). Reserve used 1.38 GPU-h; 1.62 GPU-h remain.

OLMo's main miss is the abstention diagnostic: unstated probes 11/24 and 9/24 vs Qwen 24/24. Same gap-filling pattern as Stage A. Sensitivity (descriptive only): without unstated, OLMo F1 would be 0.917 but F2 still fails; that does not change the frozen decision.

## Questions for reviewers
1. Do you accept the stop: no qualifying two-lab 7B pair under the free-access constraints already locked (no HF gate, no Mistral/European, Llama gated)?
2. Any error in the validity checks, gold labels, or parsing that would reopen run 2 before we treat B0 as closed?
3. If a later amendment names a different second model, what must that amendment state so it is not a silent post-hoc swap after seeing these numbers?

## Settled (don't reopen here)
- A5 resolution and batching fixes from review round 1.
- `*-unstated` stays an abstention diagnostic excluded from the leak rule only; it still counts in qualification.
- B1–B3 do not run without a qualifying pair and a new amendment/prereg that cites these B0 results.
- Claude is out of free-tier credit for now; Grok and GPT are the active external reviewers.
