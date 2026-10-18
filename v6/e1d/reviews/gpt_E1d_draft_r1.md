# GPT thoughts on E1d DRAFT_PLAN (1509f3f), 2026-10-19 (informal, not a formal review round)
GPT could not fetch GitHub from its sandbox; feedback is based on the summary sent.

**Overall: sound direction, but needs work before freezing.** A lifetime/workload criterion better matches deployment value than a universal 1,000-message break-even target. It supports a narrower claim: savings for a specified workload and distribution setup.

1. Justify the workload independently of the savings result: dated usage logs, an existing retention policy, or a documented deployment forecast; horizon, active recipients, messages per recipient, dictionary reuse; chosen before inspecting E1d savings. Otherwise call it a scenario experiment, not a deployment forecast.
2. Make dictionary distribution match the claimed deployment: initial copies, cache misses, new recipients, version changes, update payloads, verification traffic, fallback including failed ID attempts. Keep disk vs transmitted separate; pick one primary byte surface; name when every growing denominator is read.
3. Define what the confidence bound covers: paired total costs on the same workload; resample conversations/users, not correlated messages; keep fixed dictionary costs in every estimate. Sampling CI doesn't validate the forecast: test lower usage, more churn, more updates as sensitivity.
4. Keep development selection separate from confirmation; freeze choices after dev; say whether both directions must pass; keep accuracy, coverage, wrong-ID gates.
5. Include a credible compression baseline: prose compressed under the same transport conditions, including reusable compression state and its distribution cost.

Smaller dictionary: yes, test one dev-selected smaller dictionary alongside the current one, judged on lifetime bytes and all gates; pick primary before confirmation or pre-declare both.
Break-even and lifetime curve: keep secondary, with sensitivity to usage and redistribution assumptions.
