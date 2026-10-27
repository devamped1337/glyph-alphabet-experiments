# Share a few real agent messages with Glyph

This kit helps prepare a contribution to the E1e/E1f byte-savings research. It runs **on your computer**, uses
Python's standard library, and never connects to the internet or submits anything. Python **3.10 or newer** is
required; there is nothing to install with pip. Keep your original exports somewhere private.

The study needs real, permitted **agent-to-agent** traffic: handoffs, tool calls, delegations, status reports and
structured messages. Ordinary human chats, synthetic examples, and material already used for development do not
qualify. A ChatGPT export is a supported file format, not evidence that its contents qualify. Select only relevant
conversations before proceeding. You must have permission to share every selected message, including content
from other people or agents. If unsure, do not contribute it.

## One command

Download this repository's contribution-kit folder, then open a terminal in `v6/e1e/contrib`.

Windows:

```console
py -3 contribute.py
```

Mac or Linux:

```console
python3 contribute.py
```

Choose `text`, `chatgpt`, or `jsonl`. With no file argument, paste the selected content and finish with a separate
line containing `GLYPH-END`. Pasting uses your terminal's line endings; use a file to preserve existing CRLF bytes.
The transcript headers below make message boundaries unambiguous.

To use a file instead, drag its path into your terminal after the command, or type it in quotes:

```console
py -3 contribute.py "C:\Users\You\Downloads\conversations.json" --format chatgpt
```

The kit:

1. Reads only the file or pasted content you supply.
2. Scrubs likely emails, phone numbers, handles and secrets, and **all URLs** (including signed links and token paths).
3. Shows a local before/after diff and the complete scrubbed bodies. The diff contains original private text: do not
   record, redirect, screenshot or post your terminal output. Control/bidi characters are escaped for terminal safety.
4. Asks whether you have permission, whether the material is real agent traffic, your publication choice, and credit.
5. Writes one new `.jsonl` file **only after your final yes**. Existing files are never overwritten.

Without `--output`, the new file goes in your home folder, outside this repository. Nothing is automatically attached,
posted, committed or sent. Do not put submissions or source exports into the repository.

## Publication and credit

Choose separately for **each contribution**:

| Choice | Permission you give | How to deliver the file |
| --- | --- | --- |
| `private` | Use the scrubbed messages for byte-savings research; publish aggregates only | Arrange a private channel with the collector first. **Do not attach it to a public forum, gist, issue or PR.** |
| `raw` | Publish the **scrubbed message bodies**, as well as aggregates | Attach or post the file where the collector requested contributions |

“Raw” never means the unscrubbed export. Either choice includes the message bodies in the submission file so the
research can be done. `private` is a consent instruction, **not encryption**; anyone receiving the file can read it.
Credit can be `anonymous`, a public `name`, or a public `handle`. Named/handle credit is explicitly included in the
file and may be used publicly, including for private contributions. Other handles in the messages stay scrubbed
unless you explicitly allowlist them. Credit does not automatically allowlist message text.

The collector must retain these consent fields, keep private bodies outside git, and publish only permitted
material. The kit cannot enforce what another person does after you send a file.

## Preview without writing anything

```console
py -3 contribute.py "messages.jsonl" --format jsonl --dry-run
```

Dry run shows local changes and counts, asks no consent questions, and creates no files. It does not imply consent.
Cancel any prompt or answer `no` to stop without writing a submission.

## Optional controls

```console
py -3 contribute.py "messages.jsonl" --format jsonl --redact "Alice Example" --redact "12 Example Street" --allow-handle "@public_agent" --output "C:\Users\You\submission.jsonl"
```

- `--redact` removes that literal term, case-insensitively; repeat for names, addresses, projects, account numbers, etc.
  Remember that command arguments can appear in your local shell history. For sensitive terms, edit a **private copy**
  of the source first instead.
- `--allow-handle` keeps only that exact handle, case-insensitively. It is not a wildcard or a secrets-scan bypass.
- `--conversations 1,3` selects conversations by their first-appearance order in the input. Their original IDs/titles
  are not copied into the submission. Use the same complete export when selecting related portions; do not split a
  single workflow into invented “conversations” to inflate counts.
- `--contributor-id c-<32 hex digits>` reuses the ID printed in your previous file, so the collector counts you once
  across submissions. If omitted, a new random ID is made. Tell the collector if you previously contributed under
  another ID. IDs are pseudonyms, not identity verification.

## File formats

**Simple JSONL (best for exact bytes):** one JSON object per line, with these existing E1e message fields:

```json
{"conv_id":"workflow-1","seq":1,"sender_role":"planner","receiver_role":"worker","kind":"handoff","text":"Inspect the patch.\r\nReport findings.","synthetic":false}
{"conv_id":"workflow-1","seq":2,"sender_role":"worker","receiver_role":"planner","kind":"result","text":"No issues found.","synthetic":false}
```

These are **synthetic documentation examples**, not contributions. `seq` is a positive integer unique within a
conversation. Interleaved rows are grouped by conversation and ordered by sequence. Use generic roles/types, not
personal names. Missing required fields, duplicate JSON keys, duplicate sequence numbers, non-UTF-8 input, lone
surrogates, synthetic/dev-only flags, and messages above E1e's existing **65,536 UTF-8-byte** boundary are refused.
Unrecognized input metadata is discarded rather than copied, including original IDs, timestamps, titles and paths.
Missing `synthetic`/`dev_only` fields do not establish provenance; your explicit attestations are still required.

**ChatGPT JSON:** supply the locally extracted `conversations.json`, or a single conversation object containing
`mapping` and `current_node`. Only the parent chain ending at `current_node` is used; abandoned alternatives are
excluded. Text parts are joined without added separators, and role labels are retained. Platform system messages
are excluded. Non-text/image/attachment content and broken/cyclic branches are refused rather than silently
flattened. The kit does not download or unzip an account export, infer tool-call structure, or reinterpret human
messages as agent traffic. For unsupported content, prepare a curated JSONL file with the real message boundaries.

**Pasted text or UTF-8 `.txt`:** use these exact delimiter lines:

```text
--- planner -> worker | handoff ---
Inspect the patch.
--- worker -> planner | result ---
No issues found.
--- conversation ---
--- planner -> worker | task ---
A separate real workflow begins here.
```

The message body includes every byte after its header's line ending up to the next delimiter, including the final
line ending. A delimiter appearing inside a body is ambiguous: use JSONL for that content. No whitespace trimming,
Unicode normalization or CRLF-to-LF conversion is performed on file message bodies. A file-level UTF-8 BOM is
accepted; a BOM inside a message remains content. Redaction deliberately changes bytes and compressibility.

## Submission format and review

The output is ordinary JSONL with the existing core fields `conv_id`, `seq`, `sender_role`, `receiver_role`, `kind`,
`text`, `synthetic=false`. Intake metadata is attached to **each row**, so privacy instructions cannot be separated
from messages simply by splitting the file:

- `sanitised=true`, `scrubber_version`, `source_type`, and an intake-only `provenance` description;
- random `contribution_id` and `contributor_id`; conversations remapped under the contribution ID, sequences start at 1;
- `consent`: publication (`raw`/`private`), use (`byte-savings-research`), credit (`type`, `value`), date, and explicit
  `permission_attested`/`agent_traffic_attested` flags.

JSON uses ASCII escapes; parsing it restores retained UTF-8 message bytes, including CRLF, NFD/NFC, emoji and BOMs.
The collector's existing readers can consume the core fields. The additional consent fields are intake metadata,
not an amendment to E1E-MSG/1's transport envelopes. No timestamp (`ts`) is output: original timestamps can identify
people, so the existing frozen no-timestamp ordering/split rule applies at collection time. Do not mix partial
timestamp policies without the study maintainers' review.

The summary counts this file's messages, conversations, bytes and **one self-attested contributor**. It does not
deduplicate people or repeated exports across files, verify identities, or claim that the research gate is met.
The existing gate remains at least **50 messages, 20 conversations, 3 contributors** (subject to the study's own
recorded exception process). The collector checks outside provenance, permissions, repeats and conversation
grouping. The kit does not assign dev/held-out splits, read held-out data, mine entries or run the held-out pass.

## Limits of scrubbing

Patterns are defence in depth. Names, addresses, prose secrets, encoded attachments and indirect identification may
escape automated detection. You must inspect the full preview. Remove more from a private source copy and rerun if
needed. The independent final scan refuses detected leftovers, including several percent/Unicode-escaped forms;
it is **not a guarantee that every possible secret has been found**. Conservative rules can also remove harmless
hashes, IDs, numbers or code; this changes compressibility. Do not undo a redaction just to improve study results.
No third-party API, model, tokenizer or network service is used.

## Tests (for Glyph or other reviewers)

From the repository root:

```console
python3 -m unittest discover -s v6/e1e/contrib/tests -v
```

Fixtures under `tests/fixtures/` are small, explicitly synthetic byte fixtures. They test CRLF, Unicode, BOMs,
branches, secrets, consent cancellation, dry runs and refusal/overwrite boundaries. No real corpus or frozen
E1e/E1f module, threshold, measurement or held-out file is modified by this kit.
