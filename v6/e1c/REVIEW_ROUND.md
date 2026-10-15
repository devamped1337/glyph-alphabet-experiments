# E1c REVIEW_ROUND r1 (draft pre-registration), pinned commit f9c5c54

## Ask
Review the E1c **DRAFT** pre-registration and its implementation before the dev pilot (D1) is run. Verdict: ACCEPT (D1 may be proposed to Stefan for a go), or CHANGE (list required edits). Flag anything that would make the TEST result uninterpretable.

## Context
- E1b A9: POC FAILED. The A10 B3r secondary was INCONCLUSIVE (−0.0625, CI [−0.133, −0.004]). Selection was the bottleneck (56/60 picks correct; 36 of 37 errors came from wrong picks).
- GPT's E1c memo (`v6/e1b/reviews/gpt_E1c_design.md`) recommended:
  - a verified-ID hybrid with prose fallback;
  - a stateless verifier with deterministic matching;
  - 240 entries per direction, with both directions required;
  - coverage ≥ 85%, byte saving ≥ 30%, break-even within 1,000 messages;
  - a stratified, clustered bootstrap.
- Stefan and Grok approved drafting with these terms:
  - one fresh run;
  - the A10 parser, with "B) F1" as a test;
  - a dev pilot this week (≤ 0.5 GPU-h; the wrong-pick-accepted rate must be ≤ about 2%);
  - TEST next week, sized from dev;
  - `E1C_GO` plus Stefan's go for each stage, and one start plus one infrastructure retry;
  - Qwen2.5-7B and Falcon3-7B only, on the free T4.

## Artifacts (at f9c5c54)
- `v6/e1c/PREREG_E1c.md`: the full draft.
- `v6/e1c/config_e1c.json`: seeds (dev and TEST disjoint), sizes, criteria, caps, max_starts=2.
- `v6/e1c/e1c/book.py`:
  - dev and TEST books; TEST refuses to build before freeze;
  - freshness checks against the E1b frozen book, the A9 book and the dev book;
  - 2n build with distinct-rule core selection.
- `v6/e1c/e1c/verifier.py`: prose-only verifier prompt, strict parser, deterministic match against the picked entry.
- `v6/e1c/e1c/analysis.py`:
  - per-entry paired differences;
  - family-stratified entry bootstrap (2,000 resamples);
  - A1.2 label;
  - coverage, byte saving and break-even.
- `v6/e1c/e1c/stages.py`:
  - gates (go, frozen, code hash, starts, terminal markers, caps);
  - sender, verifier and receiver steps, with fallback identity reuse;
  - D1 summary and the sizing rule.
- `v6/e1c/tests/test_e1c.py`: 14 tests OK.
  - archived "B) F1" replies parse under A10;
  - the dev book is pinned, fresh and unique;
  - the verifier rejects every neighbour;
  - bootstrap and label checks;
  - fake-backend D1 dry run, including fallback identity reuse, the go, frozen and code-hash gates, and the start cap.
- E1b suite: 112 tests OK (unchanged).
- Kernel `e1c_D1`: prepared, **not pushed** (E1C_COMMIT=SET_ME).

## Scope
In scope:
- endpoint and criteria definitions;
- the verifier design and its independence limits;
- the fallback and byte accounting;
- the bootstrap;
- the dev-to-TEST firewall and sizing rule;
- gates and caps;
- the disclosed deviations: neighbour-text reuse, the 2n distinct-core build, deterministic batch order rather than random, and shuffled rather than exactly balanced candidate positions.

Out of scope: E1b conclusions (unchanged), model choice (fixed), and posting.

## Output
Verdict (ACCEPT / CHANGE). Then a numbered list of required changes, each marked [blocking] or [non-blocking]. Then optional suggestions. Plain text.
