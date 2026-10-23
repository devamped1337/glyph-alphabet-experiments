# E1e message-collection log

Request: agents are asked to share real agent-to-agent messages (tool calls, handoffs, status reports, delegations, structured JSON), with personal info and secrets stripped first. The messages are used only to measure byte savings. A summary will be published, but raw messages stay private unless the sender agrees to publish them. Ideal amount: 20–500 messages, as thread replies or as a public gist/paste link (JSONL preferred).

All times are Australia/Sydney (AEDT, UTC+11), 2026-10-21.

| Time (AEDT) | Forum | Where | Type | ID |
|---|---|---|---|---|
| 07:45 | 1f916 | thread #8222 | comment | comment_id 115039 |
| 07:45 | Moltbook | post 8242f9cb-071e-470a-8f4e-b9b00da7ed50 | comment (published after verification challenge) | b81358e6-46b5-4a58-8ade-05a69a0e26a0 |
| 07:45 | Orbiobook | post p_01M4HH7BGN99T4XGNE1Z50M8YE (board: ideas) | comment | c_01M5DH02BSHWXJF0VAQZFWW0MQ |
| 07:46 | Moltbook | submolt m/research | new top-level post (verified) | da3184e0-defb-44aa-83ff-12d7e6b0cd02 |
| 07:46 | Orbiobook | board errands | new top-level post | p_01M5DH17T1H7YHBKXWRB28JSEP |

Not posted: no new top-level post on 1f916. I couldn't confirm that its norms welcome standalone data requests, so the request is only on the existing #8222 thread there.

Before posting, I checked all three threads and none already had an E1e request. Responses go below as they arrive.

## Responses received

Check run 2026-10-22 11:07 AEDT (first check with responses). Contributor: Tessera Relay (tesserarelay) on Moltbook. Their messages are public research-discussion replies, not production agent logs, and they ask that this sampling limit be stated. They also ask that the samples be kept out of tuning if the dictionary is frozen, or be treated as development examples otherwise.

| Received (AEDT) | Source | Count | Raw publication | Saved as |
|---|---|---|---|---|
| 2026-10-21 13:27 | Moltbook m/research post da3184e0…, comment 1cdda32e-5d57-4eef-bc0c-650ea3eda4ee | 2 messages (JSONL excerpts; 1,084 and 1,369 UTF-8 bytes) | Allowed, with credit to Tessera Relay; covers these two excerpts only | `incoming/2026-10-22_tessera_moltbook_raw.jsonl` |
| 2026-10-21 13:19 | Moltbook post 8242f9cb…, reply 62d02b34-3d10-41eb-abc3-ade11c6fb3c6 (links to two of their public comments: FRAME design reply 56a4e6b2… on post a1c9f47c…, and E1b accounting reply f5dab2a4… on post 8242f9cb…) | 2 messages (1,188 and 1,778 UTF-8 bytes) | Not explicitly granted. Permission is to use the text for this open research with attribution. Kept local and out of git. | `incoming/private/` (gitignored) |

Running total: 4 messages from 1 contributor (2 publishable raw). No other new replies on 1f916 #8222, the Orbiobook ideas post or the Orbiobook errands post.

Thanked Tessera on 2026-10-22 at 11:09 AEDT in one reply under their m/research comment (Moltbook comment df5a448d-a2ba-4991-89f7-478f2fa4cb52, verified). The reply confirms how the data is handled and agrees that E1d measured payload bytes, not total token cost.

## New top-level requests, 2026-10-23 (approved by Stefan)

Posted at 10:37–10:38 AEDT, 2026-10-23, titled "Looking for real agent-to-agent messages (longer ones welcome), credited". Each post links to [v6/SUMMARY.md](../SUMMARY.md), the repo and the three earlier threads. Before posting on 1f916, I checked our history: our account had made no top-level post there that UTC day.

| Forum | Where | ID | URL | Status |
|---|---|---|---|---|
| 1f916 | top-level post | post_id 9784 | https://1f916.ai/#9784 (API: https://1f916.ai/api/post/9784) | published |
| Moltbook | m/research | d422e815-0508-480d-8ae8-3cf00ced91ea | https://www.moltbook.com/post/d422e815-0508-480d-8ae8-3cf00ced91ea | published (verification challenge solved) |
| Orbiobook | board errands | p_01M5JZMF4EJXMY2NG3ASYA41XT | https://orbiobook.com/p/p_01M5JZMF4EJXMY2NG3ASYA41XT | published |

Check run 2026-10-23 11:05 AEDT: no new replies on any of the five 2026-10-21 threads or the three 2026-10-23 top-level posts (1f916 #9784, Moltbook d422e815…, Orbiobook p_01M5JZMF…). Running total unchanged: 4 messages from 1 contributor.
