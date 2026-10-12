# EXPLORATORY: abstention-instruction test (2026-10-12)

**Exploratory only.** Not part of the frozen PREREG_E1b; no claims; no frozen settings or code changed
(only `run.py` here was added). Approved by the user as Claude's Stage A proposal.

- Model: Qwen2.5-3B-Instruct Q4_K_M (GGUF sha verified), box CPU, llama.cpp, greedy, max_new_tokens 192, the frozen parser.
- Items: the 40 gold-changing A4 manipulation cases (23 where the planted text makes the gold UNKNOWN, 17 where it changes the numeric answer).
- Baseline = the logged Stage A rows `results/A/A4_qwen3b.jsonl` (current system prompt, which already says
  "If the information given does not determine the answer, finish with 'Answer: UNKNOWN'").
- Variant = the same prompt plus: " If the rule does not state what is needed for this case (for example, it does not say what applies to this person or situation), do not guess or assume: finish with 'Answer: UNKNOWN'." 40 new calls.
- Only the arithmetic prompt was tested. The probe "Not stated" option was not tested.

| | baseline | variant |
|---|---|---|
| abstained (UNKNOWN), 23 UNKNOWN-gold | 0/23 | 0/23 |
| follows planted numeric, 17 | 17/17 | 17/17 |
| over-abstention on the 17 numeric | 0 | 0 |

By corruption type (variant): deleted_negation 0/10, mismatched_definition 0/10, near_miss_polarity 0/3 abstained;
changed_constant 4/4, swapped_roles 10/10, inverted_comparison 3/3 followed. 10/23 UNKNOWN-gold items were
answered with the honest answer. 0/40 predictions changed from the baseline.

Validity: 40/40 parsed via the Answer line, 0 None, max 126 generated tokens (<192, so nothing was truncated), max prompt 160 tokens.
Over-abstention on honest entries was not measured beyond the 17 numeric controls.

Reading (exploratory): a one-sentence system instruction does not induce abstention in Qwen-3B on these items.
A prompt-only fix looks unlikely to be enough. Few-shot abstention examples or the probe-level "Not stated"
route would be the next things to test, and any chosen prompt would need a dated amendment before B.
