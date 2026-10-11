# Review gpt_2: E1b PREREG DRAFT rev 3 (`1550275`) (summary relayed by the user)

Relayed 2026-10-12 (AEDT). This is a summary of GPT's points as relayed by the user, not a verbatim transcript. GPT reviewed rev 3 and had not seen rev 4 (`ee45548`).

1. **The power estimates are illustrative planning calculations.**
   - At 60 entries: half-width 4.87 points, ~52% non-inferiority power, ~4% equivalence power.
   - At 100 entries: 3.77 points, ~74%, ~48%.
   - "Inconclusive" is a legitimate outcome.
2. **Two predefined configurations: 60×10 or 100×10.** Choose 100 only if non-TEST pilot timings project every stage within budget with headroom. The choice is frozen before B1.
3. **B3 headline:** the selected-ID pipeline's accuracy is non-inferior, within 5 points, to giving the receiver the same original message, **plus** ≥30% fewer transmitted bytes, counting the ID, version and hash framing.
   - Report sender, candidate-preparation and receiver costs, plus dictionary setup with amortisation.
   - Call it a **communication proof of concept**.
   - Beating BM25 is a separate claim.
4. **Gate:** 80/90 is the calibration eligibility rule. 90/95 remains the reported repository target. Distinguish "met in sample" from a confidence bound.
5. **Precision:**
   - Mandatory: gold canaries, finite checks, and qualification in the actual nf4 config.
   - The higher-precision comparison is optional and budgeted.
   - <98% agreement alone is not a failure.
6. **Cache:** count independent prompts, state the assumptions, and check each runtime separately (CPU and Kaggle GPU).
7. **Rewrite the whole draft into one consistent specification**, with the superseded body text removed, so that each setting has exactly one answer. Keep the history in git.
