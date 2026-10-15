# GPT review of E1c Amendment A1, round 1 (REVIEW_ROUND A1 r1, pinned c9bf063), via Codex

Verdict: CHANGE.

1. The 0.8 GPU-h cap is reasonable for this pilot. The listed segments total 1,980 s; 2,880 s provides 900 s (45.5%) headroom. The stress-case arithmetic needs correction: replacing 310 + 290 + 310 s of loads with 3 × 420 s adds 350 s, not 330 s. Adding 25% to the 1,040 s of generation gives 2,590 s, leaving 290 s. This supports the cap, while the unmeasured Qwen receiver remains an explicitly disclosed estimate.

2. Yes. Keeping the established three-load order is proportionate. Three loads are necessary under the stated execution scheme with one model resident at a time. Testing co-residency would introduce memory and execution uncertainties without being necessary for D2.

3. Yes. Rerunning everything avoids cross-stage provenance and resume rules for a modest additional cost. The descriptive D1–D2 comparison is appropriate and must remain non-gating.

4. Almost, but one substantive regression appears in the diff: t1_eligibility removes the explicit requirement that the qualifying stage have a .done marker. A recorded “done” outcome plus summary is now sufficient. That changes an accepted T1 rule beyond substituting D2 for D1. The PREREG also retains contradictory normative references to D1.

5. Yes. Copying the environment dictionary, relabelling E1b’s hash, and adding the computed E1c hash correctly separates their identities without changing E1b. The supplied test covers the intended behavior.

Complete list of remaining changes:

- [blocking] [proportionate] Restore the explicit .done requirement in t1_eligibility, using the configured qualifying stage directory. Add a regression test where D2 has a valid summary and recorded “done” outcome but lacks .done; eligibility must fail.

- [blocking] [proportionate] Update current normative PREREG references from D1 to D2 wherever they govern T1 eligibility or freeze-time sizing. The pasted T1 table still explicitly requires “D1 eligibility” and sizing “from D1”; an appended amendment note leaves conflicting instructions. Update the stages.py introductory docstring as well. Preserve historical D1 statements.

- [non-blocking] [proportionate] Correct the stress calculation to +350 s for loads and 2,590 s overall. The correction does not undermine the proposed cap.

- [non-blocking] [proportionate] Replace “every segment was measured in D1” with wording that distinguishes directly measured segments from counterpart-based estimates. Also qualify “the only use of D1 … is its timings” to allow the explicitly planned descriptive reproducibility comparison.

No further blockers are evident in the pasted material. Requiring a co-residency experiment, additional GPU timing runs, cross-stage reuse machinery, or a statistically established runtime bound would be [non-blocking] [over-engineering: disclose instead] for this pilot. Tests are reported as passing; I have not independently executed them.

Is D2 ready to propose to Stefan: no.
