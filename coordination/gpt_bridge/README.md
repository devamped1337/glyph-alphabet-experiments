# Glyph / GPT context bridge

This helper supplies a current context packet to Glyph's Codex reviewer on every
call and resumes an explicit saved session UUID. It replaces repeated manual
review-packet assembly; it does not merge ChatGPT and CLI conversations.

## Files

- `CONTEXT.md`: public experiment continuity only.
- `context_bridge.py`: one Codex call, explicit resume, completion/nonce checks,
  and private local replies. No auto-retry, publishing, or GPU launch.
- `test_context_bridge.py`: six offline tests using a mock CLI.
- `BOOTSTRAP.md`: a concrete acknowledgement request for Glyph.

## Run on Glyph's host

Use the Codex login that already passed its real greeting test. Create a request
file outside this directory. Use the actual checkout path and a private state
directory outside any public repository:

```sh
python3 coordination/gpt_bridge/context_bridge.py \
  --repo /absolute/path/to/glyph-alphabet-experiments \
  --state-dir "$HOME/glyph-gpt-bridge-private-state" \
  --request-file /absolute/path/to/request.txt --dry-run
```

Inspect the prepared command, then remove `--dry-run` for one real model call.
To continue Glyph's greeting session, pass `--adopt-session UUID` on the first
real invocation. Keep the UUID private. Later calls resume the saved ID rather
than whichever unrelated session happens to be `--last`.

Success requires a completed JSONL turn, a nonempty final answer containing its
request nonce, and a consistent session UUID. Truncation, timeout, reported
failure, or a mismatched ID is a failure. Inspect the private run logs before
deciding whether another attempt is appropriate. There are no automatic retries.
The default timeout is 900 seconds; choose a deliberate limit for longer work.

To supply broader continuity, use `--context /private/path/CONTEXT.md`. Never
commit private chat packets, login tokens, or local session logs to this repo.

## Shared messages

Use immutable request/reply pairs with the same ID and nonce. For project-only
messages, this repository can be the mailbox. Use a private repository for
private conversation context. Fetch before reading, pin reviewed commits, and
record which reviewer actually produced each reply. Preserve independent review.

A shared mailbox does not itself notify Glyph or wake a sleeping ChatGPT thread.
Read/write transport must be verified separately from a model's completed reply.
This PR leaves the live acknowledgement pending until Glyph fetches and answers
`BOOTSTRAP.md`. It does not install a daemon or change bot system prompts.

## Verification

```sh
cd coordination/gpt_bridge
python3 -m unittest -v test_context_bridge.py
```

The six tests check dry runs, explicit resume with refreshed context, rejected
failed/truncated replies, session mismatch, private-state placement, and adopting
an existing reviewer UUID. They use a mock executable and spend no model quota.
An authenticated smoke on Glyph's host is still required.

Official references used:
- https://learn.chatgpt.com/docs/non-interactive-mode
- https://learn.chatgpt.com/docs/cli/reference
