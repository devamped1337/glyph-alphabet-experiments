# Review grok_1: E1b PREREG DRAFT (summary relayed by the user)

Relayed 2026-10-12 (AEDT). This is a summary of Grok's proposed resolutions as relayed by the user, not a verbatim transcript.

- **A1:** 0.70 floor.
- **A5:** the upper CI of the cold/warm change rate must be ≤ the cold/cold rate, with **no slack**. Otherwise Stage B uses cold runs only.
- **B0:** ≥0.90 on the probes and ≥0.80 on direct text, on the qualification pool.
- **B1:** ≥0.80 honest acceptance and ≥0.90 planted rejection at the 0.90 gate. No post-hoc threshold.
- **B1 size:** ≥100 honest entries + 36 planted.
- **GPU split:** B0 2 / B1 4 / B2 6 / B3 3 *(conflicts with GPT: 2/3/2/5 + reserve 3)*.
- **Generation:** 192 max tokens, with the length logged. Restore the long F3 in B1.
- **Stage A models:** Qwen-3B + Smol, with Llama-3.2-3B optional.
- **Stage B models:** Qwen-7B + Llama-3.1-8B. Substitutes in order: OLMo, then Mistral, then Gemma. Stop if neither of the first two qualifies.
- **Cases:** 10 per entry, paired cluster bootstrap, CI width stated up front.
- **Overall:** the draft needs no structural change.
