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
        self.assertEqual(len(BOOK["cases"]["cache_fixed"]), 100); self.assertEqual(len(BOOK["cases"]["cache_stress"]), 20)
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
        for st in ("fixed", "stress"):
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
    def test_regex_order_aware(self):
        labs = ["miller pays 5 hauler pays 6", "miller pays 6 hauler pays 5", "6 7", "x"]
        self.assertEqual(retrieval.regex_pick("miller billed 6, hauler billed 5", labs)[0], 1)
        self.assertEqual(retrieval.regex_pick("miller billed six, hauler billed five", labs)[0], 0)   # spelled -> no signal, tie -> first

class TestA2(unittest.TestCase):
    def test_hard_share(self):
        from e1b.cases import entries_for_config
        E = BOOK["entries"]
        for c in ("C60", "C100"):
            for f, ids in entries_for_config(BOOK, CFG, c).items():
                self.assertGreaterEqual(sum("msg_style" in E[i] for i in ids) / len(ids), 1 / 3)
    def test_ntype_recorded(self):
        for v in BOOK["neighbours"].values(): self.assertTrue(all(BOOK["entries"][n]["ntype"] in ("swap", "shift", "swap+shift") for n in v))
    def test_unstated_probes(self):
        from e1b.cases import NOT_STATED
        p = BOOK["probes"]["calib"][BOOK["groups"]["core_F1"][0]]
        u = [x for x in p if x["kind"] == "unstated"]; self.assertTrue(u)
        self.assertTrue(all(x["options"]["ABCD".index(x["gold"])] == NOT_STATED for x in u))
    def test_leak_rule_kind_baseline(self):
        from e1b.stages import leak_rule
        obs = {"F1-mem-v0": [1] * 30 + [0] * 30, "F1-mem-v1": [0] * 54 + [1] * 6, "F1-mem-v2": [0] * 54 + [1] * 6}
        r = leak_rule(obs, CFG); self.assertEqual(r["flagged"], ["F1-mem-v0"]); self.assertEqual(r["kind_level_leak"], [])
    def test_coldsplit_and_logging(self):
        be = FakeBackend(); E = BOOK["entries"]; c = BOOK["cases"]["cache_fixed"][0]
        r = cachediag.run_prompt(be, E[c["entry"]], c, 16)
        self.assertIn("cold_coldsplit", r["cmp"]); self.assertEqual(r["runs"]["coldsplit"]["mode"], "coldsplit")
        self.assertEqual(len(r["runs"]["cold1"]["prompt_sha"]), 64); self.assertEqual(len(r["runs"]["cold1"]["system_turn_sha"]), 64)
        self.assertIn(r["runs"]["cold1"]["answer_gap_source"], ("after_answer_line", "first_token_fallback"))

class TestGPTCounterexamples(unittest.TestCase):
    """Regression tests for GPT's code review r1 counterexamples (6e2636d)."""
    def test_gate_perfect_reader_rejects_planted(self):
        from e1b.analysis import gate_decision
        E = BOOK["entries"]; d = Path(tempfile.mkdtemp())
        try:
            hon = BOOK["groups"]["core_F1"][:10] + BOOK["groups"]["core_F2"][:10]
            for kind, pl in (("calib", BOOK["groups"]["planted_calib"][:20]), ("testgate", BOOK["groups"]["planted_testgate"][:20])):
                for m in ("a", "b"):
                    with open(d / f"{kind}_{m}.jsonl", "w") as f:
                        for eid in hon + pl:
                            for p in BOOK["probes"][kind][eid]:   # perfect reader of the SHOWN text
                                f.write(json.dumps(dict(entry=eid, template=p["template"], letter=p["gold"], gold=p["gold"], honest_gold=p["honest_gold"],
                                                        correct=True, honest_correct=p["gold"] == p["honest_gold"])) + "\n")
            (d / "manip.jsonl").write_text("")
            g = gate_decision(d, ["a", "b"], CFG, E)
            self.assertEqual(g["calib"]["honest_accept"]["point"], 1.0); self.assertEqual(g["calib"]["planted_reject"]["point"], 1.0)
            self.assertEqual(g["testgate_vs_repo_target"]["planted_reject"]["point"], 1.0)
        finally: shutil.rmtree(d)
    def test_cross_process_reproducible(self):
        import subprocess, os
        code = ("import json,hashlib,sys;sys.path.insert(0,%r);from e1b import load_cfg;from e1b.cases import build;"
                "print(hashlib.sha256(json.dumps(build(load_cfg()),sort_keys=True).encode()).hexdigest())") % str(ROOT)
        hs = {subprocess.run([sys.executable, "-c", code], env=dict(os.environ, PYTHONHASHSEED=s), capture_output=True, text=True, check=True).stdout
              for s in ("1", "2", "77")}
        self.assertEqual(len(hs), 1, hs)
    def test_verify_catches_role_swap(self):
        from e1b import sha256_text
        def swap(B):
            e = B["entries"][B["groups"]["core_F1"][0]]; a, b = e["sem"]["mem"], e["sem"]["non"]
            e["text"] = e["text"].replace(f"charged {a} credits", "charged @@ credits").replace(f"charged {b} credits", f"charged {a} credits").replace("charged @@ credits", f"charged {b} credits")
            e["hash"] = sha256_text(e["text"])
        B = copy.deepcopy(BOOK); swap(B)
        with self.assertRaises(AssertionError): verify(B, CFG)
    def test_validator_empty_results_not_pass(self):
        from e1b.validate import run
        d = Path(tempfile.mkdtemp())
        try:
            shutil.copy(ROOT / "config_e1b.json", d); (d / "data").mkdir()
            (d / "data" / "cases_e1b.json").write_text(json.dumps(BOOK))
            from e1b import sha256_text; (d / "data" / "cases_e1b.sha256").write_text(sha256_text((d / "data" / "cases_e1b.json").read_text()) + "\n")
            self.assertEqual(run(d), 1); self.assertEqual(run(d, inputs_only=True), 0)
            (d / "results" / "B1").mkdir(parents=True); self.assertEqual(run(d, inputs_only=True), 1)   # started, no marker -> broken
            (d / "results" / "B1" / "BUDGET_EXHAUSTED").write_text("x"); self.assertEqual(run(d, inputs_only=True), 0)
            (d / "results" / "A").mkdir(); (d / "results" / "A" / "PROJECTION_EXCEEDS_BUDGET").write_text("x")
            self.assertEqual(run(d, inputs_only=True), 0)   # Stage A's pre-registered projection stop is an explicit stop marker
        finally: shutil.rmtree(d)
    def test_cache_none_is_not_agreement(self):
        class NoneBE(FakeBackend):
            def generate(self, *a, **k):
                r = super().generate(*a, **k); r["text"] = "no answer line"; return r
        E = BOOK["entries"]; rows = []
        for st in ("fixed", "stress"):
            for c in BOOK["cases"][f"cache_{st}"][:3]:
                r = cachediag.run_prompt(NoneBE(), E[c["entry"]], c, 16); r["set"] = st; rows.append(r)
        s = cachediag.summarize(rows); self.assertFalse(s["claim_allowed"]); self.assertGreater(s["fixed"]["invalid_runs"], 0)
    def test_resolve_uses_membership_and_gate(self):
        E = BOOK["entries"]; h = BOOK["groups"]["core_F1"][0]; n = BOOK["neighbours"][h][0]; p = BOOK["groups"]["planted_calib"][0]
        D = Dictionary(BOOK)
        self.assertEqual(D.resolve(framed_id(E[n]))[1], "ok"); self.assertEqual(D.resolve(framed_id(E[p]))[1], "unknown_id")
        self.assertEqual(Dictionary(BOOK, accepted={h}).resolve(framed_id(E[n]))[1], "rejected_by_gate")
        self.assertEqual(Dictionary(BOOK, accepted={h}).resolve(framed_id(E[h]))[1], "ok")
    def test_canaries_per_record(self):
        from e1b.stages import canary_regressions
        ref = {"a": dict(pred="6", correct=True), "b": dict(pred="5", correct=False)}
        now = {"a": dict(pred="7", correct=False), "b": dict(pred="9", correct=True)}   # same total, different records
        self.assertEqual(canary_regressions(ref, now), ["a", "b"]); self.assertEqual(canary_regressions(ref, ref), [])
    def test_budget_ledger_cumulative(self):
        import e1b.stages as S
        d = Path(tempfile.mkdtemp()); old = S.RES; S.RES = d
        try:
            s1 = S.Stage("B0", 1.0, CFG); s1.prior_s = 1000.0; s1.save_ledger()
            s2 = S.Stage("B0b", 1.0, CFG, alloc="B0"); self.assertGreaterEqual(s2.prior_s, 1000.0)
            import atexit; atexit.unregister(s1.save_ledger); atexit.unregister(s2.save_ledger)
        finally: S.RES = old; shutil.rmtree(d, ignore_errors=True)
    def test_gguf_pin_mismatch_refused(self):
        from e1b.backends import verify_gguf
        import hashlib
        d = Path(tempfile.mkdtemp()); p = d / "x.gguf"; p.write_bytes(b"abc")
        try:
            self.assertEqual(verify_gguf(str(p), hashlib.sha256(b"abc").hexdigest()), hashlib.sha256(b"abc").hexdigest())
            with self.assertRaises(RuntimeError): verify_gguf(str(p), "0" * 64)
        finally: shutil.rmtree(d)
    def test_pins_complete(self):
        for k, m in CFG["models"]["stageB"].items():
            self.assertEqual(len(m["revision"]), 40); self.assertEqual(len(m["gguf_revision"]), 40)
            self.assertTrue(m["gguf_sha256"] and all(len(v) == 64 for v in m["gguf_sha256"].values()))
    def test_pilot_and_neighbours_disjoint_from_test(self):
        test_e = {c["entry"] for c in BOOK["cases"]["test"]}
        for f in CFG["families_core"]:
            for eid in BOOK["groups"][f"pilot_{f}"]:
                self.assertNotIn(eid, test_e); self.assertEqual(len(BOOK["neighbours"][eid]), 3)
        for eid in BOOK["groups"]["core_F1"]:
            for nid in BOOK["neighbours"][eid]: self.assertIn(nid, BOOK["probes"]["calib"])

class TestA3(unittest.TestCase):
    """gpt_code_2 regressions."""
    def test_b0b_replacement_full_leak_dropped(self):
        from e1b.stages import replacement_leaks
        self.assertTrue(replacement_leaks([1] * 60, 1.0, CFG))     # was kept under the old rule (threshold 115%)
        self.assertTrue(replacement_leaks([1] * 25 + [0] * 35, 0.30, CFG))   # 0.417 > 0.40 kind-level bar
        self.assertFalse(replacement_leaks([1] * 15 + [0] * 45, 0.30, CFG))
        self.assertTrue(replacement_leaks([], 0.25, CFG))
    def test_b0b_budget_check_in_loop(self):
        import inspect, e1b.stages as S
        src = inspect.getsource(S.stage_B0b); self.assertIn("S.check_budget()", src)
    def test_regex_report_uses_frozen_b3_views(self):
        from e1b.stages import regex_report
        r = regex_report(BOOK, CFG)
        self.assertEqual({k: (v["correct"], v["n"]) for k, v in r.items()},
                         {"plain": (70, 70), "reordered": (0, 13), "spelled": (5, 14), "derived": (8, 13)})
        self.assertEqual(r["spelled"]["tie_guess"], 14)
    def test_probe_latency_allowance(self):
        self.assertAlmostEqual(projection.probe_latency_allowance(CFG, "C60"), 0.446, 3)
        self.assertAlmostEqual(projection.probe_latency_allowance(CFG, "C100"), 0.290, 3)
    def test_unknown_messages_distinct(self):
        self.assertEqual(len({u["msg"] for u in BOOK["unknown_msgs"]}), CFG["unknown_id_messages"])

if __name__ == "__main__": unittest.main()
