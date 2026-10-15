# PREREG E1c: verified ID with prose fallback, both directions (DRAFT, NOT FROZEN)

Status: **DRAFT**. No E1c TEST data exists. The TEST book is not built and refuses to build until `e1c.status == "frozen"`.
Design input: `v6/e1b/reviews/gpt_E1c_design.md` (GPT memo), plus Stefan/Grok steering (2026-10-15).
E1c is a new, separate pre-registered study. It does not change any E1b result. The E1b A9 primary stays **POC FAILED**. The A10 B3r secondary result stays **INCONCLUSIVE**.

## 1. Question and claim
Does a **verified-ID protocol with prose fallback** (the hybrid arm) keep receiver accuracy within 5 points of plain prose? It must also send IDs for most entries and save bytes. Both sending directions are tested:

- Qwen2.5-7B sending to Falcon3-7B;
- Falcon3-7B sending to Qwen2.5-7B.

If it succeeds, the supported claim is: *"on this registered task distribution, verified ID/prose communication keeps accuracy within 5 points while meeting the ID-use and byte-saving requirements."* This is **not** a claim that always sending an ID is non-inferior.

## 2. Models and compute
- **Models:** `qwen7b` (Qwen2.5-7B-Instruct) and `falcon7b` (Falcon3-7B-Instruct). They use the E1b pinned revisions and the nf4 backend, unchanged.
- **Excluded:** no Mistral, no other European models, no gated Hugging Face models.
- **Compute:** free Kaggle T4 ×1 only. No paid APIs.
- **Attribution** on every Falcon result: "Falcon3-7B-Instruct results were produced using artificial intelligence technology from the Technology Innovation Institute (TII Falcon License)."

## 3. Task and books
- **Families.** F1 is member/non-member pricing. F2 is the giver/taker hand-over. Both use the frozen E1b generator, gold computation and 4-candidate sender task (the true entry plus three neighbours: swap, shift, swap+shift). Each entry has 4 cases, branch-balanced.
- **Separate seeds.** Dev and TEST use separate seed sets, committed now in `config_e1c.json` (`seeds.dev`, `seeds.test`). The two sets share no values.
- **Dev book** (`data/book_dev.json`, sha256 pinned as `dev_book_sha256`). It is built now with 40 core entries per family. It is DEV data only. Its pool named "test" is dev data and is never E1c TEST.
- **TEST book.** It has 120 core entries per family, which is 240 entries per direction (the same entries are used in both directions) and 960 cases per direction.
  - It is built only **after freeze**, on the box (CPU, no model).
  - Its sha256 is committed before T1 can start.
  - It is disjoint from the E1b frozen book, the A9 book and the dev book.
- **Freshness.** These checks run in `e1c/book.py`. None of the following is reused from an older book:
  - a case text (the frozen canary pool is the only exception);
  - an entry ID;
  - the rule text of a non-neighbour entry.
- **Neighbour texts.** A neighbour may share rule text with an old book's *neighbour*.
  - Why: forbidding every old neighbour text made the small F2 rule space unbuildable. At TEST size, 0 of 10 throwaway seeds built; with the relaxation, 10 of 10 built.
  - Neighbours still get new IDs.
- **Distinct core rules.** No two E1c core entries may state the same rule.
  - Why: the E1b builder can emit duplicates. The E1b A9 book has two duplicate F2 core pairs, which is disclosed as an E1b finding.
  - How: books build 2n core entries per family. The E1c core is the first n entries in build order whose rule text is new.
- **Seed rule.** If a book fails to build at its pinned generator seed, the seed is raised by 100 until it builds. Every attempt is logged.
  - Dev built at 91062 on the first attempt (`data/dev_seed_attempts.txt`).
  - Feasibility at TEST size was checked only with throwaway seeds (97000–97900), never with the TEST seeds.

## 4. Protocol per entry (both directions)
1. **Sender.** It uses the frozen E1b sender prompt (4 candidates, a single-letter reply, `sender_max_new_tokens` = 4, batch 1, greedy). The reply is parsed with the **A10 parser** `parse_letter_a10`. This is the frozen `parse_letter` applied after candidate-ID fragments are removed. The archived E1b failure "B) F1" is a regression test.
2. **Verifier.** This is a new call to the *sender model*, stateless and batch 8.
   - It sees **only the original prose message**: no candidates, no pick, no ID.
   - It must output one strict line:
     - F1: `GROUP= MEMBER= NONMEMBER=`
     - F2: `GIVER= GIVER_RATE= TAKER= TAKER_RATE=`
   - Up to 48 new tokens.
3. **Deterministic acceptance.** The ID is accepted only if all three hold:
   - the pick is valid;
   - the dictionary resolve passes (ID, version and hash8);
   - every parsed field equals the **picked** entry's parameters (`e1c/verifier.py`).

   Otherwise the entry falls back to prose. A format error causes fallback; entries are never dropped. There are no retries, no voting and no thresholds.
4. **Receiver.** The receiver is the other model. It uses the frozen E1b receiver prompt, parser and scoring, greedy decoding, batch 8.
   - **Prose arm:** the true entry's prose.
   - **Hybrid arm:** the accepted ID, expanded by the delegate to the dictionary text (as in E1b `id_selected`), or the *identical* prose prompt on fallback.
   - Identical requests are generated once and reused (`shared_n = 2`). This identity reuse is pre-registered.
   - Fallback prose bytes count in the hybrid arm.
5. **Canaries.** Each model load must reproduce the E1b B0x canary references. Otherwise CANARY_FAIL stops the run.

## 5. Primary endpoint (TEST, per direction)
- **Per-entry difference.** d_e = mean over 4 cases of hybrid correct − prose correct, using the true entry's cases. The point estimate is the mean of d_e over the 240 entries.
- **CI.** A 95% CI from a **paired bootstrap stratified by family and clustered by entry**: resample entries with replacement within F1 and within F2. It uses 2,000 resamples and a frozen seed (`seed_of(seeds.test.bootstrap, direction)`).
- **Label rule** (E1b A1.2, CI only, mutually exclusive):
  - lower bound > −0.05: non-inferior;
  - upper bound < −0.05: inferior;
  - otherwise: inconclusive.

## 6. Success criteria
All four must hold, **separately in BOTH directions**:
1. Lower 95% bound of the difference > −0.05.
2. **ID coverage ≥ 85%**: accepted entries ÷ all 240 assigned entries.
3. **Payload byte saving ≥ 30%**: 1 − Σhybrid payload bytes ÷ Σprose payload bytes, with fallback prose included. Whole-exchange saving is also reported.
4. **Dictionary cost recovered within 1,000 messages.**
   - Dictionary cost = UTF-8 bytes of (framed ID + entry text) for every entry the receiver must hold (the 240 entries plus their neighbours).
   - Break-even = dictionary bytes ÷ mean payload saving per message, and it must be ≤ 1,000.

E1c succeeds only if all four criteria pass in both directions. Anything else is "NOT MET", reported with the per-criterion results. There is no choosing a better direction and no post-hoc subsets.

**Secondary (descriptive) measures:**
- pick accuracy;
- verifier format rate;
- wrong-pick-accepted count and rate;
- correct-pick-rejected count;
- per-family results;
- accuracy of the ID-sent subset.

## 7. Stages, gates and caps
| Stage | Data | When | Cap | Gate |
|---|---|---|---|---|
| **D1 dev pilot** | dev book: senders and verifier on 80 entries per model; receivers on 20 entries × 4 cases × 2 arms per direction | this week (after Stefan's go) | **0.5 GPU-h** | `E1C_GO=D1`, Stefan's explicit go; allowed while DRAFT |
| **T1 TEST** | TEST book: 240 entries per direction | next week, after the Kaggle quota reset | **6.0 GPU-h** (placeholder; set from D1 at freeze, ≤ next week's quota) | `E1C_GO=T1`, Stefan's explicit go, `status=frozen`, D1 `.done`, TEST book sha pinned |

**Rules for every stage:**
- One start plus **one infrastructure retry**. The retry is allowed only for a crash, no GPU or a kernel failure; never after `.done`. This is enforced by `e1c_state.json`.
- Budget is checked continuously, using its own ledger (`results/budget_ledger.json`, `E1C_*`).
- These markers are terminal: BUDGET_EXHAUSTED, CANARY_FAIL, GPU_PREFLIGHT_FAIL, ATTEMPT_INCOMPLETE.
- There is a code-hash gate (`CODE_HASH.txt`, covering the e1c code, config, kernel runner and the E1b modules it imports).
- Status is checked once, a few minutes after a push: no polling and no relaunch.

**Load order** (both stages):
1. Qwen: send and verify.
2. Falcon: send and verify, then receive Qwen's messages.
3. Qwen: receive Falcon's messages.

D1 also logs a verifier batch-1 versus batch-8 identity check (16 entries per model).

## 8. What D1 measures, and the TEST sizing rule (pre-declared)
**D1 reports:**
- timing per step;
- A10 parse paths;
- verifier format rate;
- coverage;
- **the rate of wrong picks that pass verification** (wrong-pick-accepted ÷ entries, per sender);
- correct-pick rejections;
- descriptive hybrid-versus-prose results on the 20-entry receiver subset.

D1 gives **no E1c verdict**.

**TEST sizing (`e1c/stages.py:sizing`):**
- TEST runs at **240 entries per direction** if both hold:
  - the wrong-pick-accepted rate is **≤ 2%** for both senders;
  - the projected T1 GPU-h (from D1 timings, plus 25% margin) is ≤ the T1 cap.
- Otherwise there is no TEST until a documented amendment.

Dev results may change only these things before freeze:
- the verifier prompt or format;
- the T1 cap;
- the receiver batch size.

Each change must be documented. Thresholds, endpoints, families, candidate difficulty and models never change. After freeze there are **no outcome-driven changes**.

## 9. Freeze procedure
1. D1 runs and is reported.
2. Any dev-driven change goes in with a diff.
3. GPT/Grok review.
4. Set `status: frozen` and the T1 cap, commit, and tag `prereg-e1c`.
5. Build the TEST book on the box and commit its sha256 into the config.
6. Tag again and push the T1 kernel only on Stefan's explicit go.

Nothing on the TEST book is looked at before T1.

## 10. Known limitations and open points (disclosed)
- The verifier is the sender model and can repeat the sender's semantic error. Hiding the candidates reduces anchoring but does not make the two calls independent; D1 measures the result.
- Execution order is the deterministic E1b A5 batching (sorted by prompt length and sha), not randomised. Greedy decoding with batch-1/batch-8 conformance checks makes order effects testable rather than random.
- Candidate positions are shuffled per entry with a frozen seed, not exactly balanced across A–D.
- The 2% wrong-pass threshold rests on 80 dev entries per sender. Its 95% upper bound is wide (0 of 80 gives about 4.5%).
- The F2 rule space is small. This is why neighbour-text reuse and the 2n build are used (see §3).
