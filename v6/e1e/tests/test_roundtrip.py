"""Successful-path evidence: sync equivalence, stable serialization, exact round trips."""
import unittest

from tests.helpers import build, recv_at
from tests.fixtures import ROUND_TRIPS
from e1e import Receiver, Link, encode, decode_message, parse_canonical, canonical
from e1e.repo import parse_full


class RoundTrip(unittest.TestCase):
    def setUp(self):
        self.pub, self.deltas, self.fulls = build()

    def test_full_plus_deltas_equals_target_full(self):
        for start in range(3):
            r = recv_at(self.fulls, start)
            for d in self.deltas[start + 1:]:
                r.apply_delta(d)
            self.assertEqual(r.state.full_bytes(), self.fulls[2])
            self.assertEqual(r.state.digest, self.pub.state.digest)

    def test_deltas_from_empty_equal_full(self):
        r = Receiver()
        for d in self.deltas:
            r.apply_delta(d)
        self.assertEqual(r.state.full_bytes(), self.fulls[2])

    def test_serialization_stable(self):
        pub2, deltas2, fulls2 = build()
        self.assertEqual(deltas2, self.deltas)
        self.assertEqual(fulls2, self.fulls)
        for b in self.deltas + self.fulls:
            self.assertEqual(canonical(parse_canonical(b)), b)
            b.decode("ascii")
        self.assertEqual(parse_full(self.fulls[2]).full_bytes(), self.fulls[2])

    def test_joiner_full_sync_then_roundtrips(self):
        joiner = Receiver()
        joiner.load_full(self.fulls[2])
        link = Link(self.pub.history, joiner)
        refs = 0
        for m in ROUND_TRIPS:
            out, info = link.transmit(m)
            self.assertEqual(out, m)
            self.assertIsNone(info["rejected"])
            refs += info["kind"] == "ref"
        self.assertGreaterEqual(refs, 7)
        self.assertEqual(link.totals().get("reject", 0), 0)

    def test_specific_refs_are_exact(self):
        st = self.pub.state
        decl = {"version": st.version, "digest": st.digest}
        for m, eid in [(b"ACK: task received.\nStarting now.", "ack"),
                       ("cafe\u0301 note: x".encode(), "uni-nfd"),
                       ("caf\u00e9 note: x".encode(), "uni-nfc"),
                       (b"Handoff to a:\r\nb\r\n-- end", "handoff")]:
            wire, info = encode(self.pub.history, decl, m)
            self.assertEqual(info.get("id"), eid, info)
            self.assertEqual(decode_message(st, wire), m)

    def test_crlf_lf_distinct(self):
        st = self.pub.state
        decl = {"version": st.version, "digest": st.digest}
        lf = b"Handoff to a:\nb\n-- end"  # template requires CRLF: must not match
        wire, info = encode(self.pub.history, decl, lf)
        self.assertNotEqual(info["reason"], "ref")
        self.assertEqual(decode_message(st, wire), lf)


if __name__ == "__main__":
    unittest.main()


class DeclarationAccounting(unittest.TestCase):
    def test_declarations_counted_once_per_change(self):
        from e1e.codec import declare_wire
        pub, deltas, fulls = build()
        r = recv_at(fulls, 1)
        link = Link(pub.history, r)
        link.transmit(b"ACK"); link.transmit(b"ACK again")
        decls = [f for f in link.frames if f[1] == "declare"]
        self.assertEqual(len(decls), 1)
        self.assertEqual(decls[0], ("back", "declare", len(declare_wire(r.declare()))))
        r.apply_delta(deltas[2])
        link.transmit(b"ACK")
        self.assertEqual(sum(f[1] == "declare" for f in link.frames), 2)
        t = link.totals()
        self.assertEqual(t["all"], sum(n for _, _, n in link.frames))
        self.assertEqual(t["declare"], 2 * len(declare_wire(r.declare())))
