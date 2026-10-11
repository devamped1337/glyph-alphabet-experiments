# v5 review, round 2 request

This goes to GPT, Claude, Grok and Grok Bot.

1. Read [round1/ALL_FOUR.md](round1/ALL_FOUR.md). It contains all four round-1 reviews plus GPT's follow-up. Also read the ERRATA and "Round-1 checks" sections of [RESULTS_v5.md](../../RESULTS_v5.md).
2. State where you now agree and where you disagree with each of the other reviews. Settle every disagreement by recomputing from the per-query files (predictions_qwen.jsonl, predictions_smol.jsonl at data commit 48a7a6a5), not by reading tables. Say which numbers you recomputed.
3. Flag anything that all four reviews missed.
4. Propose the v6 PREREG. At minimum it should include:
   - **A contextual channel as its own fixed comparison.** Fix a mid-depth contextual layer (and a J-lens or sparse basis, if it can run) in advance and evaluate it on TEST against an **embedding baseline**, rather than letting one DEV argmax choose between them.
   - **LOO split by answer-held-out, with no receiver fallback.** Remove the held-out entry from the receiver's book, and report the answer-held-out and other-held-out results separately against no-message.
   - **A behaviour-based gate for the text repository.** An entry passes if both models act the same on its expanded definition across fresh test cases. Re-run the planted bad entries against this gate.
   - **Logged coverage** for every condition, so that accuracy among covered messages and end-to-end accuracy are both reported.
   - Raw-residual readout reported separately from snapped lookup, and receiver compute measured without fixed 64-token padding.
