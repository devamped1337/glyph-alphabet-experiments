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
        sel = {e: dict(accepted=True, correct=True) for e in assigned}; crit = load_cfg()["e1c"]["criteria"]
        good = A.direction_result(_rows(assigned, cases, fams), sel, B, crit, 1, assigned, cases); self.assertEqual(good["status"], "COMPLETE")
        for rows in (_rows(assigned, cases, fams, drop=("a", "a0", "hybrid")), _rows(assigned, cases, fams, dup=True),
                     _rows(assigned, cases, fams, gold_off=("b", "b1")), _rows(["a"], cases, fams),
                     _rows(assigned, cases, fams) + [dict(_rows(["a"], cases, fams)[0], case="zz")]):
            r = A.direction_result(rows, sel, B, crit, 1, assigned, cases); self.assertEqual(r["status"], "INCOMPLETE"); self.assertFalse(r["success"])
        out = dict(directions=dict(x=good, y=dict(status="INCOMPLETE", success=False)), selection=dict(q=dict(complete=True)))
        self.assertEqual(ST.verdict(out), "INCOMPLETE")
        out["directions"]["y"] = good; out["selection"]["q"]["complete"] = False; self.assertEqual(ST.verdict(out), "INCOMPLETE")
    def test_byte_unit_r2(self):
        """r2 (GPT r1 #7): message = one case exchange; saving on payload; break-even in the same unit."""
        assigned = ["a"]; fams = dict(a="F1"); cases = dict(a=[dict(text=f"a{i}", gold="1") for i in range(4)])
        B = dict(entries=dict(a=dict(id="a", fam="F1", ver=1, hash="0" * 8, text="x" * 88)), neighbours=dict(a=[]))
        r = A.direction_result(_rows(assigned, cases, fams), dict(a=dict(accepted=True, correct=True)), B, load_cfg()["e1c"]["criteria"], 1, assigned, cases)
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
        self.assertIn("sizing", S); self.assertNotIn("verdict", S); self.assertEqual(S["protocol_hash"], ST.protocol_hash(self.cfg["e1c"]))
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
        self.assertEqual(S["sizing"]["t1_verifier_batch"], 8 if all(v["identical"] == v["n"] for v in S["verifier_b1_check"].values()) else 1)
    def test_inflight_guard_r2(self):
        os.environ["E1C_GO"] = "D1"; c = copy.deepcopy(self.cfg); c["e1c"]["caps_h"]["D1"] = 0.05   # 180 s < 420 s load estimate
        self.assertEqual(self._run("D1", c), 3); self.assertTrue((ST.RES / "D1" / "BUDGET_EXHAUSTED").exists()); self.assertEqual(len(self.fakes), 0)
        self.assertEqual(self._run("D1", c), 18)
    def test_retry_rules_r2(self):
        """r2 (GPT r1 #3): second start only with an authorised infrastructure reason; cumulative budget; never a third."""
        os.environ["E1C_GO"] = "D1"; d = ST.RES / "D1"; d.mkdir()
        json.dump(dict(attempts=[dict(n=1, kind="first", outcome="running")], retry=None, cap_h=0.5), open(d / "e1c_state.json", "w"))
        self.assertEqual(self._run("D1"), 17); (d / "ATTEMPT_INCOMPLETE").unlink()
        with self.assertRaises(SystemExit): AR.authorise("D1", "bad_result", 0.1, "x", res=ST.RES, cfg=self.cfg)
        with self.assertRaises(SystemExit): AR.authorise("D1", "no_gpu", 0, "x", res=ST.RES, cfg=self.cfg)
        (d / "GPU_PREFLIGHT_FAIL").write_text("no CUDA\n"); AR.authorise("D1", "no_gpu", 0.1, "T4 not attached", res=ST.RES, cfg=self.cfg)
        with self.assertRaises(SystemExit): AR.authorise("D1", "no_gpu", 0.1, "again", res=ST.RES, cfg=self.cfg)
        self.assertIn(self._run("D1"), (None, 0))
        st = self._state(); self.assertEqual([a["kind"] for a in st["attempts"]], ["first", "infra_retry"]); self.assertEqual(st["attempts"][-1]["outcome"], "done")
        self.assertGreaterEqual(json.load(open(ST.RES / "budget_ledger.json"))["E1C_D1"], 360); self.assertTrue((d / "GPU_PREFLIGHT_FAIL.attempt1").exists())
        (d / ".done").unlink(); self.assertEqual(self._run("D1"), 17)
    def test_retry_refused_after_terminal(self):
        d = ST.RES / "D1"; d.mkdir(); (d / "CANARY_FAIL").write_text("x")
        with self.assertRaises(SystemExit): AR.authorise("D1", "kernel_crash", 0.1, "x", res=ST.RES, cfg=self.cfg)
    def test_t1_eligibility_r2(self):
        """r2 (GPT r1 #2): T1 needs a qualifying D1 for the CURRENT protocol and the frozen cap."""
        X = self.cfg["e1c"]; d = ST.RES / "D1"; d.mkdir(); (d / ".done").write_text("x")
        good = dict(protocol_hash=ST.protocol_hash(X), directions=dict(a=dict(status="COMPLETE")), selection=dict(q=dict(complete=True)),
                    sizing=dict(wrong_pass_ok=True, projected_T1_gpu_h=2.0, max_wrong_pick_accepted_rate=0.0))
        def chk(s): json.dump(s, open(d / "summary.json", "w")); return ST.t1_eligibility(X)
        self.assertEqual(chk(good), (True, "ok"))
        for mut in (dict(protocol_hash="0"), dict(sizing=dict(good["sizing"], wrong_pass_ok=False)), dict(sizing=dict(good["sizing"], projected_T1_gpu_h=99)),
                    dict(directions=dict(a=dict(status="INCOMPLETE"))), dict(selection=dict(q=dict(complete=False)))):
            self.assertFalse(chk(dict(good, **mut))[0], mut)
        X2 = dict(X, verifier_max_new_tokens=64); json.dump(good, open(d / "summary.json", "w")); self.assertFalse(ST.t1_eligibility(X2)[0])
        c = copy.deepcopy(self.cfg); c["e1c"]["status"] = "frozen"; os.environ["E1C_GO"] = "T1"; json.dump(dict(good, protocol_hash="0"), open(d / "summary.json", "w"))
        self.assertEqual(self._run("T1", c), 19)

if __name__ == "__main__": unittest.main()
