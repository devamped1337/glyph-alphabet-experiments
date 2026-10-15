import sys, os, json, re, shutil, tempfile, unittest, copy, subprocess, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT.parent / "e1b" / "tests")); sys.path.insert(0, str(ROOT / "tools"))
from e1c import load_cfg, DATA, E1B
from e1c import book as BK, verifier as V, analysis as A, stages as ST
from e1b.parsing import parse_letter, parse_letter_a10
from e1b.protocol import render_message, framed_id
import authorise_retry as AR, check_freeze as CF

class Terms(unittest.TestCase):
    def test_draft_models_and_criteria(self):
        X = load_cfg()["e1c"]; s = json.dumps(X).lower()
        self.assertEqual(X["status"], "draft"); self.assertEqual(X["pair"], ["qwen7b", "falcon7b"])
        for bad in ("mistral", "llama", "gemma"): self.assertNotIn(bad, s)
        c = X["criteria"]
        self.assertEqual((c["margin"], c["coverage_min"], c["byte_saving_min"], c["breakeven_max_messages"], c["bootstrap_resamples"], c["wrong_pass_max_dev"]),
                         (0.05, 0.85, 0.30, 1000, 2000, 0.02))
        self.assertEqual(X["caps_h"]["D1"], 0.5); self.assertEqual(X["caps_h"]["D2"], 0.8); self.assertEqual(X["sizes"]["test"]["core_per_family"] * 2, 240)
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

HOOK = ROOT / "tests" / "e1c_hook.py"

class Proc(unittest.TestCase):
    """r5: every stage run is a REAL supervisor process (run_e1c.py --stage) launching a REAL child process; the fake
    backend and faults are injected into the child by tests/e1c_hook.py (test-only, needs E1B_ALLOW_NO_GPU=1)."""
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()); self.res = self.tmp / "results"; self.res.mkdir(); self.oldRES = ST.RES; ST.RES = self.res
        self.cfg = load_cfg(); self.B = BK.load_book(self.cfg, "dev"); self.X = copy.deepcopy(json.load(open(ROOT / "config_e1c.json")))
        self.X["sizes"]["dev"] = dict(core_per_family=6, receiver_entries_per_family=3); self.cfg["e1c"]["sizes"]["dev"] = self.X["sizes"]["dev"]
        self.bad = self.B["e1c_core"]["F2"][1]; self.wr = self.B["e1c_core"]["F1"][2]; self.nb = self.B["neighbours"][self.wr][0]
        self.pin = ROOT / "CODE_HASH.txt"; self.had = self.pin.read_text() if self.pin.exists() else None; self.pin.write_text(ST.code_hash() + "\n")
        self.log = self.tmp / "calls.jsonl"; self.pids = self.tmp / "pids.txt"
    def tearDown(self):
        ST.RES = self.oldRES
        for p in (self.res, self.res / "D2"):
            if p.exists(): os.chmod(p, 0o755)
        if self.had is None: self.pin.unlink()
        else: self.pin.write_text(self.had)
        shutil.rmtree(self.tmp, ignore_errors=True)
    def run_stage(self, name="D2", go="D2", mode="ok", cap_h=None, frozen=False, timeout=120, fast_priors=False, extra={}, background=False):
        X = copy.deepcopy(self.X)
        if fast_priors: X["inflight_est_s"] = {k: 0.01 for k in X["inflight_est_s"]}   # so only the hard deadline can stop it
        if cap_h is not None: X["caps_h"][name] = cap_h
        if frozen: X["status"] = "frozen"
        X["base_config"] = str((ROOT / self.X["base_config"]).resolve()); cp = self.tmp / "cfg.json"; json.dump(X, open(cp, "w"))
        env = dict(os.environ, E1B_ALLOW_NO_GPU="1", E1C_RES=str(self.res), E1C_CONFIG=str(cp), E1C_TEST_HOOK=str(HOOK),
                   E1C_TEST_MODE=mode, E1C_TEST_LOG=str(self.log), E1C_TEST_PIDS=str(self.pids), **extra); env.pop("E1C_GO", None)
        if go: env["E1C_GO"] = go
        if background: return subprocess.Popen([sys.executable, str(ROOT / "run_e1c.py"), "--stage", name], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        t = time.time(); r = subprocess.run([sys.executable, str(ROOT / "run_e1c.py"), "--stage", name], env=env, capture_output=True, text=True, timeout=timeout)
        self.wall = time.time() - t; self.out = r.stdout + r.stderr; return r.returncode
    def d(self): return self.res / "D2"
    def state(self): return json.load(open(self.d() / "e1c_state.json"))
    def ledger(self): p = self.res / "budget_ledger.json"; return json.load(open(p)).get("E1C_D2") if p.exists() else None
    def pid(self, k):
        for _ in range(200):
            if self.pids.exists():
                v = [int(l.split()[1]) for l in open(self.pids) if l.startswith(k + " ")]
                if v: return v[-1]
            time.sleep(0.05)
    def calls(self): return [json.loads(l) for l in open(self.log)] if self.log.exists() else []
    def au(self, *a): return AR.authorise("D2", *a, res=self.res, cfg=self.cfg)

    # --- gates and the normal path
    def test_gates(self):
        self.assertEqual(self.run_stage(go=None), 14); self.assertEqual(self.run_stage("T1", go="T1"), 13)
        self.assertEqual(self.run_stage("T1", go="D2"), 14)
        self.pin.write_text("0" * 64 + "\n"); self.assertEqual(self.run_stage(), 16)
    def test_child_refuses_without_supervisor(self):
        env = dict(os.environ, E1B_ALLOW_NO_GPU="1", E1C_RES=str(self.res)); self.d().mkdir()
        json.dump(dict(attempts=[dict(n=1, token="t", outcome="running", deadline_wall=time.time() + 99)], cap_h=0.5), open(self.d() / "e1c_state.json", "w"))
        for tok in (None, "wrong"):
            e = dict(env); e.pop("E1C_ATTEMPT_TOKEN", None)
            if tok: e["E1C_ATTEMPT_TOKEN"] = tok
            self.assertEqual(subprocess.run([sys.executable, str(ROOT / "run_e1c.py"), "--child", "D2"], env=e, capture_output=True).returncode, 15)
    def test_d1_dry_run(self):
        self.assertEqual(self.run_stage(), 0, self.out); d = self.d(); S = json.load(open(d / "summary.json"))
        for m in ("qwen7b", "falcon7b"):
            s = S["selection"][m]; self.assertEqual(s["n"], 12); self.assertTrue(s["complete"]); self.assertAlmostEqual(s["pick_acc"], 11 / 12)
            self.assertEqual(s["correct_pick_rejected"], 1); self.assertEqual(s["wrong_pick_accepted"], 1); self.assertAlmostEqual(s["coverage"], 11 / 12)
        for dn, r in S["directions"].items():
            self.assertEqual(r["status"], "COMPLETE"); self.assertEqual(r["n_entries"], 6); self.assertEqual(r["n_messages"], 24)
            rows = [json.loads(l) for l in open(d / f"exchange_{dn}.jsonl")]
            fb = [x for x in rows if x["cond"] == "hybrid" and x["sent"] == "prose"]; self.assertEqual(len(fb), 4)
            for x in fb:
                tw = [y for y in rows if y["cond"] == "prose" and y["case"] == x["case"]][0]
                self.assertEqual((x["payload_bytes"], x["pred"], x["shared_n"]), (tw["payload_bytes"], tw["pred"], 2))
                self.assertEqual((x["batch_index"], x["batch_pos"], x["latency_s"]), (tw["batch_index"], tw["batch_pos"], tw["latency_s"]))
        self.assertIn("sizing", S); self.assertNotIn("verdict", S); self.assertEqual(S["protocol_hash"], ST.protocol_hash(self.cfg["e1c"], self.cfg))
        self.assertEqual(S["verifier_batch_size"], 8); self.assertEqual(set(S["verifier_b1_check"]), {"qwen7b", "falcon7b"})
        self.assertTrue(all(c["n"] <= 8 for c in self.calls() if c["kind"] == "batch"))
        a = self.state()["attempts"][-1]; self.assertEqual(a["outcome"], "done"); self.assertLess(a["ended_mono"], a["deadline_mono"]); self.assertGreaterEqual(a["finalise_s"], 0)
        self.assertAlmostEqual(self.ledger(), a["elapsed_s"], places=3); self.assertAlmostEqual(S["gpu_h"], self.ledger() / 3600)
        # wrong accepted pick: neighbour's rule sent, scored on the TRUE case (GPT r1 #4)
        from e1b.parsing import parse_answer, score_answer
        sel = {json.loads(l)["entry"]: json.loads(l) for l in open(d / "select_qwen7b.jsonl")}
        self.assertTrue(sel[self.wr]["accepted"]); self.assertFalse(sel[self.wr]["correct"]); self.assertEqual(sel[self.wr]["pick"], self.nb)
        rows = [json.loads(l) for l in open(d / "exchange_qwen7b_to_falcon7b.jsonl") if json.loads(l)["entry"] == self.wr]
        true = {c["text"]: c["gold"] for c in BK.cases_for(self.B, [self.wr])}; nbE = self.B["entries"][self.nb]; self.assertEqual(len(rows), 8)
        for r in rows: self.assertEqual(r["gold"], true[r["case"]]); self.assertEqual(r["correct"], score_answer(parse_answer(r["raw"]), true[r["case"]]))
        self.assertTrue(all(r["sent"] == "id" and r["rule_entry"] == self.nb and r["payload_bytes"] == len(framed_id(nbE)) for r in rows if r["cond"] == "hybrid"))
        self.assertEqual(self.run_stage(), 0)                                     # already finished
        (d / "BUDGET_EXHAUSTED").write_text("x"); self.assertEqual(self.run_stage(), 18)   # r5: terminal marker beats .done

    # --- r5 separate-process tests
    def test_deadline_kill(self):
        """Child hangs in a sender call; the supervisor SIGKILLs the group at the pre-recorded deadline."""
        self.assertEqual(self.run_stage(mode="sleep_send", cap_h=8 / 3600, fast_priors=True), 3, self.out); d = self.d()
        self.assertLess(self.wall, 30); self.assertTrue((d / "BUDGET_EXHAUSTED").exists()); self.assertFalse((d / ".done").exists())
        a = self.state()["attempts"][-1]; self.assertEqual((a["outcome"], a["rc"]), ("deadline", None)); self.assertAlmostEqual(self.ledger(), 8, places=3)
        self.assertEqual(self.run_stage(cap_h=8 / 3600), 18)
        with self.assertRaises(SystemExit): self.au("kernel_crash", 0.001, "x")
    def test_admission_guard(self):
        self.assertEqual(self.run_stage(cap_h=0.05), 3, self.out)      # 180 s < 420 s load estimate: child exits 3, no load
        self.assertTrue((self.d() / "BUDGET_EXHAUSTED").exists()); self.assertEqual(self.calls(), [])
        self.assertEqual(self.state()["attempts"][-1]["outcome"], "budget_admission")
    def test_concurrent_finish_after_deadline(self):
        """Child writes CHILD_COMPLETE, then is still alive at the deadline: deadline wins, never .done."""
        self.assertEqual(self.run_stage(mode="complete_then_sleep", cap_h=25 / 3600, fast_priors=True), 3, self.out); d = self.d()
        self.assertTrue((d / "CHILD_COMPLETE").exists()); self.assertFalse((d / ".done").exists()); self.assertFalse((d / "summary.json").exists())
        self.assertTrue((d / "BUDGET_EXHAUSTED").exists()); self.assertEqual(self.state()["attempts"][-1]["outcome"], "deadline")
    def test_decide_late_exit(self):
        from e1c.supervisor import decide
        self.assertEqual(decide(0, 10.0, 9.9, True)[0], "deadline"); self.assertEqual(decide(0, 9.0, 9.9, True)[0], "done")
        self.assertEqual(decide(0, 9.0, 9.9, False)[0], "crash rc=0"); self.assertEqual(decide(None, 9.0, 9.9, True)[0], "deadline")
        self.assertEqual(decide(8, 1, 2, False)[1], "CANARY_FAIL"); self.assertEqual(decide(9, 1, 2, False)[1], None)
    def test_both_writes_fail_closed(self):
        """At the deadline both the ledger and the marker writes fail (read-only dirs): the supervisor exits 70, the
        attempt stays 'running', and that is terminal: no retry, the next start is INCOMPLETE."""
        self.assertEqual(self.run_stage(mode="readonly_then_sleep", cap_h=25 / 3600, fast_priors=True), 70, self.out); d = self.d()
        for p in (self.res, d): os.chmod(p, 0o755)
        self.assertFalse((d / "BUDGET_EXHAUSTED").exists()); self.assertIsNone(self.ledger()); self.assertFalse((d / ".done").exists())
        self.assertEqual(self.state()["attempts"][-1]["outcome"], "running")
        for r in ("kernel_crash", "install_or_network", "no_gpu"):
            with self.assertRaises(SystemExit): self.au(r, 0.001, "log shows a crash")
        self.assertEqual(self.run_stage(cap_h=25 / 3600), 17); self.assertTrue((d / "ATTEMPT_INCOMPLETE").exists())
        self.assertEqual(self.run_stage(cap_h=25 / 3600), 18)
    def test_resume_after_partial_selection(self):
        """Attempt 1 crashes in the falcon sender AFTER select_qwen7b.jsonl (12 rows) is saved; authorised retry
        resumes without re-running qwen selection (file byte-identical); sizing sees both attempts' loads."""
        self.assertEqual(self.run_stage(mode="crash_send:18"), 10, self.out); d = self.d()   # sender call 18 = 6th falcon call
        q = (d / "select_qwen7b.jsonl").read_bytes(); self.assertEqual(len(q.splitlines()), 12); self.assertFalse((d / "select_falcon7b.jsonl").exists())
        self.assertEqual([c["model"] for c in self.calls() if c["kind"] == "send"], ["qwen7b"] * 12 + ["falcon7b"] * 5)
        a1 = self.state()["attempts"][0]; self.assertEqual(a1["outcome"], "crash rc=1"); led1 = self.ledger(); self.assertGreater(led1, 0)
        with self.assertRaises(SystemExit): self.au("no_gpu", 0.001, "x")            # inconsistent with a crash
        self.au("kernel_crash", 0.0001, "RuntimeError: CUDA error (log)")
        self.assertEqual(self.run_stage(), 0, self.out)
        self.assertEqual((d / "select_qwen7b.jsonl").read_bytes(), q)
        self.assertFalse([c for c in self.calls() if c["attempt"] == 2 and c["model"] == "qwen7b" and c["kind"] == "send"])
        st = self.state(); self.assertEqual([a["kind"] for a in st["attempts"]], ["first", "infra_retry"])
        self.assertAlmostEqual(self.ledger(), led1 + st["attempts"][1]["elapsed_s"], places=3)
        S = json.load(open(d / "summary.json")); z = S["sizing"]; self.assertTrue(S["selection"]["qwen7b"]["complete"])
        loads = ST.all_loads(d); self.assertEqual(len(loads), 2 + 3); self.assertAlmostEqual(z["load_s"], max(loads))
        sel = {m: [json.loads(l) for l in open(d / f"select_{m}.jsonl")] for m in ("qwen7b", "falcon7b")}
        ex = {k: [json.loads(l) for l in open(d / f"exchange_{k}.jsonl")] for k in S["directions"]}
        sv, rv = ST.unit_costs(sel, ex); self.assertAlmostEqual(z["sender_verifier_s_per_entry"], sv); self.assertAlmostEqual(z["receiver_s_per_message"], rv)
        (d / ".done").unlink(); self.assertEqual(self.run_stage(), 17)            # never a third start
    # --- r6
    def test_clock_jumps(self):
        """r6 (GPT r5): wall-clock jumps (+/- 10 days) during the run change nothing: deadline, wait, elapsed charge and
        the completion decision use the monotonic clock. Supervisor in-process with a jumping time.time()."""
        import types, e1c.supervisor as SV
        cp = self.tmp / "cfg.json"; X = copy.deepcopy(self.X); X["base_config"] = str((ROOT / self.X["base_config"]).resolve()); json.dump(X, open(cp, "w"))
        env = dict(E1B_ALLOW_NO_GPU="1", E1C_RES=str(self.res), E1C_CONFIG=str(cp), E1C_TEST_HOOK=str(HOOK), E1C_TEST_MODE="ok", E1C_GO="D2")
        old_env = {k: os.environ.get(k) for k in env}; os.environ.update(env); oldRES, oldt = SV.RES, SV.time
        try:
            for jump in (+864000.0, -864000.0):
                shutil.rmtree(self.res); self.res.mkdir(); SV.RES = self.res; n = dict(c=0)
                def wall(j=jump): n["c"] += 1; return time.time() + (j if n["c"] > 1 else 0.0)
                SV.time = types.SimpleNamespace(time=wall, monotonic=time.monotonic, strftime=time.strftime)
                with self.assertRaises(SystemExit) as e: SV.supervise(self.cfg, "D2")
                self.assertEqual(e.exception.code, 0, jump); a = self.state()["attempts"][-1]
                self.assertEqual(a["outcome"], "done"); self.assertTrue(0 < a["elapsed_s"] < 60, a["elapsed_s"])
                self.assertAlmostEqual(self.ledger(), a["elapsed_s"], places=3); self.assertTrue(ST.finished(self.d()))
        finally:
            SV.RES, SV.time = oldRES, oldt
            for k, v in old_env.items():
                if v is None: os.environ.pop(k, None)
                else: os.environ[k] = v
    def test_deadline_is_monotonic(self):
        from e1c.supervisor import decide
        a = dict(deadline_mono=100.0); self.assertEqual(decide(0, 100.1, a["deadline_mono"], True)[0], "deadline")
        src = (ROOT / "e1c" / "supervisor.py").read_text()
        self.assertNotIn("deadline_wall", src); self.assertIn("time.monotonic() + est_s > S.deadline", (ROOT / "e1c" / "stages.py").read_text())
    def test_final_state_write_fails_after_done(self):
        """r6 (GPT r5): .done and summary.json written, then the final state write fails -> exit 70, attempt 'running';
        restart, retry authorisation and T1 eligibility all refuse it."""
        self.assertEqual(self.run_stage(extra=dict(E1C_TEST_FAIL_FINAL_STATE="1")), 70, self.out); d = self.d()
        self.assertTrue((d / ".done").exists()); self.assertTrue((d / "summary.json").exists())
        self.assertEqual(self.state()["attempts"][-1]["outcome"], "running"); self.assertFalse(ST.finished(d))
        ok, why = ST.t1_eligibility(self.cfg["e1c"], self.cfg); self.assertFalse(ok); self.assertIn("recorded 'done'", why)
        for r in ("kernel_crash", "no_gpu"):
            with self.assertRaises(SystemExit): self.au(r, 0.001, "x")
        self.assertEqual(self.run_stage(), 17); self.assertTrue((d / "ATTEMPT_INCOMPLETE").exists()); self.assertEqual(self.run_stage(), 18)
    def test_done_without_recorded_outcome(self):
        d = self.d(); d.mkdir(); (d / ".done").write_text("x")
        json.dump(dict(attempts=[dict(n=1, outcome="crash rc=1")], retry=None, cap_h=0.5), open(d / "e1c_state.json", "w"))
        self.assertFalse(ST.finished(d)); self.assertEqual(self.run_stage(), 17)
    def test_directory_fsync(self):
        """r6 (GPT r5): atomic() fsyncs the file AND its directory after os.replace; new dirs fsync their parent."""
        import e1c.supervisor as SV
        seen = []; real = os.fsync
        def rec(fd): seen.append(os.readlink(f"/proc/self/fd/{fd}")); real(fd)
        os.fsync = rec
        try:
            q = self.tmp / "x" / "y"; SV.mkdir_durable(q); SV.atomic(q / "s.json", "{}")
        finally: os.fsync = real
        self.assertIn(str(self.tmp / "x"), seen); self.assertIn(str(q), seen); self.assertTrue(any(s.endswith(".tmp") for s in seen))
        self.assertEqual(seen[-1], str(q)); self.assertEqual(json.load(open(q / "s.json")), {})
    def _gone(self, pid, wait=5.0):
        t = time.time()
        while time.time() - t < wait:
            try:
                st = open(f"/proc/{pid}/stat").read().split(") ")[1][0]
                if st == "Z": return True
            except FileNotFoundError: return True
            time.sleep(0.05)
        return False
    def test_grandchild_reaped_on_normal_exit(self):
        """r6 (GPT r5 non-blocking): an ordinary grandchild still alive when the child exits 0 is killed with the group."""
        self.assertEqual(self.run_stage(mode="grandchild"), 0, self.out); g = self.pid("grandchild"); self.assertIsNotNone(g)
        self.assertTrue(self._gone(g)); self.assertTrue(ST.finished(self.d()))
    def test_supervisor_death_kills_child(self):
        """r6: if the supervisor itself dies, the child is SIGKILLed by the kernel (PR_SET_PDEATHSIG); the attempt
        stays 'running', which is terminal."""
        p = self.run_stage(mode="sleep_send", fast_priors=True, background=True); c = self.pid("child"); self.assertIsNotNone(c)
        time.sleep(1.0); p.kill(); p.wait(); self.assertTrue(self._gone(c))
        self.assertEqual(self.state()["attempts"][-1]["outcome"], "running"); self.assertEqual(self.run_stage(), 17)
    # --- A1
    def test_D1_closed_and_D2_qualifies(self):
        """A1: D1 is closed (exit 20, before any gate side effect); T1 eligibility reads D2 only, so a 'good' D1
        summary qualifies nothing and D1's BUDGET_EXHAUSTED does not block D2."""
        X = copy.deepcopy(self.X); self.assertEqual(X["closed_stages"], ["D1"]); self.assertEqual(X["t1_qualifying_dev_stage"], "D2")
        self.assertEqual(self.run_stage("D1", go="D1"), 20); self.assertFalse((self.res / "D1").exists())
        d1 = self.res / "D1"; d1.mkdir(); (d1 / "BUDGET_EXHAUSTED").write_text("x")
        self.assertEqual(self.run_stage(), 0, self.out); self.assertTrue(ST.finished(self.d()))
        good = self.good_summary(); (d1 / "BUDGET_EXHAUSTED").unlink(); (d1 / ".done").write_text("x"); json.dump(good, open(d1 / "summary.json", "w"))
        json.dump(dict(attempts=[dict(n=1, outcome="done")]), open(d1 / "e1c_state.json", "w"))
        shutil.rmtree(self.d()); self.assertFalse(ST.t1_eligibility(self.cfg["e1c"], self.cfg)[0])
    def test_log_field_relabelled(self):
        self.assertEqual(self.run_stage(), 0, self.out)
        st = [json.loads(l) for l in open(self.d() / "stage_log.jsonl") if json.loads(l)["ev"] == "start"][0]["env"]
        self.assertNotIn("code_hash", st); self.assertEqual(st["e1c_code_hash"], ST.code_hash())
        self.assertEqual(st["e1b_code_hash"], (ROOT.parent / "e1b" / "CODE_HASH.txt").read_text().strip())
    def test_resume_bound_to_protocol(self):
        d = self.d(); d.mkdir(); (d / "select_qwen7b.jsonl").write_text("")
        json.dump(dict(attempts=[dict(n=1, kind="first", outcome="crash rc=1", code_hash="old", protocol_hash="old")], retry=None, cap_h=0.5), open(d / "e1c_state.json", "w"))
        self.au("kernel_crash", 0.1, "CUDA error in log"); self.assertEqual(self.run_stage(), 17); self.assertIn("different code/protocol", (d / "ATTEMPT_INCOMPLETE").read_text())
    def test_retry_rules(self):
        d = self.d(); d.mkdir()
        json.dump(dict(attempts=[dict(n=1, kind="first", outcome="no_gpu rc=9")], retry=None, cap_h=0.5), open(d / "e1c_state.json", "w"))
        for args in (("bad_result", 0.1, "x"), ("no_gpu", 0, "x"), ("no_gpu", float("nan"), "x"), ("no_gpu", float("inf"), "x"), ("no_gpu", 0.9, "x"), ("no_gpu", 0.1, " "), ("kernel_crash", 0.1, "x")):
            with self.assertRaises(SystemExit, msg=args): self.au(*args)
        (d / "GPU_PREFLIGHT_FAIL").write_text("no CUDA\n"); self.au("no_gpu", 0.1, "T4 not attached (log line 3)")
        with self.assertRaises(SystemExit): self.au("no_gpu", 0.1, "again")
        self.assertEqual(self.run_stage(), 0, self.out); self.assertGreaterEqual(self.ledger(), 360); self.assertTrue((d / "GPU_PREFLIGHT_FAIL.attempt1").exists())
    def test_retry_reason_consistency(self):
        self.assertEqual(AR.allowed_reasons("no_gpu rc=9", False), {"no_gpu"}); self.assertEqual(AR.allowed_reasons("budget_admission", False), set())
        self.assertEqual(AR.allowed_reasons("canary_fail", False), set()); self.assertEqual(AR.allowed_reasons("deadline", False), set())
        self.assertNotIn("no_gpu", AR.allowed_reasons("crash rc=1", False)); self.assertEqual(AR.allowed_reasons("running", True), set())
        d = self.d(); d.mkdir(); (d / "CANARY_FAIL").write_text("x")
        with self.assertRaises(SystemExit): self.au("kernel_crash", 0.1, "x")
    def test_ledger_at_cap_is_terminal(self):
        json.dump({"E1C_D2": self.X["caps_h"]["D2"] * 3600}, open(self.res / "budget_ledger.json", "w"))
        self.assertEqual(self.run_stage(), 3); self.assertTrue((self.d() / "BUDGET_EXHAUSTED").exists()); self.assertEqual(self.calls(), [])
    def test_unit_costs(self):
        sel = dict(q=[dict(sender_latency_s=1.0, verifier_latency_s=0.5)] * 4, f=[dict(sender_latency_s=2.0, verifier_latency_s=0.5)] * 4)
        ex = dict(d=[dict(cond="prose", latency_s=3.0), dict(cond="hybrid", sent="prose", latency_s=3.0), dict(cond="prose", latency_s=3.0), dict(cond="hybrid", sent="id", latency_s=1.0)])
        sv, rv = ST.unit_costs(sel, ex); self.assertAlmostEqual(sv, 4.0); self.assertAlmostEqual(rv, 3.5)
    def good_summary(self):
        X = self.cfg["e1c"]; E = ST.expected_shape(X); q, f = X["pair"]
        return dict(protocol_hash=ST.protocol_hash(X, self.cfg),
                    directions={d: dict(status="COMPLETE", n_entries=E["n_entries"], n_messages=E["n_messages"]) for d in E["directions"]},
                    selection={m: dict(complete=True, n=E["n_sel"]) for m in (q, f)},
                    verifier_b1_check={m: dict(n=E["b1_n"], identical=E["b1_n"]) for m in (q, f)},
                    sizing=dict(wrong_pass_ok=True, projected_T1_gpu_h=2.0, max_wrong_pick_accepted_rate=0.0))
    def test_t1_eligibility(self):
        X = self.cfg["e1c"]; d = self.d(); d.mkdir(); (d / ".done").write_text("x")
        json.dump(dict(attempts=[dict(n=1, outcome="done")], retry=None, cap_h=0.5), open(d / "e1c_state.json", "w"))
        def chk(s, cfg=None): json.dump(s, open(d / "summary.json", "w")); return ST.t1_eligibility(X if cfg is None else cfg["e1c"], cfg or self.cfg)
        g = self.good_summary(); self.assertEqual(chk(g), (True, "ok")); q, f = X["pair"]
        muts = [dict(protocol_hash="0"), dict(sizing=dict(g["sizing"], wrong_pass_ok=False)), dict(sizing=dict(g["sizing"], projected_T1_gpu_h=99)),
                dict(sizing=dict(g["sizing"], projected_T1_gpu_h=float("nan"))), dict(directions={}), dict(selection={}), dict(verifier_b1_check={}),
                dict(directions={k: v for k, v in list(g["directions"].items())[:1]}), dict(selection={q: g["selection"][q]}),
                dict(directions={k: dict(v, n_messages=1) for k, v in g["directions"].items()}), dict(selection={m: dict(v, n=v["n"] - 1) for m, v in g["selection"].items()}),
                dict(selection={m: dict(v, complete=False) for m, v in g["selection"].items()}),
                dict(verifier_b1_check={m: dict(v, identical=15) for m, v in g["verifier_b1_check"].items()}),
                dict(verifier_b1_check={m: dict(v, n=3, identical=3) for m, v in g["verifier_b1_check"].items()})]
        for m in muts: self.assertFalse(chk(dict(g, **m))[0], m)
        c2 = copy.deepcopy(self.cfg); c2["sender_max_new_tokens"] = 8; self.assertFalse(chk(g, c2)[0])
        c3 = copy.deepcopy(self.cfg); c3["e1c"]["verifier_max_new_tokens"] = 64; self.assertFalse(chk(g, c3)[0])
        c4 = copy.deepcopy(self.cfg); c4["e1c"]["batch_size"] = 1; self.assertFalse(chk(g, c4)[0])
        for m in ST.TERMINAL:                                                       # r5: a terminal marker beats .done
            (d / m).write_text("x"); self.assertFalse(chk(g)[0], m); (d / m).unlink()
        json.dump(dict(g, protocol_hash="0"), open(d / "summary.json", "w")); self.assertEqual(self.run_stage("T1", go="T1", frozen=True), 19)
    def test_verdict_structure(self):
        X = self.cfg["e1c"]; q, f = X["pair"]; n = X["sizes"]["test"]; K = X["cases_per_entry"]
        dr = dict(status="COMPLETE", n_entries=2 * n["receiver_entries_per_family"], n_messages=2 * n["receiver_entries_per_family"] * K, success=True)
        out = dict(directions={f"{q}_to_{f}": dr, f"{f}_to_{q}": dr}, selection={m: dict(complete=True, n=2 * n["core_per_family"]) for m in (q, f)})
        self.assertEqual(ST.verdict(out, X), "SUCCESS")
        for o in (dict(out, directions={}), dict(out, selection={}), dict(out, directions={f"{q}_to_{f}": dr}),
                  dict(out, directions={k: dict(dr, n_messages=5) for k in out["directions"]}), dict(out, selection={q: out["selection"][q]}),
                  dict(out, selection={m: dict(v, n=12) for m, v in out["selection"].items()})):
            self.assertEqual(ST.verdict(o, X), "INCOMPLETE", o)
        self.assertEqual(ST.verdict(dict(out, directions={k: dict(dr, success=k.startswith(q)) for k in out["directions"]}), X), "NOT MET")
    def test_freeze_digest(self):
        import hashlib
        b = b"book"; h = hashlib.sha256(b).hexdigest()
        self.assertTrue(CF.digest_ok(b, h, h + "\n")[0]); self.assertFalse(CF.digest_ok(b, h, "0" * 64)[0]); self.assertFalse(CF.digest_ok(b + b"x", h, h)[0])

if __name__ == "__main__": unittest.main()
