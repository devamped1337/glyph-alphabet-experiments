import sys, os, json, re, shutil, tempfile, unittest, copy
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT.parent / "e1b" / "tests")); sys.path.insert(0, str(ROOT / "tools"))
from e1c import load_cfg, DATA, E1B
from e1c import book as BK, verifier as V, analysis as A, stages as ST
from e1b.parsing import parse_letter, parse_letter_a10
from e1b.protocol import render_message, framed_id
from test_e1b import FakeBackend
import authorise_retry as AR, check_freeze as CF

class Terms(unittest.TestCase):
    def test_draft_models_and_criteria(self):
        X = load_cfg()["e1c"]; s = json.dumps(X).lower()
        self.assertEqual(X["status"], "draft"); self.assertEqual(X["pair"], ["qwen7b", "falcon7b"])
        for bad in ("mistral", "llama", "gemma"): self.assertNotIn(bad, s)
        c = X["criteria"]
        self.assertEqual((c["margin"], c["coverage_min"], c["byte_saving_min"], c["breakeven_max_messages"], c["bootstrap_resamples"], c["wrong_pass_max_dev"]),
                         (0.05, 0.85, 0.30, 1000, 2000, 0.02))
        self.assertEqual(X["caps_h"]["D1"], 0.5); self.assertEqual(X["sizes"]["test"]["core_per_family"] * 2, 240)
        self.assertEqual(X["sizes"]["dev"]["core_per_family"] * 2, 160)                       # r2: dev enlarged 80 -> 160 per sender
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
        B = BK.load_book(load_cfg(), "dev")
        ids = BK.core_ids(B, 80); self.assertEqual(len(ids), 160); self.assertEqual(len(BK.cases_for(B, ids)), 640)
        self.assertEqual(len({B["entries"][k]["text"] for k in ids}), 160)
    def test_test_book_refused_before_freeze(self):
        with self.assertRaises(SystemExit): BK.build_book(load_cfg(), "test")
        self.assertFalse((DATA / "book_test.json").exists())

class Freshness(unittest.TestCase):
    """r2 (GPT r1 #8): cross-kind regression cases for exactly what check_fresh enforces."""
    def setUp(self):
        self.old = dict(cases=dict(canary=[dict(text="can 1")], pool=[dict(text="old case")]), groups=dict(canary_F1=[]),
                        entries=dict(O1=dict(text="rule a"), O2=dict(text="rule b", kind="neighbour")), meta={})
    def new(self, entries, cases=()):
        return dict(cases=dict(canary=[dict(text="can 1")], test=[dict(text=t) for t in cases]), entries=entries)
    def test_allowed(self):
        self.assertTrue(BK.check_fresh(self.new(dict(N1=dict(text="rule b"))), self.old))                  # new core = old neighbour text
        self.assertTrue(BK.check_fresh(self.new(dict(N2=dict(text="rule a", kind="neighbour"))), self.old)) # new neighbour = old core text
        self.assertTrue(BK.check_fresh(self.new(dict(N3=dict(text="rule b", kind="neighbour"))), self.old)) # neighbour = old neighbour
    def test_rejected(self):
        for B in (self.new(dict(N4=dict(text="rule a"))), self.new(dict(O1=dict(text="rule z"))), self.new({}, ["old case"])):
            with self.assertRaises(AssertionError): BK.check_fresh(B, self.old)
    def test_dev_book_forbids_only_its_e1c_core(self):
        dev = json.load(open(DATA / "book_dev.json")); f = BK._old_rule_texts(dev)
        self.assertEqual(len(f), 160)
        core = {k for g in dev["e1c_core"].values() for k in g}
        other = [k for k, e in dev["entries"].items() if k not in core and e.get("kind") != "neighbour"]
        self.assertTrue(other); self.assertFalse(any(BK.norm(dev["entries"][k]["text"]) in f and k not in core for k in other[:50]
                                                     if BK.norm(dev["entries"][k]["text"]) not in {BK.norm(dev["entries"][c]["text"]) for c in core}))

class Verifier(unittest.TestCase):
    def setUp(self): self.B = BK.load_book(load_cfg(), "dev"); self.E = self.B["entries"]
    def ent(self, fam): return self.E[self.B["e1c_core"][fam][0]]
    def line(self, e): return " ".join(f"{k}={v}" for k, v in V.expected_spec(e).items())
    def test_exact_spec_matches_true_not_neighbours(self):
        for fam in ("F1", "F2"):
            for eid in self.B["e1c_core"][fam]:
                e = self.E[eid]; spec, why = V.parse_spec(fam, self.line(e)); self.assertEqual(why, "ok"); self.assertTrue(V.matches(spec, e)[0])
                for nb in self.B["neighbours"][eid]: self.assertFalse(V.matches(spec, self.E[nb])[0], nb)
    def test_prompt_sees_only_prose(self):
        e = self.ent("F1"); s, p, u = V.verifier_parts("F1", render_message(e))
        self.assertNotIn(e["id"], s + p + u); self.assertNotIn("Candidates", u)
    def test_strict_grammar(self):
        """r2 (GPT r1 #5): whole-response grammar; every deviation is a format error -> fallback."""
        e = self.ent("F2"); ok = self.line(e)
        self.assertEqual(V.parse_spec("F2", "  " + ok + "\n")[1], "ok")
        bad = [ok + "\nBecause the giver pays more.", "Answer:\n" + ok, ok + "\n" + ok, ok + " EXTRA=1",
               ok.replace("GIVER_RATE=", "GIVER_RATE=GIVER_RATE="), ok + ".", ok.replace("TAKER_RATE=", "TAKER_RATE=") + " credits",
               re.sub(r"GIVER_RATE=(\d+)", r"GIVER_RATE=\1 credits", ok), ok.replace("GIVER=", "GIVER=the "),
               " ".join(reversed(ok.split())), ok.replace("GIVER=", "GIVER=GIVER="), "GIVER=a GIVER=b GIVER_RATE=1 TAKER=c TAKER_RATE=2",
               "GROUP=x MEMBER=3 NONMEMBER=5"]
        bad += [re.sub(r"GIVER_RATE=(\d+)", "GIVER_RATE=\u0664", ok), re.sub(r"TAKER_RATE=(\d+)", "TAKER_RATE=\uff13", ok)]   # r3: Arabic-Indic / fullwidth digits
        for t in bad: self.assertEqual(V.parse_spec("F2", t), (None, "format"), t)
        self.assertEqual(V.parse_spec("F1", "GROUP=Gold MEMBER=three NONMEMBER=5"), (None, "format"))
        self.assertEqual(V.parse_spec("F1", "GROUP=Gold MEMBER=-3 NONMEMBER=5")[0], dict(GROUP="gold", MEMBER=-3, NONMEMBER=5))
        self.assertFalse(V.matches(None, self.ent("F1"))[0])

def _rows(assigned, cases, fams, drop=None, dup=False, gold_off=None):
    rows = []
    for e in assigned:
        for c in cases[e]:
            for a in ("hybrid", "prose"):
                if drop == (e, c["text"], a): continue
                rows.append(dict(entry=e, case=c["text"], cond=a, fam=fams[e], gold=(c["gold"] if gold_off != (e, c["text"]) else "999"),
                                 correct=True, payload_bytes=10 if a == "hybrid" else 100, whole_exchange_bytes=50 if a == "hybrid" else 140))
    if dup: rows.append(dict(rows[0]))
    return rows

class Analysis(unittest.TestCase):
    def test_label_rule_A12(self):
        self.assertEqual(A.label(-0.04, 0.1, 0.05), "non-inferior"); self.assertEqual(A.label(-0.2, -0.06, 0.05), "inferior")
        self.assertEqual(A.label(-0.133, -0.004, 0.05), "inconclusive")
    def test_bootstrap_stratified_deterministic_and_percentiles(self):
        by = dict(F1=[0, 0, 0.25, -0.25], F2=[0, -0.5, 0, 0])
        self.assertEqual(A.strat_boot(by, 2000, 7), A.strat_boot(by, 2000, 7))
        lo, hi = A.strat_boot(by, 2000, 7); self.assertLessEqual(lo, A.point(by)); self.assertGreaterEqual(hi, A.point(by))
        self.assertEqual(A.strat_boot(dict(F1=[0.1] * 5, F2=[0.1] * 5), 200, 1), (0.1, 0.1))
    def test_cp_upper(self):
        self.assertAlmostEqual(A.cp_upper(0, 160), 1 - 0.05 ** (1 / 160), places=6); self.assertLess(A.cp_upper(0, 160), 0.02)
        self.assertGreater(A.cp_upper(1, 160), 0.02); self.assertGreater(A.cp_upper(0, 80), 0.02)
    def test_completeness_r2(self):
        """r2 (GPT r1 #1): any missing / duplicated / extra / gold-mismatched row -> INCOMPLETE, never SUCCESS."""
        assigned = ["a", "b"]; fams = dict(a="F1", b="F2")
        cases = {e: [dict(text=f"{e}{i}", gold=str(i)) for i in range(4)] for e in assigned}
        B = dict(entries=dict(a=dict(id="a", fam="F1", ver=1, hash="0" * 8, text="x"), b=dict(id="b", fam="F2", ver=1, hash="0" * 8, text="y")), neighbours=dict(a=[], b=[]))
        sel = [dict(entry=e, accepted=True, correct=True) for e in assigned]; crit = load_cfg()["e1c"]["criteria"]
        good = A.direction_result(_rows(assigned, cases, fams), sel, B, crit, 1, assigned, cases, assigned); self.assertEqual(good["status"], "COMPLETE")
        for rows in (_rows(assigned, cases, fams, drop=("a", "a0", "hybrid")), _rows(assigned, cases, fams, dup=True),
                     _rows(assigned, cases, fams, gold_off=("b", "b1")), _rows(["a"], cases, fams),
                     _rows(assigned, cases, fams) + [dict(_rows(["a"], cases, fams)[0], case="zz")]):
            r = A.direction_result(rows, sel, B, crit, 1, assigned, cases, assigned); self.assertEqual(r["status"], "INCOMPLETE"); self.assertFalse(r["success"])
        # r3 (GPT r2 #1): duplicate / missing / extra SELECTION rows -> INCOMPLETE
        for sr in (sel + [sel[0]], sel[:1], sel + [dict(entry="zz", accepted=True, correct=True)]):
            r = A.direction_result(_rows(assigned, cases, fams), sr, B, crit, 1, assigned, cases, assigned); self.assertEqual(r["status"], "INCOMPLETE", sr)
        r = A.direction_result(_rows(assigned, cases, fams), sel, B, crit, 1, assigned, cases, ["a"]); self.assertEqual(r["status"], "INCOMPLETE")
    def test_byte_unit_r2(self):
        """r2 (GPT r1 #7): message = one case exchange; saving on payload; break-even in the same unit."""
        assigned = ["a"]; fams = dict(a="F1"); cases = dict(a=[dict(text=f"a{i}", gold="1") for i in range(4)])
        B = dict(entries=dict(a=dict(id="a", fam="F1", ver=1, hash="0" * 8, text="x" * 88)), neighbours=dict(a=[]))
        r = A.direction_result(_rows(assigned, cases, fams), [dict(entry="a", accepted=True, correct=True)], B, load_cfg()["e1c"]["criteria"], 1, assigned, cases, assigned)
        self.assertEqual(r["n_messages"], 4); self.assertAlmostEqual(r["payload_saving"], 0.9); self.assertEqual(r["payload_saving_per_message"], 90)
        db = len((framed_id(B["entries"]["a"]) + " " + "x" * 88 + "\n").encode()); self.assertEqual(r["dict_bytes"], db); self.assertAlmostEqual(r["breakeven_messages"], db / 90)
        self.assertIn("sender-local", r["byte_boundary"])

class Freeze(unittest.TestCase):
    """r2 (GPT r1 #9): registration vs execution commit rules."""
    def test_rules(self):
        a = copy.deepcopy(load_cfg()["e1c"]); a["status"] = "frozen"; b = copy.deepcopy(a); b["test_book_sha256"] = "ab" * 32
        self.assertTrue(CF.cfg_diff_ok(a, b)[0])
        c = copy.deepcopy(b); c["seeds"]["test"]["generator"] += 300; self.assertTrue(CF.cfg_diff_ok(a, c)[0])
        for k, v in (("caps_h", {"D1": 0.5, "T1": 9}), ("criteria", {}), ("status", "draft")):
            d = copy.deepcopy(b); d[k] = v; self.assertFalse(CF.cfg_diff_ok(a, d)[0], k)
        d = copy.deepcopy(b); d["seeds"]["test"]["bootstrap"] += 1; self.assertFalse(CF.cfg_diff_ok(a, d)[0])
        self.assertFalse(CF.cfg_diff_ok(a, a)[0]); a2 = copy.deepcopy(a); a2["status"] = "draft"; self.assertFalse(CF.cfg_diff_ok(a2, b)[0])
        self.assertTrue(CF.files_ok(["v6/e1c/data/book_test.json", "v6/e1c/config_e1c.json", "v6/e1c/CODE_HASH.txt"])[0])
        self.assertFalse(CF.files_ok(["v6/e1c/e1c/verifier.py"])[0]); self.assertFalse(CF.files_ok(["v6/e1c/PREREG_E1c.md"])[0])

class Fake(FakeBackend):
    """Sender: 'X) F1'-style reply naming the TRUE candidate, or a NEIGHBOUR for entries in `wrong`; verifier: the
    spec of the entry the sender picked (so a wrong pick is ACCEPTED), off by one for `bad`; receiver: toy output.
    Records the size of every generate_batch call."""
    def __init__(self, B, bad=(), wrong=()):
        super().__init__(False); self.info = dict(backend="fake"); self.bad = set(bad); self.wrong = dict(wrong); self.B = B; self.bsz = []
        self.msg = {render_message(B["entries"][k]): B["entries"][k] for f in ("F1", "F2") for k in B["e1c_core"][f]}
    def _fix(self, j, r):
        s, p, u = j
        if u.startswith("Message:") and "Candidates:" in u:
            e = self.msg[u.split("\n\nCandidates:")[0][len("Message:\n"):]]; tgt = self.wrong.get(e["id"], e["id"])
            L = next(l[0] for l in u.splitlines() if re.match(r"^[ABCD]\) ", l) and l[3:].startswith(tgt + "@"))
            return dict(r, text=f"{L}) F1")
        if u.startswith("Message:"):
            e = self.msg[u.split("\n\nReply in exactly")[0][len("Message:\n"):]]
            sp = dict(V.expected_spec(self.B["entries"][self.wrong.get(e["id"], e["id"])]))
            if e["id"] in self.bad: k = [k for k in sp if isinstance(sp[k], int)][0]; sp[k] += 1
            return dict(r, text=" ".join(f"{k}={v}" for k, v in sp.items()))
        return r
    def generate(self, s, p, u, max_new, warm=False, mode=None): return self._fix((s, p, u), super().generate(s, p, u, max_new, warm=warm, mode=mode))
    def generate_batch(self, jobs, max_new): self.bsz.append(len(jobs)); return [self._fix(j, r) for j, r in zip(jobs, super().generate_batch(jobs, max_new))]

class DryRun(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()); self.old = (ST.RES, ST.load_B, ST.require_canaries, ST.code_hash)
        ST.RES = self.tmp / "results"; ST.RES.mkdir(); os.environ["E1B_ALLOW_NO_GPU"] = "1"
        self.cfg = load_cfg(); self.B = BK.load_book(self.cfg, "dev"); self.cfg["e1c"]["sizes"]["dev"] = dict(core_per_family=6, receiver_entries_per_family=3)
        self.bad = self.B["e1c_core"]["F2"][1]; self.wr = self.B["e1c_core"]["F1"][2]; self.nb = self.B["neighbours"][self.wr][0]
        self.fakes = []
        def lb(name, cfg, S):
            f = Fake(self.B, [self.bad], {self.wr: self.nb}); self.fakes.append(f); return f, "fake"
        ST.load_B = lb; ST.require_canaries = lambda *a: None
        h = self.old[3](); ST.code_hash = lambda: h
        self.pin = ROOT / "CODE_HASH.txt"; self.had = self.pin.read_text() if self.pin.exists() else None; self.pin.write_text(h + "\n")
    def tearDown(self):
        ST.RES, ST.load_B, ST.require_canaries, ST.code_hash = self.old; os.environ.pop("E1C_GO", None)
        if self.had is None: self.pin.unlink()
        else: self.pin.write_text(self.had)
        shutil.rmtree(self.tmp, ignore_errors=True)
    def _run(self, name, cfg=None):
        try: ST.run(cfg or self.cfg, name)
        except SystemExit as e: return e.code
    def _state(self): return json.load(open(ST.RES / "D1" / "e1c_state.json"))
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
            s = S["selection"][m]; self.assertEqual(s["n"], 12); self.assertTrue(s["complete"]); self.assertAlmostEqual(s["pick_acc"], 11 / 12)
            self.assertEqual(s["correct_pick_rejected"], 1); self.assertEqual(s["wrong_pick_accepted"], 1); self.assertAlmostEqual(s["coverage"], 11 / 12)
        for d, r in S["directions"].items():
            self.assertEqual(r["status"], "COMPLETE"); self.assertEqual(r["n_entries"], 6); self.assertEqual(r["n_messages"], 24)
            rows = [json.loads(l) for l in open(ST.RES / "D1" / f"exchange_{d}.jsonl")]
            fb = [x for x in rows if x["cond"] == "hybrid" and x["sent"] == "prose"]; self.assertEqual(len(fb), 4)
            for x in fb:
                tw = [y for y in rows if y["cond"] == "prose" and y["case"] == x["case"]][0]
                self.assertEqual((x["payload_bytes"], x["pred"], x["shared_n"]), (tw["payload_bytes"], tw["pred"], 2))
        self.assertIn("sizing", S); self.assertNotIn("verdict", S); self.assertEqual(S["protocol_hash"], ST.protocol_hash(self.cfg["e1c"], self.cfg))
        self.assertEqual(self._state()["attempts"][-1]["outcome"], "done"); self.assertEqual(self._run("D1"), 0)
    def test_wrong_accepted_pick_scored_on_true_case_r2(self):
        """r2 (GPT r1 #4): an ACCEPTED wrong neighbour sends the neighbour's rule, but both arms use the TRUE entry's
        cases and gold, and correctness is judged against that gold."""
        from e1b.parsing import parse_answer, score_answer
        os.environ["E1C_GO"] = "D1"; self.assertIn(self._run("D1"), (None, 0))
        sel = {json.loads(l)["entry"]: json.loads(l) for l in open(ST.RES / "D1" / "select_qwen7b.jsonl")}
        self.assertTrue(sel[self.wr]["accepted"]); self.assertFalse(sel[self.wr]["correct"]); self.assertEqual(sel[self.wr]["pick"], self.nb)
        rows = [json.loads(l) for l in open(ST.RES / "D1" / "exchange_qwen7b_to_falcon7b.jsonl") if json.loads(l)["entry"] == self.wr]
        true = {c["text"]: c["gold"] for c in BK.cases_for(self.B, [self.wr])}; nbE = self.B["entries"][self.nb]
        self.assertEqual(len(rows), 8)
        for r in rows:
            self.assertEqual(r["gold"], true[r["case"]]); self.assertEqual(r["correct"], score_answer(parse_answer(r["raw"]), true[r["case"]]))
        hy = [r for r in rows if r["cond"] == "hybrid"]
        self.assertTrue(all(r["sent"] == "id" and r["rule_entry"] == self.nb and r["payload_bytes"] == len(framed_id(nbE)) for r in hy))
        self.assertTrue(all(r["rule_entry"] == self.wr for r in rows if r["cond"] == "prose"))
        from e1b.cases import gold_of
        self.assertTrue(any(str(gold_of(nbE["sem"], nbE["fam"], c["meta"])) != c["gold"] for c in BK.cases_for(self.B, [self.wr])))
    def test_verifier_batches_r2(self):
        """r2 (GPT r1 #6): verifier + b1 check use explicit batch 8 on the production path."""
        os.environ["E1C_GO"] = "D1"; self._run("D1")
        self.assertTrue(self.fakes and all(max(f.bsz) <= 8 for f in self.fakes if f.bsz))
        S = json.load(open(ST.RES / "D1" / "summary.json")); self.assertEqual(set(S["verifier_b1_check"]), {"qwen7b", "falcon7b"})
        self.assertEqual(S["verifier_batch_size"], 8)
    def test_inflight_guard_r2(self):
        os.environ["E1C_GO"] = "D1"; c = copy.deepcopy(self.cfg); c["e1c"]["caps_h"]["D1"] = 0.05   # 180 s < 420 s load estimate
        self.assertEqual(self._run("D1", c), 3); self.assertTrue((ST.RES / "D1" / "BUDGET_EXHAUSTED").exists()); self.assertEqual(len(self.fakes), 0)
        self.assertEqual(self._run("D1", c), 18)
    def test_retry_rules_r2(self):
        """r2/r3 (GPT r1 #3, r2 #3): second start only with an authorised reason CONSISTENT with the recorded failure;
        finite charged_h <= cap; cumulative budget; never a third start."""
        os.environ["E1C_GO"] = "D1"; d = ST.RES / "D1"; d.mkdir()
        json.dump(dict(attempts=[dict(n=1, kind="first", outcome="running")], retry=None, cap_h=0.5), open(d / "e1c_state.json", "w"))
        self.assertEqual(self._run("D1"), 17); (d / "ATTEMPT_INCOMPLETE").unlink()
        au = lambda *a: AR.authorise("D1", *a, res=ST.RES, cfg=self.cfg)
        for args in (("bad_result", 0.1, "x"), ("no_gpu", 0, "x"), ("no_gpu", float("nan"), "x"), ("no_gpu", float("inf"), "x"), ("no_gpu", 0.6, "x"), ("no_gpu", 0.1, " ")):
            with self.assertRaises(SystemExit, msg=args): au(*args)
        (d / "GPU_PREFLIGHT_FAIL").write_text("no CUDA\n")
        with self.assertRaises(SystemExit): au("kernel_crash", 0.1, "log says no GPU")      # inconsistent with the marker
        au("no_gpu", 0.1, "T4 not attached (log line 3)")
        with self.assertRaises(SystemExit): au("no_gpu", 0.1, "again")
        self.assertIn(self._run("D1"), (None, 0))
        st = self._state(); self.assertEqual([a["kind"] for a in st["attempts"]], ["first", "infra_retry"]); self.assertEqual(st["attempts"][-1]["outcome"], "done")
        self.assertGreaterEqual(json.load(open(ST.RES / "budget_ledger.json"))["E1C_D1"], 360); self.assertTrue((d / "GPU_PREFLIGHT_FAIL.attempt1").exists())
        (d / ".done").unlink(); self.assertEqual(self._run("D1"), 17)
    def test_retry_reason_consistency_r3(self):
        self.assertEqual(AR.allowed_reasons("exit 9", False), {"no_gpu"}); self.assertEqual(AR.allowed_reasons("exit 3", False), set())
        self.assertEqual(AR.allowed_reasons("exit 8", False), set()); self.assertNotIn("no_gpu", AR.allowed_reasons("crash RuntimeError", False))
        self.assertNotIn("no_gpu", AR.allowed_reasons("running", False)); self.assertEqual(AR.allowed_reasons("running", True), {"no_gpu"})
        d = ST.RES / "D1"; d.mkdir(); json.dump(dict(attempts=[dict(n=1, outcome="exit 19")], retry=None, cap_h=0.5), open(d / "e1c_state.json", "w"))
        with self.assertRaises(SystemExit): AR.authorise("D1", "kernel_crash", 0.1, "x", res=ST.RES, cfg=self.cfg)
    def test_resume_bound_to_protocol_r3(self):
        """r3 (GPT r2 #3): attempt-1 rows from a different code/protocol cannot be resumed."""
        os.environ["E1C_GO"] = "D1"; d = ST.RES / "D1"; d.mkdir(); (d / "select_qwen7b.jsonl").write_text("")
        json.dump(dict(attempts=[dict(n=1, kind="first", outcome="crash RuntimeError", code_hash="old", protocol_hash="old")], retry=None, cap_h=0.5), open(d / "e1c_state.json", "w"))
        AR.authorise("D1", "kernel_crash", 0.1, "CUDA error in log", res=ST.RES, cfg=self.cfg)
        self.assertEqual(self._run("D1"), 17); self.assertIn("different code/protocol", (d / "ATTEMPT_INCOMPLETE").read_text())
    def test_resumed_sizing_uses_persisted_latencies_r3(self):
        """r3 (GPT r2 new #1): unit costs come from persisted per-row latencies, so a resumed attempt does not underproject."""
        sel = dict(q=[dict(sender_latency_s=1.0, verifier_latency_s=0.5)] * 4, f=[dict(sender_latency_s=2.0, verifier_latency_s=0.5)] * 4)
        ex = dict(d=[dict(cond="prose", latency_s=3.0), dict(cond="hybrid", sent="prose", latency_s=3.0), dict(cond="prose", latency_s=3.0), dict(cond="hybrid", sent="id", latency_s=1.0)])
        sv, rv = ST.unit_costs(sel, ex); self.assertAlmostEqual(sv, 4.0); self.assertAlmostEqual(rv, 3.5)
        # a resumed attempt that redid only 1 of 4 sender rows still yields the same per-entry cost
        self.assertEqual(ST.unit_costs(sel, ex), ST.unit_costs({k: list(v) for k, v in sel.items()}, ex))
    def test_watchdog_deadline_r3(self):
        """r3 (GPT r2 #6): enforceable deadline at the cap, whatever is in flight."""
        import types, time as _t
        hit = []; tmp = self.tmp / "wd"; tmp.mkdir()
        S = types.SimpleNamespace(budget_s=0.2, used_s=lambda: 0.0, save_ledger=lambda: hit.append("ledger"), dir=tmp, name="D1", log=lambda *a, **k: hit.append("log"))
        w = ST.Watchdog(S, exit_fn=lambda: hit.append("exit")); _t.sleep(0.6)
        self.assertTrue(w.fired); self.assertEqual(hit, ["ledger", "log", "exit"]); self.assertTrue((tmp / "BUDGET_EXHAUSTED").exists())
        S2 = types.SimpleNamespace(budget_s=0.2, used_s=lambda: 0.0); w2 = ST.Watchdog(S2, exit_fn=lambda: hit.append("x")); w2.cancel(); _t.sleep(0.4); self.assertFalse(w2.fired)
    def test_retry_refused_after_terminal(self):
        d = ST.RES / "D1"; d.mkdir(); (d / "CANARY_FAIL").write_text("x")
        with self.assertRaises(SystemExit): AR.authorise("D1", "kernel_crash", 0.1, "x", res=ST.RES, cfg=self.cfg)
    def good_summary(self):
        X = self.cfg["e1c"]; E = ST.expected_shape(X); q, f = X["pair"]
        return dict(protocol_hash=ST.protocol_hash(X, self.cfg),
                    directions={d: dict(status="COMPLETE", n_entries=E["n_entries"], n_messages=E["n_messages"]) for d in E["directions"]},
                    selection={m: dict(complete=True, n=E["n_sel"]) for m in (q, f)},
                    verifier_b1_check={m: dict(n=E["b1_n"], identical=E["b1_n"]) for m in (q, f)},
                    sizing=dict(wrong_pass_ok=True, projected_T1_gpu_h=2.0, max_wrong_pick_accepted_rate=0.0))
    def test_t1_eligibility_r3(self):
        """r2/r3 (GPT r1 #2, r2 #2, r2 new #2): exact D1 structure, conformance, CURRENT protocol incl. the actual
        sender token limit, screen and projection."""
        X = self.cfg["e1c"]; d = ST.RES / "D1"; d.mkdir(); (d / ".done").write_text("x")
        def chk(s, cfg=None): json.dump(s, open(d / "summary.json", "w")); return ST.t1_eligibility(X if cfg is None else cfg["e1c"], cfg or self.cfg)
        g = self.good_summary(); self.assertEqual(chk(g), (True, "ok"))
        q, f = X["pair"]
        muts = [dict(protocol_hash="0"), dict(sizing=dict(g["sizing"], wrong_pass_ok=False)), dict(sizing=dict(g["sizing"], projected_T1_gpu_h=99)),
                dict(sizing=dict(g["sizing"], projected_T1_gpu_h=float("nan"))), dict(directions={}), dict(selection={}), dict(verifier_b1_check={}),
                dict(directions={k: v for k, v in list(g["directions"].items())[:1]}), dict(selection={q: g["selection"][q]}),
                dict(directions={k: dict(v, n_messages=1) for k, v in g["directions"].items()}), dict(selection={m: dict(v, n=v["n"] - 1) for m, v in g["selection"].items()}),
                dict(selection={m: dict(v, complete=False) for m, v in g["selection"].items()}),
                dict(verifier_b1_check={m: dict(v, identical=15) for m, v in g["verifier_b1_check"].items()}),
                dict(verifier_b1_check={m: dict(v, n=3, identical=3) for m, v in g["verifier_b1_check"].items()})]
        for m in muts: self.assertFalse(chk(dict(g, **m))[0], m)
        c2 = copy.deepcopy(self.cfg); c2["sender_max_new_tokens"] = 8; self.assertFalse(chk(g, c2)[0])          # actual token limit is hashed
        c3 = copy.deepcopy(self.cfg); c3["e1c"]["verifier_max_new_tokens"] = 64; self.assertFalse(chk(g, c3)[0])
        c4 = copy.deepcopy(self.cfg); c4["e1c"]["batch_size"] = 1; self.assertFalse(chk(g, c4)[0])                # effective verifier batch is hashed
        c = copy.deepcopy(self.cfg); c["e1c"]["status"] = "frozen"; os.environ["E1C_GO"] = "T1"; json.dump(dict(g, protocol_hash="0"), open(d / "summary.json", "w"))
        self.assertEqual(self._run("T1", c), 19)
    def test_verdict_structure_r3(self):
        X = self.cfg["e1c"]; q, f = X["pair"]; n = X["sizes"]["test"]; K = X["cases_per_entry"]
        dr = dict(status="COMPLETE", n_entries=2 * n["receiver_entries_per_family"], n_messages=2 * n["receiver_entries_per_family"] * K, success=True)
        out = dict(directions={f"{q}_to_{f}": dr, f"{f}_to_{q}": dr}, selection={m: dict(complete=True, n=2 * n["core_per_family"]) for m in (q, f)})
        self.assertEqual(ST.verdict(out, X), "SUCCESS")
        for o in (dict(out, directions={}), dict(out, selection={}), dict(out, directions={f"{q}_to_{f}": dr}),
                  dict(out, directions={k: dict(dr, n_messages=5) for k in out["directions"]}), dict(out, selection={q: out["selection"][q]}),
                  dict(out, selection={m: dict(v, n=12) for m, v in out["selection"].items()})):
            self.assertEqual(ST.verdict(o, X), "INCOMPLETE", o)
        self.assertEqual(ST.verdict(dict(out, directions={k: dict(dr, success=k.startswith(q)) for k in out["directions"]}), X), "NOT MET")
    def test_freeze_digest_r3(self):
        import hashlib
        b = b"book"; h = hashlib.sha256(b).hexdigest()
        self.assertTrue(CF.digest_ok(b, h, h + "\n")[0]); self.assertFalse(CF.digest_ok(b, h, "0" * 64)[0]); self.assertFalse(CF.digest_ok(b + b"x", h, h)[0])

if __name__ == "__main__": unittest.main()
