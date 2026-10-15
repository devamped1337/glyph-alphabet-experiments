# PREREG E1c: verified ID with prose fallback, both directions (DRAFT, NOT FROZEN)

Status: **DRAFT, r6** (GPT r1–r5 fixes applied; see §11). No E1c TEST data exists. The TEST book is not built and refuses to build until `e1c.status == "frozen"`.
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
- **Dev book** (`data/book_dev.json`, sha256 pinned as `dev_book_sha256`). It is built now with **80 core entries per family** (r2: enlarged from 40, so 160 entries per sender). It is DEV data only. Its pool named "test" is dev data and is never E1c TEST.
- **TEST book.** It has 120 core entries per family, which is 240 entries per direction (the same entries are used in both directions) and 960 cases per direction.
  - It is built only **after freeze**, on the box (CPU, no model).
  - Its sha256 is committed before T1 can start.
  - It is disjoint from the E1b frozen book, the A9 book and the dev book.
- **Freshness (r2: wording = code, `e1c/book.py:check_fresh`).** Against every older book (E1b frozen, A9, and for TEST also the E1c dev book):
  - (a) no case text is reused, except the shared frozen canary pool;
  - (b) no entry ID is reused, except the canary pool;
  - (c) no *non-neighbour* entry of the new book (every E1c core entry, i.e. every TEST true rule) uses an old **true-rule** text;
  - (d) new **neighbours** are not text-checked: a new distractor may coincide with any old rule text (true rule or neighbour), and a new core entry may coincide with an old *neighbour* text.
  - "Old true-rule texts" are every non-neighbour entry of the E1b books, but for the E1c dev book only its 160 E1c core entries (the only true rules any model sees in D1). The dev book's other builder groups are never shown to a model in E1c.
  - Why the relaxations: the F2 rule space is small. With every old text forbidden, 0 of 10 throwaway seeds built a TEST-size book. With (c)/(d) and the full dev-book forbid list, 0 of 10 still built once dev grew to 80 per family. With the dev forbid limited to its E1c core, 3 of 10 built, so the seed rule is expected to fire for TEST.
  - Consequence for freshness (r3 wording): TEST true rules exclude the specified earlier **true-rule** texts, and TEST cases are fresh under checks (a)–(b). A TEST true rule or distractor may repeat the text of an earlier *distractor*, so that text is not historically unseen. Stateless inference only means no conversational context carries over between calls. The overlap can be counted from the committed books.
- **Distinct core rules.** No two E1c core entries may state the same rule.
  - Why: the E1b builder can emit duplicates. The E1b A9 book has two duplicate F2 core pairs, which is disclosed as an E1b finding.
  - How: books build 2n core entries per family. The E1c core is the first n entries in build order whose rule text is new.
- **Seed rule.** If a book fails to build at its pinned generator seed, the seed is raised by 100 until it builds. Every attempt is logged.
  - Dev (80 per family) built at 91062 on the first attempt (`data/dev_seed_attempts.txt`). `tools/build_book.py` applies the rule mechanically and logs every attempt (`data/<kind>_seed_attempts.txt`).
  - Feasibility at TEST size was checked only with throwaway seeds (97000–97900), never with the TEST seeds.

## 4. Protocol per entry (both directions)
1. **Sender.** It uses the frozen E1b sender prompt (4 candidates, a single-letter reply, `sender_max_new_tokens` = 4, batch 1, greedy). The reply is parsed with the **A10 parser** `parse_letter_a10`. This is the frozen `parse_letter` applied after candidate-ID fragments are removed. The archived E1b failure "B) F1" is a regression test.
2. **Verifier.** This is a new call to the *sender model*, stateless and batch 8.
   - It sees **only the original prose message**: no candidates, no pick, no ID.
   - It must output one strict line. **Registered grammar (r2):** the whole reply, after stripping leading and trailing whitespace, must fully match
     - F1: `GROUP=<word> MEMBER=<int> NONMEMBER=<int>`
     - F2: `GIVER=<word> GIVER_RATE=<int> TAKER=<word> TAKER_RATE=<int>`

     with keys in this order, `<word>` = `[A-Za-z]+` (compared case-insensitively), `<int>` = `-?[0-9]+`, separated by spaces or tabs. Anything else is a format error and causes fallback: extra lines, explanations, extra or duplicate keys, units ("4 credits"), articles, punctuation.
   - Up to 48 new tokens. Batch size is explicit: 8 on the production batching path, in D1 and T1 alike. There is no automatic switch: if D1's batch-1 check disagrees, T1 is ineligible until a batch-1 dev stage is added by amendment (§7, §8).
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
5. **Scoring (r2).** Both arms of an entry carry the TRUE entry's registered cases and are scored against those cases' registered gold, even when an accepted wrong pick sends a neighbour's rule. The code asserts this per row and logs `rule_entry` (the entry whose text the receiver saw).
6. **Canaries.** Each model load must reproduce the E1b B0x canary references. Otherwise CANARY_FAIL stops the run.

## 5. Primary endpoint (TEST, per direction)
- **Per-entry difference.** d_e = mean over 4 cases of hybrid correct − prose correct, using the true entry's cases. The point estimate is the mean of d_e over the 240 entries.
- **CI.** A 95% CI from a **paired bootstrap stratified by family and clustered by entry**: resample entries with replacement within F1 and within F2. It uses 2,000 resamples and a frozen seed (`seed_of(seeds.test.bootstrap, direction)`).
- **Completeness first (r2).** Before any result, each direction's rows must equal the assignment exactly: all 240 assigned entries (120 per family), each entry's 4 registered cases (by text), each case in both arms exactly once, gold equal to the registered gold, no extra or duplicate rows, and a selection row for every assigned entry. Otherwise that direction is **INCOMPLETE** and the study verdict is INCOMPLETE, never SUCCESS. The sender's selection file must hold exactly one row per assigned entry (r3). The T1 verdict also needs exactly both registered directions and both senders at the registered sizes.
- **Percentile convention.** Sorted statistics s[0..1999]: lower = s[50], upper = s[1949].
- **Label rule** (E1b A1.2, CI only, mutually exclusive):
  - lower bound > −0.05: non-inferior;
  - upper bound < −0.05: inferior;
  - otherwise: inconclusive.

## 6. Success criteria
All four must hold, **separately in BOTH directions**:
1. Lower 95% bound of the difference > −0.05.
2. **ID coverage ≥ 85%**: accepted entries ÷ all 240 assigned entries.
3. **Payload byte saving ≥ 30%**: 1 − Σhybrid payload bytes ÷ Σprose payload bytes, with fallback prose included.
   - **Communication boundary (r2).** The channel is sender → receiver. Candidate preparation and the verifier run locally at the sender, which holds the dictionary, so their bytes are local computation, not transmitted.
   - **Message** = one receiver request = one case exchange (4 per entry). Payload = the rule part of the message (framed ID or prose). "Message bytes" = payload + case text, reported as `message_saving_payload_plus_case`, not as a criterion.
4. **Dictionary cost recovered within 1,000 messages.**
   - Dictionary cost = UTF-8 bytes of (framed ID + entry text) for every entry the receiver must hold (the 240 entries plus their neighbours).
   - Break-even = dictionary bytes ÷ mean payload saving per message (per case exchange, the same unit), and it must be ≤ 1,000 messages.

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
| **D1 dev pilot** | dev book: senders and verifier on 160 entries per model; receivers on 10 entries × 4 cases × 2 arms per direction | this week (after Stefan's go) | **0.5 GPU-h** | `E1C_GO=D1`, Stefan's explicit go; allowed while DRAFT |
| **D2 dev pilot (A1)** | same as D1 (same dev book, sizes and protocol; reruns everything) | after review and Stefan's explicit go | **0.8 GPU-h** (from measured D1 timings, see AMENDMENT_E1c_A1) | `E1C_GO=D2`; D1 is closed (BUDGET_EXHAUSTED, kept as recorded); **D2 is the dev stage that qualifies T1** (§8 rules unchanged) |
| **T1 TEST** | TEST book: 240 entries per direction | next week, after the Kaggle quota reset | **6.0 GPU-h** (placeholder; set from D1 at freeze, ≤ next week's quota) | `E1C_GO=T1`, Stefan's explicit go, `status=frozen`, TEST book sha pinned, and **D1 eligibility** (§8) checked in code |

**Rules for every stage:**
- **Starts (r2, r3).** One start plus at most one **authorised infrastructure retry**, enforced through `results/<stage>/e1c_state.json`:
  - every start appends an attempt record (kind, code hash, outcome: running / done / exit code / crash type);
  - a second start is allowed only if the state carries a retry authorisation written by `tools/authorise_retry.py` after the failed attempt's Kaggle log has been read. The reason must be one of `no_gpu`, `install_or_network`, `kernel_crash`, `oom_at_load`. The authorisation records the GPU-h already used (charged_h);
  - there is never a retry after `.done`, BUDGET_EXHAUSTED, CANARY_FAIL or ATTEMPT_INCOMPLETE (these are terminal), and never a third start;
  - **GPU_PREFLIGHT_FAIL** (no CUDA device) is an infrastructure failure, **not** terminal. It permits the retry only with reason `no_gpu`; this resolves the r1 conflict;
  - **reason consistency (r3):** the reason must match the recorded failure. A GPU_PREFLIGHT_FAIL marker or the supervisor outcome `no_gpu rc=9` means `no_gpu`, and `no_gpu` needs one of them. A supervisor-recorded `crash rc=N` means `install_or_network`, `kernel_crash` or `oom_at_load`. Any other outcome (deadline, budget admission, canary, gate) is refused. **r5: an attempt still recorded as `running` (no supervisor-recorded end) is never retried: fail-closed, it is terminal and the next start writes ATTEMPT_INCOMPLETE.** If no results came back, attempt 1 is recorded by hand as "manual: from Kaggle log" with one of the non-GPU reasons; this is **external-log adjudication** (r6): the fail-closed rule cannot be checked when the durable state itself is missing, so the decision rests on the cited Kaggle log. A note citing the log is mandatory. charged_h must be finite, > 0 and ≤ the stage cap;
  - **resume binding (r3):** if attempt 1 left selection or exchange rows, the retry refuses (ATTEMPT_INCOMPLETE) unless attempt 1's recorded code hash and protocol hash equal the current ones. Reused rows therefore always come from the qualified protocol;
  - the retry kernel overlays `v6/e1c/results` from a pinned commit (`E1C_RESULTS_COMMIT`), so the attempt history and ledger travel with it.
- **Cumulative budget.** The stage cap covers both attempts: ledger value = max(recorded ledger, charged_h).
- **Budget enforcement (r3).** Two layers.
  - **Deadline (enforced, r5: supervisor process).** `run_e1c.py --stage` is a **supervisor**; the stage runs in a separate **child** process (`--child`). The supervisor is the only writer of the attempt state, the ledger, the terminal markers, `summary.json` and `.done`.
    - Before launching, it computes the remaining budget (cap − cumulative ledger) and **durably records** the attempt (token, `started_mono`, `deadline_mono`, wall times for audit). Every state write is: file fsync, atomic replace, then **fsync of the containing directory** (r6); new directories fsync their parent. If that write fails, nothing is launched.
    - **Clock (r6):** the deadline, the wait, the elapsed charge, the child's admission guard and the completion decision all use `CLOCK_MONOTONIC` (system-wide on Linux, shared by supervisor and child). Wall-clock jumps cannot shorten, extend or invert the charge.
    - The child runs in its own process group. At the deadline the supervisor SIGKILLs the whole group (outcome `deadline`, BUDGET_EXHAUSTED, the full remaining budget charged). **Wording (r6):** this is a deadline-triggered SIGKILL issued by a running supervisor, not a hard real-time bound; OS scheduling, supervisor suspension or uninterruptible kernel waits can delay the actual termination. The tests show observed behaviour (killed within seconds), not a universal bound.
    - **Process tree (r6):** after any child exit the supervisor also SIGKILLs the group, so ordinary surviving grandchildren are removed. The child is started with `PR_SET_PDEATHSIG=SIGKILL`, so if the supervisor dies the kernel kills the child (the attempt stays `running`, terminal). This is best effort: the prctl result is not checked, a supervisor death before registration is not covered, and the signal reaches the child only, not its descendants. Not covered either: a descendant that creates its own session; the E1c code path (transformers/torch on one GPU, no multiprocessing workers) creates none.
    - `.done` is written only if the child exited 0, wrote CHILD_COMPLETE (its last act) **and** exited no later than the deadline. A child that completes but is still alive at the deadline, or exits after it, ends as `deadline`. The child never writes `.done`, the ledger or any terminal marker, and it refuses to run without the running attempt's token.
    - Child exit codes: 3 = admission stop (BUDGET_EXHAUSTED), 8 = canary failure (CANARY_FAIL), 9 = no GPU (infra, GPU_PREFLIGHT_FAIL), anything else = `crash rc=N`.
    - After the child ends, the supervisor writes, in order: the ledger (monotonic elapsed time from the pre-launch record to child exit), the marker, `summary.json` + `.done` (when done), and **last** the attempt outcome. **Ledger scope (r6):** the charge covers the pre-launch record write and the child's whole run; the supervisor's post-run bookkeeping (typically well under 1 s) is reported separately as `finalise_s` in the attempt record (excluding the final state write itself) and is not charged. **Fail-closed:** if any write before the final state replace fails, the supervisor exits 70 and the attempt stays `running`, which is terminal (see Starts). Disclosed limitation: if the final state replace succeeds but the directory fsync after it fails, the supervisor exits 70 while the visible state may already say `done`, with uncertain crash durability; no further transactional machinery is added for this pilot.
    - **Completion (r6):** a stage counts as finished only when `.done` exists **and** the committed state records outcome `done` for the last attempt with no attempt `running`. `.done` alone (e.g. the final state write failed) is INCOMPLETE at start, refused by `authorise_retry`, and does not qualify T1.
    - Precedence (r5, r6): terminal markers, then unresolved `running` attempts, then completion, both at start and in the T1 eligibility check; a D1 with any terminal marker never qualifies T1. `start` also refuses (exit 3) when the ledger shows the cap used.
    - Rows already written are kept. Not covered: Kaggle wall time before the supervisor starts (clone, pip install), which is outside the stage ledger and reported separately.
  - **Admission control (estimate-based, not a bound):** the child does not start a unit (model load + canaries, sender call, verifier chunk, receiver chunk, batch-1 check call) whose estimate would cross the deadline; it exits 3 and the supervisor records BUDGET_EXHAUSTED. Estimate = max(configured prior, 1.2 × longest observed); priors: load 420 s, sender call 10 s, verifier chunk 120 s, receiver chunk 240 s, check call 20 s.
- There is a code-hash gate (`CODE_HASH.txt`, covering the e1c code, config, kernel runner and the E1b modules it imports).
- Status is checked once, a few minutes after a push: no polling and no relaunch.

**D1 time estimate** (from E1b B3/B3f/B3r logs): three loads with canaries about 750 s; senders 2 × 160 × 0.55 s ≈ 180 s; verifier about 240 s; batch-1 check about 100 s; receivers 2 × 40 messages × 2 arms ≈ 250 s. Total about 1,500 s ≈ 0.42 GPU-h, under the 0.5 h cap. If it runs slower, the guard stops it cleanly; nothing is shrunk.

**Load order** (both stages):
1. Qwen: send and verify.
2. Falcon: send and verify, then receive Qwen's messages.
3. Qwen: receive Falcon's messages.

D1 also runs a verifier batch-8 (production path) versus batch-1 identity check on 16 entries per model, budget-guarded. **Pre-declared rule (r3):** if any reply differs for either model, T1 is **not eligible**. A new dev stage (amendment, own cap and go) must re-measure the acceptance screen with the verifier at batch 1. The effective verifier batch is part of the protocol hash, so T1 always runs the configuration D1 qualified.

## 8. What D1 measures, the T1 eligibility rule and TEST sizing (pre-declared)
**D1 reports** (descriptive; no E1c verdict):
- timing per step;
- A10 parse paths;
- verifier format rate;
- coverage;
- **wrong-pick-accepted** count, rate and one-sided 95% Clopper–Pearson upper bound, per sender (denominator 160);
- correct-pick rejections and wrong picks caught;
- descriptive hybrid-versus-prose results on the 10-entry receiver subset (completeness-checked like TEST).

**What 160 dev entries can and cannot show (r2, honest wording).**
- The 2% rule is a **feasibility screen, not a demonstration**. Any rate interpretation assumes a binomial sampling model for the 160 generated, family-balanced dev entries per sender. They are generated by the registered builder, not drawn from a natural population. The screen passes if the observed rate is ≤ 2% for both senders, i.e. at most 3 wrong-and-accepted out of 160.
- A rate ≤ 2% is shown (95% one-sided) only if the Clopper–Pearson upper bound is ≤ 2%, which needs **0 of 160** (upper bound about 1.86%). With 80 entries even 0 of 80 does not show it (about 3.7%), which is why dev was enlarged.
- Whatever D1 shows, TEST measures the consequence directly: an accepted wrong pick **can** lower hybrid accuracy (a different rule need not change a particular scored answer), which is the primary endpoint, and the TEST wrong-pick-accepted count and bound are reported.

**T1 eligibility (enforced in `stages.py:t1_eligibility` / `check_d1_summary`).** T1 refuses to start (exit 19) unless the recorded D1 summary shows all of these:
1. D1 `.done`, with the **exact registered structure (r3)**: both registered directions and no others, each COMPLETE with 10 entries and 40 messages; both senders, each complete with exactly one selection row per entry (160); and both conformance records (16 entries each, all identical between batch 8 and batch 1);
2. the screen passed (observed wrong-pick-accepted ≤ 2% for both senders);
3. projected T1 GPU-h (D1 timings scaled to 240 entries per direction, both directions, plus 25% margin) ≤ the frozen T1 cap;
4. **D1's protocol hash equals the current one.** The hash covers the sender prompt, the **actual configured** sender token limit and the A10 parser, plus the verifier prompt, format, grammar, token limit and **effective batch**, and the receiver batch size.

**Projection inputs (r3, r4).** These come from **persisted per-row latencies** (sender and verifier per entry; receiver per generated row, with a fallback counted once) plus the longest model load (with canaries) **from any attempt** (loads are persisted per attempt in `loads_attempt<n>.json`). This keeps a resumed attempt from underprojecting.

Any dev-driven change to these invalidates D1. A new dev stage (D1b, with its own amendment, cap and go) is then needed; old measurements do not qualify a revised implementation. There is no override flag.

**TEST size.** 240 entries per direction (fixed). If the eligibility rule fails, there is no TEST until a documented amendment.

Dev results may change only these things before freeze, each documented with a diff and each needing a new dev stage as above:
- the verifier prompt or format;
- the receiver batch size.

The T1 cap may be set from D1 at freeze (it is not part of the protocol hash, and eligibility checks it). Thresholds, endpoints, families, candidate difficulty and models never change. After freeze there are **no outcome-driven changes**.

## 9. Freeze procedure (r2: two fixed, separate commits)
1. D1 runs and is reported. Any dev-driven change, plus its new dev stage, goes in as an amendment.
2. GPT/Grok review.
3. **Registration commit**, tagged **`prereg-e1c`** (never moved): `status: frozen`, T1 cap set, `test_book_sha256: null`, no `book_test.json`. This fixes the code, protocol and analysis.
4. On the box (CPU, no model), `tools/build_book.py test` builds the TEST book with the seed rule. That is the only time TEST data is generated.
5. **Execution commit**, tagged **`e1c-t1-exec`** (never moved): a descendant of `prereg-e1c` whose diff touches **only** `data/book_test.json`, `data/book_test.sha256`, `data/test_seed_attempts.txt`, `config_e1c.json` and `CODE_HASH.txt`. The config may differ **only** in `test_book_sha256`, plus `seeds.test.generator` if the seed rule fired (in +100 steps). `tools/check_freeze.py prereg-e1c e1c-t1-exec` must pass and its output is committed in the T1 report.
6. The T1 kernel checks out `e1c-t1-exec` and is pushed only on Stefan's explicit go.

**What may touch the TEST book before T1:** only the automated construction, integrity (sha256, `verify`, branch balance, distinct core) and freshness checks run by `build_book.py` and `load_book`. No person inspects TEST entries or cases, and no model sees them before T1.

## 10. Known limitations and open points (disclosed)
- The verifier is the sender model and can repeat the sender's semantic error. Hiding the candidates reduces anchoring but does not make the two calls independent; D1 measures the result.
- Execution order is the deterministic E1b A5 batching (sorted by prompt length and sha), not randomised. Greedy decoding with batch-1/batch-8 conformance checks makes order effects testable rather than random.
- Candidate positions are shuffled per entry with a frozen seed, not exactly balanced across A–D.
- The 2% wrong-pass rule is a screen on 160 dev entries per sender (see §8): only 0 of 160 shows ≤ 2% at 95%.
- The F2 rule space is small. This is why neighbour-text reuse, the dev-core-only forbid list and the 2n build are used (see §3). The TEST seed rule is expected to fire (about 3 of 10 throwaway seeds build).
- The T1 projection depends on dev coverage (fallback reuse), the dev prompt-length mix and dev timing.

## 11. r2 changes (GPT r1)
1. Completeness check before any result; INCOMPLETE is never SUCCESS (§5).
2. T1 eligibility enforced from the D1 summary, including the protocol hash; revalidation is needed after changes (§8).
3. Attempt records, authorised infrastructure retry only, GPU_PREFLIGHT_FAIL made retryable, cumulative budget (§7).
4. Wrong accepted pick scored on the true case: assertion plus regression test (§4).
5. Strict full-response verifier grammar (§4).
6. Explicit verifier batch, budget-guarded conformance check, pre-declared disagreement rule, in-flight guard (§7).
7. Communication boundary and message unit defined (§6).
8. Freshness wording equals the code, with cross-kind tests (§3).
9. Two fixed tags and the allowed execution diff, checked by a tool (§9).
- Also: dev enlarged to 160 per sender and the 2% gate reworded as a screen (§8).

**r3 changes (GPT r2):**
1. Selection rows are validated raw: exactly one per entry, no duplicates or extras, else INCOMPLETE (§5).
2. The protocol hash uses the actual sender token limit and the effective verifier batch. A batch-1/batch-8 disagreement makes T1 ineligible until a batch-1 dev stage runs (§7, §8).
3. Retry reason must be consistent with the recorded failure; charged_h finite and ≤ cap; mandatory log note; resume bound to the same code and protocol hash (§7).
4. Verifier grammar uses ASCII `[0-9]` (no Unicode digits) (§4).
5. Enforced deadline watchdog plus estimate-based admission control, stated honestly (§7).
6. New, blocking: sizing from persisted per-row latencies, valid after a resume (§8).
7. New, blocking: exact D1 summary and T1 verdict structure required (both directions, both senders, sizes, conformance) (§5, §8).
8. Minor: freshness wording (§3); dev-power sampling assumption, "can lower", and the 1.86% bound (§8).
9. Optional: `check_freeze.py` also verifies that the registration commit has no TEST book and that the execution book digest matches both pins.

**r4 changes (GPT r3):**
1. The watchdog stays armed through the summary and finalisation.
2. Ledger writes use a lock and are atomic. The deadline exit is guaranteed by a killer timer and never depends on bookkeeping. The deadline stays terminal through the ledger checks in `start` and the retry rule.
3. Wording: `verifier_batch_rule` and §4 now describe ineligibility plus an amendment, not an automatic switch.
4. Optional: loads are persisted across attempts; there is a genuine interrupted-then-resumed test fixture, checked against the batched-generation rows.

**r5 changes (GPT r4):**
1. Supervisor-process redesign (§7): the stage runs as a child process killed at a deadline recorded durably before launch; the supervisor alone owns the state, ledger, terminal markers and `.done`; a late or concurrent finish is never `.done`; the watchdog thread, the ledger lock and the in-process ledger writes are removed.
2. Fail-closed: if the post-run bookkeeping fails, the attempt stays `running`, which is terminal (no retry, next start INCOMPLETE).
3. Precedence: terminal markers before `.done` in `start` and in the T1 eligibility check.
4. Real separate-process tests: deadline kill, admission stop, concurrent finish after the deadline, both writes failing (read-only results directories), a resume after a crash in the Falcon sender with Qwen's 12 selection rows already saved (byte-identical after resume, not re-sent), and the child refusing to run without the supervisor's token.

**r6 changes (GPT r5):**
1. Monotonic clock for the deadline, wait, elapsed charge, admission guard and completion decision; test with ±10-day wall-clock jumps.
2. Completion requires `.done` plus a recorded `done` outcome (start, retry tool, T1 eligibility); test fails the final state write after `.done`.
3. Directory fsync after every atomic replace and on new directories; test records the fsync targets.
4. Non-blocking: kill wording qualified; group kill after normal exit plus PDEATHSIG, with grandchild and supervisor-death tests; ledger scope stated, `finalise_s` reported; manual retry route labelled external-log adjudication.

**r6 wording-only edits after GPT's r6 ACCEPT** (no behaviour change): final-state-replace limitation disclosed; PDEATHSIG limits disclosed; `finalise_s` scope, ChildStage (`deadline_mono`) and guard (not a hard bound) docstrings corrected.

**Amendment A1 (2026-10-15):** see `AMENDMENT_E1c_A1.md`. D1 ended BUDGET_EXHAUSTED (terminal, kept); new dev stage D2 (cap 0.8 GPU-h from measured D1 timings) qualifies T1 in D1's place. T1 rules and success criteria unchanged.
