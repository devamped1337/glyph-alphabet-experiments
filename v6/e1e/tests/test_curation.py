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
