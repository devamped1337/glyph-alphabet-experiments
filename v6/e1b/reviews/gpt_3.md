# Review gpt_3: E1b PREREG DRAFT rev 5 (`eaead82`) (summary relayed by the user)

Relayed 2026-10-12 (AEDT). This is a summary of GPT's points as relayed by the user, not a verbatim transcript. GPT backs the rev-5 approach, with five clarifications:

1. **Runtime projection:** use the measured elapsed time per representative call or batch (sender plus receiver), plus setup time, not a single tokens/s figure. Choose C100 only if every stage fits with headroom. Check C60 too, and if C60 doesn't fit either, report "insufficient budget".
2. **Mutually exclusive accuracy labels:**
   - CI lower bound > −0.05 → **non-inferior**;
   - CI upper bound < −0.05 → **inferior**;
   - otherwise → **inconclusive**.

   Report a missed byte target separately. The power table is per comparison; note the joint figure separately.
3. **Gate and denominators:** the accepted dictionary list is fixed from calibration, and the TEST-gate results only evaluate it. Keep all scheduled core TEST cases in the headline denominator, with rejected entries and abstentions visible. Make any family exclusion prominent.
4. **Cache:**
   - a batch-1 pass supports batch-1 cached measurements only;
   - require zero changes in cold/cold, warm/warm **and** cold/warm;
   - define the cold/warm pairing;
   - the binomial bound covers the sampled units only, not the hand-chosen near-ties.
5. **Parsing and the leak flag:**
   - freeze the handling of invalid letters, multiple answers, missing lines and abstentions, with invalid counted as wrong;
   - for the >0.40 leak flag, name the diagnostic pool and a predetermined regeneration procedure;
   - no regenerating B1 probes after seeing performance.

**Plus:** distinguish payload bytes from whole-exchange bytes.
