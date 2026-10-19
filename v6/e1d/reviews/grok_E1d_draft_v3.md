# Grok review of E1d DRAFT_PLAN v3 (commit da0fe97) and GPT r4 (commit 3ddb067), relayed by Stefan on 2026-10-19

Verbatim as relayed. Grok's review of `v6/e1d/DRAFT_PLAN.md` v3 at `da0fe97`, together with GPT's round-4 review at `3ddb067`.

---
Draft v3 is a clear improvement. Shared-repository framing matches the original idea. Wrong-ID gate correctly demoted to report. Checker stays sender-side so rejected IDs cost 0 network bytes. Serializer and framing frozen. Artifact measurement is now the object actually shipped. Those were the previous high-severity holes.

GPT's remaining issues (all medium or low) are real and should be closed before freeze:

1. F2 feasibility simulation is approximate. The counting script does not run the real builder's neighbour rejection rules or the planned "four cores per new pair" allocation. Label current numbers as approximate and make the ten actual builder trials the authoritative check.

2. Dev qualification criteria are not defined. "Run the new vocabulary through both models" does not say what result allows freeze. Specify the exact eligibility table, which E1c screens survive, what happens on failure, and what data A1 uses for its lifetime-cost selection.

3. Participant/traffic accounting still has two readings. The formula accumulates participants 20→26 while traffic stays fixed at 180k. State explicitly whether aggregate traffic is held constant despite joins, and define delta recipients as those present immediately before the update.

4. (Low) Byte-precision figures are a bit optimistic; commit the sizing calculation. Per-pair reporting should break out each new role pair rather than only pooling new vs old.

None of these change the design. They make the pre-registration precise enough that the result cannot be argued after the fact.

Fold both reviews and send the next version when ready. Nothing runs without Stefan's go.
---
