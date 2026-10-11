# E1b PREREG: DRAFT (not frozen, nothing run)

**Status: DRAFT rev 3, 2026-10-12 (AEDT).** Rev 3 applies `reviews/gpt_1.md` (GPT, on rev 1) and `reviews/grok_1.md` (Grok), and marks reviewer conflicts as **[CONFLICT]**. **The "Rev 3 decisions" section below supersedes any text later in this file that disagrees with it.** Rev 2 was `283aaad`. Previously: Rev 2 applies `v6/e1b/reviews/claude_1.md` (Claude; marked "(Claude r1)" below). Rev 1 was `ce7cd5d`. Not frozen and not tagged. No E1b code has been written and nothing has been run. It is written **after** the E1 results were seen (`RESULTS_E1.md`, `v6/e1/CALIBRATION_REPORT.md`) and responds to them. Numbers marked **[OPEN]** are proposals that need sign-off. Freezing requires resolving every [OPEN] item, a git tag `prereg-e1b`, and a dated entry in `v6/PREREG_v6.md`.

**Purpose.** This is a credible proof of concept that can attract interest and donated compute. It is not a definitive paper. The user has **no API budget**. Structure (agreed by Claude and GPT): **Stage A** (box CPU, small models, diagnostic only) → **Stage B0 → B1 → B2 → B3** (Kaggle GPU, a 7B pair).

**Limit stated up front:** every model here is open-weight. The closed-lab / public-API repository claim (delegates of closed models agreeing on a dictionary) is **untested** by this design.

Sources: Claude r1 = `v6/e1b/reviews/claude_1.md`; GPT = `v6/e1/reviews/gpt_1.md`, `gpt_2.md`; Claude = `claude_2.md`; Grok = `grok_1–3.md`. Numbers in brackets refer to the "next run must" list in `RESULTS_E1.md`.


## Rev 3 decisions (supersede the body where they differ)

Reviewers: Claude r1 = `reviews/claude_1.md`, GPT r1 = `reviews/gpt_1.md`, Grok r1 = `reviews/grok_1.md`. The proposed resolutions favour the **affordable proof of concept (GPT)** unless that would break validity. Each [CONFLICT] needs the user's sign-off.

**POC focus (GPT r1):** sender selection plus the full exchange (B3 → receiver) is the headline. Everything else is a precondition or a diagnostic.

### [CONFLICT] 1. Third small model in Stage A
- **GPT:** Qwen-3B + Smol only, no third model.
- **Claude:** add Llama-3.2-3B for A1–A4 and A6, with Smol for A5 only.
- **Grok:** Qwen-3B + Smol, Llama-3.2-3B optional.
- **Proposed:** **Qwen-3B + Smol only** (GPT/Grok). Stage A makes no claims, and Smol being at floor only makes A1–A4 single-model-informative, which is acceptable for a diagnostic. Llama-3.2-3B is added **only if** the measured Stage A projection leaves room within the cap below.

### [CONFLICT] 2. Stage A time cap
- **GPT:** 2 h.
- **Rev 2 (from Claude's n=480 cache test):** 5–6 h.
- **Grok:** no figure.
- **Proposed:** **2 h cap** (GPT), made possible by the smaller cache test (conflict 4). If the projection after A1 exceeds 2 h: stop and report, do not shrink.

### [CONFLICT] 3. Entry count (B1/B2)
- **GPT:** 60 honest entries (30 × F1, 30 × F2) × 10 TEST cases; check runtime on non-TEST cases first.
- **Claude:** ≥100.
- **Grok:** ≥100 honest + 36 planted.
- **Proposed:** **60 core entries** (GPT) + 24 planted [OPEN], **with honest power stated** (planning estimates, GPT r1). Scaling E1's ±0.077 at 24 groups gives ≈**±0.049 pooled** and ≈±0.069 per family at 60 groups. At a true difference of 0, a ±0.05 non-inferiority test has only ~50% power, so "inconclusive" is a likely outcome and is pre-declared as such. This lowers power but does not break validity. If the B0 throughput formula allows ≥100 within budget, the entry count is raised to 100 before B1 (decided by formula, not by results).

### [CONFLICT] 4. Cache test size and rule (A5 and B)
- **GPT:** a small fixed-answer set run cold/cold, warm/warm and cold/warm, plus hard examples; report counts with uncertainty; any unexplained discrepancy → withhold the cache claim and continue uncached; say "no discrepancy observed", not a certified rate.
- **Claude:** 480 per model, cold/warm ≤ cold/cold + 0.03, log the top-2 logit gap.
- **Grok:** upper CI of cold/warm ≤ cold/cold with **no slack**, otherwise B is cold-only.
- **Proposed:** **GPT's design** (≈100 fixed-answer + 20 hard near-tie prompts per model [OPEN]), keeping Claude's logit-gap logging.
  - The cache claim is allowed **only if zero changed predictions** are observed. It is then worded "no discrepancy observed in n=…, 95% upper bound …" (rule of three).
  - Any change → cache claim withheld and B runs uncached (consistent with Grok's cold-only fallback).
  - This is stricter than both Claude's +0.03 and Grok's CI rule, so validity is preserved at lower cost.

### [CONFLICT] 5. GPU-hour split (T4/P100 class)
- **GPT:** pilot+B0 2 / B1 3 / B2 2 / B3 5 / reserve 3.
- **Claude/rev 2 and Grok:** B0 2 / B1 4 / B2 6 / B3 3.
- **Proposed:** **GPT's split** (15 h total either way). B2 shrinks because of the byte-identity assertion (below), and B3 is the headline. **Permitted reserve uses (fixed now):**
  - (a) re-running a sub-stage after an infrastructure crash with no result seen;
  - (b) the substitute model's qualification in B0;
  - (c) completing an interrupted checkpointed stage.

  The reserve is never used to extend N or add conditions after seeing results.

### [CONFLICT] 6. Long definitions (F3)
- **GPT:** a small exploratory arm.
- **Claude:** F3L as a separate family at 7B.
- **Grok:** restore F3 long in B1.
- **Proposed:** **F3L as a small exploratory arm** (10 entries [OPEN]). It is a separate family, never in the gate primary or the B2/B3 primary, and is reported descriptively. This satisfies Claude's "separate" requirement.

### [CONFLICT] 7. Gate bars
- **GPT:** target ≥0.90 valid acceptance and ≥0.95 corruption rejection; the 80/90 rule must not become the success criterion.
- **Grok:** B1 ≥0.80 honest acceptance / ≥0.90 planted rejection at 0.90, with no post-hoc threshold.
- **Claude:** separate calibration and TEST bars.
- **Proposed:**
  - **Calibration-separation (go/no-go for using the gate): ≥0.80 / ≥0.90** (Grok).
  - **Reported target: ≥0.90 / ≥0.95** (GPT).
  - TEST-pass bar ≥0.80 / ≥0.90 [OPEN].
  - The per-entry 0.90 probe threshold stays fixed, with no post-hoc threshold.
  - **None of these is the POC success criterion**, which is defined in B3/B2.

### [CONFLICT] 8. 7B substitutes
- **GPT:** OLMo, then Mistral only.
- **Grok:** OLMo → Mistral → Gemma, and stop if neither of the first two qualifies.
- **Claude:** silent.
- **Proposed:** **OLMo-2-7B-Instruct → Mistral-7B-Instruct-v0.3**, then stop and report (GPT). Gemma is dropped. Grok's "stop if neither of the first two qualifies" is read as "stop if no two-lab pair qualifies after the listed substitutes".

### [CONFLICT] 9. Precision
- **GPT:** a pinned, memory-tested 4-bit bitsandbytes config.
- **Claude:** fp16 with a fail-loud guard and a reference check, or 8-bit.
- **Proposed:** **pinned 4-bit nf4 bitsandbytes** (GPT), one model at a time, the same for qualification and TEST. Claude's **fail-loud non-finite guard** and the **reference smoke check** (4-bit vs a higher-precision reference on 50 prompts; agreement ≥98% [OPEN]) are both kept. Precision and the library versions are logged.

### Non-conflicting changes applied (rev 3)
- **Before Stage A:** freeze the generator code hash and seeds (GPT). **Verify model access** (HF gated licences for Llama) before any GPU stage (GPT).
- **Qualification (B0):** rule comprehension ≥0.90 **and**, as a separate qualification, arithmetic direct text ≥0.80 (GPT; Grok), on the qualification pool. Models are loaded one after the other (GPT).
- **Probes:** their output format (a single letter) and token budget (≤4 tokens) are kept separate from the arithmetic format and its 192-token budget (GPT). Generation length is logged for every row (Grok).
- **Manipulation check:** counted **only on questions whose gold answer changes** under the plant (GPT).
- **B2 shrink:** if the id_oracle prompt (after local expansion) is byte-identical to the matched direct-text prompt, **assert equality in code** (sha256 per item). Then run only a small paired check (e.g. 60 items [OPEN]) to confirm identical outputs, instead of a full second condition (GPT).
- **B3:**
  - log exactly what the sender sees (message, candidate labels or definitions);
  - include candidate preparation (label generation, BM25/embedding) in the cost;
  - frame it as **4-way selection, not a repository search**;
  - the direct-text receiver gets **the same original message** the sender saw (GPT);
  - the retrieval baseline must be beaten (Claude).
- **CI widths** throughout are **planning estimates** (GPT). Cases per entry: 10, paired cluster bootstrap over entries (Grok).
- **Core families:** F1 negation and F2 roles (GPT). F3s (shortened) stays in Stage A only as a diagnostic.

---

## 0. Global rules (all stages)

- **The 0.90 gate bar is NOT lowered.** What the gate *measures* changes instead: rule comprehension (small-choice probes) instead of arithmetic answers (Claude [3]; GPT; supersedes Grok 2's lower-bar suggestion).
- **Rule probes (Claude r1):** **≥20 four-option probes per entry.** An entry passes the probe gate iff **each model ≥0.90** on its probes **and** inter-model agreement **≥0.90**.
- **Probe leakage controls (Claude r1, fix 4):**
  - (a) **No-entry-text check:** every probe is also asked *without* the entry text. Mean accuracy must be within 0.25 ± 0.08 [OPEN] (chance). Probes above that are dropped before freezing, and the drop is logged.
  - (b) **Invented rules only:** made-up names, rates and roles, so that no world-knowledge default can answer them.
  - (c) **Every planted corruption must flip the gold answer of ≥1 probe** of its entry, asserted in the builder. A plant that flips none is regenerated.
- **Separate, explicit bars (Claude r1):**
  - **Calibration-separation bar:** honest acceptance ≥0.80 **and** planted rejection ≥0.90 [OPEN numbers].
  - **TEST-pass bar** (unseen corruption types, fresh cases): honest acceptance ≥0.80 **and** planted rejection ≥0.80 [OPEN].
  - Each is judged on its own and reported on its own.
- **Verdict rule for a point estimate vs a CI (Claude r1):** for every pass/fail bar:
  - **"pass"** = the CI lower bound ≥ the bar;
  - **"pass, imprecise"** = the point estimate ≥ the bar but the CI straddles it;
  - **"fail"** = the point estimate < the bar.
  - "Pass, imprecise" is never reported as "pass".
- **Family exclusion (Claude r1):** a family that fails qualification (B0) or the precondition (A1) is **excluded from the gate and from the B2 primary**, but **all of its results are still reported** (labelled "excluded family").
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

- **Models (Claude r1):** **Qwen2.5-3B-Instruct + Llama-3.2-3B-Instruct** (Q4_K_M, `bartowski/Llama-3.2-3B-Instruct-GGUF`) for **A1–A4 and A6**. **SmolLM2-1.7B for A5 only** (it has the E1 cache-disagreement baseline). Qwen-3B is the strongest reference model available on the box.
- **Stage A amendment limit (Claude r1):** even if Stage A leads to a small-pair calibration amendment, **no amendment based on Stage A can carry repository claims.** Such a calibration is a diagnostic too.
- **Hardware / runtime:** 8 threads, ~15 GB RAM, one model loaded at a time (~2–2.3 GB each). E1 measured rates: Qwen 2.25 s/call (main mean), Smol 1.31 s/call. **Budget ≤6 h wall-clock** [OPEN]. Stop and report if it is exceeded; do not shrink the stage.
- **Tasks:** F1 negation, F2 roles, F3s = **shortened** F3 (≤60 words, no filler; Grok 2). 6 entries per family (18) plus 6 planted [OPEN]. This is a diagnostic, so ≥100 entries is not attempted here.

| A-step | Content | Calls (≈) |
|---|---|---|
| A1 capability precondition (Claude [1]) | 10 diagnostic cases × 18 entries × 2 models, direct text | 360 |
| A2 rule-comprehension probes (Claude [3]; Claude r1) | 20 four-option probes × 24 entries × 2 models, plus the no-entry-text leakage check (20 × 24 × 2); report accuracy vs the 0.90 bar and inter-model agreement | 1,920 (short) |
| A3 prompt fix as a tested change (GPT: "hypothesis") | the A1 cases re-run with the E1 trailing `Answer:`; paired change in accuracy and in the rate of missing Answer lines | 360 |
| A4 manipulation check (Claude [4]) | 6 planted × 10 cases on Qwen-3B; does the answer follow the planted text? Ignored plants are kept as a stress test (Grok 1) | 60 |
| A5 cache determinism, item by item (GPT [7]; Claude r1 fix 3) | **480 prompts per model** × {cold, cold, warm, warm} × 3 models (Qwen, Llama, Smol) | 5,760 |
| A6 real prefix cache (Claude [8]) | per entry, cache `system + expansion` once, then 10 *different* cases; prose gets an equivalent cached message prefix; both vs cold | 720 |
| **Total** | | **≈9,200 calls.** About 1,900 are short probe calls (≈0.6 h). The A5 cache calls are ≈5,760 × ~1.9 s mean ≈ 3.0 h, with the warm calls cheaper. **≈5–6 h total** [OPEN: verify against the A1 measured rate; if the projection is >6 h, stop and report rather than shrink] |

**A1 precondition:** a model "has" a family if direct-text accuracy is ≥0.70 [OPEN] on it. This only determines what Stage A reports per family. It is not a repository gate.

**A5 cache-determinism rule (pre-registered, item by item):** for each prompt, compare predictions and correctness between runs.
- **Noise floor = the cold/cold change rate** (two fresh-context runs of the same prompt).
- A cache **passes** only if **cold/warm change rate ≤ cold/cold change rate + 0.03** (Claude r1), judged by the verdict rule above (CI upper bound of the difference ≤ 0.03 = pass). n=480 per model, because at n=120 the rule cannot be shown. Warm/warm is also reported.
- **Log the top-2 logit gap on the first answer token** for every A5 row (Claude r1). This lets changed predictions be attributed to near-tie items.
- Report **changed predictions** and **correctness flips** per model, per family, next to the **E1 baseline** (cold id_expanded vs repeat-cached, identical prompts, greedy; re-verified 2026-10-12 from `v6/e1/results/predictions_main_*.jsonl`): **Qwen 45/480 changed, 21 flipped; Smol 104/480 changed, 33 flipped**; 0/480 prompt differences.
- **Efficiency work (A6, and all of B's cost numbers) is gated on A5.** If the cache fails, A6 latency/FLOPs are reported as "cache inconsistent, not interpretable", and B uses cold runs only for any accuracy claim.

**Stage A exit / go rule:**
- If the small pair clears **0.90** on the rule probes (each model and agreement, on ≥75% [OPEN] of honest entries) and A4 shows the planted entries changing Qwen's behaviour, the small pair **may be calibrated** in a separately pre-registered amendment.
- **Otherwise (expected): go to Stage B (7B).** Either way, Stage A artifacts and diagnostics are published as they are.

## Stage B: 7B pair on Kaggle GPU

Common rules: frozen generator and seeds; disjoint pools; checkpoints after each sub-stage; **each sub-stage has a fixed GPU-hour budget [OPEN]. If a budget runs out: STOP and report, never shrink N or drop conditions.** **Precision (Claude r1, fix 1):** T4/P100 have no native bf16, and fp32 7–8B models do not fit in 16 GB. Proposed: **fp16 with a fail-loud overflow guard.** Any non-finite logit aborts the sub-stage (no `__OVERFLOW__` placeholder rows as in v5k). Before B0, a **reference smoke check** compares fp16 with an 8-bit or CPU-fp32 reference on 50 prompts per model: greedy outputs must agree on ≥98% [OPEN]. The alternative is **8-bit (bitsandbytes) everywhere** [OPEN: choose one]. The same precision is used in every B sub-stage and for every model, and it is logged in the MANIFEST. Every result is per family.

### B0: qualification of a 7B pair from two labs
- **Primary pair:** Qwen2.5-7B-Instruct + **Llama-3.1-8B-Instruct**. **Named substitute sequence** for the second model, used in this order if one fails: OLMo-2-1124-7B-Instruct → Mistral-7B-Instruct-v0.3 → Gemma-2-9B-it [OPEN].
- **Qualification on its own data** (the qualification pool, disjoint from calibration and TEST): rule probes ≥0.90 and direct-text task accuracy ≥0.80 [OPEN] per family. The first two qualifying models from **different labs** form the pair. Substitutions are logged.
- **Throughput measurement (Claude r1):** B0 measures each model's batched generation throughput (tokens/s, at the chosen precision and batch size) on qualification prompts.
- **N is derived by a written formula** and frozen in an amendment before B1:
  `N_cases_per_entry = floor( (B2_budget_h·3600·tps_min·0.8) / (E·C·(P̄ + Ḡ)·M) )`
  - E = number of entries; C = number of conditions; P̄ and Ḡ = mean newly processed prompt tokens and generated tokens; M = 2 models; tps_min = the slower model's measured tokens/s; 0.8 = safety factor.
  - Capped at 10 and floored at 5. If the formula gives <5: stop and report "budget insufficient".
- Budget: 2 GPU-h [OPEN]. If no pair qualifies: stop and report "no qualifying 7B pair".

### B1: gate calibration (≥100 entries)
- **≥100 honest entries** (≈25 per family across **four** families: F1, F2, F3s (shortened, as in Stage A) and **F3L (long F3 restored, kept as a separate family**; Claude r1)) + 36 planted (calibration corruption types). Per-family results are descriptive (power ≈±0.065 per family). Pooled power ≈±0.038. TEST-gate cases use **unseen** corruption types (E1 list).
- **Gate:** ≥20 probes per entry. An entry passes iff each model scores ≥**0.90** and agreement is ≥0.90 (§0). Calibration is judged against the **calibration-separation bar** and TEST-gate against the **TEST-pass bar** (§0), each with the verdict rule. A manipulation check on the stronger model accompanies it.
- Budget: 4 GPU-h [OPEN].
- **If B1 fails: B2 and B3 still run**, but the combined pipeline **may not be called a checked repository**. Report gate acceptance, coverage and abstentions alongside every B2/B3 number.

### B2: oracle-ID receiver comparison
- The receiver gets the correct ID and expands it locally (hash-checked). Conditions: **id_oracle** vs the **matched direct_text** (exact expansion text and framing; GPT [5]) vs prose, id_raw and placebo. Plus prefix-cached variants for id and prose, valid only if the A5-style determinism rule passes on the 7B models.
- **Primary:** id_oracle vs direct_text, non-inferiority margin **±0.05**, paired cluster bootstrap over entries (2000 resamples). Inconclusive is reported separately from equivalent.
- **Power:** E1's half-width was ≈0.077 at 24 groups. At ≥100 entries it scales to ≈±0.038 pooled and ≈±0.065 per family. Pooled ±0.05 is attainable; per-family is reported as descriptive [OPEN: N per entry 10].
- Held-out TEST cases only. Coverage-only results are reported only if B1 passed.
- **Batched generation is required (Claude r1, fix 2):** ≈12k generations and >1M tokens. The B2 budget must be checked against B0's measured throughput via the N formula before B2 starts.
- Budget: 6 GPU-h [OPEN].

### B3: sender selection (its own experiment; GPT, Claude [12])
- The sender reads a natural-language message (never the entry text) and picks one ID from **4 confusable neighbours** (same family and wording, differing in polarity / role direction / threshold). Two variants: short labels (primary) and full definitions (ceiling). Both models act as sender.
- **Retrieval baseline (Claude r1):** BM25 over the candidate labels/definitions and nearest-label embedding similarity (a small open sentence-embedding model [OPEN: which]). **The sender must beat the better retrieval baseline** (paired CI over entries) for B3 to count as model-based selection.
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

## Open choices (rev 2)
- **Numbers still [OPEN]:**
  - the no-entry-text chance band (±0.08);
  - the calibration-separation bar (0.80 / 0.90) and the TEST-pass bar (0.80 / 0.80);
  - A1 0.70;
  - B0 task-accuracy 0.80;
  - fp16-vs-reference agreement 98%;
  - GPU-hour budgets (B0 2, B1 4, B2 6, B3 3);
  - `max_new_tokens` 192.
- **Precision:** fp16 + fail-loud guard + reference smoke check, **or** 8-bit everywhere.
- **The second 7B model and substitute order** (Llama-3.1-8B → OLMo-2-7B → Mistral-7B-v0.3 → Gemma-2-9B).
- **The embedding model for the B3 retrieval baseline.**
- **Stage A runtime:** the ≈5–6 h projection must be confirmed against the A1 measured rate.
- **Resolved in rev 2 (Claude r1):**
  - 0.90 kept, with ≥20 probes;
  - separate bars plus the "pass, imprecise" verdict;
  - N derived by formula from B0 tokens/s;
  - ≥100 entries;
  - Llama-3.2-3B in A1–A4/A6, Smol in A5 only;
  - F3L separate at 7B;
  - the family-exclusion rule;
  - A5 at n=480 with +0.03 and the logit gap;
  - probe leakage controls;
  - the B3 retrieval baseline;
  - no repository claims from Stage A amendments.
- The code (`e1b.py`, `run.sh`, the validator `--e1b`) is specified, not written.
