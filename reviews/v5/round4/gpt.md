# GPT final check on PREREG_v6_DRAFT rev 3, round 4 (relayed by the user; summary, not verbatim)

1. **Depths:**
   - Candidates are 40/50/60%. Choose the shallowest with ≥95% balanced accuracy on a held-out negation calibration set; the secondary is +20 points.
   - Freeze the procedure first, and call the result "calibration-selected".
2. **E2:** accepts E2 as a control.
3. **LOO:**
   - Run all four baselines.
   - The +0.10 bound must hold on 2 of 3 families, in both directions.
   - Use simultaneous paired bounds for multiple comparisons.
   - Smaller effects are still reported.
4. **Gate:**
   - Calibrate at N=40, then evaluate on separate TEST cases and unseen corruptions.
   - Keep the confirmatory targets of ≥90% acceptance and ≥95% rejection. 80% is reported as a weaker outcome, not a pass.
   - Report counts plus uncertainty.
5. **Efficiency:**
   - Primary: non-inferior within 5 points plus ≥20% lower receiver latency vs a valid cached expansion, with tokens and FLOPs reported.
   - A separate ≥30% token claim, defined as newly processed tokens after the cache.
   - Sender ~170 ms is to be measured. End-to-end timing includes sender and encoding.
6. **Power:** the formula is precision, not power. 80% power for 5 points needs ~300 pairs at 10% discordance and ~600 at 20%, and more with clustering.
7. **J-lens budget:** pilot ≤30 min, peak ≤80% RAM/VRAM, full basis ≤2 h on the target hardware. Otherwise, omit before TEST.
