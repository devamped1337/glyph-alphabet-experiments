"""Synthetic regressions for Glyph's review of PR #3 at 2c8c922."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT))
import contribute as c
import formats as f
import scrub as s
from errors import KitError


def row(text="Keep this result.", seq=1, **labels):
    return dict(conv_id="private-workflow", seq=seq, sender_role="planner", receiver_role="worker",
                kind="handoff", text=text) | labels


def build(rows, extra_terms=()):
    consent = dict(publication="private", use="byte-savings-research", credit=dict(type="anonymous", value=""),
                   date="2026-10-28", permission_attested=True, agent_traffic_attested=True)
    return c.build(rows, "jsonl", consent, "c-" + "a" * 32, "s-" + "b" * 32, extra_terms=extra_terms)


def conversation(messages):
    mapping = {"root": dict(parent=None, message=None)}
    parent = "root"
    for i, message in enumerate(messages):
        node = "node-%d" % i
        mapping[node] = dict(parent=parent, message=message)
        parent = node
    return dict(mapping=mapping, current_node=parent)


def message(role="assistant", text="Keep this tool call.", recipient="python", **content):
    return dict(author=dict(role=role), recipient=recipient,
                content=dict(content_type="text", parts=[text]) | content)


class SpanRegressions(unittest.TestCase):
    def assert_clean(self, before, after):
        self.assertEqual(s.scrub(before), after)
        s.scan(after)

    def test_review_json_date_and_unicode_unchanged(self):
        value = r'{"msg":"caf\u00e9 ok","date":"2026-10-28"}'
        self.assert_clean(value, value)

    def test_unicode_percent_ellipsis_dash_preserve_surroundings(self):
        for marker in (r"caf\u00e9", "…", "—", "%20"):
            before = '{"msg":"%s ok","mail":"alice@example.org","date":"2026-10-28"}\r\n' % marker
            self.assert_clean(before, before.replace("alice@example.org", s.PLACEHOLDER))

    def test_encoded_match_only_redacts_its_span(self):
        for value in (r"\u0061lice\u0040example.org", "alice%40example.org", "ａｌｉｃｅ＠ｅｘａｍｐｌｅ．ｏｒｇ", "al\u200bice@example.org"):
            self.assert_clean("prefix… " + value + " suffix—\r\n", "prefix… <REDACTED> suffix—\r\n")

    def test_fully_percent_encoded_surroundings_preserved(self):
        # 'hi ' before the address and ' ok' after it must retain their original encoding.
        value = "".join("%%%02X" % b for b in b"hi alice@example.org ok")
        self.assert_clean(value, "%68%69%20<REDACTED>%20%6F%6B")

    def test_dates_versions_and_ips_all_preserved(self):
        for value in ("2026-10-28", "192.168.1.20", "10.0.0.1", "1.2.3", "123.456.789"):
            self.assert_clean(value, value)

    def test_date_next_to_phone_does_not_hide_phone(self):
        self.assert_clean("2026-10-28 +61 412 345 678", "2026-10-28 <REDACTED>")

    def test_decorators_and_broadcast_mentions_preserved(self):
        value = "@property @staticmethod @classmethod @dataclass @abstractmethod @here @channel"
        self.assert_clean(value, value)
        self.assert_clean("@property.other @dataclasses @person", "<REDACTED> <REDACTED> <REDACTED>")

    def test_python_headers_and_indented_code_preserved(self):
        for value in ("if token:\n    run()\nnext()", "if token: run()", "while token:\r\n    run()\r\n"):
            self.assert_clean(value, value)

    def test_yaml_mapping_keeps_siblings_and_redacts_nested_scalar(self):
        self.assert_clean("secret:\n  description: keep\n  token: violet\nnext: ok\n",
                          "secret:\n  description: keep\n  token: <REDACTED>\nnext: ok\n")

    def test_yaml_block_scalars_redacted_without_sibling_loss(self):
        for marker in ("|", ">", "|-", ">+"):
            self.assert_clean("password: %s\r\n  violet horse\r\n  blue\r\nnext: ok\r\n" % marker,
                              "password: %s\r\n  <REDACTED>\r\n  <REDACTED>\r\nnext: ok\r\n" % marker)

    def test_json_quoted_credential_preserves_other_fields(self):
        self.assert_clean('{"token":"violet horse", "msg":"keep"}', '{"token":"<REDACTED>", "msg":"keep"}')
        self.assert_clean(r'\"client_secret\":\"violet\", \"msg\":\"keep\"',
                          r'\"client_secret\":\"<REDACTED>\", \"msg\":\"keep\"')

    def test_credential_assignments_and_flags_preserve_context(self):
        for before, after in (("PGPASSWORD=x psql", "PGPASSWORD=<REDACTED> psql"),
                              ("DB_PASS=x", "DB_PASS=<REDACTED>"),
                              ("secretKey: x", "secretKey: <REDACTED>"),
                              ("session_id=x", "session_id=<REDACTED>"),
                              ("pass: x", "pass: <REDACTED>"),
                              ("--password x --quiet", "--password <REDACTED> --quiet"),
                              ("--password=x --quiet", "--password=<REDACTED> --quiet"),
                              ("curl -u user:pass --silent", "curl -u <REDACTED> --silent")):
            with self.subTest(before=before):
                with self.assertRaises(KitError): s.scan(before)
                self.assert_clean(before, after)

    def test_additional_review_leaks_removed_whole(self):
        for value in ("github.com/user/private-repo", "x.com/handle", "sk_live_abcdefghijk123456",
                      "name at gmail dot com", "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQdemo user@host",
                      "/home/alice/private/file", "/Users/alice/private/file", r"C:\Users\Bob\private.txt",
                      "123e4567-e89b-12d3-a456-426614174000", "(02) 9876 5432"):
            with self.subTest(value=value):
                with self.assertRaises(KitError): s.scan(value)
                self.assert_clean(value, s.PLACEHOLDER)

    def test_long_identifiers_preserved_and_long_message_supported(self):
        for value in ("identifier_" * 8, "a" * 65536):
            self.assert_clean(value, value)

    def test_extra_terms_apply_to_encoded_text(self):
        self.assertEqual(s.scrub("%41lice and Alice", extra_terms=["Alice"]), "<REDACTED> and <REDACTED>")

    def test_scrubbing_is_idempotent(self):
        value = 'password="violet horse"\nsecret:\n  token: violet\nPGPASSWORD=x psql\ncurl -u user:pass'
        clean = s.scrub(value)
        s.scan(clean)
        self.assertEqual(s.scrub(clean), clean)


class ImportRegressions(unittest.TestCase):
    def parse(self, conversations, selection=None):
        with contextlib.redirect_stderr(io.StringIO()) as err:
            rows = f.parse(json.dumps(conversations).encode(), "chatgpt", selection)
        return rows, err.getvalue()

    def test_mixed_real_export_skips_nontext_and_human_traffic(self):
        conv = conversation([message("user", "PRIVATE HUMAN PROMPT"), message("system", "PRIVATE INSTRUCTIONS"),
                             message(content_type="thoughts"), message(content_type="code"),
                             message("tool", content_type="execution_output"),
                             message(parts=[{"asset_pointer": "PRIVATE IMAGE"}]),
                             message("assistant", "PRIVATE FINAL ANSWER", recipient="all"),
                             message(text="Call the tool."), message("tool", "Tool result.")])
        rows, warning = self.parse([conv])
        self.assertEqual([r["text"] for r in rows], ["Call the tool.", "Tool result."])
        self.assertEqual([r["kind"] for r in rows], ["tool_call", "tool_result"])
        self.assertIn("skipped 7", warning)
        self.assertNotIn("PRIVATE", warning + json.dumps(rows))

    def test_selection_precedes_branch_and_message_validation(self):
        good = conversation([message()])
        bad = dict(mapping={}, current_node="broken")
        rows, _ = self.parse([good, bad], {1})
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["conv_id"], "1")
        with self.assertRaises(KitError): self.parse([good, bad])

    def test_selection_keeps_original_number_when_other_conversation_empty(self):
        rows, _ = self.parse([conversation([message("user")]), conversation([message()])], {2})
        self.assertEqual(rows[0]["conv_id"], "2")

    def test_null_and_nonobject_fields_refuse_cleanly(self):
        for field in ("author", "content"):
            for value in (None, "bad", []):
                item = message(); item[field] = value
                with self.assertRaises(KitError) as caught:
                    self.parse([conversation([item])])
                self.assertEqual(caught.exception.rule, "chatgpt-" + field)
                self.assertIsNotNone(caught.exception.message)

    def test_human_only_export_cannot_be_contributed(self):
        with self.assertRaisesRegex(KitError, "No eligible messages"):
            self.parse([conversation([message("user"), message("assistant", recipient="all")])])

    def test_selected_empty_conversation_reports_no_eligible_messages(self):
        with self.assertRaisesRegex(KitError, "No eligible messages"):
            self.parse([conversation([message("user")]), conversation([message()])], {1})

    def test_invalid_parent_type_has_no_raw_python_error(self):
        conv = conversation([message()]); conv["mapping"]["node-0"]["parent"] = []
        with self.assertRaisesRegex(KitError, "chatgpt-branch"):
            self.parse([conv])

    def test_null_fields_cli_no_traceback_or_source_content(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "private-export.json"
            item = message(text="DO-NOT-PRINT-PRIVATE-CONTENT"); item["author"] = None
            path.write_text(json.dumps([conversation([item])]))
            result = subprocess.run([sys.executable, str(KIT / "contribute.py"), str(path), "--format", "chatgpt", "--dry-run"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("rule chatgpt-author", result.stderr)
        self.assertIn("message 2", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertNotIn("DO-NOT-PRINT", result.stdout + result.stderr)


class SubmissionRegressions(unittest.TestCase):
    def test_personal_role_and_kind_labels_anonymised_consistently(self):
        rows = build([row(sender_role="Stefan", receiver_role="Claude", kind="PrivateProject"),
                      row(seq=2, sender_role="Claude", receiver_role="Stefan", kind="PrivateProject")])
        self.assertEqual(rows[0]["sender_role"], rows[1]["receiver_role"])
        self.assertEqual(rows[0]["receiver_role"], rows[1]["sender_role"])
        self.assertNotEqual(rows[0]["sender_role"], rows[0]["receiver_role"])
        self.assertEqual(rows[0]["kind"], "type-1")
        for name in ("Stefan", "Claude", "PrivateProject"):
            self.assertNotIn(name, json.dumps(rows))

    def test_extra_redactions_apply_to_role_and_kind_labels(self):
        rows = build([row()], ["planner", "worker", "handoff"])
        self.assertEqual((rows[0]["sender_role"], rows[0]["receiver_role"], rows[0]["kind"]), ("agent-1", "agent-2", "type-1"))

    def test_generated_labels_do_not_collide_with_existing_generic_labels(self):
        rows = build([row(sender_role="Stefan", receiver_role="agent-1"),
                      row(seq=2, sender_role="Claude", receiver_role="agent-2")])
        self.assertEqual(rows[0]["sender_role"], "agent-3")
        self.assertEqual(rows[1]["sender_role"], "agent-4")

    def test_validation_catches_injected_private_role(self):
        rows = build([row()]); rows[0]["sender_role"] = "Stefan"
        with self.assertRaisesRegex(KitError, "message 1; rule generic-label"):
            c.validate(rows)

    def test_leftover_error_identifies_rule_and_message_without_content(self):
        rows = build([row(), row(seq=2)]); rows[1]["text"] = "PRIVATE alice@example.org"
        with self.assertRaises(KitError) as caught: c.validate(rows)
        self.assertIn("message 2", str(caught.exception))
        self.assertIn("rule email", str(caught.exception))
        self.assertNotIn("PRIVATE", str(caught.exception))
        self.assertNotIn("alice", str(caught.exception))

    def test_bad_jsonl_error_has_message_number_without_contents(self):
        raw = (json.dumps(row()) + '\n{"text":"PRIVATE", "seq":null}').encode()
        with self.assertRaises(KitError) as caught: f.parse(raw, "jsonl")
        self.assertIn("message 2; rule jsonl-message", str(caught.exception))
        self.assertNotIn("PRIVATE", str(caught.exception))

    def test_git_checkout_and_worktree_destinations_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for kind in ("checkout", "worktree"):
                repo = root / kind; repo.mkdir()
                if kind == "checkout": (repo / ".git").mkdir()
                else: (repo / ".git").write_text("gitdir: /not-needed-for-test")
                target = repo / "nested"; target.mkdir()
                path = target / "glyph-contribution-test.jsonl"
                with self.assertRaisesRegex(KitError, "output-in-git"): c.write_new(path, b"PRIVATE")
                self.assertFalse(path.exists())

    def test_bare_repository_destination_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "HEAD").write_text("ref: refs/heads/main")
            (root / "objects").mkdir(); (root / "refs").mkdir()
            with self.assertRaisesRegex(KitError, "output-in-git"):
                c.write_new(root / "output.jsonl", b"PRIVATE")

    def test_symlink_into_checkout_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); repo = root / "repo"; repo.mkdir(); (repo / ".git").mkdir()
            link = root / "link"; link.symlink_to(repo, target_is_directory=True)
            with self.assertRaisesRegex(KitError, "output-in-git"):
                c.write_new(link / "output.jsonl", b"PRIVATE")
            self.assertFalse((repo / "output.jsonl").exists())

    def test_destination_outside_git_allowed(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "output.jsonl"
            c.write_new(path, b"clean")
            self.assertEqual(path.read_bytes(), b"clean")

    def test_ignore_pattern_matches_default_filename(self):
        result = subprocess.run(["git", "check-ignore", "--no-index", "v6/e1e/contrib/glyph-contribution-abc.jsonl"], cwd=KIT.parents[2], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_cli_preview_contains_only_scrubbed_role_labels(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "input.txt"
            path.write_text("--- Stefan -> Claude | PrivateProject ---\nReady.\n")
            with contextlib.redirect_stdout(io.StringIO()) as out:
                code = c.main([str(path), "--format", "text", "--dry-run"])
        self.assertEqual(code, 0)
        for name in ("Stefan", "Claude", "PrivateProject"):
            self.assertNotIn(name, out.getvalue())
        self.assertIn("SCRUBBED role/type labels", out.getvalue())

    def test_cli_selection_skips_unselected_malformed_chat(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "input.json"
            path.write_text(json.dumps([conversation([message()]), {"mapping": {}, "current_node": "missing"}]))
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                code = c.run([str(path), "--format", "chatgpt", "--conversations", "1", "--dry-run"])
        self.assertEqual(code, 0)

    def test_default_home_in_repo_is_also_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); (root / ".git").mkdir()
            source = root / "input.jsonl"; source.write_text(json.dumps(row()))
            with patch.object(Path, "home", return_value=root), patch("builtins.input", side_effect=["yes", "yes", "private", "anonymous"]), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as err:
                code = c.run([str(source), "--format", "jsonl"])
            self.assertEqual(code, 2)
            self.assertIn("output-in-git", err.getvalue())
            self.assertEqual(list(root.glob("glyph-contribution-*.jsonl")), [])


if __name__ == "__main__":
    unittest.main()
