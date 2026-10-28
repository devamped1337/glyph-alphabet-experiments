**Approve freezing the plan text at `fa12dab325733da6b5e520deaf4ed342a270a10f`. No required plan changes.**

I reviewed the commit diff and the full `v6/e1e/BYTE_AUDIT_PLAN_DRAFT.md`. Both r7 requests are satisfied:

- §8 specifies all three refs+zstd candidates, deterministic tie handling, framing, and charging only the selected transmission plus any rejects/retransmissions.
- The earlier compact-form requirement is marked superseded, and §10 reflects its deferral.

This approves the **plan text only**. Implementation and validation remain separate review gates before measurement, including ensuring baseline 6 can consider a ref that loses the uncompressed comparison but wins after compression.
