# GPT review of the E1c T1 freeze, round 1 (REVIEW_ROUND T1-freeze r1, pinned aabad44), via Codex

Verdict: CHANGE.

1. The two commits satisfy the supplied §9 commit requirements: registration freezes the configuration and cap without a TEST book or digest; execution changes only allowed files and permitted config values. JSON whitespace changes are harmless. The supplied checker verifies ancestry and matching book digests. Its expected missing-path stderr is cosmetic.

However, the overall freeze procedure does not follow §9 exactly: the fake-backend T1 dry run processed the TEST book beyond the expressly permitted construction, integrity and freshness checks.

2. The 5.0 GPU-h cap is soundly derived. The supplied precise timings give 2.9295 h raw and 3.6619 h with 25% margin. The cap adds approximately 36.5% above that projection. The stated stress calculation also checks out: approximately 3.71 h raw and 4.63 h with margin. That is sensible for this bounded run, though it remains a projection dependent on the disclosed coverage and prompt-length assumptions. No extra GPU pilot is needed.

3. The supplied builder and log support mechanical use of the seed rule: 93062 → 93162 → 93262 → 93362, stopping at the first successful build. Nothing supplied indicates human inspection or model exposure; those remain attestations rather than facts independently established by the log.

The dry run is nevertheless outside the explicit access restriction. “No person or model looked” does not make arbitrary automated TEST processing permissible under the quoted wording. This is a procedural deviation, not evidence of seed selection or outcome-driven tuning.

4. Before T1, resolve and document that deviation, then complete the already planned launch prerequisites. Additional performance experiments, a rebuilt TEST book, or an expanded audit system would be over-engineering.

Complete list of remaining required changes and prerequisites:

- [blocking] [proportionate] Record the TEST dry run as a deviation in a separate reviewable note: identify what consumed the book, what aggregate outputs were observed, and whether any implementation, configuration or launch decision changed because of it. Obtain explicit acceptance of that deviation before proceeding. Preserve both frozen tags and the existing TEST book; deleting scratch results does not erase the deviation.
- [blocking] [proportionate] Before kernel push, replace SET_ME with the full commit SHA corresponding to aabad44 and verify it resolves to e1c-t1-exec. This is an ordinary launch prerequisite, not a defect in a deliberately guarded prepared kernel.
- [blocking] [proportionate] Obtain Stefan’s explicit T1 go before pushing the kernel, and satisfy the registered quota-reset timing and available-budget condition.
- [non-blocking] [proportionate] Include the successful check_freeze command and output in the T1 report, as §9 requires. This can be completed with the report; it does not require changing either frozen tag.
- [non-blocking] [proportionate] The PREREG title and config label still say DRAFT. Clarify this cosmetic inconsistency in accompanying documentation; do not move the registration tag to tidy it.

No additional required changes. Suppressing the checker’s expected stderr, further dry runs, or more elaborate safeguards would be [non-blocking] [over-engineering] for this run.

May the tags be pushed and T1 proposed to Stefan: no, pending explicit acceptance of the documented dry-run deviation.
