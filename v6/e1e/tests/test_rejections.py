"""Rejection boundaries. Every rejected operation must leave holder state unchanged.
These are NOT round trips; corrupted inputs are asserted to fail."""
import json
import unittest

from tests.helpers import build, recv_at, redigest_delta, RejectMixin
from e1e import (Publisher, Receiver, E1EError, Link, make_entry, make_delta, canonical,
                 parse_canonical, decode_message, encode, sha256_hex)
from e1e.repo import RepoState, parse_full
from e1e.schema import match_template, entry_digest


def ref(state, eid, args, v=None, digest=None, snap=None):
    e = state.entries[eid]
    return canonical({"format": "E1E-MSG/1", "type": "ref", "snap": snap or state.digest, "id": eid,
                      "v": v or e["v"], "entry": digest or e["digest"], "args": args})


class Artifacts(RejectMixin, unittest.TestCase):
    def setUp(self):
        self.pub, self.deltas, self.fulls = build()

    def test_wrong_base_digest_same_version(self):
        # A forked v1 (different content, same version) receives the real v1->v2 delta.
        fork = Publisher()
        fork.publish([make_entry("other", 1, "forked content")])
        r = Receiver(); r.load_full(fork.state.full_bytes())
        self.assertEqual(r.state.version, 1)
        self.assertRejected(r, lambda: r.apply_delta(self.deltas[1]), "E_BASE_MISMATCH")

    def test_target_digest_mismatch(self):
        r = recv_at(self.fulls, 0)
        obj = json.loads(self.deltas[1]); obj["target_digest"] = "sha256:" + "0" * 64
        self.assertRejected(r, lambda: r.apply_delta(redigest_delta(obj)), "E_TARGET_MISMATCH")

    def test_truncated_and_corrupt(self):
        r = recv_at(self.fulls, 0)
        for b in (self.deltas[1][:-1], self.deltas[1][: len(self.deltas[1]) // 2], b""):
            self.assertRejected(r, lambda: r.apply_delta(b), "E_MALFORMED")
        flipped = self.deltas[1].replace(b"Starting", b"Startinh")
        self.assertRejected(r, lambda: r.apply_delta(flipped), "E_DIGEST")
        self.assertRejected(r, lambda: r.load_full(self.fulls[1].replace(b"Starting", b"Startinh")),
                            "E_DIGEST")
        self.assertRejected(r, lambda: r.load_full(self.fulls[1][:-3]), "E_MALFORMED")
        self.assertRejected(r, lambda: r.load_full(self.fulls[1] + b" "), "E_NONCANONICAL")
        pretty = json.dumps(json.loads(self.fulls[1]), indent=1).encode()
        self.assertRejected(r, lambda: r.load_full(pretty), "E_NONCANONICAL")
        self.assertRejected(r, lambda: r.load_full("é".encode() + self.fulls[1]), "E_MALFORMED")

    def test_entry_digest_tamper_resealed(self):
        r = recv_at(self.fulls, 0)
        obj = json.loads(self.deltas[1]); obj["entries"][0]["body"] = "ACK changed"
        self.assertRejected(r, lambda: r.apply_delta(redigest_delta(obj)), "E_DIGEST")

    def test_duplicate_json_keys(self):
        r = recv_at(self.fulls, 0)
        dup = self.deltas[1].replace(b'{"base_digest"', b'{"base_digest":"x","base_digest"', 1)
        self.assertRejected(r, lambda: r.apply_delta(dup), "E_DUP_KEY")

    def test_duplicate_delta_entries(self):
        r = recv_at(self.fulls, 0)
        obj = json.loads(self.deltas[1])
        obj["entries"] = [obj["entries"][0], obj["entries"][0], obj["entries"][1]]
        self.assertRejected(r, lambda: r.apply_delta(redigest_delta(obj)), "E_DUP_ENTRY")
        self.assertRaises(E1EError, self.pub.publish, [make_entry("zz", 1, "a"), make_entry("zz", 1, "a")])

    def test_illegal_version_reuse(self):
        r = recv_at(self.fulls, 1)  # holds ack v2
        alt = make_entry("ack", 2, "ACK: different content, same version")
        d = make_delta(r.state, [alt])
        self.assertRejected(r, lambda: r.apply_delta(d), "E_VERSION_REUSE")
        before = self.pub.state.fingerprint()
        alt3 = make_entry("lf", 1, "different lf v1 {k}", [("k", "int")])
        with self.assertRaises(E1EError) as cm:
            self.pub.publish([alt3])
        self.assertEqual(cm.exception.code, "E_VERSION_REUSE")
        self.assertEqual(self.pub.state.fingerprint(), before)
        # same body, changed parameter schema at same version is also reuse
        st = make_entry("status", 1, "status: job {job} is {state} after {n} steps",
                        [("job", "word"), ("state", "text"), ("n", "int")])
        self.assertNotEqual(st["digest"], self.pub.state.entries["status"]["digest"])
        self.assertRejected(r, lambda: r.apply_delta(make_delta(r.state, [st])), "E_VERSION_REUSE")

    def test_version_skip_and_regress(self):
        r = recv_at(self.fulls, 1)
        self.assertRejected(r, lambda: r.apply_delta(make_delta(r.state, [make_entry("ack", 4, "x")])), "E_VERSION")
        self.assertRejected(r, lambda: r.apply_delta(make_delta(r.state, [make_entry("new", 2, "x")])), "E_VERSION")
        self.assertRejected(r, lambda: r.load_full(self.fulls[0]), "E_STALE")
        self.assertRejected(r, lambda: r.apply_delta(self.deltas[1]), "E_BASE_MISMATCH")  # replay
        r0 = recv_at(self.fulls, 0)  # v1 holder receiving the v2->v3 delta (gap)
        self.assertRejected(r0, lambda: r0.apply_delta(self.deltas[2]), "E_STALE")

    def test_publish_transactional(self):
        before = self.pub.state.fingerprint(); hist = dict(self.pub.history)
        good = make_entry("fresh", 1, "fresh")
        bad = dict(make_entry("bad", 1, "x")); bad["digest"] = "sha256:00"
        for batch in ([good, bad], [good, make_entry("ack", 9, "x")], []):
            self.assertRaises(E1EError, self.pub.publish, batch)
            self.assertEqual(self.pub.state.fingerprint(), before)
            self.assertEqual(self.pub.history, hist)

    def test_bad_template_schemas(self):
        for body, params in [("a {x", [("x", "text")]), ("a {x}{y}", [("x", "text"), ("y", "text")]),
                             ("a {x}", []), ("a } b", []), ("a {x} {x}", [("x", "text")]),
                             ("{x}", [("x", "text")]), ("a {X}", [("X", "text")]),
                             ("a {x}", [("x", "float")])]:
            with self.assertRaises(E1EError, msg=body):
                make_entry("t", 1, body, params, kind="template")


class Messages(RejectMixin, unittest.TestCase):
    def setUp(self):
        self.pub, self.deltas, self.fulls = build()
        self.r = recv_at(self.fulls, 2)
        self.st = self.r.state

    def test_malformed_parameters(self):
        for args in ({"job": "a b", "state": "ok", "n": 1}, {"job": "a", "state": "ok", "n": "1"},
                     {"job": "a", "state": "ok"}, {"job": "a", "state": "ok", "n": 1, "x": 1},
                     {"job": "a", "state": "ok", "n": True}, {"job": "", "state": "ok", "n": 1},
                     {"job": "a", "state": "ok", "n": 10**19}):
            self.assertRejected(self.r, lambda: decode_message(self.st, ref(self.st, "status", args)), "E_PARAM")
        self.assertRejected(self.r, lambda: decode_message(self.st, ref(self.st, "ack", {"x": "y"})), "E_PARAM")
        bad = b'{"args":{"job":"a","n":1.5,"state":"b"}}'
        self.assertRejected(self.r, lambda: decode_message(self.st, bad), "E_SCHEMA")

    def test_unknown_references(self):
        for w in (canonical({"format": "E1E-MSG/1", "type": "ref", "snap": self.st.digest, "id": "nope",
                             "v": 1, "entry": "sha256:00", "args": {}}),
                  ref(self.st, "ack", {}, v=1), ref(self.st, "ack", {}, digest="sha256:" + "1" * 64)):
            self.assertRejected(self.r, lambda: decode_message(self.st, w), "E_UNKNOWN_REF")
        self.assertRejected(self.r, lambda: decode_message(self.st, ref(self.st, "ack", {}, snap="sha256:ab")),
                            "E_STALE")

    def test_ambiguous_match_not_encoded(self):
        e = self.st.entries["pair"]
        m = "pair x and y and z"
        self.assertEqual(len(match_template(e, m)), 2)
        decl = self.r.declare()
        wire, info = encode(self.pub.history, decl, m.encode())
        self.assertNotEqual(info["reason"], "ref")
        self.assertIn(("pair", "ambiguous"), info["skipped"])
        self.assertEqual(decode_message(self.st, wire), m.encode())
        self.assertEqual(len(match_template(e, "pair x and y")), 1)

    def test_nfc_nfd_not_interchangeable(self):
        nfc, nfd = self.st.entries["uni-nfc"], self.st.entries["uni-nfd"]
        self.assertEqual(match_template(nfc, "cafe\u0301 note: t"), [])
        self.assertEqual(match_template(nfd, "caf\u00e9 note: t"), [])

    def test_wire_escaping_and_invalid_unicode(self):
        w = canonical({"format": "E1E-MSG/1", "type": "raw", "text": "a"})
        self.assertRejected(self.r, lambda: decode_message(self.st, w.replace(b'"a"', b'"\\ud800"')), "E_SCHEMA")
        self.assertRejected(self.r, lambda: decode_message(self.st, w.replace(b'"a"', b'"\\u0061"')), "E_NONCANONICAL")
        self.assertRejected(self.r, lambda: decode_message(self.st, b'{"b64":"AA=","format":"E1E-MSG/1","type":"raw"}'), "E_SCHEMA")


class ReceiverState(RejectMixin, unittest.TestCase):
    def setUp(self):
        self.pub, self.deltas, self.fulls = build()

    def test_stale_copy_receiver_falls_back(self):
        stale = recv_at(self.fulls, 0)  # honest v1 declaration, ack v1 only
        link = Link(self.pub.history, stale)
        m = b"ACK: task received.\nStarting now."  # only encodable with ack v2
        out, info = link.transmit(m)
        self.assertEqual(out, m)
        self.assertEqual(info["kind"], "raw")  # sender used the declared v1 snapshot, not its own v3
        self.assertIsNone(info["rejected"])

    def test_stale_declaration_rejected_then_fallback(self):
        r = recv_at(self.fulls, 1)
        old_decl = r.declare()
        r.apply_delta(self.deltas[2])  # receiver advanced after declaring
        link = Link(self.pub.history, r)
        m = b"status: job a is ok after 1 steps"
        before = r.state.fingerprint()
        out, info = link.transmit(m, declaration=old_decl)
        self.assertEqual(out, m)
        self.assertEqual(info["rejected"], "E_STALE")
        self.assertEqual(r.state.fingerprint(), before)
        t = link.totals()
        self.assertGreater(t["reject"], 0); self.assertGreater(t["fallback"], 0)
        self.assertEqual(t["all"], t["ref"] + t["reject"] + t["fallback"])

    def test_receiver_copy_diverged_from_declaration(self):
        # Receiver lies/mis-declares v2 while holding a fork: decoder must reject, fallback delivers.
        fork = Publisher(); fork.publish([make_entry("status", 1, "forked {x}!", [("x", "word")])])
        r = Receiver(); r.load_full(fork.state.full_bytes())
        v1 = parse_full(self.fulls[0])
        decl = {"version": 1, "digest": v1.digest}  # declares the real v1, holds a fork
        out, info = Link(self.pub.history, r).transmit(b"status: job a is ok after 1 steps", decl)
        self.assertEqual(out, b"status: job a is ok after 1 steps")
        self.assertEqual(info["rejected"], "E_STALE")

    def test_unknown_declaration_sends_raw(self):
        r = Receiver()
        out, info = Link(self.pub.history, r).transmit(b"ACK", {"version": 7, "digest": "sha256:zz"})
        self.assertEqual((out, info["reason"]), (b"ACK", "unknown_declared_snapshot"))


if __name__ == "__main__":
    unittest.main()


class ReviewR1Regressions(RejectMixin, unittest.TestCase):
    """Regressions for gpt_E1e_code_r1 findings and its requested extra coverage."""

    def setUp(self):
        self.pub, self.deltas, self.fulls = build()

    def _full(self, version, entries):
        return RepoState(version, {e["id"]: e for e in entries}).full_bytes()

    def test_full_load_cannot_delete(self):
        r = recv_at(self.fulls, 0)
        self.assertRejected(r, lambda: r.load_full(self._full(2, [])), "E_DELETION_DEFERRED")

    def test_full_load_fork_and_history_conflict(self):
        r = recv_at(self.fulls, 0)
        fork = list(parse_full(self.fulls[0]).entries.values()) + [make_entry("zzz", 1, "extra")]
        self.assertRejected(r, lambda: r.load_full(self._full(1, fork)), "E_FORK")
        conflict = [make_entry("ack", 1, "ACK other")] + [e for e in parse_full(self.fulls[0]).entries.values() if e["id"] != "ack"]
        self.assertRejected(r, lambda: r.load_full(self._full(2, conflict)), "E_VERSION_REUSE")

    def test_snapshots_do_not_alias(self):
        old = self.pub.history[parse_full(self.fulls[0]).digest]
        b0, d0 = old.full_bytes(), self.pub.state.full_bytes()
        old.entries["status"]["body"] = "changed"
        self.pub.state.entries["status"]["body"] = "changed"
        self.assertEqual((old.full_bytes(), self.pub.state.full_bytes()), (b0, d0))

    def test_bool_version_rejected(self):
        r = recv_at(self.fulls, 0); st = r.state
        e = st.entry("ack")
        w = canonical({"format": "E1E-MSG/1", "type": "ref", "snap": st.digest, "id": "ack", "v": True,
                       "entry": e["digest"], "args": {}})
        self.assertRejected(r, lambda: decode_message(st, w), "E_SCHEMA")

    def test_oversized_send_records_nothing(self):
        r = recv_at(self.fulls, 2); link = Link(self.pub.history, r)
        with self.assertRaises(E1EError) as cm:
            link.transmit(b"a" * 65537)
        self.assertEqual((cm.exception.code, link.frames), ("E_TOO_LARGE", ()))

    def test_match_budget_and_candidate_limit(self):
        e = make_entry("p", 1, "x{a}y{b}y{c}z", [("a", "text"), ("b", "text"), ("c", "text")])
        self.assertIsNone(match_template(e, "x" + "y" * 400 + "q"))  # budget exhausted -> no match
        pub = Publisher()
        pub.publish([make_entry(f"c{i:02d}", 1, "hdr " + "h" * i + " {t}", [("t", "text")]) for i in range(12)])
        st = pub.state
        from e1e.codec import candidates
        cs = candidates(st, "hdr " + "h" * 11 + " body")
        self.assertEqual([c["id"] for c in cs], ["c11"])
        cs = candidates(st, "hdr ")
        self.assertEqual(cs, [])
        many = Publisher(); many.publish([make_entry(f"d{i:02d}", 1, "same {t}", [("t", "text")]) for i in range(12)])
        self.assertEqual([c["id"] for c in candidates(many.state, "same q")], [f"d{i:02d}" for i in range(8)])

    def test_candidates_do_not_alias(self):
        from e1e.codec import candidates
        st = self.pub.state; b0 = st.full_bytes()
        candidates(st, "status: job a is ok after 1 steps")[0]["body"] = "changed"
        self.assertEqual(st.full_bytes(), b0)
        self.assertEqual(parse_full(st.full_bytes()).digest, st.digest)

    def test_metadata_reassignment_blocked(self):
        st = self.pub.state; b0, d0 = st.full_bytes(), st.digest
        for name, val in (("version", 99), ("digest", "sha256:00"), ("_e", {}), ("_seen", {}), ("new", 1)):
            with self.assertRaises(AttributeError):
                setattr(st, name, val)
        with self.assertRaises(AttributeError):
            del st.version
        self.assertEqual((st.full_bytes(), st.digest), (b0, d0))
        self.assertIs(self.pub.history[d0], st)
        with self.assertRaises(AttributeError):
            self.pub.state = RepoState()
        with self.assertRaises(TypeError):
            self.pub.history["sha256:00"] = st
        r = recv_at(self.fulls, 2)
        with self.assertRaises(AttributeError):
            r.state = RepoState()
        link = Link(self.pub.history, r); link.transmit(b"ACK")
        with self.assertRaises(AttributeError):
            link.frames.append(("fwd", "ref", 1))
        self.assertEqual(len(link.frames), 1)
