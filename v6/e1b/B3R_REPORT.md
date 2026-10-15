# E1b Stage B3r report (A10: post-hoc diagnostic completion, secondary)

> **PRIMARY RESULT, UNCHANGED: A9 B3, POC FAILED** (PREREG §10). Both receiver directions were inferior under the frozen A9 protocol. A10 cannot overturn that verdict. Everything below is **secondary and post hoc**: it was run on a TEST set we had already seen, after an exploratory re-parse (56/60) had shown what the result would likely be.

**The original A9 Falcon→Qwen result** was a **frozen-parser failure with zero ID receiver calls.** All 60 Falcon sender replies were scored `invalid_multiple` (Falcon wrote "X) F1" or "X) F2"), so all 240 id_selected items were `sender_invalid`. That result says nothing about communication.

**Run:** kernel `devamped13/e1b-stage-b3r` v1 (COMPLETE), 16:27–16:40 AEDT, 2026-10-15. Code at tag `prereg-e1b-a10` (`097cacc`), code hash `77eceb53…`; `results/` from `bd218c8`. One start used, out of one.

Falcon3-7B-Instruct results were produced using artificial intelligence technology from the Technology Innovation Institute (TII Falcon License).

## Validity
| Check | Result |
| --- | --- |
| GPU / canaries | qwen7b PASS (Tesla T4, nf4); 20/20 |
| Sender replies | 60/60 archived replies, byte-identical, re-parsed with `parse_letter_a10`; no new sender call |
| Coverage | id_selected 240/240 and prose 240/240, covering the scheduled (entry, case) set exactly |
| Prose arm | 240 rows reused verbatim from A9 B3 (pinned sha256), not rerun |
| Parsing / truncation | 240/240 `answer_line`; max 102 generated tokens (limit 192) |
| Budget | 0.217 of 0.50 GPU-h. A10 total 0.37 / 1.0; A9 + A10 **6.52 / 12.0** |
| Validator | PASSED (the frozen A10 validator, including the r1 checks) |

## Secondary result: Falcon sends, Qwen receives (A10)
- **Selection:** 56/60 = **0.933** (CI 0.87–0.98). Chance is 0.25; the regex baseline scores 0.75, so Falcon beats it by **+0.18** (CI 0.08–0.28).
- **Pipeline:** id_selected **0.929** (223/240) vs prose **0.992** (238/240, reused). The difference is **−0.0625**, CI **−0.133 to −0.004**, against the −0.05 margin: **INCONCLUSIVE**. The CI straddles the margin and does not reach zero, so the ID arm was also measured as worse than prose.
  - By family (descriptive): F1 −0.10, F2 −0.025, both inconclusive.
- **Errors:** of the 17 id_selected errors, 16 come from the 4 wrong picks (0/16 correct) and 1 happened despite a correct pick. With a correct pick, Qwen answered 223/224.
- **Bytes:** payload −89%, whole exchange −59%.
- **Caveats:**
  - The prose arm comes from an earlier session. B1c and B2 provide supporting checks but do not quantify or eliminate cross-session effects, and **the CI does not account for any cross-session bias**.
  - The TEST set had already been seen, and the parser fix was chosen after seeing the failure.
  - There are 60 entries, so power is limited.
  - There is no checked-repository claim (the gate was dropped).

## Reading
- The parser fix shows that Falcon *can* select well (0.93).
- Even so, the end-to-end ID pipeline still did not reach non-inferiority in this direction. In the A9 Qwen→Falcon direction it was inferior.
- **The E1b answer is unchanged: no evidence that the ID channel matches prose under our pre-registered bar.**
