# Contribute real agent messages to Glyph

Help test whether shared dictionaries save communication bytes. Use only real, permitted **agent-to-agent**
messages: tool calls, handoffs, delegations and status reports. Human chats, generated examples and development
material do not qualify. A supported export format does not make its contents eligible.

## Open the folder and start

You need Python **3.10+**. No pip packages, account or internet connection are needed.
Download/extract the repository and find `v6/e1e/contrib`.

- **Windows:** open that folder in File Explorer, click the address bar, type `cmd`, and press Enter.
- **Mac:** in Finder, select the `contrib` folder, then use **Services → New Terminal at Folder** (sometimes under
  the right-click menu). Alternatively, open Terminal, type `cd `, drag the folder into the window and press Return.
- **Linux:** open the folder, right-click empty space and choose **Open in Terminal**, or use `cd` in your terminal.

| Task | Windows | Mac / Linux |
| --- | --- | --- |
| Start and paste | `py -3 contribute.py` | `python3 contribute.py` |
| Preview a local JSONL file | `py -3 contribute.py "messages.jsonl" --format jsonl --dry-run` | `python3 contribute.py "messages.jsonl" --format jsonl --dry-run` |

Choose `text`, `chatgpt` or `jsonl`. For plain text, paste actual permitted messages with these headers and finish
with `GLYPH-END` on its own line, then press Enter. This is a **synthetic usage example**, not research data:

```text
--- planner -> worker | handoff ---
Inspect the patch and report findings.
--- worker -> planner | result ---
Review complete.
GLYPH-END
```

To read a local ChatGPT export instead:

```console
py -3 contribute.py "C:\Users\You\Downloads\conversations.json" --format chatgpt --conversations 1
```

Mac/Linux: `python3 contribute.py "$HOME/Downloads/conversations.json" --format chatgpt --conversations 1`.
The ChatGPT importer keeps **only text tool calls and tool results** on the selected current branches. Human
prompts, normal assistant replies, system/custom instructions, reasoning, code/image/attachment content and empty
messages are skipped, with a count. The selected conversations are checked first; unrelated conversations cannot
block the import. A normal human-to-ChatGPT chat is **not eligible** and produces no contribution. For real agent
handoffs or tool traffic not represented by this limited importer, prepare curated JSONL using [FORMATS.md](FORMATS.md).
You must have permission for every retained message, and the collector still checks eligibility.

## Review, choose consent, then save

The kit scrubs likely personal information and secrets, displays a **local diff and the full scrubbed messages**,
and asks for permission, real-agent-traffic confirmation, publication choice and credit. Unrecognized role/type
labels are replaced consistently with `agent-1`, `agent-2`, `type-1`, etc.; generic labels such as `planner` remain.
`--redact` applies to message text and labels. Names, addresses and contextual secrets can escape patterns:
inspect everything and edit a private source copy if necessary. Automated scrubbing cannot guarantee anonymity.

The diff includes original private text. Do not record, redirect or post the terminal output.

| Your choice | What may be published | Where to send the file |
| --- | --- | --- |
| `private` | Aggregates only | A private channel agreed with the collector. **Never a public forum, gist, issue or PR.** |
| `raw` | The **scrubbed** message bodies and aggregates | Attach/post where the collector requested contributions |

Both choices produce a file containing scrubbed message bodies; private means a consent restriction, **not
encryption**. Raw never means your unscrubbed export. Credit can be a public name, a public handle, or anonymous.
Named/handle credit is included in the file even for private contributions. Choose consent separately each time.

After your final yes, one new JSONL file is saved to your home folder (or `--output`). **Destinations inside any git
checkout/worktree, including paths through symlinks, are refused.** Choose a private folder outside repositories.
Existing files are never replaced. **Nothing is sent automatically.** Send the file yourself using the appropriate
channel; keep it and your original export out of git. Say `no` or cancel a prompt to stop without writing.

Dry run writes nothing and records no consent. File input preserves retained message bytes, including CRLF;
pasting uses terminal line endings. Reuse the printed contributor ID with `--contributor-id` next time so you are
counted once. Tell the collector if you already contributed under another ID.

## If something stops

Errors name a rule and, when applicable, a message number without printing that message's contents.

| Error | What to do |
| --- | --- |
| Python command not found | Install Python 3.10+; on Windows try `python` if `py -3` is unavailable. |
| `jsonl-message` / `text-headers` | Check the numbered message and the exact format in [FORMATS.md](FORMATS.md). |
| `chatgpt-author` / `chatgpt-content` | A selected export message has a missing/null object. Use a fresh export or curate real traffic as JSONL. |
| `chatgpt-branch` | The selected conversation has a broken/cyclic branch. Export again or curate JSONL. |
| `eligible-messages` | No supported real tool traffic was retained. Human chats do not qualify. |
| `conversation-selection` | Use positive conversation numbers, such as `--conversations 1,3`. |
| `output-in-git` | Choose `--output` in a private folder outside all repositories. |
| `destination-exists` | Choose a new filename; existing files are protected. |
| `file-access` / `destination-resolution` | Check the input exists, the destination folder exists, and you can read/write there. |
| A sensitive-content rule | Edit a private copy, add a literal `--redact` term, or choose anonymous public credit, then rerun. |

Do not paste private content or terminal diffs into a public bug report. See [FORMATS.md](FORMATS.md) for exact
formats, privacy limits and tests. The kit never assigns splits or runs the held-out pass; existing study rules apply.
