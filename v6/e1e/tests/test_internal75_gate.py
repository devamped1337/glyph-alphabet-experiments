"""Gate tests for the internal-75 prep. No compression, mining, or dictionary training."""
import hashlib
import signal
import importlib.util
import inspect
import os
import pathlib
import subprocess
import sys
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

    def test_watchdog_is_armed_before_the_package_import(self):
        src = inspect.getsource(MOD.run_measurement)
        self.assertLess(src.index("install_watchdog"), src.index("from e1e"))

    def test_complete_ack_accepts_and_rejects_tampered_reviews(self):
        head = "ab" * 20
        harness = MOD._sha256(MOD.__file__)
        support = MOD.support_hashes()
        approve = "VERDICT: APPROVE\nSOURCE_COVERAGE: full\nCANDIDATE: %s\nHARNESS: %s\n" % (head, harness)
        gpt = self._text(approve)
        grok = self._text(approve)
        payload = {
            "authorize_run": True,
            "candidate_commit": head,
            "combined_sha256": MOD.manifest()["combined_sha256"],
            "harness_sha256": harness,
            "support_sha256": support,
            "gpt_review_path": gpt[0],
            "gpt_review_sha256": gpt[1],
            "grok_review_path": grok[0],
            "grok_review_sha256": grok[1],
        }
        self.assertIsNone(MOD.ack_refusal(self._ack(payload), head_sha=head))
        changed = self._text("VERDICT: CHANGES REQUIRED\nSOURCE_COVERAGE: full\nCANDIDATE: %s\nHARNESS: %s\n" % (head, harness))
        payload["gpt_review_path"], payload["gpt_review_sha256"] = changed[0], changed[1]
        self.assertIn("verdict", MOD.ack_refusal(self._ack(payload), head_sha=head))
        payload["gpt_review_path"], payload["gpt_review_sha256"] = gpt
        payload["gpt_review_sha256"] = "0" * 64
        self.assertIn("hash mismatch", MOD.ack_refusal(self._ack(payload), head_sha=head))
        payload["gpt_review_path"] = os.path.join(ROOT, "internal75", "NO_SUCH_REVIEW.md")
        payload["gpt_review_sha256"] = gpt[1]
        self.assertIn("missing", MOD.ack_refusal(self._ack(payload), head_sha=head))
        partial = self._text("VERDICT: APPROVE\nSOURCE_COVERAGE: partial\nCANDIDATE: %s\nHARNESS: %s\n" % (head, harness))
        payload["gpt_review_path"], payload["gpt_review_sha256"] = partial[0], partial[1]
        self.assertIn("coverage", MOD.ack_refusal(self._ack(payload), head_sha=head))

    def test_existing_output_is_not_overwritten(self):
        folder = ROOT / "measurements" / "internal75-audit"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / "collision.json"
        path.write_bytes(b"keep")
        try:
            with self.assertRaises(SystemExit):
                MOD.prepare_output(str(path))
            self.assertEqual(path.read_bytes(), b"keep")
        finally:
            path.unlink()

    def test_report_keeps_component_tallies_and_separates_gzip(self):
        def arm(total):
            return {
                "message_bytes": 3, "message_prefix_bytes": 1, "control_bytes": 2, "control_prefix_bytes": 1,
                "declare_bytes_incl_prefix": 4, "reject_bytes_incl_prefix": 0, "retransmit_bytes_incl_prefix": 0,
                "sync_upload": 8, "sync_download": 16, "sync_total": 24, "total": total,
                "covered_bytes": 1, "input_bytes": 9,
            }
        totals = {name: arm(10) for name in MOD.ARMS}
        totals["7"]["total"] = 30
        totals["_break_even"] = {"updates_observed": 0, "joins_observed": 0}
        publication = {"publications": [{"sched_version": 1, "new_entries": 2, "full_bytes": 40}],
                       "schedule": [{"sched_version": 1, "status": "published"}],
                       "version_index_by_rank": [1]}
        report = MOD.build_report({"combined_sha256": "abc", "messages": 1}, totals, publication, 7, ("0.23.0", (1, 5, 6)))
        self.assertEqual(report["arms"]["5"]["sync_upload"], 8)
        self.assertEqual(report["arms"]["5"]["message_bytes"], 3)
        self.assertEqual(report["arms"]["5"]["declare_bytes_incl_prefix"], 4)
        self.assertEqual(report["break_even"]["updates_observed"], 0)
        self.assertEqual(report["publication"]["publications"][0]["new_entries"], 2)
        self.assertFalse(report["gzip9_message_frames_only"]["comparable_as_arm_total"])
        self.assertNotIn("gzip9", report["primary_totals"])

    def test_encoder_verify_failure_aborts_before_raw_fallback(self):
        from e1e import Publisher, make_entry
        from e1e.canon import AuditAbort, E1EError
        from e1e import compact as compact
        pub = Publisher()
        pub.publish([make_entry("e00", 1, "OK")])
        state = pub.state
        known = {state.digest: state}
        decl = {"version": state.version, "digest": state.digest}
        original = compact.decode_compact

        def bad(*args, **kwargs):
            raise E1EError("E_SCHEMA", "forced")

        compact.decode_compact = bad
        try:
            with self.assertRaises(AuditAbort):
                compact.encode(known, decl, b"OK", audit_strict=True)
            payload, info = compact.encode(known, decl, b"OK", audit_strict=False)
            self.assertEqual(info["reason"], "verify_failed")
            self.assertTrue(payload.startswith(b"{"))
        finally:
            compact.decode_compact = original

    def test_arm1_mismatch_aborts_under_optimization(self):
        from e1e.canon import AuditAbort
        from e1e import codec
        self.assertNotIn("\n    assert ", inspect.getsource(codec.audit_arm1))
        original = codec.decode_message
        codec.decode_message = lambda state, wire: b"nope"
        try:
            with self.assertRaises(AuditAbort):
                codec.audit_arm1(b"hello", codec.raw_wire(b"hello"))
        finally:
            codec.decode_message = original
        script = (
            "import e1e.codec as codec\n"
            "from e1e.canon import AuditAbort\n"
            "codec.decode_message = lambda state, wire: b'nope'\n"
            "try:\n"
            "    codec.audit_arm1(b'hello', codec.raw_wire(b'hello'))\n"
            "except AuditAbort:\n"
            "    raise SystemExit(0)\n"
            "raise SystemExit(1)\n"
        )
        ran = subprocess.run([sys.executable, "-O", "-c", script], cwd=str(ROOT), capture_output=True, text=True)
        self.assertEqual(ran.returncode, 0, ran.stderr)

    def test_publication_never_deletes_a_path_it_did_not_create(self):
        folder = ROOT / "measurements" / "internal75-audit"
        folder.mkdir(parents=True, exist_ok=True)
        final = folder / "owned.json"
        partial = folder / "owned.json.partial"
        raced = folder / "raced.json"
        for path in (final, partial, raced):
            if path.exists():
                path.unlink()
        partial.write_bytes(b"KEEP-PARTIAL")
        try:
            with self.assertRaises(SystemExit) as caught:
                MOD.run_measurement(str(final), deadline_s=30, compute=lambda: b"NEW")
            self.assertIn("preexisting", str(caught.exception))
            self.assertEqual(partial.read_bytes(), b"KEEP-PARTIAL")
            self.assertFalse(final.exists())
            raced.write_bytes(b"KEEP-FINAL")

            def plant():
                raced.write_bytes(b"KEEP-FINAL")
                return b"NEW-FINAL"

            raced.unlink()
            with self.assertRaises(SystemExit) as caught:
                MOD.run_measurement(str(raced), deadline_s=30, compute=plant)
            self.assertIn("preexisting", str(caught.exception))
            self.assertEqual(raced.read_bytes(), b"KEEP-FINAL")
            self.assertFalse(pathlib.Path(str(raced) + ".partial").exists())
        finally:
            MOD.clear_watchdog()
            for path in (final, partial, raced, pathlib.Path(str(raced) + ".partial")):
                if path.exists():
                    path.unlink()

    def test_write_accepts_only_a_complete_buffer(self):
        folder = ROOT / "measurements" / "internal75-audit"
        folder.mkdir(parents=True, exist_ok=True)
        marker = folder / "write-marker"
        marker.write_bytes(b"KEEP")
        blob = b"{\"report\":true}\n"
        real = os.write
        created = []

        def run(mode):
            dest = folder / ("write-" + mode + ".json")
            partial = pathlib.Path(str(dest) + ".partial")
            for path in (dest, partial):
                if path.exists():
                    path.unlink()
            created.extend((dest, partial))
            state = {"n": 0}

            def wrapped(fd, data):
                state["n"] += 1
                if mode == "short":
                    if state["n"] == 1:
                        return real(fd, data[:1])
                    return real(fd, data)
                if mode == "zero":
                    return 0
                if mode == "error":
                    if state["n"] == 1:
                        return real(fd, data[:1])
                    raise OSError(28, "no space")
                if mode == "deadline":
                    MOD._WATCH["expired"] = True
                    return real(fd, data[:1])
                if mode == "wild":
                    return len(data) + 5
                return real(fd, data)

            os.write = wrapped
            try:
                if mode == "short":
                    MOD.run_measurement(str(dest), deadline_s=30, compute=lambda: blob)
                    self.assertEqual(dest.read_bytes(), blob)
                    self.assertFalse(partial.exists())
                elif mode == "error":
                    with self.assertRaises(OSError):
                        MOD.run_measurement(str(dest), deadline_s=30, compute=lambda: blob)
                    self.assertFalse(dest.exists())
                    self.assertFalse(partial.exists())
                else:
                    with self.assertRaises(SystemExit) as caught:
                        MOD.run_measurement(str(dest), deadline_s=30, compute=lambda: blob)
                    self.assertFalse(dest.exists(), mode)
                    self.assertFalse(partial.exists(), mode)
                    if mode == "zero":
                        self.assertIn("no progress", str(caught.exception))
                    elif mode == "wild":
                        self.assertIn("not progress", str(caught.exception))
                    else:
                        self.assertIn("deadline", str(caught.exception))
            finally:
                os.write = real
                MOD.clear_watchdog()
            self.assertEqual(marker.read_bytes(), b"KEEP", mode)

        try:
            for mode in ("short", "zero", "error", "deadline", "wild"):
                run(mode)
        finally:
            os.write = real
            MOD.clear_watchdog()
            if marker.exists():
                marker.unlink()
            for path in created:
                if path.exists():
                    path.unlink()

    def test_signal_between_create_and_register_does_not_leave_a_file(self):
        """SIGALRM is sent after the creating call returns and before registration.

        The mask must defer delivery until the new path is owned. Otherwise the
        created file survives the 'no report kept' cleanup.
        """
        folder = ROOT / "measurements" / "internal75-audit"
        folder.mkdir(parents=True, exist_ok=True)
        cases = ("partial", "final")
        created = []
        real_open, real_link = os.open, os.link
        try:
            for case in cases:
                dest = folder / ("signal-" + case + ".json")
                partial = pathlib.Path(str(dest) + ".partial")
                marker = folder / ("signal-marker-" + case)
                for path in (dest, partial):
                    if path.exists():
                        path.unlink()
                marker.write_bytes(b"KEEP")
                created.extend((dest, partial, marker))

                def wrapped_open(path, flags, mode=0o644, *, dir_fd=None):
                    fd = real_open(path, flags, mode) if dir_fd is None else real_open(path, flags, mode, dir_fd=dir_fd)
                    if case == "partial" and str(path).endswith(".partial") and flags & os.O_EXCL:
                        os.kill(os.getpid(), signal.SIGALRM)
                    return fd

                def wrapped_link(src, dst, **kwargs):
                    real_link(src, dst)
                    if case == "final":
                        os.kill(os.getpid(), signal.SIGALRM)

                os.open = wrapped_open
                os.link = wrapped_link
                try:
                    with self.assertRaises(SystemExit) as caught:
                        MOD.run_measurement(str(dest), deadline_s=30, compute=lambda: b"NEW")
                finally:
                    os.open, os.link = real_open, real_link
                    MOD.clear_watchdog()
                self.assertIn("deadline", str(caught.exception), case)
                self.assertFalse(dest.exists(), case)
                self.assertFalse(partial.exists(), case)
                self.assertEqual(marker.read_bytes(), b"KEEP", case)
        finally:
            os.open, os.link = real_open, real_link
            MOD.clear_watchdog()
            for path in created:
                if path.exists():
                    path.unlink()

    def test_deadline_at_each_publication_boundary_leaves_no_success_file(self):
        folder = ROOT / "measurements" / "internal75-audit"
        folder.mkdir(parents=True, exist_ok=True)
        boundaries = ("before_create", "after_create", "after_write", "after_link", "after_publish")
        created = []
        try:
            for name in boundaries:
                dest = folder / ("bound-" + name + ".json")
                partial = pathlib.Path(str(dest) + ".partial")
                marker = folder / ("marker-" + name)
                for path in (dest, partial):
                    if path.exists():
                        path.unlink()
                if name == "before_create":
                    partial.write_bytes(b"KEEP-PARTIAL")
                marker.write_bytes(b"KEEP")
                created.extend((dest, partial, marker))

                def hook(step, target=name):
                    if step == target:
                        MOD._WATCH["expired"] = True

                with self.assertRaises(SystemExit) as caught:
                    MOD.run_measurement(str(dest), deadline_s=30, compute=lambda: b"NEW", hook=hook)
                self.assertIn("deadline", str(caught.exception), name)
                self.assertFalse(dest.exists(), name)
                if name == "before_create":
                    self.assertEqual(partial.read_bytes(), b"KEEP-PARTIAL", name)
                else:
                    self.assertFalse(partial.exists(), name)
                self.assertEqual(marker.read_bytes(), b"KEEP", name)
        finally:
            MOD.clear_watchdog()
            for path in created:
                if path.exists():
                    path.unlink()

    def test_late_alarm_after_publish_removes_the_report(self):
        folder = ROOT / "measurements" / "internal75-audit"
        folder.mkdir(parents=True, exist_ok=True)
        dest = folder / "late-alarm.json"
        if dest.exists():
            dest.unlink()
        original = MOD.clear_watchdog

        def late():
            original()
            MOD._WATCH["expired"] = True

        MOD.clear_watchdog = late
        try:
            with self.assertRaises(SystemExit) as caught:
                MOD.run_measurement(str(dest), deadline_s=30, compute=lambda: b"NEW")
            self.assertIn("deadline", str(caught.exception))
            self.assertFalse(dest.exists())
            self.assertFalse(pathlib.Path(str(dest) + ".partial").exists())
        finally:
            MOD.clear_watchdog = original
            MOD.clear_watchdog()
            if dest.exists():
                dest.unlink()

    def test_timeout_during_compute_and_finalization_leaves_no_report(self):
        folder = ROOT / "measurements" / "internal75-audit"
        folder.mkdir(parents=True, exist_ok=True)
        slow_path = folder / "slow.json"
        late_path = folder / "late.json"

        def slow():
            time.sleep(0.3)
            return b"{}\n"

        def late():
            MOD._WATCH["expired"] = True
            return b"{}\n"

        try:
            with self.assertRaises(SystemExit) as caught:
                MOD.run_measurement(str(slow_path), deadline_s=0.05, compute=slow)
            self.assertIn("deadline", str(caught.exception))
            self.assertFalse(slow_path.exists())
            self.assertFalse(pathlib.Path(str(slow_path) + ".partial").exists())
            with self.assertRaises(SystemExit) as caught:
                MOD.run_measurement(str(late_path), deadline_s=30, compute=late)
            self.assertIn("deadline", str(caught.exception))
            self.assertFalse(late_path.exists())
            self.assertFalse(pathlib.Path(str(late_path) + ".partial").exists())
        finally:
            MOD.clear_watchdog()
            for path in (slow_path, late_path, pathlib.Path(str(slow_path) + ".partial"), pathlib.Path(str(late_path) + ".partial")):
                if path.exists():
                    path.unlink()

    def _text(self, text):
        handle = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False)
        handle.write(text)
        handle.close()
        self.addCleanup(os.remove, handle.name)
        raw = pathlib.Path(handle.name).read_bytes()
        return handle.name, hashlib.sha256(raw).hexdigest()

    def _ack(self, payload):
        handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        import json
        json.dump(payload, handle)
        handle.close()
        self.addCleanup(os.remove, handle.name)
        return handle.name


if __name__ == "__main__":
    unittest.main()
