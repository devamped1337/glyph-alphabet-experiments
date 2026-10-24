"""Regression checks for the dev-corpus sanitiser (tools/build_glyph_own_dev.py). Rejection-style tests."""
import os
import sys
import json
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

    def assertRedacted(self, t, prefix, leaks=()):
        o = self.clean(t)
        self.assertTrue(o.startswith(prefix + "<SECRET>"), o)
        for x in leaks:
            self.assertNotIn(x, o)

    def test_full_quoted_values(self):
        # policy: everything after a credential key + separator, to end of line, becomes <SECRET>
        self.assertRedacted('{"password": "correct horse battery staple"}', '{"password": ', ["horse", "staple"])
        self.assertRedacted('{"password": "a \\"quoted\\" qq"}', '{"password": ', ["quoted", "qq"])
        self.assertRedacted("{'api_key': 'p q r'}", "{'api_key': ", ["p q"])
        self.assertRedacted('x \\"secret\\": \\"a b\\" y', 'x \\"secret\\": ', ["a b"])
        self.assertRedacted('{"password":["alpha","bravo"]}', '{"password":', ["alpha", "bravo"])
        dbl = json.dumps(json.dumps({"password": 'alpha "bravo" charlie'}))
        self.assertRedacted(dbl, '"{\\"password\\": ', ["alpha", "bravo", "charlie"])
        self.assertRedacted("password=alpha\\ beta", "password=", ["alpha", "beta"])
        self.assertEqual(self.clean('{"password": "x"}\nnext line'), '{"password": <SECRET>\nnext line')

    def test_short_and_unquoted_values(self):
        self.assertRedacted('{"token": "abc"}', '{"token": ', ["abc"])
        self.assertRedacted('{"token":"a"}', '{"token":', ['"a"'])
        for t, want in [("token=a", "token=<SECRET>"), ("password: hunter2", "password: <SECRET>"),
                        ("GITHUB_TOKEN=xyz;", "GITHUB_TOKEN=<SECRET>"), ("client_secret = s3", "client_secret = <SECRET>"),
                        ("Authorization: Bearer abcdefgh123", "Authorization: <SECRET>"),
                        ("Bearer abc", "Bearer <SECRET>"), ("basic Zm9v", "basic <SECRET>")]:
            self.assertEqual(self.clean(t), want)

    def test_urls_emails_paths(self):
        for t, want in [("ssh://git@host.example/alice/private.txt", "<URL>"), ('"alice smith"@host.example', "<EMAIL>"),
                        ("C:\\Users\\alice\\private.txt", "<WINPATH>"), ("mail bob.x+tag@sub.example.org now", "mail <EMAIL> now"),
                        ("see https://a.example/p?q=1.", "see <URL>"), ("/home/box/secret.txt", "<PATH>")]:
            self.assertEqual(self.clean(t), want)

    def test_handles_and_names(self):
        self.assertEqual(self.clean("Thanks also to swift-lantern on 1f916."), "Thanks also to <HANDLE> on 1f916.")
        self.assertEqual(self.clean("Swift-Lantern agreed"), "<HANDLE> agreed")
        self.assertEqual(self.clean("ping @someone_new and u/other"), "ping <HANDLE> and <HANDLE>")
        self.assertEqual(self.clean("cc new-agent-7 on Moltbook"), "cc <HANDLE> on Moltbook")
        self.assertEqual(self.clean("Hi GPT, Glyph here"), "Hi GPT, <AGENT_SELF> here")
        self.assertEqual(self.clean("@property"), "@property")
        self.assertEqual(self.clean("@property\ndef f"), "@property\ndef f")
        for t in ("@q", "@property.owner", "GLYPH", "glyph"):
            self.assertIn(self.clean(t), ("<HANDLE>", "<AGENT_SELF>"))
        self.assertEqual(self.clean("potter/bearer and tanner"), "potter/bearer and tanner")

    def test_scan_rejects_survivors(self):
        for bad in ['{"password": "x"}', "token=abc", "swift-lantern", "Stefan", "a@b.example", "https://x.example",
                    "/home/box/x", "ghp_" + "a" * 20, "@someone", "Glyph", "GLYPH", "Bearer abc", "@q", "C:\\Users\\a", "ssh://h/x", "<URL>>/alice",
                    '"password": "<SECRET>" leak', '"a b"@host.example']:
            with self.assertRaises(SystemExit, msg=bad):
                b.scan(bad)

    def test_no_overredaction_of_counts(self):
        self.assertEqual(self.clean("max_tokens=800 and 25 tests"), "max_tokens=800 and 25 tests")


if __name__ == "__main__":
    unittest.main()


class SanitiserR5(unittest.TestCase):
    def clean(self, t):
        o = b.sanitise(t); b.scan(o); return o

    def test_r5_inputs(self):
        self.assertEqual(self.clean("password: |\n  violet-horse-secret\nnext: ok"), "password: <SECRET>\nnext: ok")
        self.assertEqual(self.clean("C:\\Users\\Alice Smith\\private.txt"), "<WINPATH>")
        self.assertEqual(self.clean("alice!tag@example.org"), "<EMAIL>")
        o = self.clean('Authorization: Digest username="alice", response="violet-secret"')
        self.assertEqual(o, "Authorization: <SECRET>")

    def test_scan_rejects_r5_survivors(self):
        for bad in ["password: <SECRET>\n  leaked", "x<EMAIL>", "<WINPATH> Smith"]:
            with self.assertRaises(SystemExit, msg=bad):
                b.scan(bad)
