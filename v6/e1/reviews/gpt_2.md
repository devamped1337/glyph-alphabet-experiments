# Review gpt_2: v6 E1 results (summary relayed by the user)

Relayed 2026-10-12 (AEDT). This is a summary of GPT's points as relayed by the user, not a verbatim transcript.

- **Reproduced:** the counts, CIs, gate, unknown-ID results and all 2080 gold answers. The validator passed.
- **Per task (id_expanded / prose, %, n=160 each):** Qwen F1 98.8/99.4, F2 76.3/61.9, F3 16.9/31.3. Smol F1 34.4/30.6, F2 41.3/29.4, F3 10.0/5.6. On Qwen, +23 points on roles (F2) and −23 on long definitions (F3) cancel out.
- **Qwen vs prose:** the CI [−7.5, +7.9] crosses the ±5 margin, so the result is **inconclusive, not equivalent**.
- **Smol's advantage** looks like a presentation effect. Testing that needs a direct-text baseline with the exact expanded definition and matched framing.
- **Cold vs cached:** predictions differ on 45/480 (Qwen) and 104/480 (Smol), and correctness flips on 21 and 33 of them, even though the prompts are identical and decoding is greedy.
- **Overlap:** 97/480 main questions duplicate calibration questions (43 F1, 54 F3), and there are 9 more duplicates within main.
- **"End-to-end" is wrong:** these are oracle-ID receiver accuracies with the gate bypassed.
- **The gate TEST figures** are descriptive only.
- **The validator** is an engineering check. It does not certify the claims.
