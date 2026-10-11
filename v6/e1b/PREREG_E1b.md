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
