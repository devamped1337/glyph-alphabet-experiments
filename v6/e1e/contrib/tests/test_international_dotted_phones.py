"""Saved-file phone/privacy and decorator complexity regressions for 08d11a4."""
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

PHONES = ("+61.412.345.678", "0412.345.678", "1.555.123.4567",
          "+1.555.123.4567", "02.9876.5432", "44.20.7946.0958")


class InternationalDottedPhones(unittest.TestCase):
    def save(self, text):
        with tempfile.TemporaryDirectory() as folder:
            source, target = Path(folder) / "input.jsonl", Path(folder) / "output.jsonl"
            source.write_text(json.dumps(dict(conv_id="one", seq=1, sender_role="planner", receiver_role="worker", kind="handoff", text=text)))
            with patch("builtins.input", side_effect=["yes", "yes", "private", "anonymous", "yes"]), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(c.main([str(source), "--format", "jsonl", "--output", str(target)]), 0)
            row = json.loads(target.read_text())
            c.validate([row])
            return row

    def test_all_reported_phones_scrubbed_and_raw_final_scan_refuses(self):
        for phone in PHONES:
            for ending in ("", ".", ". Next sentence.", ", please."):
                with self.subTest(phone=phone, ending=ending):
                    original = "Call " + phone + ending
                    self.assertEqual(s.scrub(original), "Call <REDACTED>" + ending)
                    with self.assertRaisesRegex(KitError, "rule phone"):
                        s.scan(original)
                    s.scan(s.scrub(original))

    def test_all_reported_phones_absent_from_actual_saved_rows(self):
        for phone in PHONES:
            for ending in ("", "."):
                with self.subTest(phone=phone, ending=ending):
                    row = self.save("Call " + phone + ending)
                    self.assertEqual(row["text"], "Call <REDACTED>" + ending)
                    self.assertNotIn(phone, json.dumps(row))
                    # The submission validator also refuses reintroduced raw content.
                    row["text"] = phone + ending
                    with self.assertRaisesRegex(KitError, "message 1; rule phone"):
                        c.validate([row])

    def test_real_versions_and_valid_ipv4_survive_saved_rows(self):
        for token in ("1.2.3", "10.0.19045.1234", "120.0.6099.109", "123.456.789",
                      "0.0.0.0", "0.123.45.67", "10.0.0.1", "127.0.0.1", "192.168.1.20", "255.255.255.255"):
            for ending in ("", "."):
                with self.subTest(token=token, ending=ending):
                    self.assertEqual(self.save("Keep " + token + ending)["text"], "Keep " + token + ending)
                    s.scan(token + ending)

    def test_adjacent_versions_ips_dates_and_phone_keep_their_boundaries(self):
        for phone in PHONES:
            original = "2026-10-28 10.0.19045.1234; call " + phone + ". IP 0.0.0.0 and 120.0.6099.109.\r\n"
            self.assertEqual(self.save(original)["text"], original.replace(phone, "<REDACTED>"))

    def test_encoded_forms_are_also_removed_from_saved_rows(self):
        for text in ("+61%2e412%2e345%2e678", r"0412\u002e345\u002e678", "%2b1.555.123.4567"):
            with self.subTest(text=text):
                with self.assertRaises(KitError): s.scan(text)
                self.assertEqual(self.save(text)["text"], "<REDACTED>")

    def test_decorator_stacks_do_not_reparse_following_lines(self):
        count = 2000
        text = "@package.decorator\n" * count + "def example():\n    pass\n"
        original_parse = s.ast.parse
        calls = 0
        def bounded_parse(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls > count * 4:
                self.fail("Decorator lines were repeatedly reparsed within the literal/canonical scrub and scan passes")
            return original_parse(*args, **kwargs)
        with patch.object(s.ast, "parse", side_effect=bounded_parse):
            self.assertEqual(s.scrub(text), text)
            s.scan(text)


if __name__ == "__main__": unittest.main()
