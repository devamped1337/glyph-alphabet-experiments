# E1b PREREG: FROZEN 2026-10-12 (AEDT)

**Status: FROZEN on 2026-10-12 (AEDT). Git tag `prereg-e1b`.** No E1b code had been written and no E1b data generated when it was frozen. Any later change must be a dated entry under **Amendments** at the end of this file, stating whether it was made before or after any E1b result was seen.

Frozen from DRAFT rev 6 (`838c9fa`). Written after the E1 results were seen (`RESULTS_E1.md`, `v6/e1/CALIBRATION_REPORT.md`) and designed in response to them.

**Review history** (`v6/e1b/reviews/`, all summaries relayed by the user):
- [claude_1](reviews/claude_1.md) (rev 1)
- [gpt_1](reviews/gpt_1.md) (rev 1)
- [grok_1](reviews/grok_1.md) (rev 1–2)
- [grok_2](reviews/grok_2.md) (rev 3)
- [gpt_2](reviews/gpt_2.md) (rev 3)
- [claude_2](reviews/claude_2.md) (rev 3; stale fetch, judged from a description)
- [claude_3](reviews/claude_3.md) (rev 5, read directly)
- [grok_3](reviews/grok_3.md) (rev 5 sign-off)

Draft lineage in git: rev 1 `ce7cd5d` → rev 2 `283aaad` → rev 3 `1550275` → rev 4 `ee45548` → rev 5 `eaead82` → rev 6 `838c9fa` ([PREREG_E1b_DRAFT.md](PREREG_E1b_DRAFT.md)). **Sign-off:** Grok (grok_3: "lock it"), GPT (gpt_2 backed the rev-5 approach), and Claude (claude_3; its fixes were applied in rev 6 with no new conflicts).

---

## 1. Purpose and limits

- **This is a communication proof of concept** to attract interest and donated compute. It is not a definitive paper. The user has no API budget.
- **The headline question (B3):** can a sender model pick the right entry ID from 4 confusable neighbours, so that a receiver given only `ID@version#hash` recovers the meaning on held-out cases about as well as when it gets the original message, while transmitting ≥30% fewer bytes?
- **What the −0.05 margin implies (Claude r3 f):** a wrong pick almost always gives a wrong answer (asserted in §5). So the pipeline can only be within 5 points of the original-message arm if **selection accuracy is about ≥0.95**. A B3 failure will therefore most likely reflect **selection**, not the receiver's handling of the expansion.
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
  - **confusable neighbours are load-bearing (Claude r3 f):** for every core entry, each of its 3 wrong neighbours must change the gold answer on **≥80% of that entry's TEST cases**. Otherwise the neighbour is regenerated before freezing the pools;
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
- **A2:** each model ≥0.90 on the probes and agreement ≥0.90, per entry. No-entry-text accuracy is reported (chance 0.25). **Leak flag (Claude r3 c): per probe template, pooled across entries, with ≥50 no-text observations per template. A template with no-text accuracy > 0.40 is flagged as leaky.** In Stage A they are reported. In B1 the probe set is regenerated **before** the B1 data is generated, never after.
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
- **4-bit load test on the assigned GPU (Claude r3 i):** load each model in the pinned nf4 config on the GPU Kaggle actually assigns, and run the canaries. **Pre-registered fallback:** if bitsandbytes nf4 fails to load or run on that GPU (expected risk: P100, compute capability 6.0), use **GGUF Q4_K_M via llama.cpp with CUDA** for **all** Stage B models and stages. Logged and never mixed.
- Access check → precision canaries (§4) → qualification on the **qualification pool**, per family:
  - **rule probes ≥0.90**;
  - **separately, direct-text arithmetic ≥0.80** (GPT r1, Grok r1).
- **Family exclusion:** a family that fails for either pair model is **excluded from the gate decision and the B2/B3 primary**, and is still reported (Claude r1).
- **Throughput:** batched generation tokens/s per model in nf4 (Claude r1). Batched generation is used for B1–B3.
- **Pilot timings** on non-TEST pilot cases → the C60/C100 choice (§5), frozen by amendment before B1.

### B1: gate (3 GPU-h)
- **Probes:** ≥20 four-option probes per entry. An entry passes iff **each model ≥0.90 and agreement ≥0.90**. Fixed, with no post-hoc threshold.
- **Leakage controls:**
  - no-text probe accuracy reported (target ≈0.25), with the leak flag per probe template (≥50 no-text observations per template, flag at >0.40, as in §7);
  - invented rules only;
  - every planted corruption flips the gold of ≥1 of its probes, asserted in the builder (Claude r1).
- **Manipulation check:** on the stronger model, scored only on questions whose gold answer changes (GPT r1).
- **Two bars (GPT r2; Claude r1):**
  - **Calibration eligibility rule:** honest acceptance ≥0.80 **and** planted rejection ≥0.90 on the calibration pool. This decides only whether the gate is used to filter entries in B2/B3.
  - **Repository target:** honest acceptance ≥0.90 **and** planted rejection ≥0.95, reported on the **TEST-gate pool** (unseen corruption types).
- **TEST-gate pool size (Claude r3 a):** all core honest entries (60 or 100) re-probed with fresh probes, plus **40 planted entries** (4 unseen corruption types × 10). **Precision:** at 40 planted, a point estimate of 0.95 (38/40) has a 95% lower bound of ≈**0.83–0.84** (Wilson 0.835). At 60 honest entries, 0.90 (54/60) has a lower bound of ≈0.80. So the 90/95 target can be "met in sample" but not "met at 95% confidence" at this size. This is stated in advance.
- **Verdict wording:** "met in sample" (point estimate ≥ bar) is kept distinct from "met at 95% confidence" (CI lower bound ≥ bar), for every bar.
- **None of these bars is the POC success criterion** (GPT r1).
- **If B1 fails** (eligibility not met): **B2 and B3 still run, but the combined pipeline is not a checked repository. Gate acceptance, coverage and abstentions are reported alongside every B2/B3 number** (Grok r2 lock 4).

### B2: oracle-ID receiver comparison (2 GPU-h)
- **What B2 shows (Claude r3 h):** given byte identity, the id_oracle vs direct_text difference is **zero by construction**, so it is a check, not a finding. B2's content is the **prose comparison** and the **cost table**.
- The receiver gets the correct `ID@version#hash`. The delegate expands it locally after a **version/hash check in code**. On a mismatch it returns `UNKNOWN` with no model call. Test: 48 unknown, stale or wrong-hash messages; pass = 48/48.
- **id_oracle vs matched direct_text:** if the expanded id_oracle prompt is **byte-identical** to the direct_text prompt, this is asserted by a **sha256 per item on all items**, and outputs are confirmed identical on a **20-item paired check** (Claude r3 d; GPT r1). If not identical, both run in full.
- **Prose** (the original message) runs on all TEST items.
- **Sanity controls:** id_raw (ID only) and placebo (answer-determining constants removed) run on a **pre-registered 30-entry sanity subset** (15 F1 + 15 F2, chosen by seed before any data) × 10 cases (Claude r2).
- **GPU cache test** (§8) and prefix-cached timing for id-expansion and prose, valid only if §8 passes.
- **Cost (all reported):** newly processed prompt tokens, generated tokens, latency, and **FLOPs = 2·params·(newly processed + generated tokens)**. Cached prefix tokens count 0 only if §8 passes. Uncached cost is always shown. **Cached timing is measured at batch size 1 only** (the §8 assumption). The cost table labels it "batch-1". Batched cached throughput is not measured or claimed (Claude r3 b).

### B3: sender selection and full exchange: HEADLINE (5 GPU-h)
- The sender reads the natural-language **original message** (never the entry text) and picks one of **4 confusable candidates** (same family and wording, differing in polarity, role direction or a constant). This is **4-way selection, not a repository search** (GPT r1). Both models act as sender; each sender's pick goes to the other model as receiver.
- **Logged:** exactly what the sender sees: the message, the candidate IDs and the one-line labels (GPT r1).
- **Primary comparison (GPT r2):** **selected-ID pipeline accuracy** (sender pick → receiver expands the hash-checked entry → answers the TEST case) vs **the receiver given the same original message**. Non-inferiority margin **−0.05 (5 points)**, paired cluster bootstrap over entries (2000 resamples).
- **Message definition (Claude r3 g):**
  - A "message" carries the **rule** only. The **case text** (the question) reaches the receiver **identically in both arms**: the same bytes, appended after the rule part.
  - **Byte denominators:** for each arm, **total receiver-input bytes** = the transmitted rule part (`ID@version#hash8` with its framing, vs the original message's UTF-8 bytes) **+** the identical case-text bytes. The saving is reported both on the rule part alone and on the total.
  - Messages with **slots** (parameters filled per message) are future work.
  - **The byte saving is near-guaranteed by design** (a ~20-byte ID vs a multi-sentence message), so the ≥30% criterion is a sanity bar, not evidence of a hard result.
- **Bytes:** transmitted bytes of `ID@version#hash8` with its framing vs the bytes of the original message. Target: **≥30% fewer** total receiver-input bytes.
- **Costs reported (GPT r2):** sender, candidate preparation (labels, any retrieval), receiver, and **dictionary setup amortised** over the number of messages (reported as break-even message count).
- **Separate secondary claim:** the sender beats retrieval baselines and chance (0.25) on selection accuracy (Claude r1). The baselines are a **lexical TF-IDF and a BM25** match of the message against the candidate labels (Claude r3 j), and nearest-label embedding with sentence-transformers `all-MiniLM-L6-v2`. The sender must beat the best of the three. This is not part of the headline.

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
- **Joint power for both receiver directions (Claude r3 e):** success requires non-inferiority in **both** directions. The joint power lies between the product (independent directions) and the single-direction value (perfectly correlated directions):
  - **C100 ≈ 0.55–0.74**;
  - **C60 ≈ 0.27–0.52**;

  at a true difference of 0.
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

## 12. Review status at freeze

- **Resolved:** all rev-5 §12 items.
  - Grok signed off on all of them (`grok_3.md`: "lock it"), including the C60/C100 timing-only choice and the 90/95 TEST target.
  - GPT backed this approach (`gpt_2.md`).
  - Claude reviewed rev 5 directly (`claude_3.md`). Its fixes (a)–(j) are applied in rev 6, and none introduces a conflict with GPT or Grok.
  - The byte-identity check went from 60 to 20 items, plus a per-item sha256 on all items.
- **Stage A model set** stays Qwen-3B + Smol (GPT r1, Grok r1). Claude did not reopen this in r3.
- **The code is not written:** `e1b.py`, `run.sh` and the `--e1b` validator mode are specified, not implemented.

## Amendments

### A1: 2026-10-12 (AEDT), made BEFORE any E1b code, data or result existed

**Source:** [gpt_3](reviews/gpt_3.md), GPT's review of rev 5. It arrived just after the freeze commit `cf43e68` (tag `prereg-e1b`). These clarifications were meant to be part of the freeze, so they are recorded here as the first amendment instead of moving the tag. **They are binding and take precedence over the sections they name.**

1. **Runtime projection (replaces the formula in §5):**
   - The projection for each stage = **measured elapsed wall time per representative call or batch** (sender + receiver, at the batch size actually used) × the number of calls or batches, **plus measured setup time** (model load, canaries, cache warm-up). It is measured on B0 non-TEST pilot cases, not derived from a single tokens/s figure.
   - **C100 is chosen only if every stage (B1, B2, B3) projects at ≤80% of its budget.** Otherwise C60 is checked by the same rule. If C60 also doesn't fit, report **"insufficient budget"** and stop.
2. **Accuracy labels (replaces the §10 wording, and applies to every non-inferiority comparison). They are mutually exclusive:**
   - CI lower bound > −0.05 → **non-inferior**;
   - CI upper bound < −0.05 → **inferior**;
   - otherwise → **inconclusive**.

   A missed byte target (§9 B3) is reported **separately** and never merged into the accuracy label. The §10 power table is **per comparison**. The joint power for both directions is noted separately (§10).
3. **Gate and denominators (§9 B1, B3):**
   - The **accepted dictionary list is fixed from calibration**. TEST-gate results only evaluate it and never change it.
   - **All scheduled core TEST cases stay in the headline denominator.** Cases of rejected entries, and abstentions (`UNKNOWN`), are counted as not correct and shown as separate columns.
   - Any family exclusion is stated in the headline itself, not only in a footnote.
4. **Cache (§8):**
   - A pass at batch size 1 supports **batch-1 cached measurements only**.
   - The claim requires **zero changed predictions in all three comparisons**: cold/cold, warm/warm and cold/warm.
   - **Pairing:** for each prompt, cold run 1 is paired with warm run 1, and cold run 2 with warm run 2. Both pairs must agree.
   - The binomial / rule-of-three bound is computed on the **100 randomly sampled fixed-answer prompts only**. The 20 hand-chosen near-tie prompts are reported separately as a stress test and are not covered by the bound.
5. **Parsing (§6) and the leak flag (§7, §9 B1):**
   - **Probe replies:** the first standalone letter A–D is taken. No letter, a letter outside A–D, or two or more different letters → **invalid, counted as wrong**.
   - **Arithmetic replies:** the last `Answer:` line is taken. If there is none, the last integer. `Answer: UNKNOWN` → abstention, counted as not correct and reported separately. Two or more conflicting `Answer:` lines → the last one is used, and the case is flagged. Nothing parseable → invalid, counted as wrong.
   - **Leak-flag diagnostic pool:** the no-text probe runs in **Stage A (A2)** and in a dedicated **B0 probe-diagnostic pool** (non-TEST, separate from qualification).
   - **Regeneration procedure (predetermined):** a flagged template is replaced by the next template in the frozen seeded template list. It is re-checked once on the same diagnostic pool and dropped if it is flagged again.
   - All regeneration finishes **before any B1 data is generated**. **No B1 probe is regenerated after any B1 performance has been seen.**
6. **Bytes (§9 B3):**
   - **payload bytes** = the rule part only (`ID@version#hash8` with its framing, vs the original message);
   - **whole-exchange bytes** = payload + identical case text + any sender-side transmission (candidate labels, if they cross the wire).

   Both are reported. The ≥30% target applies to **payload bytes**.

### A2: 2026-10-12 (AEDT), made BEFORE any E1b stage was run (code review round 1)

**Sources:** [claude_code_1](reviews/claude_code_1.md) (Claude's code review of `6e2636d`, read only), [gpt_code_1](reviews/gpt_code_1.md) (GPT's code review of `6e2636d`; it ran the tests and built counterexamples) and [grok_code_1](reviews/grok_code_1.md) (Grok: ready to run). Credit: items 1–15 come from Claude, items 16–26 from GPT, and the B3 wording in item 1 from Grok. **No stage had been run when this amendment was written**; the only model execution was a CPU smoke test of the HF cache path with a tiny model (item 6), which is code testing, not a stage. **Binding; takes precedence over the sections it names, and over A1 where the two conflict.**

**Selection (§9 B3)**
1. **Order-aware regex number-matching baseline**, reported beside TF-IDF, BM25 and MiniLM. It scores each candidate label by the longest common subsequence of the ordered digit-numbers in the message and in the label. Selection is worded as **"selection among compact labelled candidates (4-way)"**, not a repository search (Grok). On the generated data (no model involved), regex alone picks the right entry for **70/70 plain messages** and 11/13 derived ones, but 0/13 reordered and 0/14 spelled. On plain messages, selection can be solved by number matching alone, and that must be reported next to the sender's accuracy.
2. **Harder original messages for ≥1/3 of TEST entries**, pre-registered by the frozen seed `hard_messages = 61067`. Three styles are cycled: spelled-out numbers, reordered clauses, and a derived (relative) form. Entries are sampled separately inside the C60 block and the C100-only block, so the share holds under either configuration: C60 11/30 per core family, C100 18/50, F3L 4/10. The message reaches the sender and the prose arm identically. Accuracy is also reported per message style.
3. **Selection accuracy by neighbour type** (swap, shift, swap+shift; the type is recorded on each neighbour), for the sender and each baseline.
4. **Selection trials per family** are stated: one trial per entry per sender, so C60 = 30 per core family, C100 = 50, F3L = 10.

**Probes and leak flag (§7, §9 B1; replaces A1.5's flat 0.40)**
5. **Leak flag against each probe kind's measured no-text baseline:** a template is flagged if its no-text accuracy > max(kind baseline, 0.25) + 0.15, with ≥50 no-text observations. A kind whose own pooled baseline exceeds 0.40 is a kind-level leak, and all of its templates are flagged. The B0b re-check uses the same rule. **Plausible distractors:** the entry's other constants first, then truth ±1–3; no more random 2–20 fillers. **A new "unstated" probe kind** (honest gold = "Not stated by the rule") means "Not stated" can no longer always be eliminated. Probes per entry are now 24 (F1/F2: 5 kinds; F3: 6).

**Cache (§8, A1.4)**
6. **Cold-split arm:** prefix and suffix as two evaluations in a fresh context, with no state restore. It is reported as a diagnostic (cold vs coldsplit, coldsplit vs warm) to separate "batch split" from "state restore" as the source of any change. The claim rule is unchanged (zero changes in cold/cold, warm/warm, cold1–warm1, cold2–warm2). **CPU smoke test of the HF path** (`tools/smoke_hf_cpu.py`; SmolLM2-135M-Instruct, fp32, CPU, no nf4; 10 prompts): all six comparisons were token-identical on 10/10, and warm processed fewer tokens on every prompt. This tests the code only; it says nothing about the Stage B models.
7. **"Hard" set renamed "multi-step stress prompts"** (pool `cache_stress`).
8. **Bound reconciled (replaces the §8 figure):** n = 100 sampled fixed prompts per model. "No changed prediction observed in n=100 sampled prompts; 95% upper bound on the per-prompt change probability ≈3.0% (rule of three)." Prompts are clustered within entries (10 entries per family), so the bound assumes independence and is optimistic. The 20 stress prompts are outside the bound.
9. **Invalid parses (GPT):** `None == None` is not agreement. Any invalid parse in any cache run counts as a change, is reported (`invalid_runs`), and withholds the claim.

**Logging**
10. Every rendered prompt is logged once per stage and model (`prompts_<model>.jsonl`, keyed by sha256). Rows carry `prompt_sha` and `system_turn_sha`, and each backend load logs the system-turn hash for every system prompt. The validator checks that every logged sha resolves.
11. `answer_gap_source` is recorded: `after_answer_line`, or `first_token_fallback` when no `Answer:` line appears.

**Smaller items**
12. **An invalid-reply rate >5%** (probe or arithmetic, either pair model, on B0 qualification) writes `PROMPT_FIX_REQUIRED`. B1 refuses to start (exit 8) until a prompt fix is recorded in a dated amendment (`PROMPT_FIX_AMENDED`).
13. **The manipulation-check model** is the pair model with the higher B0 core qualification score (probe + arithmetic), recorded in `config_choice.json`. It replaces "the first-listed model".
14. **mk_case substring skew (noted, not changed):** a case is rejected if its gold string appears anywhere in the entry text, the message or the question, including as a substring (e.g. gold 6 inside "16"). This skews the case distribution slightly away from golds whose digits occur in the rule. It applies equally to every arm.
15. Code hash re-recorded (`CODE_HASH.txt`).

**Bugs found by GPT, fixed with regression tests (GPT's counterexamples reproduced on `6e2636d` before fixing)**
16. **CRITICAL: the gate now scores probes against `honest_gold`** (the agreed meaning), not `gold` (the shown, possibly corrupted text). Comprehension and manipulation diagnostics keep using `gold`. On `6e2636d`, a simulated perfect reader of the shown text was accepted on 100% of honest entries with **0% planted rejection**. After the fix it gives 100% acceptance and 100% rejection. The builder now asserts that every planted entry flips enough probes that a perfect reader falls below the 0.90 bar (actual minimum: 5 of 24).
17. **Cross-process reproducibility:** a set was sorted with random keys, so the book differed between PYTHONHASHSEED=1 and 2 on `6e2636d` (`ce97f620…` vs `3a93398a…`). The distractor code now uses ordered lists, and a test builds the book in three processes with different hash seeds and requires identical sha256.
18. **`verify()` checks role/number binding:** the rule text is parsed into role → rate (member/non-member, giver/taker, first-days/later-days/fee), the question is parsed into quantities and the asked role, and gold is recomputed from the texts alone. A member/non-member rate swap passed on `6e2636d` and is caught now.
19. **The validator is stage-aware:** an empty results dir FAILS unless `--inputs-only` is given. A started stage must be complete (`.done`) or carry an explicit stop marker. A complete stage must have its expected files, keys must be unique, and the row counts are checked for B1 calibration and B3.
20. **Pilot timing** uses dedicated pilot entries, with their own neighbours checked against pilot cases. It never uses TEST entries.
21. **Neighbours are calibrated** in B1 like any other candidate (calibration probes for every neighbour of every core/F3L entry, plus F3L itself), so a gated B3 treats all candidates consistently. Neighbour acceptance is reported. This adds about 2.5× calibration probes; the B1 projection includes them (C60: 19,392 probe calls for the pair; C100: 29,760).
22. **`Dictionary.resolve`** uses membership in the published TEST dictionary (core + F3L + neighbours) and the **recorded gate decision** (`B1/accepted.json`). It never uses the hidden `kind` label. The accepted list is the gate decision itself, with no filtering by hidden label.
23. **Budgets persist cumulatively** across restarts in `results/budget_ledger.json`, keyed by allocation. B0b shares B0's allocation.
24. **Canaries are compared record by record:** any canary whose prediction changed, or that was correct in B0 and is now wrong, aborts the stage. A matching total no longer passes.
25. **Dictionary setup** counts the full predefined dictionary for the configuration (entries + all candidates).
26. **Pins:** HF commit SHAs (`revision`), GGUF repo revisions and GGUF LFS sha256 for all four Stage B models, plus the sha256 of the two Stage A GGUFs, are in `config_e1b.json` (read from the HF API on 2026-10-12). Kaggle downloads use the pinned revisions, and every GGUF is sha256-verified before it is loaded (CPU or GPU). Still to do on Kaggle before B0: memory-test the pinned package versions.

### A3: 2026-10-12 (AEDT), made BEFORE any E1b stage was run (code review round 2)

**Source:** [gpt_code_2](reviews/gpt_code_2.md), GPT's review of `b12b0ce`. It passed all 37 tests, verified the code hash and cross-process reproducibility, and **approved Stage A as diagnostics only**. Credit: GPT. Binding; it takes precedence over A2 where they conflict. No stage had been run.

1. **Dry-run harness (`tests/test_dryrun.py`):** the harness now stubs only the GGUF sha256 check and writes canary refs as the per-case dicts the real B0 produces. The full fake-backend dry run (A → B0 → B1 → B2 → B3 → validator) passes. Real runs keep the GGUF pin check and the per-record canary check, and a test asserts that both are still called. The dry run also exposed a data bug: two of the 48 unknown-ID messages were identical. The builder now uses one entry per message and asserts that all 48 are distinct, so the case data was regenerated.
2. **B0b leak recheck (replaces the A2.5 recheck rule):** a replacement template is dropped if its no-text accuracy exceeds the **absolute kind-level bar of 0.40**, or the kind-relative threshold (max(kind baseline, 0.25) + 0.15). A replacement with no observations is dropped. Under A2 alone, a replacement at 100% no-text accuracy could be kept, because a leaky kind's baseline pushed the threshold above 100%. B0b now checks the budget inside its inference loop and resumes by key.
3. **Regex baseline on the frozen B3 views (corrects the A2.1 figures):** B3 and the pre-run report (`stages.regex_report`) both use `b3_view`, which builds the same seeded per-entry candidate order. On those views regex gets: **plain 70/70, reordered 0/13, spelled 5/14, derived 8/13**. All 5 spelled hits and 7 of the 8 derived hits are tie-break guesses (tied top scores, resolved to the first-listed candidate). Ties are logged per trial (`regex_tie`) and reported, both counts and correct-by-guess. The A2.1 figures (11/13 derived, 0/14 spelled) came from a different, non-frozen shuffle and are superseded.
4. **Probe latency allowances (B1, 3 GPU-h, 20% headroom):** the mean probe latency must stay under **≈0.446 s/call for C60** (19,392 pair probe calls) and **≈0.290 s/call for C100** (29,760). Setup and the manipulation check come on top, so the real limits are slightly tighter. The A1.1 projection rule applies unchanged: if neither configuration fits every stage, report **insufficient budget** and stop. `projection.probe_latency_allowance` computes these numbers.

### A4: 2026-10-12 (AEDT), Stage A budget raised; decided after A1 only

**Decision (the user's):** the **Stage A box-CPU budget is raised from 2 h to 5.5 h** (`stageA.budget_h`). **Nothing else changes:** the workload (A1–A6, the same cases, probes and cache sets), all thresholds, the 192-token reply limit, the models, the seeds and the exit rule stay as frozen in PREREG_E1b + A1–A3.

**Reason:** the pre-registered projection after A1 (§7) gave **4.99 h**, over the 2 h cap, so the first attempt stopped as required ([STAGE_A_REPORT.md](STAGE_A_REPORT.md)). The overrun comes from per-call times (Qwen 7.68 s, Smol 4.08 s) that are longer than E1's, because the A1 prompt fix allows 192-token replies (mean 99 and 76 tokens). **The decision was made before any Stage A outcome beyond A1 was seen** (A1 is the capability smoke only; no probe, cache or exit-rule data existed). Stage A resumes from its checkpoint: the completed A1 rows are kept, and the cumulative budget ledger includes the first attempt's time. The stop marker from the first attempt is removed (it remains in git history, commit `f6bc078`).

### A5: 2026-10-12 (AEDT), proceed to Stage B; approved by the user

**Status:** frozen. The user approved the DRAFT resolution in [AMENDMENT_A5_DRAFT.md §5d](AMENDMENT_A5_DRAFT.md). It is based on the reviews [claude_A5](reviews/claude_A5.md), [grok_A5](reviews/grok_A5.md) and [gpt_A5](reviews/gpt_A5.md), with ties settled by majority. It was decided after Stage A and before any Stage B run. Nothing here changes Stage A's reported results.

**Settled:**
1. **Go to Stage B.** §7's "otherwise: go to Stage B" applies. Stage A's failure blocks only small-pair calibration.
2. **Cache:** B0 runs **uncached**. The cache claim stays withheld, and the GPU cache path is tested separately under the frozen strict rule.
3. **Leak rule:** the dedicated `*-unstated` probe templates are **excluded from the leak rule** and reported as an **abstention diagnostic** (no-text "Not stated" rate per template/kind; `leak_rule(...)["abstention_diagnostic"]`).
   - The leak rule stays as frozen for every other kind.
   - Ordinary probes whose gold becomes "Not stated" through a corruption stay in the gate.
4. **Calibration plants, builder-only:** these are the explicitly-wrong-rule calibration plants: F1/F2 `changed_constant` and F2 `deleted_negation`.
   - `changed_constant` changes **both** stated rates (+3).
   - An F2 `deleted_negation` plant's calibration-only source is oriented so the higher/lower probes also flip. This uses no rng.
   - `verify()` asserts that each such plant flips **≥ 0.30 of its probes** among the ordinary (non-unstated) probes, i.e. ≥ 8/24.
   - It also asserts that every calibration corruption type has **≥ 3** plants meeting that bar (`config_e1b.json` `a5_plants`).
5. **What the plant rebuild changed in the book:**
   - Only the 15 affected calibration plants changed, plus 2 of their source entries, their 15 calibration probe sets, and the `manip_B1` cases that are derived from them.
   - **TEST-gate plants, TEST cases, testgate probes, neighbours, unknown-ID messages, the dictionary and all Stage A groups are byte-identical**, and this was checked against the previous book.
   - Before: 13/40 calibration plants had < 8 ordinary flips. After: 0/40.
6. **UNKNOWN-implying plants** (F1 `deleted_negation`, `mismatched_definition`, and in TEST `near_miss_polarity` and `dropped_clause`) are not rebuilt.
   - Their rejection is **reported separately**: B1 `planted_reject_by_type` with an `unknown_implying` flag.
   - They will be revisited after B, and rebuilt only if the 7B pair shows the Stage A abstention pattern.
   - With the current book, a gap-filling reader would pass the 90% gate on 20/40 calibration plants. All 20 are UNKNOWN-implying.
7. **Stated limit:** answer agreement alone cannot detect a reader that silently reconstructs the intended rule. This sentence is carried in the B1 gate note.
8. **Reporting:** B1 reports planted rejection **per corruption type**.
9. **Batching, code hygiene:**
   - byte-identical prompts are generated once and reused;
   - batch composition is deterministic (prompt length, then content sha), with `batch_index/pos/n` logged;
   - padding asserts;
   - **neutral generation parameters pinned** (`repetition_penalty=1.0`, no sampling knobs; a GPT-found bug).
   - Batched output equals batch-1 on CPU even under a penalised `generation_config`.
10. **Unchanged:** the 0.90 bar, all thresholds, budgets and seeds, and A1-A4.

**To be settled after B0 and before B1** (by a dated amendment, before any B1 data):
- **(a)** The per-entry probe bar vs qualification (P4).
  - With 24 probes: P(≥22/24) is 0.564 / 0.766 / 0.884 / 0.966 at p = 0.90 / 0.93 / 0.95 / 0.97.
  - With 20 probes: P(≥18/20) is 0.677 / 0.839 / 0.925 / 0.979.
- **(b)** Reserve probe templates for kinds other than the flagged ones.
- **(c)** The B0 batch-size selection rule. Proposed: the largest size whose outputs match batch-1 on ≥ 99% of non-TEST items in the real nf4 GPU config, frozen before B1.

### A6: 2026-10-12 (AEDT), Llama-3.1-8B replaced by OLMo-2-7B for access reasons; made BEFORE any B0 data was seen

**Status:** frozen; approved by the user. B0 has not been run, so no Stage B output of any kind existed when this was decided.

1. **Reason: access only.** `meta-llama/Llama-3.1-8B-Instruct` is gated and needs a Hugging Face account and token, which the user cannot obtain. The swap is not based on any model performance or result.
2. **Change:** `llama8b` is removed from `stageB_order`, which becomes `qwen7b, olmo7b, mistral7b`. The pair is therefore Qwen2.5-7B-Instruct (Alibaba) + `allenai/OLMo-2-1124-7B-Instruct` (AI2), the substitute already pinned in A2 (revision `470b1fba1ae01581f270116362ee4aa1b97f4c84`, GGUF pins unchanged). Mistral remains the next substitute under §9 B0 (b). The `llama8b` config entry is kept for the record only.
3. **Anonymous access checked on 2026-10-12:** config.json, tokenizer and weight shards of the pinned OLMo-2 revision download with no token (HF API `gated: false`).
4. **Consequences required by the swap:** OLMo-2 (`model_type olmo2`) needs `transformers>=4.47`, so the Kaggle pin moves from 4.46.3 to **4.47.1** (bitsandbytes, accelerate and other pins unchanged; versions are still logged). The HF token is optional in the notebook. The chat template is the model's own (`<|system|>/<|user|>/<|assistant|>`, eos `<|endoftext|>`, pad `<|pad|>`), already mapped as `olmo2` in `backends.py`.
5. **Nothing else changes:** nf4 config (fp16 compute), neutral greedy generation settings (`repetition_penalty=1.0` explicit, all knobs pinned), bars, budgets (B0 2 GPU-h), pools, seeds, analysis and the GGUF fallback rule are as frozen. Non-finite logits stay fail-loud (§4).

### A7: 2026-10-12 (AEDT), B0 environment failure, version fix, Mistral removed, B0 resumed from the reserve; approved by the user (Grok reviewer signed off)

**Status:** frozen. Decided after the first B0 attempt (see [B0_REPORT.md](B0_REPORT.md)) and before any further B0 run, B0b, or any B1–B3 data.

1. **Environment failure (first B0 attempt, kernel v1, `fb423f0`).**
   - Kaggle's image is now Python 3.13 / CUDA 12.8.
   - The pinned `bitsandbytes==0.44.1` ships no `libbitsandbytes_cuda128.so` and fails on import (`No module named 'triton.ops'`), so the nf4 load test failed. The §9 fallback then set `backend.json = gguf_cuda`.
   - The pinned `llama-cpp-python==0.3.2` cu121 wheel has no cp313 build, so a CPU-only build was installed. The GGUF "CUDA" fallback therefore ran on the **CPU** (about 18–20 s per 1-token probe).
   - B0 used its full 2 GPU-h (7217.6 s) on qwen7b alone and stopped with `BUDGET_EXHAUSTED`. OLMo-2 was never loaded.
2. **Partial results already seen (disclosed).** Probe bar 0.90 and arithmetic bar 0.80, both unchanged.
   - qwen7b F1: probes 137/144 = 0.951, arithmetic 60/60 = 1.000.
   - qwen7b F2: probes 89/96 = 0.927 on 4/6 entries; arithmetic not run.
   - F3 and F3L were not run. Canaries were 20/20.
   - These numbers are published in `results/B0_run1_gguf_cpu/` and in B0_REPORT.md. **They do not enter the qualification decision** (see 5).
3. **Version fix.**
   - `bitsandbytes` is pinned to **0.47.0**. Its wheel is `py3-none` and ships `libbitsandbytes_cuda128.so`, and it no longer imports `triton.ops`.
   - `transformers==4.47.1` (A6), `accelerate==1.1.1` and the nf4 config (fp16 compute) are unchanged.
4. **Hard GPU preflight (new, fail-closed).**
   - B0 aborts with exit 9 and a `GPU_PREFLIGHT_FAIL` marker if `torch.cuda` is unavailable.
   - After every Stage B model load, `gpu_preflight` asserts the following, and aborts with exit 9 if any check fails:
     - HF path: every parameter and buffer is on CUDA, nothing is offloaded to cpu/disk/meta, and the model has bitsandbytes `Linear4bit` layers.
     - GGUF path: llama.cpp reports GPU offload support and `n_gpu_layers = -1`.
   - **A silent CPU run is no longer possible.** The result is logged as `gpu_preflight` in `stage_log.jsonl`.
5. **Backend decision (explicit).**
   - `backend.json` is **reset**, because an environment failure caused it, not the GPU's capability. B0 again **prefers the pre-registered primary path, 4-bit nf4** (bitsandbytes restored).
   - The §9 fallback rule is otherwise unchanged: if nf4 genuinely fails on the assigned GPU, GGUF via llama.cpp is used for all Stage B models, now subject to the offload preflight. The backend is never mixed.
   - Consequence: the first attempt's qwen7b records came from a different backend (GGUF on CPU). They **cannot be mixed** with nf4 records, so they are archived (`results/B0_run1_gguf_cpu/`, including its `BUDGET_EXHAUSTED` and `backend.json`) and not reused.
6. **Resume under reserve use (c), from the checkpoint.**
   - B0 continues as the same interrupted, checkpointed stage, under §2 reserve use (c).
   - Its budget is drawn from the **3 GPU-h reserve** (`config_e1b.json` `b0_resume`, ledger key `reserve`, cumulative). B0b, if needed, shares the same allocation. The exhausted B0 allocation is not reused.
   - The B0 qualification and probe-diagnostic loops now **skip records already written, by key**. The first attempt's B0 loops did not. Any interruption within this resumed run therefore continues from the checkpoint.
   - Because of 5, the resumed run starts with an empty B0 checkpoint on the nf4 backend.
   - If the reserve runs out: stop and report (§2).
7. **Mistral removed entirely (user rule).** No Mistral or other European model is used in B0, as a substitute or as a fallback.
   - `stageB_order = [qwen7b, olmo7b]`, and the `mistral7b` config entry and its template are deleted. This supersedes the substitute chain in §3, A2 and A6.
   - If qwen7b and olmo7b do not both qualify (a two-lab pair), there is **no further substitute: stop Stage B and report**.
8. **Nothing else changes:** bars, pools, seeds, N, canary rule, generation settings (greedy, `repetition_penalty=1.0` explicit, all knobs pinned), analysis and the B1–B3 budgets are as frozen.

### A8 (FROZEN): 2026-10-13 (AEDT), one bounded post-hoc B0 extension with one named candidate

**Status: FROZEN 2026-10-13 (AEDT).** All three reviewers approved freezing (`reviews/*_A8_final.md`), with Claude's two wording fixes applied. Tag `prereg-e1b-a8`. Nothing in A8 runs until all three reviewers (Grok, Claude, GPT; `reviews/*_B0.md`) approve. Then A8 is frozen by a dated, hash-pinned commit and tag `prereg-e1b-a8`, and config `b0_ext.status` is set to `"frozen"`. Until then, stage `B0x` refuses to run (exit 10).

1. **Disclosure.** E1b's B0 result is final and stays the **primary result: no qualifying two-lab 7B pair** under the free-access constraints. That result is at commit `7873596fdc127486d83c90baa65d1718585dec39` (B0_REPORT.md, run 2):
   - qwen7b QUALIFIED: F1 0.924/1.000, F2 0.924/1.000.
   - olmo7b FAILED: F1 0.840/1.000, F2 0.736/0.883.
   - Post-hoc diagnostic: OLMo's 41/41 wrong `unstated` answers were numeric.

   **This extension is chosen after seeing those results.** Every result from it is labelled a **post-hoc follow-up**, never the primary result.
2. **Selection rule.** No abstention or capability evidence for any candidate was consulted, before or after the rule was written. **Commit-order disclosure (Claude A8 #3):**
   - The rule and the candidate table were committed **together**, in `de992d1` (2026-10-13 19:08 AEDT). Git history cannot prove that the rule predates the candidate list.
   - The candidates' access, license, size and architecture metadata were looked up **before** the rule was written down. The rule's order follows the example ordering in the user's instruction (eligibility, then a different lab, then size near 7–8B, then license), which arrived before those lookups.
   - So the rule is **not** hash-provably prior to the candidate metadata. It is only prior to any performance evidence. Candidates are checked in this order, and the first rule that separates them decides:
   - (i) **Eligibility** (all must hold):
     - (a) ≥ 7B parameters (the prereg's 7B class);
     - (b) anonymous download with no token (HF API `gated: false` and `config.json` HTTP 200);
     - (c) no Mistral and no European lab (A7 §7);
     - (d) a lab other than Alibaba (two-lab pair);
     - (e) loads under the A7 environment (`transformers==4.47.1`, `bitsandbytes==0.47.0` nf4) with a chat template that has a system role;
     - (f) fits a 16 GB T4 in nf4.
   - (ii) Parameter count inside 7.0–8.0B, otherwise the nearest.
   - (iii) License, as **loosened in review round 3 (disclosed; see 3a)**: royalty-free, ungated, research use permitted. An OSI-approved license is preferred only as a lower-priority tie-break. The original draft said "OSI-permissive".
   - (iv) The most recent release within the family.
3. **Candidates considered** (all checked 2026-10-13; the reviewers' list):

   | candidate | lab | revision | gated | config.json | license | arch / transformers 4.47.1 | params | nf4 on T4 | outcome |
   |---|---|---|---|---|---|---|---|---|---|
   | `tiiuae/Falcon3-7B-Instruct` | TII (UAE) | `1e57a0ecd176c7c139f289c60a74e57f887c3dfb` | false | 200 (weights 206) | TII Falcon License (royalty-free; AUP + attribution; **not OSI-approved**) | LlamaForCausalLM ✔; template `<\|system\|>/<\|user\|>/<\|assistant\|>`, eos `<\|endoftext\|>` (11), pad `<\|pad\|>` | 7.46B | ~5.5 GB ✔ | **SELECTED**: eligible, and inside 7–8B at (ii) |
   | `ibm-granite/granite-3.3-8b-instruct` | IBM (US) | `51dd4bc2ade4059a6bd87649d68aa11e4fb2529b` | false | 200 | Apache-2.0 | GraniteForCausalLM ✔ (4.47.1 ships `granite`; template uses `strftime_now`, which 4.47.1 supports) | 8.17B | ~5.5 GB ✔ | eligible; **dropped at (ii)** (8.17B is outside 7–8B; Falcon is inside) |
   | `ibm-granite/granite-3.0/3.1/3.2-8b-instruct` | IBM (US) | `5af56291…` / `4009206d…` / `610d8c6e…` | false | 200 | Apache-2.0 | ✔ | 8.17B | ✔ | same family; dropped at (ii); (iv) would have preferred 3.3 |
   | `microsoft/Phi-4-mini-instruct` | Microsoft (US) | `cfbefacb99257ffa30c83adab238a50856ac3083` | false | 200 | MIT | Phi3ForCausalLM (longrope) | 3.84B | ✔ | **ineligible at (i)(a)**: below the 7B class |
   | Mistral-7B-Instruct-v0.3 | Mistral (FR) | — | — | — | — | — | — | — | excluded (A7 §7, user rule) |
   | Llama-3.1-8B-Instruct | Meta | — | gated | — | — | — | — | — | excluded (A6: gated) |
   | OLMo-2-1124-7B-Instruct | AI2 | — | — | — | — | — | — | — | already failed B0 (not retried) |

   **Choice: `falcon7b` = `tiiuae/Falcon3-7B-Instruct` @ `1e57a0e…`** (GGUF pin `tiiuae/Falcon3-7B-Instruct-GGUF` @ `b5eb297…` for completeness only, since the backend is fixed to nf4). The license has an acceptable-use policy and an attribution clause ("built using … technology from the Technology Innovation Institute"). It is free and needs no account, so it meets the free-access constraint.
3a. **License resolution (GPT A8, adopted; Claude A8 #1, Grok A8).**
   - **OSI status, checked 2026-10-13:** the TII Falcon License is **not** on opensource.org/licenses. Searching OSI's list for "falcon" or "Technology Innovation" returns nothing, and `opensource.org/license/tii-falcon` returns 404.
   - Under the original (iii), "OSI-permissive", Falcon would fail, and so would every candidate except Granite (Apache-2.0) and Phi-4-mini (MIT). The options were:
     - **A:** stop as "no eligible candidate";
     - **B:** openly loosen (iii).
   - **B is adopted, following GPT's resolution.**
     - (iii) becomes "royalty-free, ungated, research use permitted", with OSI as a lower-priority preference only.
     - Falcon is selected at step (ii), size, which comes before the license step. So the loosening does not change the choice relative to Granite, which loses at (ii).
     - The license is described as the **TII Falcon License (royalty-free; acceptable-use policy plus attribution)**. It is never described as Apache-2.0 or as OSI-permissive.
     - This loosening was made **after the candidates were known**, and it is disclosed here and in the final report.
   - Grok accepts this license as "free access" for this experiment.
   - **Attribution (license §6.1, verbatim):** "You shall include prominently in any public statement regarding a Derivative Work the following statement: '[name of relevant Derivative Work] is built using artificial intelligence technology from the Technology Innovation Institute'." E1b publishes measurements of the unmodified model, not a Derivative Work. Even so, every E1b report or post that shows Falcon results will carry: "Falcon3-7B-Instruct results were produced using artificial intelligence technology from the Technology Innovation Institute (TII Falcon License)."
   - **AUP** (falconllm.tii.ae/falcon3/falcon-3-acceptable-use-policy.html, read 2026-10-13). It forbids using the model, a Work or a Derivative Work:
     - (1) in violation of law;
     - (2) to exploit or harm minors or living beings;
     - (3) to generate or disseminate verifiably false information with the purpose of harming others;
     - (4) to defame, disparage or harass others.

     License §5.2 extends this to outputs used to create other works, and §5.3 says the AUP may be updated. **Publishing research results** (accuracy numbers and logged replies to synthetic rule puzzles) **conflicts with none of these.** The AUP URL and read date are recorded here, and the AUP will be re-read before any publication.
4. **Unchanged:** bars (probes ≥ 0.90 and arithmetic ≥ 0.80 per family; ≥ 1 core family); the `unstated` probes stay in qualification; the qualification, probe-diagnostic and pilot pools; scoring and parsing; the canary rule; generation settings (greedy, `repetition_penalty=1.0` explicit, all knobs pinned); the 5% invalid-reply rule; the leak rule; the nf4 config.
5. **Qwen's records are reused, not re-run, by design.** B0's result stands unchanged.
   - Stage `B0x` copies Qwen's qual, probediag, canary and **prompt log** byte-identically.
   - It verifies each file against sha256 pinned in `config_e1b.json` `b0_ext.reuse_sha256`, taken from immutable commit `7873596` with `git show`. A mismatch refuses the run (exit 12). The validator re-checks the copies.
   - **Any B1–B3 run must run both models fresh, under identical conditions** (Claude A8 #3).

   Why the reused records are comparable:
   - same backend (`nf4`, `backend.json` unchanged; B0x refuses any other backend, exit 11);
   - same A7 environment pins;
   - same frozen book, pools and seeds;
   - same code paths: the B0 per-model logic is moved unchanged into `_b0_model` and shared by B0 and B0x.

   The candidate runs the same sequence: GPU preflight, canaries, qualification, probe-diagnostic pool, pilot timings.
6. **Budget and stop rule (frozen with A8):**
   - **≤ 1.2 GPU-h**, drawn from the reserve (ledger key `reserve`, cumulative; the hard cap is also ≤ the 1.62 GPU-h remaining).
   - **One attempt, no chain, no rolling search.** If Falcon fails access, the preflight or qualification: `NO_QUALIFYING_PAIR`, stop and report. No further candidate is added under A8.
   - Budget exhaustion: stop and report (§2).
   - **Deadline fixed once (GPT A8 #1).** The first start writes `B0x/b0x_state.json` with the initial reserve usage and the absolute reserve deadline (initial + 1.2 h, capped at 3.0 h). Every restart and the retry reuse that deadline; it is never recomputed from the current ledger.
   - **Deterministic access failures are not retried (Claude final #1).** Gated, 401, 403, 404, missing revision or licence errors, at the access check or at load, mean `NO_ACCESS` and therefore `NO_QUALIFYING_PAIR`. The retry below covers only load, OOM, non-finite or crash failures.
   - **Infra-abort rule (Claude A8 #2).** An abort before **any** candidate probe is scored (load failure, preflight failure, crash) does **not** use the attempt.
     - **One** retry is allowed, with the pre-registered fallback: nf4 compute dtype **float32** instead of fp16. All else is unchanged, and the deadline is the same.
     - A second such abort means **INCOMPLETE = not qualified**.
     - **The fp32 retry is not a real second chance (Claude final #2).** fp32 compute is slower and uses more memory on a T4, and it runs under the same absolute deadline. It may not fit and may end INCOMPLETE, which counts as not qualified.
     - The compute dtype actually used is recorded per model in `B0x/compute_dtype.json` and in `stage_log.jsonl` (`compute_dtype`). The validator expects that file (GPT final).
   - **Once a probe is scored, the attempt is used.**
     - An interrupted attempt after that point counts as INCOMPLETE = not qualified (`ATTEMPT_INCOMPLETE`).
     - Hitting the cap (`BUDGET_EXHAUSTED`) also counts as **INCOMPLETE = not qualified**.
7. **If the pair qualifies:**
   - B0x writes `results/B0x/config_choice.json` (pair, leak flags, pilot-based C60/C100 projection).
   - **B1–B3 stay blocked.** The remaining reserve (< 1 GPU-h) cannot cover B1–B3. They wait for a new budget period and a further dated amendment that freezes the pair choice.
   - That amendment uses a **fresh TEST pool**: newly generated with new pinned seeds and a new book hash, disjoint from every pool seen so far. The current TEST pool has not been touched by any model, but the extension is post hoc, so a fresh one is used (Claude).
8. **Code (not run):** `stage_B0x`, a `falcon7b` config entry, a `falcon3` template entry, and `b0_ext` config with `status: "draft"`. Tests cover:
   - the refusal while draft;
   - pin verification against `7873596`;
   - the hash-mismatch refusal;
   - byte-identical reuse including the prompt log;
   - the single candidate;
   - a deadline that stays fixed across a restart with 0.5 h more reserve spent;
   - the single fp32 retry;
   - a second abort or a post-scoring interrupt counting as not qualified;
   - a full B0x → validator run (B0x registered in the validator's stages, expected files, uniqueness, prompt resolution and reuse-hash checks), including a duplicate key, a missing prompt log and a tampered reused file. The Kaggle notebook defaults to `E1B_STAGE=B0x` at tag `prereg-e1b-a8`, which does not exist until A8 is frozen. **The kernel has not been pushed.**

### A9 (FROZEN 2026-10-14; revised after review round 4 → "4b"): 2026-10-14 (AEDT), B1–B3 for the post-hoc pair Qwen2.5-7B + Falcon3-7B-Instruct

**Status: FROZEN 2026-10-14 (AEDT).** Tag `prereg-e1b-a9`. Config `a9.status = "frozen"`; the code hash is recorded in `CODE_HASH.txt`.
- **Final votes:** Grok and GPT voted YES at `b3edce6` (`reviews/grok_A9_final.md`, `reviews/gpt_A9_final.md`; both are summaries).
- **Claude:** no A9 review is on file. A9 was frozen on the two votes at Stefan's instruction. This departs from the three-reviewer wording of the earlier drafts and is disclosed here.
- **Nothing in A9 has run, and no Kaggle kernel has been pushed.** Every stage still refuses to run without `E1B_GO=<stage>`, which is set only on Stefan's explicit go.

Round-4 reviews: `reviews/grok_A9.md` and `reviews/gpt_A9.md` (both are summaries). Both said yes-with-changes. The changes are applied below, and **4b** marks what changed.

1. **Labels (carried into every B result).**
   - The primary E1b B0 result stays **NO QUALIFYING PAIR** (`7873596`).
   - The pair `qwen7b` + `falcon7b` qualified only in the **post-hoc** A8 extension (B0x, `e1b-stage-b0` v3 at `e258b45`; B0_REPORT.md at `781b397`). Every B1, B2 and B3 number, table and post is labelled **"POST-HOC follow-up (A8 pair)"**. None is ever called the pre-registered primary result. Each stage logs this label (`stage_log` event `a9`).
   - Every report, table or post that shows Falcon results carries, verbatim: "Falcon3-7B-Instruct results were produced using artificial intelligence technology from the Technology Innovation Institute (TII Falcon License)." (config `a9.attribution`). The AUP is re-read before any publication.
   - The duplicate kernel `devamped13/e1b-stage-b0x` (pushed by an automation on 2026-10-14) is excluded. Its output is never used or looked at.
2. **Fresh, untouched TEST pool.**
   - The A9 book `data/cases_e1b_a9.json` is a full rebuild with **new pinned seeds** (`a9.seeds`: generator 81062, probes_fresh 81063, sanity_subset 81064, cache_sample 81065, bootstrap 81066, hard_messages 81067).
   - **4b: rebuilt for branch balance.** Its sha256 is now **`19f8d46da3fffa8f9502e28d8e0adde960f3a0a6683d0e0dc747c04b24869f41`**, pinned in `a9.book_sha256` and committed before any run. It replaces `bc0df849…`, which never ran. Every A9 stage re-checks the sha (exit 15), and so does the validator.
   - **Branch balance (4b, GPT A9 #2):** every TEST entry has exactly half its cases on each answer branch: F1 member / non-member, F2 x-pays / y-pays, F3L permit / no permit. At L4 that is 2 + 2. This is asserted in `a9.check_branches`. The frozen book is still reproduced byte-identically (tested).
   - **Asserted on the rebuilt book:**
     - Disjointness from the frozen book (`a9.check_fresh`): no case text, entry text or entry id is shared, except the 20-prompt canary pool, which the B0x canary references need.
     - All builder assertions, including gold recomputed from text, load-bearing neighbours on exactly the cases used, plant flips and pool disjointness.
3. **Both models fresh, under identical conditions.** `a9.reuse = []`.
   - No B0/B0x record is reused as a result.
   - Both models run on the same items, with the same backend (nf4, fp16 as in B0x), A7 pins, prompts and parsing, generation settings and batch rule.
   - Canaries are checked against the B0x references.
   - The manipulation check runs on `falcon7b`, the higher B0x qualification score.
4. **Budget (new budget period).** Stefan's Kaggle has about 16 GPU-h left this week. A9 caps the total at **≤ 12.0 GPU-h** (`a9.total_cap_h`).
   - **4b, corrected projection (GPT A9 #1).** Each call type uses the latency measured for its mode:
     - **batch-8 per-item receiver** for batched receiver calls (B2 main + sanity, B3 receivers, the B1c batched arithmetic): Qwen 2.81 s, Falcon 5.06 s;
     - **batch-1 arithmetic** for batch-1 calls (B1 manipulation check, B2 paired id_oracle, the 3 cold runs per B2 cache-test prompt, the B1c references): from the B0x qualification rows, 4.65 / 6.37 s;
     - **warm** for warm runs (2 per cache prompt, plus B2 prefix timing): 4.29 / 6.76 s;
     - **batched probe** 0.365 / 0.537 s, **batch-1 probe** (B1c) 0.451 / 0.532 s, **sender** (batch 1) 0.477 / 0.656 s;
     - **setup** 247 / 289 s per load. **B3 loads each model twice**, so it is charged two setups.
   - The B2 warm-prefix timing is budgeted even though it runs only if the cache claim is allowed, so the projection is conservative.
   - **Cap rule:** each stage's cap = projection / 0.8, rounded up to 0.05 h. **Ladder (4b reordered: drop the exploratory F3L arm before cutting cases; cases per entry stay even, for branch balance):** the first level whose summed caps (B1c + B1 + B2 + B3) are ≤ 12.0 is used. Nothing else is cut.

   | level | entries | TEST cases / entry | F3L arm | B1c | B1 | B2 | B3 | Σ projected | Σ caps | fits ≤ 12? |
   |---|---|---|---|---|---|---|---|---|---|---|
   | L0 | C100 | 10 | yes | 0.50 | 4.18 | 14.92 | 5.14 | 24.74 | 31.00 | no |
   | L1 | C60 | 10 | yes | 0.50 | 2.76 | 10.72 | 3.38 | 17.35 | 21.80 | no |
   | L2 | C60 | 10 | **no** | 0.50 | 2.52 | 9.66 | 2.94 | 15.62 | 19.65 | no |
   | L3 | C60 | 6 | no | 0.50 | 2.52 | 6.62 | 1.89 | 11.53 | 14.55 | no |
   | **L4** | **C60** | **4** | **no** | 0.50 | 2.52 | 5.10 | 1.37 | **9.48** | **12.00** | **yes** |
   | L5 | C60 | 2 | no | (not reached) | | | | | | |

   (projected GPU-h per stage; caps for L4: **B1c 0.65, B1 3.20, B2 6.40, B3 1.75; total 12.00 ≤ 12.0**, which leaves about 4 GPU-h of the week unbudgeted)

   - **Chosen: L4** = C60 (30 F1 + 30 F2 honest core entries, 24 calibration plants, 40 TEST-gate plants), **4 TEST cases per entry (2 per branch)**, and **the F3L arm not run**. F3L is reported as "not run (budget, A9 L4)".
   - **Reduced power, flagged (Grok A9).** TEST is 240 items per condition per model, against 600 at C60 × 10. The 60 entries carry most of the power, but every per-case and per-cell interval is wider. This is stated next to the headline.
   - **The total is at the bar.** The L4 caps sum to exactly 12.00. If any stage hits its cap, the stage is INCOMPLETE; nothing is borrowed from another stage or from the headroom.
5. **Stop rules, fixed caps, infra aborts, order and launch gate.**
   - **Fixed caps:**
     - Each stage has its own cumulative ledger allocation (`A9_<stage>`).
     - Its cap is written to `results/<stage>/a9_state.json` at the first start and never recomputed.
     - Hitting the cap writes `BUDGET_EXHAUSTED`, and the stage is INCOMPLETE.
     - A start is refused once the A9 allocations together reach the total cap.
   - **Infra retry:**
     - A stage may start at most **1 + 1** times. The retry is for an infrastructure abort (load, OOM, non-finite, crash, session loss).
     - The retry resumes by key, under the same cap and config.
     - A third start: `ATTEMPT_INCOMPLETE` (exit 17).
     - **4b: resume never duplicates rows.** B2's `unknown.jsonl` now skips completed keys. This is tested with an interrupt, then a resume, then the validator.
   - **4b: terminal markers.** `NO_ACCESS` (a deterministic access error, written by the stage guard), `BUDGET_EXHAUSTED`, `CANARY_FAIL` and `ATTEMPT_INCOMPLETE` are terminal. The stage never restarts (exit 18).
   - **4b: prerequisites are checked before any start is consumed:**
     - the go and the frozen status;
     - the book sha;
     - no terminal marker;
     - **stage order** B1c → B1 → B2 → B3: every earlier stage must have `.done`, else exit 19;
     - a passing B1c rule (exit 16);
     - the total cap.

     A refused prerequisite leaves `a9_state.json` untouched.
   - **Launch gate (Stefan's rule):** no automated, scheduled or proactive launches.
     - Each stage refuses unless `a9.status == "frozen"` **and** `E1B_GO` equals that stage's name (exit 14). A go for one stage never starts another.
     - The Kaggle runner has no default stage. `E1B_STAGE` and `E1B_GO` are set by hand, per stage, only after Stefan's explicit go.
     - No agent, script, cron or loop may push a Kaggle kernel for E1b.
   - **No Mistral** (and no other European model). The pair is fixed.
6. **Items deferred "until after B0":**
   - **(a) Per-entry gate: DROPPED for B2/B3 (4b; decision by Stefan, the PI).**
     - **This decision was made after seeing the qualification scores** (Qwen 0.924 / 0.924, Falcon 0.958 / 0.972 on F1 / F2) and is disclosed as such.
     - **Reason:** E1b's question is whether the ID-as-text channel communicates better than prose, not whether a checked repository exists.
     - **What changes:**
       - B2 and B3 run **ungated**, as the pre-declared ungated comparison (§9 B1, "If B1 fails").
       - Config `a9.gate_policy = "ungated"`. B3 never filters the dictionary by the B1 decision, whatever B1 finds, and logs `a9_gate_dropped`.
     - **What is not claimed:** no checked repository, no corruption protection and no gate-filtered result.
     - **What stays:**
       - B1 still runs in full: calibration, TEST-gate and the manipulation check.
       - The per-entry bar (each model ≥ 0.90 and agreement ≥ 0.90, i.e. ≥ 22/24) and both gate bars are computed and **reported descriptively**, with the "met in sample" / "met at 95% confidence" wording.
       - A per-entry exact binomial test is also reported descriptively. The independence figures (P(≥ 22/24) = 0.726 for Qwen, 0.922 / 0.971 for Falcon F1 / F2) only illustrate how strict the bar is. They are not a forecast, since probes are not independent.
     - **Reviewer positions (recorded):**
       - **GPT:** keep the ≥ 22/24 bar unchanged, report the eligibility failure, and run the ungated comparisons with limited claims.
       - **Grok:** change the bar or drop the gate explicitly; keeping a bar known to fail is weak.
       - **Stefan chose to drop the gate.** Earlier tie-breaks went to GPT. This one is a PI decision, not a tie-break.
   - **(b) Reserve probe templates: deferred.** Only `F3L-waive-v0…v3` were flagged (a kind-level leak), and F3L does not run at L4. B0b is not run. If F3L is restored later, the A1.5 procedure applies.
   - **(c) Batch-size rule: B1c (4b, GPT A9 #4, Grok).**
     - **Items:** per pair model, **120 non-TEST items from the A9 qualification pool**, stratified over both core families and both batched downstream paths:
       - **60 arithmetic** (30 F1 + 30 F2);
       - **60 with-text probes** (30 F1 + 30 F2).
     - Each item is run at batch 1 and at batch 8.
     - **Pass rule:** **parsed decisions** (answer or letter) must match on ≥ 99% **per path**, which is 60/60 each, for **every expected model**.
       - The expected models, counts and paired keys must be present, with no duplicates.
       - A `None` decision never counts as a match, and an empty mapping fails. Both are regression-tested (GPT bug).
       - Full-token agreement is a diagnostic only.
     - Pass: batch 8 for B1–B3. Fail: stop and report for this budget period.
     - **Not covered:** B3 sender selection is a **single batch-1 run per entry**, and the B2 cache test and warm runs are batch 1 (§8).
7. **Unchanged:** all bars and thresholds (now reported descriptively where 6a applies); scoring and parsing; the canary rule; the 5% invalid rule; the leak rule; B2 conditions, the cache rule and the comparisons; B3 selection, baselines, receivers and denominators; and the generation settings.
8. **Code (tested; not run on any GPU):**
   - `e1b/a9.py`:
     - gate, book build/pin/freshness and branch-balance checks;
     - corrected call counts by latency type, with loads;
     - ladder, batch rule, binomial helper.
   - `cases`: optional reserved texts and ids, plus optional branch forcing, with frozen defaults.
   - `tools/build_a9_book.py`.
   - `stages`:
     - `stage_B1c` (stratified);
     - `_a9_start` (prerequisites before a start, order, terminal markers);
     - `_a9_guard` (access errors → `NO_ACCESS`);
     - B2 unknown-row resume;
     - B3 ungated under `a9.gate_policy`.
   - Validator: B1c and the A9 book pools.
   - Kaggle runner: no default stage.
   - `tests/test_a9.py` (18 tests):
     - gate and go;
     - order and prerequisites without consuming a start;
     - terminal markers, and an access error as terminal;
     - book pin, determinism, freshness, branch balance and tamper tests;
     - the ladder order and the frozen level and caps;
     - batch-rule regressions;
     - B1c stratification;
     - the start limit;
     - B2 interrupt → resume → validate;
     - a full fake-backend B1c → B3 → validator run, with B3 ungated.

     **All 95 tests pass.**

**A9 errata (non-blocking, GPT final):** B1's projection averages both models' batch-1 latency for the manipulation check, which runs on Falcon only. Using Falcon's batch-1 latency (6.37 s) adds about 0.029 h, so B1 projects about 2.55 h. The B1 cap stays **3.20**, and the total stays 12.00. Neither the frozen level nor any cap changes.

---

### A10 (DRAFT, NOT FROZEN): 2026-10-15 (AEDT). Post-hoc diagnostic completion of B3, Falcon sends → Qwen receives

**What A10 is (GPT A10 #1).** A10 is a **post-hoc diagnostic completion on a TEST set we have already seen.** It was written **after** we saw the A9 B3 results, including the exploratory first-letter re-parse that gave 56/60.
- **The A9 B3 verdict stands as the primary result: POC FAILED** (§10; both directions inferior).
- A10 results are **secondary**, are labelled `POST-HOC DIAGNOSTIC COMPLETION (A10)` everywhere, and **cannot overturn the two-direction claim**, whatever they show.
- A9's results, summaries and reports are not edited, apart from the factual correction in item 7.
- The gate stays dropped (A9 4b), so there is no checked-repository claim.

**1. The defect.**
- Under the frozen sender settings (4 new tokens), Falcon3-7B answered all 60 B3 sender prompts as `X) F1` or `X) F2`: the option letter, then the start of the candidate ID (`F1-1434@v1#…`), cut off at the token limit.
- The frozen `parse_letter` treats the `F` of `F1` as a second standalone letter, so it returned `invalid_multiple` for all 60. No Falcon pick was valid, and the Qwen receiver was never called on id_selected (`sender_invalid` × 240).
- So that direction tested nothing about communication.

**2. Parser fix (GPT A10 #3), `parsing.parse_letter_a10`.**
- It deletes **candidate-ID fragments** first: `F1`, `F2` or `F3L`, optionally followed by `-NNNN`, `@vN` and `#hash`, possibly truncated, and only as a whole token.
- It then applies the frozen `parse_letter` **unchanged**:
  - a bare `F1` / `F2-1434` → `invalid_none`;
  - `F` or `E` → `invalid_letter`;
  - two different option letters (`B or C`, `B) F1 C)`) → `invalid_multiple`.
- **There is no broad first-letter rule.**
- The frozen `parse_letter` is kept for every A9 result.

**3. Unchanged.**
- The sender prompt, the generation settings (greedy, `sender_max_new_tokens = 4`), the candidate order (`b3_view` seeds) and the TEST book (`19f8d46d…`).
- The cases, scoring, the −0.05 non-inferiority margin, the paired cluster bootstrap (2000 resamples, A9 bootstrap seed) and the analysis code (`summarize_B3`, unchanged).
- This replaces the earlier idea of raising max tokens or changing the prompt. That idea is dropped.

**4. Design (GPT A10 #4).**
- **(a) Sender: no new sender call.**
  - All 60 **archived** Falcon replies (`B3/select_falcon7b.jsonl`) are re-parsed with `parse_letter_a10`.
  - Every reply is kept byte for byte (the validator checks this), alongside its frozen parse.
  - No sender attempt is regenerated or chosen.
- **(b) Receiver: only the missing arm is run.** qwen7b answers the 240 `id_selected` items for the re-parsed picks. It is a fresh load with canaries, B1c batch 8, and the frozen receiver prompt and settings.
- **(c) Prose arm: reused, not rerun.**
  - The 240 `prose` rows of `B3/exchange_falcon7b_to_qwen7b.jsonl` are copied verbatim, with `reused_from`, and their rendered prompts are copied too.
  - Reason: rerunning prose would add a second, selectable prose measurement.
  - Known limitation: the id_selected arm runs in a later session, with different batch neighbours from the prose arm. B1c's 120/120 batch conformance and B2's 20/20 paired identity bound that risk but do not remove it.
- **(d) Pinned fingerprints.** Every reused input carries a pinned sha256 (`a10.reuse_sha256`); B3f and B3r refuse (exit 15) and the validator fails on any mismatch:

| Reused file | sha256 |
| --- | --- |
| `B3/select_falcon7b.jsonl` | `6d2494fb966d9304d880960dd10e23d1e4606c901c31fd6f830be04c2737ce06` |
| `B3/exchange_falcon7b_to_qwen7b.jsonl` | `cd7121960fa186fde50a8437110068f052882d9775f76678787f485e5d77d1be` |
| `B3/prompts_qwen7b.jsonl` | `d0cdca2c15a7eae44298e7010672ccd1a8f6e0b56e6e49d5d9cc797395b1fd17` |
| `B3/select_qwen7b.jsonl` (unchanged direction, analysis input) | `d7a301d2be10c25c9806424f830378ac329ddef2a0f3585fb40a73c2b4be4d01` |
| `B3/exchange_qwen7b_to_falcon7b.jsonl` (same) | `0d89fe4d9a1239035ee9553b1ca6bf124a808f66f948bf8b7552c5276b335f96` |
| `B3/summary.json` (A9 verdict) | `42cf348edc8ae3c652a44d38f713839b4b1f706dfa2211235748583462ea58e7` |

  The TEST book is still checked against `a9.book_sha256`.
- **(e) Analysis.** The unchanged `summarize_B3` runs on the A10 Falcon→Qwen files, alongside the unchanged A9 Qwen→Falcon files. **Only the Falcon→Qwen block is reported**, as secondary.
- **(f) Dropped (GPT A10 #4):** the optional symmetric re-run of the Qwen-sends direction. Its frozen parse is identical under A10 (60/60 same), so it would only buy a second draw.

**5. Checks before the freeze (GPT A10 #5).**
- **Offline pilot, done** (`tools/a10_offline_pilot.py` → `a10_offline_pilot.json`). Both parsers were applied to all 22,296 archived letter-parsed replies of both models (B0x, B1c, B1 probes; B3 sender):
  - **22,236 identical**;
  - **0 changed decisions**;
  - **60 rescued**: all 60 Falcon B3 sender replies, of which 56 picks are correct (exploratory; already seen).
  - The 60 Qwen sender replies parse identically.
- **B3f, a non-TEST sender format check (GPU, small; may run before the freeze on `E1B_GO=B3f`).**
  - Both models get the frozen sender prompt and settings on the A9 **pilot** entries, which are never TEST: 2 per core family, each in 6 seeded candidate orders, so 24 views per model.
  - Raw replies are logged and parsed by both parsers. Neither the TEST set nor any receiver is used.
  - This is the only way to see Falcon's sender formatting on non-TEST data: B0x's pilot sender calls did not keep the text.
  - **Reviewers see B3f before the freeze.** The proposed bar is: A10 gives a valid parse for at least 22/24 replies per model, with 0 changed frozen decisions. If it fails, A10 is not frozen as written.
- **Unit tests** (`tests/test_a10.py`): unambiguous replies, candidate-ID fragments, bare fragments, conflicting choices, no changed frozen decision, the offline invariants above, launch gates, tampered reuse, the one-start rule, caps, and a fake-backend B3f → B3r → validator run on the real archived A9 results.

**6. Budget, attempts and launch (GPT A10 #6).**
- **Results** go in separate directories, `results/B3f` and `results/B3r`. A9's `results/B3` is read only.
- **One authorised start per stage** (`a10.max_starts = 1`). There is no infra retry; a second start writes `ATTEMPT_INCOMPLETE`. The terminal markers are A9's.
- **Persistent caps**, in their own ledger allocations: B3f **0.25 h** (`A10_B3f`) and B3r **0.50 h** (`A10_B3r`). The A10 total cap is **1.0 h**, and the cumulative A9 + A10 cap is **12.0 h**.
  - A9 has used 6.15 h, so the worst case is 6.90 h.
  - A stage refuses (exit 6) if its cap would break either limit. Every check runs before a start is consumed.
- **Estimates:**
  - B3f: about 0.15 GPU-h (two model loads of ~170 + 145 s, canaries ~70 + 135 s, 48 sender calls at ~0.55 s).
  - B3r: about 0.21 GPU-h (one Qwen load ~170 s, canaries ~70 s, 240 receiver calls at ~2.1 s at batch 8).
  - Total about **0.36 GPU-h**.
- **Gates:**
  - `B3r` refuses unless `a10.status == "frozen"` and `E1B_GO == "B3r"`, A9 B3 is `.done`, and B3f is `.done`.
  - `B3f` needs `E1B_GO == "B3f"`.
  - **A10 is frozen only after Grok and GPT review. Both stages launch only on Stefan's explicit go**, with no automation and no Mistral.
  - **Code hash.** A9's frozen hash `d0203f22…` stays pinned by the tag `prereg-e1b-a9`, and every A9 result logs it. `CODE_HASH.txt` now records the A10 draft code, `543a369c…`; B3f runs at that draft commit, under the `run.sh` hash check. At the freeze, `a10.status` becomes `frozen`, which changes the config and therefore the hash; the new hash is recorded and the commit is tagged `prereg-e1b-a10`.

**7. Correction to B3_REPORT (GPT A10 #2), verified from the raw results at `3973107`.**
- In Qwen→Falcon id_selected, there were **37 errors**: **36 came from the 9 wrong selections**, and **1 (F2-3288) happened despite a correct selection**.
- The earlier wording ("every loss came from the wrong picks") was wrong and is corrected in `B3_REPORT.md`.
- The forum posts of 2026-10-15 06:23 AEDT carry the same wrong wording; a correction is pending Stefan's go.

**8. Reporting.**
- `B3R_REPORT.md` will carry: the A10 label, the unchanged A9 verdict first, the parse paths (frozen vs A10) for all 60, the selection accuracy and baselines, the pipeline accuracy vs the reused prose arm with its CI and label, and the bytes and costs.
- It also carries the TII attribution line: Falcon3-7B-Instruct results were produced using artificial intelligence technology from the Technology Innovation Institute (TII Falcon License).
