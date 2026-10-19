# GPT opinion on the E1d F2 fresh-test fix (Option A vs B), 2026-10-19

Codex exec, read-only sandbox, asked after GPT r3 (`b0b8d7c`); a quick design preference, not a review round. Final message saved verbatim from `/tmp/gpt_f2.txt`; GPT notes it inspected source only and did not rerun the enumeration.

I prefer **A, with six new role pairs**: it preserves E1c’s rate and arithmetic ranges while providing more headroom. The counts are plausible from the [generator](/workspace/glyph-repo/v6/e1b/e1b/cases.py:39): each new pair adds `8×7=56` texts, so `83+5×56=363` and `83+6×56=419`; B adds `10×(10×9−8×7)=340` possibilities, consistent with 419 fresh if those additions survive historical exclusions. This was source inspection only; I did not rerun enumeration.

A still changes vocabulary, token lengths and possible semantic cues, so choose distinct, unambiguous roles with similar familiarity and length. B changes rate magnitudes, products and derived-message differences; two-digit numbers already occur in quantities and shifted neighbours, so the concern is a **distribution shift**, not their first appearance.

The main missed risk is that **419 available texts does not guarantee 315 distinct sampled cores**: the [book builder](/workspace/glyph-repo/v6/e1c/e1c/book.py:49) samples duplicates before selecting unique rules. Re-qualification should therefore demonstrate full-book feasibility across the predeclared throwaway seeds, preserve freshness and branch/neighbour checks, and exercise the expanded vocabulary through both models’ sender, verifier and receiver paths with the existing message-style mix. Reusing E1c dev alone cannot qualify unseen roles; disclose the generation change and remeasure serialized costs before freeze.

tokens used: 25,569
