# E1d: draft plan v2 (DRAFT, not frozen)

Status: draft for review. Nothing is pre-registered or run. v1 = `1509f3f`; this v2 answers GPT r2 (`reviews/gpt_E1d_draft_r2.md`, 8 issues) and Grok r1 (`reviews/grok_E1d_draft_r1.md`, 5 points). The change table is §12. Numbers are labelled **measured** (file), **declared** (this plan) or **derived** (formula).

## 1. Motivation
E1c T1 (`v6/e1c/T1_REPORT.md`) was NOT MET only on break-even: 1,142 and 1,114 messages against a fixed 1,000-message line. Accuracy, coverage and payload saving passed in both directions, and no wrong ID was accepted (0/240 per sender). A fixed message count does not say whether the scheme pays off in a given deployment. E1d replaces it with a lifetime criterion on a workload W declared before any run. The result is conditional on W: it does not show that W is realistic.

## 2. What stays from E1c, and what changes
- **Unchanged:** models (Qwen2.5-7B, Falcon3-7B, nf4, free Kaggle T4), both directions, families F1/F2, E1b sender prompt and A10 parser, verifier prompt, grammar and acceptance rule (`v6/e1c/e1c/verifier.py`), receiver prompt and scoring, 4 cases per entry, supervisor, ledger, retry and `.done` rules.
- **Checker: unchanged, sender-side** (Grok #3, GPT #5). The verifier stays a stateless call to the sender model on the original prose (`PREREG_E1c.md` §4.2, `stages.py:160`). A rejected ID never leaves the sender: the message goes as prose only, so a rejected ID costs **0 network bytes**. Verifier compute (GPU-s and generated tokens per entry) is reported separately and is not converted into bytes. No receiver-side check is added, so no requalification of a moved checker is needed.
- **Changed:** (a) the receiver's dictionary is loaded only from the distribution artifact (§4.2), not from the book; (b) the byte endpoint (§4); (c) the gates and verdict (§8); (d) TEST size and data (§6, §7); (e) an optional dev-selected smaller-dictionary arm (§9).

## 3. Primary criterion: lifetime saving under W
Per direction:
- `total_prose(W) = M · P`
- `total_hybrid(W) = F(W) + M · (a·H + (1 − a)·P)`
- `S(W) = 1 − total_hybrid / total_prose`

where M = messages in W, a = share of messages that may use an ID (§5), P and H = family-weighted mean serialized bytes per message in the prose and hybrid arms (TEST, §4.1; H includes fallback prose), and F(W) = all dictionary distribution and update bytes in W (§4.2, §5). Messages that cannot use an ID (novel rule, version mismatch) cost P in the hybrid arm.

**Gate G4:** the one-sided 95% lower bound of S(W_base) > 0.20, in both directions (bootstrap in §3.1). The claim is limited to plain, uncompressed prose (§10).

### 3.1 Bootstrap (GPT #3)
- Unit: TEST entry e with family f. h_e and p_e = mean serialized message bytes over its 4 cases in the hybrid and prose arm. They are paired: each drawn entry brings both.
- Replicate: draw 315 entries with replacement within F1 and 315 within F2 (family sizes kept). H* = 0.5·mean_F1(h*) + 0.5·mean_F2(h*); P* likewise. Then `S* = 1 − (F(W) + M·(a·H* + (1 − a)·P*)) / (M·P*)`.
- F(W) is fixed and measured exactly; it is added in **every** replicate and never resampled. This is a ratio of workload totals, not a mean of per-message percentages.
- 10,000 replicates; seed `seed_of(95066, direction, "lifetime")` (E1b `seed_of`, Python `random.Random`, as `analysis.py:58`). Sorted ascending s[0..9999]; lower bound = s[500]. Pass iff s[500] > 0.20.
- Dependence: W messages are scenario draws from the TEST entry distribution; per-message bytes do not depend on which receiver instance gets them, so no receiver or conversation cluster is resampled. This is stated as an assumption.
- The interval covers sampling of entries only. It is conditional on W and does not validate W.

## 4. Byte accounting (Grok #1, #2; GPT #1, #2)
### 4.1 Primary boundary and serializer
- **Boundary:** everything sent sender → receiver in W: (i) every serialized message, **case text and framing included in both arms**; (ii) every full dictionary artifact; (iii) every delta update.
- **Excluded:** receiver responses (answers, acks, NACKs), transport overhead (TCP/TLS/HTTP), verifier and candidate-preparation compute (sender-local), disk storage.
- **Setup:** none. There is no per-conversation handshake; the sender knows each receiver's installed `dict_ver` from its own distribution log. This is 0 bytes in both arms, stated, not omitted.
- **Serializer (frozen):** canonical JSON, UTF-8, sorted keys, no whitespace, `ensure_ascii=False`: `{"c":<case text>,"p":<prose>}` or `{"c":<case text>,"i":<ID@vN#hash8>}` (`v6/e1d/tools/measure_dict_artifact.py: serialize`). Measured on the 960 T1 cases: framing = 15 B per message in both arms (no escaping occurs).
- Because case text and framing are common, they cancel in the byte difference but enter the denominator; this lowers S relative to a payload-only ratio, which is the intended, conservative choice.
- **Secondary (reported, not gated):** rule-payload-only saving and break-even (the E1c definition, `analysis.py:108`); payload + case (E1c `message_saving_payload_plus_case`); the lifetime curve; disk = artifact bytes × holders.

### 4.2 Dictionary distribution artifact (measured)
- **Format `E1D-DICT/1`:** a manifest line `E1D-DICT/1 kind=<full|delta> dict_ver=<v> base=<v|-> n=<entries> sha256=<body digest>`, then one line per member sorted by ID: `<ID>@v<ver>#<hash8> <entry text>`.
- **Loader:** checks the manifest, body digest, entry count, and `sha256(text)[:8] == hash8` per line; applies a delta only onto its stated base version; returns a book-like object that the **unchanged** `e1b.protocol.Dictionary` uses for `resolve` (`protocol.py:17`). Nothing else is needed by the receiver: resolve uses ID, version, hash8; the delegate expands to the text.
- **Membership:** exactly the entries a sender can pick: the TEST core entries plus their neighbours (arm A0). Spare entries from the 2n build and F3L entries are excluded. In E1d the receiver's Dictionary is built only from this artifact, so **the object shipped is the object charged**.
- **Measured on the E1c T1 book** (`v6/e1d/tools/measure_dict_artifact.py`, output `v6/e1d/measurements/dict_artifact_e1c_t1.json`; book sha256 `32f3a7c0…f850e2`):

| Object | Entries | Bytes | gzip-9 |
|---|---:|---:|---:|
| E1c registered cost (`analysis.py:89` `dict_bytes`, line sum) | 960 | 165,969 | n/a |
| **Minimal artifact** (117 B manifest + 165,969 B body) | 960 | **166,086** | 15,746 |
| Published membership `book['dictionary']`, line sum | 1,960 | 373,936 | n/a |
| Artifact of the published membership | 1,960 | 374,054 | 31,295 |
| Delta example: 24 core + 72 neighbours, v1 → v2 | 96 | 18,704 | n/a |

- **Explanation.** The minimal T1 artifact is E1c's registered 165,969 B plus a 117 B manifest; the line encoding is the one E1c priced. The 1,960-entry membership is 240 used core + 240 spare core (2n build, `book.py:45`) + 10 F3L + 1,470 neighbours; its line sum is 373,936 B, which **confirms GPT r2's figure independently**. The extra 1,000 entries could not be picked by any T1 sender. E1c charged the 960-entry cost while `Dictionary(B)` held 1,960 entries; E1d removes that gap by loading from the artifact.
- **Round trip:** 960/960 and 1,960/1,960 members resolve `ok` with identical text and receiver rule block; 200 non-members give `unknown_id`; stale version and wrong hash are rejected; a tampered body is rejected; v1 + delta equals the full artifact.
- **E1d scale (derived estimate only):** 630 core × 4 = 2,520 entries × 172.9 B mean line ≈ 435.8 KB. The E1d value is **measured** from the E1d TEST book by the same frozen script at the execution commit, before T1, and pinned.

## 5. Workload W (Grok #5, GPT #4)
W is a **declared SCENARIO, not a forecast**: no usage logs or deployment forecast exist. Values were chosen for the reasons given. Disclosure: they were written with E1c's public per-copy break-even (≈ 1,100 messages per 166 KB copy) in view, and the drafter did a rough order-of-magnitude check that the base case is not trivially decided; no E1d data exist and no projected S for W is recorded. Reviewers may change the values before freeze; after freeze they are fixed.

**W_base, per direction:**

| Item | Value | Reason |
|---|---|---|
| Horizon | 90 days | one quarter, a common review period for a rule set |
| Topology | 1 sender, 5 receiver instances active at all times | a small agent team; more than one copy so distribution matters |
| Traffic | 200 messages per receiver per day → M = 90,000 | an automated pipeline, about one rule-referencing request per receiver every 7 min; round number |
| Family mix | F1 50%, F2 50% | the only families; equals the TEST strata weights |
| Dictionary | the E1d TEST dictionary (630 rules + neighbours under A0) | measured artifact, no extrapolation |
| In-dictionary share | 90% of messages refer to a dictionary rule; 10% are novel rules (prose in both arms) | most traffic covered, some never is |
| Rule reuse (derived) | 0.89 × 90,000 / 630 ≈ 127 messages per rule (≈ 25 per receiver) | follows from the rows above |
| Version mismatch | 1% of messages refer to a rule the receiver's installed version lacks; the sender knows this and sends prose (cost P) | conservative vs 10% new rules × 1-day install lag / 30 days ≈ 0.3% |
| So a = | 0.89 | 1 − 0.10 − 0.01 |
| Initial provisioning | 1 full copy to the sender (conservative) + 5 to receivers, day 0, v1 | the sender also needs the dictionary for candidates |
| Churn | 1 receiver replaced every 30 days (days 15, 45, 75), each gets the current full artifact | 20%/month restarts or replacements |
| Cache | each holder keeps its copy for the horizon; no eviction, no shared cache; a replaced receiver has no copy | simple, no free reuse |
| Updates | delta every 30 days (days 30, 60), each adds 10% of v1 rules (63) + their neighbours, to the sender and 5 active receivers (12 transmissions); no full re-ship | rule sets grow; deltas, not full copies |
| Update pricing | delta = manifest + added entries × measured mean line bytes of the E1d v1 body; full artifact at v = v1 + (v − 1) × delta body | the delta rules do not exist in TEST, so they are priced by formula |

`F(W_base) = 7·A_v1 + A_v2 + A_v3 + 12·Δ` (7 = sender + 5 receivers + day-15 replacement).

**Sensitivity scenarios (declared, reported, not gates):**
- **W_low:** 50 messages per receiver per day (M = 22,500); all else as base.
- **W_churn:** every receiver replaced monthly (15 replacement copies), weekly deltas of 2.5% (12 deltas × 6 holders = 72 transmissions), mismatch 2%.
- **W_low+churn:** both.

**Secondary:** the minimum traffic (integer messages per receiver per day, all else W_base) at which s[500] > 0.20, by search over the same replicates; plus break-even and the lifetime curve.

## 6. Wrong-ID gate and TEST size (Grok #4, GPT #6)
- **Gate G3:** wrong IDs accepted / **all picks** (one sender pick per assigned TEST entry; an invalid pick counts in the denominator and cannot be a wrong accept), one-sided 95% Clopper–Pearson upper bound (`analysis.py:77`) ≤ 1%, per direction.
- **Required picks per direction** (computed with `cp_upper`): 0 errors needs ≥ 299; 1 error ≥ 473; 2 errors ≥ 628. E1c's 0/240 gives 1.24%.
- **TEST size: 315 entries per family = 630 picks per direction** (gate passes with up to 2 wrong accepts; at 630: 0 → 0.47%, 1 → 0.75%, 2 → 0.996%, 3 → 1.23%).
- **Independence:** picks are independent only if the entries are. Core rules are distinct (`check_unique`), texts fresh (§7), calls stateless. The binomial model is still an assumption about generated entries, not a natural population. The same entries serve both directions; each direction's gate uses its own sender's picks. The descriptive "wrong picks caught" count is reported separately.
- **Which entries go where:** sender + verifier on all 630 entries (G2, G3, bytes). Bytes are deterministic from the selection row and the book, so they are computed for all 630 × 4 cases without a receiver call. Receivers run on the first 120 per family in build order (240 entries, 960 messages, as E1c) for G1.
- **Compute (derived estimate):** from T1 timings, send+verify ≈ 1,480 s for 630 entries (both senders), receivers ≈ 10,370 s, loads ≈ 640 s: ≈ 3.5 GPU-h raw. The cap is set from the E1d dev stage at freeze.

## 7. Data (GPT #7)
- **TEST:** a fresh E1d TEST book, built only after freeze (as `PREREG_E1c.md` §9). Old books: E1b frozen, A9, E1c dev **and E1c TEST** (`book.py:47` lists only the first three and must be extended). E1c TEST cases and IDs are forbidden outright; its 240 core rule texts are forbidden as true rules (the E1c rule for dev, §3).
- **Feasibility first:** F2 rule space is small (E1c: 3 of 10 seeds built 120/family). Before freeze, build-only checks on throwaway seeds 99000–99900 (CPU, no model) test 315/family. Pre-declared ladder if infeasible, chosen by feasibility only: 237/family (474 picks, 1-error headroom), then 150/family (300 picks, 0-error). No smaller TEST.
- **Seeds:** E1d TEST seeds 95061–95066 (generator 95062, bootstrap 95066), disjoint from E1c (91xxx, 93xxx) and the throwaway ranges; the +100 seed rule applies.
- **Dev:** reuse the E1c dev book (80/family). It is already excluded from TEST and costs no extra F2 rule space. Dev is never confirmation.

## 8. Gates and verdict (GPT #8)
Per direction; SUCCESS only if all four pass in **both** directions, after completeness:

| Gate | Measure | Data | Pass |
|---|---|---|---|
| C | completeness (rows = assignment, as `analysis.py:14`, extended to 630 selection rows) | all | else INCOMPLETE |
| G1 | accuracy hybrid − prose, E1c bootstrap, lower bound (s[50] of 2,000) | 240 receiver entries | > −0.05 |
| G2 | ID coverage, accepted / assigned | 630 entries | ≥ 85% |
| G3 | wrong accepted / all picks, CP95 upper | 630 picks | ≤ 1% |
| G4 | S(W_base) one-sided 95% lower bound (§3.1) | 630 entries + F(W_base) | > 20% |

Verdicts: INCOMPLETE (any C failure), SUCCESS (all pass both directions), NOT MET otherwise, with the per-gate table. E1c's 30% payload and 1,000-message break-even criteria are dropped as gates and kept as secondary.

**Code that must be adapted (not reused as is):** E1c's `direction_result` and `verdict` enforce the old criteria (`analysis.py:113`, `stages.py:281`); `check_freeze.py` hardcodes `v6/e1c` paths (`check_freeze.py:9`); the code hash omits `tools/` (`code_hash.py`). E1d needs its own gate code, freeze paths, and a code hash that covers `tools/` (incl. the artifact script), the W file and the analysis. Focused tests: F(W) present in every replicate, copy and delta counts, the artifact round trip, both-direction enforcement, the G3 denominator.

## 9. Optional smaller-dictionary arm (dev only)
- **A0 (default):** E1c design: dictionary = core + 3 neighbours each; sender sees the true entry + its 3 neighbours.
- **A1 "no neighbours":** dictionary = core rules only (¼ of A0's entries). Retrieval: the sender's 4 candidates are the true entry + the 3 nearest other dictionary rules of the same family, by a frozen distance (number of differing fields among names and integer parameters, ties by summed absolute integer difference, then ID); positions shuffled with the E1c seed rule. Verifier and acceptance unchanged. This changes the 4-candidate task (distractors are other real rules, probably less confusable), so A1 is a different protocol and is qualified on dev.
- **Selection (dev only, pre-declared):** an arm is eligible if, on the 160 dev entries per sender, coverage ≥ 85% and wrong accepts = 0 for both senders, and the dev receiver subset shows no observed accuracy drop > 5 points. Among eligible arms, pick the higher minimum-over-directions dev point S(W_base), with F priced at TEST scale from dev mean line bytes; tie or none eligible → A0. The chosen arm is frozen in config; TEST runs only that arm.

## 10. Compressed prose (claim scope)
The primary claim is **limited to plain, uncompressed prose**. This is a choice of claim scope, not a correction of E1c. Reported secondary: both arms with per-message gzip-9 (mtime 0) of the serialized message, and gzip-9 artifacts (measured T1 minimal: 15,746 B). Neighbour lines compress very well, so a compressed comparison may differ a lot. A shared-state compressor (e.g. zstd with a trained dictionary) is not included; it would need its own distribution cost (open question 3).

## 11. Measure, don't assume; open questions
Every cost input is measured in a stage and cited (file, row), declared in W, or derived by formula. Growing stores name their read time (the artifact is read at the execution commit).

**Open questions (for Stefan, GPT, Grok):**
1. W_base values (§5): accept as a labelled scenario, or change any value before freeze? Who signs off?
2. If 315/family is infeasible, is the §7 ladder acceptable?
3. Compression baseline: per-message gzip-9 only, or also zstd with a trained dictionary and its distribution cost?
4. Run A1 at all, given it changes the sender task?
5. Count the sender's own provisioning copy (as declared), or treat the sender as the publisher (0 bytes)?

## 12. Change table (v1 → v2)
| Review point | Fix | Section |
|---|---|---|
| GPT r2 #1 "total bytes" undefined | one boundary, frozen serializer, case text + framing in both arms, setup = 0 stated, responses/transport excluded, disk separate | §4.1 |
| GPT r2 #2 subset vs 1,960-entry object | minimal artifact defined, measured (166,086 B), loader round trip, receiver loads only the artifact; 373,936 B confirmed | §4.2 |
| GPT r2 #3 bootstrap | ratio of totals, F fixed per replicate, paired entry clusters within families, 10,000, seed, s[500] | §3.1 |
| GPT r2 #4 W underspecified | concrete scenario table, provisioning, churn, cache, deltas, mismatch; 3 sensitivities | §5 |
| GPT r2 #5 verifier location | sender-side checker unchanged; rejected IDs 0 bytes; compute separate | §2 |
| GPT r2 #6 1% CP gate infeasible | all-picks denominator, CP95 ≤ 1%, 630 picks per direction | §6 |
| GPT r2 #7 TEST reuse, arm selection | fresh TEST excluding E1c TEST; feasibility ladder; dev-only A1 selection with retrieval specified | §7, §9 |
| GPT r2 #8 old verdict logic, freeze paths, code hash | E1d gate/verdict table; adaptation list | §8 |
| GPT r1 (informal) compression baseline, W justification | gzip secondary, claim scope; W labelled scenario with disclosure | §10, §5 |
| Grok #1 dictionary cost | as GPT r2 #2 | §4.2 |
| Grok #2 total bytes | as GPT r2 #1 | §4.1 |
| Grok #3 checker | keep sender-side, charge 0 for rejected IDs | §2 |
| Grok #4 wrong-ID gate | 299 / 473 / 628 picks; denominator all picks; TEST 630 | §6 |
| Grok #5 workload W | scenario with mix, reuse, churn, updates, mismatch | §5 |

Falcon3-7B-Instruct results will be produced using artificial intelligence technology from the Technology Innovation Institute (TII Falcon License).
