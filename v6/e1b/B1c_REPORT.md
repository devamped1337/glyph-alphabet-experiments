# E1b Stage B1c report (A9 post-hoc follow-up)

**Status:** PASS (batch-size rule). Frozen A9 stage order: B1c → B1 → B2 → B3.  
**Kernel:** `devamped13/e1b-stage-b1c` (COMPLETE). Done marker: `2026-10-14 03:32:59 UTC`.  
**Pinned:** commit `b2ec2f3` / tag `prereg-e1b-a9`, `CODE_HASH` `d0203f221f243991917520e0ccc322b5937661e24e3ea653dd3c5907584a23d6`.  
**Pair:** qwen7b + falcon7b (A8 post-hoc). Primary B0 result stays `NO_QUALIFYING_PAIR`.

## Did the test actually run?

| Check | Result |
| --- | --- |
| GPU preflight | PASS both models (Tesla T4, nf4 / `hf-nf4`, not CPU) |
| Canaries | qwen7b 20/20, falcon7b 20/20 |
| Items | 120 non-TEST per model, stratified 60 arithmetic + 60 probe |
| Batch-1 vs batch-N parsed-decision match | **120/120 (1.000)** each model; path a 60/60, path p 60/60 |
| Raw-string identical | qwen 117/120, falcon 118/120 (token diffs allowed; decisions still match) |
| Chosen batch size | **8** (112 items at 8; remainder 8 items at batch 4 in the last short batch) |
| Cap | 0.65 h; used **0.442 h** (`A9_B1c` 1592.7 s in budget ledger) |
| Terminal | `.done` present; `batch_rule.json` / `summary.json` have `pass_: true` |

Independent re-pair of `batchcheck_*.jsonl` (batch1 vs batchN by item id) reproduces the 1.000 match rates. Probe rows store the letter in `raw` with `pred: null` and `parse_path: letter`; the batch rule compares decisions, not the null `pred` field. One qwen probe was content-wrong on gold (raw `A` vs gold `D`); that is not a batch-conformance failure.

## Rule outcome

Per A9 § batch-size rule (≥ 99% match → use batch 8 for B1–B3): **PASS → batch_size = 8**.

## Next

B1 is ready to prepare. Cap 3.20 GPU-h. Launch only on Stefan's explicit go (`E1B_GO=B1`). No Kaggle push from this report alone.
