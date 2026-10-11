# Grok feedback on PREREG_v6_DRAFT, round 3 (relayed by the user; summary, not verbatim)

**Endorses all four [DIFFERS] resolutions:**
1. Both the ~40% (primary) and ~60% layers, plus the emb baseline, with the exact layer indices frozen before TEST.
2. A J-lens feasibility check first. Run sparse NNLS on 7B only if it passes; otherwise record the omission before TEST.
3. Slot-ablated as the primary LOO baseline, with no-message alongside, 3+ candidates, and the transfer rate defined in advance.
4. A numeric gate, an external correctness check, and 10+ planted entries with a false-reject rate. The old 6 are re-run for continuity only.

**Lock these:**
- Raw residual as its own condition.
- Unknown-ID must call the model and log abstention.
- Prose baselines must not contain the gold string.
- Compute measured without padding, against uncached and cached KV expansion.
- The stop rule pre-registered.

**Settled:** the cross-model null result and the negation collision.

Grok says the plan is ready to freeze once these are closed.
