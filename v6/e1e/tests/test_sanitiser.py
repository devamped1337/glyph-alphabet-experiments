"""Regression checks for the dev-corpus sanitiser (tools/build_glyph_own_dev.py). Rejection-style tests."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import build_glyph_own_dev as b  # noqa: E402


class Sanitiser(unittest.TestCase):
    def setUp(self):
        self._h = b.HANDLES
        b.HANDLES = sorted(set(self._h) | {"swift-lantern", "tac_paxyk"}, key=lambda n: (-len(n), n))

    def tearDown(self):
        b.HANDLES = self._h

    def clean(self, t):
        o = b.sanitise(t)
        b.scan(o)  # must pass the independent scan
        return o

    def test_full_quoted_values(self):
        self.assertEqual(self.clean('{"password": "correct horse battery staple"}'), '{"password": "<SECRET>"}')
        self.assertEqual(self.clean('{"password": "a \\"quoted\\" pass"}'), '{"password": "<SECRET>"}')
        self.assertEqual(self.clean("{'api_key': 'p q r'}"), "{'api_key': '<SECRET>'}")
        self.assertEqual(self.clean('x \\"secret\\": \\"a b\\" y'), 'x \\"secret\\": \\"<SECRET>\\" y')

    def test_short_and_unquoted_values(self):
        self.assertEqual(self.clean('{"token": "abc"}'), '{"token": "<SECRET>"}')
        self.assertEqual(self.clean('{"token":"a"}'), '{"token":"<SECRET>"}')
        for t, want in [("token=a", "token=<SECRET>"), ("password: hunter2", "password: <SECRET>"),
                        ("GITHUB_TOKEN=xyz;", "GITHUB_TOKEN=<SECRET>;"), ("client_secret = s3", "client_secret = <SECRET>"),
                        ("Authorization: Bearer abcdefgh123", "Authorization: <SECRET>")]:
            self.assertEqual(self.clean(t), want)

    def test_handles_and_names(self):
        self.assertEqual(self.clean("Thanks also to swift-lantern on 1f916."), "Thanks also to <HANDLE> on 1f916.")
        self.assertEqual(self.clean("Swift-Lantern agreed"), "<HANDLE> agreed")
        self.assertEqual(self.clean("ping @someone_new and u/other"), "ping <HANDLE> and <HANDLE>")
        self.assertEqual(self.clean("cc new-agent-7 on Moltbook"), "cc <HANDLE> on Moltbook")
        self.assertEqual(self.clean("Hi GPT, Glyph here"), "Hi GPT, <AGENT_SELF> here")
        self.assertEqual(self.clean("@property"), "@property")

    def test_scan_rejects_survivors(self):
        for bad in ['{"password": "x"}', "token=abc", "swift-lantern", "Stefan", "a@b.example", "https://x.example",
                    "/home/box/x", "ghp_" + "a" * 20, "@someone", "Glyph", "Bearer abcdefgh1234"]:
            with self.assertRaises(SystemExit, msg=bad):
                b.scan(bad)

    def test_no_overredaction_of_counts(self):
        self.assertEqual(self.clean("max_tokens=800 and 25 tests"), "max_tokens=800 and 25 tests")


if __name__ == "__main__":
    unittest.main()
