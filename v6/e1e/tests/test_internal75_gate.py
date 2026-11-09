"""Gate tests for the internal-75 prep. No compression, mining, or dictionary training."""
import hashlib
import importlib.util
import os
import pathlib
import tempfile
import time
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
                MOD.prepare_output(str(ROOT / rel))
        with self.assertRaises(SystemExit):
            MOD.prepare_output(str(ROOT / "data" / "internal75" / "combined75_messages.jsonl"))
        with self.assertRaises(SystemExit):
            MOD.prepare_output(str(ROOT / "tools" / "internal75_run.py"))

    def test_review_text_must_approve_full_source_and_this_candidate(self):
        head, harness = "a" * 40, "b" * 64
        good = "VERDICT: APPROVE\nSOURCE_COVERAGE: full\nCANDIDATE: %s\nHARNESS: %s\n" % (head, harness)
        self.assertEqual(MOD.review_problems(good, head, harness), [])
        self.assertTrue(MOD.review_problems("VERDICT: CHANGES REQUIRED\nSOURCE_COVERAGE: full\nCANDIDATE: %s\nHARNESS: %s\n" % (head, harness), head, harness))
        self.assertTrue(MOD.review_problems("VERDICT: APPROVE\nSOURCE_COVERAGE: partial\nCANDIDATE: %s\nHARNESS: %s\n" % (head, harness), head, harness))
        self.assertTrue(MOD.review_problems(good, "c" * 40, harness))
        self.assertTrue(MOD.review_problems(good, head, "d" * 64))

    def test_ack_rejects_unbound_support_hashes(self):
        claimed = MOD.support_hashes()
        claimed["e1e/codec.py"] = "0" * 64
        path = self._ack({"authorize_run": True, "candidate_commit": "a" * 40,
                          "harness_sha256": MOD._sha256(MOD.__file__),
                          "combined_sha256": MOD.manifest()["combined_sha256"],
                          "support_sha256": claimed})
        reason = MOD.ack_refusal(path, head_sha="a" * 40)
        self.assertIn("support", reason)

    def test_coverage_does_not_invent_zero_and_gzip_is_not_an_arm(self):
        with self.assertRaises(SystemExit):
            MOD.coverage_record({"input_bytes": 10})
        zero = MOD.coverage_record({"covered_bytes": 0, "input_bytes": 0})
        self.assertIsNone(zero["coverage"])
        self.assertFalse(zero["coverage_defined"])
        gzip = MOD.gzip_record(12)
        self.assertFalse(gzip["comparable_as_arm_total"])
        self.assertNotIn("gzip", MOD.ARMS)

    def test_strict_decode_failure_does_not_retransmit(self):
        import e1e.codec as codec
        from e1e.canon import AuditAbort
        from e1e.compact import CompactLink

        class Rx:
            def declare(self):
                return {"version": 0, "digest": "sha256:" + "ab" * 32}

            @property
            def state(self):
                return self

            def fingerprint(self):
                return "fp"

        calls = {"n": 0}
        original = codec.decode_message

        def once(state, wire):
            calls["n"] += 1
            if calls["n"] == 1:
                raise codec.E1EError("E_SCHEMA", "forced")
            return b"hello"

        codec.decode_message = once
        try:
            plain = codec.Link({}, Rx())
            out, info = plain.transmit(b"hello")
            self.assertEqual(out, b"hello")
            self.assertTrue(any(frame[1] == "fallback" for frame in plain.frames))
            calls["n"] = 0
            strict = codec.Link({}, Rx(), audit_strict=True)
            with self.assertRaises(AuditAbort):
                strict.transmit(b"hello")
            self.assertFalse(any(frame[1] == "fallback" for frame in strict.frames))
        finally:
            codec.decode_message = original

        class Bad:
            class state:
                @staticmethod
                def fingerprint():
                    return "fp"

            @staticmethod
            def decode(payload):
                return b"other"

        strict_compact = CompactLink({}, Bad(), audit_strict=True)
        with self.assertRaises(AuditAbort):
            strict_compact.deliver(b"{}", b"hello", "raw")
        self.assertFalse(any(frame[1] == "fallback" for frame in strict_compact.frames))

    def test_watchdog_fires_and_is_not_an_exception(self):
        self.assertTrue(issubclass(MOD.AuditDeadline, BaseException))
        self.assertFalse(issubclass(MOD.AuditDeadline, Exception))
        MOD.install_watchdog(0.05)
        try:
            with self.assertRaises(MOD.AuditDeadline):
                time.sleep(0.4)
        finally:
            MOD.clear_watchdog()

    def _ack(self, payload):
        handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        import json
        json.dump(payload, handle)
        handle.close()
        self.addCleanup(os.remove, handle.name)
        return handle.name


if __name__ == "__main__":
    unittest.main()
