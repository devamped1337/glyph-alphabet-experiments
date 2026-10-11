"""Unit tests on tiny synthetic data; no model inference. Run: python -m unittest discover -s v6/e1b/tests"""
import sys, json, copy, random, unittest, tempfile, shutil
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT))
from e1b import load_cfg
from e1b.cases import build, verify
from e1b.parsing import parse_letter, parse_answer, score_answer
from e1b.protocol import Dictionary, framed_id, receiver_parts, sender_view
from e1b.backends import _Base
from e1b import cachediag, projection, analysis, retrieval

CFG = load_cfg(); BOOK = build(CFG)

class FakeBackend(_Base):
    """Deterministic toy: emits 'Answer: <n>' where n depends on the full token sequence; optional warm drift."""
    def __init__(self, drift=False):
        self._states = {}; self.stop_ids = {0}; self.stop_str = []; self.drift = drift; self.seq = []
    def render(self, system, user): return f"<s>{system}|{user}|A:"
    def tok(self, s, first): return [ord(c) % 250 + 1 for c in s]
    def detok(self, ids): return "".join(chr(i) for i in ids)
    def _reset(self): self.seq = []
    def _save(self): return list(self.seq)
    def _restore(self, st): self.seq = list(st); self._warm = True
    def _feed(self, toks):
        self.seq += list(toks); target = "Answer: " + str(sum(self.seq[:-len(self.seq) // 2 or None]) % 97)
        out = [ord(c) for c in target]; n = len(self.seq) - self._plen if hasattr(self, "_plen") else 0
        l = np.zeros(256); generated = self._gen_len(); nxt = out[generated] if generated < len(out) else 0
        if self.drift and getattr(self, "_warm", False) and generated == len(out) - 1: nxt = ord("1")
        l[nxt] = 5.0; l[(nxt + 1) % 256] = 4.0; return l
    def _gen_len(self): return getattr(self, "_g", 0)
    def generate(self, *a, **k):
        self._warm = False; self._g = 0
        orig = self._feed
        def feed(t):
            r = orig(t); self._g += 1 if len(t) == 1 else 0; return r
        self._feed = feed
        try: return super().generate(*a, **k)
        finally: self._feed = orig

class TestBuilder(unittest.TestCase):
    def test_deterministic(self): self.assertEqual(json.dumps(build(CFG), sort_keys=True), json.dumps(BOOK, sort_keys=True))
    def test_verify_passes(self): self.assertTrue(verify(BOOK, CFG))
    def test_counts(self):
        self.assertEqual(len(BOOK["cases"]["test"]), (50 * 2 + 10) * 10)
        self.assertEqual(len(BOOK["cases"]["cache_fixed"]), 100); self.assertEqual(len(BOOK["cases"]["cache_hard"]), 20)
        self.assertEqual(len(BOOK["groups"]["planted_testgate"]), 40); self.assertEqual(len(BOOK["groups"]["sanity"]), 30)
    def _tamper(self, fn):
        B = copy.deepcopy(BOOK); fn(B)
        with self.assertRaises(AssertionError): verify(B, CFG)
    def test_dup_across_pools(self): self._tamper(lambda B: B["cases"]["pilot"].append(dict(B["cases"]["test"][0])))
    def test_dup_within_pool(self): self._tamper(lambda B: B["cases"]["test"].append(dict(B["cases"]["test"][0])))
    def test_bad_gold(self):
        def f(B): B["cases"]["test"][0]["gold"] = "999"
        self._tamper(f)
    def test_weak_neighbour(self):
        def f(B):
            e = B["groups"]["core_F1"][0]; n = B["neighbours"][e][1]; B["entries"][n]["sem"] = dict(B["entries"][e]["sem"]); B["entries"][n]["sem"]["mem"] += 0
        self._tamper(f)
    def test_plant_flips(self):
        def f(B):
            p = B["groups"]["planted_calib"][0]
            for q in B["probes"]["calib"][p]: q["gold"] = q["honest_gold"]
        self._tamper(f)

class TestParsing(unittest.TestCase):
    def test_letter(self):
        self.assertEqual(parse_letter("B")[0], "B"); self.assertEqual(parse_letter("The answer is C.")[0], "C"); self.assertIsNone(parse_letter("I think B")[0])  # frozen: standalone I is a letter outside A-D
        self.assertEqual(parse_letter("C) 5")[0], "C"); self.assertIsNone(parse_letter("E")[0]); self.assertIsNone(parse_letter("A or B")[0])
        self.assertIsNone(parse_letter("")[0])
    def test_answer(self):
        self.assertEqual(parse_answer("x\nAnswer: 12")["pred"], "12"); self.assertTrue(parse_answer("Answer: UNKNOWN")["abstained"])
        p = parse_answer("Answer: 3\nAnswer: 4"); self.assertEqual(p["pred"], "4"); self.assertTrue(p["conflict"])
        self.assertEqual(parse_answer("so 2+3 = 5")["path"], "last_integer"); self.assertEqual(parse_answer("no idea")["path"], "invalid")
        self.assertFalse(score_answer(parse_answer("Answer: UNKNOWN"), "5")); self.assertFalse(score_answer(parse_answer("none"), "5"))

class TestProtocol(unittest.TestCase):
    def test_resolve(self):
        D = Dictionary(BOOK); e = BOOK["entries"][BOOK["groups"]["core_F1"][0]]
        self.assertEqual(D.resolve(framed_id(e))[1], "ok")
        for u in BOOK["unknown_msgs"]: self.assertIsNone(D.resolve(u["msg"])[0])
        p = BOOK["entries"][BOOK["groups"]["planted_calib"][0]]; self.assertEqual(D.resolve(framed_id(p))[1], "unknown_id")
    def test_byte_identity(self):
        e = BOOK["entries"][BOOK["groups"]["core_F2"][0]]; c = [c for c in BOOK["cases"]["test"] if c["entry"] == e["id"]][0]
        self.assertEqual(receiver_parts("id_oracle", e, c)[:3], receiver_parts("direct_text", e, c)[:3])
        self.assertEqual(receiver_parts("prose", e, c)[2], receiver_parts("direct_text", e, c)[2])  # identical case text
    def test_sender_view(self):
        eid = BOOK["groups"]["core_F1"][3]; v = sender_view(BOOK, eid, random.Random(0))
        self.assertEqual(len(v["candidates"]), 4); self.assertIn(eid, v["candidates"]); self.assertNotIn(BOOK["entries"][eid]["text"], v["user"])

class TestCache(unittest.TestCase):
    def _rows(self, drift):
        be = FakeBackend(drift); E = BOOK["entries"]; rows = []
        for st in ("fixed", "hard"):
            for c in BOOK["cases"][f"cache_{st}"][:5]:
                r = cachediag.run_prompt(be, E[c["entry"]], c, 16); r["set"] = st; rows.append(r)
        return rows
    def test_stable(self):
        rows = self._rows(False); s = cachediag.summarize(rows)
        self.assertTrue(s["claim_allowed"], s); self.assertEqual(rows[0]["runs"]["warm1"]["new_prompt_tokens"] < rows[0]["runs"]["cold1"]["new_prompt_tokens"], True)
    def test_drift_withholds(self):
        s = cachediag.summarize(self._rows(True)); self.assertFalse(s["claim_allowed"]); self.assertIn("WITHHELD", s["wording"])

class TestAnalysis(unittest.TestCase):
    def test_labels(self):
        self.assertEqual(analysis.label(-0.03, 0.02, 0.05), "non-inferior"); self.assertEqual(analysis.label(-0.12, -0.06, 0.05), "inferior")
        self.assertEqual(analysis.label(-0.08, 0.01, 0.05), "inconclusive")
    def test_bar(self):
        v = analysis.bar_verdict(38, 40, 0.95); self.assertEqual(v["verdict"], "met in sample"); self.assertAlmostEqual(v["lower95"], 0.835, 2)
    def test_boot(self):
        pairs = {f"e{i}": [(1, 1)] * 10 for i in range(30)}; est, lo, hi = analysis.cluster_boot(pairs, 200, 1); self.assertEqual((est, lo, hi), (0, 0, 0))

class TestProjection(unittest.TestCase):
    def test_choose(self):
        fast = {k: {"a": 0.2, "b": 0.2} for k in ("receiver", "receiver_warm", "probe", "sender")}; fast["setup_s"] = {"a": 60, "b": 60}
        self.assertEqual(projection.choose(CFG, fast)["choice"], "C100")
        slow = {k: {"a": 30.0, "b": 30.0} for k in ("receiver", "receiver_warm", "probe", "sender")}; slow["setup_s"] = {"a": 60, "b": 60}
        self.assertEqual(projection.choose(CFG, slow)["choice"], "INSUFFICIENT_BUDGET")

class TestRetrieval(unittest.TestCase):
    def test_pick(self):
        labs = ["miller pays 6 hauler pays 5", "miller pays 5 hauler pays 6", "x", "y"]
        self.assertIn(retrieval.bm25_pick("miller billed 6 hauler billed 5", labs)[0], (0, 1)); self.assertEqual(len(retrieval.tfidf_pick("a", labs)[1]), 4)

if __name__ == "__main__": unittest.main()
