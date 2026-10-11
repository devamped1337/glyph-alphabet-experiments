# GPT review round 1: follow-up correction (2026-10-11)

Note recorded by Grok Bot from GPT's follow-up, relayed by Stefan. GPT's points as relayed:

> Contextual layers DID run on DEV (pooled DEV: emb 75.0%, ~25% depth 71.6%, ~33% depth 67.3%), so the pre-registered rule correctly selected emb for TEST.

Verification at 48a7a6a5: recomputed with the prereg5.py Rule B logic (glyph_id rows on counted tasks, pooled over both receivers, from v5/results/dev_qwen.json + dev_smol.json): emb 0.7500, li1 (qwen L9 / smol L6) 0.7165, li2 (qwen L12 / smol L8) 0.6727, n=776 per depth. Matches frozen5.json. Per receiver: qwen 0.785/0.757/0.715, smol 0.707/0.667/0.621. CONFIRMED.
