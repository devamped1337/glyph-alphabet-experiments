# E1d: draft plan v3 (DRAFT, not frozen)

Status: draft for review. Nothing is pre-registered or run. v1 = `1509f3f`, v2 = `22e4b58`. v3 applies Stefan's decisions of 2026-10-19, Grok's F2 preference (`reviews/grok_E1d_F2_fix.md`), GPT's F2 opinion (`reviews/gpt_E1d_F2_fix.md`) and GPT r3 (`reviews/gpt_E1d_draft_r3.md`). Change log: §13. Numbers are labelled **measured** (file), **declared** (this plan) or **derived** (frozen formula from measured inputs).

## 1. Framing and motivation
Stefan's framing (2026-10-19): E1d is a **proof of concept** about better and faster agent communication by sending fewer kilobytes, not a foolproof product. The dictionary is a **shared repository that agents keep up to date**, used across many agents and conversations. It is synced by each participant, not shipped fresh per receiver.

E1c T1 (`v6/e1c/T1_REPORT.md`) was NOT MET only on break-even (1,142 and 1,114 messages against a fixed 1,000). Accuracy, coverage and payload saving passed in both directions. E1d replaces the fixed break-even with a lifetime byte criterion on a workload W declared before any run. The result is conditional on W.

## 2. What stays from E1c, and what changes
- **Unchanged:** models (Qwen2.5-7B, Falcon3-7B, nf4, free Kaggle T4), both directions, families F1/F2, credit rates 2–9, the E1b sender prompt and A10 parser, the verifier prompt, grammar and acceptance rule (`v6/e1c/e1c/verifier.py`), receiver prompt and scoring, 4 cases per entry, supervisor, ledger, retry and `.done` rules.
- **Checker: unchanged, sender-side.** The verifier stays a stateless call to the sender model on the original prose (`PREREG_E1c.md` §4.2, `stages.py:160`). A rejected ID never leaves the sender, so it costs **0 network bytes**. Verifier compute is reported separately (§11).
- **Changed:** (a) the receiver's dictionary is loaded only from the repository artifact (§4.2), not from the book; (b) the byte endpoint and W (§3–§5); (c) the gates (§8); the wrong-ID gate of v2 is **dropped** (§6); (d) TEST size (§6); (e) F2 gets three new role pairs (§7); (f) speed is reported (§11).

## 3. Primary criterion: lifetime saving under W
Per direction d:
- `total_prose_d = M_d · P_d`
- `total_hybrid_d = F_d + M_d · (a·H_d + (1 − a)·P_d)`
- `S_d = 1 − total_hybrid_d / total_prose_d`

M_d = messages in direction d under W; a = share that may use an ID (§5); P_d, H_d = family-weighted mean serialized bytes per message, prose and hybrid arm (H includes fallback prose); F_d = the direction's share of repository sync and update traffic (§5). Messages that cannot use an ID cost P in the hybrid arm.

**Gate G3:** one-sided 95% lower bound of S_d(W_base) > 0.20 in both directions. The claim is limited to plain, uncompressed prose (§10).

### 3.1 Bootstrap
- Unit: TEST entry e. h_e, p_e = mean serialized message bytes over its 4 cases, hybrid and prose, paired.
- Replicate: draw 80 entries with replacement within F1 and 80 within F2. H* = 0.5·mean_F1(h*) + 0.5·mean_F2(h*); P* likewise. `S* = 1 − (F_d + M_d·(a·H* + (1 − a)·P*)) / (M_d·P*)`.
- F_d is a **fixed, derived scenario cost** (measured v1 artifact bytes plus the frozen formulas in §5). It is added in every replicate and never resampled.
- 10,000 replicates, seed `seed_of(95066, direction, "lifetime")`, Python `random.Random`. Sorted ascending s[0..9999]; lower bound = s[500]. Pass iff s[500] > 0.20.
- Assumption: per-message bytes do not depend on which participant or conversation carries them, so no participant or conversation cluster is resampled.
- The interval covers entry sampling only. It is conditional on W and on the §5 formulas, and does not validate W.

## 4. Byte surfaces (named separately)
| Surface | What | In the primary sum? |
|---|---|---|
| **1. Repository storage** | artifact bytes held on disk by each participant and by the repository host | no, reported |
| **2. Sync and update traffic** | full syncs (joins) and delta syncs, downloads by participants plus the maintainer's upload of each delta | **yes** (F) |
| **3. Per-message transmission** | serialized sender → receiver messages, both arms | **yes** (M·…) |

### 4.1 Per-message boundary and serializer
- Every serialized message, **case text and framing included in both arms**. Excluded: receiver responses (answers, acks), transport overhead (TCP/TLS/HTTP), sender-local compute.
- **Setup: 0 bytes.** There is no per-conversation handshake; the sender knows each participant's synced version from the repository's sync log.
- **Serializer (frozen):** canonical JSON, UTF-8, sorted keys, no whitespace, `ensure_ascii=False`: `{"c":<case>,"p":<prose>}` or `{"c":<case>,"i":<ID@vN#hash8>}` (`v6/e1d/tools/measure_dict_artifact.py: serialize`). **Measured** on the 960 T1 cases: 15 B framing per message in both arms.
- Secondary: rule-payload-only saving and break-even (E1c definition, `analysis.py:108`), payload + case, and the lifetime curve.

### 4.2 Repository artifact (v1 measured)
- **Format `E1D-DICT/1`:** manifest line `E1D-DICT/1 kind=<full|delta> dict_ver=<v> base=<v|-> n=<entries> sha256=<body digest>`, then one line per member sorted by ID: `<ID>@v<ver>#<hash8> <entry text>`.
- **Loader:** checks manifest, body digest, count and `sha256(text)[:8] == hash8`; applies a delta only onto its base version; feeds the **unchanged** `e1b.protocol.Dictionary` (`protocol.py:17`).
- **Membership:** TEST core entries plus their neighbours (arm A0); no spare 2n-build entries, no F3L. The receiver's Dictionary is built only from the artifact, so the object shipped is the object charged.
- **Measured on the E1c T1 book** (`measurements/dict_artifact_e1c_t1.json`): minimal artifact **166,086 B** (960 entries = 117 B manifest + E1c's 165,969 B); published 1,960-entry membership 373,936 B line sum (confirms GPT r2), 374,054 B as artifact; gzip-9 15,746 B and 31,295 B; round trip, rejection and delta checks all pass. Per core rule (rule + 3 neighbours): 691.5 B.
- **E1d v1** is measured by the same script from the E1d TEST book at the execution commit, before T1, and pinned. Derived estimate: 160 rules × 691.5 B ≈ 110.6 KB.

## 5. Workload W
W is a declared **scenario, not a forecast**. Values were chosen for the reasons given, with E1c's public break-even in view; no projected S for any W is recorded. After freeze they are fixed.

### 5.1 W_base: one shared, agent-maintained repository
| Item | Value | Reason |
|---|---|---|
| Horizon | 90 days | one quarter |
| Participants | 20 agents at day 0, each both sender and receiver, each holding one synced copy | Stefan's framing: many agents share one repository |
| Traffic | 100 messages sent per agent per day → 180,000 messages, M_d = 90,000 per direction | a busy automated team; round number |
| Conversations | many; average 10 messages each (≈ 18,000); 0 setup bytes each | conversations do not change bytes in this design |
| Family mix | F1 50%, F2 50% | the only families; equals the TEST strata |
| Dictionary | the E1d TEST dictionary at v1 (160 rules + neighbours) | measured artifact |
| In-dictionary share | 90%; 10% novel rules go as prose in both arms | most traffic covered |
| Version mismatch | 1% go as prose (sender sees from the sync log that the receiver lacks the rule) | conservative vs 4 new rules per 160, 1-day sync lag, weekly deltas ≈ 0.4% |
| a | 0.89 | 1 − 0.10 − 0.01 |
| Joins (churn) | 2 new participants on days 15, 45, 75 (6 joins); leavers cost nothing | 10% joins per month |
| Updates | an agent publishes a delta every 7 days (days 7, 14, …, 84: 12 deltas) | agents keep the repository up to date |
| Delta size | per family, ceil(0.02 × 80) = 2 new rules + their neighbours | 2% weekly growth relative to v1 |
| Cache | every participant keeps its copy for the horizon; syncs are incremental; no eviction | a maintained repository |
| Allocation | F_d = F_total / 2 (pro rata by messages; M_d is half of all messages) | sync bytes serve all traffic once |

### 5.2 Frozen lifecycle formulas (derived from measured v1 bytes)
- Version after k deltas: v = 1 + k. On a day with both a delta and a join, the delta is published first; a joiner gets v = 1 + (number of deltas published on or before its join day). W_base joiners get v3 (day 15), v7 (day 45), v11 (day 75).
- Rules per delta per family: `ceil(r × n_core_v1_per_family)`, r relative to v1 (no compounding).
- Bytes per added rule: `L_rule = body_v1 / n_core_v1` (measured v1 body; A0 includes the 3 neighbour lines).
- Delta body: `ceil(added_rules × L_rule)`. Delta manifest: the exact length of its manifest string (§4.2) for that version and entry count.
- Full artifact at version v: body `body_v1 + (v − 1) × delta_body`, plus its exact manifest length.
- `F_total = Σ_day0 participants A_v1 + Σ_joins A_v(join) + Σ_deltas (participants at that day + 1 upload) × Δ_v`, where Δ_v has the constant delta body and the exact manifest length for version v.
  W_base: 20·A_v1 + 2·(A_v3 + A_v7 + A_v11) + 21·(Δ_2 + Δ_3) + 23·(Δ_4 + … + Δ_7) + 25·(Δ_8 + … + Δ_11) + 27·(Δ_12 + Δ_13).
- gzip variants of future artifacts (secondary only): measured v1 gzip ratio × derived bytes.

### 5.3 Sensitivity scenarios (reported, not gates)
- **W_copy (conservative, v2 model):** per direction, 1 sender + 5 receivers each get their own full copy at day 0 (v1); one receiver replaced on days 15 (gets v1), 45 (v2), 75 (v3); deltas on days 30 and 60 of ceil(0.10 × 80) = 8 rules per family, sent to the sender and 5 receivers; M_d = 90,000; F charged in full to that direction.
- **W_low:** W_base with 25 messages per agent per day (M_d = 22,500).
- **W_churn:** W_base with 4 joins on days 15, 45, 75 (12 joins), deltas every 3 days (days 3, 6, …, 87: 29 deltas) of ceil(0.01 × 80) = 1 rule per family, mismatch 2%.
- **W_low+churn:** both.
- **Secondary:** the minimum messages per agent per day (integer, all else W_base) at which s[500] > 0.20.

## 6. TEST size, and wrong IDs as a reported metric
**Wrong-ID gate dropped (Stefan, 2026-10-19).** Wrong IDs accepted are reported descriptively, as in E1c: count, rate over all picks, and the one-sided 95% Clopper–Pearson upper bound (`analysis.py:77`), per direction and separately for new-pair F2 entries. At 160 picks, 0 errors gives an upper bound of 1.86%. Wrong picks caught are reported too.

**TEST size: 80 entries per family = 160 entries and 640 messages per direction**, receivers on all of them. It is sized from E1c T1's observed rates (`results/T1/`), and the justification uses those rates, stated here:
- **G1 accuracy:** T1 per-entry difference SD was 0.036 (Qwen→Falcon) and 0.050 (Falcon→Qwen), with 2 and 10 entries non-zero. At 80 per family the approximate CI half-width is 0.006–0.008, far inside the 0.05 margin; it stays inside if the SD triples on new roles.
- **G2 coverage:** T1 coverage was 92.9% and 95.4%. At 160 entries the chance of observing < 85% is about 0.02% and < 0.01% at those rates, and about 1.7% if true coverage were 90%.
- **G3 bytes:** bootstrapping T1 entries at 80 per family gives SD 0.008–0.011 for the hybrid/prose message-byte ratio, so the one-sided lower bound sits about 1.2–1.5 points below the point estimate (about 1.0–1.3 at 120 per family). The gain from a larger TEST is small.
- **Why not larger:** the fresh F2 pool is finite (Grok). 80 per family uses 80 fresh F2 texts for TEST cores (§7). E1c's 120 per family would use 40 more for little precision.
- **Compute (derived estimate):** from T1 timings, send+verify ≈ 380 s, receivers ≈ 6,900 s, loads ≈ 640 s: ≈ 2.2 GPU-h raw. The cap is set from the E1d dev stage at freeze.

## 7. Data and the F2 fix (Option A)
**Counts (measured on CPU, `tools/count_f2_fresh.py`, `measurements/f2_fresh_counts.json`):**
- F2 with the 10 old pairs: 560 texts. Fresh against old true rules (the E1c rule): 83. Fresh against **all** E1b/E1c entry texts of any kind (the E1d rule below): **5**.
- Each new role pair adds 56 texts (8 × 7 ordered rates, 2–9).
- **Three new pairs: 173 fresh F2 texts.** Simulating the builder (2n draws, keep n distinct; 2,000 trials): dev 12 cores, then TEST 80 cores, fill in 99.95–100% of trials, with at least 49–51 texts left unused. Two pairs: 117 texts, 30% fill. Four pairs: 229 texts, at least 94 left.
- F1 is not short: 14,919 of 16,800 F1 texts are fresh under the E1d rule.

**Generation method (frozen):**
- F2 role pairs = the 10 E1b pairs + **("baker", "porter"), ("potter", "bearer"), ("tanner", "loader")**, in this order. Same template (`render_def`, `render_message`, labels, cases, neighbours), credits 2–9, uniform choice over pairs then rates, as `cases.py:44`.
- New role words: single lowercase ASCII words (verifier grammar `[A-Za-z]+`), consonant-initial (templates say "a {x}"), common trade nouns of similar length. CPU check: none appears in any E1b/E1c entry or case text, and none collides with old roles, scheme nouns or units.
- E1d passes the extended list through its own builder code. It does not edit `v6/e1b/e1b/cases.py`, so E1b and E1c hashes stay valid.
- **Step-up rule (feasibility only):** if fewer than 8 of 10 throwaway seeds build (below), add the next pair from ("farmer", "packer"), ("cooper", "driver"), ("grocer", "runner"), one at a time, up to six new pairs in total, and repeat. Decided before freeze; never from model outcomes.

**Exclusion list (frozen):** a TEST or dev true rule may not use any entry text of **any kind**, and no case text or entry ID may be reused, from the E1b frozen book, the E1b A9 book, the E1c dev book, the E1c TEST book, and the E1d dev-new material (its core entries, their neighbours and its cases). `book.py:47` lists only the first three and must be replaced. Canary pool as before.

**Seeds and the order of steps before freeze:**
1. **Throwaway seeds 99000–99900** (10 seeds, CPU only, never shown to a model, not used afterwards). Each builds the dev-new and TEST-size books and checks: the build succeeds; `verify` passes (gold labels computed); for every core and neighbour, the verifier's expected line for the rendered prose parses under the frozen grammar and matches `expected_spec`; freshness against the exclusion list; branch balance; distinct core. Results are committed.
2. **E1d dev-new book** (seed 94062): **12 F2 core entries, 4 per new pair**, 4 cases each, to run the new vocabulary through both models' sender, verifier and receiver paths with the existing message-style mix. This uses 12 fresh texts plus their neighbours. The E1c dev book is reused for everything else (no fresh texts). Reusing E1c dev alone cannot qualify the new roles (GPT).
3. Freeze, then build the E1d TEST book (seeds 95061–95066, generator 95062, +100 seed rule).

**F2 pair reporting:** with 5 old-pair fresh texts left, F2 TEST cores will be almost all new-pair. Coverage, accuracy, wrong IDs and bytes are reported separately for new-pair and old-pair F2 entries, next to E1c T1 F2 as the old-pair reference. A difference is a reported finding, not a gate.

## 8. Gates and verdict
Per direction; SUCCESS only if all pass in **both** directions, after completeness:

| Gate | Measure | Data | Pass |
|---|---|---|---|
| C | completeness (rows = assignment, as `analysis.py:14`) | all | else INCOMPLETE |
| G1 | accuracy hybrid − prose, E1c bootstrap, lower bound s[50] of 2,000 | 160 entries, 640 messages | > −0.05 |
| G2 | ID coverage, accepted / assigned | 160 entries | ≥ 85% |
| G3 | S_d(W_base) one-sided 95% lower bound (§3.1) | 160 entries + F_d | > 20% |

Reported, not gated: wrong IDs (§6), sensitivities (§5.3), compressed baselines (§10), speed (§11), per-pair F2 results (§7), E1c's 30% payload and break-even.

**Code to adapt:** E1c's `direction_result` and `verdict` enforce the old criteria (`analysis.py:113`, `stages.py:281`); `check_freeze.py` hardcodes `v6/e1c` paths; the code hash omits `tools/`. E1d needs its own gate code, freeze paths, and a hash covering `tools/` (incl. both counting scripts), the W file, the builder and the analysis. Tests: F_d in every replicate, the §5.2 event counts and versions, the artifact round trip, both-direction enforcement.

## 9. Optional smaller-dictionary arm (dev only)
- **A0 (default):** dictionary = core + 3 neighbours; the sender sees the true entry + its neighbours.
- **A1 "no neighbours":** dictionary = core only. Sender candidates = true entry + the 3 nearest other same-family dictionary rules (frozen distance: number of differing names and integer parameters, ties by summed absolute integer difference, then ID). This changes the sender task, so A1 is a different protocol, qualified on dev.
- Selection on dev only: eligible if dev coverage ≥ 85% for both senders and no observed accuracy drop > 5 points; pick the higher minimum-over-directions dev S(W_base); tie or none → A0. TEST runs only the frozen arm.

## 10. Compressed prose (claim scope)
The primary claim is **limited to plain, uncompressed prose**, a choice of claim scope. Reported secondary: both arms with per-message gzip-9 (mtime 0), and gzip-9 artifacts and syncs.

## 11. Speed (secondary, reported; no new compute)
From fields the runs already log (`exchange_*.jsonl`, `select_*.jsonl`), per direction and arm:
- wire bytes per message (surface 3) as the transmission-time proxy;
- receiver `prompt_tokens`, `gen_tokens` and `latency_s` per exchange. Note: in the ID arm the receiver's delegate expands the ID to the full text, so receiver tokens and latency should be close to prose; the saving is in transmission, not receiver compute;
- ID-arm sender-side overhead: `sender_latency_s`, `sender_gen_tokens`, `verifier_latency_s` per entry.
Latencies are batch-level measurements on a shared T4 and are descriptive only.

## 12. Open questions (for Stefan, GPT, Grok)
1. W_base values (§5.1): accept as a labelled scenario, or change any value before freeze?
2. Is 12 dev-new entries (4 per new pair) enough to qualify the new vocabulary, given the fresh pool?
3. Run arm A1 at all, given it changes the sender task?
4. Compression: per-message gzip-9 only, or also zstd with a trained dictionary and its distribution cost?

## 13. Change log
**v3 (2026-10-19)**

| Point | Fix | Section |
|---|---|---|
| Stefan: drop the wrong-ID gate. Quoted: E1d is "a proof of concept about reducing kilobytes for better transmission, not a foolproof product", and "the 1% gate was an addition in my earlier draft, not something E1c had" | wrong IDs reported only, with CP95 upper bound | §6, §8 |
| Stefan: TEST sized from accuracy and byte-bound needs | 80 per family, justified from T1 rates; uses 80 fresh F2 texts | §6 |
| Stefan: the dictionary is a shared, agent-maintained repository, synced once per participant and spread over all traffic; keep per-receiver copies as a conservative check; name byte surfaces; add speed | W_base reframed; W_copy sensitivity; three surfaces; speed metric | §1, §4, §5, §11 |
| GPT r3 High / Grok F2 fix: only 83 (strictly 5) fresh old-pair F2 texts | Option A: 3 new role pairs (173 fresh texts), frozen method, strict exclusion list, step-up rule up to 6, throwaway seeds first, per-pair reporting | §7 |
| GPT F2 opinion: pool size ≠ distinct sampled cores; similar familiarity/length of roles; E1c dev cannot qualify new roles; remeasure costs | builder simulation; role-word rules and leak check; dev-new book; v1 artifact measured at execution | §7, §4.2 |
| GPT r3 Medium #2: lifecycle costs called "measured exactly" | F labelled fixed, derived from measured v1 bytes, with frozen formulas incl. manifests and rounding | §3.1, §5.2 |
| GPT r3 Medium #3: churn sensitivity not reproducible | version per joiner/replacement, event ordering, ceil rule relative to v1, explicit F formula | §5.2, §5.3 |
| Open questions resolved | sender copy (shared repo: one copy per participant); feasibility ladder (replaced by §7) | §5, §7 |

**v2 (22e4b58):** answered GPT r2 #1–8 and Grok r1 #1–5: frozen byte boundary and serializer; measured minimal artifact and loader; sender-side checker kept; ratio bootstrap; W as a scenario; E1d gate table; compressed prose as claim scope.

Falcon3-7B-Instruct results will be produced using artificial intelligence technology from the Technology Innovation Institute (TII Falcon License).
