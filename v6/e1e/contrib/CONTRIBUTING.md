# Contribute real agent messages to Glyph

Help test whether shared dictionaries save communication bytes. Use only real, permitted **agent-to-agent**
messages: tool calls, handoffs, delegations and status reports. Human chats, generated examples and development
material do not qualify. A supported export format does not make its contents eligible.

## Start with one command

You need Python **3.10+**. No pip packages, account or internet connection are needed.
Download the contribution-kit folder, open a terminal in `v6/e1e/contrib`, and run:

```console
py -3 contribute.py
```

On Mac/Linux, use `python3 contribute.py`. Choose `text`, `chatgpt` or `jsonl`, paste selected content, and finish
with a separate line containing `GLYPH-END`. For plain text, use the message headers shown in [FORMATS.md](FORMATS.md).

To read a local file instead:

```console
py -3 contribute.py "C:\Users\You\Downloads\conversations.json" --format chatgpt
```

Only select relevant conversations. You must have permission for **all** the content you share.

## Review, choose consent, then save

The kit scrubs likely emails, phone numbers, handles, URLs and secrets. It shows a **local diff and the full
scrubbed messages**, then asks for permission, real-agent-traffic confirmation, publication choice and credit.
Names, addresses and contextual secrets can escape patterns: inspect everything. Edit a private copy and rerun if
anything sensitive remains. Automated scrubbing cannot guarantee anonymity or find every secret.

The diff includes original private text. Do not record, redirect or post the terminal output.

| Your choice | What may be published | Where to send the file |
| --- | --- | --- |
| `private` | Aggregates only | A private channel agreed with the collector. **Never a public forum, gist, issue or PR.** |
| `raw` | The **scrubbed** message bodies and aggregates | Attach/post where the collector requested contributions |

Both choices produce a file containing scrubbed message bodies; private means a consent restriction, **not
encryption**. Raw never means your unscrubbed export. Credit can be a public name, a public handle, or anonymous.
Named/handle credit is included in the file even for private contributions. Choose consent separately each time.

After your final yes, one new JSONL file is saved to your home folder (or `--output`). Existing files are never
replaced. **Nothing is sent automatically.** Attach/send that file yourself using the appropriate channel; keep it
and your original export out of git. Say `no` or cancel a prompt to stop without writing.

## Try a preview first

```console
py -3 contribute.py "messages.jsonl" --format jsonl --dry-run
```

Dry run writes nothing and records no consent. File input preserves retained message bytes, including CRLF;
pasting uses terminal line endings. Your output includes a random contributor ID: reuse it with `--contributor-id`
next time so you are counted once. Tell the collector if you already contributed under another ID.

See [FORMATS.md](FORMATS.md) for exact input/output formats, conversation selection, extra redactions, handle
allowlisting, byte limits, privacy limits and tests. The kit reports counts but never assigns splits or runs the
held-out pass; the study's existing eligibility and sample-size rules stay in force.
