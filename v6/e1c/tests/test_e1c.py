import sys, os, json, re, shutil, tempfile, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT.parent / "e1b" / "tests"))
from e1c import load_cfg, DATA, E1B
from e1c import book as BK, verifier as V, analysis as A, stages as ST
from e1b.parsing import parse_letter, parse_letter_a10
from e1b.protocol import render_message
from test_e1b import FakeBackend

class Terms(unittest.TestCase):
    def test_draft_models_and_criteria(self):
        X = load_cfg()["e1c"]; s = json.dumps(X).lower()
        self.assertEqual(X["status"], "draft"); self.assertEqual(X["pair"], ["qwen7b", "falcon7b"])
        for bad in ("mistral", "llama", "gemma"): self.assertNotIn(bad, s)
        c = X["criteria"]
        self.assertEqual((c["margin"], c["coverage_min"], c["byte_saving_min"], c["breakeven_max_messages"], c["bootstrap_resamples"], c["wrong_pass_max_dev"]),
                         (0.05, 0.85, 0.30, 1000, 2000, 0.02))
        self.assertEqual(X["caps_h"]["D1"], 0.5); self.assertEqual(X["max_starts"], 2); self.assertEqual(X["sizes"]["test"]["core_per_family"] * 2, 240)
        self.assertFalse(set(X["seeds"]["dev"].values()) & set(X["seeds"]["test"].values()))
        self.assertIsNone(X["test_book_sha256"])

class Parser(unittest.TestCase):
    def test_archived_B_F1_failure(self):
        """Archived E1b B3 falcon7b replies rejected by the frozen parser (e.g. 'B) F1') parse under A10."""
        rows = [json.loads(l) for l in open(E1B / "results" / "B3" / "select_falcon7b.jsonl")]
        rej = [r for r in rows if r["letter"] is None]; self.assertGreater(len(rej), 0)
        self.assertTrue(any(r["raw"].strip().startswith("B) F1") for r in rows))
        for r in rej: self.assertIn(parse_letter_a10(r["raw"])[0], list("ABCD"), r["raw"])
        self.assertIsNone(parse_letter("B) F1")[0]); self.assertEqual(parse_letter_a10("B) F1")[0], "B")
        self.assertIsNone(parse_letter_a10("F1")[0]); self.assertIsNone(parse_letter_a10("A or B")[0])

class Book(unittest.TestCase):
    def test_dev_book_pinned_fresh_balanced_unique(self):
        B = BK.load_book(load_cfg(), "dev")   # sha + verify + freshness vs E1b frozen & A9 + branch balance + unique core
        ids = BK.core_ids(B, 40); self.assertEqual(len(ids), 80); self.assertEqual(len(BK.cases_for(B, ids)), 320)
        self.assertEqual(len({B["entries"][k]["text"] for k in ids}), 80)
    def test_test_book_refused_before_freeze(self):
        with self.assertRaises(SystemExit): BK.build_book(load_cfg(), "test")
        self.assertFalse((DATA / "book_test.json").exists())

class Verifier(unittest.TestCase):
    def setUp(self): self.B = BK.load_book(load_cfg(), "dev"); self.E = self.B["entries"]
    def ent(self, fam): return self.E[self.B["e1c_core"][fam][0]]
    def test_exact_spec_matches_true_not_neighbours(self):
        for fam in ("F1", "F2"):
            for eid in self.B["e1c_core"][fam]:
                e = self.E[eid]; line = " ".join(f"{k}={v}" for k, v in V.expected_spec(e).items())
                spec, why = V.parse_spec(fam, "Here:\n" + line); self.assertEqual(why, "ok"); self.assertTrue(V.matches(spec, e)[0])
                for nb in self.B["neighbours"][eid]: self.assertFalse(V.matches(spec, self.E[nb])[0], nb)
    def test_prompt_sees_only_prose(self):
        e = self.ent("F1"); s, p, u = V.verifier_parts("F1", render_message(e))
        self.assertNotIn(e["id"], s + p + u); self.assertNotIn("Candidates", u)
    def test_format_failures(self):
        self.assertEqual(V.parse_spec("F1", "MEMBER=3 NONMEMBER=5")[1], "format")
        self.assertEqual(V.parse_spec("F1", "GROUP=gold MEMBER=three NONMEMBER=5")[1], "non_integer_MEMBER")
        self.assertEqual(V.parse_spec("F2", "GIVER=The Miller GIVER_RATE=4 credits TAKER=hauler TAKER_RATE=2")[0],
                         dict(GIVER="miller", GIVER_RATE=4, TAKER="hauler", TAKER_RATE=2))
        self.assertFalse(V.matches(None, self.ent("F1"))[0])

class Analysis(unittest.TestCase):
    def test_label_rule_A12(self):
        self.assertEqual(A.label(-0.04, 0.1, 0.05), "non-inferior"); self.assertEqual(A.label(-0.2, -0.06, 0.05), "inferior")
        self.assertEqual(A.label(-0.133, -0.004, 0.05), "inconclusive")
    def test_bootstrap_stratified_deterministic(self):
        by = dict(F1=[0, 0, 0.25, -0.25], F2=[0, -0.5, 0, 0])
        self.assertEqual(A.strat_boot(by, 2000, 7), A.strat_boot(by, 2000, 7))
        lo, hi = A.strat_boot(by, 2000, 7); self.assertLessEqual(lo, A.point(by)); self.assertGreaterEqual(hi, A.point(by))
        self.assertEqual(A.strat_boot(dict(F1=[0.1] * 5, F2=[0.1] * 5), 200, 1), (0.1, 0.1))
    def test_unpaired_rejected(self):
        with self.assertRaises(ValueError): A.entry_diffs([dict(fam="F1", entry="x", cond="hybrid", correct=True)])

class Fake(FakeBackend):
    """Sender: 'B) F1'-style reply naming the TRUE candidate; verifier: exact spec (off by one for `bad` entries);
    receiver: the toy arithmetic output."""
    def __init__(self, B, bad=()):
        super().__init__(False); self.info = dict(backend="fake"); self.bad = set(bad)
        self.msg = {render_message(B["entries"][k]): B["entries"][k] for f in ("F1", "F2") for k in B["e1c_core"][f]}
    def _fix(self, j, r):
        s, p, u = j
        if u.startswith("Message:") and "Candidates:" in u:
            e = self.msg[u.split("\n\nCandidates:")[0][len("Message:\n"):]]
            L = next(l[0] for l in u.splitlines() if re.match(r"^[ABCD]\) ", l) and l[3:].startswith(e["id"] + "@"))
            return dict(r, text=f"{L}) F1")
        if u.startswith("Message:"):
            e = self.msg[u.split("\n\nReply in exactly")[0][len("Message:\n"):]]; sp = dict(V.expected_spec(e))
            if e["id"] in self.bad: k = [k for k in sp if isinstance(sp[k], int)][0]; sp[k] += 1
            return dict(r, text=" ".join(f"{k}={v}" for k, v in sp.items()))
        return r
    def generate(self, s, p, u, max_new, warm=False, mode=None): return self._fix((s, p, u), super().generate(s, p, u, max_new, warm=warm, mode=mode))
    def generate_batch(self, jobs, max_new): return [self._fix(j, r) for j, r in zip(jobs, super().generate_batch(jobs, max_new))]

class DryRun(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()); self.old = (ST.RES, ST.load_B, ST.require_canaries, ST.code_hash)
        ST.RES = self.tmp / "results"; ST.RES.mkdir(); os.environ["E1B_ALLOW_NO_GPU"] = "1"
        self.cfg = load_cfg(); self.B = BK.load_book(self.cfg, "dev"); self.cfg["e1c"]["sizes"]["dev"] = dict(core_per_family=6, receiver_entries_per_family=3)
        bad = [self.B["e1c_core"]["F2"][1]]
        ST.load_B = lambda name, cfg, S: (Fake(self.B, bad), "fake"); ST.require_canaries = lambda *a: None
        h = self.old[3](); ST.code_hash = lambda: h
        self.pin = ROOT / "CODE_HASH.txt"; self.had = self.pin.read_text() if self.pin.exists() else None; self.pin.write_text(h + "\n")
    def tearDown(self):
        ST.RES, ST.load_B, ST.require_canaries, ST.code_hash = self.old; os.environ.pop("E1C_GO", None)
        if self.had is None: self.pin.unlink()
        else: self.pin.write_text(self.had)
        shutil.rmtree(self.tmp, ignore_errors=True)
    def _run(self, name):
        try: ST.run(self.cfg, name)
        except SystemExit as e: return e.code
    def test_gates(self):
        self.assertEqual(self._run("D1"), 14)
        os.environ["E1C_GO"] = "T1"; self.assertEqual(self._run("T1"), 13)
        os.environ["E1C_GO"] = "D1"; self.assertEqual(self._run("T1"), 14)
    def test_code_hash_gate(self):
        os.environ["E1C_GO"] = "D1"; self.pin.write_text("0" * 64 + "\n"); self.assertEqual(self._run("D1"), 16)
    def test_d1_dry_run(self):
        os.environ["E1C_GO"] = "D1"; self.assertIn(self._run("D1"), (None, 0))
        S = json.load(open(ST.RES / "D1" / "summary.json"))
        for m in ("qwen7b", "falcon7b"):
            s = S["selection"][m]; self.assertEqual(s["n"], 12); self.assertEqual(s["pick_acc"], 1.0); self.assertEqual(s["sender_invalid"], 0)
            self.assertEqual(s["correct_pick_rejected"], 1); self.assertAlmostEqual(s["coverage"], 11 / 12)
        for d, r in S["directions"].items():
            self.assertEqual(r["n_entries"], 6); self.assertEqual(r["n_items"], 24); self.assertEqual(r["wrong_pick_accepted"], 0)
            rows = [json.loads(l) for l in open(ST.RES / "D1" / f"exchange_{d}.jsonl")]
            fb = [x for x in rows if x["cond"] == "hybrid" and x["sent"] == "prose"]; self.assertEqual(len(fb), 4)
            for x in fb:
                tw = [y for y in rows if y["cond"] == "prose" and y["case"] == x["case"]][0]
                self.assertEqual((x["payload_bytes"], x["pred"], x["shared_n"]), (tw["payload_bytes"], tw["pred"], 2))
        self.assertIn("sizing", S); self.assertNotIn("verdict", S); self.assertEqual(self._run("D1"), 0)
    def test_start_cap(self):
        os.environ["E1C_GO"] = "D1"; d = ST.RES / "D1"; d.mkdir(); json.dump(dict(starts=2, cap_h=0.5), open(d / "e1c_state.json", "w"))
        self.assertEqual(self._run("D1"), 17)

if __name__ == "__main__": unittest.main()
