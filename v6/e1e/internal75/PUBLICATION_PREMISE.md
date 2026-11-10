# Publication premise (tested before the fix)

The deadline and output changes in `c84b581` and `ebbb94c` shared one premise:

A path is exclusively owned once this process intends to use it. Putting that path on a cleanup list, replacing a temporary file onto the destination, and checking the deadline immediately before forgetting the path are enough to stop a late alarm from leaving a success file and enough to avoid deleting a file this process did not create.

That premise was tested on `ebbb94c` with three deterministic interleavings and no use of the 75-message corpus.

1. A pre-existing `name.partial` was registered for deletion before `O_EXCL`. Creation raised `FileExistsError`, the cleanup list still contained that path, and the same deletion handler used by `run_measurement` removed the pre-existing bytes.
2. A destination created after the empty-path check was passed to `os.replace`. The pre-existing bytes `KEEP-FINAL` became `NEW-FINAL`.
3. The deadline check was false, the owned-path list was then cleared, and only after that was the expired flag set, which is what a disarmed late signal does. The owned list was already empty, so nothing could remove a published report.

The condition those fixes left in place is that intention, `os.replace`, and a check followed by forgetting the path all count as ownership. This commit removes that condition.

A path is owned only after this process exclusively creates it (`O_EXCL` for the partial file, `os.link` for the final name). `os.link` fails if the final name exists, so a raced destination is left untouched. Deletion applies only to the owned set. The owned set is not cleared when a report is published. After the watchdog is disarmed, one more deadline check runs; if it fails, only owned paths are removed and the call fails. There is no success return that outlives that check.

A later review of that repair showed a remaining false premise: the next Python statement after a successful `open` or `link` is soon enough to register the path. `SIGALRM` can run in that gap, before `owned.append`, and the cleanup then leaves the new file while reporting that no report was kept. Creation and registration are therefore one masked step. `SIGALRM` is blocked before the creating call and released only after the new path is in the owned set. A signal that arrives in the gap is delivered after registration, so the path is deleted with the other owned paths and is not a success artifact. A file that already existed is still not entered into the owned set.

A review of that masked step found a separate false premise about the write itself: a single `os.write` return is the whole buffer. The call may return after fewer bytes, including one byte, and it may return zero. Publishing after that return stores a truncated report and still looks like success. The write now continues until every byte is stored, stops if a call makes no progress or reports a count outside the remaining buffer, and checks the file size before `os.link`. A deadline or an error during the write deletes only owned paths.
