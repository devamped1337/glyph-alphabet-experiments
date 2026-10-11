# Review claude_2: v6 E1 results (summary relayed by the user)

Relayed 2026-10-12 (AEDT). This is a summary of Claude's points as relayed by the user, not a verbatim transcript.

> **Note:** Claude read only `RESULTS_E1.md` and `v6/e1/CALIBRATION_REPORT.md` and **recomputed nothing** from the data.

- **The gate failure is a capability failure.** Claude takes responsibility for the per-model 0.90 bar, which came from its round-3 proposal.
- **Fixes:** run a capability smoke test before calibration. Gate on rule comprehension (small-choice questions), not on arithmetic. Add a manipulation check that planted entries change a strong model's behaviour. Use a pair of ≥7B models from two different families.
- **Qwen:** tied with prose, but non-inferiority is not established.
- **Smol's win is a floor effect** and should not be counted (by the prose ≥0.90 logic). Report results per family.
- **id_raw and placebo at ~0.01** support the delegate design: the bare ID carries nothing without the expansion.
- **Without caching, expansion costs more** (Qwen: 194 vs 139 prompt tokens, 2.86 vs 2.35 s).
- **The cache figure is a best case.** Test a cached definition prefix shared across different cases, with prose given an equivalent cached prefix.
- **The effective n is 24 message groups.** Use ≥100 entries.
- **Unknown-ID is a safety finding:** Smol acts on 42/48 unknown IDs. Verify the entry version and hash in code.
- **Make sender ID selection a separate experiment.**
- **Fix FLOPs** so that only newly processed tokens are counted.
- **Priorities:** (1) a capability precondition plus a 7B pair; (2) rule probes plus a manipulation check; (3) a real prefix cache; (4) per-family reporting with ≥100 entries; (5) sender selection.
