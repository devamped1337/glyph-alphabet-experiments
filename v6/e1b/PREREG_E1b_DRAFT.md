# E1b PREREG: DRAFT rev 5 (consolidated specification)

**Status: DRAFT, 2026-10-12 (AEDT). Not frozen and not tagged. No E1b code exists and nothing has been run.** Written after the E1 results were seen (`RESULTS_E1.md`, `v6/e1/CALIBRATION_REPORT.md`).

**What this revision is:** one consistent specification. Every setting has exactly one value. All superseded text was removed (GPT r2, point 7). The earlier revisions stay in git: rev 1 `ce7cd5d`, rev 2 `283aaad`, rev 3 `1550275`, rev 4 `ee45548`.

**Reviews applied** (`v6/e1b/reviews/`): `claude_1.md`, `claude_2.md` (Claude's fetcher served rev 1; judged from the user's description), `gpt_1.md`, `gpt_2.md`, `grok_1.md`, `grok_2.md`. Earlier E1 reviews: `v6/e1/reviews/*`. Disagreements that remain are listed in §12.

**Freezing requires:** sign-off on §12, the git tag `prereg-e1b`, and a dated entry in `v6/PREREG_v6.md`.

---

## 1. Purpose and limits

- **This is a communication proof of concept** to attract interest and donated compute. It is not a definitive paper. The user has no API budget.
- **The headline question (B3):** can a sender model pick the right entry ID from 4 confusable neighbours, so that a receiver given only `ID@version#hash` recovers the meaning on held-out cases about as well as when it gets the original message, while transmitting ≥30% fewer bytes?
- **Limit:** only open-weight models are used. The closed-lab / public-API version of the repository (delegates of closed models) is **untested**.
- **Stage A** (box CPU, small models) is **diagnostic only and carries no repository, ID-channel or efficiency claims**. Neither does any amendment based on Stage A (Claude r1).

## 2. Structure, budgets and stop rules

| Stage | Where | Purpose | Budget |
|---|---|---|---|
| A | box CPU (8 threads, ~15 GB RAM) | diagnostics: capability, probes, prompt fix, manipulation, CPU cache | **2 h wall-clock** |
| B0 | Kaggle GPU (T4/P100 class) | access check, precision canaries, qualification, throughput, pilot timings, N choice | **2 GPU-h** (pilot included) |
| B1 | Kaggle | gate calibration + TEST gate | **3 GPU-h** |
| B2 | Kaggle | oracle-ID receiver comparison + GPU cache check | **2 GPU-h** |
| B3 | Kaggle | sender selection + full exchange (headline) | **5 GPU-h** |
| Reserve | Kaggle | only the permitted uses below | **3 GPU-h** |

- **Budget rule:** if a stage's budget runs out, **stop and report**. N is never shrunk and **conditions are never dropped because the budget ran out** (Claude r2).
- **Permitted reserve uses (fixed now):**
  - (a) re-running a stage after an infrastructure crash with no result seen;
  - (b) qualification of a substitute model in B0;
  - (c) completing an interrupted checkpointed stage;
  - (d) the optional higher-precision comparison (§4).

  The reserve **never extends N or adds conditions** (Grok r2).
- **No interim looks** at any B2/B3 primary comparison. No alpha-spending is pre-registered, so there is none (Claude r2).
- **Other stop rules:**
  - a disjointness, uniqueness or gold assertion fails → abort the build;
  - the validator fails at a checkpoint → stop that stage;
  - a non-finite logit → abort the stage (§4);
  - no qualifying two-lab pair in B0 → stop Stage B and report.

## 3. Models

- **Stage A:** Qwen2.5-3B-Instruct Q4_K_M + SmolLM2-1.7B-Instruct Q4_K_M (the E1 files, sha256 logged), llama-cpp-python. No third small model (GPT r1; Grok r1).
- **Stage B pair:** **Qwen2.5-7B-Instruct + Llama-3.1-8B-Instruct**, loaded one at a time. If Llama fails access or qualification, the substitutes in order are **OLMo-2-1124-7B-Instruct → Mistral-7B-Instruct-v0.3**. If no pair from two labs qualifies: stop and report (GPT r1).
- **Model access** (including Llama's gated licence) is verified before any GPU stage (GPT r1).
- Every artifact logs the HF repo, revision, file sha256 and library versions (transformers, bitsandbytes, torch, llama-cpp-python).

## 4. Precision (Stage B)

- **Pinned 4-bit nf4 bitsandbytes config** (compute dtype fp16, double-quant setting pinned), memory-tested in B0, and **the same for qualification, calibration and TEST**. It is logged in the MANIFEST (GPT r1).
- **Mandatory (GPT r2):**
  - **gold canaries:** 20 fixed prompts with known answers per model, run at the start of every stage; any canary failing that passed in B0 aborts the stage;
  - **finite checks:** any non-finite logit aborts the stage (fail-loud, no placeholder rows; Claude r1, Grok r2);
  - **qualification run in the actual nf4 config.**
- **Optional:** a higher-precision comparison (50 prompts per model, budgeted from the reserve). Agreement is reported descriptively. **<98% agreement alone is not a failure** (GPT r2).

## 5. Tasks, entries, pools

- **Core families:** F1 negation pricing and F2 roles (paraphrased). **F3L** (long definitions, as in E1) is a separate **exploratory arm of 10 entries**, reported descriptively. It never enters a primary analysis or the gate decision. Stage A also uses **F3s** (shortened, ≤60 words) as a diagnostic.
- **Rules are invented** (made-up names, rates and roles) so that world knowledge can't answer them (Claude r1).
- **Entry configurations (GPT r2 + Claude r2):**
  - exactly two are predefined: **C60 = 60 honest core entries (30 F1 + 30 F2) × 10 TEST cases**, or **C100 = 100 (50 + 50) × 10**;
  - **planted entries:** 24 (C60) or 40 (C100), split equally across families and corruption types;
  - **choice rule:** after the B0 pilot, which uses **non-TEST** pilot cases only, the formula below is computed. **C100 is chosen only if the projected time of every one of B1, B2 and B3 is ≤80% of its budget**; otherwise C60. Cap: 100.
  - `projected_stage_h = Σ_conditions Σ_models (items × (P̄_new + Ḡ)) / (3600 · tps_measured)`, where P̄_new = mean newly processed prompt tokens per item, Ḡ = mean generated tokens, and tps = the batched throughput measured in B0 for that model.
  - The choice and its inputs are **frozen in a dated amendment before B1**. It depends only on pilot timings, never on any accuracy result. **No later change to N**.
- **Cases per entry:** 10 (entries buy power; cases don't; Claude r2).
- **Pools (frozen generator code hash and seeds, recorded before Stage A; GPT r1):** Stage A diagnostic; A5/B2 cache set; B0 qualification; B0 pilot; B1 calibration; B1 TEST-gate; **B2/B3 TEST**.
- **Disjointness, enforced in code (Grok r2 lock 3; GPT E1 review):**
  - the builder asserts that the **B2/B3 TEST pool shares no case** (normalised text, and (entry, text)) with any other pool, and that no two pools share a case;
  - no duplicates within any pool;
  - every gold answer is independently recomputed from the parsed entry text;
  - any violation aborts the build, and the validator re-checks it on all output files.

## 6. Prompts and parsing

- **Arithmetic answers:** no trailing `Answer:` in the user turn and no line cap. The system asks for brief working plus a final `Answer: <int>|UNKNOWN`. `max_new_tokens=192`. Generation length is logged for every row (Grok r1).
- **Probes:** a separate format (answer with a single letter A–D) and a separate budget (≤4 new tokens), never mixed with the arithmetic settings (GPT r1).
- The parse path is logged. A missing `Answer:` line is counted and reported.

## 7. Stage A: CPU diagnostics (2 h)

Estimated from E1's measured CPU rates (Qwen-3B 2.25 s/call, Smol 1.31 s/call; probe calls ≈0.5 s). If the projection after A1 exceeds 2 h: stop and report.

| Step | Content | Calls | ≈ time |
|---|---|---|---|
| A1 capability | 4 entries × 3 families (F1, F2, F3s) × 10 cases × 2 models, direct text | 240 | 7 min |
| A2 probes | 24 entries (18 honest + 6 planted) × 20 probes × 2 models, **with** and **without** entry text | 1,920 | 16 min |
| A3 prompt fix | the A1 cases re-run **with** the E1 trailing `Answer:`; paired accuracy change and Answer-line rate | 240 | 7 min |
| A4 manipulation | 6 planted × 10 cases, Qwen-3B, scored **only on cases whose gold answer changes** under the plant (GPT r1) | 60 | 2 min |
| A5 CPU cache | 100 fixed-answer + 20 hard near-tie prompts × {cold, cold, warm, warm} × 2 models | 960 | 28 min |
| A6 CPU prefix-cache timing | 12 core entries × 10 cases × {id-expansion, prose} × {prefix-cached, cold} × 2 models | 960 | 28 min |
| **Total** | | **4,380** | **≈1.5 h** |

- **A1:** a model "has" a family if direct-text accuracy ≥ **0.70** (Grok r1). This is reported per family.
- **A2:** each model ≥0.90 on the probes and agreement ≥0.90, per entry. No-entry-text accuracy is reported (chance 0.25). **Probes with pooled no-text accuracy > 0.40 are flagged as leaky.** In Stage A they are reported. In B1 the probe set is regenerated **before** the B1 data is generated, never after.
- **Stage A → B rule:** the small pair "clears 0.90" if each model and their agreement reach ≥0.90 on ≥**80%** of honest entries **and** A4 shows that the plants change Qwen's answers on ≥70% of the changed-gold cases. If so, the small pair may be calibrated in a **separately pre-registered amendment, still with no repository claims**. Otherwise (expected): go to Stage B. Stage A results are published either way.

## 8. Cache test (CPU in A5, GPU in B2; each runtime checked separately; GPT r2)

- **Unit = independent prompt** (distinct case text). n = 120 independent prompts per model per runtime (100 fixed-answer + 20 hard near-tie). Repeats of the same prompt are not counted as extra n.
- **Runs per prompt:** cold, cold (a fresh context each time), warm, warm (prefix restored from the cache). Comparisons: cold/cold (**noise floor**; Claude r2), warm/warm, cold/warm.
- **Logged:** the prediction, token sequence, and the **top-2 logit gap on the first answer token** (Claude r1).
- **Rule:** the cache claim for that runtime is allowed **only if 0 changed predictions** are observed in cold/warm **and** in cold/cold. It is then worded **"no discrepancy observed in n=120 prompts (95% upper bound ≈2.5%, rule of three)"**, not as a certified rate (GPT r1/r2). **Any change:** the counts are reported with exact binomial CIs, the cache claim for that runtime is **withheld**, and every accuracy and cost claim in that runtime uses **uncached** runs.
- **Assumptions stated:** greedy decoding, the same build and library versions, batch size 1 for the cache test (batching effects are out of scope), and independence across distinct prompts.
- **E1 baseline** (CPU, cold vs repeat-cached, identical prompts; re-verified 2026-10-12): Qwen 45/480 changed, 21 correctness flips; Smol 104/480, 33 flips.

## 9. Stage B

### B0: qualification, throughput, pilot (2 GPU-h)
- Access check → precision canaries (§4) → qualification on the **qualification pool**, per family:
  - **rule probes ≥0.90**;
  - **separately, direct-text arithmetic ≥0.80** (GPT r1, Grok r1).
- **Family exclusion:** a family that fails for either pair model is **excluded from the gate decision and the B2/B3 primary**, and is still reported (Claude r1).
- **Throughput:** batched generation tokens/s per model in nf4 (Claude r1). Batched generation is used for B1–B3.
- **Pilot timings** on non-TEST pilot cases → the C60/C100 choice (§5), frozen by amendment before B1.

### B1: gate (3 GPU-h)
- **Probes:** ≥20 four-option probes per entry. An entry passes iff **each model ≥0.90 and agreement ≥0.90**. Fixed, with no post-hoc threshold.
- **Leakage controls:**
  - no-text probe accuracy reported (target ≈0.25);
  - invented rules only;
  - every planted corruption flips the gold of ≥1 of its probes, asserted in the builder (Claude r1).
- **Manipulation check:** on the stronger model, scored only on questions whose gold answer changes (GPT r1).
- **Two bars (GPT r2; Claude r1):**
  - **Calibration eligibility rule:** honest acceptance ≥0.80 **and** planted rejection ≥0.90 on the calibration pool. This decides only whether the gate is used to filter entries in B2/B3.
  - **Repository target:** honest acceptance ≥0.90 **and** planted rejection ≥0.95, reported on the **TEST-gate pool** (unseen corruption types).
- **Verdict wording:** "met in sample" (point estimate ≥ bar) is kept distinct from "met at 95% confidence" (CI lower bound ≥ bar), for every bar.
- **None of these bars is the POC success criterion** (GPT r1).
- **If B1 fails** (eligibility not met): **B2 and B3 still run, but the combined pipeline is not a checked repository. Gate acceptance, coverage and abstentions are reported alongside every B2/B3 number** (Grok r2 lock 4).

### B2: oracle-ID receiver comparison (2 GPU-h)
- The receiver gets the correct `ID@version#hash`. The delegate expands it locally after a **version/hash check in code**. On a mismatch it returns `UNKNOWN` with no model call. Test: 48 unknown, stale or wrong-hash messages; pass = 48/48.
- **id_oracle vs matched direct_text:** if the expanded id_oracle prompt is **byte-identical** to the direct_text prompt, this is asserted per item (sha256), and only a **60-item paired check** confirms identical outputs (GPT r1). If not identical, both run in full.
- **Prose** (the original message) runs on all TEST items.
- **Sanity controls:** id_raw (ID only) and placebo (answer-determining constants removed) run on a **pre-registered 30-entry sanity subset** (15 F1 + 15 F2, chosen by seed before any data) × 10 cases (Claude r2).
- **GPU cache test** (§8) and prefix-cached timing for id-expansion and prose, valid only if §8 passes.
- **Cost (all reported):** newly processed prompt tokens, generated tokens, latency, and **FLOPs = 2·params·(newly processed + generated tokens)**. Cached prefix tokens count 0 only if §8 passes. Uncached cost is always shown.

### B3: sender selection and full exchange: HEADLINE (5 GPU-h)
- The sender reads the natural-language **original message** (never the entry text) and picks one of **4 confusable candidates** (same family and wording, differing in polarity, role direction or a constant). This is **4-way selection, not a repository search** (GPT r1). Both models act as sender; each sender's pick goes to the other model as receiver.
- **Logged:** exactly what the sender sees: the message, the candidate IDs and the one-line labels (GPT r1).
- **Primary comparison (GPT r2):** **selected-ID pipeline accuracy** (sender pick → receiver expands the hash-checked entry → answers the TEST case) vs **the receiver given the same original message**. Non-inferiority margin **−0.05 (5 points)**, paired cluster bootstrap over entries (2000 resamples).
- **Bytes:** transmitted bytes of `ID@version#hash8` with its framing vs the bytes of the original message. Target: **≥30% fewer**.
- **Costs reported (GPT r2):** sender, candidate preparation (labels, any retrieval), receiver, and **dictionary setup amortised** over the number of messages (reported as break-even message count).
- **Separate secondary claim:** the sender beats retrieval baselines (BM25 over labels; nearest-label embedding with sentence-transformers `all-MiniLM-L6-v2`) and chance (0.25) on selection accuracy (Claude r1). This is not part of the headline.

## 10. Success criteria, CI widths and power (Grok r2 lock 2; GPT r2; Claude r2)

- **POC success = all of:**
  - (i) the B3 primary is non-inferior (CI lower bound > −0.05) on the pooled non-excluded core families, for **both** receiver directions;
  - (ii) ≥30% fewer transmitted bytes;
  - (iii) all costs reported per §9.

  Anything else is reported as **inconclusive** (CI straddles −0.05) or **failed** (point estimate < −0.05), never reframed. **Inconclusive is a legitimate, pre-declared outcome.**
- **Illustrative planning calculation** (normal approximation, scaled from E1's ±0.077 half-width at 24 groups; not a guarantee):

| Entries | 95% half-width | P(non-inferior at −5 pts), true diff 0 | P(equivalent ±5), true diff 0 | P(NI), true diff −2 |
|---|---|---|---|---|
| 60 | ±4.87 pts | ~52% | ~4% | n/a |
| 100 | ±3.77 pts | ~74% | ~48% | ~34% |
| 150 (not run) | ±3.08 | ~89% | n/a | n/a |
| 200 (not run) | ±2.67 | ~96% | n/a | n/a |

  These figures were re-computed on 2026-10-12 and match GPT r2 and Claude r2.
- **Per-family** results are descriptive.

## 11. Run interface, artifacts, validator

- **One entrypoint per stage:** `bash v6/e1b/run.sh <A|B0|B1|B2|B3>` → `python v6/e1b/e1b.py --stage …`, resumable with `.done` checkpoints. At the start it logs the commit, config sha256, generator hash and seeds, model revisions/sha256, library versions and hardware.
- **Artifacts:** `v6/e1b/results/<stage>/` (the cases with their disjointness report, all predictions, canary, cache and timing logs, `summary.json`, `MANIFEST.json` with sha256s). Committed if each file is <10 MB.
- **Validator** `v6/checks/validate_v6.py --e1b`. It is an **engineering check only and certifies no claim**. It checks:
  - disjointness, uniqueness and gold, across all pools and outputs;
  - row counts per condition against the frozen config, including the sanity subset;
  - cache: cold/cold, warm/warm and cold/warm records exist for every prompt, and the counts match the report;
  - FLOPs recomputed from newly processed tokens;
  - unknown-ID 48/48 with no model call;
  - canaries and finite checks logged;
  - MANIFEST hashes.

  A non-zero exit means nothing is published.

## 12. Remaining disagreements and items needing sign-off

1. **N: two configurations vs a fixed 60.** Grok r2 asked for "no raising N after seeing numbers" and accepted a fixed 60. This spec follows **GPT r2 and Claude r2**: C60 or C100, chosen by a timing-only formula before B1. Timing data is not outcome data, but Grok has not confirmed this reading.
2. **TEST bar: 90/95 vs 80/90.** GPT r2 overrides Grok r2's lock of the TEST-pass bar at 0.80/0.90. Here 80/90 is only the calibration eligibility rule, and **90/95 is the reported repository target** on TEST. Grok's sign-off is needed.
3. **Stage A model set:** Claude r1 wanted Llama-3.2-3B. This spec follows GPT r1 and Grok r1 (Qwen-3B + Smol only).
4. **Cache rule:** this spec uses "zero changes observed" at n=120 independent prompts (GPT). Claude r1 asked for n=480 with a +0.03 margin, and Grok r1 for no slack. The zero-change rule is stricter than both for making a claim, but at n=120 it cannot show a rate below ≈2.5%.
5. **Thresholds proposed by the drafter and not yet reviewed:**
   - the leaky-probe flag at >0.40;
   - the Stage A exit "≥80% of honest entries" and A4 ≥70%;
   - 20 canaries;
   - the 60-item byte-identity check;
   - the 30-entry sanity subset split;
   - the ≤80%-of-budget rule for choosing C100;
   - `all-MiniLM-L6-v2` as the embedding baseline.
6. **Claude r2 judged rev 3 from a description only**, because its fetcher served stale content. It should re-review this file directly.
7. **Code not written:** `e1b.py`, `run.sh` and the `--e1b` validator mode are specified, not implemented.
