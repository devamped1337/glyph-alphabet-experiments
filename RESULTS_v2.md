# Shared glyph alphabet: negotiated dictionary pass (v2)

Run date: 10 Oct 2026, Sydney time. Machine: CPU-only box (8 threads). Models: Qwen/Qwen2.5-0.5B and HuggingFaceTB/SmolLM2-360M. Artifacts live under `results/v2/` and `dictionary_v2.json`.

## What changed from v1
v1 imposed a 2000-word anchor alphabet. v2 negotiates: only concepts that pass meaning, round-trip, geometry, and readability for both models are kept. The agreed set is a versioned 96-d canonical dictionary with per-model adapters.

## Negotiation (10 rounds)
- Started from a few hundred probe concepts; finished with **183 accepted** (176 passed every check, rest on probation then filtered).
- Final rates: meaning 0.94, round-trip 0.98, geometry 0.995, readability 1.00 (both models). Global RSA Spearman 0.935.
- Kept relation operators: country→capital, country→language, country→city (non-capital), male→female, adj→comparative. Dropped number→next and (by the end) adj→opposite as unstable.
- Dictionary file: `dictionary_v2.json` / `results/v2/dictionary_v2.pt` (created 2026-10-10 07:40 AEDT).

## Retrieval in canonical space (vs v1)
| set | glyph | A→B @1 | B→A @1 | shuffled control @1 |
|---|---|---|---|---|
| multihop | adapter_mu | 0.656 | 0.473 | 0.005 |
| multihop | set_mean | 0.591 | 0.613 | 0.004 |
| multihop | v1 late J-lens | 0.624 | 0.624 | 0.009 |
| assoc | adapter_mu | 0.098 | 0.127 | 0.011 |
| assoc | set_mean | 0.480 | 0.422 | 0.006 |
| paraphrase | adapter_mu | 0.400 | 0.250 | 0.010 |
| paraphrase | set_mean | 0.613 | 0.550 | 0.013 |

Centering matters: assoc collapses under adapter_mu and recovers under set_mean. Multihop adapter_mu is roughly on par with v1 late-band J-lens, still well above shuffled.

## Causal injection (negotiated glyphs)
Task: hop-1 country fact → inject into a capital/language prompt that omits the bridge. Chance ≈ 0.07. Covered bridges: 11 countries (22 prompts where the concept is in the dictionary).

Best α for each condition (accuracy):

| direction | none | text single word | text bow16 | dict lookup | sender snap | sender raw | shuffled | wrong concept |
|---|---|---|---|---|---|---|---|---|
| Qwen→Qwen | 0.07 | **0.86** | 0.75 | **0.73** (α2) | 0.54 | 0.61 | 0.11 | 0.12 |
| Smol→Smol | 0.07 | **1.00** | 0.46 | **0.77** (α2) | 0.50 | 0.43 | 0.15 | 0.14 |
| Qwen→Smol | 0.07 | **1.00** | 0.64 | **0.77** (α2) | **0.64** | 0.57 | 0.15 | 0.14 |
| Smol→Qwen | 0.07 | **0.86** | 0.46 | **0.73** (α2) | 0.39 | 0.29 | 0.11 | 0.12 |

### Honest read
- **Negotiated glyphs beat the controls.** Dict lookup and live sender encodings sit far above shuffled / wrong-concept / wrong-country.
- **Plain text still wins.** A single country word as text remains the strongest condition. That is the same ceiling v1 hit: the glyph path is causal and cross-model, but not yet more efficient than naming the concept.
- **Dict lookup ≈ receiver-side agreed vector.** Scores match by receiver (0.73 into Qwen, 0.77 into Smol), so the strong dict-lookup number is "inject the shared concept" more than "transfer a live sender state". Live transfer is the snap/raw columns; Qwen→Smol snap (0.64) is the best cross-model live transfer.
- Sender snap-to-dictionary is imperfect (Qwen snap_correct 0.57, Smol 0.36), which caps live transfer.

## Files
- `dictionary_v2.json`, `results/v2/dictionary_v2.pt`, `results/v2/negotiation.json`
- `results/v2/metrics_v2.json` (retrieval + minimal pairs)
- `results/v2/inject_*.json`, `results/v2/inject_tables.json`
- Code: `v2/negotiate.py`, `v2/inject_v2.py`, `v2/analyze_v2.py`, `v2/concepts.py`

## Next (already approved)
Closed maths book: digits 0-9, add/subtract/equals/greater-than, fixed left/operator/right/result slots, negotiated the same way, scored against terse `7+2=` text, scrambled bag, and operator-shuffled glyph.
