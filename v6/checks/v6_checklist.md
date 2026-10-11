# v6 pre-flight and post-result checklist

Run before claiming any result. Items in bold are the ones that were missed in v5.

## Before any run
- [ ] Layer indices for the contextual channel are frozen in the prereg (not chosen by DEV argmax after seeing data).
- [ ] J-lens feasibility budget (memory + time) is filled in, or the omission is pre-registered.
- [ ] Coverage, selection, and decoding are separate fields in the prediction schema.
- [ ] Unknown-ID condition is implemented as a model call, not a parser short-circuit.
- [ ] Prose baselines are generated without the gold string present.
- [ ] LOO procedure removes the held-out entry from the receiver’s book / prototypes / adapters before the test.
- [ ] Slot-ablated baseline is implemented and will be reported alongside no-message.
- [ ] Behaviour-gate calibration set (≥10 planted bad entries) is ready and the numeric threshold is pre-registered.

## After the run, before writing RESULTS
- [ ] **Run `python validate_v6.py --results-dir <dir>` and require a clean pass.**
- [ ] Rejection / uncovered count is logged per task and matches the book-negotiation log (do not assume coverage=1.0).
- [ ] LOO results are split: answer-held-out vs other-held-out, each compared to the best baseline.
- [ ] Raw residual (unsnapped) is reported as its own condition, separate from snapped lookup.
- [ ] Receiver token / FLOP / latency numbers are measured without the 64-token padding and compared to both uncached and cached KV expansion.
- [ ] Place-task (or any high-rejection task) accuracy is reported as end-to-end and covered-only separately.
- [ ] Depth actually used is stated (embedding vs contextual) in the results header.
- [ ] If any number disagrees with a reviewer’s earlier claim, the disagreement is recomputed from the JSONL and the recomputation is cited.

## Amendments rule
- [ ] Any change after results have been seen is dated in the amendments section and states whether results had already been examined.
