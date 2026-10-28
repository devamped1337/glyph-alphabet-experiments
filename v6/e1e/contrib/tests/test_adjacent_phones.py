"""Actual saved-file regressions for adjacent/oversized phone candidates at f7b98f2."""
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

PAIRS = (
    "Call 555-123-4567 555-987-6543",
    "+61 412 345 678 (0412 345 678)",
    "(02) 9876 5432 (02) 9876 5433",
    "0412.345.678. 1.555.123.4567",
)


class AdjacentPhones(unittest.TestCase):
    def save(self, text):
        with tempfile.TemporaryDirectory() as folder:
            source, target = Path(folder) / "input.jsonl", Path(folder) / "output.jsonl"
            source.write_text(json.dumps(dict(conv_id="one", seq=1, sender_role="planner", receiver_role="worker", kind="handoff", text=text)))
            with patch("builtins.input", side_effect=["yes", "yes", "private", "anonymous", "yes"]), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(c.main([str(source), "--format", "jsonl", "--output", str(target)]), 0)
            row = json.loads(target.read_text())
            c.validate([row])
            return row

    def test_reported_pairs_do_not_survive_actual_saved_submission(self):
        for value in PAIRS:
            for ending in ("", "."):
                with self.subTest(value=value, ending=ending):
                    row = self.save(value + ending)
                    self.assertIn("<REDACTED>", row["text"])
                    self.assertFalse(any(char.isdigit() for char in row["text"]), row["text"])
                    row["text"] = value + ending
                    with self.assertRaisesRegex(KitError, "message 1; rule phone"):
                        c.validate([row])

    def test_final_scan_refuses_all_reported_raw_pairs(self):
        for value in PAIRS:
            for ending in ("", "."):
                with self.subTest(value=value, ending=ending):
                    with self.assertRaisesRegex(KitError, "rule phone"): s.scan(value + ending)
                    clean = s.scrub(value + ending)
                    self.assertFalse(any(char.isdigit() for char in clean))
                    s.scan(clean)

    def test_more_than_eighteen_digits_does_not_disable_redaction(self):
        for value in ("1234567890123456789", "123456789012345678901234567890",
                      "123 456 789 012 345 678 901", "555-123-4567 (555-987-6543) 555-654-3210"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(KitError, "rule phone"): s.scan(value)
                self.assertFalse(any(char.isdigit() for char in self.save(value)["text"]))

    def test_encoded_separator_variants_are_removed_from_saved_rows(self):
        for value in ("555-123-4567%20555-987-6543", r"555-123-4567\u0020555-987-6543",
                      "+61 412 345 678%20(0412 345 678)"):
            with self.subTest(value=value):
                with self.assertRaises(KitError): s.scan(value)
                self.assertFalse(any(char.isdigit() for char in self.save(value)["text"]))

    def test_protected_versions_ips_and_dates_between_phones_still_survive(self):
        for token in ("1.2.3", "10.0.19045.1234", "120.0.6099.109", "192.168.1.20", "0.0.0.0", "2026-10-28"):
            with self.subTest(token=token):
                original = "555-123-4567 " + token + " 555-987-6543"
                self.assertEqual(self.save(original)["text"], "<REDACTED> " + token + " <REDACTED>")


if __name__ == "__main__": unittest.main()
