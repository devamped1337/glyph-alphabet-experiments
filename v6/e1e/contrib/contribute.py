#!/usr/bin/env python3
"""Offline E1e contribution wizard. Python 3.10+, standard library only."""
import argparse
import collections
import datetime
import difflib
import json
import os
import re
from pathlib import Path
import sys
import uuid

from errors import KitError
from formats import MAX_INPUT, check_text, parse, LABEL
from scrub import scrub, scan, safe_display

VERSION = "3"
GENERIC_ROLES = frozenset("planner worker reviewer orchestrator coordinator assistant user tool agent sender receiver system developer client server manager executor researcher supervisor controller contributor collector unknown".split())
GENERIC_KINDS = frozenset("handoff result task status chat tool_result tool_call delegation request response message report update error".split())


def generic_label(value, field):
    choices = GENERIC_KINDS if field == "kind" else GENERIC_ROLES
    prefix = "type" if field == "kind" else "agent"
    return isinstance(value, str) and (value in choices or bool(re.fullmatch(prefix + r"-[1-9][0-9]*", value)))

CORE = {"conv_id", "seq", "sender_role", "receiver_role", "kind", "text", "synthetic"}
EXTRA = {"sanitised", "source_type", "provenance", "contribution_id", "contributor_id", "consent", "scrubber_version"}


def choose(prompt, allowed):
    while True:
        value = input(prompt).strip().lower()
        if value in allowed:
            return value
        print("Choose " + ", ".join(allowed) + ".")


def validate(rows, allow_handles=()):
    if not rows:
        raise KitError("submission-schema", "No messages selected.")
    seen, last, metadata = set(), {}, None
    for message_number, row in enumerate(rows, 1):
        if set(row) != CORE | EXTRA:
            raise KitError("submission-schema", "Unexpected submission fields.", message_number)
        if row["synthetic"] is not False or row["sanitised"] is not True:
            raise KitError("submission-schema", "Contribution must be real and scrubbed.", message_number)
        if row["source_type"] not in ("jsonl", "chatgpt", "text") or row["scrubber_version"] != VERSION:
            raise KitError("submission-schema", "Invalid provenance.", message_number)
        for key, prefix in (("contribution_id", "s-"), ("contributor_id", "c-")):
            value = row[key]
            if not isinstance(value, str) or len(value) != 34 or not value.startswith(prefix):
                raise KitError("submission-schema", "Invalid opaque contribution/contributor identifier.", message_number)
            try:
                int(value[2:], 16)
            except ValueError as exc:
                raise KitError("submission-schema", "Invalid identifier.", message_number) from exc
        if not isinstance(row["conv_id"], str) or row["conv_id"][:35] != row["contribution_id"] + "-" or not row["conv_id"][35:].isdigit():
            raise KitError("submission-schema", "Invalid conversation identifier.", message_number)
        pair = (row["conv_id"], row["seq"])
        if type(row["seq"]) is not int or row["seq"] < 1 or pair in seen or row["seq"] != last.get(row["conv_id"], 0) + 1:
            raise KitError("submission-schema", "Invalid or duplicate sequence.", message_number)
        seen.add(pair)
        last[row["conv_id"]] = row["seq"]
        try:
            check_text(row["text"])
        except ValueError as exc:
            raise KitError("message-text", str(exc), message_number) from None
        for key in ("sender_role", "receiver_role", "kind"):
            if not isinstance(row[key], str) or not LABEL.fullmatch(row[key]) or not generic_label(row[key], key):
                raise KitError("generic-label", "Use generic role/type labels.", message_number)
        for key in ("text", "sender_role", "receiver_role", "kind"):
            try:
                scan(row[key], allow_handles)
            except KitError as exc:
                raise KitError(exc.rule, "Sensitive content remains in " + key + "; edit a private copy and rerun.", message_number) from None
        consent = row["consent"]
        if not isinstance(consent, dict) or set(consent) != {"publication", "use", "credit", "date", "permission_attested", "agent_traffic_attested"}:
            raise KitError("submission-schema", "Missing consent.", message_number)
        if consent["publication"] not in ("raw", "private") or consent["use"] != "byte-savings-research":
            raise KitError("submission-schema", "Invalid consent scope.", message_number)
        if consent["permission_attested"] is not True or consent["agent_traffic_attested"] is not True:
            raise KitError("submission-schema", "Permission and real agent traffic attestations required.", message_number)
        try:
            datetime.date.fromisoformat(consent["date"])
        except (TypeError, ValueError):
            raise KitError("consent-date", "Invalid consent date.", message_number) from None
        credit = consent["credit"]
        if not isinstance(credit, dict) or set(credit) != {"type", "value"} or credit["type"] not in ("name", "handle", "anonymous"):
            raise KitError("submission-schema", "Invalid credit.", message_number)
        if not isinstance(credit["value"], str) or len(credit["value"]) > 100 or any(ord(c) < 32 for c in credit["value"]):
            raise KitError("submission-schema", "Invalid credit value.", message_number)
        if credit["type"] == "anonymous" and credit["value"] != "":
            raise KitError("submission-schema", "Anonymous credit must be empty.", message_number)
        if credit["type"] != "anonymous" and not credit["value"].strip():
            raise KitError("submission-schema", "Credit value required.", message_number)
        try:
            scan(credit["value"], (credit["value"],) if credit["type"] == "handle" else ())
        except KitError as exc:
            raise KitError(exc.rule, "Sensitive content in public credit; choose anonymous credit or a safe public value.", message_number) from None
        shared = {k: row[k] for k in EXTRA if k != "sanitised"}
        if metadata is None:
            metadata = shared
        elif metadata != shared:
            raise KitError("submission-schema", "A file must contain one contribution with consistent consent.", message_number)
    return {"messages": len(rows), "conversations": len(last), "contributors": 1,
            "text_bytes": sum(len(r["text"].encode("utf-8")) for r in rows)}


def build(rows, source, consent, contributor_id, contribution_id, allow_handles=(), extra_terms=()):
    convs, counts, output, roles, kinds = {}, collections.Counter(), [], {}, {}
    for row in rows:
        cid = convs.setdefault(row["conv_id"], len(convs) + 1)
        counts[cid] += 1
        value = {}
        for key in ("sender_role", "receiver_role", "kind"):
            label = row[key]
            hidden = any(term and re.search(re.escape(term), label, re.I) for term in extra_terms)
            if generic_label(label, key) and not hidden:
                value[key] = label
            else:
                labels, prefix = (kinds, "type") if key == "kind" else (roles, "agent")
                # Reserve generic numbered labels already present in this contribution.
                if label not in labels:
                    used = {r[k] for r in rows for k in (("kind",) if key == "kind" else ("sender_role", "receiver_role"))} | set(labels.values())
                    number = 1
                    while prefix + "-" + str(number) in used:
                        number += 1
                    labels[label] = prefix + "-" + str(number)
                value[key] = labels[label]
        value.update(conv_id=contribution_id + "-" + str(cid), seq=counts[cid],
                     text=scrub(row["text"], allow_handles, extra_terms), synthetic=False, sanitised=True,
                     source_type=source, provenance="Contributor-attested real agent traffic; sanitised; intake only, not assigned to a split",
                     contribution_id=contribution_id, contributor_id=contributor_id,
                     consent=consent, scrubber_version=VERSION)
        output.append(value)
    validate(output, allow_handles)
    return output


def safe_destination(path):
    """Reject git checkouts/worktrees, bare repos and symlink paths into them."""
    path = Path(path).expanduser().absolute()
    try:
        resolved = path.resolve()
    except (OSError, RuntimeError):
        raise KitError("destination-resolution", "Cannot resolve destination; choose an existing accessible folder.") from None
    for parent in resolved.parents:
        marker = parent / ".git"
        bare = (parent / "HEAD").is_file() and (parent / "objects").is_dir() and (parent / "refs").is_dir()
        if marker.exists() or marker.is_symlink() or bare:
            raise KitError("output-in-git", "Choose a destination outside every git repository (for example, your home folder).")
    return path


def write_new(path, content):
    """Exclusive create: never replace an existing submission, source file or symlink."""
    path = safe_destination(path)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input", nargs="?", type=Path, help="Local UTF-8 transcript, conversations.json, or JSONL; omit to paste")
    p.add_argument("--format", choices=("text", "chatgpt", "jsonl"), help="Input format; prompted when omitted")
    p.add_argument("--output", type=Path, help="New JSONL file (default: your home folder, outside the repository)")
    p.add_argument("--dry-run", action="store_true", help="Show local diff/preview and counts; write nothing")
    p.add_argument("--allow-handle", action="append", default=[], help="Exact handle to keep, repeatable (no wildcard)")
    p.add_argument("--redact", action="append", default=[], help="Additional literal name/address/project to remove, repeatable")
    p.add_argument("--conversations", help="Comma-separated conversation numbers in input order, e.g. 1,3; default all")
    p.add_argument("--contributor-id", help="Reuse c-<32 hex> from your previous submission to avoid counting you twice")
    a = p.parse_args(argv)
    if a.output:
        safe_destination(a.output)
    print("Glyph contribution kit — offline. Nothing is sent. Local preview includes your original text.")
    kind = a.format or choose("Format [text/chatgpt/jsonl]: ", ("text", "chatgpt", "jsonl"))
    if a.input:
        with a.input.open("rb") as stream:
            raw = stream.read(MAX_INPUT + 1)
    else:
        print("Paste the transcript. Finish with a line containing only GLYPH-END (no transcript file is saved).")
        parts, total = [], 0
        while True:
            line = input()
            if line == "GLYPH-END":
                break
            total += len(line.encode("utf-8")) + 1
            if total > MAX_INPUT:
                raise KitError("input-size", "Pasted input exceeds 32 MiB.")
            parts.append(line + "\n")
        raw = "".join(parts).encode("utf-8")
    selection = None
    if a.conversations:
        try:
            selection = {int(s) for s in a.conversations.split(",")}
        except ValueError:
            raise KitError("conversation-selection", "Conversation selection must contain numbers.") from None
        if not selection or any(n < 1 for n in selection):
            raise KitError("conversation-selection", "Conversation numbers must be positive.")
    rows = parse(raw, kind, selection)
    cid = a.contributor_id or "c-" + uuid.uuid4().hex
    sid = "s-" + uuid.uuid4().hex
    # Dry run uses clearly non-binding placeholders; no consent is inferred or persisted.
    consent = {"publication": "private", "use": "byte-savings-research", "credit": {"type": "anonymous", "value": ""},
               "date": datetime.date.today().isoformat(), "permission_attested": True, "agent_traffic_attested": True}
    clean = build(rows, kind, consent, cid, sid, a.allow_handle, a.redact)
    for i, (before, after) in enumerate(zip(rows, clean), 1):
        print("\nMessage %d (%d UTF-8 bytes after scrubbing):" % (i, len(after["text"].encode("utf-8"))))
        if before["text"] != after["text"]:
            diff = difflib.unified_diff(before["text"].splitlines(keepends=True), after["text"].splitlines(keepends=True),
                                        fromfile="original (local only)", tofile="scrubbed")
            print(safe_display("".join(diff)))
        print("SCRUBBED BODY:\n" + safe_display(after["text"]))
    stats = validate(clean, a.allow_handle)
    print("\n%d messages; %d conversations; 1 contributor; %d body bytes." % (stats["messages"], stats["conversations"], stats["text_bytes"]))
    print("Review names, locations and context too: regexes cannot guarantee anonymity or detect every secret.")
    print("SCRUBBED role/type labels: " + ", ".join(sorted({r[k] for r in clean for k in ("sender_role", "receiver_role", "kind")})))
    if a.dry_run:
        print("DRY RUN: no file written; no consent recorded.")
        return 0
    print("Only real agent-to-agent traffic belongs here. Human chats, generated examples and development data are excluded.")
    if choose("Do you have permission to share every selected message for byte-savings research? [yes/no]: ", ("yes", "no")) != "yes":
        print("Cancelled. No file written.")
        return 1
    if choose("Are these real agent-to-agent messages, with no synthetic or development-only material? [yes/no]: ", ("yes", "no")) != "yes":
        print("Cancelled. No file written.")
        return 1
    consent["publication"] = choose("Publication [private/raw]: private = aggregates only; raw = publish SCRUBBED message bodies: ", ("private", "raw"))
    credit_type = choose("Credit [anonymous/name/handle]: ", ("anonymous", "name", "handle"))
    credit_value = "" if credit_type == "anonymous" else input("Public credit value (this will be included): ").strip()
    consent["credit"] = {"type": credit_type, "value": credit_value}
    clean = build(rows, kind, consent, cid, sid, a.allow_handle, a.redact)
    validate(clean, a.allow_handle)
    path = safe_destination(a.output or (Path.home() / ("glyph-contribution-" + sid[2:] + ".jsonl")))
    if consent["publication"] == "private":
        print("PRIVATE: this file contains scrubbed messages. Send it only through a private channel agreed with the collector. Never post it publicly or commit it.")
    else:
        print("RAW PUBLICATION PERMITTED: scrubbed message bodies and chosen credit may be published.")
    print("Credit: " + safe_display(credit_type + (": " + credit_value if credit_value else "")))
    print("Destination: " + safe_display(str(path)))
    if choose("Have you reviewed the diff, full scrubbed bodies, role labels and consent, and approve writing this file? [yes/no]: ", ("yes", "no")) != "yes":
        print("Cancelled. No file written.")
        return 1
    payload = b"".join((json.dumps(r, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii") for r in clean)
    # Parse/validate the actual serialized rows immediately before exclusive write.
    validate([json.loads(line) for line in payload.splitlines()], a.allow_handle)
    write_new(path, payload)
    print("Saved " + safe_display(str(path)))
    print("Your contributor ID (reuse for future submissions): " + cid)
    print("Nothing submitted. Intake review decides eligibility; this kit does not run or assign the held-out split.")
    return 0


def run(argv=None):
    try:
        return main(argv)
    except KitError as exc:
        print("Stopped: " + str(exc) + " No submission sent.", file=sys.stderr)
    except OSError as exc:
        rule = "destination-exists" if isinstance(exc, FileExistsError) else "file-access"
        print("Stopped: rule " + rule + ": Cannot read input or exclusively create output; check the location and permissions. No submission sent.", file=sys.stderr)
    except (EOFError, KeyboardInterrupt):
        print("Stopped: rule cancelled-input: Input ended or was cancelled. No submission sent.", file=sys.stderr)
    except ValueError:
        # Unexpected library exceptions may contain source text, dates or private paths.
        print("Stopped: rule input-validation: Invalid input or metadata; see CONTRIBUTING.md. No submission sent.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(run())
