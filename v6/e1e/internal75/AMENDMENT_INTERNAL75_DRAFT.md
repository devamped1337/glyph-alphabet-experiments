# Amendment internal-75 (DRAFT) — exploratory synthetic cohort

Date: 2026-11-10 (Australia/Sydney). Status: **data freeze of the attached bytes; not a code freeze; not a tag; measurement not run.**

This file does not edit `E1F_PROPOSAL_DRAFT.md`, `E1F_AMENDMENT_A1_DRAFT.md`, `BYTE_AUDIT_PLAN_DRAFT.md`, or any module under `e1e/`. The grid `L ∈ {32,64,128,256}`, `k ∈ {2,3}`, `C ∈ {50,200,1000}`, the 20% Stage-1 floor, the retirement rule, and the seed `e1e-fold-1` stay as they are on `e1f-freeze` commit `2903702144efd135c25da9c70216debed40c205a`.

## What the owner already decided

The owner accepted this 75-message set (t1393u) and said to run the experiment after packaging and disclosure (t1394u, ~09:35 AEDT). That approval is for a later CPU byte measurement. It is not a result, and it is not a review of this code. GPT and Grok still have to review this plan and this commit before that measurement starts. No further owner question is required for the packaging itself.

## Cohort

75 synthetic messages, 30 whole conversations, all dev, held-out count 0. Authors, as labels of who wrote the synthetic lines, not as outside contributors: GPT 25, Grok 25, Claude 15, Glyph 10. Combined file sha256 `b94115fb424947f0555b2ba6669f8d3ba11b53e664e640d4b9670a6b30535439` (22064 bytes). Author-file hashes are in `MANIFEST.json`. Bodies are the attached bytes. Nothing in this prep rewrites, strips, or normalises them.

`e1e-fold-1` is recorded and **not** applied. `split_real` is not called. Synthetic corpora are all dev under E1f proposal §4. The external gate remains unmet: 0 evaluation-eligible outside messages. Tessera's four and Tidemark's five are not in these files.

The message bytes are the data freeze. The canonical package zip, hashed from the delivered file in this workspace, is sha256 `990b3ef816dedfe140ecd0a8d27675bd27b5c575f1ac825fab32c438d2e58cbc` (74912 bytes). The copy of the combined JSONL inside that zip is the same 22064 bytes. The handoff stored inside the zip still says zip sha256 `818a0e67d34eca9119190ef21fa6ac8003cb9b1b92da8e9194e7ff934553ce0e`. That value is the previous package-pass hash, kept so the zip and the handoff do not chase each other. It is not a change to the messages. An earlier initial hash `b89637b7fe7443506671ea7893dad65eb2b0290d279292ed06a844ac884f6b58` is also not the corpus and not the canonical zip. The historical partial-50 package is unchanged and is superseded by this 75-message set. The zip itself is not committed: it holds prompts and receipts outside this public review set.

## What a later run may do

One descriptive replay, in sample, on these 75 only:

- Fixed point transferred from the already published public-synthetic screen: `L=32`, `k=2`, `C=50`. It is not chosen again on these messages.
- Primary scenario only: `V=5`, 2 participants, 0 joiners. zstd level 19, headline frame, pin `zstandard==0.23.0` / libzstd 1.5.6.
- Arms 1, 3, 4b, 4b-delta, 5, 6, 7, plus byte-audit baseline 2 (gzip-9, `mtime=0`, message bytes only).
- Arm 4 is not run. `select_baseline4` would train a dictionary on the same messages being scored.
- No call to `tune`, no grid sweep, no edit of the floor or the retirement rule.
- Byte-exact decode is the frozen `replay_arms` assert. A mismatch aborts. There is no second parameter set.
- No timings and no speedup claim. If the run happens, a second invocation must reproduce the aggregate sha256 or the run is invalid.
- Stop conditions, fixed before any result: one process; no Kaggle, GPU, model call, or paid API; no second parameter set; abort on the first byte-exact mismatch; abort if zstd is not 0.23.0 / libzstd 1.5.6; abort if the combined hash differs; do not overwrite the old dev-screen files. Operator wall-clock cap: kill the process if it exceeds 60 seconds. The published 300-message synthetic screen recorded 1.4 seconds including tuning. That figure is a scale reference for a larger, tuned job, not a measurement of these 75.

## Decision the run is allowed to answer

On this synthetic internal cohort, after repository and setup bytes, is arm 7's primary-scenario total strictly smaller than both arm 4b-delta and arm 6?

A yes would be an exploratory synthetic observation. It would not show that the representation saves bytes on real outside traffic. It would not meet the ≥50 / ≥20 / ≥3 outside gate. It would not clear the earlier Stage-1 failures (synthetic coverage about 3.2%, Glyph-own about 1.2%, both under the 20% floor; arm 7 larger than 4b-delta on both). Those files stay as they are. A coverage figure on these 75, even if it were above 20%, does not reopen them.

## What stays blocked

Held-out replay, outside-gate claims, pooling with `synthetic_gpt_r1.jsonl` or the private Glyph-own corpus, entry `prov` values other than the existing `synthetic` label, and any forum post. The contribution kit still rejects `synthetic=true`; these lines are not submitted through it.
