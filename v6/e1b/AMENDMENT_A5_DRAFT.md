# DRAFT Amendment A5: proceed to Stage B (B0 qualification) after Stage A

**Status: DRAFT for review by Grok and GPT. It is not merged into the frozen `PREREG_E1b.md`, and nothing in it has been run.** Date: 2026-10-12 (AEDT). Basis: Stage A results at commit `73a528b` ([STAGE_A_REPORT.md](STAGE_A_REPORT.md)). Scope, budgets and models are **unchanged**; no new models are added.

## 1. What the Stage A exit rule says, quoted exactly (PREREG_E1b §7)

> **Stage A → B rule:** the small pair "clears 0.90" if each model and their agreement reach ≥0.90 on ≥**80%** of honest entries **and** A4 shows that the plants change Qwen's answers on ≥70% of the changed-gold cases. If so, the small pair may be calibrated in a **separately pre-registered amendment, still with no repository claims**. Otherwise (expected): go to Stage B. Stage A results are published either way.

**Reading it literally:**
- **Failing the rule does not block Stage B.** The rule's "otherwise" branch says **"go to Stage B"**, and it marks that outcome as **expected**. Stage A measured 0/18 honest entries passing (need ≥80%) and an A4 follow rate of 0.425 (need ≥0.70), so the rule sends us to Stage B.
- **What the failure does block is calibrating the small pair** (Qwen-3B + SmolLM2-1.7B). That path is closed, and nothing here proposes reopening it.
- **The rule does not certify the 7B pair.** Whether the 7B pair can do the probes is decided only by B0 qualification (§9), on its own data.
- **Two caveats against overstating:**
  - Stage A did not finish. It stopped on `BUDGET_EXHAUSTED` with A6 partial, and the stage has no `.done`. The exit rule depends only on A2 and A4, both of which completed (1152/1152 probe rows per model, 60/60 A4 rows), so the verdict is computable. But Stage A as a whole is incomplete.
  - The prereg's §2 stop rules for Stage B (no qualifying two-lab pair, assertion or validator failure, non-finite logits, budget) contain no condition tied to Stage A's outcome.

**Why this amendment exists anyway:** §7 already directs us to Stage B. This draft does not change that rule. It records, before any GPU use, what Stage A's findings require us to apply or fix first, so that the decision and those conditions are reviewed in advance rather than improvised.

## 2. Justification (original design intent)

- **Stage A was pre-registered as a no-claim smoke and diagnostic stage** (§1, §7; "Stage A: small models, smoke and diagnostic only, with NO repository claims"). Its failure is informative (small models do not comprehend the rules at the 0.90 bar), but it supports no claim about the 7B pair either way.
- **B0 qualification is an independent test of the 7B pair** on its own qualification pool: ≥0.90 rule comprehension and ≥0.80 arithmetic per family, plus precision canaries, an access check, the nf4 load test and the GGUF fallback. If no two-lab pair qualifies, Stage B stops and we report. **So proceeding to B0 cannot by itself produce a positive claim; it can only test the 7B pair.**
- The design always expected the small pair to fail (the exit rule's "(expected)"); Stage B was the planned route.

## 3. What must be applied or fixed before any Stage B GPU work, because of Stage A's findings

### 3.1 Leaky probe kinds: use the frozen procedure, no ad-hoc edits
- **Stage A finding:** kind-level no-text leaks on **F1-unstated (0.625), F2-unstated (0.542) and F3s-unstated (0.729)**. Other kinds are near chance. This looks **structural**: the honest gold for "unstated" questions is always "Not stated", which a model can guess without the text.
- **Action: none beyond what is frozen.** B0 runs its own probe-diagnostic pool (no entry text) on the 7B pair. The A2.5 / A3.2 leak rules flag templates, including a whole kind whose pooled baseline exceeds 0.40. B0b replaces flagged templates from the frozen reserve list and re-checks them on the same pool, dropping any that still leak under the absolute 0.40 bar. All of this finishes **before any B1 data**.
- **No templates are edited by hand, and Stage A's flags are not imported into B.** The 7B pair's own B0 measurements decide.
- **Expected consequence, stated in advance:** if the unstated kind leaks for the 7B pair too, its replacements are likely to be dropped as well. That leaves 20 probes per entry (F1/F2: 4 kinds × 5; F3: 5 × 4), which still meets the ≥20 minimum. Reviewers should confirm this outcome is acceptable rather than a reason to redesign.

### 3.2 Cache claim withheld; B runs uncached unless the GPU runtime passes on its own
- **Stage A finding (CPU, llama.cpp):** cold/cold and warm/warm were stable (0/100), but **cold/warm changed predictions on Qwen 6/100 and Smol 16/100** (Smol also 4/20 stress prompts). Coldsplit matched warm, so the source is splitting prefix and suffix into separate evaluations, not restoring state.
- **Action:**
  - No CPU cache claim (frozen rule).
  - Stage B accuracy and cost claims use **uncached** runs. A cached claim is allowed **only if B2's GPU cache check passes on its own** (zero changes in every required comparison and zero invalid parses; batch-1 only; §8 + A1.4 + A2.6–9).
  - The CPU result does not carry over in either direction.

### 3.3 A6 cost data incomplete
- **Finding:** A6 has qwen3b 218/480 and no smol17 rows.
- **Action:** no CPU cost or efficiency statement from Stage A. A6 is reported as partial. Stage B cost tables come only from Stage B measurements.
- **Lesson for budgeting:** Stage A used 5.5 h against its original 2 h estimate, because 192-token replies made calls about 3× slower than E1's. The same effect applies on GPU (see 3.4).

### 3.4 Per-call latency vs the C60/C100 allowances; batched generation is a conformance gap
- **The frozen projection rule (A1.1) is unchanged.** C100 is chosen only if every stage projects at ≤80% of its budget; otherwise C60 is checked the same way; otherwise the run reports **"insufficient budget"** and stops after B0. N is never shrunk.
- **Mean per-call allowances implied by the current call counts** (80% of budget, setup excluded):

  | Stage | C60 | C100 |
  |---|---|---|
  | B1 probes (A3.4) | ≤0.446 s | ≤0.290 s |
  | B2 (8,040 / 11,240 calls) | ≤0.72 s | ≤0.51 s |
  | B3 (2,940 / 4,620 calls) | ≤4.9 s | ≤3.1 s |

- **Risk to state up front:** B2's allowance requires about **0.7 s per arithmetic call with up to 192 generated tokens** (mean ~80–100 tokens in Stage A). A 7B nf4 model on a T4 **at batch 1** cannot do that. If generation stays at batch 1, B0's projection will almost certainly return **"insufficient budget"**.
- **Conformance gap (implementation, not design):** PREREG §9 says **"Batched generation is used for B1–B3"**, and the A1.1 projection uses "the batch size actually used". **The current code generates at batch size 1 only.** Before any GPU work this must be **implemented to match the frozen spec**:
  - batched greedy generation for the non-cache paths in B1–B3, with the same prompts, parser and decoding;
  - the cache test stays batch-1, as frozen;
  - the batch size is logged and the pilot timing is measured at that batch size;
  - a regression test shows that batched outputs equal batch-1 outputs on a CPU smoke model, or the differences are reported.

  This is a code change and will re-record the code hash. **It changes neither scope nor budget.**
- If, even with batching, neither C60 nor C100 fits, the pre-registered outcome is **"insufficient budget" → stop and report**.

### 3.5 Outstanding infrastructure items (before B0)
- **Memory-test the pinned packages on Kaggle:** `transformers 4.46.3`, `bitsandbytes 0.44.1`, `llama-cpp-python 0.3.2` (cu121). Load each Stage B model in nf4 one at a time on the assigned GPU type, record peak memory, and confirm the nf4 load test and GGUF fallback path. Note that transformers 4.46.3 warns its legacy tuple KV-cache format will be removed in 4.47; the version stays pinned. This counts against B0's 2 GPU-h; it is not a new allowance.
- **Kaggle CLI auth on the box:**
  - The box environment has `KAGGLE_KEY` but no `KAGGLE_USERNAME`/`KAGGLE_API_TOKEN` and no `~/.kaggle/kaggle.json`, and the `kaggle` CLI is not installed.
  - Fix: install the CLI in a venv, and supply the username plus key through environment variables (or a `kaggle.json` with mode 600) built from the existing secret, **without printing, logging or committing the key**.
  - Verify with a read-only command (e.g. `kaggle kernels list --mine`).
  - Until this works, notebooks can be pushed through the Kaggle web UI; nothing in the prereg depends on the CLI.
- **HF access:** Llama-3.1-8B is gated. B0's access check runs first; substitutes follow the frozen order (OLMo-2-7B → Mistral-7B). No new models.

## 4. Unchanged (explicit)
- Budgets: B0 2, B1 3, B2 2, B3 5, reserve 3 GPU-h, with the same permitted reserve uses.
- Models and substitute order, thresholds, the 192-token reply limit, seeds, the case data and the frozen parsing rules.
- No interim looks.
- The C60/C100 rule.
- No repository claim if B1 fails.
- Stage A remains diagnostic only.

## 5. Reviewer input received

- **GPT ([gpt_stageA](reviews/gpt_stageA.md), on `73a528b`):** proceed to **B0 uncached**, **keep the leak checks**, and **test the GPU cache path separately**. Also: A4's low follow rate is an abstention failure (17/17 numeric follows, 0/23 UNKNOWN), the A2 planted accuracy is scored against the shown text, and the CPU cache divergence is localised to one-chunk vs prefix/suffix chunking (coldsplit = warm on 120/120). All verified against the raw rows; see the STAGE_A_REPORT corrections.
- **Claude ([claude_stageA](reviews/claude_stageA.md)): proposals for the reviewers, NOT adopted. Each needs a dated amendment before B.**
  - **P1, gap-filling guarantee (builder):** require every planted entry to be rejected by a reader who answers the honest way wherever the shown text leaves a gap, with a margin of ≥8/24 flipped probes.
    - Verified context: the current calibration pool has **16 planted entries with only 5/24 flipped probes** (changed_constant 13, deleted_negation 3). They would have to be regenerated. TEST-gate entries have 15–20 flips.
  - **P2, abstention prompt:** an exploratory abstention-instruction prompt test on Qwen-3B CPU (~40 calls, logged as exploratory, no claims). The chosen prompt would be frozen by a dated amendment before B. **Not run; it awaits approval.**
  - **P3:** B1 reports planted rejection **per corruption type**. This is reporting only.
  - **P4, entry bar vs qualification (decide with P1):** at 24 probes the 0.90 bar means ≥22/24, and P(pass | p = 0.90) = 0.564 (verified; 0.318 for two independent models). Options:
    - more probes per entry;
    - a binomial entry test (e.g. a lower confidence bound ≥ a fixed value);
    - a higher qualification bar (e.g. ≥0.95 per probe, where P(≥22/24) = 0.884).
  - **P5, cache:** use **warm vs cold-split as the primary state-restore check** and report cold vs split as chunking sensitivity, keeping the strict rule alongside. Stage A CPU: warm = cold-split token-identical on 120/120 for both models; chunking noise floor 6% (Qwen) / 16% (Smol) of predictions.
  - **P6:** treat the *-unstated no-text "leaks" as an **abstention diagnostic**, excluded from the leak rule. This conflicts with §3.1, which keeps the frozen B0b procedure; reviewers decide.
  - **P7:** report the share of rows whose first and last integers after `Answer:` differ, with >2% as a B0 prompt-fix trigger. Stage A max is 0.9%.
- **Batched generation (§3.4) is implemented** (conformance with PREREG §9):
  - `HFBackend.generate_batch` does left-padded greedy decoding with per-row stop handling and per-step top-2 gaps. It is fail-loud on non-finite logits. llama.cpp (the GGUF fallback) stays sequential at batch 1.
  - B1 probes, the B2 main conditions and the B3 receiver calls run in chunks of `stageB_batch_size = 8`. The B3 sender, the cache test, warm runs, B0 qualification and the canaries stay batch-1. Each row logs `batch`.
  - The B0 pilot measures per-call receiver and probe time at the batch size used, so the A1.1 projection uses batched timings.
  - **Regression test** (`tools/smoke_hf_batch.py`, run by `tests/test_e1b.py`; SmolLM2-135M, fp32, CPU, no nf4): batched vs batch-1 output tokens were **identical on 8/8 receiver and 6/6 probe prompts**, with identical parsed predictions. Per-call time went from 1.41 s to 0.49 s (receiver) and 0.21 s to 0.075 s (probe) on CPU.
  - **Caveat:** fp16/nf4 on GPU with padding may not be bit-identical to batch-1. Proposal for reviewers: B0 re-runs this check on the Kaggle GPU in nf4 and reports any differences, and the batch size is frozen in the post-B0 amendment.
  - The code hash is re-recorded. Nothing has been run on Kaggle.

### 5b. Review of this draft (2026-10-12): Claude, Grok, GPT

- **Claude ([claude_A5](reviews/claude_A5.md)):**
  - rebuild the weak calibration plants with f/n >= 0.30 (>=3 per type, TEST untouched);
  - withdraws P6 (keep the frozen leak rule, add reporting only);
  - settle P1/P4 after B0 and before B1;
  - review batching hygiene;
  - add reserve probe templates;
  - choose the B0 batch size by >=99% batch-1 agreement.
  - P4 table verified (n=20: 0.677/0.839/0.925/0.979; the current n=24 gives 0.564/0.766/0.884/0.966).
- **Grok ([grok_A5](reviews/grok_A5.md)):**
  - don't rebuild now; after B, rebuild only the UNKNOWN-implying plants, and only if the 7B pair shows the same pattern;
  - drop unstated from the leak check, because the prompt test didn't remove the structural guess (0/23).
- **Open disagreements, broken by GPT:**
  - Rebuild: Claude says now, Grok says after B.
  - Unstated: Claude says frozen rule + B0b, Grok says exclude. Both routes end with unstated out of the gate.
- **GPT ([gpt_A5](reviews/gpt_A5.md)):**
  - unstated becomes an abstention diagnostic, excluded from the leak rule;
  - strengthen only explicitly-wrong-rule plants;
  - found the generation-config bug.
  - Counts verified: 13 / 33 / 20 of 40. Our earlier 16 = 13 on the 40 + 3 on the 6 A2 plants (see gpt_A5.md).

### 5c. Code-hygiene fixes implemented (no rule change)
- `stages.batched_generate`: B1 probes, B2 and B3 receiver calls now go through it.
  - **Compute-once:** byte-identical prompts are generated once and reused (B2 id_oracle vs direct_text); rows log `shared_n`.
  - **Deterministic batch composition:** unique jobs are sorted by (prompt token length, content sha) and chunked by `stageB_batch_size`, so composition doesn't depend on input order. Rows log `batch_index`, `batch_pos` and `batch_n`, and come back in input order.
- `HFBackend.generate_batch`:
  - **Padding asserts:** left padding; the mask covers exactly the real tokens; the real tokens are unchanged by padding.
  - **Pad token logging:** the pad token id and its source are logged in `info`.
  - **Positions:** derived by HF from the attention mask; equality with batch-1 is checked by the smoke test.
  - **Per-row stop:** unchanged.
- **GPT's bug (fixed):** `generate_batch` now passes `NEUTRAL_GEN` (repetition_penalty=1.0, temperature/top_p/top_k neutral, no other processors) plus `do_sample=False`, so it no longer inherits the model's `generation_config`.
- **Tests:**
  - `tests/test_e1b.py`: TestBatchHygiene, TestNeutralGen.
  - `tools/smoke_hf_batch.py` now sets a Qwen-7B-like penalised generation_config (repetition_penalty 1.05, top_k 20, top_p 0.8) and still gets batched == batch-1 tokens on 8/8 receiver and 6/6 probe prompts (SmolLM2-135M, CPU fp32).
  - 51 unit tests OK (1 skipped); the fake-backend dry run passes the validator.
- **Small fix:** `log_prompt` now creates its directory. This was a test-order failure; no behaviour change in real runs.

## 5d. DRAFT resolution (pending the user's final OK; nothing frozen)
**All three reviewers agree:**
- proceed to B0 uncached;
- the cache claim stays withheld, and the GPU cache path is tested separately;
- keep the leak checks on the non-unstated kinds;
- B1 reports planted rejection per corruption type;
- settle the P4 entry-bar question after B0 and before B1;
- batching needs the hygiene fixes (§5c, done).

**Settled by majority:**
- **Unstated** (Grok + GPT): the dedicated *-unstated probes are excluded from the leak rule and reported as an abstention diagnostic (no-text "Not stated" rate by kind). Ordinary questions that become UNKNOWN through a corruption stay in.
- **Plants** (GPT, with Grok's timing for the rest):
  - **Now:** strengthen only the explicitly-wrong-rule calibration plants (changed_constant: 11/13 have <8 flips). TEST plants stay untouched.
  - **Report separately:** rejection of UNKNOWN-implying plants (deleted_negation, mismatched_definition). Revisit them after B, and rebuild only if the 7B pair shows the Stage A abstention pattern.
  - **Stated limit:** answer agreement alone cannot detect a reader that silently reconstructs the intended rule (20/40 calibration plants would pass a gap-filling reader today).
- **Still open:** reserve probe templates per kind (Claude 5), and the batch-size selection rule (Claude 6: largest size matching batch-1 on >=99% of non-TEST items).

## 6. Questions for the reviewers
1. Do you agree that §7's "otherwise: go to Stage B" means Stage A's failure does not block B, only small-pair calibration?
2. Is implementing batched generation (§3.4) a conformance fix that is acceptable before B0, or does it need its own re-review of the code?
3. Is the expected loss of the "unstated" probe kind via B0b acceptable (20 probes per entry remain)?
4. Should B0's pilot measure several batch sizes and pick the fastest that fits memory, with the choice frozen before B1?
