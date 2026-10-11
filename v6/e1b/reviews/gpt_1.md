# Review gpt_1: E1b PREREG DRAFT rev 1 (`ce7cd5d`) (summary relayed by the user)

Relayed 2026-10-12 (AEDT). This is a summary of GPT's points as relayed by the user, not a verbatim transcript. GPT reviewed rev 1, not rev 2.

- **Proof-of-concept focus:** sender selection plus the full exchange.
- **Small models:** keep Qwen-3B + Smol only, with no third small model. *(Conflicts with Claude r1: add Llama-3.2-3B.)*
- **The Stage A cap is 2 h.** *(Conflicts with rev 2's 5–6 h.)*
- **7B pair:** Qwen2.5-7B + Llama-3.1-8B, loaded one after the other. Substitutes: OLMo, then Mistral only.
- **Families:** the core families are negation (F1) and roles (F2). Long definitions become a small exploratory arm.
- **Size:** 60 honest entries (30 per core family) × 10 TEST cases. Check the runtime on non-TEST cases first. *(Conflicts with Claude's ≥100 entries.)*
- **Qualification:** ≥90% rule comprehension, plus ≥80% arithmetic as a separate qualification. The gate target stays at ≥90% valid acceptance and ≥95% corruption rejection.
- **Shrinking B2:** if id_oracle and matched direct text produce byte-identical prompts, assert the equality in code and run only a small paired check.
- **GPU-hour budget:** pilot + B0 2, B1 3, B2 2, B3 5, reserve 3 (the permitted uses of the reserve are defined in advance).
- **Precision:** a pinned, memory-tested 4-bit (bitsandbytes) config, one model at a time, the same for qualification and TEST. Verify model access first.
- **Cache:** a simple fixed-answer set run cold/cold, warm/warm and cold/warm, plus hard examples, reported as counts with uncertainty. If a discrepancy is unexplained, withhold the cache claim and continue uncached. Say "no discrepancy observed", not a certified rate.
- **B3:**
  - log what information the sender has access to;
  - include candidate preparation in the cost;
  - treat it as 4-way selection, not a repository search;
  - give the direct-text receiver the same original message.
- **Probes and the gate:**
  - keep the probe output format and token budget separate from the arithmetic ones;
  - check planted-entry changes only on questions whose answers change;
  - keep the gate thresholds fixed, and don't let the B1 80/90 rule become the success criterion;
  - call the CI widths planning estimates;
  - freeze the generator code hash and seeds before Stage A.
