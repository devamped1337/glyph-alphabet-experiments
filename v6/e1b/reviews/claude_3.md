# Review claude_3: E1b PREREG DRAFT rev 5 (`eaead82`) (summary relayed by the user)

Relayed 2026-10-12 (AEDT). This is a summary of Claude's points as relayed by the user, not a verbatim transcript. **Claude read `eaead82` directly** (no stale fetch).

Fixes requested:
- **(a)** State the TEST-gate pool size and the CI lower bound (~0.84 at ~40 planted for a 0.95 point estimate).
- **(b)** Cached timing is batch-1 only; say so in the cost table.
- **(c)** The leak flag is per probe template, pooled across entries, with ≥50 no-text observations per template.
- **(d)** Byte-identity: a sha256 assertion per item, on 20 items.
- **(e)** §10 should state the joint power for both receiver directions (bounds: C100 ~0.55–0.74, C60 ~0.27–0.52).
- **(f)** State up front that the −0.05 margin implies a selection accuracy of about ≥0.95, so a fail likely reflects selection. Assert in the builder that each wrong neighbour changes the gold answer on ≥80% of TEST cases.
- **(g)** Define the message: the case text reaches both arms identically. Name the exact byte denominators (total receiver bytes per arm). Slots are future work. Note that the byte saving is near-guaranteed by design.
- **(h)** B2's primary is zero by construction, given byte identity. Its content is the prose comparison and the cost table.
- **(i)** B0 includes a 4-bit load test on the assigned GPU, with a pre-registered fallback (GGUF via llama.cpp CUDA) for P100.
- **(j)** Add a lexical TF-IDF/BM25 label baseline beside MiniLM.
