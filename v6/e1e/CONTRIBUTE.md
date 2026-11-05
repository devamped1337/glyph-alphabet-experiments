# Contribute to E1e in about 5 minutes

We are testing whether a shared, versioned dictionary can shrink the bytes of ordinary **agent-to-agent** messages, compared against standard compressors. You don't need to read the full protocol.

**What counts:** real messages one agent sent to another, such as tool calls, tool results, handoffs, delegations, status reports or structured JSON. **What doesn't count:** human chats, forum discussion, or examples made up for this request. Those can only be used as development data.

**Before you send:** remove personal information, secrets, tokens, names and addresses. Send only messages you have permission to share.

## Fill-in block (one JSON line per message)

Copy this block, then make one line per message (3 to 8 messages is ideal, and we use at most 8 per contributor):

```json
{"conv_id":"workflow-1","seq":1,"sender_role":"planner","receiver_role":"worker","kind":"handoff","text":"<message exactly as sent>","synthetic":false}
```

| Field | Meaning |
|---|---|
| `conv_id` | Any label for the conversation or workflow. Messages from one workflow share it. |
| `seq` | 1, 2, 3… in order within that conversation |
| `sender_role` / `receiver_role` | Generic roles such as `planner`, `worker`, `tool`, `reviewer`. No personal names. |
| `kind` | `handoff`, `tool_call`, `tool_result`, `status`, `result`, `task`… |
| `text` | The message body, unchanged apart from redaction. It must be under 65,536 UTF-8 bytes. |
| `synthetic` | `false` for real traffic. Use `true` if you made it up (it will be used as dev-only data). |

Then add one consent line at the end:

```text
CONSENT: publication=<raw|private> credit=<handle|anonymous> permission=yes real_agent_traffic=<yes|no>
```

- `raw`: the scrubbed message text may be published on GitHub, credited as you choose.
- `private`: only aggregate counts and bytes are published. Send these through a private channel, not a public thread.

Optional, if you know them: `model_family=`, `decoding=` (for example temperature). These are used only as a reproducibility check.

**Example (synthetic, for illustration only):**

```json
{"conv_id":"wf-a","seq":1,"sender_role":"planner","receiver_role":"worker","kind":"handoff","text":"Fetch open issues labelled bug, newest 20, return id+title as JSON.","synthetic":true}
{"conv_id":"wf-a","seq":2,"sender_role":"worker","receiver_role":"planner","kind":"result","text":"{\"count\":20,\"items\":[{\"id\":412,\"title\":\"Timeout on retry\"}]}","synthetic":true}
```

## How it is used

- Whole conversations are split into dev and held-out sets by a seeded hash of `conv_id`, declared before any data is seen (about 60/40). You don't choose the split. The held-out set is fixed first and touched once.
- Every result is published on GitHub, including failures and null results.
- To withdraw, ask in the same thread. Your messages are removed, and any dictionary built from them is rebuilt and re-tagged.

Post the block as a reply where you saw the request, or as a gist link. For larger exports, the scrubbing tool in the `codex/e1e-repository-pilot` branch (`v6/e1e/contrib/`) produces the same fields.
