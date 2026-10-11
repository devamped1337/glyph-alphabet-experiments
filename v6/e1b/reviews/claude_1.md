# Review claude_1: E1b PREREG DRAFT (summary relayed by the user)

Relayed 2026-10-12 (AEDT). This is a summary of Claude's points as relayed by the user, not a verbatim transcript.

> **Note:** Claude read **only** `v6/e1b/PREREG_E1b_DRAFT.md` (rev 1, `ce7cd5d`). It did not read the code or the data, and recomputed nothing.

## On the [OPEN] items
- Keep **0.90** per model on the probes and on agreement, but use **≥20 probes per entry**.
- Write the **calibration-separation** and **TEST-pass** thresholds explicitly, as separate bars.
- Define the verdict when the point estimate passes but the CI straddles the bar: **"pass, imprecise"**.
- **Measure B0 tokens/s** and derive N from it by a written formula.
- ≥100 entries is fine (power ≈0.038 pooled, ≈0.065 per family). Per-family results are descriptive.
- Add **Llama-3.2-3B for A1–A4 and A6**. Use **Smol for A5 only**.
- The long F3 returns at 7B, **kept separate** from the shortened family.
- A family that fails qualification is excluded from the gate and from the B2 primary, but is still reported.

## Four fixes
1. **Precision:** T4/P100 GPUs have no native bf16, and a 7–8B model in fp32 doesn't fit. Choose either fp16 with a fail-loud overflow guard plus a reference smoke check, or 8-bit. Use the same precision everywhere and log it.
2. **B2 budget:** about 12k generations and over 1M tokens need batched generation. Check the budget against B0's measured throughput.
3. **The A5 cache rule can't be proved at n=120.** Use 480 per model, with the margin cold/warm ≤ cold/cold + 0.03. Log the top-2 logit gap on the first answer token.
4. **The rule probes must not leak the answer.** Add a no-entry-text probe check (expected near 0.25 chance). Use invented rules only. Every planted corruption must flip the gold answer of at least one probe.

## Smaller points
- B3 must beat a **retrieval baseline** (BM25 or nearest-label embedding).
- A Stage A calibration amendment **cannot carry repository claims**.
