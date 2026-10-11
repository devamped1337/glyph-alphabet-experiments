# E1b PREREG: DRAFT (not frozen, nothing run)

**Status: DRAFT, 2026-10-12 (AEDT).** Not frozen and not tagged. No E1b code has been written and nothing has been run. It is written **after** the E1 results were seen (`RESULTS_E1.md`, `v6/e1/CALIBRATION_REPORT.md`) and responds to them. Numbers marked **[OPEN]** are proposals that need sign-off. Freezing requires resolving every [OPEN] item, a git tag `prereg-e1b`, and a dated entry in `v6/PREREG_v6.md`.

**Purpose.** This is a credible proof of concept that can attract interest and donated compute. It is not a definitive paper. The user has **no API budget**. Structure (agreed by Claude and GPT): **Stage A** (box CPU, small models, diagnostic only) → **Stage B0 → B1 → B2 → B3** (Kaggle GPU, a 7B pair).

**Limit stated up front:** every model here is open-weight. The closed-lab / public-API repository claim (delegates of closed models agreeing on a dictionary) is **untested** by this design.

Sources: GPT = `v6/e1/reviews/gpt_1.md`, `gpt_2.md`; Claude = `claude_2.md`; Grok = `grok_1–3.md`. Numbers in brackets refer to the "next run must" list in `RESULTS_E1.md`.

---

## 0. Global rules (all stages)

- **The 0.90 gate bar is NOT lowered.** What the gate *measures* changes instead: rule comprehension (small-choice probes) instead of arithmetic answers (Claude [3]; GPT; supersedes Grok 2's lower-bar suggestion).
- **The evaluation generator and seeds are frozen** at tag time (generator code hash + seed list recorded in the config). The disjoint case pools are **smoke/diagnostic**, **qualification**, **calibration** and **TEST**. Diagnostic and qualification cases never enter TEST.
- **Disjoint and unique cases are enforced in code (GPT [6]):** the builder asserts that no normalised case text is shared between any two pools (checked by text and by (entry, text)), that there are no duplicates within a pool, and that every gold answer matches an independent recomputation from the parsed entry text. The build aborts on any violation.
- **Unknown-ID (Claude [11]):** messages carry `ID@version#hash8`. The delegate code checks existence, version and hash before any model call. On any mismatch it returns `UNKNOWN` deterministically with no model call. Tested in every stage with 48 unknown, stale or wrong-hash messages; pass = 48/48. The raw-model behaviour without the check is a labelled diagnostic (E1: Smol acted on 42/48).
- **FLOPs = 2·params·(newly processed prompt tokens + generated tokens).** Cached prefix tokens count 0 (Claude [9]; GPT). Uncached cost is always shown alongside.
- **Per-family reporting is mandatory** (Claude [10]; GPT per-task table). Any pooled number sits next to its per-family table.
- **Prompt format:** no trailing `Answer:` in the user turn and no 3-line cap. The system asks for brief working plus a final `Answer: <int>|UNKNOWN` line, `max_new_tokens` = 192 [OPEN]. (Grok 2; E1 calibration report.)
- **The validator (`v6/checks/validate_v6.py --e1b`)** is an engineering check only. It re-checks disjointness, uniqueness and gold; per-condition row counts; cache-consistency pairs and the reported change/flip rates; FLOPs from newly processed tokens; the 48/48 unknown-ID result; and the MANIFEST sha256s. A non-zero exit means nothing is published.
- **Single entrypoint per stage:** `bash v6/e1b/run.sh <A|B0|B1|B2|B3>` → `python v6/e1b/e1b.py --stage ...`, resumable via `.done` checkpoints. It logs the commit, config sha256, model sha256 / HF revision, llama.cpp / transformers versions, and the hardware. Artifacts go to `v6/e1b/results/<stage>/` with a `MANIFEST.json`.

## Stage A: small models on the box CPU (diagnostic only, NO repository claims)

**Pre-registered: Stage A makes no claim about the repository, the ID channel or efficiency. It is a smoke and diagnostic stage.** Results are reported as diagnostics.

- **Models:** Qwen2.5-3B-Instruct Q4_K_M (E1 file) + SmolLM2-1.7B-Instruct Q4_K_M (E1 file). Optional: Llama-3.2-3B-Instruct Q4_K_M as a second-family alternative to the floor-level Smol [OPEN]. Qwen-3B is the strongest reference model available on the box.
- **Hardware / runtime:** 8 threads, ~15 GB RAM, one model loaded at a time (~2–2.3 GB each). E1 measured rates: Qwen 2.25 s/call (main mean), Smol 1.31 s/call. **Budget ≤6 h wall-clock** [OPEN]. Stop and report if it is exceeded; do not shrink the stage.
- **Tasks:** F1 negation, F2 roles, F3s = **shortened** F3 (≤60 words, no filler; Grok 2). 6 entries per family (18) plus 6 planted [OPEN]. This is a diagnostic, so ≥100 entries is not attempted here.

| A-step | Content | Calls (≈) |
|---|---|---|
| A1 capability precondition (Claude [1]) | 10 diagnostic cases × 18 entries × 2 models, direct text | 360 |
| A2 rule-comprehension probes (Claude [3]) | 8 four-option probes × 24 entries × 2 models; report accuracy vs the 0.90 bar and inter-model agreement | 384 |
| A3 prompt fix as a tested change (GPT: "hypothesis") | the A1 cases re-run with the E1 trailing `Answer:`; paired change in accuracy and in the rate of missing Answer lines | 360 |
| A4 manipulation check (Claude [4]) | 6 planted × 10 cases on Qwen-3B; does the answer follow the planted text? Ignored plants are kept as a stress test (Grok 1) | 60 |
| A5 cache determinism, item by item (GPT [7]) | 120 prompts × {cold, cold, warm, warm} × 2 models | 960 |
| A6 real prefix cache (Claude [8]) | per entry, cache `system + expansion` once, then 10 *different* cases; prose gets an equivalent cached message prefix; both vs cold | 720 |
| **Total** | | **≈2,850 calls ≈ 1.6–2 h** |

**A1 precondition:** a model "has" a family if direct-text accuracy is ≥0.70 [OPEN] on it. This only determines what Stage A reports per family. It is not a repository gate.

**A5 cache-determinism rule (pre-registered, item by item):** for each prompt, compare predictions and correctness between runs.
- **Noise floor = the cold/cold change rate** (two fresh-context runs of the same prompt).
- A cache **passes** only if the **cold/warm change rate ≤ the cold/cold change rate** (upper CI of the difference ≤ 0 [OPEN: or within +1 pp]). Warm/warm is also reported.
- Report **changed predictions** and **correctness flips** per model, per family, next to the **E1 baseline** (cold id_expanded vs repeat-cached, identical prompts, greedy; re-verified 2026-10-12 from `v6/e1/results/predictions_main_*.jsonl`): **Qwen 45/480 changed, 21 flipped; Smol 104/480 changed, 33 flipped**; 0/480 prompt differences.
- **Efficiency work (A6, and all of B's cost numbers) is gated on A5.** If the cache fails, A6 latency/FLOPs are reported as "cache inconsistent, not interpretable", and B uses cold runs only for any accuracy claim.

**Stage A exit / go rule:**
- If the small pair clears **0.90** on the rule probes (each model and agreement, on ≥75% [OPEN] of honest entries) and A4 shows the planted entries changing Qwen's behaviour, the small pair **may be calibrated** in a separately pre-registered amendment.
- **Otherwise (expected): go to Stage B (7B).** Either way, Stage A artifacts and diagnostics are published as they are.

## Stage B: 7B pair on Kaggle GPU

Common rules: frozen generator and seeds; disjoint pools; checkpoints after each sub-stage; **each sub-stage has a fixed GPU-hour budget [OPEN]. If a budget runs out: STOP and report, never shrink N or drop conditions.** bf16/fp32 forward (avoids the v5k OLMo fp16 overflow). Every result is per family.

### B0: qualification of a 7B pair from two labs
- **Primary pair:** Qwen2.5-7B-Instruct + **Llama-3.1-8B-Instruct**. **Named substitute sequence** for the second model, used in this order if one fails: OLMo-2-1124-7B-Instruct → Mistral-7B-Instruct-v0.3 → Gemma-2-9B-it [OPEN].
- **Qualification on its own data** (the qualification pool, disjoint from calibration and TEST): rule probes ≥0.90 and direct-text task accuracy ≥0.80 [OPEN] per family. The first two qualifying models from **different labs** form the pair. Substitutions are logged.
- Budget: 2 GPU-h [OPEN]. If no pair qualifies: stop and report "no qualifying 7B pair".

### B1: gate calibration (≥100 entries)
- **≥100 honest entries** (≈34 per family, F1/F2/F3 with the long F3 restored [OPEN]) + 36 planted (calibration corruption types). TEST-gate cases use **unseen** corruption types (E1 list).
- **Gate:** an entry passes iff each model scores ≥**0.90** on its rule probes and inter-model agreement is ≥0.90. Separation requirement: honest acceptance ≥0.80 and planted rejection ≥0.90 [OPEN]. A manipulation check on the stronger model accompanies it.
- Budget: 4 GPU-h [OPEN].
- **If B1 fails: B2 and B3 still run**, but the combined pipeline **may not be called a checked repository**. Report gate acceptance, coverage and abstentions alongside every B2/B3 number.

### B2: oracle-ID receiver comparison
- The receiver gets the correct ID and expands it locally (hash-checked). Conditions: **id_oracle** vs the **matched direct_text** (exact expansion text and framing; GPT [5]) vs prose, id_raw and placebo. Plus prefix-cached variants for id and prose, valid only if the A5-style determinism rule passes on the 7B models.
- **Primary:** id_oracle vs direct_text, non-inferiority margin **±0.05**, paired cluster bootstrap over entries (2000 resamples). Inconclusive is reported separately from equivalent.
- **Power:** E1's half-width was ≈0.077 at 24 groups. At ≥100 entries it scales to ≈±0.038 pooled and ≈±0.065 per family. Pooled ±0.05 is attainable; per-family is reported as descriptive [OPEN: N per entry 10].
- Held-out TEST cases only. Coverage-only results are reported only if B1 passed.
- Budget: 6 GPU-h [OPEN].

### B3: sender selection (its own experiment; GPT, Claude [12])
- The sender reads a natural-language message (never the entry text) and picks one ID from **4 confusable neighbours** (same family and wording, differing in polarity / role direction / threshold). Two variants: short labels (primary) and full definitions (ceiling). Both models act as sender.
- **Metrics:** selection accuracy (chance 0.25) per family. Then **id_selected** end-to-end (the chosen ID → receiver) vs direct_text, and selection-error decomposition (id_selected − id_oracle).
- Budget: 3 GPU-h [OPEN].

## Stop rules (summary)
1. Disjointness/uniqueness/gold assertion fails → abort the build.
2. Validator fails at a checkpoint → stop that stage and report.
3. GPU-hour budget exhausted → stop and report (no shrinking).
4. B0 finds no qualifying pair → stop Stage B and report.
5. No interim looks at the primary B2 comparison.

## What donated GPU time would test
The budgets for B0–B3 [OPEN, ≈15 GPU-h total, T4/P100 class]. Beyond them: the **contextual glyph arm** (vector delivery at a contextual layer and a J-lens basis vs the embedding channel; unresolved in v5), larger N for per-family ±0.05, and a second 7B pair for replication.

## Open choices
- All [OPEN] numbers: max tokens, the A1 0.70, the A5 tolerance, entry counts, B0 qualification thresholds, B1 separation thresholds, GPU-hour budgets, N per entry.
- Llama-3.2-3B in Stage A (Smol is at floor) vs only the E1 pair.
- The second 7B model and the substitute order.
- Whether the long F3 returns in B1 (the draft says yes; F3s in Stage A).
- The code (`e1b.py`, `run.sh`, the validator `--e1b`) is specified, not written. That is the next step after sign-off.
