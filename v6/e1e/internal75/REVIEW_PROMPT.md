# Review prompt — internal-75 prep (code and plan only)

Please review the commit that adds `v6/e1e/internal75/` and `v6/e1e/tools/internal75_run.py` on branch `cursor/e1e-internal-75-prep-87f2`. Do not run `internal75_run.py`. Do not mine entries, train a dictionary, or score the 75. Unit tests under `tests/test_internal75_gate.py` are the only command this prep asks a reviewer to run.

Verdict wanted: APPROVE or CHANGES, against the exact hashes in `v6/e1e/internal75/MANIFEST.json`. This is not an experiment-launch approval unless you explicitly say the gated command may be run after both reviews exist.

## Check

1. Combined file sha256 `b94115fb424947f0555b2ba6669f8d3ba11b53e664e640d4b9670a6b30535439`, 22064 bytes, 75 records, 30 conversations. Author files match the manifest. Bodies are not rewritten.
2. Partition is all dev, held-out 0, seed `e1e-fold-1` unused. Outside gate stays unmet. Tessera and Tidemark are absent.
3. The harness does not call `tune`, `select_baseline4`, `split_real`, or `e1f_dev_screen`. It does not overwrite the old measurement JSON.
4. The fixed point `L=32,k=2,C=50` is transferred from the old public-synthetic screen, not fit on these 75. Arm 4 is omitted for that reason. Floor 0.20 and the retirement rule are unchanged. A descriptive coverage number cannot clear the old failures.
5. The decision question is only whether arm 7's primary total is strictly smaller than both 4b-delta and arm 6 on this synthetic cohort after sync bytes. A yes would not generalise to outside traffic.
6. Owner run approval already exists for after packaging and disclosure. Code review is still open. Say if the ack gate is too weak or too strong.
7. Canonical zip sha256 is `990b3ef816dedfe140ecd0a8d27675bd27b5c575f1ac825fab32c438d2e58cbc` (74912 bytes). The embedded handoff hash `818a0e67d34eca9119190ef21fa6ac8003cb9b1b92da8e9194e7ff934553ce0e` is the previous package pass, not a new corpus. Combined sha256 stays `b94115fb424947f0555b2ba6669f8d3ba11b53e664e640d4b9670a6b30535439`.
8. Planned execution if both reviews later allow it: one process, `audit_strict=True`, no tune, no baseline-4 training, no Kaggle/GPU/model/paid API. A decode or verification failure aborts before fallback. The 60-second timer is armed before the `e1e` import and is disarmed before a report is published; a late alarm cannot leave that report in place. Output is a new file inside `measurements/internal75-audit/` only. Gzip-9 is not an arm total. No speedup claim. Approvals of `6019ee8`, `c84b581`, or `ebbb94c` do not approve this commit. A review that is not `VERDICT: APPROVE` with `SOURCE_COVERAGE: full`, and bound to this commit and harness, does not open the gate.

## Command

From `v6/e1e`:

```
python3 -m unittest tests.test_internal75_gate -v
```

Needs no zstd and does not measure. The measurement command, which this review must not execute, is:

```
python3 tools/internal75_run.py --ack /path/outside/REVIEW_ACK.json --out measurements/internal75_exploratory_aggregates.json
```

`REVIEW_ACK.json` is not in the tree. It would need `authorize_run: true`, the combined sha256, this harness sha256, and 64-hex sha256 strings of the GPT and Grok code reviews.

## Do not

Do not merge, do not move tag `e1f-freeze`, do not retune, do not post to a forum, and do not treat the four author labels as outside contributors.
