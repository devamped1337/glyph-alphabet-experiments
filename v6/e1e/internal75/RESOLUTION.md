# Resolution of the 6019ee8 reviews

GPT/Codex on `6019ee8c968986ef8889aa242404e385e3fdb565`: CHANGES REQUIRED. Grok on the same commit: APPROVE, and Grok stated that `compact.py` was only partly read. That approval is not treated as full-source approval. Neither review authorises a measurement. This commit changes the harness and the audit path, so both must review it again.

## What was wrong

1. `replay_arms` used `assert` for byte equality. Python `-O` removes asserts. `codec.encode` skipped a reference after a failed verify and could send raw. `CompactLink.deliver` caught a bad decode and retransmitted raw. The harness treated a finished replay as success.
2. The ack accepted any 64-hex strings. It did not read a review, require `VERDICT: APPROVE`, require `SOURCE_COVERAGE: full`, or bind the candidate commit and the support files.
3. The 60-second limit was only a written instruction.
4. The output check blocked a few named files and still allowed an overwrite of the corpus, the manifest, or the harness.
5. The saved report kept arm totals only. Gzip sat beside them in a way that looked like another complete arm. Missing coverage keys would become zero.

## What this commit does

Normal codec calls are unchanged: `audit_strict` defaults to false, and existing tests call that default. The internal-75 replay passes `audit_strict=True`. On a verification or decode failure the codec raises `AuditAbort` before charging a fallback frame. `AuditAbort` is not an `E1EError`, so the fallback handlers do not catch it. Arm 1 calls `decode_message` and compares the bytes with an `if`, not an assert.

The ack must name two review files, those files must hash to the ack, and each file must contain `VERDICT: APPROVE`, `SOURCE_COVERAGE: full`, `CANDIDATE:` equal to `git rev-parse HEAD`, and `HARNESS:` equal to this harness file. Support hashes for canon, schema, repo, codec, compact, curation, and baselines must match the manifest and the files on disk.

`install_watchdog(60)` uses `signal.setitimer` for the whole measurement function, including the zstd import, validation, curation, replay, and output. `AuditDeadline` is a `BaseException`. Timeout deletes a partial output and does not leave a successful report.

The only legal output is a new file directly inside `measurements/internal75-audit/`, created with `O_EXCL`. The report stores each arm's component tally, break-even, and publication/schedule records without entry text or source-conversation ids. Gzip is under `gzip9_message_frames_only` with `comparable_as_arm_total: false`. Coverage is omitted from the arithmetic when the fields are absent; a zero eligible-byte denominator is `coverage: null`, not zero.

The message files are the same bytes. `L=32`, `k=2`, `C=50` is unchanged. There is still no `tune()`, no baseline-4 training, and no measurement in this commit.

## Second GPT review

GPT's full-source review of `c84b5814b64549a56f6537de18415c76d0bddcba` is `VERDICT: CHANGES REQUIRED` with `SOURCE_COVERAGE: full`. Its file sha256 is `0d4e05cc29f93834cc04a69ccb968e5832b797192700f1ebdc35a8d57a7ae40a`. It does not approve a run. A separate Grok review of that same commit cannot approve the commit that contains these further fixes.

The watchdog is now installed before the `e1e` import inside `run_measurement`. Disarming clears the armed flag before the timer is stopped, so a signal delivered while disarming does not raise out of `finally` and skip deletion. The report is published only after that disarm, and only if the deadline flag and the monotonic clock are still inside the limit. A late deadline deletes the partial file and the final file.

The gate tests now drive the whole ack function through an accepting pair of review files, a `CHANGES REQUIRED` verdict, a tampered digest, a missing file, and `SOURCE_COVERAGE: partial`. They refuse an existing output file, check that a fake tally keeps sync and message components with gzip outside the arm totals, abort a tiny `OK` entry when compact verification fails, and abort an arm-1 mismatch under `python -O`. Timeout coverage calls `run_measurement` with a stand-in compute function, not the 75-message replay.

## Third GPT review

GPT's full-source review of `ebbb94c9a8047ea6aa684d8887ae3c0010d14d9b` is `VERDICT: CHANGES REQUIRED`, file sha256 `d03586cf9e1c455c7a586a6780dfa493b9948a4c45900663a61057bdb81d39d7`. It does not approve a run. `PUBLICATION_PREMISE.md` records the shared premise of the earlier deadline and output fixes and the three interleavings that refuted it on that commit.

Publication no longer treats a chosen name as owned. The partial path is added to the owned set only after `O_EXCL` succeeds, so a pre-existing partial is not deleted. The final name is created with `os.link`, which fails if that name already exists, instead of `os.replace`. The owned set is kept until the watchdog is disarmed and the deadline is checked again; a late alarm deletes only owned paths and fails the call.

GPT's full-source review of `cae023b02cd297c9b5867b170b74685ac4865380` is `VERDICT: CHANGES REQUIRED`, file sha256 `e335d14113809bff29f8f574a97461f1c4fa485c682bdf5ca2ceb93db42b6bd5`. The remaining hole was the gap between a successful `open` or `link` and `owned.append`. `SIGALRM` is now blocked for that whole step and delivered only after the new path is registered, so a deadline cannot leave a file this process created while reporting that no report was kept. A file that already existed is still not registered and is not deleted. Tests send `SIGALRM` from inside the creating call, before registration, for both the partial file and the final name.

GPT's full-source review of `45d17b4a2b58ea5e1504a67f212357a15cff9b05` is `VERDICT: CHANGES REQUIRED`, file sha256 `bf59f5eaadf384ddfb9c66dee838822626d7d82b0a423b81be5e99bb6f7e0ee3`. It accepts the signal mask and rejects the single `os.write`. That call can return after one byte. `write_all` continues until the stored size equals the serialized report, and a zero-length or out-of-range return fails before `os.link`. Deadline and write errors still delete only owned paths. The 75-message replay was not run.
