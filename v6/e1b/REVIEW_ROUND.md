# E1b review round 1

- **Pinned commit:** `fde7bb8315624767a8d7baad220b0f309ac8becd` (code hash `96a59725…`)
- **Scope:** A5 DRAFT resolution + the batching fixes. Nothing is frozen and nothing has been run on Kaggle.

## Changed since the last review (Stage A, `73a528b`)
- [AMENDMENT_A5_DRAFT.md](https://github.com/devamped1337/glyph-alphabet-experiments/blob/fde7bb8315624767a8d7baad220b0f309ac8becd/v6/e1b/AMENDMENT_A5_DRAFT.md):
  - §5b collects the Claude/Grok/GPT reviews of the draft;
  - §5d is the DRAFT resolution.
- Reviews: [claude_A5](https://github.com/devamped1337/glyph-alphabet-experiments/blob/fde7bb8315624767a8d7baad220b0f309ac8becd/v6/e1b/reviews/claude_A5.md), [grok_A5](https://github.com/devamped1337/glyph-alphabet-experiments/blob/fde7bb8315624767a8d7baad220b0f309ac8becd/v6/e1b/reviews/grok_A5.md), [gpt_A5](https://github.com/devamped1337/glyph-alphabet-experiments/blob/fde7bb8315624767a8d7baad220b0f309ac8becd/v6/e1b/reviews/gpt_A5.md). GPT's counts are verified (13/33/20 of 40), and our earlier "16" is reconciled.
- [Exploratory abstention test](https://github.com/devamped1337/glyph-alphabet-experiments/blob/fde7bb8315624767a8d7baad220b0f309ac8becd/v6/e1b/exploratory/abstention_test/README.md): the explicit instruction gave 0/23 abstentions, numeric stayed at 17/17, no over-abstention. No claims.
- Batching ([stages.py](https://github.com/devamped1337/glyph-alphabet-experiments/blob/fde7bb8315624767a8d7baad220b0f309ac8becd/v6/e1b/e1b/stages.py) `batched_generate`, [backends.py](https://github.com/devamped1337/glyph-alphabet-experiments/blob/fde7bb8315624767a8d7baad220b0f309ac8becd/v6/e1b/e1b/backends.py) `generate_batch`):
  - compute-once for byte-identical prompts (`shared_n`);
  - deterministic batch composition (length, sha) with `batch_index/pos/n` logged;
  - padding asserts and pad-token logging.
- **Bug fix (GPT):** batched HF generate no longer inherits generation_config (`NEUTRAL_GEN`, repetition_penalty=1.0).
- **Tests:** [smoke_hf_batch.py](https://github.com/devamped1337/glyph-alphabet-experiments/blob/fde7bb8315624767a8d7baad220b0f309ac8becd/v6/e1b/tools/smoke_hf_batch.py) with a penalised config gives batched == batch-1 on 8/8 + 6/6; 51 unit tests OK; the dry run passes.

## Questions for reviewers
1. Does the §5d DRAFT resolution reflect your position? Raise only errors in it.
2. Batching review: are padding, positions, per-row stop and NEUTRAL_GEN sufficient, and is anything missing before B0?
3. Which explicitly-wrong-rule plants should be strengthened, and to what bar? Is it changed_constant only (11/13 weak), with f/n >= 0.30 as Claude proposed?
4. Open items: reserve probe templates per kind, and the B0 batch-size rule (largest size with >=99% batch-1 agreement on non-TEST items).

## Settled (don't reopen)
- Proceed to B0 uncached. The cache claim stays withheld, and the GPU cache path is tested separately.
- *-unstated probes are excluded from the leak rule and kept as an abstention diagnostic. Leak checks stay on the other kinds.
- UNKNOWN-implying plants are reported separately and revisited after B. TEST plants stay untouched.
- B1 reports planted rejection per corruption type. The P4 entry bar is decided after B0 and before B1.
- The 0.90 bar is unchanged. The frozen PREREG and A1-A4 stand.
