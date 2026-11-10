# Reviewer policy for this CPU audit only

Date: 2026-11-10 11:01 Australia/Sydney.

The owner answered the approval question in this chat, verbatim: "Use GPT’s full-source approval only for this CPU-only audit. Drop the Grok approval requirement and proceed."

That sentence changes the reviewer rule for the internal 75-message CPU audit and for nothing else. It does not change outside qualification, held-out rules, or any later experiment. The earlier instruction to run after reviews still stands. This file does not start the measurement.

## Why Grok is not an authorization input

Grok's full-source coverage of the final candidate was not verified. Reads of earlier commits were partial: files were skipped, `compact.py` was not complete, and line counts for the same `canon.py` did not match. A partial APPROVE is not a full-source approval and is not relabeled here. No Grok review file is created or required by the gate.

## What the gate still requires

One GPT review file whose bytes match the ack digest and whose text contains `VERDICT: APPROVE`, `SOURCE_COVERAGE: full`, and the candidate commit and harness hash of the tree being run. Support hashes, the corpus hash, the watchdog, exclusive publication, the full write, and the strict decode abort stay in force. The ack must also carry `reviewer_policy` equal to `internal75-cpu-gpt-full-source-only-2026-11-10`.

The historical record that GPT and Grok both reviewed earlier drafts remains. This dated amendment does not say Grok approved the final candidate.

GPT's full-source APPROVE of `88059e18ada644e6f2b4b7d307c48ec9ce5b0940` (review sha256 `529e629a190ffada0a7c9b00173d65e7bcce7cb4429d47c97ab625e40a950cdb`) is historical context for that commit. It is not an approval of a later commit.
