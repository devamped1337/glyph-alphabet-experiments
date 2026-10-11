# Code review gpt_code_2: E1b implementation at `b12b0ce` (summary relayed by the user)

Relayed 2026-10-12 (AEDT). This is a summary relayed by the user, not a verbatim transcript.

- All 37 tests passed; the code hash and cross-process reproducibility were verified. **Stage A is approved as diagnostics only.**
- To fix before any GPU work, each with a regression test:
  1. `tests/test_dryrun.py` is out of date. It needs real GGUF files for the hash check, and once that is stubbed it crashes because it writes integer canary refs where per-case dicts are expected. Update the harness, keep the real-run hash and canary checks, and make the full fake-backend dry run pass.
  2. **B0b leak recheck:** replacements were compared against the kind baseline + 15 points, so a replacement with 100% no-text accuracy was kept (the effective threshold was 115%). Apply the same kind-level >40% leak rule during the recheck, and add budget checks inside B0b's inference loop.
  3. **Regex baseline:** report it using B3's actual frozen per-entry candidate shuffle. GPT's numbers: plain 70/70, reordered 0/13, spelled 5/14 (tie-break guesses), derived 8/13.
- **Latency allowances:** with 3 h and 20% headroom, probe latency must stay under ~0.446 s (C60) and ~0.290 s (C100). If neither fits, report insufficient budget.
