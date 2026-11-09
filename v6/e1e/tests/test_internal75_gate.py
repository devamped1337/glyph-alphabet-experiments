"""Gate tests for the internal-75 prep. No compression, mining, or dictionary training."""
import hashlib
import importlib.util
import json
import os
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("internal75_run", ROOT / "tools" / "internal75_run.py")
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


class Internal75Gate(unittest.TestCase):
    def test_validate_frozen_counts_and_bytes(self):
        summary = MOD.validate()
        self.assertEqual(summary["messages"], 75)
        self.assertEqual(summary["conversations"], 30)
        self.assertEqual(summary["authors"], {"gpt": 25, "grok": 25, "claude": 15, "glyph": 10})
        self.assertEqual(summary["combined_sha256"],
                         "b94115fb424947f0555b2ba6669f8d3ba11b53e664e640d4b9670a6b30535439")

    def test_plan_does_not_tune_or_hold_out(self):
        got = MOD.plan()
        self.assertFalse(got["calls_tune"])
        self.assertFalse(got["calls_select_baseline4"])
        self.assertFalse(got["calls_dev_screen"])
        self.assertEqual(got["heldout_count"], 0)
        self.assertEqual(got["partition"], "all_dev")
        self.assertEqual(got["fixed_point_transferred_from_prior_synthetic_screen"]["L"], 32)
        self.assertEqual(got["fixed_point_transferred_from_prior_synthetic_screen"]["k"], 2)
        self.assertEqual(got["fixed_point_transferred_from_prior_synthetic_screen"]["C"], 50)
        self.assertNotIn("4", got["arms"])
        self.assertEqual(got["coverage_floor_unchanged"], 0.20)
        self.assertTrue(got["prior_negative_screens_remain_failed"])
        self.assertFalse(got["generalisable_to_outside_traffic"])

    def test_missing_ack_refuses_before_measurement(self):
        reason = MOD.ack_refusal(os.devnull)
        self.assertIn("missing", reason)
        with self.assertRaises(SystemExit) as caught:
            MOD.main(["--ack", os.path.join(ROOT, "internal75", "NO_SUCH_ACK.json"), "--out", os.path.join(ROOT, "nope.json")])
        self.assertIn("missing", str(caught.exception))
        self.assertFalse((ROOT / "nope.json").exists())

    def test_harness_source_does_not_call_tuner(self):
        text = (ROOT / "tools" / "internal75_run.py").read_text(encoding="utf-8")
        for banned in ("K.tune(", "select_baseline4(", "e1f_dev_screen.py", "split_real("):
            self.assertNotIn(banned, text)
        pin = MOD.manifest()["harness_sha256"]
        self.assertEqual(pin, hashlib.sha256((ROOT / "tools" / "internal75_run.py").read_bytes()).hexdigest())

    def test_protected_outputs_are_refused(self):
        for rel in MOD.PROTECTED:
            with self.assertRaises(SystemExit):
                MOD._refuse_output(str(ROOT / rel))


if __name__ == "__main__":
    unittest.main()
