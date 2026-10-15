# E1c freeze notes (2026-10-16): one procedural deviation and two clarifications

These notes accompany the freeze tags `prereg-e1c` (04b7285a6bd3f7c0ae2faff49e8b79e8f457611d) and `e1c-t1-exec` (aabad44a9525e0b72248ed15d06d4458f4a21a23). Neither tag is moved, and the TEST book is not rebuilt. Raised by GPT's freeze review r1 (`reviews/gpt_E1c_T1_r1.md`).

## 1. Deviation: a fake-backend T1 dry run processed the TEST book
PREREG §9 allows only the automated construction, integrity and freshness checks to touch the TEST book before T1. After the execution commit I also ran a **fake-backend T1 dry run**. That went beyond what §9 allows. I should have asked first.

**What consumed the book.** The command was `run_e1c.py --stage T1`, with `E1B_ALLOW_NO_GPU=1`, `E1C_TEST_HOOK=tests/e1c_hook.py` (fake backend), and a scratch results directory `/tmp/t1dry/results` holding a copy of `results/D2`.
- The supervisor and child ran the normal T1 pipeline: selection for both senders, verifier, exchanges and analysis.
- The fake backend replaced every model. Its sender names the true candidate, except for one fixed entry, where it names a neighbour. Its verifier returns the picked entry's spec, off by one for one fixed entry. Its receiver returns E1b's toy fake output.
- It read the book's entries, candidates, messages and cases only to build these fake replies.
- **No language model was loaded or called**, and nothing ran on a GPU.

**What was observed.** Only the last 3 lines of stdout (`T1: done (rc=0)`) and a 3-line printout of `summary.json`:
- verdict `NOT MET`, expected from a toy receiver that does not solve cases;
- both directions `COMPLETE` with 240 entries and 960 messages each;
- both senders 240/240 complete.

No entry text, rule, case, gold, accuracy, coverage or byte figure was printed or read. The scratch directory was deleted straight afterwards and nothing from it was committed.

**What changed because of it.** Nothing: no code, config, cap, book, seed, kernel or launch decision. The aggregates are structural only (sizes and completeness) and say nothing about how the real models will do. The fake outputs carry no information about real outcomes.

**Status.** This is a disclosed procedural deviation. It is not seed selection or outcome-driven tuning. It is submitted for explicit acceptance before the tags are pushed or T1 is proposed.

## 2. Labels inside the frozen files
The PREREG title line and the config `label` still read "DRAFT, not frozen". The binding status is the config `status: "frozen"` and the PREREG status line ("**FROZEN** …"), both in the registration commit. The stale title and label are cosmetic. They are not edited, to avoid moving `prereg-e1c`.

## 3. Launch prerequisites (unchanged procedure)
- Kernel `glyph-kaggle/e1c_T1`: set `E1C_COMMIT` to the full SHA `aabad44a9525e0b72248ed15d06d4458f4a21a23`, check that `git rev-parse e1c-t1-exec` resolves to it, and push only on Stefan's explicit T1 go, within the free quota.
- The T1 report will include the `tools/check_freeze.py prereg-e1c e1c-t1-exec` command and its output (§9).
