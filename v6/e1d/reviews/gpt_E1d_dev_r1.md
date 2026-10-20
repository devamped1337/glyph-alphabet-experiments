# GPT review of D1-E1d dev results (d8688b4), 2026-10-20

**Verdict: proceed to TEST freeze prep.** D1–D8 pass under the plan at `prereg-e1d`; outcome rule 1 applies: **dev-new qualified**. This is not TEST launch approval. Nothing was changed or launched.

I reviewed results at `d8688b4` and independently checked the raw selection/exchange assignments, correctness against registered gold, serialized message bytes, and timing arithmetic.

| Check | Re-derived result | Verdict |
|---|---|---|
| D1 | `.done`, one recorded `done`, rc 0, no terminal markers; 2,245.7235 s = 0.623812 h | Pass |
| D2 | Each sender: exactly 160 old + 12 new selections. Each direction: exactly 176 exchange rows—40 old + 48 new cases, each in both arms; no missing/duplicate assignments | Pass |
| D3 | Stage-log conformance records: 16/16 identical for each model | Pass¹ |
| D4 | Recomputed protocol hash equals recorded dev hash: `11d7af03…e8777a2` | Pass |
| D5 | Sender/verifier 2.601880 s/entry; receiver 5.738877 s/message; maximum load including canaries 268.074206 s → **2.974405 h**, including 25% margin | Pass |
| D6 | All ten individual trial records report successful builds; adopted roles match | Pass |
| D7 | Every pair and sender: verifier format 4/4, valid pick 4/4, prose receiver parse 16/16 | Pass |
| D8 | Counts below; all pair and pooled thresholds satisfied | Pass |

¹ D3 is supported by [stage_log.jsonl:6](/workspace/glyph-repo/v6/e1d/results/D1-E1d/stage_log.jsonl:6) and [:10](/workspace/glyph-repo/v6/e1d/results/D1-E1d/stage_log.jsonl:10). The comparison code checks exact output equality, but does not persist the paired outputs. Independent reconstruction of those comparisons is therefore unavailable.

D8 counts, shown as **prose / hybrid correct**:

| New pair | Qwen → Falcon | Falcon → Qwen |
|---|---:|---:|
| baker/porter | 16 / 16 | 14 / 16 |
| potter/bearer | 16 / 16 | 16 / 16 |
| tanner/loader | 15 / 16 | 14 / 16 |
| Pooled | **47 / 48** | **44 / 48** |

**Discrepancies:** I found no numerical discrepancy between the report and raw rows. Selection counts also reproduce the report: Qwen correct/accepted = 147/146 old and 9/9 new; Falcon = 156/152 old and 12/12 new. Wrong picks accepted are **zero across all 344 selections**.

The apparent artifact disagreement is correctly disclosed: [summary.json:1087](/workspace/glyph-repo/v6/e1d/results/D1-E1d/summary.json:1087) has D1 unknown and [:1251](/workspace/glyph-repo/v6/e1d/results/D1-E1d/summary.json:1251) has eligibility false. Those are child-time values, not a failed completed-stage check. Running the post-run checker read-only returned `eligible_for_freeze: true`, matching `eligibility.json` and [report:38](/workspace/glyph-repo/v6/e1d/D1_E1d_REPORT.md:38).

**Adding `check_eligibility.py` after the run is acceptable as disclosed.** The execution-path diff contains only that added wrapper; it invokes the existing eligibility implementation and supplies completed supervisor state. It changes neither observations nor thresholds. Preserve the original execution hash and results. The current code digest is `889662dd…23f06dd`, versus the recorded/pinned `fa8d8b80…3993c0`; re-pin the final reviewed TEST code rather than rewriting dev provenance. D4 checks protocol identity, so this code-hash mismatch does not itself invalidate D4.

**The Qwen weakness triggers no remedy under the frozen plan.** I reproduce 9/12 ID use, including 2/4 potter/bearer, and illustrative dev-new lifetime lower bound **0.182529**. D7 requires parseable picks, not correct or accepted picks; D8 passes. Thus no pair replacement, extra qualification run, or gate adjustment is called for. Retain the warning and let unchanged TEST G2/G3 evaluate it.

Before TEST freeze:

- Complete and review TEST execution support and E1d freeze-integrity tooling. The current child explicitly implements dev only ([stages.py:95](/workspace/glyph-repo/v6/e1d/e1d/stages.py:95)); re-pinning alone is insufficient.
- Confirm the 4.0 h cap, retain the frozen roles, gates, workload and seeds, and verify final TEST protocol hash still matches dev.
- Pin the complete reviewed code and record its relationship to `f092214`. Correct the stale advertised `--eligibility` option ([run_e1d.py:1](/workspace/glyph-repo/v6/e1d/run_e1d.py:1)) and the previously noted stress-margin wording.
- Freeze before generating TEST. Subsequently build using the frozen seed procedure and strict exclusions, pin the TEST book and measured v1 artifact, and verify freeze-to-execution integrity.
- Obtain Stefan’s explicit go before launch.

Files opened/read, directly or through the read-only validation:

- Frozen `DRAFT_PLAN.md` at `prereg-e1d`; report and prior GPT code review.
- `summary.json`, `eligibility.json`, both selection files, both exchange files, both prompt files (searched), `stage_log.jsonl`, `kaggle_log.json`, `loads_attempt1.json`, `e1d_state.json`, `.done`, `CHILD_COMPLETE`, `dict_v1.e1d`, and budget ledger.
- `run_e1d.py`; all seven `e1d/*.py` modules; `config_e1d.json`, `w_e1d.json`, `CODE_HASH.txt`.
- `tools/check_eligibility.py`, `tools/code_hash.py`, artifact serializer/loader, builder-trial tooling and `measurements/builder_trials.json`.
- Pinned dev-new and prerequisite old books/base configuration through `load_dev`; reused E1c stage functions and E1c freeze checker.
