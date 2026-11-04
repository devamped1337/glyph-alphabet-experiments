"""Saved-file regressions for typographic phone separators; synthetic data only."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.parse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import contribute as c
import scrub as s
from errors import KitError


class UnicodePhoneDashes(unittest.TestCase):
    def save(self, text):
        with tempfile.TemporaryDirectory() as folder:
            source, target = Path(folder) / "input.jsonl", Path(folder) / "output.jsonl"
            source.write_text(json.dumps(dict(conv_id="one", seq=1, sender_role="planner",
                                             receiver_role="worker", kind="handoff", text=text)))
            with patch("builtins.input", side_effect=["yes", "yes", "private", "anonymous", "yes"]), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(c.main([str(source), "--format", "jsonl", "--output", str(target)]), 0)
            row = json.loads(target.read_text())
            c.validate([row])
            return row

    def test_all_six_dashes_are_removed_in_actual_saved_files(self):
        for dash in "‐‑‒–—−":
            for ending in ("", "."):
                text = "Call " + dash.join(("555", "123", "4567")) + ending
                with self.subTest(dash=dash, ending=ending):
                    row = self.save(text)
                    self.assertEqual(row["text"], "Call <REDACTED>" + ending)
                    row["text"] = text
                    with self.assertRaisesRegex(KitError, "message 1; rule phone"):
                        c.validate([row])

    def test_encoded_dashes_are_removed_in_actual_saved_files(self):
        for dash in "‐‑‒–—−":
            for separator in (urllib.parse.quote(dash), "\\u%04x" % ord(dash)):
                with self.subTest(separator=separator):
                    text = separator.join(("555", "123", "4567"))
                    self.assertEqual(self.save(text)["text"], "<REDACTED>")
                    with self.assertRaisesRegex(KitError, "rule phone"):
                        s.scan(text)

    def test_international_and_adjacent_unicode_dash_phones(self):
        for text in ("+61–412–345–678", "02−9876−5432", "555‑123‑4567 555–987–6543"):
            with self.subTest(text=text):
                self.assertFalse(any(char.isdigit() for char in self.save(text)["text"]))

    def test_unmatched_unicode_punctuation_and_numeric_context_are_preserved(self):
        text = "caf\u00e9 ‐ ‑ ‒ – — −\r\n1.2.3 10.0.19045.1234 120.0.6099.109 192.168.1.20 2026-10-28"
        self.assertEqual(self.save(text)["text"], text)

    def test_repeated_dot_message_does_not_stall(self):
        # Bound the reported maximum-message case in a child so a regression cannot hang the suite.
        code = "import scrub; text='1.'*32767+'1'; assert scrub.scrub(text)==text; scrub.scan(text)"
        subprocess.run([sys.executable, "-c", code], cwd=Path(s.__file__).parent,
                       check=True, capture_output=True, timeout=5)

    def test_separator_prechecks_keep_matching_real_credentials_and_hosts(self):
        for text in ("password = 'hunter2'", "x.y.secret: hidden", "user.name@host",
                     "user at gmail dot com", "user.name@example.com"):
            with self.subTest(text=text):
                with self.assertRaises(KitError):
                    s.scan(text)
                self.assertIn("<REDACTED>", s.scrub(text))


if __name__ == "__main__":
    unittest.main()
