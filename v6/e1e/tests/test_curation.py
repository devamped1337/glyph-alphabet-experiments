"""Section 4 curation on MADE-UP data only (no real or private text)."""
import hashlib
import unittest

from tests import fixtures  # noqa: F401
from e1e import E1EError, make_entry
from e1e import curation as K
from e1e.canon import canonical


def h(c):
    return hashlib.sha256(("e1e-fold-1" + "\x00" + c).encode()).digest()


def msgs(spec):
    """spec: {conv_id: [text,...]} -> list of message dicts."""
    return [{"conv_id": c, "seq": i + 1, "text": t} for c, ts in spec.items() for i, t in enumerate(ts)]


def convs_of(spec, order=None):
    order = order or list(spec)
    return [(c, spec[c]) for c in order]


LINE_A = ("The reviewer found problems in module alpha; please fix the retry path first, then rerun the "
          "full suite and attach the failing output to the ticket for the maintainers.")  # 160 bytes
LINE_B = ("Second shared line: do not change the public interface of the codec package, and keep every "
          "public name exactly as it is today so that downstream callers keep working.")
OTHER = ["filler text number %d, nothing shared here at all" % i for i in range(40)]


class TestOrderSplitSchedule(unittest.TestCase):
    def test_order_by_hash_without_timestamps(self):
        ms = msgs({"b": ["x"], "a": ["y"], "c": ["z"]})
        self.assertEqual(K.order_conversations(ms), sorted("abc", key=h))

    def test_order_by_first_message_time_then_hash(self):
        ms = [{"conv_id": "a", "seq": 1, "text": "", "ts": 5}, {"conv_id": "a", "seq": 2, "text": "", "ts": 1},
              {"conv_id": "b", "seq": 1, "text": "", "ts": 3}, {"conv_id": "c", "seq": 1, "text": "", "ts": 3}]
        exp = ["a"] + sorted(["b", "c"], key=h)  # a's first message is at ts 1
        self.assertEqual(K.order_conversations(ms), exp)

    def test_missing_timestamp_means_no_timestamps(self):
        ms = [{"conv_id": "a", "seq": 1, "text": "", "ts": 9}, {"conv_id": "b", "seq": 1, "text": ""}]
        self.assertEqual(K.order_conversations(ms), sorted("ab", key=h))

    def test_split_with_timestamps_60_percent_rounded_down(self):
        ms = [{"conv_id": f"c{i}", "seq": 1, "text": "", "ts": 100 - i} for i in range(7)]
        dev, held = K.split_real(ms)
        self.assertEqual(len(dev), 4)  # floor(7*0.6)
        self.assertEqual(dev, ["c6", "c5", "c4", "c3"])
        self.assertEqual(held, ["c2", "c1", "c0"])

    def test_split_without_timestamps_uses_hash_mod_5(self):
        ms = msgs({f"conv{i}": ["x"] for i in range(40)})
        dev, held = K.split_real(ms)
        for c in dev:
            self.assertLessEqual(int.from_bytes(h(c)[:8], "big") % 5, 2)
        for c in held:
            self.assertGreaterEqual(int.from_bytes(h(c)[:8], "big") % 5, 3)
        self.assertEqual(sorted(dev + held), sorted(f"conv{i}" for i in range(40)))
        self.assertTrue(dev and held)

    def test_version_schedule(self):
        self.assertEqual([K.prefix_size(j, 30, 5) for j in range(1, 6)], [6, 12, 18, 24, 30])
        self.assertEqual([K.prefix_size(j, 7, 5) for j in range(1, 6)], [2, 3, 5, 6, 7])  # ceil(j*7/5)
        self.assertEqual(K.prefix_size(1, 9, 1), 9)
        self.assertEqual([K.version_for_rank(r, 10, 5) for r in range(10)], [1, 1, 2, 2, 3, 3, 4, 4, 5, 5])
        self.assertEqual([K.version_for_rank(r, 7, 20) for r in range(7)], [1, 3, 6, 9, 12, 15, 18])

    def test_tuning_blocks(self):
        self.assertEqual(K.tuning_blocks(98), [(0, 20), (20, 40), (40, 60), (60, 79), (79, 98)])
        self.assertEqual(K.tuning_blocks(30), [(0, 6), (6, 12), (12, 18), (18, 24), (24, 30)])
        b = K.tuning_blocks(13)
        self.assertEqual([y - x for x, y in b], [3, 3, 3, 2, 2])
        self.assertEqual(b[0][0], 0)
        self.assertEqual(b[-1][1], 13)

    def test_heldout_order_ties_by_hash(self):
        ms = [{"conv_id": "a", "seq": 1, "ts": 1}, {"conv_id": "b", "seq": 1, "ts": 1}, {"conv_id": "c", "seq": 1, "ts": 0}]
        out = K.heldout_order(ms)
        self.assertEqual(out[0]["conv_id"], "c")
        keys = [hashlib.sha256((m["conv_id"] + str(m["seq"])).encode()).digest() for m in out[1:]]
        self.assertEqual(keys, sorted(keys))


class TestProvenance(unittest.TestCase):
    def test_prov_required_everywhere(self):
        with self.assertRaises(TypeError):
            K.make_entry_strict("e00001", 1, "body")  # keyword-only, no default: omitting it raises
        for bad in (None, "evaluation", "Synthetic"):
            with self.assertRaises(E1EError):
                K.make_entry_strict("e00001", 1, "body", prov=bad)
        self.assertEqual(K.make_entry_strict("e00001", 1, "body", prov="real_dev")["prov"], "real_dev")
        with self.assertRaises(E1EError):
            K.Miner([("c", ["x"])], None)
        with self.assertRaises(E1EError):
            K.entries_from_picks([{"kind": "literal", "body": "x" * 40, "params": []}], None)

    def test_curated_entries_carry_the_miner_prov(self):
        spec = {f"c{i}": [chr(97 + i) + LINE_A + chr(65 + i)] for i in range(6)}
        m = K.Miner(convs_of(spec), "glyph_own_dev")
        picks, _ = m.curate(6, 32, 2, 10)
        ents = K.entries_from_picks(picks, "glyph_own_dev")
        self.assertTrue(ents and all(e["prov"] == "glyph_own_dev" for e in ents))


class TestSuffixAutomaton(unittest.TestCase):
    def brute(self, a, b, min_len):
        """All (start in b, len) that are common substrings, right-maximal against b, longest per end, >= min_len."""
        out = []
        for i in range(len(b)):
            best = 0
            for l in range(1, i + 2):
                if b[i - l + 1:i + 1] in a:
                    best = l
            ms_next = 0
            if i + 1 < len(b):
                for l in range(1, i + 3):
                    if b[i + 1 - l + 1:i + 2] in a:
                        ms_next = l
            if best >= min_len and (i == len(b) - 1 or ms_next <= best):
                out.append((i - best + 1, best))
        return out

    def test_matches_bruteforce(self):
        import random
        rng = random.Random(3)
        for _ in range(60):
            a = bytes(rng.choice(b"abc") for _ in range(rng.randint(1, 30)))
            b = bytes(rng.choice(b"abc") for _ in range(rng.randint(1, 30)))
            self.assertEqual(K.maximal_common(K.sam_build(a), b, 3), self.brute(a, b, 3), (a, b))

    def test_known_case(self):
        a, b = b"xxHELLO WORLDxx", b"yyHELLO WORLDyy"
        self.assertEqual(K.maximal_common(K.sam_build(a), b, 5), [(2, 11)])

    def test_trim_utf8(self):
        s = "a\u00e9\u65e5\U0001F600b".encode()
        self.assertEqual(K.trim_utf8(s), s)
        self.assertEqual(K.trim_utf8(s[2:]), s[3:])  # leading continuation byte dropped (\u00e9's 2nd byte)
        self.assertEqual(K.trim_utf8(s[:-1]), s[:-1])
        self.assertEqual(K.trim_utf8(s[:-2]), s[:-2 - 3 + 0] if False else s[:6])  # cut inside the emoji
        self.assertEqual(K.trim_utf8(b"\x80\x80"), b"")


class TestCandidates(unittest.TestCase):
    def test_line_blocks_need_k_conversations_and_include_subruns(self):
        spec = {"c1": [LINE_A + "\n" + LINE_B + "\nunique one"], "c2": ["pre\n" + LINE_A + "\n" + LINE_B],
                "c3": [LINE_B + "\nother tail"]}
        m = K.Miner(convs_of(spec), "synthetic")
        blocks, sk = m.line_blocks(m.cutoff_msgs(3), 2)
        texts = {b["text"] for b in blocks}
        self.assertEqual(texts, {LINE_A, LINE_B, LINE_A + "\n" + LINE_B})
        blocks, _ = m.line_blocks(m.cutoff_msgs(3), 3)
        self.assertEqual({b["text"] for b in blocks}, {LINE_B})  # only LINE_B is in all three conversations
        by = {b["text"]: b for b in m.line_blocks(m.cutoff_msgs(3), 2)[0]}
        self.assertEqual(len(by[LINE_B]["convs"]), 3)
        self.assertEqual(by[LINE_A + "\n" + LINE_B]["bytes"], len((LINE_A + "\n" + LINE_B).encode()))

    def test_blocks_over_16384_code_points_are_skipped_and_counted(self):
        big = "\n".join(f"line {i:04d} " + "x" * 90 for i in range(200))  # ~ 20,000 chars
        spec = {"c1": [big], "c2": [big]}
        m = K.Miner(convs_of(spec), "synthetic")
        blocks, skipped = m.line_blocks(2, 2)
        self.assertGreater(skipped, 0)
        self.assertTrue(all(len(b["text"]) <= 16384 for b in blocks))
        # the common-substring route skips the whole 20k message too
        cs, sk = m.common_substrings(2, 32)
        self.assertEqual((len(cs), sk), (0, 1))

    def test_common_substrings_pairwise_different_conversations_only(self):
        s = "shared fragment that is long enough to count as a candidate, ok"
        spec = {"c1": ["aaa|" + s + "|bbb", "zzz-" + s + "-yyy"], "c2": ["qq/" + s + "/rr"]}
        m = K.Miner(convs_of(spec), "synthetic")
        cs, _ = m.common_substrings(3, 32)
        self.assertIn(s, cs)
        spec = {"c1": ["aaa|" + s + "|bbb", "zzz-" + s + "-yyy"]}  # same conversation only: no pair
        m = K.Miner(convs_of(spec), "synthetic")
        self.assertEqual(m.common_substrings(2, 32), (set(), 0))

    def test_oversized_messages_excluded_and_counted(self):
        spec = {"c1": [LINE_A, "y" * 70000], "c2": [LINE_A]}
        m = K.Miner(convs_of(spec), "synthetic")
        self.assertEqual(len(m.msgs), 2)
        self.assertEqual(m.oversized, [(0, 70000)])
        picks, st = m.curate(2, 32, 2, 5)
        self.assertEqual((st["oversized_messages_excluded"], st["oversized_bytes_excluded"]), (1, 70000))

    def test_mixed_source_is_not_possible(self):
        # one Miner = one prov; the entries of a build all carry that prov
        spec = {"c1": [LINE_A], "c2": [LINE_A]}
        for prov in ("synthetic", "real_dev"):
            m = K.Miner(convs_of(spec), prov)
            picks, _ = m.curate(2, 32, 2, 5)
            self.assertTrue(all(e["prov"] == prov for e in K.entries_from_picks(picks, prov)))


class TestMinimumLengthAfterTrimming(unittest.TestCase):
    """Amendment A1 note 10 (choice made): L applies to the byte length AFTER trimming to code-point boundaries."""

    def test_result_shorter_than_L_after_trimming_is_discarded(self):
        X = "abcdefghijklmnopqrstuvwxyz01234"   # 31 ASCII bytes
        m = K.Miner([("c1", ["P" + X + "\u00e9!"]), ("c2", ["R" + X + "\u00e8?"])], "synthetic")
        self.assertEqual(m.pair_results(0, 1), [(1, 32)])  # the raw maximal common byte string is X + 0xC3 (32 bytes)
        out, _ = m.common_substrings(2, 32)
        self.assertEqual(out, set())                         # trimmed to 31 bytes: below L = 32
        out, _ = m.common_substrings(2, 31)
        self.assertEqual(out, {X})

    def test_orientation_is_earlier_message_automaton_later_message_walk(self):
        X = "abcdefghijklmnopqrstuvwxyz0123456"
        m = K.Miner([("c1", ["1" + X + "!"]), ("c2", ["2" + X + "?"])], "synthetic")
        self.assertEqual(m.pair_results(0, 1), [(1, len(X))])  # start offset is in the LATER message (b)


class TestObjective(unittest.TestCase):
    def test_gain_arithmetic_literal(self):
        spec = {"c1": ["a" + LINE_A + "1"], "c2": ["b" + LINE_A + "2"], "c3": ["c" + LINE_A + "3"]}
        m = K.Miner(convs_of(spec), "synthetic")
        picks, st = m.curate(3, 32, 2, 10)
        self.assertEqual(len(picks), 1)
        p = picks[0]
        self.assertEqual(p["body"], LINE_A)
        n = len(LINE_A.encode())
        rec = len(canonical(make_entry("e00000", 1, LINE_A, prov="synthetic")))
        self.assertEqual(p["entry_cost"], rec)
        self.assertEqual(p["G"], 3 * (n - (1 + 2)) - rec)  # opcode 1 + ordinal fixed at 2
        self.assertEqual((p["occurrences"], p["total_len"]), (3, 3 * n))

    def test_entry_cost_scales_with_joiners(self):
        big = LINE_A + LINE_B + LINE_A
        spec = {f"c{i}": [chr(97 + i) + big + chr(65 + i)] for i in range(12)}
        m = K.Miner(convs_of(spec), "synthetic")
        p0 = m.curate(12, 32, 2, 10, joiners=0)[0][0]
        p3 = m.curate(12, 32, 2, 10, joiners=3)[0][0]
        self.assertEqual(p3["entry_cost"], 4 * p0["entry_cost"])
        self.assertEqual(p0["G"] - p3["G"], 3 * p0["entry_cost"])
        self.assertEqual(p0["body"], p3["body"])

    def test_not_picked_when_gain_not_positive(self):
        spec = {"c1": ["a" + LINE_B[:60] + "1"], "c2": ["b" + LINE_B[:60] + "2"]}  # 2 * (60 - 3) < record bytes
        m = K.Miner(convs_of(spec), "synthetic")
        self.assertEqual(m.curate(2, 32, 2, 10)[0], [])

    def test_marginal_overlap_removes_occurrences(self):
        big = LINE_A + "\n" + LINE_B
        spec = {f"c{i}": [chr(97 + i) + "\n" + big + "\n" + chr(65 + i)] for i in range(6)}
        m = K.Miner(convs_of(spec), "synthetic")
        picks, st = m.curate(6, 32, 2, 10)
        # one block wins (the common substring may carry the shared newlines); every sub-block loses all its
        # occurrences to it through marginal overlap removal, so nothing else is picked
        self.assertEqual(len(picks), 1)
        self.assertEqual(picks[0]["body"].strip("\n"), big)

    def test_partial_overlap_recomputed_gain_changes_pick(self):
        a = "AAAA " + "a" * 250 + " AAAA"
        b = "BBBB " + "b" * 250 + " BBBB"
        spec = {f"c{i}": [chr(97 + i) + "|" + a + "\n" + b + "|" + chr(65 + i)] for i in range(4)}
        spec["d0"] = ["p~" + b + "~q"]
        spec["d1"] = ["r!" + b + "!s"]
        m = K.Miner(convs_of(spec), "synthetic")
        picks, _ = m.curate(6, 32, 2, 10)
        strip = lambda x: x.strip("|~!\n")
        self.assertEqual(strip(picks[0]["body"]), a + "\n" + b)  # 4 occurrences of the long block win first
        p_b = [p for p in picks if strip(p["body"]) == b]
        self.assertEqual(len(p_b), 1)  # b survives only through the two d* occurrences left after marginal removal
        self.assertEqual(p_b[0]["occurrences"], 2)

    def test_tie_rules_longer_total_length_then_lexicographic(self):
        # identical G and total length: lexicographically smaller body first
        x = "x" * 300
        y = "y" * 300
        spec = {"c1": ["1" + x + "2" + y + "3"], "c2": ["4" + x + "5" + y + "6"], "c3": ["7" + x + "8" + y + "9"]}
        m = K.Miner(convs_of(spec), "synthetic")
        picks, _ = m.curate(3, 32, 2, 10)
        self.assertEqual([p["body"] for p in picks], [x, y])  # equal G and length: smaller body bytes first
        # same G (record sizes differ with escaping, so build the tie directly in the greedy)
        cands = {("literal", "b" * 40, "[]"): ("literal", "b" * 40, []), ("literal", "a" * 40, "[]"): ("literal", "a" * 40, [])}
        spec = {"c1": ["a" * 40 + "\n" + "b" * 40], "c2": ["a" * 40 + "\n" + "b" * 40]}
        m = K.Miner(convs_of(spec), "synthetic")
        m._greedy.__func__  # the greedy is exercised directly with a negative-G pair: nothing is picked
        self.assertEqual(m._greedy(cands, 2, 10, 0), [])
        # longer total matched length wins over a shorter one at equal G is covered by test_gain_* arithmetic

    def test_tie_equal_gain_prefers_longer_total_matched_length(self):
        X, Y = "x" * 397, "y" * 200  # G_X = 2*(397-3) - rec(397) == G_Y = 3*(200-3) - rec(200); total length 794 vs 600
        spec = {"c1": ["a" + X + "b" + Y + "c"], "c2": ["d" + X + "e" + Y + "f"], "c3": ["g" + Y + "h"]}
        m = K.Miner(convs_of(spec), "synthetic")
        picks, _ = m.curate(3, 32, 2, 10)
        self.assertEqual([p["body"] for p in picks], [X, Y])
        self.assertEqual(picks[0]["G"], picks[1]["G"])
        self.assertGreater(picks[0]["total_len"], picks[1]["total_len"])

    def test_greedy_sequence_independent_of_C(self):
        spec = {f"c{i}": [f"u{i}\n" + "\n".join(f"shared line {j} " + "z" * 60 for j in range(4))] for i in range(5)}
        spec.update({f"d{i}": ["only " + "q" * 80 + f" {i}"] for i in range(3)})
        m = K.Miner(convs_of(spec), "synthetic")
        full, _ = m.curate(8, 32, 2, 1000)
        for C in (1, 2, 5):
            part, _ = m.curate(8, 32, 2, C)
            self.assertEqual([p["body"] for p in part], [p["body"] for p in full][:C])

    def test_deterministic(self):
        spec = {f"c{i}": [f"u{i}\n{LINE_A}\n{LINE_B}"] for i in range(4)}
        a = K.Miner(convs_of(spec), "synthetic").curate(4, 32, 2, 10)[0]
        b = K.Miner(convs_of(spec), "synthetic").curate(4, 32, 2, 10)[0]
        self.assertEqual(a, b)


class _GreedyStub:
    """Minimal Miner stand-in: made-up occurrence lists, so occurrence contributions can be negative."""
    prov = "synthetic"

    def __init__(self, msg_lens, occ_by_body):
        self.msgs = ["x" * n for n in msg_lens]
        self.msg_conv = {i: f"c{i}" for i in range(len(msg_lens))}
        self.occ_by_body = occ_by_body

    def _occ_list(self, kind, body, params, cutoff):
        return list(self.occ_by_body.get(body, []))

    _gain = staticmethod(K.Miner._gain)


def _naive_reference(stub, cands, C, joiners):
    """Independent reference: after EVERY pick, recompute the gain of EVERY remaining candidate from scratch."""
    mult = 1 + joiners
    items = []
    for key in sorted(cands, key=lambda x: (x[1], x[2])):
        kind, body, params = cands[key]
        occ = stub._occ_list(kind, body, params, None)
        if occ:
            items.append((kind, body, params, occ, K._record_size(kind, body, [dict(name=n, type=t) for n, t in params], stub.prov) * mult))
    covered = set()
    picks, alive = [], list(range(len(items)))
    while len(picks) < C:
        best = None
        for i in alive:
            kind, body, params, occ, rec = items[i]
            g = tl = 0
            taken, last_m, last_e = [], -1, -1
            for m, s, e, lb, ab in occ:
                if m != last_m:
                    last_m, last_e = m, -1
                if s < last_e or any((m, x) in covered for x in range(s, e)):
                    continue
                g += lb - (1 + K.PROVISIONAL_ORDINAL_BYTES + ab)
                tl += lb
                taken.append((m, s, e))
                last_e = e
            g -= rec
            if g > 0:
                key = (-g, -tl, body.encode("utf-8"), i)
                if best is None or key < best[0]:
                    best = (key, i, g, taken)
        if best is None:
            break
        _, i, g, taken = best
        for m, s, e in taken:
            covered.update((m, x) for x in range(s, e))
        picks.append((items[i][1], g))
        alive.remove(i)
    return picks


class TestGreedyExactness(unittest.TestCase):
    """GPT blocker 1: the greedy must equal a full recomputation after every pick (G can RISE when a negative-contribution
    occurrence is masked)."""

    def test_gain_rises_after_masking_a_negative_occurrence(self):
        # GPT's +1, +1, -1 example: candidate B's occurrences contribute +rec, +1, -1 (messages 0, 1, 2).
        rec = K._record_size("literal", "B" * 40, [], "synthetic")
        # B: +rec+1 total only after the -1 occurrence is masked away; A (picked first, higher G) masks it.
        stub = _GreedyStub([10, 10, 10],
                           {"A" * 40: [(2, 0, 10, 10 + 3 + 400, 0)],
                            "B" * 40: [(0, 0, 10, 3 + rec, 0), (1, 0, 10, 3 + 1, 0), (2, 0, 10, 3 - 1, 0)]})
        cands = {("literal", b, ()): ("literal", b, ()) for b in ("A" * 40, "B" * 40)}
        got = K.Miner._greedy(stub, cands, None, 10, 0)
        ref = _naive_reference(stub, cands, 10, 0)
        self.assertEqual([(p["body"], p["G"]) for p in got], ref)
        # before A: G(B) = rec + 1 - 1 - rec = 0 (not pickable); after A: G(B) = rec + 1 - rec = 1 (picked)
        self.assertEqual([b[0] for b in ref], ["A" * 40, "B" * 40])
        self.assertEqual(ref[1][1], 1)

    def test_randomised_equals_naive_full_recompute(self):
        import random
        rng = random.Random(77)
        for trial in range(400):
            nm = rng.randint(2, 6)
            lens = [rng.randint(12, 40) for _ in range(nm)]
            occ_by_body, cands = {}, {}
            for ci in range(rng.randint(2, 8)):
                body = chr(97 + ci) * rng.randint(30, 40)
                occ = []
                for m in range(nm):
                    s = 0
                    while s + 4 <= lens[m] and rng.random() < 0.7:
                        e = rng.randint(s + 3, min(lens[m], s + 14))
                        ab = rng.choice([0, 0, 1, 3, 9])
                        lb = (e - s) + rng.choice([0, 0, 0, 20, 100, 150, 200])
                        if ab and rng.random() < 0.5:
                            lb = rng.randint(1, 3 + ab)  # a negative contribution
                        occ.append((m, s, e, lb, ab))  # contributions lb-(3+ab) may be negative
                        s = e + rng.randint(0, 3)
                if occ:
                    occ_by_body[body] = occ
                    cands[("literal", body, ())] = ("literal", body, ())
            stub = _GreedyStub(lens, occ_by_body)
            joiners = rng.choice([0, 0, 3])
            C = rng.choice([1, 2, 5, 50])
            got = K.Miner._greedy(stub, cands, None, C, joiners)
            self.assertEqual([(p["body"], p["G"]) for p in got], _naive_reference(stub, cands, C, joiners), trial)

    def test_selection_is_deterministic(self):
        rec = K._record_size("literal", "A" * 40, [], "synthetic")
        stub = _GreedyStub([10, 10], {"A" * 40: [(0, 0, 10, 3 + rec + 5, 0)], "B" * 40: [(1, 0, 10, 3 + rec + 5, 0)]})
        cands = {("literal", b, ()): ("literal", b, ()) for b in ("B" * 40, "A" * 40)}
        runs = [[p["body"] for p in K.Miner._greedy(stub, cands, None, 5, 0)] for _ in range(3)]
        self.assertEqual(runs[0], runs[1])
        self.assertEqual(runs[0], ["A" * 40, "B" * 40])  # equal G and total length: lexicographically smaller body first


class _ChainStub:
    """Scripted curation: picks_by_n[n_convs] -> list of literal bodies (pick order)."""
    prov = "synthetic"

    def __init__(self, picks_by_n):
        self.picks_by_n, self.calls = picks_by_n, []

    def curate(self, n, L, k, C, joiners):
        self.calls.append(n)
        picks = [{"kind": "literal", "body": b, "params": [], "G": 100 - i, "total_len": 50, "occurrences": 3,
                  "convs": [f"conv{i}"], "entry_cost": 10} for i, b in enumerate(self.picks_by_n.get(n, []))]
        return picks, {"n_convs": n}


class TestAppendOnlyChain(unittest.TestCase):
    """Amendment A1 section 4.7: the append-only publication rule, stated and tested exactly."""
    A, B, C_, D = ("alpha " * 8, "bravo " * 8, "charlie " * 8, "delta " * 8)

    def test_stable_ids_union_and_published_vs_scheduled_numbering(self):
        # n_dev=10, V=5 -> prefixes 2,4,6,8,10 (ceil(j*10/5))
        stub = _ChainStub({2: [self.A], 4: [self.A], 6: [self.B, self.A], 8: [self.B], 10: [self.C_]})
        ch = K.build_repository_chain(stub, 10, 5, 32, 2, 50, 0)
        self.assertEqual(stub.calls, [2, 4, 6, 8, 10])          # every scheduled version <= max_version is curated
        self.assertEqual([r["sched_version"] for r in ch], [1, 3, 5])   # 2 and 4 added nothing: no publication
        self.assertEqual([r["skipped_versions"] for r in ch], [[], [2], [4]])
        ids = lambda r: {e["body"]: e["id"] for e in r["state"].entries.values()}
        self.assertEqual(ids(ch[0]), {self.A: "e00001"})
        self.assertEqual(ids(ch[1]), {self.A: "e00001", self.B: "e00002"})          # A keeps its id; B appended
        self.assertEqual(ids(ch[2]), {self.A: "e00001", self.B: "e00002", self.C_: "e00003"})  # union keeps B although v4 omitted it
        self.assertEqual([r["state"].version for r in ch], [1, 2, 3])               # published numbering is consecutive
        self.assertIsNone(ch[0]["delta"])
        self.assertIsNotNone(ch[1]["delta"])
        self.assertEqual([row["status"] for row in ch.schedule], ["published", "empty", "published", "empty", "published"])
        self.assertEqual([row["published_index"] for row in ch.schedule], [1, None, 2, None, 3])
        self.assertEqual(ch.trailing_skipped, [])
        self.assertEqual([x["id"] for x in ch[1]["entry_lineage"]], ["e00002"])
        self.assertEqual(ch[1]["entry_lineage"][0]["convs"], ["conv0"])  # first-publication lineage (pick 0 of version 3)

    def test_empty_snapshots_and_trailing_skipped_versions_are_preserved(self):
        stub = _ChainStub({2: [self.A]})
        ch = K.build_repository_chain(stub, 10, 5, 32, 2, 50, 0)
        self.assertEqual(len(ch), 1)
        self.assertEqual(ch.trailing_skipped, [2, 3, 4, 5])
        self.assertEqual(len(ch.schedule), 5)
        self.assertEqual([r["status"] for r in ch.schedule], ["published", "empty", "empty", "empty", "empty"])

    def test_max_version_leaves_higher_versions_unused(self):
        stub = _ChainStub({2: [self.A], 4: [self.B], 6: [self.C_]})
        ch = K.build_repository_chain(stub, 10, 5, 32, 2, 50, 0, max_version=2)
        self.assertEqual(stub.calls, [2, 4])
        self.assertEqual([r["status"] for r in ch.schedule], ["published", "published", "unused", "unused", "unused"])
        self.assertEqual(ch.trailing_skipped, [3, 4, 5])
        self.assertEqual(ch.max_version, 2)

    def test_nothing_published_at_all(self):
        ch = K.build_repository_chain(_ChainStub({}), 10, 2, 32, 2, 50, 0)
        self.assertEqual(len(ch), 0)
        self.assertEqual(ch.trailing_skipped, [1, 2])

    def test_union_limit_and_overflow_drops_the_last_new_entries_in_pick_order(self):
        old = K.MAX_ENTRIES
        K.MAX_ENTRIES = 3
        try:
            stub = _ChainStub({2: [self.A, self.B], 4: [self.C_, self.A, self.D]})
            ch = K.build_repository_chain(stub, 10, 5, 32, 2, 50, 0)
        finally:
            K.MAX_ENTRIES = old
        self.assertEqual([r["new_entries"] for r in ch], [2, 1])
        self.assertEqual([r["overflow"] for r in ch], [0, 1])
        self.assertEqual({e["body"] for e in ch[1]["state"].entries.values()}, {self.A, self.B, self.C_})  # D (last new in pick order) dropped
        self.assertEqual(ch.schedule[1]["overflow"], 1)

    def test_a_full_repository_publishes_nothing_more(self):
        old = K.MAX_ENTRIES
        K.MAX_ENTRIES = 2
        try:
            ch = K.build_repository_chain(_ChainStub({2: [self.A, self.B], 4: [self.C_]}), 10, 5, 32, 2, 50, 0)
        finally:
            K.MAX_ENTRIES = old
        self.assertEqual(len(ch), 1)
        self.assertEqual(ch.schedule[1]["status"], "empty")
        self.assertEqual(ch.schedule[1]["overflow"], 1)

    def test_C_does_not_limit_the_union(self):
        stub = _ChainStub({2: [self.A], 4: [self.B], 6: [self.C_]})
        ch = K.build_repository_chain(stub, 10, 5, 32, 2, 1, 0)   # C=1 per version, but the union holds 3 entries
        self.assertEqual(len(ch[-1]["state"].entries), 3)


class TestSizeAwareOverflow(unittest.TestCase):
    """GPT r2 blocker 1 / amendment A1.3.1: the byte limit (E1E-REPO/1 1 MiB, inclusive) applies to BOTH the canonical full
    snapshot and the publication delta, measured on exact serialized bytes; the longest prefix of new entries in pick order
    is admitted; the first pick that does not fit ends the prefix."""
    LIMIT = 1 << 20

    @staticmethod
    def body(i, n, ch="a"):
        h = f"<{i:04d}>"
        return (h + ch * n)[:n] if n >= len(h) else (h)[:n]

    @staticmethod
    def sizes(state, bodies, first_id=None):
        """Exact (len(full), len(delta)) for publishing `bodies` on `state` with sequential ids (reference, independent of
        artifacts_fit: it uses the real Publisher machinery and canonical serialization)."""
        from e1e.repo import Publisher, make_delta, RepoState
        n0 = len(state._e)
        ents = [K.make_entry_strict(f"e{n0 + 1 + i:05d}", 1, b, None, prov="synthetic") for i, b in enumerate(bodies)]
        merged = dict(state._e)
        merged.update({e["id"]: e for e in ents})
        return len(RepoState(state.version + 1, merged).full_bytes()), len(make_delta(state, ents))

    def reference_prefix(self, state, bodies):
        k = 0
        for i in range(1, len(bodies) + 1):
            f, d = self.sizes(state, bodies[:i])
            if f <= self.LIMIT and d <= self.LIMIT:
                k = i
            else:
                break
        return k

    def chain_of_bodies(self, picks_by_n, n_dev=10, V=5):
        return K.build_repository_chain(_ChainStub(picks_by_n), n_dev, V, 32, 2, 1000, 0)

    def test_64_entries_of_16384_ascii_chars_no_longer_raise(self):
        from e1e.repo import RepoState
        bodies = [self.body(i, 16384) for i in range(64)]
        ch = self.chain_of_bodies({2: bodies})
        k = self.reference_prefix(RepoState(), bodies)
        self.assertEqual(k, 63)                      # 64 x 16,384 B alone exceeds 1 MiB
        self.assertEqual(ch[0]["new_entries"], k)
        self.assertEqual((ch[0]["overflow_bytes"], ch[0]["overflow_count"], ch[0]["overflow"]), (64 - k, 0, 64 - k))
        self.assertLessEqual(len(ch[0]["full"]), self.LIMIT)
        self.assertEqual([x["id"] for x in ch[0]["entry_lineage"]], [f"e{i + 1:05d}" for i in range(k)])  # the prefix in pick order
        self.assertEqual(ch.schedule[0]["overflow_bytes"], 64 - k)

    def test_escaped_and_non_ascii_bodies_are_measured_on_serialized_bytes(self):
        from e1e.repo import RepoState
        bodies = []
        for i in range(40):
            ch = ["\u00e9", "\U0001F600", "\"", "\\", "\n"][i % 5]  # 6, 12, 2, 2, 2 serialized bytes per code point
            bodies.append(self.body(i, 16384, ch=ch))
        chain = self.chain_of_bodies({2: bodies})
        k = self.reference_prefix(RepoState(), bodies)
        self.assertGreater(k, 0)
        self.assertLess(k, 40)
        self.assertEqual(chain[0]["new_entries"], k)
        self.assertEqual(chain[0]["overflow_bytes"], 40 - k)
        self.assertLessEqual(len(chain[0]["full"]), self.LIMIT)
        # the next pick would have fit by raw character count (16,384 x k+1 chars < 1 MiB) but not by serialized bytes
        self.assertLess(16384 * (k + 1), self.LIMIT)

    def test_overflow_against_an_existing_repository_preserves_existing_entries(self):
        first = [self.body(0, 16384), self.body(1, 16384)]
        more = [self.body(2 + i, 16384) for i in range(70)]
        ch = self.chain_of_bodies({2: first, 4: first + more})
        self.assertEqual(len(ch), 2)
        st1 = ch[0]["state"]
        k = self.reference_prefix(st1, more)
        self.assertGreater(k, 55)
        self.assertLess(k, 70)
        self.assertEqual(ch[1]["new_entries"], k)
        self.assertEqual(ch[1]["overflow_bytes"], 70 - k)
        self.assertEqual(len(ch[1]["state"]._e), 2 + k)
        for i, e in st1._e.items():                     # existing entries preserved unchanged
            self.assertEqual(ch[1]["state"]._e[i], e)
        self.assertLessEqual(len(ch[1]["full"]), self.LIMIT)
        self.assertLessEqual(len(ch[1]["delta"]), self.LIMIT)

    def _fill_and_tune(self, state, want, which, extra=()):
        """(fill bodies, n): `fill` = f maximal 16,384-char bodies (f as large as possible) then one body of n chars (50 <= n <=
        16,384) such that the chosen artifact (0 = full snapshot, 1 = delta) of publishing extra + fill + tuned on `state` is
        EXACTLY `want` bytes. Exact serialized sizes, ASCII bodies (1 byte per char)."""
        for f in range(64, 0, -1):
            fill = [self.body(1 + i, 16384) for i in range(f)]
            n0 = 100
            a = self.sizes(state, list(extra) + fill + [self.body(900, n0)])[which]
            n = n0 + (want - a)
            if 50 <= n <= 16384:
                bodies = list(extra) + fill + [self.body(900, n)]
                assert self.sizes(state, bodies)[which] == want
                return fill, n
        raise AssertionError("no tuning found")

    def test_exact_boundary_is_inclusive_full_snapshot(self):
        small = [self.body(0, 200)]
        st1 = self.chain_of_bodies({2: small})[0]["state"]
        for extra, admitted in ((0, True), (1, False)):
            fill, n = self._fill_and_tune(st1, self.LIMIT + extra, 0)
            nf = len(fill)
            ch = self.chain_of_bodies({2: small, 4: small + fill + [self.body(900, n)]})
            self.assertEqual(len(ch), 2)
            self.assertLessEqual(len(ch[1]["full"]), self.LIMIT)
            if admitted:
                self.assertEqual(len(ch[1]["full"]), self.LIMIT)       # exactly the limit: admitted (inclusive)
                self.assertEqual((ch[1]["new_entries"], ch[1]["overflow_bytes"]), (nf + 1, 0))
            else:
                self.assertEqual((ch[1]["new_entries"], ch[1]["overflow_bytes"]), (nf, 1))  # one byte over: last entry dropped

    def test_exact_boundary_is_inclusive_delta(self):
        from e1e.repo import RepoState
        for extra, admitted in ((0, True), (1, False)):
            fill, n = self._fill_and_tune(RepoState(), self.LIMIT + extra, 1)
            nf = len(fill)
            ch = self.chain_of_bodies({2: fill + [self.body(900, n)]})
            self.assertEqual((ch[0]["new_entries"], ch[0]["overflow_bytes"]), (nf + 1, 0) if admitted else (nf, 1))
            self.assertLessEqual(len(ch[0]["full"]), self.LIMIT)
        # (for the first publication the delta is the binding artifact: it is larger than the full snapshot)

    def test_delta_over_the_limit_while_the_full_snapshot_fits(self):
        from e1e.repo import RepoState
        fill, n = self._fill_and_tune(RepoState(), self.LIMIT + 1, 1)   # delta exactly one byte over
        bodies = fill + [self.body(900, n)]
        f, d = self.sizes(RepoState(), bodies)
        self.assertTrue(f <= self.LIMIT < d, (f, d))
        ch = self.chain_of_bodies({2: bodies})
        self.assertEqual(ch[0]["new_entries"], len(fill))     # the last is dropped because of the DELTA, although the full fits
        self.assertEqual(ch[0]["overflow_bytes"], 1)

    def test_nothing_fits_publishes_nothing_and_never_skips_to_a_later_smaller_pick(self):
        small = [self.body(0, 200)]
        st1 = self.chain_of_bodies({2: small})[0]["state"]
        fill, n = self._fill_and_tune(st1, self.LIMIT - 400, 0)   # existing repository: full snapshot 400 B below the limit
        first = small + fill + [self.body(900, n)]
        too_big = self.body(901, 3000)
        tiny = self.body(902, 50)
        ch = self.chain_of_bodies({2: small, 4: first, 6: first + [too_big, tiny]})
        self.assertEqual([r["sched_version"] for r in ch], [1, 2])
        r3 = ch.schedule[2]
        self.assertEqual((r3["status"], r3["new_entries"], r3["overflow_bytes"], r3["overflow_count"]), ("empty", 0, 2, 0))
        self.assertEqual(ch.trailing_skipped, [3, 4, 5])
        self.assertEqual(len(ch[1]["state"]._e), len(first))   # current snapshot preserved; "tiny" not admitted in place of "too_big"
        f, d = self.sizes(ch[1]["state"], [tiny])
        self.assertTrue(f <= self.LIMIT and d <= self.LIMIT, (f, d))            # tiny alone WOULD have fit

    def test_count_limit_and_byte_limit_overflow_are_reported_separately(self):
        old = K.MAX_ENTRIES
        K.MAX_ENTRIES = 5
        try:
            bodies = [self.body(i, 16384) for i in range(8)]   # 8 new picks: count limit keeps 5, bytes keep all 5 (5 x 16 KiB)
            ch = self.chain_of_bodies({2: bodies})
        finally:
            K.MAX_ENTRIES = old
        self.assertEqual((ch[0]["new_entries"], ch[0]["overflow_count"], ch[0]["overflow_bytes"], ch[0]["overflow"]), (5, 3, 0, 3))
        old = K.MAX_ENTRIES
        K.MAX_ENTRIES = 70
        try:
            bodies = [self.body(i, 16384) for i in range(72)]  # count limit 70 -> drops 2; then the byte limit keeps 63
            ch = self.chain_of_bodies({2: bodies})
        finally:
            K.MAX_ENTRIES = old
        self.assertEqual((ch[0]["new_entries"], ch[0]["overflow_count"], ch[0]["overflow_bytes"], ch[0]["overflow"]), (63, 2, 7, 9))

    def test_longest_fitting_prefix_matches_a_linear_scan(self):
        import random
        from e1e.repo import RepoState
        rng = random.Random(5)
        for _ in range(4):
            bodies = [self.body(i, rng.choice([2000, 9000, 16384, 16384])) for i in range(100)]
            ents = [K.make_entry_strict(f"e{i + 1:05d}", 1, b, None, prov="synthetic") for i, b in enumerate(bodies)]
            self.assertEqual(K.longest_fitting_prefix(RepoState(), ents), self.reference_prefix(RepoState(), bodies))


class TestTemplates(unittest.TestCase):
    TAIL = "; report to the orchestrator now and attach the full log for the maintainers to read"

    def line(self, i):
        return f"STATUS: job-{i} is {'done' if i % 2 else 'failed'} after {i * 7} steps" + self.TAIL

    def mk(self):
        # four distinct lines, each in two conversations (so each is a literal candidate), differing only in args
        spec = {}
        for i in range(1, 5):
            for r in range(2):
                spec[f"c{i}{r}"] = [chr(97 + 2 * i + r) + "\n" + self.line(i) + "\n" + chr(65 + 2 * i + r)]
        return spec

    def test_template_mined_with_int_and_word_params(self):
        m = K.Miner(convs_of(self.mk()), "synthetic")
        picks, st = m.curate(8, 32, 2, 10)
        t = [p for p in picks if p["kind"] == "template"]
        self.assertEqual(len(t), 1, [p["body"] for p in picks])
        self.assertEqual(t[0]["body"], "STATUS: {p1} is {p2} after {p3} steps" + self.TAIL)
        self.assertEqual(t[0]["params"], [("p1", "word"), ("p2", "word"), ("p3", "int")])
        self.assertEqual(t[0]["occurrences"], 8)

    def test_mine_templates_rules(self):
        m = K.Miner([("c", ["x"])], "synthetic")
        mk = lambda texts: [{"text": t, "convs": frozenset({0, 1})} for t in texts]
        # identical separators and token counts group; int only when every value is an int
        tp, d = m.mine_templates(mk(["id 5 ok go", "id 6 ok go", "id 7 ok go"]), 2)
        self.assertEqual([(b, p) for b, p, _ in tp], [("id {p1} ok go", [("p1", "int")])])
        tp, d = m.mine_templates(mk(["id 5 ok go", "id x7 ok go"]), 2)
        self.assertEqual([p for _, p, _ in tp], [[("p1", "word")]])
        # different separators or token counts: different groups, no template (single distinct member)
        tp, d = m.mine_templates(mk(["id 5 ok go", "id  6 ok go", "id 7 ok go now"]), 2)
        self.assertEqual(tp, [])
        # more than 4 params: discarded
        tp, d = m.mine_templates(mk(["a1 b1 c1 d1 e1 end", "a2 b2 c2 d2 e2 end"]), 2)
        self.assertEqual((tp, d), ([], 1))
        # braces in source are escaped
        tp, d = m.mine_templates(mk(["{id 5} ok go", "{id 6} ok go"]), 2)
        self.assertEqual(tp[0][0], "{{id {p1}}} ok go")
        # group must reach k conversations
        tp, d = m.mine_templates([{"text": "id 5 ok go", "convs": frozenset({0})},
                                  {"text": "id 6 ok go", "convs": frozenset({0})}], 2)
        self.assertEqual(tp, [])
        # leading zeros: not an int
        tp, d = m.mine_templates(mk(["id 05 ok go", "id 6 ok go"]), 2)
        self.assertEqual(tp[0][1], [("p1", "word")])
        # a block with no token at all makes no template
        tp, d = m.mine_templates(mk(["  ++  ", "  ++  "]), 2)
        self.assertEqual(tp, [])

    def test_template_gain_uses_per_occurrence_length(self):
        m = K.Miner(convs_of(self.mk()), "synthetic")
        picks, _ = m.curate(8, 32, 2, 10)
        p = [p for p in picks if p["kind"] == "template"][0]
        total = sum(2 * len(self.line(i).encode()) for i in range(1, 5))
        self.assertEqual(p["total_len"], total)  # lengths vary with the args; not 8 * a constant
        self.assertNotEqual(total, 8 * len(self.line(1).encode()))
        # G = sum(len(o) - (1 + 2 + arg bytes of o)) - entry cost; args: word len+bytes, word len+bytes, zigzag int
        from e1e.compact import encode_zigzag
        argb = sum(2 * (1 + len(f"job-{i}") + 1 + len('done' if i % 2 else 'failed') + len(encode_zigzag(i * 7)))
                   for i in range(1, 5))
        rec = len(canonical(make_entry("e00000", 1, p["body"], p["params"], prov="synthetic")))
        self.assertEqual(p["G"], total - 8 * 3 - argb - rec)


class TestIdsAndTuning(unittest.TestCase):
    def test_ids_reused_for_identical_content(self):
        picks = [{"kind": "literal", "body": "A" * 40, "params": []}, {"kind": "literal", "body": "B" * 40, "params": []}]
        first = K.entries_from_picks(picks, "synthetic")
        self.assertEqual([e["id"] for e in first], ["e00001", "e00002"])
        prev = {e["id"]: e for e in first}
        picks2 = [{"kind": "literal", "body": "C" * 40, "params": []}] + picks
        again = K.entries_from_picks(picks2, "synthetic", prev)
        self.assertEqual([(e["id"], e["body"][0]) for e in again], [("e00003", "C")])

    def test_forward_only_tuning_never_sees_block_t_or_later(self):
        spec = {f"c{i:02d}": [f"msg {i} " + LINE_A + f" tail {i}"] for i in range(10)}
        m = K.Miner(convs_of(spec), "synthetic")
        seen = []
        orig = m.curate

        def spy(n_convs, L, k, C, joiners=0):
            seen.append(n_convs)
            return orig(n_convs, L, k, C, joiners)
        m.curate = spy
        calls = []

        def evaluate(picks, block):
            calls.append(block)
            return 1000 + len(picks)
        best, scores = K.tune(m, evaluate)
        self.assertEqual(sorted(set(seen)), [2, 4, 6, 8])  # B1..B(t-1) for t = 2..5 = first 2,4,6,8 of 10 conversations
        self.assertEqual(len(scores), 24)
        self.assertEqual(set(calls), {(2, 4), (4, 6), (6, 8), (8, 10)})

    def test_tuning_tie_break_prefers_smaller_L_then_k_then_C(self):
        spec = {f"c{i:02d}": [f"m{i} " + LINE_A] for i in range(10)}
        m = K.Miner(convs_of(spec), "synthetic")
        best, scores = K.tune(m, lambda picks, block: 5000)  # every grid point ties
        self.assertEqual(best, (32, 2, 50))
        best, scores = K.tune(m, lambda picks, block: 5000 - len(picks))  # fewer bytes with more picks
        self.assertEqual(scores[best], min(scores.values()))

    def test_tuning_needs_five_conversations(self):
        m = K.Miner(convs_of({"a": ["x"], "b": ["y"]}), "synthetic")
        with self.assertRaises(ValueError):
            K.tune(m, lambda p, b: 0)


if __name__ == "__main__":
    unittest.main()
