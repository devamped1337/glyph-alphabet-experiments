"""E1f baselines additions: framing prefix lines, oversized fallback, 4b-delta, arm 7 accounting, scenario runner.
Made-up data only."""
import unittest

from tests import fixtures  # noqa: F401
from e1e import Publisher, make_entry, E1EError
from e1e import baselines as B
from e1e import compact as C
from e1e.codec import raw_wire, declare_wire

BODY1 = "The reviewer found problems in module alpha; please fix the retry path first, then rerun everything."
BODY2 = "STATUS: complete | suite=retry_policy | passed=8 | failed=0 | all checks finished for the nightly run."


def chain_of(*batches):
    pub = Publisher()
    out = []
    for i, ents in enumerate(batches):
        delta, full = pub.publish(ents)
        out.append({"state": pub.state, "full": full, "delta": delta if i else None})
    return out


def replay_of(texts, conv="c1"):
    return [{"conv_id": conv, "sender": "a", "receiver": "b", "msg": t if isinstance(t, bytes) else t.encode()} for t in texts]


class TestPrefixAndFallback(unittest.TestCase):
    def test_prefix_lengths(self):
        self.assertEqual([B.prefix_len(n) for n in (0, 127, 128, 16383, 16384, 2**21 - 1, 2**21, 2**32 - 1)],
                         [1, 1, 2, 2, 3, 3, 4, 5])

    def test_oversized_fallback_smaller_of_zstd_and_raw_ties_raw(self):
        c3 = B.baseline3()
        msg = b"abc " * 20000  # 80,000 bytes, compresses to a few bytes
        data, kind = B.oversized_fallback(msg, c3)
        self.assertEqual(kind, "zstd")
        self.assertEqual(c3.decompress(data), msg)
        self.assertLess(len(data), len(raw_wire(msg)))
        # incompressible-ish: raw envelope can never beat zstd by tie unless equal; ties go to raw
        class Fake:
            def compress(self, m):
                return b"x" * len(raw_wire(m))
        self.assertEqual(B.zstd_or_raw(b"hi", Fake())[1], "raw")


class TestSyncAccounting(unittest.TestCase):
    def setUp(self):
        self.chain = chain_of([make_entry("e1", 1, BODY1)], [make_entry("e2", 1, BODY2)], [make_entry("e3", 1, "third entry body " * 5)])

    def test_repo_artifact_sync_numbers(self):
        c = self.chain
        full1, d2, d3 = len(c[0]["full"]), len(c[1]["delta"]), len(c[2]["delta"])
        s = B.repo_artifact_sync(c, participants=2)
        self.assertEqual(s["upload"], full1 + d2 + d3)
        self.assertEqual(s["download"], 2 * (full1 + d2 + d3))
        s = B.repo_artifact_sync(c, participants=10, joiner_versions=[2, 3, 3])
        up = full1 + d2 + d3 + len(c[1]["full"]) + len(c[2]["full"])  # joined versions' full snapshots uploaded once each
        down = 10 * (full1 + d2 + d3) + len(c[1]["full"]) + 2 * len(c[2]["full"])
        self.assertEqual((s["upload"], s["download"], s["total"]), (up, down, up + down))

    def test_4b_full_rebuild_vs_4b_delta_sync(self):
        c = self.chain
        sizes = [len(B.repo_dict_bytes(r["state"])) for r in c]
        a1 = B.dict_rebuild_sync(c, 2, [3])
        self.assertEqual(a1["upload"], sum(sizes))
        self.assertEqual(a1["download"], 2 * sum(sizes) + sizes[2])
        delta = B.repo_artifact_sync(c, 2, [3])
        self.assertNotEqual(a1["total"], delta["total"])

    def test_joiner_indexes(self):
        self.assertEqual(B.joiner_indexes(100), [25, 50, 75])
        self.assertEqual(B.joiner_indexes(7), [1, 3, 5])

    def test_empty_chain(self):
        self.assertEqual(B.repo_artifact_sync([], 2, [1])["total"], 0)
        self.assertEqual(B.dict_rebuild_sync([], 2, [1])["total"], 0)


class TestRunner(unittest.TestCase):
    def setUp(self):
        self.chain = chain_of([make_entry("e1", 1, BODY1)], [make_entry("e2", 1, BODY2)])
        self.texts = ["intro " + BODY1 + " outro", BODY2, "unrelated short", BODY1, "\u00e9 " + BODY2 + " \u65e5"] * 4
        self.replay = replay_of(self.texts)

    def run_it(self, vi=lambda r: 1 if r < 10 else 2, arms=B.ARMS):
        return B.replay_arms(self.replay, self.chain, vi, arms)

    def test_all_arms_byte_exact_and_accounted(self):
        res = self.run_it()
        self.assertEqual(set(res), set(B.ARMS))
        for a, r in res.items():
            self.assertEqual(r["eligible_messages"], 20, a)
            self.assertEqual(sum(r["kinds"].values()), 20, a)
        self.assertEqual(res["1"]["kinds"], {"raw": 20})
        self.assertEqual(res["1"]["message_bytes"], sum(len(raw_wire(m["msg"])) for m in self.replay))

    def test_4b_delta_has_the_same_message_bytes_as_4b(self):
        res = self.run_it()
        for k in ("message_bytes", "message_prefix_bytes", "kinds", "declare_bytes_incl_prefix"):
            self.assertEqual(res["4b"][k], res["4b-delta"][k], k)
        tot = B.scenario_totals(res, self.chain, 2, [1])
        self.assertNotEqual(tot["4b"]["sync_total"], tot["4b-delta"]["sync_total"])
        self.assertEqual(tot["4b"]["message_bytes"], tot["4b-delta"]["message_bytes"])

    def test_declaration_rule_is_the_same_for_repo_arms_including_empty_repository(self):
        # no snapshot published for the first messages: every repo arm still pays the (version 0) declaration
        res = B.replay_arms(self.replay, self.chain, lambda r: 0 if r < 4 else 1)
        decl = {a: res[a]["declare_bytes_incl_prefix"] for a in ("4b", "4b-delta", "5", "6", "7")}
        self.assertEqual(len(set(decl.values())), 1, decl)
        self.assertGreater(decl["7"], 0)
        self.assertEqual(res["3"]["declare_bytes_incl_prefix"], 0)

    def test_arm7_accounting_lines(self):
        res = self.run_it()
        r = res["7"]
        self.assertEqual(r["rejected"], 0)
        self.assertGreater(r["messages_with_refs"], 0)
        self.assertGreater(r["covered_bytes"], 0)
        # one declaration per link per snapshot change: version 1 first use, then version 2
        self.assertEqual(r["declare_bytes_incl_prefix"],
                         sum(len(declare_wire({"version": i, "digest": self.chain[i - 1]["state"].digest}))
                             + B.prefix_len(len(declare_wire({"version": i, "digest": self.chain[i - 1]["state"].digest})))
                             for i in (1, 2)))
        # every compact/raw first send is charged its LEB128 prefix on its own line
        self.assertGreaterEqual(r["message_prefix_bytes"], r["eligible_messages"])
        self.assertLess(r["message_bytes"], res["1"]["message_bytes"])  # un-escaped framing alone beats the raw envelope

    def test_totals_separate_message_and_sync(self):
        res = self.run_it()
        tot = B.scenario_totals(res, self.chain, 2, [])
        t7 = tot["7"]
        self.assertEqual(t7["total"], t7["message_plus_control_total"] + t7["sync_total"])
        self.assertEqual(t7["sync_total"], B.repo_artifact_sync(self.chain, 2)["total"])
        self.assertEqual(tot["1"]["sync_total"], 0)
        self.assertEqual(tot["5"]["sync_total"], t7["sync_total"])
        self.assertEqual(tot["4b-delta"]["sync_total"], t7["sync_total"])

    def test_arm6_charges_baseline4_dictionary_on_top_of_repo_sync(self):
        c4 = B.baseline4([("%s %d" % (BODY1, i)).encode() for i in range(60)], 1024)
        if c4 is None:
            self.skipTest("zstd could not train on this made-up sample")
        res = B.replay_arms(self.replay, self.chain, lambda r: 1, ("6", "7"), b4_codec=c4)
        tot = B.scenario_totals(res, self.chain, 2, [1], c4)
        art = B.repo_artifact_sync(self.chain, 2, [1])
        self.assertEqual(tot["6"]["sync_total"], art["total"] + len(c4.dict_bytes) * (1 + 2 + 1))

    def test_oversized_message_common_fallback_in_every_arm(self):
        big = b"zq " * 30000
        rep = replay_of(["hello " + BODY1, big, BODY2])
        res = B.replay_arms(rep, self.chain, lambda r: 1)
        c3 = B.baseline3()
        data, kind = B.oversized_fallback(big, c3)
        for a, r in res.items():
            self.assertEqual(r["eligible_messages"], 2, a)
            self.assertEqual(r["oversized"], {"count": 1, "input_bytes": len(big), "fallback_bytes": len(data),
                                              "fallback_prefix_bytes": B.prefix_len(len(data))}, a)
        tot = B.scenario_totals(res, self.chain, 2, [])
        for a in B.ARMS:
            self.assertEqual(tot[a]["all_message_total"], tot[a]["total"] + len(data) + B.prefix_len(len(data)))

    def test_empty_repository_all_arms_still_exact(self):
        res = B.replay_arms(self.replay, [], lambda r: 0)
        self.assertEqual(res["7"]["kinds"], {"raw": 20})  # compact needs an epoch >= 1
        self.assertEqual(res["5"]["kinds"], {"raw": 20})
        self.assertEqual(res["4b"]["message_bytes"], res["3"]["message_bytes"])  # A1: empty repo == baseline 3

    def test_scenario_grid(self):
        self.assertEqual(len(B.SCENARIO_GRID), 12)
        self.assertEqual(B.PRIMARY_SCENARIO, {"V": 5, "participants": 2, "joiners": 0})
        self.assertIn(B.PRIMARY_SCENARIO, B.SCENARIO_GRID)

    def test_select_baseline4_ineligible_is_not_trainable(self):
        codec, rep = B.select_baseline4([("c%d" % i, [b"x" * 100]) for i in range(5)])
        self.assertIsNone(codec)
        self.assertEqual(rep["status"], "not trainable (insufficient dev corpus)")


if __name__ == "__main__":
    unittest.main()
