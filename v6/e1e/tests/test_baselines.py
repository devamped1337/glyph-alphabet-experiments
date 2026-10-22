"""Baseline 4b (Amendment A1) and section-8 send-path selection. Synthetic fixtures only."""
import unittest

from tests import fixtures  # noqa: F401  (sets sys.path)
from tests.fixtures import V1, ROUND_TRIPS
from tests.helpers import build, recv_at
from e1e import Publisher, Receiver, Link, encode, decode_message, make_entry
from e1e import codec as codec_mod
from e1e.baselines import (ZSTD_MAGIC, HEADLINE_FRAME, INTEGRITY_FRAME, ZstdCodec, baseline3, baseline4,
                           baseline4b, repo_dict_bytes, select_b6, sync_cost, unwrap, zstd_versions)
from e1e.codec import raw_wire


class FakeCodec:
    """Deterministic stand-in: compressed length chosen per input, so ties and flips are exact."""

    def __init__(self, sizes):
        self.sizes, self._store = sizes, {}

    def compress(self, data):
        n = self.sizes(data)
        out = ZSTD_MAGIC + bytes([len(self._store) % 256]) * (n - 4)
        self._store[out] = data
        return out

    def decompress(self, frame):
        return self._store[frame]


class Baseline4b(unittest.TestCase):
    def setUp(self):
        self.pub, self.deltas, self.fulls = build()

    def test_versions_pinned(self):
        self.assertEqual(zstd_versions(), {"zstandard": "0.23.0", "libzstd": "1.5.6"})

    def test_dict_bytes_exact_definition(self):
        st = self.pub.state
        ents = st.entries
        want = b"\n".join(ents[k]["body"].encode("utf-8") for k in sorted(ents))
        self.assertEqual(repo_dict_bytes(st), want)
        self.assertIn("ACK: task received.\nStarting now.".encode(), want)  # current version (ack v2), not v1
        self.assertNotIn(b"starting now.", want)
        self.assertTrue(want.startswith(ents[sorted(ents)[0]]["body"].encode()))
        self.assertFalse(want.endswith(b"\n\n"))

    def test_dict_bytes_deterministic(self):
        pub2, _, fulls2 = build()
        self.assertEqual(repo_dict_bytes(pub2.state), repo_dict_bytes(self.pub.state))
        p3 = Publisher(); p3.publish(list(reversed(V1)))  # insertion order must not matter
        self.assertEqual(repo_dict_bytes(p3.state), repo_dict_bytes(recv_at(self.fulls, 0).state))
        self.assertEqual(repo_dict_bytes(recv_at(self.fulls, 2).state), repo_dict_bytes(self.pub.state))
        self.assertNotEqual(repo_dict_bytes(recv_at(self.fulls, 0).state), repo_dict_bytes(self.pub.state))

    def test_exact_round_trip_each_message_independent(self):
        sender, receiver = baseline4b(self.pub.state), baseline4b(recv_at(self.fulls, 2).state)
        frames = [sender.compress(m) for m in ROUND_TRIPS]
        for m, f in reversed(list(zip(ROUND_TRIPS, frames))):  # any order: no stream state
            self.assertEqual(f[:4], ZSTD_MAGIC)
            self.assertEqual(receiver.decompress(f), m)
        self.assertEqual(frames, [baseline4b(self.pub.state).compress(m) for m in ROUND_TRIPS])

    def test_same_level_and_frame_as_baseline4(self):
        msgs = [m for m in ROUND_TRIPS if m] * 40
        b4 = baseline4(msgs, 1024)
        b4b = baseline4b(self.pub.state)
        if b4 is not None:
            self.assertEqual((b4.level, b4.frame), (b4b.level, b4b.frame))
        self.assertEqual(b4b.frame, HEADLINE_FRAME)
        integ = baseline4b(self.pub.state, frame=INTEGRITY_FRAME)
        m = ROUND_TRIPS[1]
        self.assertEqual(integ.decompress(integ.compress(m)), m)
        self.assertGreater(len(integ.compress(m)), len(b4b.compress(m)))

    def test_dictionary_helps_repo_text(self):
        m = b"status: job build-7 is done after 42 steps"
        self.assertLess(len(baseline4b(self.pub.state).compress(m)), len(baseline3().compress(m)))

    def test_empty_repository_is_baseline3(self):
        st = Receiver().state
        self.assertEqual(repo_dict_bytes(st), b"")
        b = baseline4b(st)
        self.assertEqual(b.dict_bytes, b"")
        for m in ROUND_TRIPS:
            self.assertEqual(b.compress(m), baseline3().compress(m))
            self.assertEqual(b.decompress(b.compress(m)), m)
        self.assertEqual(sync_cost([len(b.dict_bytes)], 5)["total"], 0)

    def test_tiny_repository(self):
        p = Publisher(); p.publish([make_entry("a", 1, "A")])
        self.assertEqual(repo_dict_bytes(p.state), b"A")
        b = baseline4b(p.state)
        for m in ROUND_TRIPS + [b"A", b"AAAA"]:
            self.assertEqual(b.decompress(b.compress(m)), m)

    def test_wrong_dictionary_not_byte_exact(self):
        m = b"status: job build-7 is done after 42 steps"
        f = baseline4b(self.pub.state).compress(m)
        try:
            out = baseline3().decompress(f)
        except Exception:
            out = None
        self.assertNotEqual(out, m)  # headline frames: only the offline oracle catches this

    def test_sync_cost_charging(self):
        sizes = [len(repo_dict_bytes(recv_at(self.fulls, i).state)) for i in range(3)]
        c = sync_cost(sizes, participants=4, joiners=[(2, 2)])
        self.assertEqual(c["upload"], sum(sizes))
        self.assertEqual(c["download"], 4 * sum(sizes) + 2 * sizes[2])  # full rebuild per version, no deltas
        self.assertEqual(c["total"], c["upload"] + c["download"])
        self.assertEqual(c["storage_per_participant"], sizes[2])
        c2 = sync_cost(sizes, participants=[2, 3, 4])
        self.assertEqual(c2["download"], 2 * sizes[0] + 3 * sizes[1] + 4 * sizes[2])
        self.assertEqual(sync_cost([], 3)["total"], 0)
        with self.assertRaises(ValueError):
            sync_cost(sizes, participants=[1, 2])


class SendPath(unittest.TestCase):
    def setUp(self):
        self.pub, self.deltas, self.fulls = build()
        self.st = self.pub.state
        self.decl = {"version": self.st.version, "digest": self.st.digest}

    def test_baseline5_ref_larger_sends_raw(self):
        m = b"ACK: task received.\nStarting now."
        wire, info = encode(self.pub.history, self.decl, m, require_smaller=True)
        self.assertEqual((wire, info["reason"]), (raw_wire(m), "ref_not_smaller"))
        r = recv_at(self.fulls, 2)
        link = Link(self.pub.history, r)  # default policy is require_smaller=True
        out, li = link.transmit(m)
        self.assertEqual((out, li["kind"]), (m, "raw"))
        self.assertEqual(link.totals()["raw"], len(raw_wire(m)))

    def test_baseline5_tie_goes_raw(self):
        m = b"status: job a is ok after 1 steps"
        ref, info = encode(self.pub.history, self.decl, m)
        self.assertEqual(info["reason"], "ref")
        orig = codec_mod.raw_wire
        try:
            codec_mod.raw_wire = lambda msg: orig(msg) + b" " * (len(ref) - len(orig(msg)))  # equal length
            self.assertEqual(len(codec_mod.raw_wire(m)), len(ref))
            _, i2 = encode(self.pub.history, self.decl, m, require_smaller=True)
            self.assertEqual(i2["reason"], "ref_not_smaller")
            codec_mod.raw_wire = lambda msg: orig(msg) + b" " * (len(ref) + 1 - len(orig(msg)))
            _, i3 = encode(self.pub.history, self.decl, m, require_smaller=True)
            self.assertEqual(i3["reason"], "ref")
        finally:
            codec_mod.raw_wire = orig

    def test_b6_ties(self):
        raw, ref = b"{" + b"r" * 49, b"{" + b"f" * 59
        self.assertEqual(select_b6(ref, raw, FakeCodec(lambda d: 50))[1], "raw")       # all three tie
        self.assertEqual(select_b6(ref, raw, FakeCodec(lambda d: 40))[1], "zstd_raw")  # (i)=(ii) < (iii)
        self.assertEqual(select_b6(ref, raw, FakeCodec(lambda d: 40 if d == ref else 45))[1], "zstd_ref")
        self.assertEqual(select_b6(None, raw, FakeCodec(lambda d: 10))[1], "zstd_raw")
        self.assertEqual(select_b6(None, raw, FakeCodec(lambda d: 50))[1], "raw")

    def test_b6_compressed_size_flips(self):
        small_ref, big_raw = b"{" + b"f" * 29, b"{" + b"r" * 59
        # ref smaller uncompressed, but compressed raw is smaller -> zstd_raw
        self.assertEqual(select_b6(small_ref, big_raw, FakeCodec(lambda d: 25 if d == big_raw else 28))[1], "zstd_raw")
        # ref larger uncompressed, but compressed ref is smaller -> zstd_ref
        big_ref, small_raw = b"{" + b"f" * 79, b"{" + b"r" * 59
        self.assertEqual(select_b6(big_ref, small_raw, FakeCodec(lambda d: 20 if d == big_ref else 30))[1], "zstd_ref")

    def _b6_link(self, codec):
        return Link(self.pub.history, recv_at(self.fulls, 2), codec=codec)

    def test_b6_real_send_path_round_trips_and_billing(self):
        cdc = baseline4b(self.st)  # any ZstdCodec; baseline 6 uses the baseline-4 dictionary in the audit
        extra = ["\u65e5\u672c\u8a9e\U0001F600".encode() * 40, bytes(range(256)) * 3]
        for c in (cdc, baseline3()):
            link = self._b6_link(c)
            billed = 0
            for m in ROUND_TRIPS + extra:
                n0 = len(link.frames)
                out, info = link.transmit(m)
                self.assertEqual(out, m)
                self.assertIsNone(info["rejected"])
                sends = [f for f in link.frames[n0:] if f[0] == "fwd"]
                self.assertEqual(len(sends), 1)  # only the selected candidate is billed
                ref, ei = encode(self.pub.history, self.decl, m)
                exp, kind = select_b6(ref if ei["reason"] == "ref" else None, raw_wire(m), c)
                self.assertEqual(sends[0], ("fwd", kind, len(exp)))
                billed += len(exp)
            t = link.totals()
            self.assertEqual(t["all"] - t["declare"], billed)

    def test_b6_fake_codec_flip_through_link(self):
        m = b"status: job build-7 is done after 42 steps"
        ref, _ = encode(self.pub.history, self.decl, m)
        fake = FakeCodec(lambda d: 10 if d == ref else 30)
        out, info = self._b6_link(fake).transmit(m)
        self.assertEqual((out, info["kind"], info["reason"]), (m, "zstd_ref", "ref"))
        fake2 = FakeCodec(lambda d: 10 if d == raw_wire(m) else 30)
        out, info = self._b6_link(fake2).transmit(m)
        self.assertEqual((out, info["kind"], info["reason"]), (m, "zstd_raw", "ref_not_smaller"))

    def test_unicode_and_base64_envelope_overhead(self):
        uni = "\u65e5\u672c\u8a9e".encode() * 50
        self.assertGreater(len(raw_wire(uni)), len(uni))
        binm = bytes(range(128, 256)) * 2
        env = raw_wire(binm)
        self.assertIn(b'"b64"', env)
        self.assertGreaterEqual(len(env), len(binm) * 4 // 3)
        for m in (uni, binm, b"\x00\x01\x1f" * 30):
            link = self._b6_link(baseline3())
            out, info = link.transmit(m)
            self.assertEqual(out, m)
            self.assertLessEqual(link.totals()[info["kind"]], len(raw_wire(m)))

    def test_unwrap_framing(self):
        c = baseline3()
        self.assertEqual(unwrap(c.compress(b"{x}"), c), b"{x}")
        self.assertEqual(unwrap(b'{"a":1}', None), b'{"a":1}')
        from e1e import E1EError
        with self.assertRaises(E1EError):
            unwrap(b"zz", c)
        with self.assertRaises(E1EError):
            unwrap(ZSTD_MAGIC + b"\x00", None)

    def test_codec_class_raw_empty_equals_none(self):
        self.assertEqual(ZstdCodec(dict_data=b"").compress(b"hi"), ZstdCodec().compress(b"hi"))


if __name__ == "__main__":
    unittest.main()


class FrameIntegrity(unittest.TestCase):
    """GPT r1 required change: complete frame, verified checksum, no trailing bytes, bounded output."""

    def setUp(self):
        self.pub, self.deltas, self.fulls = build()
        self.m = b"status: job build-7 is done after 42 steps " * 50

    def _codecs(self):
        return [baseline3(), baseline4b(self.pub.state), baseline3(frame=INTEGRITY_FRAME),
                baseline4b(self.pub.state, frame=INTEGRITY_FRAME)]

    def assertZstdError(self, c, data, code="E_ZSTD", **kw):
        from e1e import E1EError
        with self.assertRaises(E1EError) as cm:
            c.decompress(data, **kw)
        self.assertEqual(cm.exception.code, code)

    def test_truncated_checksum_rejected(self):
        c = baseline3(frame=INTEGRITY_FRAME)
        f = c.compress(self.m)
        self.assertEqual(c.decompress(f), self.m)
        for cut in (1, 2, 3, 4):
            self.assertZstdError(c, f[:-cut])

    def test_corrupted_checksum_rejected(self):
        c = baseline3(frame=INTEGRITY_FRAME)
        f = bytearray(c.compress(self.m)); f[-1] ^= 1
        self.assertZstdError(c, bytes(f))

    def test_truncated_frame_rejected_all_settings(self):
        for c in self._codecs():
            f = c.compress(self.m)
            for cut in (1, len(f) // 2, len(f) - 4):
                self.assertZstdError(c, f[:-cut])

    def test_trailing_bytes_rejected(self):
        for c in self._codecs():
            f = c.compress(self.m)
            for tail in (b"\x00", b"garbage" * 100, f):
                self.assertZstdError(c, f + tail)
            self.assertEqual(c.decompress(f), self.m)

    def test_empty_message_and_empty_input(self):
        for c in self._codecs():
            self.assertEqual(c.decompress(c.compress(b"")), b"")
            self.assertZstdError(c, b"")

    def test_oversized_output_rejected_during_decoding(self):
        c = baseline3()
        big = b"\x00" * (4 << 20)  # compresses to a few hundred bytes
        f = c.compress(big)
        self.assertZstdError(c, f, code="E_TOO_LARGE")  # default bound 1 MiB
        self.assertZstdError(c, c.compress(self.m), code="E_TOO_LARGE", max_output=len(self.m) - 1)
        self.assertEqual(c.decompress(c.compress(self.m), max_output=len(self.m)), self.m)

    def test_reject_then_fallback_billing_through_link(self):
        class Truncating:
            """Sender codec whose frames lose their last 4 bytes in transit."""
            def __init__(self, inner):
                self.inner = inner
            def compress(self, d):
                return self.inner.compress(d)[:-4]
            def decompress(self, f):
                return self.inner.decompress(f)

        st = self.pub.state
        for inner in (baseline3(frame=INTEGRITY_FRAME), baseline3()):
            link = Link(self.pub.history, recv_at(self.fulls, 2), codec=Truncating(inner))
            out, info = link.transmit(self.m)
            self.assertEqual(out, self.m)
            self.assertEqual(info["rejected"], "E_ZSTD")
            kinds = [f[1] for f in link.frames]
            self.assertEqual(kinds, ["declare", info["kind"], "reject", "fallback"])
            t = link.totals()
            self.assertEqual(t["fallback"], len(raw_wire(self.m)))
            self.assertEqual(t["all"], t["declare"] + t[info["kind"]] + t["reject"] + t["fallback"])
            self.assertTrue(info["kind"].startswith("zstd"))
        self.assertEqual(st.fingerprint(), self.pub.state.fingerprint())
