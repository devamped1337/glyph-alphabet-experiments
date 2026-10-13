# Claude final sign-off on A8 (2026-10-13)

Yes after 2 wording fixes: (1) resolve the clause overlap. Deterministic access failures (gated, 401, 404, licence) are NOT retried and mean NO_QUALIFYING_PAIR. Load, OOM, non-finite or crash failures before any scored probe get the one fp32 retry. (2) State that the fp32 retry may not fit the absolute cap on a T4 and may end INCOMPLETE (= not qualified); it is not a real second chance.
