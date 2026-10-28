"""Synthetic byte fixtures and security/consent regressions; no real contributor data."""
import contextlib
import io
import json
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
KIT = HERE.parent
sys.path.insert(0, str(KIT))
import contribute as c
import formats as f
import scrub as s


def row(body="Result ready.\r\nCafé; cafe\u0301; \ufeff; 🚀\n", conv="private-original-id", seq=1):
    return dict(conv_id=conv, seq=seq, sender_role="reviewer", receiver_role="orchestrator", kind="handoff", text=body, synthetic=False)


def consent(publication="private"):
    return dict(publication=publication, use="byte-savings-research", credit=dict(type="anonymous", value=""),
                date="2026-10-27", permission_attested=True, agent_traffic_attested=True)


def build(rows=None):
    return c.build(rows or [row()], "jsonl", consent(), "c-" + "a" * 32, "s-" + "b" * 32)


class Formats(unittest.TestCase):
    def test_byte_fixture_preserved(self):
        raw = (HERE / "fixtures" / "unicode-crlf.jsonl").read_bytes()
        parsed = f.parse(raw, "jsonl")
        self.assertEqual(parsed[0]["text"].encode(), b"Result ready.\r\nCaf\xc3\xa9; cafe\xcc\x81; \xef\xbb\xbf; \xf0\x9f\x9a\x80\n")
        after = build(parsed)
        self.assertEqual(after[0]["text"].encode(), parsed[0]["text"].encode())
        self.assertNotIn("private-original-id", json.dumps(after))

    def test_jsonl_rejects_duplicate_keys_pairs_and_bad_seq(self):
        with self.assertRaises(ValueError): f.parse(b'{"text":"a","text":"b"}', "jsonl")
        for rows in ([row(), row()], [dict(row(), seq=True)], [dict(row(), seq=0)], [dict(row(), synthetic=True)], [dict(row(), dev_only=True)]):
            with self.assertRaises(ValueError): f.jsonl("\n".join(json.dumps(r) for r in rows))

    def test_unicode_separators_are_content(self):
        original = row("first\u2028second\u2029third")
        self.assertEqual(f.jsonl(json.dumps(original, ensure_ascii=False))[0]["text"], original["text"])

    def test_invalid_utf8_surrogate_size_empty(self):
        for raw in (b'\xff', b''):
            with self.assertRaises(ValueError): f.parse(raw, "jsonl")
        for text in ("\ud800", "a" * 65537, " "):
            with self.assertRaises(ValueError): f.check_text(text)
        f.check_text("a" * 65536)
        with self.assertRaises(ValueError): f.check_text("é" * 32769)

    def test_jsonl_sequence_sorting_preserves_conversations(self):
        rows = [row("later", "A", 4), row("other", "B", 1), row("first", "A", 2)]
        parsed = f.jsonl("\n".join(map(json.dumps, rows)))
        self.assertEqual([r["text"] for r in parsed], ["first", "later", "other"])
        output = build(parsed)
        self.assertEqual([r["seq"] for r in output], [1, 2, 1])

    def test_transcript_fixture_byte_preservation(self):
        parsed = f.parse((HERE / "fixtures" / "transcript.txt").read_bytes(), "text")
        self.assertEqual(len(parsed), 3)
        self.assertEqual(len({r["conv_id"] for r in parsed}), 2)
        self.assertEqual(parsed[0]["text"], "Ready.\r\n")
        self.assertEqual(parsed[1]["text"], "Café\r\n")

    def test_transcript_requires_explicit_header(self):
        with self.assertRaises(ValueError): f.parse(b"user: ambiguous transcript", "text")

    def chat(self, content=None):
        def message(role, text): return dict(author=dict(role=role), recipient="tool" if role == "assistant" else "assistant", content=dict(content_type="text", parts=[text]))
        return dict(current_node="selected", mapping={
            "root": dict(parent=None, message=None),
            "prompt": dict(parent="root", message=message("assistant", "Task\r\n")),
            "selected": dict(parent="prompt", message=content or message("tool", "Done\u0301")),
            "alternative": dict(parent="prompt", message=message("assistant", "DO NOT INCLUDE THIS BRANCH"))})

    def test_chatgpt_only_current_branch_and_no_ids_titles(self):
        conv = self.chat(); conv["title"] = "Private name"
        parsed = f.chatgpt(json.dumps([conv]))
        self.assertEqual([r["text"] for r in parsed], ["Task\r\n", "Done\u0301"])
        self.assertNotIn("Private name", json.dumps(parsed))

    def test_chatgpt_rejects_broken_cycles_and_skips_nontext(self):
        cycle = self.chat(); cycle["mapping"]["prompt"]["parent"] = "selected"
        broken = self.chat(); broken["current_node"] = "missing"
        image = self.chat(dict(author=dict(role="user"), content=dict(content_type="text", parts=[{}])))
        for conv in (cycle, broken):
            with self.assertRaises(ValueError): f.chatgpt(json.dumps(conv))
        self.assertEqual([r["text"] for r in f.chatgpt(json.dumps(image))], ["Task\r\n"])


class Scrubber(unittest.TestCase):
    def test_secret_byte_fixture(self):
        original = (HERE / "fixtures" / "fake-secrets.txt").read_bytes().decode()
        clean = s.scrub(original)
        s.scan(clean)
        for marker in ("example.org", "abc123", "alice", "violet", "ghp_", "eyJ", "123456789"):
            self.assertNotIn(marker, clean)

    def test_handle_allowlist_exact_not_prefix(self):
        clean = s.scrub("@allowed @allowed.other @other u/other", ["@allowed"])
        self.assertEqual(clean, "@allowed <REDACTED> <REDACTED> <REDACTED>")
        s.scan(clean, ["@allowed"])
        with self.assertRaises(ValueError): s.scan(clean)

    def test_url_credentials_query_path_fragment_all_removed(self):
        for value in ("https://name:pass@host/x", "https://host/?t=abc123", "https://host/abc123#secret", "ssh://name@host/path", "www.host.example/q"):
            self.assertEqual(s.scrub(value), "<REDACTED>")
            with self.assertRaises(ValueError): s.scan(value)

    def test_credential_yaml_and_json_fail_closed(self):
        for value in ('{"password": "violet horse"}', 'password: |\n  violet-horse\nnext: ok', 'Authorization: Digest username="alice", response="violet"', r'\"client_secret\":\"violet\"'):
            clean = s.scrub(value); s.scan(clean)
            self.assertNotIn("violet", clean)
            with self.assertRaises(ValueError): s.scan(value)

    def test_encoded_obfuscated_secrets_cannot_bypass_final_scan(self):
        for value in (r'\u0061lice\u0040example.org', 'alice%40example.org', 'al\u200bice@example.org', 'ａｌｉｃｅ＠ｅｘａｍｐｌｅ．ｏｒｇ', 'password%3Dviolet'):
            with self.assertRaises(ValueError): s.scan(value)
            clean = s.scrub(value)
            # Either scrubbed completely or final validation refuses it.
            try: s.scan(clean)
            except ValueError: pass
            else: self.assertEqual(clean, "password%3D<REDACTED>" if value == "password%3Dviolet" else "<REDACTED>")

    def test_extra_names_and_terminal_escape(self):
        self.assertEqual(s.scrub("Alice met ALICE", extra_terms=["Alice"]), "<REDACTED> met <REDACTED>")
        self.assertNotIn("\x1b", s.safe_display("x\x1b[2Jy\u202ez"))
        self.assertNotIn("\u202e", s.safe_display("x\u202e"))


class Submission(unittest.TestCase):
    def test_counts_schema_and_consent(self):
        rows = build([row(), row("next", seq=2), row("second conversation", conv="B")])
        self.assertEqual(c.validate(rows)["conversations"], 2)
        self.assertEqual(c.validate(rows)["messages"], 3)
        self.assertEqual(rows[0]["consent"]["publication"], "private")
        self.assertNotIn("ts", rows[0])
        self.assertEqual(set(rows[0]), c.CORE | c.EXTRA)

    def test_invalid_schema_secrets_and_mixed_consent_rejected(self):
        for field, value in (("synthetic", True), ("sanitised", False), ("text", "password=leak"), ("seq", True), ("sender_role", "a@b.example")):
            rows = build(); rows[0][field] = value
            with self.assertRaises(ValueError): c.validate(rows)
        rows = build([row(), row("next", seq=2)])
        rows[1]["consent"] = consent("raw")
        with self.assertRaises(ValueError): c.validate(rows)

    def test_credit_explicit_and_scanned(self):
        con = consent(); con["credit"] = dict(type="handle", value="@credit")
        rows = c.build([row()], "jsonl", con, "c-"+"a"*32, "s-"+"b"*32)
        self.assertEqual(rows[0]["consent"]["credit"]["value"], "@credit")
        con["credit"] = dict(type="name", value="alice@example.org")
        with self.assertRaises(ValueError): c.build([row()], "jsonl", con, "c-"+"a"*32, "s-"+"b"*32)

    def run_cli(self, answers, extras=()):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "submission.jsonl"
            with patch("builtins.input", side_effect=answers), contextlib.redirect_stdout(io.StringIO()) as out:
                code = c.main([str(HERE / "fixtures" / "unicode-crlf.jsonl"), "--format", "jsonl", "--output", str(path), *extras])
            return code, path.read_bytes() if path.exists() else None, out.getvalue()

    def test_dry_run_no_prompts_no_writes_no_network(self):
        with patch.object(socket, "socket", side_effect=AssertionError("Network attempted")):
            code, payload, out = self.run_cli([], ["--dry-run"])
        self.assertEqual(code, 0); self.assertIsNone(payload); self.assertIn("DRY RUN", out)

    def test_cancel_at_each_attestation_and_final_confirmation(self):
        for answers in (["no"], ["yes", "no"], ["yes", "yes", "private", "anonymous", "no"]):
            code, payload, _ = self.run_cli(answers)
            self.assertEqual(code, 1); self.assertIsNone(payload)

    def test_private_and_raw_explicit_choices_roundtrip(self):
        for publication in ("private", "raw"):
            code, payload, out = self.run_cli(["yes", "yes", publication, "anonymous", "yes"])
            self.assertEqual(code, 0)
            rows = [json.loads(line) for line in payload.splitlines()]
            c.validate(rows)
            self.assertEqual(rows[0]["consent"]["publication"], publication)
            self.assertEqual(rows[0]["text"].encode(), row()["text"].encode())
            self.assertIn("Nothing submitted", out)

    def test_exclusive_create_no_source_or_symlink_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "output"; path.write_bytes(b"keep")
            with self.assertRaises(FileExistsError): c.write_new(path, b"replacement")
            self.assertEqual(path.read_bytes(), b"keep")
            link = Path(folder) / "link"; link.symlink_to(path)
            with self.assertRaises(FileExistsError): c.write_new(link, b"replacement")

    def test_oversized_input_and_unsupported_labels(self):
        with self.assertRaises(ValueError): f.parse(b"x" * (f.MAX_INPUT + 1), "text")
        with self.assertRaises(ValueError): f.jsonl(json.dumps(dict(row(), sender_role="Alice Smith")))


if __name__ == "__main__":
    unittest.main()
