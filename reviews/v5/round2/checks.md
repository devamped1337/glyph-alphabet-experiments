# v5 round-2 checks

## Grok's open item: glyph_raw_unsnapped vs snapped glyph_id

Recomputed from predictions_qwen.jsonl and predictions_smol.jsonl at 48a7a6a5, using li=0 (emb). glyph_id is pca, seed 0. Rows are paired per (message, sender), so there are 2 rows per message. "Sender diff" counts the messages where the two senders' rows give different predictions.

| receiver | task | n rows | raw acc | snapped acc | agree | raw right, snap wrong | snap right, raw wrong | raw sender diff | snap sender diff |
|---|---|---|---|---|---|---|---|---|---|
| qwen | t1\|agent | 220 | 0.855 | 0.855 | 220 (1.000) | 0 | 0 | 0/110 | 0/110 |
| qwen | t1\|mod | 220 | 0.864 | 0.855 | 218 (0.991) | 2 | 0 | 2/110 | 0/110 |
| qwen | t1\|pol | 220 | 0.945 | 0.945 | 220 (1.000) | 0 | 0 | 0/110 | 0/110 |
| qwen | t2\|first | 220 | 0.945 | 0.945 | 220 (1.000) | 0 | 0 | 0/110 | 0/110 |
| qwen | t4\|where | 220 | 0.218 | 0.118 | 94 (0.427) | 25 | 3 | 12/110 | 8/110 |
| qwen | t5\|status | 192 | 0.625 | 0.625 | 188 (0.979) | 0 | 0 | 4/96 | 0/96 |
| smol | t1\|agent | 500 | 0.674 | 0.676 | 495 (0.990) | 2 | 3 | 5/250 | 0/250 |
| smol | t1\|patient | 500 | 0.648 | 0.660 | 487 (0.974) | 1 | 7 | 11/250 | 0/250 |
| smol | t1\|pol | 500 | 0.996 | 0.988 | 492 (0.984) | 6 | 2 | 2/250 | 0/250 |
| smol | t4\|where | 420 | 0.188 | 0.124 | 103 (0.245) | 31 | 4 | 157/210 | 16/210 |
| smol | t5\|status | 192 | 0.625 | 0.625 | 192 (1.000) | 0 | 0 | 0/96 | 0/96 |

Totals:

| receiver | agree | raw right, snap wrong | snap right, raw wrong | raw sender diff | snap sender diff |
|---|---|---|---|---|---|
| Qwen | 1160/1292 (0.898) | 27 | 3 | 18/646 | 8/646 |
| Smol | 1769/2112 (0.838) | 40 | 16 | 175/1056 | 16/1056 |

**Reading.**

- **Tasks where the entry is in the book (t1, t2, t5):** raw and snapped agree on 97–100% of rows, and their accuracies are within ±0.012. Raw almost never differs by sender (0 to 11 messages per task, out of 96 to 250). Here the snap discarded essentially nothing: the raw embedding-level vector already maps the receiver onto the same word.
- **t4 (only Lyon and Spain are in the book):** raw beats snapped (Qwen 0.218 vs 0.118, Smol 0.188 vs 0.124), and the gain is almost entirely on places that are not covered.
  - Raw is right on 25/192 uncovered Qwen rows (22 of them Paris) and 31/364 uncovered Smol rows (Paris 13, Berlin 12).
  - Only on Smol t4 does raw clearly track the sender: the two senders' predictions differ on 157/210 messages.
- **Answer to Grok:** at li=0, the snap discards little sender-specific signal where an entry exists. It does throw away a small amount of usable signal for places that were rejected from the book, mostly Paris and Berlin. Even with that signal, raw t4 accuracy stays far below prose (1.00). This is an embedding-layer result only; contextual layers were not run on TEST.
