**Verdict: required changes before freezing commit `7f19228`.** I reviewed the exact diff and all three requested files in full.

The uncompressed rule is correct: `encode(require_smaller=True)` compares serialized ref bytes against `raw_wire(msg)`, and ties fall back (`>=`, reason `ref_not_smaller`). This caps message bytes against the **raw envelope**, not bare message bytes; envelope overhead remains.

Required plan changes:

1. **Define the refs+zstd comparison precisely** ([§8](/workspace/e1e-gpt/v6/e1e/BYTE_AUDIT_PLAN_DRAFT.md:111)). Specify whether fallback is an uncompressed raw envelope or a zstd-compressed raw envelope. Count all bytes needed to identify and decode the selected form, including any selector/framing. “Raw/plain” currently leaves this measurement choice unresolved.
2. **Remove the obsolete compact-form requirement** from [§10](/workspace/e1e-gpt/v6/e1e/BYTE_AUDIT_PLAN_DRAFT.md:130), and mark §8’s earlier “decision required” paragraph as historical/superseded.

Implementation work **is required before measurement**:

- Thread `require_smaller=True` through the actual replay path. [Link.transmit()](/workspace/e1e-gpt/v6/e1e/e1e/codec.py:155) currently calls `encode()` with its default `False`.
- Implement the declared refs+zstd boundary comparison. An uncompressed size gate alone cannot establish which compressed form is smaller.
- Charge only the selected initial transmission; if it fails, retain its cost and add reject/retransmission bytes. Continue charging declarations, artifacts, and lifecycle traffic separately.
- Verify ties, Unicode/base64 envelope overhead, compressed size-order reversals, and byte-exact reconstruction through the actual replay path.

**Nothing else changed in the protocol:** the commit adds only 15 plan lines. Repository mechanics, E1E-MSG/1 forms, digests, matching, validation, and rejection behavior remain unchanged. The existing uncompressed link accounting correctly counts emitted frames; it does not yet implement the chosen audit policy.

After the two plan clarifications, I would approve the plan freeze, with implementation and validation remaining gates before measurement.
