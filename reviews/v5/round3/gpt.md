# GPT feedback on PREREG_v6_DRAFT, round 3 (relayed by the user; summary, not verbatim)

**Reproduced** the raw-vs-snapped counts: Qwen 1160/1292 agree, 27 vs 3; Smol 1769/2112, 40 vs 16.

The "beats nulls" claim must say **cross-model**.

**Decisions on the four [DIFFERS]:**
1. 40% primary, 60% secondary, plus emb, with frozen block-output hooks. A good 60% result stays labelled secondary.
2. A 7B J-lens feasibility check with a numeric memory/time budget, run as a separate arm against PCA and random. Sparse NNLS alone does not prove J-space.
3. Slot-ablated as primary plus no-message, in identical context, with 3+ balanced candidates. Transfer must beat both baselines.
4. Gate: 100 fresh calibration cases per entry; each model ≥95% correct and ≥95% agreement. Target ≥90% acceptance of valid entries and ≥95% rejection of planted corruptions. These are engineering targets, to be frozen before results.

**Five fixes:**
1. Unknown-ID may stay a deterministic parser test. Add a model abstention test only if a claim about abstention is made.
2. Specify the token position plus a contextual hook. The problem was reading before context, not the choice of token.
3. A cached baseline must use a valid cache: identical prefix only, no concatenating independent KV. Report construction, storage, hit rates, and cold and warm timing.
4. Numeric criteria:
   - Accuracy win: paired 95% CI above zero vs ID-expanded text.
   - Efficiency win: within ±5 points plus ≥20% lower receiver latency.
   - LOO win: beats both baselines in each cross-model direction.
   - Count message groups and semantic items separately, and declare aggregation and sample size in advance.
5. Narrowed stop rule: if this 7B implementation shows neither an accuracy nor an efficiency advantage, stop expanding it and prioritise the text repository. Record inconclusive separately from equivalence.
