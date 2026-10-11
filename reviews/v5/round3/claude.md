# Claude feedback on PREREG_v6_DRAFT, round 3 (relayed by the user; summary, not verbatim)

**Corrections to its own round 2:** "authorized" is not a collision. The gate rule was underspecified, not "not met".

**Four points:**
1. **Depths:** two depths, with one primary claim (~40%). 60% is secondary and cannot rescue the primary.
   - Depths are qualified by a neutral calibration probe that separates negated pairs (≥0.95).
   - Freeze the shallowest qualifying depth and the depth +20 points deeper. Never use glyph accuracy to choose.
   - Run nulls at the primary depth only.
2. **J-lens:** pre-register the feasibility criteria (memory/time budget, reference implementation support).
   - If it is omitted, make no J-space claim and call it the "contextual channel".
   - Run it in E3 at the primary depth only.
3. **LOO:**
   - Baselines: zero and mean-of-slot ablations plus a copy baseline; compare against the best of the three.
   - Forced choice over entities not named in the message.
   - Success: the lower 95% bound of (held-out minus best baseline) ≥ +0.10 on ≥2 of 3 task families.
4. **Gate:**
   - Calibrate the threshold on honest and planted entries, targeting ≥0.90 sensitivity and ≥0.80 specificity.
   - Per entry: N=40 fresh cases, each model ≥0.90 vs gold, and ≥0.90 agreement.
   - TEST corruption types must be unseen in calibration, including near-miss pairs.
   - If nothing separates, don't freeze; report it.

**Other changes:**
- LOO must use the unsnapped contextual readout.
- Demote E2 to a control inside E3.
- Run E1 first (API-based, cross-lab, takes days).
- Power analysis: n ≈ 1540 × discordance (about 150 items at 10%, 300 at 20%), with item counts stated per task.
- Efficiency accounting: amortized dictionary cost, break-even count, and sender compute (~170 ms).
- A placebo prose baseline with the answer token removed.
- Stop rule: "equal" means within a non-inferiority margin, plus a minimum saving such as 30% fewer receiver tokens.

**Freeze now:** structure, the LOO channel and baselines, the gate calibration procedure, statistics, the stop rule.
**Defer:** exact depths (until the probe), J-lens (until feasibility).
