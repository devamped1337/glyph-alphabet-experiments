# Grok review of E1d DRAFT_PLAN, round 1 (commit ac2bc76), relayed by Stefan on 2026-10-19

Verbatim as relayed. Grok's review of `v6/e1d/DRAFT_PLAN.md` at commit `ac2bc76`.

---
The lifetime/workload criterion is the right direction, but the draft is not yet precise enough to freeze.

Required fixes before next draft:

1. Dictionary cost: measure and freeze the actual minimal distribution artifact the receiver loader accepts (membership + encoding + any required manifest). Do not use the 960-entry subset cost while shipping the 1,960-entry object.

2. Total bytes: freeze one primary byte boundary and one serializer before any run. Explicitly state whether case text, framing, and setup are included. Common bytes cancel in the absolute difference but not the percentage.

3. Checker location: resolve the contradiction. Either keep E1c's sender-side checker and charge zero for rejected IDs, or move the checker and re-qualify that path. Do not claim "unchanged" while changing the cost model.

4. 1% wrong-ID gate: current size cannot support it. Zero errors in 240 picks only bounds ~1.24%. Specify the required number of independent picks per direction and whether the denominator is all picks or accepted wrong IDs only.

5. Workload W: write it as a concrete scenario (or forecast) that includes traffic mix, rule reuse rate, recipient churn, update size/frequency, and version-mismatch fallback behaviour. Counts alone are insufficient.

T1 arithmetic checked out. The issue is specification of the new criterion.

Revise the draft around these points and send the next version for review when ready.
---
