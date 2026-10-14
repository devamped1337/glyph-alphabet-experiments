"""A9 (DRAFT): launch gate, fresh pinned book, pre-registered ladder + caps, start limit, batch rule, no reuse,
and a full fake-backend dry run of B1c -> B1 -> B2 -> B3 -> validator. No model, no GPU, no network."""
import sys, os, json, shutil, tempfile, unittest, copy, math
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tests"))
from e1b import load_cfg, norm, sha256_text
from e1b import a9 as A9
import e1b.stages as S
from test_e1b import FakeBackend

class Fake(FakeBackend):
    """Fake pair model; probe calls (<= 4 new tokens) answer a valid letter so the B1c probe path is exercised."""
    def __init__(self, name="fake"): super().__init__(False); self.info = dict(backend="fake"); self.name = name
    def _letter(self, r, max_new):
        if max_new <= 4: r = dict(r, text="B")
        return r
    def generate(self, system, prefix_user, suffix_user, max_new, warm=False, mode=None):
        return self._letter(super().generate(system, prefix_user, suffix_user, max_new, warm=warm, mode=mode), max_new)
    def generate_batch(self, jobs, max_new): return [self._letter(r, max_new) for r in super().generate_batch(jobs, max_new)]

ATTR = "Falcon3-7B-Instruct results were produced using artificial intelligence technology from the Technology Innovation Institute (TII Falcon License)."

class A9Config(unittest.TestCase):
    def test_draft_and_terms(self):
        X = load_cfg()["a9"]
        self.assertEqual(X["status"], "draft"); self.assertEqual(X["pair"], ["qwen7b", "falcon7b"]); self.assertEqual(X["reuse"], [])
        self.assertNotIn("mistral", json.dumps(X).lower()); self.assertEqual(X["attribution"], ATTR); self.assertIn("POST-HOC", X["label"])
    def test_ladder_choice_from_b0x_timings(self):
        cfg = load_cfg(); X = cfg["a9"]; r = A9.choose(cfg, A9.pilot_timings(ROOT / "results"))
        self.assertEqual(r["choice"], X["frozen_level"])   # the frozen level is the mechanical ladder result
        last = [x for x in r["report"] if x["fits"]][0]
        self.assertEqual({k: v["cap_h"] for k, v in last["stages"].items()}, X["caps_h"])
        self.assertLessEqual(sum(X["caps_h"].values()), X["total_cap_h"])
        self.assertTrue(all(not x["fits"] for x in r["report"][:-1]))   # every earlier (larger) level was tried and does not fit
        for x in r["report"]:
            for v in x["stages"].values(): self.assertLessEqual(v["projected_h"], X["headroom"] * v["cap_h"] + 1e-9)
    def test_entry_pass_prob(self):
        self.assertAlmostEqual(A9.entry_pass_prob(24, 0.9, 0.90), 0.564, places=3)
        self.assertAlmostEqual(A9.entry_pass_prob(20, 0.9, 0.90), 0.677, places=3)
    def test_batch_rule(self):
        cfg = load_cfg(); K = [f"a|{i}" for i in range(60)] + [f"p|{i}" for i in range(60)]; good = [(k, "1", "1", True) for k in K]
        ex = dict(models=["a", "b"], keys=K)
        ok = A9.batch_rule(cfg, {"a": good, "b": good}, ex); self.assertTrue(ok["pass_"]); self.assertEqual(ok["batch_size"], 8)
        one_off = good[:-1] + [(K[-1], "1", "2", False)]
        self.assertFalse(A9.batch_rule(cfg, {"a": one_off, "b": good}, ex)["pass_"])
        tok_diff = [(k, "1", "1", False) for k in K]   # full-token disagreement is a diagnostic only
        self.assertTrue(A9.batch_rule(cfg, {"a": tok_diff, "b": good}, ex)["pass_"])
    def test_batch_rule_regressions(self):
        """GPT A9 bug: 60 x (None, None) and an empty mapping must FAIL; so must missing models, missing or duplicate keys."""
        cfg = load_cfg(); K = [f"k{i}" for i in range(60)]
        nones = [(k, None, None, True) for k in K]
        self.assertFalse(A9.batch_rule(cfg, {"a": nones, "b": nones})["pass_"])
        self.assertFalse(A9.batch_rule(cfg, {})["pass_"])
        self.assertFalse(A9.batch_rule(cfg, {"a": [], "b": []})["pass_"])
        good = [(k, "1", "1", True) for k in K]
        self.assertFalse(A9.batch_rule(cfg, {"a": good}, dict(models=["a", "b"], keys=K))["pass_"])
        self.assertFalse(A9.batch_rule(cfg, {"a": good[:-1], "b": good}, dict(models=["a", "b"], keys=K))["pass_"])
        self.assertFalse(A9.batch_rule(cfg, {"a": good + good[:1], "b": good})["pass_"])

class A9Book(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = load_cfg(); cls.old = json.load(open(ROOT / "data" / "cases_e1b.json")); cls.B = A9.get_book(cls.cfg)
    def test_pinned_and_deterministic(self):
        self.assertEqual(sha256_text(open(ROOT / "data" / "cases_e1b_a9.json").read()), self.cfg["a9"]["book_sha256"])
        self.assertEqual(json.dumps(A9.build_book(self.cfg, self.old)), open(ROOT / "data" / "cases_e1b_a9.json").read())
    def test_fresh_vs_frozen_book(self):
        self.assertTrue(A9.check_fresh(self.B, self.old))
        old_t = {norm(c["text"]) for cs in self.old["cases"].values() for c in cs}
        self.assertFalse(old_t & {norm(c["text"]) for c in self.B["cases"]["test"]})
        self.assertNotEqual(self.B["meta"]["seeds"], self.old["meta"]["seeds"])
        self.assertEqual(self.B["cases"]["canary"], self.old["cases"]["canary"])   # only the canary pool is shared
        self.assertEqual(len(self.B["cases"]["test"]), (50 * 2 + 10) * self.cfg["a9"]["frozen_level"]["cases_per_entry"])
    def test_branch_balance(self):
        T = self.cfg["a9"]["frozen_level"]["cases_per_entry"]; self.assertTrue(A9.check_branches(self.B, T))
        B = copy.deepcopy(self.B); c = B["cases"]["test"][0]; k = dict(F1="mem", F2="ask_y", F3L="perm")[c["fam"]]; c["meta"][k] = not c["meta"][k]
        with self.assertRaises(AssertionError): A9.check_branches(B, T)
    def test_ladder_drops_f3l_before_cases(self):
        L = load_cfg()["a9"]["ladder"]; i = next(i for i, x in enumerate(L) if not x["f3l"])
        self.assertTrue(all(x["cases_per_entry"] == 10 for x in L[:i + 1])); self.assertTrue(all(x["cases_per_entry"] % 2 == 0 for x in L))
    def test_tampered_reuse_fails(self):
        B = copy.deepcopy(self.B); B["cases"]["test"][0] = dict(B["cases"]["test"][0], text=self.old["cases"]["test"][0]["text"])
        with self.assertRaises(AssertionError): A9.check_fresh(B, self.old)
        B = copy.deepcopy(self.B); eid = B["groups"]["core_F1"][0]; B["entries"][eid] = dict(B["entries"][eid], text=self.old["entries"][self.old["groups"]["core_F1"][0]]["text"])
        with self.assertRaises(AssertionError): A9.check_fresh(B, self.old)

class A9Stages(unittest.TestCase):
    def setUp(self):
        self.old = (S.RES, S.load_B); self.tmp = Path(tempfile.mkdtemp()); self.res = self.tmp / "results"; self.res.mkdir()
        shutil.copytree(ROOT / "results" / "B0x", self.res / "B0x"); shutil.copytree(ROOT / "results" / "B0", self.res / "B0")
        json.dump({}, open(self.res / "B0x" / "canaries_ref.json", "w"))   # fake models: real refs would (correctly) abort on canaries
        shutil.copyfile(ROOT / "config_e1b.json", self.tmp / "config_e1b.json"); (self.tmp / "data").symlink_to(ROOT / "data")
        os.environ["E1B_ALLOW_NO_GPU"] = "1"; os.environ.pop("E1B_GO", None)
        self.calls = []
        def lb(name, cfg, St): self.calls.append(name); return Fake(name), "nf4"
        S.load_B = lb
    def tearDown(self): S.RES, S.load_B = self.old; os.environ.pop("E1B_GO", None); shutil.rmtree(self.tmp, ignore_errors=True); S._A9.clear()
    def _cfg(self, status="frozen"): c = load_cfg(); c["a9"]["status"] = status; return c
    def _run(self, st, cfg, go=True):
        if go: os.environ["E1B_GO"] = st
        else: os.environ.pop("E1B_GO", None)
        S.RES = self.res
        try: S.STAGES[st](cfg); return None
        except SystemExit as e: return e.code
    def test_refuses_draft_and_without_go(self):
        for st in ("B1c", "B1", "B2", "B3"):
            self.assertEqual(self._run(st, self._cfg("draft")), 13)
            self.assertEqual(self._run(st, self._cfg(), go=False), 14)
        os.environ["E1B_GO"] = "B1"; S.RES = self.res
        with self.assertRaises(SystemExit) as cm: S.STAGES["B2"](self._cfg())
        self.assertEqual(cm.exception.code, 14)   # a go for one stage never launches another
        self.assertEqual(self.calls, [])
    def test_order_and_prereqs_before_start(self):
        self.assertEqual(self._run("B1", self._cfg()), 19); self.assertEqual(self._run("B3", self._cfg()), 19)
        self.assertFalse((self.res / "B1" / "a9_state.json").exists())   # no start consumed by a refused prerequisite
        (self.res / "B1c").mkdir(); (self.res / "B1c" / ".done").write_text("x")
        json.dump(dict(pass_=False, batch_size=1), open(self.res / "B1c" / "batch_rule.json", "w"))
        self.assertEqual(self._run("B1", self._cfg()), 16); self.assertFalse((self.res / "B1" / "a9_state.json").exists())
        self.assertEqual(self.calls, [])
    def test_terminal_markers(self):
        for m in ("BUDGET_EXHAUSTED", "NO_ACCESS", "CANARY_FAIL"):
            d = self.res / "B1c"; d.mkdir(exist_ok=True); [x.unlink() for x in d.glob("*")]; (d / m).write_text("x")
            self.assertEqual(self._run("B1c", self._cfg()), 18, m)
        self.assertEqual(self.calls, [])
    def test_access_error_is_terminal(self):
        class GatedRepoError(Exception): pass
        def gated(name, cfg, St): raise GatedRepoError("401 Client Error: gated repo")
        S.load_B = gated; os.environ["E1B_GO"] = "B1c"; S.RES = self.res
        with self.assertRaises(GatedRepoError): S.STAGES["B1c"](self._cfg())
        self.assertTrue((self.res / "B1c" / "NO_ACCESS").exists()); self.assertEqual(self._run("B1c", self._cfg()), 18)
    def test_b2_interrupt_resume_validate(self):
        """GPT A9 bug: a B2 abort at the first model load, then resume, must not duplicate unknown.jsonl rows."""
        import io, contextlib
        from e1b import validate
        cfg = self._cfg()
        for st in ("B1c", "B1"): self.assertIn(self._run(st, cfg), (None, 0), st)
        ok_loader = S.load_B
        def abort(name, cfg, St): sys.exit(9)
        S.load_B = abort; self.assertEqual(self._run("B2", cfg), 9)
        self.assertEqual(len(open(self.res / "B2" / "unknown.jsonl").read().splitlines()), 48)
        S.load_B = ok_loader; self.assertIn(self._run("B2", cfg), (None, 0))
        rows = [json.loads(l) for l in open(self.res / "B2" / "unknown.jsonl")]
        self.assertEqual(len(rows), 48); self.assertEqual(len({r["key"] for r in rows}), 48)
        self.assertEqual(json.load(open(self.res / "B2" / "a9_state.json"))["starts"], 2)
        self.assertIn(self._run("B3", cfg), (None, 0))
        validate.write_manifest(self.tmp); buf = io.StringIO()
        with contextlib.redirect_stdout(buf): rc = validate.run(self.tmp)
        self.assertEqual(rc, 0, [l for l in buf.getvalue().splitlines() if l.startswith("FAIL")])
    def test_b1c_stratified(self):
        cfg = load_cfg(); B = A9.get_book(cfg); a, p = S.b1c_items(B, cfg)
        fa = [B["entries"][c["entry"]]["fam"] for c in a]; fp = [B["entries"][e]["fam"] for e, _ in p]
        self.assertEqual((fa.count("F1"), fa.count("F2")), (30, 30)); self.assertEqual((fp.count("F1"), fp.count("F2")), (30, 30))
        test_t = {c["text"] for c in B["cases"]["test"]}; self.assertFalse(any(c["text"] in test_t for c in a))
    def test_start_limit(self):
        def abort(name, cfg, St): sys.exit(9)
        S.load_B = abort
        self.assertEqual(self._run("B1c", self._cfg()), 9); self.assertEqual(self._run("B1c", self._cfg()), 9)
        self.assertEqual(self._run("B1c", self._cfg()), 17); self.assertTrue((self.res / "B1c" / "ATTEMPT_INCOMPLETE").exists())
        st = json.load(open(self.res / "B1c" / "a9_state.json")); self.assertEqual(st["cap_h"], load_cfg()["a9"]["caps_h"]["B1c"])
    def test_full_dry_run_fresh_and_validator(self):
        import io, contextlib
        from e1b import validate
        cfg = self._cfg(); X = cfg["a9"]; B = A9.get_book(cfg)
        for st in ("B1c", "B1", "B2", "B3"):
            self.assertIn(self._run(st, cfg), (None, 0), st); self.assertTrue((self.res / st / ".done").exists(), st)
        self.assertEqual(sorted(set(self.calls)), ["falcon7b", "qwen7b"])   # both models loaded fresh in every stage
        br = json.load(open(self.res / "B1c" / "batch_rule.json")); self.assertTrue(br["pass_"])
        self.assertEqual(sorted(br["per_model"]), sorted(X["pair"])); self.assertTrue(all(v["n"] == 120 and v["keys_ok"] for v in br["per_model"].values()))
        L = json.load(open(self.res / "budget_ledger.json")); self.assertTrue({"A9_B1c", "A9_B1", "A9_B2", "A9_B3"} <= set(L))
        n = cfg["configs"][X["frozen_level"]["config"]]["core_per_family"] * 2; T = X["frozen_level"]["cases_per_entry"]
        for m in X["pair"]:
            sel = [json.loads(l) for l in open(self.res / "B3" / f"select_{m}.jsonl")]
            self.assertEqual(len(sel), n); self.assertFalse(any(r["fam"] == "F3L" for r in sel))   # L4: F3L not run
        ex = [json.loads(l) for l in open(self.res / "B3" / "exchange_qwen7b_to_falcon7b.jsonl")]; self.assertEqual(len(ex), 2 * n * T)
        self.assertTrue(all(r.get("gated") is False for r in ex if "gated" in r))   # A9 4b: gate dropped, B3 ungated
        self.assertFalse(json.load(open(self.res / "B3" / "summary.json"))["gated"])
        self.assertTrue(any(json.loads(l)["ev"] == "a9_gate_dropped" for l in open(self.res / "B3" / "stage_log.jsonl")))
        tt = {c["text"] for c in B["cases"]["test"]}; self.assertTrue(all(r["key"].split("|", 1)[1] in tt for r in ex))
        old_t = {c["text"] for c in json.load(open(ROOT / "data" / "cases_e1b.json"))["cases"]["test"]}
        self.assertFalse(any(r["key"].split("|", 1)[1] in old_t for r in ex))   # nothing from the old TEST pool
        log = [json.loads(l) for l in open(self.res / "B2" / "stage_log.jsonl")]
        a = [x for x in log if x["ev"] == "a9"][0]; self.assertEqual(a["book_sha256"], X["book_sha256"]); self.assertIn("POST-HOC", a["label"])
        for st in ("B1c", "B1", "B2", "B3"): self.assertEqual(self._run(st, cfg), 0)   # finished stages never re-run
        validate.write_manifest(self.tmp); buf = io.StringIO()
        with contextlib.redirect_stdout(buf): rc = validate.run(self.tmp)
        self.assertEqual(rc, 0, [l for l in buf.getvalue().splitlines() if l.startswith("FAIL")])

if __name__ == "__main__": unittest.main()
