"""Real saved-file and scan regressions for Glyph's 32f0178 re-review."""
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
import scrub as s
from errors import KitError


class FinalReview(unittest.TestCase):
    def saved_text(self, text):
        with tempfile.TemporaryDirectory() as folder:
            source, target = Path(folder) / "input.jsonl", Path(folder) / "output.jsonl"
            source.write_text(json.dumps(dict(conv_id="one", seq=1, sender_role="planner", receiver_role="worker", kind="handoff", text=text)))
            with patch("builtins.input", side_effect=["yes", "yes", "private", "anonymous", "yes"]), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(c.main([str(source), "--format", "jsonl", "--output", str(target)]), 0)
            row = json.loads(target.read_text())
            c.validate([row])
            return row["text"]

    def test_dotted_handles_with_parentheses_are_removed_and_scan_refuses(self):
        for text in ("@john.doe (my coworker) please review", "@jane.smith(cc) ok", "@john.doe (note)"):
            with self.subTest(text=text):
                with self.assertRaises(KitError): s.scan(text)
                self.assertNotIn(text.split()[0].split("(")[0], s.scrub(text))
                s.scan(s.scrub(text))

    def test_dotted_handles_do_not_survive_saved_submission(self):
        for text in ("@john.doe (my coworker) please review", "@jane.smith(cc) ok", "@john.doe (note)"):
            with self.subTest(text=text):
                result = self.saved_text(text)
                self.assertNotIn("@john.doe", result)
                self.assertNotIn("@jane.smith", result)
                self.assertTrue(result.startswith("<REDACTED>"))

    def test_dotted_phone_is_scrubbed_and_raw_scan_refuses(self):
        for text in ("555.123.4567", "555.123.4567.", "Call 555.123.4567. Then review."):
            with self.subTest(text=text):
                with self.assertRaises(KitError): s.scan(text)
                self.assertEqual(s.scrub(text), text.replace("555.123.4567", "<REDACTED>"))
                s.scan(s.scrub(text))

    def test_dotted_phone_does_not_survive_saved_submission(self):
        for text in ("555.123.4567", "555.123.4567."):
            self.assertEqual(self.saved_text(text), text.replace("555.123.4567", "<REDACTED>"))

    def test_actual_dotted_decorators_survive_with_def_class_and_chains(self):
        for text in ("@functools.lru_cache\ndef f():\n    pass\n", "@pytest.fixture\n\ndef fixture():\n    pass\n", '@app.route("/")\n@auth.required\ndef home():\n    pass\n', "@package.decorator\nclass Example:\n    pass\n", "@package.decorator\nasync def fetch():\n    pass\n"):
            with self.subTest(text=text):
                self.assertEqual(self.saved_text(text), text)
                s.scan(text)

    def test_orphan_decorator_and_personal_handle_chain_not_exempt(self):
        for text in ("@pytest.fixture", "@functools.lru_cache", "@john.doe(note)\n@jane.smith(cc)\nplease review"):
            with self.subTest(text=text):
                self.assertIn("<REDACTED>", s.scrub(text))
                with self.assertRaises(KitError): s.scan(text)

    def test_other_versions_dates_and_ips_still_unchanged(self):
        text = "2026-10-28 1.2.3 123.456.789 10.0.0.1 192.168.1.20."
        self.assertEqual(self.saved_text(text), text)
        s.scan(text)


if __name__ == "__main__":
    unittest.main()
