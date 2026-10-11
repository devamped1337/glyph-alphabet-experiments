# Review grok_1: v6 E1 calibration (relayed summary)

Relayed 2026-10-11 (AEDT). This is a summary of the reviewer's points, not a verbatim transcript.

- The calibration failure is real: the gate did not separate honest from planted entries at 0.90.
- SmolLM2-1.7B is the main limiter. Under the weakest-link rule its low accuracy caps every honest entry.
- The planted entries that Qwen ignored (it answered with the honest gold despite the corruption, e.g. deleted_negation) should be **kept as a stress test** in any rerun.
- If the 0.90 bar is kept, the rerun needs a stronger gate pair.
