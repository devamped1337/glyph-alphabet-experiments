# E1e CPU mechanics — fixture-tested mechanics draft — no corpus measurement or savings claim

What this is: a stdlib-only Python implementation of `SPEC_E1E_REPO_1.md` (package `e1e/`) plus unittest suites in
`tests/`. It follows `reviews/gpt_E1e_pilot_r1.md` §4 and the §3 corrections (delta duplicate IDs rejected, delta bound
to base full digest and checked against target digest, version progression and ID/version immutability, template
schema inside the entry digest).

What this is not: no real or private messages (none are approved; fixtures in `tests/fixtures.py` are synthetic),
no corpus, no compression baselines (zstd deliberately not used yet), no byte-saving numbers. With 64-hex digests
in every reference, refs are often *larger* than the raw envelope for these short fixtures; that is expected and is
not a measurement.

Run (CPU only, no dependencies): `cd v6/e1e && python3 -m unittest discover -s tests -t . -v`

Layout: `e1e/canon.py` (escaped canonical JSON, strict parse), `e1e/schema.py` (entries, templates, matching),
`e1e/repo.py` (state, full/delta, transactional ops, publisher/receiver), `e1e/codec.py` (encode/verify/decode,
fallback, link accounting). Tests: `tests/test_roundtrip.py` (successful-path evidence) and
`tests/test_rejections.py` (rejection boundaries, each asserting unchanged state). Results are reported separately.
