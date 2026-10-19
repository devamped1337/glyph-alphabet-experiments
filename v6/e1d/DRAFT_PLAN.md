# E1d: draft plan v5 (DRAFT, not frozen)

Status: draft for review. Nothing is pre-registered or run. v1 = `1509f3f`, v2 = `22e4b58`, v3 = `da0fe97`, v4 = `4ffdc76`. v5 closes GPT r5 (`reviews/gpt_E1d_draft_r5.md`, 2 issues) and Grok's v4 review (`reviews/grok_E1d_draft_v4.md`). Change log: §14. Numbers are labelled **measured** (file), **declared** (this plan) or **derived** (frozen formula from measured inputs).

## 1. Framing and motivation
Stefan's framing (2026-10-19): E1d is a **proof of concept** about better and faster agent communication by sending fewer kilobytes, not a foolproof product. The dictionary is a **shared repository that agents keep up to date**, used across many agents and conversations. Each participant syncs it; it is not shipped fresh per receiver.

E1c T1 (`v6/e1c/T1_REPORT.md`) was NOT MET only on break-even (1,142 and 1,114 messages against a fixed 1,000). Accuracy, coverage and payload saving passed in both directions. E1d replaces the fixed break-even with a lifetime byte criterion on a workload W declared before any run. The result is conditional on W.

## 2. What stays from E1c, and what changes
- **Unchanged:** models (Qwen2.5-7B, Falcon3-7B, nf4, free Kaggle T4), both directions, families F1/F2, credit rates 2–9, the E1b sender prompt and A10 parser, the verifier prompt, grammar and acceptance rule (`v6/e1c/e1c/verifier.py`), receiver prompt and scoring, 4 cases per entry, supervisor, ledger, retry and `.done` rules.
- **Checker: unchanged, sender-side.** The verifier stays a stateless call to the sender model on the original prose (`PREREG_E1c.md` §4.2, `stages.py:160`). A rejected ID never leaves the sender, so it costs **0 network bytes**. Verifier compute is reported separately (§12).
- **Changed:** (a) the receiver's dictionary is loaded only from the repository artifact (§4.2); (b) the byte endpoint and W (§3–§5); (c) the gates (§9); wrong IDs are reported, not gated (§6); (d) TEST size (§6); (e) F2 TEST uses three new role pairs only (§7); (f) an explicit dev eligibility table (§8); (g) speed is reported (§12); (h) **one arm only: A0** (the E1c design, dictionary = core + 3 neighbours, sender sees the true entry + its neighbours). The smaller "no neighbours" arm A1 is deferred (§14).

## 3. Primary criterion: lifetime saving under W
Per direction d:
- `total_prose_d = M_d · P_d`
- `total_hybrid_d = F_d + M_d · (a·H_d + (1 − a)·P_d)`
- `S_d = 1 − total_hybrid_d / total_prose_d`

M_d = messages in direction d under W; a = share that may use an ID (§5); P_d, H_d = family-weighted mean serialized bytes per message, prose and hybrid arm (H includes fallback prose); F_d = the direction's share of repository sync and update traffic (§5). Messages that cannot use an ID cost P in the hybrid arm.

**Gate G3:** one-sided 95% lower bound of S_d(W_base) > 0.20 in both directions. The claim is limited to plain, uncompressed prose (§11).

### 3.1 Bootstrap
- Unit: TEST entry e. h_e, p_e = mean serialized message bytes over its 4 cases, hybrid and prose, paired.
- Replicate: draw 80 entries with replacement within F1 and 80 within F2. H* = 0.5·mean_F1(h*) + 0.5·mean_F2(h*); P* likewise. `S* = 1 − (F_d + M_d·(a·H* + (1 − a)·P*)) / (M_d·P*)`.
- F_d is a **fixed, derived scenario cost** (measured v1 artifact bytes plus the frozen formulas in §5.2). It is added in every replicate and never resampled.
- 10,000 replicates, seed `seed_of(95066, direction, "lifetime")`, Python `random.Random`. Sorted ascending s[0..9999]; lower bound = s[500]. Pass iff s[500] > 0.20.
- Assumption: per-message bytes do not depend on which participant or conversation carries them, so no participant or conversation cluster is resampled.
- The interval covers entry sampling only. It is conditional on W and on the §5.2 formulas, and does not validate W.

## 4. Byte surfaces (named separately)
| Surface | What | In the primary sum? |
|---|---|---|
| **1. Repository storage** | artifact bytes on disk at each participant and at the repository host | no, reported |
| **2. Sync and update traffic** | full syncs (initial and joins), delta syncs to participants, and the maintainer's one upload per delta | **yes** (F) |
| **3. Per-message transmission** | serialized sender → receiver messages, both arms | **yes** (M·…) |

### 4.1 Per-message boundary and serializer
- Every serialized message, **case text and framing included in both arms**. Excluded: receiver responses (answers, acks), transport overhead (TCP/TLS/HTTP), sender-local compute.
- **Setup: 0 bytes.** There is no per-conversation handshake; the sender knows each participant's synced version from the repository's sync log.
- **Serializer (frozen):** canonical JSON, UTF-8, sorted keys, no whitespace, `ensure_ascii=False`: `{"c":<case>,"p":<prose>}` or `{"c":<case>,"i":<ID@vN#hash8>}` (`tools/measure_dict_artifact.py: serialize`). **Measured** on the 960 T1 cases: 15 B framing per message in both arms.
- Secondary: rule-payload-only saving and break-even (E1c definition, `analysis.py:108`), payload + case, and the lifetime curve.

### 4.2 Repository artifact (v1 measured)
- **Format `E1D-DICT/1`:** manifest line `E1D-DICT/1 kind=<full|delta> dict_ver=<v> base=<v|-> n=<entries> sha256=<body digest>`, then one line per member sorted by ID: `<ID>@v<ver>#<hash8> <entry text>`.
- **Loader:** checks manifest, body digest, count and `sha256(text)[:8] == hash8`; applies a delta only onto its base version; feeds the **unchanged** `e1b.protocol.Dictionary` (`protocol.py:17`).
- **Membership:** TEST core entries plus their neighbours (A0, the only arm); no spare 2n-build entries, no F3L. The receiver's Dictionary is built only from the artifact, so the object shipped is the object charged.
- **Measured on the E1c T1 book** (`measurements/dict_artifact_e1c_t1.json`): minimal artifact **166,086 B** (960 entries = 117 B manifest + E1c's 165,969 B); published 1,960-entry membership 373,936 B line sum (confirms GPT r2), 374,054 B as artifact; gzip-9 15,746 B and 31,295 B. Per core rule (rule + 3 neighbours): 691.5 B.
- **E1d v1** is measured by the same script from the E1d TEST book at the execution commit, before T1, and pinned. Derived estimate: 160 rules × 691.5 B ≈ 110.6 KB.

## 5. Workload W
W is a declared **scenario, not a forecast**. Values were chosen for the reasons given, with E1c's public break-even in view; no projected S for any W is recorded. After freeze they are fixed.

### 5.1 W_base: one shared, agent-maintained repository
| Item | Value | Reason |
|---|---|---|
| Horizon | 90 days | one quarter |
| Participants | 20 agents at day 0, each both sender and receiver, each holding one synced copy | many agents share one repository |
| Traffic | **aggregate traffic is held constant at 180,000 messages (M_d = 90,000 per direction), whatever the joins.** Nominal rate: 100 messages per initial agent per day; joiners take a share of the same traffic and add none | a busy automated team; joins change sync bytes only, so the traffic term is not inflated by churn |
| Conversations | many; average 10 messages each (≈ 18,000); 0 setup bytes each | conversations do not change bytes in this design |
| Family mix | F1 50%, F2 50% | the only families; equals the TEST strata |
| Dictionary | the E1d TEST dictionary at v1 (160 rules + neighbours) | measured artifact |
| In-dictionary share | 90%; 10% novel rules go as prose in both arms | most traffic covered |
| Version mismatch | 1% go as prose (the sender sees from the sync log that the receiver lacks the rule) | conservative vs 4 new rules per 160, 1-day sync lag, weekly deltas ≈ 0.4% |
| a | 0.89 | 1 − 0.10 − 0.01 |
| Joins | 2 new participants on days 15, 45, 75 (6 joins); leavers cost nothing | 10% joins per month |
| Updates | an agent publishes a delta every 7 days (days 7, 14, …, 84: 12 deltas) | agents keep the repository up to date |
| Delta size | per family, ceil(0.02 × 80) = 2 new rules + their neighbours | 2% weekly growth relative to v1 |
| Cache | every participant keeps its copy for the horizon; syncs are incremental; no eviction | a maintained repository |
| Allocation | F_d = F_total / 2 (pro rata by messages) | sync bytes serve all traffic once |

### 5.2 Frozen lifecycle formulas (derived from measured v1 bytes)
- **Event order.** Version after k deltas: v = 1 + k. A delta goes to the **participants present immediately before it** (plus one maintainer upload). On a day with both a delta and joins, the delta is processed first; joiners then get the **then-current full version** and do **not** pay that day's delta.
- Joiner version = 1 + (number of deltas published on or before its join day). W_base joiners: v3 (day 15), v7 (day 45), v11 (day 75).
- Rules per delta per family: `ceil(r × n_core_v1_per_family)`, r relative to v1 (no compounding).
- Bytes per added rule: `L_rule = body_v1 / n_core_v1` (measured v1 body; A0 includes the 3 neighbour lines).
- Delta body: `ceil(added_rules × L_rule)`; delta manifest: the exact length of its manifest string (§4.2) for that version and entry count. Δ_v = delta into version v.
- Full artifact at version v: body `body_v1 + (v − 1) × delta_body`, plus its exact manifest length.
- `F_total = Σ_day0 A_v1 + Σ_joins A_v(join) + Σ_deltas (participants immediately before + 1) × Δ_v`.
- **W_base:** participants before each delta: 20 (days 7, 14), 22 (21–42), 24 (49–70), 26 (77, 84).
  F_total = 20·A_1 + 2·(A_3 + A_7 + A_11) + 21·(Δ_2 + Δ_3) + 23·(Δ_4 + … + Δ_7) + 25·(Δ_8 + … + Δ_11) + 27·(Δ_12 + Δ_13).
- gzip variants of future artifacts (secondary only): measured v1 gzip ratio × derived bytes.

### 5.3 Sensitivity scenarios (reported, not gates)
- **W_copy (conservative, v2 model).** Per direction, 6 holders: 1 sender + 5 receivers, each with its own full copy at day 0 (v1). One receiver is replaced on days 15 (gets v1), 45 (v2) and 75 (v3); a replacement takes over its predecessor's traffic, so M_d stays 90,000. Deltas on days 30 and 60 of ceil(0.10 × 80) = 8 rules per family go to the 6 holders present before them. **The maintainer's upload is counted (+1 per delta), as in W_base.** F is charged in full to the direction. F_copy = 6·A_1 + (A_1 + A_2 + A_3) + 7·(Δ_2 + Δ_3).
- **W_low:** W_base with aggregate traffic 45,000 (M_d = 22,500; nominal 25 per initial agent per day).
- **W_churn:** W_base with 4 joins on days 15, 45, 75 (12 joins), deltas every 3 days (days 3, 6, …, 87: 29 deltas) of ceil(0.01 × 80) = 1 rule per family, mismatch 2% (a = 0.88); traffic still 180,000. Joins coincide with deltas on days 15, 45, 75: delta first, joiners get v6, v16, v26. Participants before each delta: 20 (days 3–15), 24 (18–45), 28 (48–75), 32 (78–87).
  F_churn = 20·A_1 + 4·(A_6 + A_16 + A_26) + 21·(Δ_2 + … + Δ_6) + 25·(Δ_7 + … + Δ_16) + 29·(Δ_17 + … + Δ_26) + 33·(Δ_27 + … + Δ_30).
- **W_low+churn:** both.
- **Secondary:** the minimum aggregate traffic (multiples of 1,800 messages = 1 per initial agent per day, all else W_base) at which s[500] > 0.20.

## 6. TEST size, and wrong IDs as a reported metric
**Wrong-ID gate dropped (Stefan, 2026-10-19).** Wrong IDs accepted are reported descriptively, as in E1c: count, rate over all picks, and the one-sided 95% Clopper–Pearson upper bound (`analysis.py:77`), per direction and per new role pair (§10). At 160 picks, 0 errors gives 1.85%. Wrong picks caught are reported too.

**TEST size: 80 entries per family = 160 entries and 640 messages per direction**, receivers on all of them, sized from E1c T1's observed rates (`results/T1/`):
- **G1 accuracy:** T1 per-entry difference SD was 0.036 and 0.050 (2 and 10 non-zero entries). At 80 per family the approximate CI half-width is 0.006–0.008, far inside the 0.05 margin; it stays inside if the SD triples on new roles.
- **G2 coverage:** T1 coverage was 92.9% and 95.4%. At 160 entries the chance of observing < 85% is about 0.02% and < 0.01% at those rates, and about 1.7% if true coverage were 90%.
- **G3 bytes (measured sizing, `tools/size_byte_bound.py`, `measurements/byte_bound_sizing.json`; seed 95100, 10,000 replicates, 15 B framing):** at 80 per family, the SD of the hybrid/prose message-byte ratio H*/P* is 0.0107 (Qwen→Falcon) and 0.0086 (Falcon→Qwen). Its one-sided 95% distance above the point is 1.86 and 1.52 points; times a = 0.89 the S lower bound sits about **1.65 and 1.36 points** below the point estimate. This agrees with GPT r4 (1.64 / 1.36). At 120 per family it would be 1.35 / 1.09 points, a gain of about 0.3 points. The F/(M·P) term also moves with P*; that part depends on W and is left to the real bootstrap (no W-level projection is computed).
- **Why not larger:** the fresh F2 pool is finite (Grok; §7). E1c's 120 per family would use 40 more fresh F2 texts for about 0.3 points.
- **Compute (derived estimate):** from T1 timings, send+verify ≈ 380 s, receivers ≈ 6,900 s, loads ≈ 640 s: ≈ 2.2 GPU-h raw. From E1c D2 per-row rates (2.14 s per entry sender+verifier, 4.82 s per receiver message, 261 s per load): 2.0 h raw, 2.5 h with +25%. **Planned TEST cap: 4.0 GPU-h**, provisional; at freeze it is confirmed only if the D1-E1d projection (+25%) is ≤ 4.0 h (check D5).
- **Dev stage D1-E1d (§8), derived estimate:** E1c D2 took 1,461 s (0.41 GPU-h) for the same E1c-dev work; dev-new adds about 50 s of sender+verifier and about 930 s of receivers (48 messages × 2 arms × 2 directions × 4.82 s): ≈ 2,440 s ≈ 0.68 GPU-h. With all loads at the 420 s prior: ≈ 0.76 h. **Planned dev cap: 1.0 GPU-h.** Total planned ≈ 3 GPU-h, within the free weekly Kaggle quota.

## 7. Data and the F2 fix (Option A)
**Approximate counts** (`tools/count_f2_fresh.py`, `measurements/f2_fresh_counts.json`; a simplified occupancy model, not the builder): F2 with the 10 old pairs has 560 texts; 83 are fresh against old true rules, **5** against all E1b/E1c entry texts of any kind (the E1d rule). Each new pair adds 56 texts. F1: 14,919 of 16,800 fresh.

**Authoritative check: the real builder, 10 throwaway trials** (`tools/builder_trials.py`, `measurements/builder_trials.json`; CPU only, no model; books discarded). Each trial runs the real E1b/E1c builder with the exact dev-new allocation (first 4 distinct cores per new pair) and the TEST allocation (80 per family, first 80 distinct of 2n = 160 draws), the strict exclusion list, the builder's neighbour rules (load-bearing gold change, distinct labels, forbidden texts), then `verify`, branch balance, distinct core, strict freshness, verifier expected-spec parse for every shown entry, and the role-word leak check.
- **Result: 10 of 10 seeds (99000–99900) build** (rule: ≥ 8 of 10). Every check passes in every trial.
- **What the trials changed.** The first trial found that the 5 remaining old-pair F2 texts cannot get fresh load-bearing neighbours under the strict rule. So **F2 TEST role pairs are the three new pairs only**; the old pairs are exhausted. E1c T1 F2 is the old-pair reference. (A trial-tool bug, letting new entries take canary IDs or case texts, was also found and fixed before the recorded run.)
- **Pool use per trial:** the new-pair space is 168 texts; dev-new shows 29–34 of them (cores + neighbours), TEST cores use 80, leaving 54–59 unused as cores; counting TEST neighbours too, 11–19 are left. A later round will need further new pairs (56 texts each).
- TEST F2 per pair across trials: 21–33 cores each (e.g. seed 99000: baker/porter 24, potter/bearer 23, tanner/loader 33).

**Generation method (frozen):**
- F2 role pairs: dev-new and TEST use **("baker", "porter"), ("potter", "bearer"), ("tanner", "loader")** only. Same template (`render_def`, `render_message`, labels, cases, neighbours), credits 2–9, uniform choice over pairs then rates (`cases.py:44`). F1 is unchanged.
- Role words: single lowercase ASCII words (verifier grammar `[A-Za-z]+`), consonant-initial (templates say "a {x}"), common trade nouns of similar length. CPU check: none appears in any E1b/E1c entry or case text, and none collides with old roles, scheme nouns or units.
- E1d passes the role list through its own builder code (the trial tool rebinds `e1b.cases.ROLES` in-process); `v6/e1b/e1b/cases.py` is not edited, so E1b and E1c hashes stay valid.
- **Step-up list (frozen order):** ("farmer", "packer"), ("cooper", "driver"), ("grocer", "runner"); at most six new pairs are ever used. A builder failure (D6) **adds** the next pair (k grows by one) and the trials rerun; a dev failure (D7/D8) **replaces** a failed pair by the next one (k unchanged), by the deterministic rule in §8. Let k = the number of adopted pairs (now 3); dev-new size is always 4k.

**Exclusion list (frozen):** a dev-new or TEST entry (core or neighbour) may not use any entry text of **any kind**, and no case text or entry ID may be reused, from the E1b frozen book, the E1b A9 book, the E1c dev book and the E1c TEST book. **TEST also excludes everything shown to a model in any earlier dev stage:** E1c D1 and D2 (the E1c dev book, already excluded whole), and every E1d dev stage, including the first dev-new book and any replacement dev-new book (their cores, neighbours, cases and IDs). A role pair replaced after a dev failure is never used in TEST. Throwaway builder-trial books are never shown to a model and are not excluded (their seeds are disjoint). The canary pool is spliced in as in E1c. `book.py:47` lists only the first three books and must be replaced.

**Order of steps before freeze:**
1. Throwaway builder trials (done: 10/10; rerun if pairs change).
2. E1d dev-new book (seed 94062): 4k = 12 F2 cores, 4 per new pair, 4 cases each. The E1c dev book is reused for everything else (no fresh texts). Reusing E1c dev alone cannot qualify the new roles (GPT).
3. The E1d dev stage (§8), after Stefan's go.
4. Freeze, then build the E1d TEST book (seeds 95061–95066, generator 95062, +100 seed rule).

## 8. Dev stage and eligibility for freeze
One dev stage, **D1-E1d**, after Stefan's explicit go, with the planned cap of 1.0 GPU-h (§6). Arm A0 only. Data:
- **E1c dev book** (reused; old pairs; 80 per family): senders + verifier on all 160 entries per sender; receivers on the E1c 10-entry subset (5 per family), 40 messages × 2 arms per direction.
- **E1d dev-new** (4k = 12 F2 entries on the new pairs, 4 per pair): senders + verifier and receivers, both directions, all 16k = 48 messages × 2 arms per direction.

**The dev-new entries are a vocabulary smoke test only.** They can catch gross breakage of the new role words; they do not establish new-pair reliability. TEST measures that, reported per pair (§10).

Freeze is allowed only if every row holds (checked in code, like E1c `t1_eligibility`):

| Check | Measures | Pass | From E1c? | On failure |
|---|---|---|---|---|
| D1 completion | `.done` + recorded `done`, no terminal marker | yes | carried (`stages.py:98`) | E1c retry rules; no freeze |
| D2 structure | both directions, both senders; 160 selection rows per sender (E1c dev), 4k per sender (dev-new); receiver rows exactly as assigned | exact | carried, extended | INCOMPLETE; no freeze |
| D3 verifier batch conformance | batch 8 vs batch 1 on 16 E1c-dev entries per model | all identical | carried | not eligible; amendment with a batch-1 dev stage |
| D4 protocol hash | dev hash = TEST config hash (also covers the role list) | equal | carried, extended | new dev stage |
| D5 projection | dev per-row timings scaled to 160 entries × 2 directions, + 25% | ≤ TEST cap (4.0 h) | carried | no TEST until amendment |
| D6 builder feasibility | real-builder throwaway trials (§7) | ≥ 8 of 10 | new | add the next step-up pair, rerun (§7) |
| D7 vocabulary smoke test | per pair, see below | all six sub-checks | new | deterministic rule below |
| D8 dev-new accuracy | per pair and pooled, see below | all | new | deterministic rule below |
| Wrong-pick screen | E1c's observed ≤ 2% screen (`stages.py:109`) | reported only | **not carried as blocking** (consistent with Stefan's decision to drop the wrong-ID gate; TEST G1 captures its effect on accuracy) | n/a |

**D7 (per adopted pair p; three screens, each checked separately, for each sender; a pair passes D7 only if all six pass).** Each sender has 4 entries of pair p.
- D7a verifier format: `verifier_parse == "ok"` on **≥ 3 of 4** entries.
- D7b sender pick valid: `pick` not null (a letter parsed) on **≥ 3 of 4** entries.
- D7c receiver parse, prose arm, in that sender's direction: **16 case-level observations** (4 entries × 4 cases); pass if the frozen E1b receiver parser returns an answer (`pred` not null) on **≥ 14 of 16**.

**D8 (accuracy; counts are case-level messages).**
- Per pair p and direction (16 messages per arm): D8a prose correct **≥ 12 of 16**; D8b hybrid correct − prose correct **≥ −2**. A pair passes D8 only if D8a and D8b hold in both directions.
- Pooled over all k adopted pairs, per direction (16k messages per arm; 48 at k = 3): D8c prose correct **≥ 12k** (36 at k = 3); D8d hybrid correct − prose correct **≥ −floor(1.6k)** (−4 at k = 3). Pooled D8 passes only if D8c and D8d hold in both directions.

**Deterministic outcome rule** (f = number of adopted pairs failing D7 or D8; u = unused step-up pairs left):
1. f = 0 and pooled D8 passes: dev-new is qualified.
2. f = 0 and pooled D8 fails: **stop**. Option A is not qualified; back to Stefan (no automatic remedy).
3. 1 ≤ f < k and f ≤ u: each failed pair is replaced by the next unused step-up pair, in frozen order, failed pairs taken in adopted-list order. Then: builder trials rerun with the new set (D6); a replacement dev-new stage (own cap, Stefan's go) runs only the 4f new entries; passing pairs keep their results; D7/D8 are re-evaluated on the final set (pooled D8 from each pair's latest results), and this rule applies again.
4. f = k (every pair fails), or f > u: **stop**, as in 2.

The step-up list holds three pairs, so at most three replacements happen across all dev stages.

## 9. Gates and verdict
Per direction; SUCCESS only if all pass in **both** directions, after completeness:

| Gate | Measure | Data | Pass |
|---|---|---|---|
| C | completeness (rows = assignment, as `analysis.py:14`) | all | else INCOMPLETE |
| G1 | accuracy hybrid − prose, E1c bootstrap, lower bound s[50] of 2,000 | 160 entries, 640 messages | > −0.05 |
| G2 | ID coverage, accepted / assigned | 160 entries | ≥ 85% |
| G3 | S_d(W_base) one-sided 95% lower bound (§3.1) | 160 entries + F_d | > 20% |

Reported, not gated: wrong IDs (§6), sensitivities (§5.3), compressed baselines (§11), speed (§12), per-pair results (§10), E1c's 30% payload and break-even.

**Code to adapt:** E1c's `direction_result` and `verdict` enforce the old criteria (`analysis.py:113`, `stages.py:281`); `check_freeze.py` hardcodes `v6/e1c` paths; the code hash omits `tools/`. E1d needs its own gate code, the §8 eligibility check, freeze paths, and a hash covering `tools/` (all four scripts), the W file, the builder and the analysis. Tests: F_d in every replicate, the §5.2 event counts, versions and order, the artifact round trip, both-direction enforcement, and the D7/D8 outcome rule on synthetic rows.

## 10. Per-pair reporting
For **each adopted new role pair** separately (baker/porter, potter/bearer, tanner/loader, and any step-up pair), per direction: entries, picks and messages (denominators shown); coverage; hybrid and prose accuracy; wrong accepts with CP95 upper bound; hybrid and prose bytes per message. Also the pooled F2 new-pair group, F1, and E1c T1 F2 as the old-pair reference. Groups with no entries are marked "n/a". These are reported findings, not gates. With 21–33 entries per pair (§7) the per-pair numbers are imprecise and say so.

## 11. Compressed prose (claim scope)
The primary claim is **limited to plain, uncompressed prose**, a choice of claim scope. Reported secondary: both arms with per-message gzip-9 (mtime 0), and gzip-9 artifacts and syncs.

## 12. Speed (secondary, reported; no new compute)
From fields the runs already log (`exchange_*.jsonl`, `select_*.jsonl`), per direction and arm:
- wire bytes per message (surface 3) as the transmission-time proxy;
- receiver `prompt_tokens`, `gen_tokens` and `latency_s` per exchange. In the ID arm the receiver's delegate expands the ID to the full text, so receiver tokens and latency should be close to prose; the saving is in transmission, not receiver compute;
- ID-arm sender-side overhead: `sender_latency_s`, `sender_gen_tokens`, `verifier_latency_s` per entry.
Latencies are batch-level measurements on a shared T4 and are descriptive only.

## 13. Open questions and closed decisions
**For Stefan:**
1. The freeze decision itself, with the planned compute: dev stage D1-E1d cap 1.0 GPU-h (estimate ≈ 0.7 h); TEST cap 4.0 GPU-h (estimate ≈ 2.0–2.5 h, confirmed by D5 at freeze).
2. D7/D8 thresholds (§8): accept as written, or change before freeze?

**Closed:**
- W_base values: accepted by Grok (`reviews/grok_E1d_draft_v4.md`) as a proof-of-concept shared-repository scenario; unchanged.
- Arm A1 "no neighbours": dropped; A0 is the only arm (Grok, GPT r5).
- Dev wrong-pick screen: reported only, consistent with Stefan's decision to drop the wrong-ID gate.
- Compression: gzip-9 stays the reported compressed baseline. zstd with a trained dictionary (and its distribution cost) is **deferred** as a possible reported extra; not part of E1d's frozen analysis.

## 14. Change log
**v5 (2026-10-19)**

| Point | Fix | Section |
|---|---|---|
| GPT r5 #2 / Grok v4 #1: A1 not fully specified | A1 dropped and deferred; A0 the only arm; every A1 step and dependency removed (dev data, D2 rows, D4 hash, selection data) | §2, §4.2, §8 |
| GPT r5 #1 / Grok v4 #2: D7/D8 not mechanical | D7 three screens checked separately per sender with actual counts (4 entries; 16 case-level receiver parses, ≥ 14); D8 pair-level (16 messages) and pooled (16k) numeric thresholds; deterministic replace/stop rule in terms of k and remaining step-up pairs | §8, §7 |
| GPT r5 #1: TEST exclusions | TEST excludes everything shown in any earlier dev stage, incl. replacement dev-new books; replaced pairs never used | §7 |
| Grok v4: W_base acceptable | recorded as closed | §13 |
| Open questions | closed: W_base, A1, dev wrong-pick screen (reported), zstd (deferred); planned compute added for the freeze decision | §6, §13 |

**v4 (`4ffdc76`, 2026-10-19)**
**v4 (2026-10-19)**

| Point | Fix | Section |
|---|---|---|
| GPT r4 #1 / Grok #1: F2 simulation approximate | simulation labelled approximate; 10 real-builder trials with exact allocation and neighbour rules: 10/10 build; F2 TEST restricted to new pairs (old pairs exhausted); pool use recorded | §7 |
| GPT r4 #2 / Grok #2: dev qualification undefined | dev data and eligibility table D1–D8 with thresholds, carried E1c screens, failure actions incl. step-up; dev-new = smoke test only; A1 selection data stated | §8 |
| GPT r4 #3 / Grok #3: participant/traffic accounting | aggregate traffic held at 180,000 despite joins; delta recipients = participants immediately before; joiners get the current full version and skip that day's delta; W_copy counts the maintainer upload; explicit F formulas for W_base, W_copy, W_churn | §5 |
| GPT r4 #4 / Grok #4a: byte-precision figures | sizing script and output committed; 1.65 / 1.36 points at 80 per family, agreeing with GPT's 1.64 / 1.36 | §6 |
| GPT r4 #5 / Grok #4b: per-pair reporting | each new pair reported separately with denominators | §10 |

**v3 (`da0fe97`, 2026-10-19):** Stefan's decisions: wrong-ID gate dropped (quoted: E1d is "a proof of concept about reducing kilobytes for better transmission, not a foolproof product", and "the 1% gate was an addition in my earlier draft, not something E1c had"); TEST 80 per family from T1 rates; the dictionary as a shared, agent-maintained repository with per-receiver copies as a sensitivity; byte surfaces named; speed reported. F2 Option A (Grok, GPT F2 opinion). GPT r3 medium points: lifecycle costs derived from measured v1 bytes; reproducible churn.

**v2 (`22e4b58`):** answered GPT r2 #1–8 and Grok r1 #1–5: frozen byte boundary and serializer; measured minimal artifact and loader; sender-side checker kept; ratio bootstrap; W as a scenario; E1d gate table; compressed prose as claim scope.

Falcon3-7B-Instruct results will be produced using artificial intelligence technology from the Technology Innovation Institute (TII Falcon License).
