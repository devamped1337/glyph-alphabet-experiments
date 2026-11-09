Required changes:

1. **Reject incomplete zstd frames and trailing bytes** in [baselines.py:58](/workspace/e1e-gpt/v6/e1e/e1e/baselines.py:58). The temporary decompression object is discarded without checking `eof` or `unused_data`. I reproduced `INTEGRITY_FRAME` accepting a frame with all four checksum bytes removed and returning the complete original message. The byte-exact oracle therefore also passes despite the missing checksum. Appended garbage is silently accepted too. Retain the decompression object, require frame completion and no trailing data, and raise `E1EError` otherwise. Add regression tests for these cases, including rejection/fallback billing through `Link`.

Optional suggestion: enforce `max_output` during decompression; the current check runs after the entire output has been allocated.

I read both commits and the current files. Amendment A1, dictionary construction, full-rebuild sync charging, baseline-5 policy, baseline-6 selection/ties, and selected-send billing otherwise match the stated plan. No other required changes found.

Validation: **62 passed**, using `-s -p no:cacheprovider` with bytecode writing disabled for this read-only environment.
