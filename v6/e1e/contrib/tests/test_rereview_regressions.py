"""Synthetic regressions for Glyph's bfa1c17 re-review, including actual saved rows."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import contribute as c
import formats as f
import scrub as s
from errors import KitError


class ReReview(unittest.TestCase):
    def test_sentence_ending_phones_scrubbed_completely_and_raw_scan_refuses(self):
        for phone in ("555-123-4567", "(02) 9876 5432", "+61 412 345 678"):
            for punctuation in (".", ". Next sentence.", ",", ";", ")", "!"):
                with self.subTest(phone=phone, punctuation=punctuation):
                    raw = "Call " + phone + punctuation
                    self.assertEqual(s.scrub(raw), "Call <REDACTED>" + punctuation)
                    with self.assertRaises(KitError): s.scan(raw)
                    s.scan(s.scrub(raw))

    def test_sentence_ending_phones_not_written_to_submission(self):
        for phone in ("555-123-4567", "(02) 9876 5432", "+61 412 345 678"):
            with self.subTest(phone=phone), tempfile.TemporaryDirectory() as folder:
                source = Path(folder) / "input.jsonl"
                source.write_text(json.dumps(dict(conv_id="one", seq=1, sender_role="planner", receiver_role="worker", kind="handoff", text="Call " + phone + ".")))
                target = Path(folder) / "output.jsonl"
                with patch("builtins.input", side_effect=["yes", "yes", "private", "anonymous", "yes"]), contextlib.redirect_stdout(io.StringIO()):
                    code = c.main([str(source), "--format", "jsonl", "--output", str(target)])
                self.assertEqual(code, 0)
                saved = json.loads(target.read_text())
                self.assertEqual(saved["text"], "Call <REDACTED>.")
                self.assertNotIn(phone, target.read_text())
                c.validate([saved])

    def test_dates_versions_and_ips_still_preserved_at_sentence_end(self):
        for value in ("2026-10-28.", "192.168.1.20.", "10.0.0.1.", "1.2.3."):
            self.assertEqual(s.scrub(value), value)
            s.scan(value)

    def test_password_comparison_literal_scrubbed_without_damaging_operator(self):
        for operator in ("==", "!="):
            value = "if password " + operator + " 'hunter2':"
            self.assertEqual(s.scrub(value), "if password " + operator + " '<REDACTED>':")
            with self.assertRaises(KitError): s.scan(value)
            s.scan(s.scrub(value))

    def test_dotted_decorator_context_preserved_but_prose_handles_scrubbed(self):
        for value in ("@pytest.fixture\n", "@pytest.mark.slow\ndef test_example():\n    pass\n", '@app.route("/")\ndef index():\n    pass\n'):
            self.assertEqual(s.scrub(value), value)
            s.scan(value)
        self.assertEqual(s.scrub("Ping @person.other please."), "Ping <REDACTED> please.")

    def test_bare_type_hints_preserved_but_quoted_secret_values_scrubbed(self):
        for value in ("token: str", "pwd: str", "token: Optional[str]", "pwd: str | None"):
            self.assertEqual(s.scrub(value), value)
            s.scan(value)
        self.assertEqual(s.scrub("password: 'str'"), "password: '<REDACTED>'")

    def test_environment_reference_preserved(self):
        for value in ("{'secret': os.environ['S']}", 'password = os.getenv("PASSWORD")'):
            self.assertEqual(s.scrub(value), value)
            s.scan(value)

    def test_user_at_host_scrubbed_and_scan_refuses(self):
        self.assertEqual(s.scrub("ssh user@host now"), "ssh <REDACTED> now")
        with self.assertRaisesRegex(KitError, "user-host"): s.scan("user@host")

    def test_chatgpt_message_number_ignores_null_root_nodes(self):
        conv = dict(current_node="bad", mapping={"root":dict(parent=None, message=None),
                    "empty":dict(parent="root", message=None),
                    "bad":dict(parent="empty", message=dict(author=None, content={}))})
        with self.assertRaises(KitError) as caught: f.chatgpt(json.dumps(conv))
        self.assertEqual(caught.exception.message, 1)


if __name__ == "__main__":
    unittest.main()
