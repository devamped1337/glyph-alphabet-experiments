# GPT (Codex CLI, read-only) re-check r4 of E1e byte-audit plan draft

Reviewed checkout: commit e9f26f0. Date: 2026-10-21 (AEDT). Verbatim response below. All reported adversarial inputs were fixed in the following commit (rest-of-line credential redaction, URL-before-email ordering, quoted-local emails, Windows paths, any-length Bearer/Basic and @handles, case-insensitive self name), each with a regression test in tests/test_sanitiser.py; corpus rebuilt.

At `e9f26f0`, these adversarial inputs reproducibly leak content and pass `scan(sanitise(input))`:

- **Credential parsing:** `password=alpha\ beta` → `password=<SECRET> beta`; `{"password":["alpha","bravo"]}` retains both secrets. Double-encoded JSON made with `json.dumps(json.dumps({"password": 'alpha "bravo" charlie'}))` leaks `bravo` and `charlie`. Sanitiser and scan share the faulty value parser ([line 66](/workspace/e1e-gpt/v6/e1e/tools/build_glyph_own_dev.py:66)).
- **URL processing:** `ssh://git@host.example/alice/private.txt` → `<URL>>/alice/private.txt`. Email replacement breaks URL matching, exposing its path ([line 42](/workspace/e1e-gpt/v6/e1e/tools/build_glyph_own_dev.py:42)).
- **Quoted email:** `"alice smith"@host.example` → `"alice smith"<HANDLE>`, retaining the identifying local part.
- **Windows paths:** `C:\Users\alice\private.txt` survives unchanged; the scan incorrectly expects doubled backslashes ([line 123](/workspace/e1e-gpt/v6/e1e/tools/build_glyph_own_dev.py:123)).
- **Token/identity formats:** `Bearer abc`, `@q`, `@property.owner`, and `GLYPH` each survive unchanged and pass.

All 40 tests pass; all pinned hashes match. Scanning all 188 corpus records found no confirmed sensitive disclosure. Declaration accounting checks pass.

**Verdict: needs fixes before Grok review toward a freeze.**
