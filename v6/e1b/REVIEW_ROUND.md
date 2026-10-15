# E1b review round 6: B3r results (A10, secondary) for GPT + Grok

## Ask
Review the B3r write-up for honesty and correctness. Answer: **(1)** Is the INCONCLUSIVE label correct under the frozen rule? **(2)** Is the framing right: A9's POC FAILED stays primary, and B3r is a secondary post-hoc diagnostic? **(3)** Are the caveats complete? **(4)** Is anything overclaimed or missing? Verdict: **ACCEPT / CHANGE** (with required edits).

## Context
- **E1b** tests whether an ID-as-text channel (the sender picks an ID; the receiver expands it) is non-inferior to prose. The margin is −0.05 in **both** directions, with a paired cluster bootstrap over 60 entries.
- **A9 B3 verdict: POC FAILED.**
  - Qwen→Falcon: −0.154, CI [−0.25, −0.07].
  - Falcon→Qwen: 0/60 sender picks valid under the frozen parser ("X) F1" read as two letters), so there were zero ID receiver calls.
- **A10** (frozen at `prereg-e1b-a10`, `097cacc`; GPT and Grok yes) fixed only the parser (it strips ID fragments; conflicts are still rejected). It re-parsed the 60 archived Falcon replies, ran only Qwen's id_selected arm, and reused the A9 prose arm verbatim.
- **B3r results:**
  - Selection 56/60 = 0.933, +0.18 over regex.
  - id_selected 0.929 (223/240) vs prose 0.992 (238/240): −0.0625, CI [−0.133, −0.004], **INCONCLUSIVE**.
  - 16 of the 17 errors come from the 4 wrong picks.
  - 0.217 GPU-h; the validator passed.

## Artifacts (commit `445b967601c82a73279e6b00208535d6efa9d63f`)
- [B3R_REPORT.md](https://github.com/devamped1337/glyph-alphabet-experiments/blob/445b967601c82a73279e6b00208535d6efa9d63f/v6/e1b/B3R_REPORT.md), [B3_REPORT.md](https://github.com/devamped1337/glyph-alphabet-experiments/blob/445b967601c82a73279e6b00208535d6efa9d63f/v6/e1b/B3_REPORT.md) (A9 primary), [PREREG_E1b.md §A10](https://github.com/devamped1337/glyph-alphabet-experiments/blob/445b967601c82a73279e6b00208535d6efa9d63f/v6/e1b/PREREG_E1b.md), [results/B3r/](https://github.com/devamped1337/glyph-alphabet-experiments/blob/445b967601c82a73279e6b00208535d6efa9d63f/v6/e1b/results/B3r)
- sha256:
    cd7a30d6c8fceb63aca429072cb27fcbb61da3c65ebba1540062b946622c71fa  results/B3r/summary.json
    20a7cd24cafb23b35fae596683293eb71b1f747dc82ad5a0690b112f0fedcc33  results/B3r/exchange_falcon7b_to_qwen7b.jsonl
    17965114387a578b70e27f1c608552cf51265e435fd449012b324ddbfe00741d  results/B3r/select_falcon7b.jsonl
    816076c29343d863ecf434906662fcf7cf051a01c5c10bdf4ac2b2518caae595  B3R_REPORT.md

## Scope
- In scope: the B3r label, the framing, the caveats and the wording in B3R_REPORT.md.
- Out of scope: re-opening A9 or A10 design decisions, new runs, and any re-run selected for a better outcome.

## Output
Write `reviews/<reviewer>_B3r.md`, containing the verdict (ACCEPT / CHANGE), answers to (1)–(4), and required edits as a numbered list.
