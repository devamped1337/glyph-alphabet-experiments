"""Read supported local exports; never silently flatten conversation branches or normalize text."""
import json
import re

MAX_INPUT = 32 * 1024 * 1024
MAX_MESSAGE = 65536  # Existing E1e message boundary, not a new eligibility threshold.
LABEL = re.compile(r"[A-Za-z][A-Za-z0-9_.-]{0,63}\Z")


def strict_json(text):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError("Duplicate JSON key; fix the export.")
            out[key] = value
        return out
    def bad_constant(_):
        raise ValueError("Non-finite JSON number.")
    try:
        return json.loads(text, object_pairs_hook=pairs, parse_constant=bad_constant)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("Invalid JSON export (contents omitted).") from exc


def check_text(text):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Each message needs nonempty text.")
    try:
        size = len(text.encode("utf-8", errors="strict"))
    except UnicodeError as exc:
        raise ValueError("Invalid Unicode in a message.") from exc
    if size > MAX_MESSAGE:
        raise ValueError("Message exceeds E1e's 65,536-byte limit; select a smaller conversation.")


def jsonl(text):
    rows, seen = [], set()
    for line in text.split("\n"):
        if not line.strip():
            continue
        row = strict_json(line)
        if not isinstance(row, dict):
            raise ValueError("Each JSONL line must be a message object.")
        required = {"conv_id", "seq", "sender_role", "receiver_role", "kind", "text"}
        if not required <= row.keys():
            raise ValueError("JSONL requires conv_id, seq, sender_role, receiver_role, kind, text.")
        if row.get("synthetic", False) is not False or row.get("dev_only", False) is not False:
            raise ValueError("Synthetic or development-only data cannot be submitted through this intake kit.")
        if not isinstance(row["conv_id"], str) or not row["conv_id"]:
            raise ValueError("conv_id must be a nonempty string.")
        if type(row["seq"]) is not int or row["seq"] < 1:
            raise ValueError("seq must be a positive integer.")
        for field in ("sender_role", "receiver_role", "kind"):
            if not isinstance(row[field], str) or not LABEL.fullmatch(row[field]):
                raise ValueError(field + " must be a generic role/type label, not a personal name or free text.")
        check_text(row["text"])
        pair = (row["conv_id"], row["seq"])
        if pair in seen:
            raise ValueError("Duplicate conversation/sequence pair.")
        seen.add(pair)
        rows.append({k: row[k] for k in required})
    # Sequence is authoritative even if rows in the export are interleaved.
    order = {c: i for i, c in enumerate(dict.fromkeys(r["conv_id"] for r in rows))}
    return sorted(rows, key=lambda r: (order[r["conv_id"]], r["seq"]))


def chatgpt(text):
    root = strict_json(text)
    conversations = root if isinstance(root, list) else [root]
    rows = []
    for ci, conv in enumerate(conversations, 1):
        if not isinstance(conv, dict) or not isinstance(conv.get("mapping"), dict):
            raise ValueError("Expected ChatGPT conversations.json with mapping and current_node.")
        mapping, cursor, visited, chain = conv["mapping"], conv.get("current_node"), set(), []
        if not isinstance(cursor, str) or cursor not in mapping:
            raise ValueError("ChatGPT conversation lacks a valid current_node; cannot choose a branch safely.")
        while cursor is not None:
            if cursor in visited or cursor not in mapping:
                raise ValueError("Cyclic or broken ChatGPT conversation branch.")
            visited.add(cursor)
            node = mapping[cursor]
            if not isinstance(node, dict):
                raise ValueError("Invalid ChatGPT node.")
            chain.append(node.get("message"))
            cursor = node.get("parent")
        seq = 0
        for message in reversed(chain):
            if message is None:
                continue
            if not isinstance(message, dict):
                raise ValueError("Invalid ChatGPT message.")
            role = message.get("author", {}).get("role")
            if role == "system":
                continue  # platform instructions, not contributor traffic
            if role not in ("user", "assistant", "tool"):
                raise ValueError("Unsupported ChatGPT role; use a curated JSONL export.")
            content = message.get("content", {})
            parts = content.get("parts")
            if content.get("content_type") != "text" or not isinstance(parts, list) or not all(isinstance(p, str) for p in parts):
                raise ValueError("Non-text ChatGPT content cannot be exported losslessly; curate JSONL instead.")
            body = "".join(parts)
            if not body.strip():
                continue
            check_text(body)
            seq += 1
            rows.append({"conv_id": str(ci), "seq": seq, "sender_role": role,
                         "receiver_role": "assistant" if role in ("user", "tool") else "user",
                         "kind": "tool_result" if role == "tool" else "chat", "text": body})
    return rows


def transcript(text):
    """Explicit delimiters only. Body starts immediately after the header's line ending."""
    rows, conv, seq, header, body = [], 1, 0, None, []
    marker = re.compile(r"--- ([A-Za-z][A-Za-z0-9_.-]*) -> ([A-Za-z][A-Za-z0-9_.-]*) \| ([A-Za-z][A-Za-z0-9_.-]*) ---\Z")
    def finish():
        nonlocal seq, body
        if header is not None:
            value = "".join(body)
            check_text(value)
            seq += 1
            rows.append(dict(zip(("sender_role", "receiver_role", "kind"), header),
                             conv_id=str(conv), seq=seq, text=value))
        body = []
    for line in text.splitlines(keepends=True):
        label = line.rstrip("\r\n")
        match = marker.fullmatch(label)
        if label == "--- conversation ---":
            finish()
            if rows:
                conv += 1
            seq, header = 0, None
        elif match:
            finish()
            header = match.groups()
        elif header is not None:
            body.append(line)
        elif line.strip():
            raise ValueError("Transcript needs explicit message headers; see CONTRIBUTING.md.")
    finish()
    return rows


def parse(raw, kind):
    if len(raw) > MAX_INPUT:
        raise ValueError("Input exceeds 32 MiB; export a selected subset.")
    try:
        text = raw.decode("utf-8-sig")  # optional file BOM; message BOMs remain untouched
    except UnicodeError as exc:
        raise ValueError("Input must be UTF-8; no replacement decoding is performed.") from exc
    rows = {"jsonl": jsonl, "chatgpt": chatgpt, "text": transcript}[kind](text)
    if not rows:
        raise ValueError("No messages found.")
    return rows
