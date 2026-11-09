# Disclosure — internal 75 (2026-11-10, Australia/Sydney)

Owner approval to run the experiment, after packaging and disclosure, already exists (t1394u, ~09:35 AEDT). This document is that disclosure. The CPU measurement has not been run. GPT and Grok have not yet reviewed this code and plan. Their review is the remaining technical precondition, not a new request to the owner.

The 75 messages are synthetic lines written for this feasibility check by four authoring labels: GPT 25, Grok 25, Claude 15, Glyph 10. They are one operator-side internal cohort. They are not four outside contributors. They are all dev. None are held out. They do not meet the outside gate of at least 50 messages, 20 conversations, and 3 eligible outside contributors. Logged outside intake remains 9 messages from 2 authors, of which 0 are evaluation-eligible. Tessera's four reserved messages and Tidemark's five constructed examples are not in this set.

Combined bytes are frozen at sha256 `b94115fb424947f0555b2ba6669f8d3ba11b53e664e640d4b9670a6b30535439`. Grok's lines were checked as a UI "Copy response" paste (label Fast), parsed identical to the saved file, 25 of 25, with no reroll. That paste is not a server-raw byte identity. The handoff records the paste as 5287 bytes and the saved `grok_messages.jsonl` as the pinned 5288-byte file. A prompt-editor newline expansion of 18530 versus 18268 bytes is recorded there and was not re-measured in this commit. GPT, Claude, and Glyph model labels are the handoff's self-reported labels and were not independently verified here.

No result is claimed. The earlier dev screens failed their pre-set 20% coverage floor and are unchanged. A later byte count on this cohort, if reviewers authorise the gated command, answers only the exploratory question in `AMENDMENT_INTERNAL75_DRAFT.md`. It is not a public claim about real agent traffic.

Forum posts are not part of this disclosure. Nothing here authorises contacting people or posting this text.
