# E1b Stage B3r report (A10: post-hoc diagnostic completion, secondary)

> **PRIMARY RESULT, UNCHANGED: A9 B3, POC FAILED** (PREREG §10). Both directions failed the frozen A9 success criterion; Falcon→Qwen made zero ID receiver calls. A10 cannot overturn that verdict. Everything below is **secondary and post hoc**: it was run on a TEST set we had already seen, after an exploratory re-parse (56/60) had shown what the result would likely be.

**The original A9 Falcon→Qwen result** was a **frozen-parser failure with zero ID receiver calls.** All 60 Falcon sender replies were scored `invalid_multiple` (Falcon wrote "X) F1" or "X) F2"), so all 240 id_selected items were `sender_invalid`. It demonstrates failure of the frozen pipeline but does not measure receiver performance given valid IDs.

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
- **Selection** (on these 60 archived replies, under the revised A10 parser): 56/60 = **0.933** (CI 0.87–0.98). Chance is 0.25; the regex baseline scores 0.75, so Falcon beats it by **+0.18** (CI 0.08–0.28).
- **Pipeline:** id_selected **0.929** (223/240) vs prose **0.992** (238/240, reused). The difference is **−0.0625**, CI **−0.133 to −0.004**, against the −0.05 margin: **INCONCLUSIVE**. The label follows the frozen rule **A1.2**, which replaced the §10 wording: labels are mutually exclusive and set by the CI alone (lower bound > −0.05 → non-inferior; upper bound < −0.05 → inferior; otherwise inconclusive). The point estimate is below −0.05, but under A1.2 that does not by itself make a label; the code applies the same rule (`analysis.label`). Non-inferiority was **not** established, and the upper bound is below zero.
  - The CI comes from a **paired cluster bootstrap over the 60 entries** (2000 resamples, A9 seed). The 240 scored items are 4 cases per entry, not 240 independent observations.
  - By family (**descriptive only**, not part of the frozen headline): F1 −0.10, F2 −0.025, both inconclusive.
- **Errors:** of the 17 id_selected errors, 16 come from the 4 wrong picks (0/16 correct) and 1 happened despite a correct pick. With a correct pick, Qwen answered 223/224. This is **descriptive conditioning** on the observed picks; it does not show what the pipeline would score under an intervention that fixed selection.
- **Bytes (this direction only):** the comparator is the original prose message.
  - **Payload** compares the ID rule part (`ID@version#hash8` with its framing) with the prose message's UTF-8 bytes: **−89%**.
  - **Whole exchange** adds the identical case-text bytes and any sender wire bytes to both arms: **−59%**, above the ≥30% target in this direction.
  - Dictionary setup cost is reported separately in `summary.json` (break-even about 235 messages). The saving is near-guaranteed by design (A1.6, §9).
- **Caveats:**
  - The prose arm comes from an earlier session. B1c and B2 provide supporting checks but do not quantify or eliminate cross-session effects, and **the CI does not account for any cross-session bias**.
  - The TEST set had already been seen, and the parser fix was chosen after seeing the failure.
  - There are 60 entries, so power is limited.
  - There is no checked-repository claim (the gate was dropped).

## Reading
- Under the revised parser, Falcon's 60 archived replies selected correctly 0.93 of the time. That is limited to these replies and this TEST set.
- Even so, the end-to-end ID pipeline still did not reach non-inferiority in this direction. In the A9 Qwen→Falcon direction it was inferior.
- **The E1b answer is unchanged: no evidence that the ID channel matches prose under our pre-registered bar.**
