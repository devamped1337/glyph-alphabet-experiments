"""E1F-MSG/1 compact frames: normative section 3.5 fixtures, section 3.3 races, framing, limits, fuzz.
Synthetic made-up data only."""
import random
import unittest

from tests import fixtures  # noqa: F401  (sets sys.path)
from e1e import E1EError, Publisher, make_entry
from e1e import compact as C
from e1e.canon import canonical
from e1e.codec import MAX_MESSAGE_BYTES, raw_wire, decode_message

H = bytes.fromhex


def s1_entries():
    # ordinal 0 = "OK", ordinal 5 = "done."; 6 entries, no ordinal 127
    ents = [make_entry("e00", 1, "OK"), make_entry("e01", 1, "filler one"), make_entry("e02", 1, "filler two"),
            make_entry("e03", 1, "filler three"), make_entry("e04", 1, "filler four"),
            make_entry("e05", 1, "done.")]
    return ents


def build_s1_s2():
    pub = Publisher()
    pub.publish(s1_entries())
    s1 = pub.state
    pub.publish([make_entry("a00", 1, "NO")])  # sorts first: epoch-2 ordinal 0 = "NO"; S1 content is a subset
    return pub, s1, pub.state


class FixtureBase(unittest.TestCase):
    def setUp(self):
        self.pub, self.s1, self.s2 = build_s1_s2()
        self.rx = C.CompactReceiver()
        self.rx.load_full(self.s1.full_bytes())
        self.rx.load_full(self.s2.full_bytes())  # retains S1 (previous) and S2 (current)

    def dec(self, hexs, rx=None):
        return (rx or self.rx).decode(H(hexs.replace(" ", "")))

    def err(self, hexs, code, rx=None):
        with self.assertRaises(E1EError) as cm:
            self.dec(hexs, rx)
        self.assertEqual(cm.exception.code, code, cm.exception)


class TestNormativeFixtures(FixtureBase):
    def test_valid_bodies(self):
        self.assertEqual(self.dec("01 01 02 03 61 62 63"), b"abc")
        self.assertEqual(self.dec("01 01 01 00"), b"OK")
        self.assertEqual(self.dec("01 01 02 02 68 69 01 05"), b"hidone.")

    def test_epoch_retained_and_not_retained(self):
        self.assertEqual(self.dec("01 02 01 00"), b"NO")  # S2
        self.assertEqual(self.dec("01 01 01 00"), b"OK")  # S1 still retained
        self.err("01 03 01 00", "E_STALE")  # epoch 3 never held

    def test_malformed(self):
        self.err("01", "E_TRUNCATED")
        self.err("01 01", "E_SCHEMA")
        self.err("01 01 02 05 61", "E_TRUNCATED")
        self.err("01 01 01 FF FF FF FF FF 01", "E_RANGE")
        self.err("01 01 01 80 00", "E_NONCANONICAL")
        self.err("01 01 03 00", "E_SCHEMA")
        self.err("00", "E_SCHEMA")
        self.err("01 01 01 7F", "E_UNKNOWN_REF")

    def test_more_malformed(self):
        self.err("01 01 02 00", "E_SCHEMA")  # LIT of length 0
        self.err("01 01 02 02 ff fe", "E_SCHEMA")  # LIT not UTF-8
        self.err("01 01 02", "E_TRUNCATED")  # LIT length missing
        self.err("01 01 01", "E_TRUNCATED")  # REF ordinal missing
        self.err("01 80", "E_TRUNCATED")  # epoch varint cut off
        self.err("01 80 00", "E_NONCANONICAL")  # epoch non-canonical
        self.err("01 FF FF FF FF 1F", "E_RANGE")  # epoch > 2^32-1
        self.err("01 00 01 00", "E_STALE")  # epoch 0
        self.err("", "E_SCHEMA")
        self.err("ff", "E_SCHEMA")
        self.err("01 01 01 FF FF FF FF 10", "E_RANGE")  # ordinal 2^32
        self.err("01 01 01 80 80 80 80 00", "E_NONCANONICAL")

    def test_stale_precedes_later_segment_errors(self):
        self.err("01 09 01 7F", "E_STALE")  # epoch checked before ordinal lookup
        self.err("01 09", "E_STALE")  # stale before 'no segments'
        self.err("01 01 01 7F 03", "E_UNKNOWN_REF")  # ordinal before later bad opcode

    def test_trailing_segment_bytes_are_segments(self):
        self.assertEqual(self.dec("01 01 01 00 01 00 02 01 21"), b"OKOK!")
        self.err("01 01 01 00 ff", "E_SCHEMA")  # bytes that do not parse are an error
        self.err("01 01 01 00 02", "E_TRUNCATED")


class TestLengthPrefix(FixtureBase):
    def test_prefix_boundary_127_128(self):
        for n_payload, pre in ((127, "7f"), (128, "8001")):
            lit = n_payload - 4  # 01, epoch, 02, 1-byte n, data
            frame_payload = bytes([1, 1, 2, lit]) + b"x" * lit
            self.assertEqual(len(frame_payload), n_payload)
            fr = C.frame(frame_payload)
            self.assertEqual(fr[:len(pre) // 2].hex(), pre)
            got, pos = C.read_frame(fr)
            self.assertEqual((got, pos), (frame_payload, len(fr)))
            self.assertEqual(self.rx.decode(got), b"x" * lit)

    def test_varint_widths(self):
        for v, enc in ((0, "00"), (1, "01"), (127, "7f"), (128, "8001"), (16383, "ff7f"), (16384, "808001"),
                       (2**32 - 1, "ffffffff0f")):
            self.assertEqual(C.encode_varint(v).hex(), enc)
            self.assertEqual(C.read_varint(H(enc), 0), (v, len(enc) // 2))
        with self.assertRaises(E1EError):
            C.encode_varint(2**32)

    def test_prefix_errors(self):
        for bad, code in (("8000", "E_NONCANONICAL"), ("ffffffffff01", "E_RANGE"), ("ffffffff1f", "E_RANGE"),
                          ("80", "E_TRUNCATED"), ("", "E_TRUNCATED")):
            with self.assertRaises(E1EError) as cm:
                C.read_frame(H(bad))
            self.assertEqual(cm.exception.code, code, bad)

    def test_declared_length_checked_before_allocation(self):
        # a 4 GiB declared length with 3 bytes behind it is rejected from the byte count alone
        with self.assertRaises(E1EError) as cm:
            C.read_frame(H("ffffffff0f") + b"abc")
        self.assertEqual(cm.exception.code, "E_TRUNCATED")
        for hexs in ("01 01 02 ffffff7f 61", "01 01 02 80808080 08 61"):
            self.err(hexs, "E_TRUNCATED")

    def test_two_frames_back_to_back(self):
        a, b = H("01010100"), H("0101020161")
        buf = C.frame(a) + C.frame(b)
        p1, pos = C.read_frame(buf)
        p2, pos = C.read_frame(buf, pos)
        self.assertEqual((p1, p2, pos), (a, b, len(buf)))


class TestZigzagAndArgs(unittest.TestCase):
    def setUp(self):
        pub = Publisher()
        pub.publish([make_entry("t1", 1, "n={n} w={w}.", [("n", "int"), ("w", "word")]),
                     make_entry("t2", 1, "[{t}]", [("t", "text")])])
        self.st = pub.state
        self.rx = C.CompactReceiver()
        self.rx.load_full(self.st.full_bytes())

    def test_zigzag_values(self):
        for n, z in ((0, 0), (-1, 1), (1, 2), (-2, 3), (10**18 - 1, 2 * (10**18 - 1)), (-(10**18 - 1), 2 * (10**18 - 1) - 1)):
            self.assertEqual(C.zigzag(n), z)
            self.assertEqual(C.unzigzag(z), n)
        for bad in (10**18, -10**18):
            with self.assertRaises(E1EError) as cm:
                C.zigzag(bad)
            self.assertEqual(cm.exception.code, "E_PARAM")

    def ref(self, ordn, *args):
        return bytes([1, 1, 1, ordn]) + b"".join(args)

    def test_args_roundtrip(self):
        fr = self.ref(0, C.encode_zigzag(-42), C.encode_varint(3), b"a-b")
        self.assertEqual(self.rx.decode(fr), b"n=-42 w=a-b.")
        body = "x\n{y}\u00e9".encode("utf-8")
        fr = self.ref(1, C.encode_varint(len(body)), body)
        self.assertEqual(self.rx.decode(fr), b"[" + body + b"]")

    def test_arg_errors(self):
        def err(fr, code):
            with self.assertRaises(E1EError) as cm:
                self.rx.decode(fr)
            self.assertEqual(cm.exception.code, code, fr.hex())
        err(self.ref(0, C.encode_varint(2 * 10**18, 10, C.MAX_U64)), "E_PARAM")  # zigzag out of int domain
        err(self.ref(0, b"\xff" * 9 + b"\x7f"), "E_RANGE")  # 10-byte varint > 2^64-1
        err(self.ref(0, b"\xff" * 10), "E_RANGE")  # width
        err(self.ref(0, b"\x80\x00"), "E_NONCANONICAL")
        err(self.ref(0, C.encode_varint(0), C.encode_varint(0)), "E_PARAM")  # empty word
        err(self.ref(0, C.encode_varint(0), C.encode_varint(3), b"a b"), "E_PARAM")  # space is not a word char
        err(self.ref(0, C.encode_varint(0), C.encode_varint(2), "\u00e9".encode()), "E_PARAM")  # non-ASCII word
        err(self.ref(1, C.encode_varint(0)), "E_PARAM")  # empty text
        err(self.ref(1, C.encode_varint(2), b"\xff\xfe"), "E_PARAM")  # text not UTF-8
        err(self.ref(1, C.encode_varint(5), b"ab"), "E_TRUNCATED")  # text length over the frame
        err(self.ref(0, C.encode_varint(0)), "E_TRUNCATED")  # second arg missing


def ent_set(*bodies, tpl=()):
    ents = [make_entry(f"e{i:03d}", 1, b) for i, b in enumerate(bodies)]
    for j, (body, params) in enumerate(tpl):
        ents.append(make_entry(f"t{j:03d}", 1, body, params))
    return ents


def setup_pub(ents):
    pub = Publisher()
    pub.publish(ents)
    st = pub.state
    return st, {st.digest: st}, {"version": st.version, "digest": st.digest}


class TestEncoder(unittest.TestCase):
    def enc(self, ents, msg):
        st, known, decl = setup_pub(ents)
        payload, info = C.encode(known, decl, msg)
        rx = C.CompactReceiver()
        rx.load_full(st.full_bytes())
        self.assertEqual(rx.decode(payload), msg)  # every output decodes exactly
        return payload, info, st

    def test_all_literal_message_is_compact_and_smaller_than_raw_envelope(self):
        p, info, _ = self.enc(ent_set("zzzz unused"), b"hello world")
        self.assertEqual(p, bytes([1, 1, 2, 11]) + b"hello world")
        self.assertEqual(info["kind"], "compact")
        self.assertLess(len(p), len(raw_wire(b"hello world")))

    def test_ref_in_the_middle(self):
        body = "the long shared sentence."
        p, info, _ = self.enc(ent_set(body), ("pre " + body + " post").encode())
        self.assertEqual(p, bytes([1, 1, 2, 4]) + b"pre " + bytes([1, 0]) + bytes([2, 5]) + b" post")
        self.assertEqual((info["refs"], info["covered_bytes"], info["ref_bytes"], info["lit_segments"]), (1, len(body), 2, 2))

    def test_saved_must_be_positive(self):
        # REF costs 2 bytes: an entry of 2 bytes saves 0 and is never used; 3 bytes saves 1
        p, info, _ = self.enc(ent_set("ab"), b"xxabxx")
        self.assertEqual(info["refs"], 0)
        p, info, _ = self.enc(ent_set("abc"), b"xxabcxx")
        self.assertEqual(info["refs"], 1)

    def test_ordinal_two_byte_ref_cost(self):
        ents = [make_entry(f"e{i:03d}", 1, f"filler {i:03d}") for i in range(130)] + [make_entry("e130", 1, "abc")]
        st, known, decl = setup_pub(ents)
        p, info = C.encode(known, decl, b"..abc..")
        self.assertEqual(info["refs"], 0)  # REF = 01 + 2-byte ordinal 3 bytes, covers 3: saved 0
        p, info = C.encode(known, decl, b"..abcabc..")
        self.assertEqual(info["refs"], 0)  # still saved 0 each

    def test_greedy_earliest_start_then_saved(self):
        # earliest start wins even if a later overlapping candidate would save more
        ents = ent_set("abcdefgh", "defghijklmnop")
        p, info, _ = self.enc(ents, b"abcdefghijklmnop")
        st, known, decl = setup_pub(ents)
        segs = C.plan_segments("abcdefghijklmnop", C.find_candidates(st, "abcdefghijklmnop")[0])
        self.assertEqual(segs, [("ref", bytes([1, 0]), 8), ("lit", b"ijklmnop")])

    def test_same_start_prefers_saved_then_span_then_ordinal(self):
        st, known, decl = setup_pub([make_entry("e000", 1, "abcdefg"), make_entry("e001", 1, "abcdefghij"),
                                     make_entry("e002", 1, "abcdefghij")])
        cands, _ = C.find_candidates(st, "abcdefghij!")
        self.assertEqual([(c[0], c[1], c[2]) for c in cands], [(0, 7, 0), (0, 10, 1), (0, 10, 2)])
        segs = C.plan_segments("abcdefghij!", cands)
        self.assertEqual(segs[0], ("ref", bytes([1, 1]), 10))  # more saved; ties between 1 and 2 -> lower ordinal

    def test_enumeration_order_and_cap(self):
        ents = ent_set("aaaa", "aaaaa")
        st, _, _ = setup_pub(ents)
        cands, stats = C.find_candidates(st, "aaaaaa")
        self.assertEqual([(c[0], c[1], c[2]) for c in cands],
                         [(0, 4, 0), (0, 5, 1), (1, 5, 0), (1, 6, 1), (2, 6, 0)])
        cands, stats = C.find_candidates(st, "aaaaaa", cap=3)
        self.assertEqual(len(cands), 3)
        self.assertTrue(stats["cap_hit"])
        self.assertEqual(stats["entries_pending"], 2)  # both entries still had an unexamined start

    def test_default_cap_is_4096(self):
        self.assertEqual(C.CANDIDATE_CAP, 4096)
        st, _, _ = setup_pub(ent_set("aaaa"))
        cands, stats = C.find_candidates(st, "a" * 5000)
        self.assertEqual(len(cands), 4096)
        self.assertTrue(stats["cap_hit"])
        self.assertEqual(stats["entries_pending"], 1)

    def test_template_segment_and_end_choice(self):
        tpl = [("build {n} ok.", [("n", "int")])]
        st, known, decl = setup_pub(ent_set("zz long unused entry", tpl=tpl))
        msg = b"x build 12 ok. and build -7 ok."
        p, info = C.encode(known, decl, msg)
        self.assertEqual(info["refs"], 2)
        rx = C.CompactReceiver()
        rx.load_full(st.full_bytes())
        self.assertEqual(rx.decode(p), msg)

    def test_template_ambiguous_is_not_a_candidate(self):
        st, known, decl = setup_pub(ent_set("zz long unused entry", tpl=[("{a}.{b}!", [("a", "word"), ("b", "word")])]))
        cands, _ = C.find_candidates(st, "q x.y.z!")
        self.assertNotIn(2, [c[0] for c in cands])  # "x.y.z!" has two parses: never a candidate

    def test_end_tries_cap_64(self):
        tpl = [("k{n}.", [("n", "int")])]
        st, _, _ = setup_pub(ent_set("zz long unused entry", tpl=tpl))
        cands, _ = C.find_candidates(st, "k1." + "." * 62)  # 63 dots: the right end is try 63 of 64
        self.assertEqual([(c[0], c[1]) for c in cands], [(0, 3)])
        cands, _ = C.find_candidates(st, "k1." + "." * 64)  # right end would be try 65
        self.assertEqual(cands, [])

    def test_text_template_whole_message_only(self):
        tpl = [("Handoff to {a}:\n{note}\n-- end", [("a", "word"), ("note", "text")])]
        st, known, decl = setup_pub(ent_set("zz long unused entry", tpl=tpl))
        whole = b"Handoff to bob:\nplease {check}\nthis\n-- end"
        cands, _ = C.find_candidates(st, whole.decode())
        self.assertEqual([(c[0], c[1]) for c in cands], [(0, len(whole))])
        inside = b"prefix " + whole
        self.assertEqual(C.find_candidates(st, inside.decode())[0], [])  # not segmented
        p, info = C.encode(known, decl, whole)
        self.assertEqual(info["refs"], 1)

    def test_template_ending_in_param_is_whole_message_only(self):
        st, known, decl = setup_pub(ent_set("zz long unused entry", tpl=[("count: {n}", [("n", "int")])]))
        self.assertEqual([(c[0], c[1]) for c in C.find_candidates(st, "count: 41")[0]], [(0, 9)])
        self.assertEqual(C.find_candidates(st, "see count: 41")[0], [])

    def test_non_ascii_offsets(self):
        body = "caf\u00e9 \u65e5\u672c shared line"
        msg = ("\u00e9\u00e9 " + body + " \U0001F600 end").encode("utf-8")
        p, info, _ = self.enc(ent_set(body), msg)
        self.assertEqual(info["refs"], 1)
        self.assertEqual(info["covered_bytes"], len(body.encode("utf-8")))

    def test_raw_cases(self):
        st, known, decl = setup_pub(ent_set("abc"))
        for msg, reason in ((b"", "empty_message"), (b"\xff\xfe\x00", "not_utf8")):
            p, info = C.encode(known, decl, msg)
            self.assertEqual((p, info["reason"]), (raw_wire(msg), reason))
        p, info = C.encode(known, {"version": 9, "digest": "sha256:x"}, b"abc")
        self.assertEqual(info["reason"], "unknown_declared_snapshot")
        with self.assertRaises(E1EError) as cm:
            C.encode(known, decl, b"x" * (MAX_MESSAGE_BYTES + 1))
        self.assertEqual(cm.exception.code, "E_TOO_LARGE")

    def test_send_rule_ties_go_to_raw(self):
        self.assertEqual(C.send_rule(b"12345", b"123456"), (b"12345", "compact"))
        self.assertEqual(C.send_rule(b"123456", b"123456"), (b"123456", "raw"))
        self.assertEqual(C.send_rule(b"1234567", b"123456"), (b"123456", "raw"))

    def test_frame_over_limit_falls_back_to_raw(self):
        st, known, decl = setup_pub(ent_set("abc"))
        msg = b"a" * MAX_MESSAGE_BYTES  # compact would be 65540 bytes > 65536
        p, info = C.encode(known, decl, msg)
        self.assertEqual((p, info["reason"], info["verify_error"]), (raw_wire(msg), "verify_failed", "E_TOO_LARGE"))

    def test_more_than_256_segments_falls_back_to_raw(self):
        st, known, decl = setup_pub(ent_set("abcd"))
        msg = b"abcd-" * 300
        p, info = C.encode(known, decl, msg)
        self.assertEqual((p, info["reason"], info["verify_error"]), (raw_wire(msg), "verify_failed", "E_TOO_LARGE"))

    def test_verification_discards_a_wrong_frame(self):
        st, known, decl = setup_pub(ent_set("abcdef"))
        orig = C.plan_segments
        try:
            C.plan_segments = lambda text, cands: [("lit", b"not the message")]
            p, info = C.encode(known, decl, b"abcdef")
        finally:
            C.plan_segments = orig
        self.assertEqual((p, info["reason"]), (raw_wire(b"abcdef"), "verify_failed"))


class TestCandidateGenerationA1(unittest.TestCase):
    """Amendment A1 (blocker 3): incremental, bounded candidate generation; outputs equal the pre-A1 enumeration."""

    def test_regression_against_pre_a1_enumeration(self):
        from tests import old_compact_ref as OLD
        rng = random.Random(404)
        words = ["alpha", "beta", "x1", "job-7", "Q.z", "9", "-3", "done."]
        for trial in range(120):
            ents = []
            for i in range(rng.randint(1, 8)):
                kind = rng.randrange(4)
                lit = "".join(rng.choice("ab .:-") for _ in range(rng.randint(1, 6)))
                if kind == 0:
                    ents.append(make_entry(f"e{i:03d}", 1, lit * rng.randint(1, 3) + "!"))
                elif kind == 1:
                    ents.append(make_entry(f"e{i:03d}", 1, "k" + lit + "{n}" + lit + ".", [("n", "int")]))
                elif kind == 2:
                    ents.append(make_entry(f"e{i:03d}", 1, "{w}" + lit + "{n}" + lit + "z", [("w", "word"), ("n", "int")]))
                else:
                    ents.append(make_entry(f"e{i:03d}", 1, lit + "{t}" + lit + "!", [("t", "text")]))
            pub = Publisher()
            pub.publish(ents)
            st = pub.state
            text = "".join(rng.choice(words + ["k", "a", "b", " ", ".", ":", "!", "z", "\n"]) for _ in range(rng.randint(5, 60)))
            new, ns = C.find_candidates(st, text)
            old, os_ = OLD.find_candidates(st, text)
            self.assertEqual(new, old, (trial, text, [e["body"] for e in ents]))
            self.assertFalse(ns["cap_hit"])
            cap = rng.randint(1, 6)
            n2, s2 = C.find_candidates(st, text, cap=cap)
            o2, _ = OLD.find_candidates(st, text, cap=cap)
            self.assertEqual(n2, o2)

    def test_stress_4096_literal_entries_vs_65536_char_message(self):
        import time
        ents = [make_entry(f"e{i:04d}", 1, "aaaa") for i in range(4096)]  # 4096 entries, each matching everywhere
        pub = Publisher()
        pub.publish(ents)
        st = pub.state
        text = "a" * 65536
        t = time.time()
        cands, stats = C.find_candidates(st, text)
        dt = time.time() - t
        self.assertEqual(len(cands), 4096)
        self.assertTrue(stats["cap_hit"])
        self.assertLess(dt, 5.0, dt)  # the pre-A1 code materialised ~2.7e8 pairs here
        self.assertEqual([c[:3] for c in cands[:3]], [(0, 4, 0), (0, 4, 1), (0, 4, 2)])
        known = {st.digest: st}
        p, info = C.encode(known, {"version": 1, "digest": st.digest}, text.encode())
        self.assertIn(info["reason"], ("compact", "compact_not_smaller", "verify_failed"))

    def test_template_work_is_bounded_by_matcher_call_and_character_budgets(self):
        import time
        pub = Publisher()
        pub.publish([make_entry("t0", 1, "{a}.{b}.{c}.{d}!", [("a", "word"), ("b", "word"), ("c", "word"), ("d", "word")])])
        st = pub.state
        text = "a." * 2000 + "x!"   # ~4,000-char spans; each E1E matcher call exhausts its 20,000-step budget
        t = time.time()
        cands, stats = C.find_candidates(st, text, match_cap=5)
        self.assertEqual(stats["matcher_calls"], 5)
        self.assertTrue(stats["match_cap_hit"])
        cands, stats = C.find_candidates(st, text, work_cap=9000)
        self.assertEqual(stats["matcher_calls"], 2)  # 4,002- and 4,000-char spans fit in 9,000 characters; the third does not
        self.assertTrue(stats["match_cap_hit"])
        self.assertLess(time.time() - t, 30)  # no regex backtracking anywhere in candidate generation

    def test_whole_message_match_suppressed_by_the_character_budget_is_reported(self):
        pub = Publisher()
        pub.publish([make_entry("t0", 1, "x{w}", [("w", "word")])])
        st = pub.state
        cands, stats = C.find_candidates(st, "xabcd", work_cap=1)
        self.assertEqual(cands, [])
        self.assertEqual(stats["matcher_calls"], 0)
        self.assertEqual(stats["matcher_span_chars"], 0)
        self.assertTrue(stats["match_cap_hit"])
        cands, stats = C.find_candidates(st, "xabcd")          # with the default budget the match is found
        self.assertEqual([(c[0], c[1]) for c in cands], [(0, 5)])
        self.assertFalse(stats["match_cap_hit"])
        self.assertEqual((stats["matcher_calls"], stats["matcher_span_chars"]), (1, 5))
        cands, stats = C.find_candidates(st, "xabcd", match_cap=0)  # call cap exhausted before the only pair
        self.assertTrue(stats["match_cap_hit"])

    def test_matcher_span_characters_are_emitted(self):
        pub = Publisher()
        pub.publish([make_entry("t0", 1, "{a}.{b}!", [("a", "word"), ("b", "word")])])
        st = pub.state
        cands, stats = C.find_candidates(st, "ab.cd!")
        self.assertEqual((stats["matcher_calls"], stats["matcher_span_chars"]), (1, 6))  # one try, span "ab.cd!" = 6 chars

    def test_exhausted_template_work_does_not_suppress_literals(self):
        pub = Publisher()
        pub.publish([make_entry("t0", 1, "{n}x!", [("n", "int")]), make_entry("l0", 1, "zz")])
        st = pub.state
        text = "1" * 200 + "x!" + "zz"
        cands, stats = C.find_candidates(st, text, eval_cap=1)
        self.assertTrue(stats["eval_cap_hit"])
        self.assertIn((len(text) - 2, len(text), 0), [(c[0], c[1], c[2]) for c in cands])

    def test_eval_cap_stops_template_enumeration(self):
        pub = Publisher()
        pub.publish([make_entry("t0", 1, "{n}x!", [("n", "int")])])
        st = pub.state
        cands, stats = C.find_candidates(st, "1" * 500 + "x!", eval_cap=10)
        self.assertTrue(stats["eval_cap_hit"])
        self.assertEqual(stats["template_evaluations"], 10)

    def test_all_lit_saving_is_not_universal_a_65536_byte_unmatched_message_goes_raw(self):
        """Amendment A1 note 4: the all-LIT frame is 4+ bytes longer than the message, so at 65,536 bytes it is an
        oversized compact frame (E_TOO_LARGE in the real decoder) and the send rule falls back to the raw envelope."""
        pub = Publisher()
        pub.publish([make_entry("e1", 1, "nothing like the message " * 3)])
        st = pub.state
        known = {st.digest: st}
        msg = b"q" * 65536
        p, info = C.encode(known, {"version": 1, "digest": st.digest}, msg)
        self.assertEqual((info["kind"], info["reason"], info.get("verify_error")), ("raw", "verify_failed", "E_TOO_LARGE"))
        self.assertEqual(p, raw_wire(msg))
        small = b"q" * 65000
        p, info = C.encode(known, {"version": 1, "digest": st.digest}, small)
        self.assertEqual((info["kind"], info["reason"]), ("compact", "compact"))

    def test_default_caps(self):
        self.assertEqual(C.EVAL_CAP, 65536)
        self.assertEqual(C.MATCH_CALL_CAP, 4096)
        self.assertEqual(C.MATCH_WORK_CAP, 1 << 20)


class TestLimits(FixtureBase):
    def test_compact_frame_limit(self):
        n = 65536 - 4 - 2
        ok = bytes([1, 1, 2]) + C.encode_varint(n) + b"x" * n
        self.assertLessEqual(len(ok), 65536)
        self.assertEqual(self.rx.decode(ok), b"x" * n)
        bad = bytes([1, 1, 2]) + C.encode_varint(n + 3) + b"x" * (n + 3)
        self.assertGreater(len(bad), 65536)
        with self.assertRaises(E1EError) as cm:
            self.rx.decode(bad)
        self.assertEqual(cm.exception.code, "E_TOO_LARGE")

    def test_segment_limit(self):
        ok = bytes([1, 1]) + bytes([1, 0]) * 256
        self.assertEqual(self.rx.decode(ok), b"OK" * 256)
        with self.assertRaises(E1EError) as cm:
            self.rx.decode(ok + bytes([1, 0]))
        self.assertEqual(cm.exception.code, "E_TOO_LARGE")

    def test_reconstructed_size_checked_last(self):
        pub = Publisher()
        pub.publish([make_entry("big", 1, "x" * 16384)])
        rx = C.CompactReceiver()
        rx.load_full(pub.state.full_bytes())
        rx_ok = bytes([1, 1]) + bytes([1, 0]) * 4
        self.assertEqual(len(rx.decode(rx_ok)), 65536)
        over = bytes([1, 1]) + bytes([1, 0]) * 5
        for tail, code in ((b"", "E_TOO_LARGE"), (bytes([1, 9]), "E_UNKNOWN_REF"), (bytes([3]), "E_SCHEMA")):
            with self.assertRaises(E1EError) as cm:
                rx.decode(over + tail)
            self.assertEqual(cm.exception.code, code)

    def test_entry_bodies_over_16384_do_not_exist(self):
        with self.assertRaises(E1EError):
            make_entry("big", 1, "x" * 16385)

    def test_more_than_8_args_cannot_exist(self):
        with self.assertRaises(E1EError):
            make_entry("many", 1, "".join("{p%d}," % i for i in range(9)), [(f"p{i}", "int") for i in range(9)])

    def test_e1e_envelope_and_zstd_discrimination(self):
        self.assertEqual(self.rx.decode(raw_wire(b"plain")), b"plain")
        self.err("28 b5 2f fd 00", "E_SCHEMA")  # zstd frame without a codec
        self.err("7b", "E_MALFORMED")  # E1E decoder behaviour is unchanged


class TestRaces(unittest.TestCase):
    """Section 3.3 injected races, through the real receiver and the link accounting."""

    def setUp(self):
        self.pub = Publisher()
        d1, f1 = self.pub.publish(s1_entries())
        self.s1 = self.pub.state
        self.d2, f2 = self.pub.publish([make_entry("a00", 1, "NO")])
        self.s2 = self.pub.state
        self.d3, f3 = self.pub.publish([make_entry("a01", 1, "MAYBE LATER ENTRY")])
        self.s3 = self.pub.state
        self.f1, self.f2, self.f3 = f1, f2, f3
        self.known = {s.digest: s for s in (self.s1, self.s2, self.s3)}
        self.rx = C.CompactReceiver()
        self.rx.load_full(f1)
        self.link = C.CompactLink(self.known, self.rx)

    def frame_for(self, st, msg):
        p, info = C.encode(self.known, {"version": st.version, "digest": st.digest}, msg)
        return p, info

    def test_old_snapshot_frame_after_new_declaration(self):
        p = bytes([1, 1, 1, 0])  # epoch 1, ordinal 0: "OK" under S1
        self.rx.apply_delta(self.d2)  # receiver moves on to v2 before the frame arrives
        self.assertEqual(self.rx.state.version, 2)
        out, rej = self.link.deliver(p, b"OK")
        self.assertEqual((out, rej), (b"OK", None))  # decoded against the retained S1, never against S2's ordinal 0 "NO"
        self.assertNotIn("reject", self.link.totals())

    def test_epoch_two_versions_old_is_stale_and_resent_raw(self):
        self.rx.apply_delta(self.d2)
        self.rx.apply_delta(self.d3)  # retains S3 and S2 only
        p = bytes([1, 1, 1, 0])
        with self.assertRaises(E1EError) as cm:
            self.rx.decode(p)
        self.assertEqual(cm.exception.code, "E_STALE")
        out, rej = self.link.deliver(p, b"OK")
        self.assertEqual((out, rej), (b"OK", "E_STALE"))
        t = self.link.totals()
        self.assertEqual(t["reject"], len(reject_for(p)))
        self.assertEqual(t["fallback"], len(raw_wire(b"OK")))
        kinds = [(d, k) for d, k, _, _ in self.link.frames]
        self.assertEqual(kinds, [("fwd", "compact"), ("back", "reject"), ("fwd", "fallback")])

    def test_epoch_never_declared(self):
        p = bytes([1, 7, 1, 0])
        out, rej = self.link.deliver(p, b"OK")
        self.assertEqual((out, rej), (b"OK", "E_STALE"))

    def test_retained_snapshots_are_current_and_previous(self):
        self.assertIsNone(self.rx.previous)
        self.rx.apply_delta(self.d2)
        self.assertEqual((self.rx.state.version, self.rx.previous.version), (2, 1))
        self.rx.apply_delta(self.d3)
        self.assertEqual((self.rx.state.version, self.rx.previous.version), (3, 2))
        self.assertIsNone(self.rx.resolve(1))
        self.assertIsNotNone(self.rx.resolve(2))

    def test_failed_update_does_not_rotate(self):
        with self.assertRaises(E1EError):
            self.rx.apply_delta(self.d3)  # ahead of the held version
        self.assertEqual(self.rx.state.version, 1)
        self.assertIsNone(self.rx.previous)

    def test_fork_same_version_other_digest(self):
        other = Publisher()
        other.publish([make_entry("zz", 1, "different content")])
        with self.assertRaises(E1EError) as cm:
            self.rx.load_full(other.state.full_bytes())
        self.assertEqual(cm.exception.code, "E_FORK")
        self.assertEqual(self.rx.state.digest, self.s1.digest)

    def test_link_transmit_charges_declare_once_prefix_and_compact(self):
        body = "a sufficiently long shared body line"
        pub = Publisher()
        pub.publish([make_entry("e0", 1, body)])
        st = pub.state
        rx = C.CompactReceiver()
        rx.load_full(st.full_bytes())
        link = C.CompactLink({st.digest: st}, rx)
        out, info = link.transmit(("x " + body).encode())
        out2, info2 = link.transmit(b"plain text")
        self.assertEqual((info["kind"], info2["kind"]), ("compact", "compact"))
        t = link.totals()
        self.assertEqual(t["declare"], len(C.declare_wire(rx.declare())))  # declaration charged once
        self.assertEqual(t["prefix"], sum(C.prefix_len(n) for _, _, n, _ in link.frames))
        self.assertEqual(t["all"], t["declare"] + t["compact"] + t["prefix"])


def reject_for(p):
    return C.reject_wire("E_STALE", p)


class TestFuzz(unittest.TestCase):
    KNOWN = {"E_MALFORMED", "E_NONCANONICAL", "E_DUP_KEY", "E_SCHEMA", "E_TOO_LARGE", "E_STALE", "E_UNKNOWN_REF",
             "E_PARAM", "E_TRUNCATED", "E_RANGE", "E_FORK"}

    def setUp(self):
        ents = [make_entry("e000", 1, "alpha beta gamma delta"), make_entry("e001", 1, "line one\nline two\n"),
                make_entry("e002", 1, "caf\u00e9 \u65e5\u672c")]
        tpl = [make_entry("t000", 1, "job {j} state {s} n={n}.", [("j", "word"), ("s", "word"), ("n", "int")]),
               make_entry("t001", 1, "<<{t}>>", [("t", "text")])]
        pub = Publisher()
        pub.publish(ents + tpl)
        self.st = pub.state
        self.rx = C.CompactReceiver()
        self.rx.load_full(self.st.full_bytes())
        self.known = {self.st.digest: self.st}
        self.decl = {"version": 1, "digest": self.st.digest}

    def rand_message(self, rng):
        parts = []
        for _ in range(rng.randint(1, 6)):
            k = rng.randrange(6)
            if k == 0:
                parts.append("alpha beta gamma delta")
            elif k == 1:
                parts.append("line one\nline two\n")
            elif k == 2:
                parts.append("caf\u00e9 \u65e5\u672c")
            elif k == 3:
                parts.append("job %s state %s n=%d." % (rng.choice(["a", "b-1", "x.y"]), rng.choice(["ok", "bad_2"]),
                                                       rng.choice([0, -5, 12345678901234567, 7])))
            elif k == 4:
                parts.append("".join(rng.choice("ab {}\n\u00e9\u2603\U0001F600.:") for _ in range(rng.randint(1, 20))))
            else:
                parts.append("<<" + "".join(rng.choice("xy {}\n\u00e9") for _ in range(rng.randint(1, 8))) + ">>")
        return "".join(parts).encode("utf-8")

    def test_encoder_roundtrip_property(self):
        rng = random.Random(1337)
        for _ in range(400):
            msg = self.rand_message(rng)
            p, info = C.encode(self.known, self.decl, msg)
            self.assertEqual(self.rx.decode(p), msg)
            self.assertLessEqual(len(p), len(raw_wire(msg)))

    def test_link_roundtrip_framed_stream(self):
        rng = random.Random(7)
        link = C.CompactLink(self.known, self.rx)
        buf = b""
        for _ in range(60):
            msg = self.rand_message(rng)
            out, info = link.transmit(msg)
            self.assertEqual((out, info["rejected"]), (msg, None))
            buf += C.frame(C.encode(self.known, self.decl, msg)[0])
        pos, n = 0, 0
        while pos < len(buf):
            payload, pos = C.read_frame(buf, pos)
            self.rx.decode(payload)
            n += 1
        self.assertEqual(n, 60)

    def test_random_valid_frames_vs_independent_oracle(self):
        rng = random.Random(99)
        for _ in range(300):
            out, exp = bytearray([1, 1]), []
            for _ in range(rng.randint(1, 8)):
                k = rng.randrange(4)
                if k == 0:
                    t = "".join(rng.choice("pq \u00e9\U0001F600") for _ in range(rng.randint(1, 12))).encode()
                    out += bytes([2]) + C.encode_varint(len(t)) + t
                    exp.append(t)
                elif k == 1:
                    o = rng.randrange(3)
                    out += bytes([1]) + C.encode_varint(o)
                    exp.append(self.st._e[sorted(self.st._e)[o]]["body"].encode())
                elif k == 2:
                    n = rng.choice([0, -1, 5, -10**17, 10**18 - 1])
                    w = rng.choice(["a", "b.c-d_9"]).encode()
                    out += bytes([1]) + C.encode_varint(3) + C.encode_varint(len(w)) + w + C.encode_varint(len(w)) + w + C.encode_zigzag(n)
                    exp.append(b"job %s state %s n=%d." % (w, w, n))
                else:
                    t = "".join(rng.choice("t{} \n") for _ in range(rng.randint(1, 9))).encode()
                    out += bytes([1]) + C.encode_varint(4) + C.encode_varint(len(t)) + t
                    exp.append(b"<<" + t + b">>")
            self.assertEqual(self.rx.decode(bytes(out)), b"".join(exp))

    def test_mutations_only_raise_defined_errors(self):
        rng = random.Random(2026)
        seeds = []
        for _ in range(60):
            seeds.append(C.encode(self.known, self.decl, self.rand_message(rng))[0])
        decoded = errors = 0
        for base in seeds:
            for _ in range(60):
                b = bytearray(base)
                for _ in range(rng.randint(1, 4)):
                    op = rng.randrange(4)
                    if op == 0 and b:
                        b[rng.randrange(len(b))] = rng.randrange(256)
                    elif op == 1 and b:
                        del b[rng.randrange(len(b))]
                    elif op == 2:
                        b.insert(rng.randrange(len(b) + 1), rng.randrange(256))
                    elif b:
                        del b[rng.randrange(len(b)):]
                try:
                    self.rx.decode(bytes(b))
                    decoded += 1
                except E1EError as e:
                    errors += 1
                    self.assertIn(e.code, self.KNOWN)
        self.assertGreater(errors, 100)

    def test_random_bytes_only_raise_defined_errors(self):
        rng = random.Random(5)
        for _ in range(3000):
            n = rng.randrange(0, 40)
            b = bytes([rng.choice([1, 1, 1, 2, 0x7B, 0x28])]) + bytes(rng.randrange(256) for _ in range(n))
            try:
                self.rx.decode(b)
            except E1EError as e:
                self.assertIn(e.code, self.KNOWN)
            try:
                C.read_frame(b)
            except E1EError as e:
                self.assertIn(e.code, self.KNOWN)

    def test_e1e_msg1_behaviour_unchanged(self):
        # an E1E envelope still decodes through the same receiver, and compact codes are not raised by it
        with self.assertRaises(E1EError) as cm:
            decode_message(self.st, b"\x01\x01\x01\x00")
        self.assertEqual(cm.exception.code, "E_MALFORMED")


if __name__ == "__main__":
    unittest.main()
