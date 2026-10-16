import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import uuid

SCRIPT = Path(__file__).with_name("context_bridge.py")
THREAD = "0199a213-81c0-7800-8aa1-bbab2a035a53"


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.context = self.root / "context.md"
        self.context.write_text("A9 remains a fail. A10 is secondary.")
        self.request = self.root / "question.txt"
        self.request.write_text("Acknowledge context.")
        self.state = self.root / "private"
        self.fake = self.root / "fake-codex"

    def fake_cli(self, mode="ok", thread=THREAD):
        self.fake.write_text(
            "#!/usr/bin/env python3\nimport json,re,sys\n"
            "prompt=sys.stdin.read()\n"
            "nonce=re.search(r'Handoff nonce: ([^\\n]+)',prompt).group(1)\n"
            f"mode={mode!r}\nthread={thread!r}\n"
            "print(json.dumps({'type':'thread.started','thread_id':thread}))\n"
            "if mode=='failed':\n"
            " print(json.dumps({'type':'turn.failed'}));sys.exit(0)\n"
            "text='Context received. '+(nonce if mode!='no_nonce' else '')\n"
            "print(json.dumps({'type':'item.completed','item':"
            "{'type':'agent_message','text':text}}))\n"
            "if mode!='truncated':print(json.dumps({'type':'turn.completed'}))\n"
        )
        self.fake.chmod(0o700)

    def run_bridge(self, *extra):
        return subprocess.run([
            sys.executable, str(SCRIPT), "--repo", str(self.repo),
            "--context", str(self.context), "--state-dir", str(self.state),
            "--request-file", str(self.request), "--codex-command", str(self.fake),
            *extra,
        ], capture_output=True, text=True)

    def test_dry_run_calls_no_model_and_writes_no_session(self):
        result = self.run_bridge("--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)["model_called"])
        self.assertFalse((self.state / "session.json").exists())

    def test_success_then_explicit_resume_with_updated_context(self):
        self.fake_cli()
        first = self.run_bridge()
        self.assertEqual(first.returncode, 0, first.stderr)
        old = json.loads((self.state / "session.json").read_text())
        self.context.write_text("A new decision, supplied on the next turn.")
        second = self.run_bridge()
        self.assertEqual(second.returncode, 0, second.stderr)
        new = json.loads((self.state / "session.json").read_text())
        request = json.loads((self.state / new["last_run"] / "request.json").read_text())
        self.assertIn("resume", request["command"])
        self.assertIn(THREAD, request["command"])
        self.assertNotIn("--last", request["command"])
        self.assertNotEqual(old["context_sha256"], new["context_sha256"])

    def test_bad_outputs_never_record_success(self):
        for mode in ("failed", "truncated", "no_nonce"):
            with self.subTest(mode=mode):
                self.fake_cli(mode)
                result = self.run_bridge()
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((self.state / "session.json").exists())

    def test_wrong_session_preserves_previous_state(self):
        self.fake_cli()
        self.assertEqual(self.run_bridge().returncode, 0)
        before = (self.state / "session.json").read_bytes()
        self.fake_cli(thread=str(uuid.uuid4()))
        result = self.run_bridge()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.state / "session.json").read_bytes(), before)

    def test_private_state_cannot_be_inside_project(self):
        self.state = self.repo / "private"
        result = self.run_bridge("--dry-run")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.state.exists())

    def test_adopts_explicit_greeting_session(self):
        self.fake_cli()
        result = self.run_bridge("--adopt-session", THREAD)
        self.assertEqual(result.returncode, 0, result.stderr)
        state = json.loads((self.state / "session.json").read_text())
        request = json.loads((self.state / state["last_run"] / "request.json").read_text())
        self.assertIn("resume", request["command"])
        self.assertEqual(state["session_id"], THREAD)


if __name__ == "__main__":
    unittest.main()
