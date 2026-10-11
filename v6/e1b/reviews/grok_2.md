# Review grok_2: E1b PREREG DRAFT rev 3 (`1550275`) (summary relayed by the user)

Relayed 2026-10-12 (AEDT). This is a summary of Grok's points as relayed by the user, not a verbatim transcript.

**Grok accepts all nine rev-3 [CONFLICT] resolutions as written**, with these tightenings:
- Lock the TEST-pass bar at ≥0.80 honest acceptance / ≥0.90 planted rejection.
- No raising N after seeing any numbers.
- The reserve never extends N or adds conditions.
- Keep the fail-loud guard.

**Four hard locks for rev 4:**
1. Close the remaining [OPEN] numbers: the planted count for the 60-entry core (proposed 24), the A5 set size (~100 fixed + 20 hard per model), the TEST-pass bar 0.80/0.90, and F3L at 10 entries.
2. State the expected CI width (~±0.049) and the ~50% power at zero difference in the success-criteria section.
3. Confirm that B2/B3 use only held-out TEST cases that are disjoint from Stage A, qualification and B1, asserted in code.
4. Keep the sentence: if B1 fails, B2/B3 still run, but the combined pipeline is not a checked repository, and gate acceptance, coverage and abstentions are reported with every number.
