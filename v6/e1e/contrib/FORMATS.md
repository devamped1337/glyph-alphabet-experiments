# Contribution kit: formats and reviewer notes

## Optional controls

```console
py -3 contribute.py "messages.jsonl" --format jsonl --redact "Alice Example" --redact "12 Example Street" --allow-handle "@public_agent" --output "C:\Users\You\submission.jsonl"
```

- `--redact` removes that literal term from message bodies (including supported encoded forms), case-insensitively;
  matching role/type labels are anonymised too. Repeat for names, addresses, projects, account numbers, etc.
  Remember that command arguments can appear in your local shell history. For sensitive terms, edit a **private copy**
  of the source first instead.
- `--allow-handle` keeps only that exact handle, case-insensitively. It is not a wildcard or a secrets-scan bypass.
- `--conversations 1,3` selects conversations by their first-appearance order in the input. Their original IDs/titles
  are not copied into the submission. Use the same complete export when selecting related portions; do not split a
  single workflow into invented “conversations” to inflate counts. ChatGPT selection is applied before branch/message
  validation, using original export positions even when an earlier conversation has no eligible text.
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
personal names. Labels outside the fixed generic vocabulary in `contribute.py` are consistently anonymised as
`agent-N` or `type-N`; generated labels avoid collisions with existing generic numbered labels. Missing required fields, duplicate JSON keys, duplicate sequence numbers, non-UTF-8 input, lone
surrogates, synthetic/dev-only flags, and messages above E1e's existing **65,536 UTF-8-byte** boundary are refused.
Unrecognized input metadata is discarded rather than copied, including original IDs, timestamps, titles and paths.
Missing `synthetic`/`dev_only` fields do not establish provenance; your explicit attestations are still required.

**ChatGPT JSON (limited tool-traffic importer):** supply locally extracted `conversations.json`, or a single
conversation object containing `mapping` and `current_node`. Conversation selection uses original list positions;
unselected branches/messages are not validated. For each selected conversation, only the parent chain ending at
`current_node` is used; abandoned alternatives are excluded. Broken/cyclic branches and malformed/null author or
content objects are refused with content-free errors.

Only text messages whose author role is `tool`, or `assistant` with an explicit tool recipient (not `all`/`user`),
are retained. They become generic `tool_result` / `tool_call` messages; tool names are not copied. Text parts are
joined without added separators. Human prompts, normal final replies, system/developer instructions, reasoning,
code/execution-output content, image/attachment/mixed parts and empty messages are skipped, with a summary count.
Messages with non-text content are not flattened or partly retained. Sequence numbers count only retained messages.

Ordinary human-to-assistant chats are **ineligible**, and human-only exports are refused. An export may qualify
only for real, permitted tool traffic; an explicit recipient is a structural filter, not proof of provenance or
permission. The contributor attests and the collector checks. The kit does not download/unzip exports or infer
missing tool-call structure. Curate unsupported real agent messages as JSONL without changing their boundaries.

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

- `sanitised=true`, `scrubber_version="7"`, `source_type`, and an intake-only `provenance` description;
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
Redactions replace matched source spans, including spans mapped from supported Unicode/percent escapes and
compatibility characters; unrelated Unicode, JSON fields and line endings stay intact. Credential scalars and
explicit YAML block scalars are scrubbed, while empty mapping containers and Python condition headers are kept.
ISO dates, ordinary dotted versions and valid IPv4 addresses are preserved. Ambiguous dotted values are treated
as phones when prefixed by `+` or `0`, when a later multi-digit group starts with zero, or when grouped as 3-3-4
(optionally prefixed by `1.`). Valid IPv4 addresses take precedence over the zero-prefix rule; use `--redact` for
sensitive values in these categories. Known decorators, dotted decorator syntax such as `@pytest.fixture` /
`@app.route(...)` followed by a function/class declaration (with optional decorator chains), and `@here`/`@channel`
are retained. Decorator lines are classified once per scan view rather than repeatedly walking each remaining
chain. Bare built-in type hints and environment-variable lookups are preserved; literal credential comparisons
are scrubbed. Common
scheme-less domains, known key prefixes, credential assignments/flags, UUIDs, obfuscated emails, SSH keys and home
paths are covered, but neither this list nor its regexes is exhaustive. Long plain/snake_case identifiers are not
blanket-redacted solely for length. No third-party API, model, tokenizer or network service is used.

Phone candidates with seven or more digits are redacted even when the pattern joins several adjacent phone
numbers into one long run. The entire candidate is removed; separators inside it may also be removed. This is
conservative and can over-redact long harmless digit runs. Recognized version/date/IPv4 spans are still excluded
before phone matching. Unicode dashes `‐ ‑ ‒ – — −` are folded to `-` for detection, including
supported Unicode/percent escapes; the matched original source span is redacted. Unmatched punctuation is kept.
Searches that require `@`, whitespace or credential separators are skipped when those characters are absent;
this avoids the reported repeated-dot stall without imposing credential/username length caps.

Known numeric ambiguities remain: unprefixed dotted phones such as `61.412.345.678`, `44.7911.123456` and
`555.1234` can be preserved as versions. Inspect for these and use exact `--redact` terms or edit a private source
copy before sharing. Conversely, the dotted date `2024.01.15` is treated as phone-like and redacted; inspect the
local diff for this known false positive. The final scan uses the same numeric classification and cannot resolve
these ambiguities for you. Phones separated by `/`, `_` or `·` are not reliably detected; inspect for these
and use exact `--redact` terms or edit a private source copy. Other adversarial inputs can still be slow; the
separator prechecks are not a general regex runtime bound.

Output is refused inside git checkouts (including `.git` files used by linked worktrees), bare repositories and
symlink paths into them. The exclusive create still protects existing files and symlinks, and destination checks
run again at write time. The local ignore patterns cover both `*.submission.jsonl` and the default
`glyph-contribution-*.jsonl`; they are only a fallback within this folder, not protection for arbitrary copied files.

## Tests (for Glyph or other reviewers)

From the repository root:

```console
python3 -m unittest discover -s v6/e1e/contrib/tests -v
```

Fixtures under `tests/fixtures/` are small, explicitly synthetic byte fixtures. They test CRLF, Unicode, BOMs,
branches, secrets, consent cancellation, dry runs and refusal/overwrite boundaries. No real corpus or frozen
E1e/E1f module, threshold, measurement or held-out file is modified by this kit.
