# E1b review round 3 (A8 draft: one bounded B0 extension)

- **Pinned commit:** `de992d1d647c1a7a62e12fa3dd28cb1351164586` (code hash `8c6562b5…`)
- **Scope:** approve or reject **Amendment A8 (DRAFT)**. Nothing has run. Stage `B0x` refuses to run until A8 is frozen. The kernel has not been pushed.

## Context
- B0 is closed at `7873596`: Qwen-7B qualified, OLMo-2-7B failed → **no qualifying pair**. This stays the primary E1b result.
- All three B0 reviews accept the stop: [grok_B0](https://github.com/devamped1337/glyph-alphabet-experiments/blob/de992d1d647c1a7a62e12fa3dd28cb1351164586/v6/e1b/reviews/grok_B0.md), [claude_B0](https://github.com/devamped1337/glyph-alphabet-experiments/blob/de992d1d647c1a7a62e12fa3dd28cb1351164586/v6/e1b/reviews/claude_B0.md), [gpt_B0](https://github.com/devamped1337/glyph-alphabet-experiments/blob/de992d1d647c1a7a62e12fa3dd28cb1351164586/v6/e1b/reviews/gpt_B0.md).
- Post-hoc OLMo diagnostic ([B0_REPORT.md](https://github.com/devamped1337/glyph-alphabet-experiments/blob/de992d1d647c1a7a62e12fa3dd28cb1351164586/v6/e1b/B0_REPORT.md)):
  - 0% invalid replies.
  - On the unstated probes, all 41/41 wrong answers were numeric, and 30 of them reused another number from the rule. Qwen-7B scored 72/72.

## A8 in one screen ([PREREG_E1b.md §A8](https://github.com/devamped1337/glyph-alphabet-experiments/blob/de992d1d647c1a7a62e12fa3dd28cb1351164586/v6/e1b/PREREG_E1b.md))
- **Candidate:** `tiiuae/Falcon3-7B-Instruct` @ `1e57a0ecd176c7c139f289c60a74e57f887c3dfb`, TII (UAE), 7.46B.
  - Anonymous access: `gated:false`, config.json 200, weights 206.
  - License: TII Falcon License. It is Apache-2.0-based and royalty-free, with an acceptable-use policy and an attribution clause.
- **Selection rule (written before any abstention evidence for the candidates was looked at):**
  - (i) Eligibility: ≥7B; no token needed; no Mistral or European lab; a lab other than Alibaba; loads under the A7 environment; fits a T4.
  - (ii) Size inside 7–8B.
  - (iii) OSI license.
  - (iv) Latest release.
- **Rule outcome:**
  - Granite-3.x-8B was dropped at (ii): 8.17B.
  - Phi-4-mini is ineligible at (i): 3.8B.
  - Mistral, Llama and OLMo were excluded earlier and are listed in the table.
- **Unchanged:** bars, unstated probes in qualification, pools, scoring and parsing, generation settings, canary rule, leak rule, 5% invalid rule, nf4 config.
- **Qwen reused:** byte-identical copy of its B0 records, with sha256 logged. Same nf4 backend, A7 environment, book, pools and code path.
- **Budget:** ≤1.2 GPU-h from the reserve (1.62 left).
- **Stop rule:** one attempt, no chain. If Falcon fails, the result is NO_QUALIFYING_PAIR and E1b stops.
- **If the pair qualifies:**
  - The result is a post-hoc follow-up only.
  - B1–B3 stay blocked until a new budget period and a further amendment with a **fresh TEST pool**.

## Questions
1. Approve A8 as drafted (yes / no / yes-with-changes)?
2. Is the selection rule acceptable, and is the Falcon license acceptable under "free access"? Note its AUP and attribution clause.
3. Is reusing Qwen's run-2 records justified, or must Qwen be re-run alongside Falcon? Re-running would cost about 0.75 GPU-h, and both models would then not fit in 1.2 GPU-h with margin.
4. Is the 1.2 GPU-h cap right? OLMo took about 0.78 GPU-h for the same sequence.

## Settled (don't reopen here)
- B0 primary result: no qualifying pair (`7873596`).
- Mistral and other European models are excluded (user rule). Llama is excluded (gated).
- `*-unstated` probes count in qualification.
