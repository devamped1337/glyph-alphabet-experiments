"""E1d tests (CPU, no model).  python -m unittest v6/e1d/tests/test_e1d.py"""
import sys, os, json, copy, math, unittest, tempfile, subprocess, shutil
from pathlib import Path
HERE = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(HERE))
from e1d import load_cfg
from e1d import lifetime as LT, analysis as AN, eligibility as EL, book as BK
from e1b import norm

cfg = load_cfg(); X = cfg["e1d"]; W = X["W"]
LC = lambda s, body=110600, n=640, c=160: LT.Lifecycle(body, n, c, 80, 2, W[s]["r"])

class Lifecycle(unittest.TestCase):
    def test_w_base_counts_versions_order(self):
        L = LC("W_base"); ev = LT.events(W["W_base"], L)
        self.assertEqual([(d, v) for d, v, _ in ev["full"]], [(0, 1), (15, 3), (45, 7), (75, 11)])
        self.assertEqual(len(ev["deltas"]), 12); self.assertEqual(ev["final_version"], 13)
        self.assertEqual([r for _, _, r in ev["deltas"]], [21, 21] + [23] * 4 + [25] * 4 + [27] * 2)
        A, D = L.A, L.D
        want = 20 * A(1) + 2 * (A(3) + A(7) + A(11)) + 21 * (D(2) + D(3)) + 23 * sum(D(v) for v in range(4, 8)) \
               + 25 * sum(D(v) for v in range(8, 12)) + 27 * (D(12) + D(13))
        self.assertEqual(ev["F_total"], want); self.assertEqual(L.rules, 4); self.assertEqual(LT.F_d(W["W_base"], L), want / 2)
    def test_w_copy(self):
        L = LC("W_copy"); ev = LT.events(W["W_copy"], L); A, D = L.A, L.D
        self.assertEqual(L.rules, 16); self.assertEqual([(d, v) for d, v, _ in ev["full"]], [(0, 1), (15, 1), (45, 2), (75, 3)])
        self.assertEqual(ev["F_total"], 6 * A(1) + (A(1) + A(2) + A(3)) + 7 * (D(2) + D(3))); self.assertEqual(LT.F_d(W["W_copy"], L), ev["F_total"])
    def test_w_churn(self):
        L = LC("W_churn"); ev = LT.events(W["W_churn"], L); A, D = L.A, L.D
        self.assertEqual([v for _, v, _ in ev["full"]], [1, 6, 16, 26]); self.assertEqual(len(ev["deltas"]), 29)
        want = 20 * A(1) + 4 * (A(6) + A(16) + A(26)) + 21 * sum(D(v) for v in range(2, 7)) + 25 * sum(D(v) for v in range(7, 17)) \
               + 29 * sum(D(v) for v in range(17, 27)) + 33 * sum(D(v) for v in range(27, 31))
        self.assertEqual(ev["F_total"], want)
    def test_manifest_exact(self):
        import measure_dict_artifact as MA
        B = json.load(open(HERE / "data" / "book_dev_new.json")); m = BK.shown_of(B, B["e1d_dev_new_core"])
        raw, hb, bb = MA.build(B["entries"], m); self.assertEqual(hb, LT.manifest_len("full", 1, None, len(set(m))))
        L = MA.load(raw); self.assertEqual(sorted(L["entries"]), sorted(set(m)))

def by_fam(h, p, n=80): return {"F1": [(h, p)] * n, "F2": [(h + 10, p + 10)] * n}

class Bootstrap(unittest.TestCase):
    def test_fixed_cost_in_every_replicate(self):
        by = {"F1": [(40 + i % 7, 300 + i % 11) for i in range(80)], "F2": [(45 + i % 5, 280 + i % 13) for i in range(80)]}
        _, lo0, s0 = LT.lifetime_boot(by, 0, 90000, 0.89, 1, 2000, 100); F = 5e6
        _, lo1, s1 = LT.lifetime_boot(by, F, 90000, 0.89, 1, 2000, 100)
        # same resamples: every replicate differs by exactly F/(M*P*) (P* > 0), so F is in every replicate and fixed
        self.assertTrue(all(a > b for a, b in zip(s0, s1)))
        H, P = LT.fam_mean(by, 0), LT.fam_mean(by, 1); pt, _, _ = LT.lifetime_boot(by, F, 90000, 0.89, 1, 10, 0)
        self.assertAlmostEqual(pt, 1 - (F + 90000 * (0.89 * H + 0.11 * P)) / (90000 * P))
        rng_check = LT.lifetime_boot({"F1": [(10, 100)] * 3, "F2": [(10, 100)] * 3}, F, 90000, 0.89, 7, 50, 0)[2]
        self.assertEqual(len(set(round(x, 12) for x in rng_check)), 1); self.assertAlmostEqual(rng_check[0], 1 - (F + 90000 * (8.9 + 11)) / 9e6)
    def test_index_and_seed(self):
        self.assertEqual(LT.lifetime_seed("a"), LT.lifetime_seed("a")); self.assertNotEqual(LT.lifetime_seed("a"), LT.lifetime_seed("b"))

def mkrows(n=4, fam="F1", acc=True, idb=40, pb=300, eid="e"):
    out = []
    for i in range(n):
        for cond, b in (("prose", pb), ("hybrid", idb)):
            out.append(dict(entry=f"{eid}{i}", fam=fam, cond=cond, correct=acc, wire_bytes=b, wire_gzip9_bytes=b, pred=1))
    return out

class Verdict(unittest.TestCase):
    def _out(self, s1=True, s2=True, one=False):
        n = X["sizes"]["test"]; K = 4; q, f = X["pair"]
        d = lambda s: dict(status="COMPLETE", n_entries=160, n_messages=640, success=s)
        D = {f"{q}_to_{f}": d(s1)} if one else {f"{q}_to_{f}": d(s1), f"{f}_to_{q}": d(s2)}
        return dict(directions=D, selection={q: dict(complete=True, n=160), f: dict(complete=True, n=160)})
    def test_both_directions_required(self):
        self.assertEqual(AN.verdict(self._out(), X), "SUCCESS")
        self.assertEqual(AN.verdict(self._out(one=True), X), "INCOMPLETE")
        self.assertEqual(AN.verdict(self._out(s2=False), X), "NOT MET")
        o = self._out(); o["directions"][list(o["directions"])[1]]["success"] = None; self.assertEqual(AN.verdict(o, X), "NOT MET")
    def test_no_breakeven_gate(self):
        import inspect; src = inspect.getsource(AN.direction_result)
        self.assertNotIn("breakeven_max", src); self.assertEqual(set(["G1", "G2", "G3"]), {"G1", "G2", "G3"})

class Freshness(unittest.TestCase):
    def setUp(self):
        self.B = json.load(open(HERE / "data" / "book_dev_new.json")); self.core = self.B["e1d_dev_new_core"]; self.ex = BK.exclusions("dev_new")
    def test_pinned_book_passes_and_roles(self):
        self.assertTrue(BK.check_fresh_e1d(self.B, self.core, self.ex)); self.assertEqual(len(self.core), 12)
        prs = [BK.pair_of(self.B["entries"][k]) for k in self.core]
        self.assertEqual(sorted(set(prs)), sorted(f"{a}/{b}" for a, b in X["roles_adopted"])); self.assertTrue(all(prs.count(p) == 4 for p in set(prs)))
    def test_e1c_test_book_text_rejected(self):
        T = json.load(open(HERE.parent / "e1c" / "data" / "book_test.json")); nb = self.B["neighbours"][self.core[0]][0]
        B = copy.deepcopy(self.B); t = next(e["text"] for e in T["entries"].values() if e.get("kind") == "neighbour"); B["entries"][nb]["text"] = t
        with self.assertRaisesRegex(AssertionError, "entry text reused"): BK.check_fresh_e1d(B, self.core, self.ex)
    def test_old_case_and_id_rejected(self):
        D = json.load(open(HERE.parent / "e1c" / "data" / "book_dev.json")); B = copy.deepcopy(self.B)
        c = next(x for x in B["cases"]["test"] if x["entry"] == self.core[0]); c["text"] = D["cases"]["test"][0]["text"]
        with self.assertRaisesRegex(AssertionError, "case text reused"): BK.check_fresh_e1d(B, self.core, self.ex)
        B = copy.deepcopy(self.B); k = self.core[1]; old = next(iter(D["e1c_core"]["F1"])); B["entries"][old] = B["entries"][k]
        B["neighbours"][old] = B["neighbours"][k]; core = [old if x == k else x for x in self.core]
        with self.assertRaisesRegex(AssertionError, "reused"): BK.check_fresh_e1d(B, core, self.ex)
    def test_test_excludes_dev_new(self):
        ex = BK.exclusions("test", [self.B])
        with self.assertRaises(AssertionError): BK.check_fresh_e1d(self.B, self.core, ex)

class Eligibility(unittest.TestCase):
    def _fake(self, prose_ok=16, hy_ok=16, parse=4):
        B = json.load(open(HERE / "data" / "book_dev_new.json")); new = B["e1d_dev_new_core"]; B["e1d_ids"] = dict(dev_new=new, e1c_dev_sel=[], e1c_dev_recv=[])
        q, f = X["pair"]; sel = {}; ex = {}
        for m in (q, f):
            seen = {}; sel[m] = []
            for e in new:
                p = BK.pair_of(B["entries"][e]); seen[p] = seen.get(p, 0) + 1
                sel[m].append(dict(entry=e, verifier_parse="ok" if seen[p] <= parse else "bad", pick=e))
            ex[f"{m}_to_{f if m == q else q}"] = [dict(entry=e, cond=c, pred=1, correct=(j < (prose_ok if c == "prose" else hy_ok)))
                                                 for e in new for j in range(4) for c in ("prose", "hybrid")]
        # correct pattern per pair: 4 entries x 4 cases; first `ok` of 16 per pair
        for d, rows in ex.items():
            cnt = {}
            for r in rows:
                p = BK.pair_of(B["entries"][r["entry"]]); key = (p, r["cond"]); cnt[key] = cnt.get(key, 0) + 1
                r["correct"] = cnt[key] <= (prose_ok if r["cond"] == "prose" else hy_ok)
        return B, sel, ex
    def test_pass(self):
        B, sel, ex = self._fake(); pr, po = EL.d7_d8(X, B, sel, ex)
        self.assertTrue(all(r["pass"] for r in pr.values())); self.assertEqual(EL.outcome_rule(X, pr, po)["rule"], 1)
    def test_pair_fail_replace(self):
        B, sel, ex = self._fake(prose_ok=11); pr, po = EL.d7_d8(X, B, sel, ex)
        self.assertEqual(EL.outcome_rule(X, pr, po)["rule"], 4)   # all 3 fail -> stop
        p0 = list(pr)[0]
        for p in pr: pr[p]["pass"] = p == p0
        r = EL.outcome_rule(X, pr, po); self.assertEqual(r["rule"], 3); self.assertEqual(r["replacements"], X["roles_step_up"][:2])
    def test_d7_and_pooled(self):
        B, sel, ex = self._fake(parse=2); pr, po = EL.d7_d8(X, B, sel, ex); self.assertFalse(any(r["D7_pass"] for r in pr.values()))
        B, sel, ex = self._fake(hy_ok=14); pr, po = EL.d7_d8(X, B, sel, ex)   # -2 per pair ok, pooled -6 < -4
        self.assertTrue(all(r["pass"] for r in pr.values())); self.assertFalse(any(v["ok"] for v in po.values())); self.assertEqual(EL.outcome_rule(X, pr, po)["rule"], 2)
    def test_d6(self): self.assertTrue(EL.builder_feasibility(X)["ok"])

class Launch(unittest.TestCase):
    def test_projection_under_cap(self):
        from e1d.supervisor import launch_projection
        p = launch_projection(X, "D1-E1d"); self.assertTrue(p["ok"]); self.assertLess(p["projected_h"], 1.0)
        X2 = copy.deepcopy(X); X2["caps_h"]["D1-E1d"] = 0.5; self.assertFalse(launch_projection(X2, "D1-E1d")["ok"])

class DryRun(unittest.TestCase):
    """Fake-model CPU dry run of D1-E1d end to end through the supervisor."""
    def test_dev_stage(self):
        res = Path(tempfile.mkdtemp()); env = dict(os.environ, E1B_ALLOW_NO_GPU="1", E1D_RES=str(res), E1D_TEST_HOOK=str(HERE / "tests" / "e1d_hook.py"), E1D_GO="D1-E1d")
        r = subprocess.run([sys.executable, str(HERE / "run_e1d.py"), "--stage", "D1-E1d"], env=env, capture_output=True, text=True, timeout=900)
        self.assertEqual(r.returncode, 0, r.stdout[-3000:] + r.stderr[-3000:])
        S = json.load(open(res / "D1-E1d" / "summary.json")); E = S["eligibility_D2_D8"]
        self.assertTrue(E["D2"]["ok"]); self.assertTrue(E["D4"]["ok"]); self.assertTrue(E["D6"]["ok"])
        for d in S["directions"].values():
            self.assertEqual(d["dev_new"]["n_messages"], 48); self.assertEqual(d["e1c_dev"]["n_messages"], 40)
            self.assertIn("W_base", d["dev_new"]["lifetime"])
        self.assertEqual(S["artifact_v1_dev"]["n_core"], 172)
        json.dump(dict(eligibility=E, sizing=S["sizing"], artifact=S["artifact_v1_dev"],
                       dev_new={k: dict(gates=v["dev_new"]["gates"], cov=v["dev_new"]["coverage"], W_base=v["dev_new"]["lifetime"]["W_base"]) for k, v in S["directions"].items()}),
                  open("/tmp/e1d_dryrun_summary.json", "w"), indent=1, default=str)
        shutil.rmtree(res)

if __name__ == "__main__": unittest.main()

class TestStage(unittest.TestCase):
    """Fake-model CPU dry run of T1-E1d end to end, on a THROWAWAY book (seed 99050, a builder-trial seed; never shown
    to a model), with the real D1-E1d results copied in for the eligibility gate."""
    def test_t1_stage(self):
        tmp = Path(tempfile.mkdtemp()); res = tmp / "res"; td = tmp / "data"; td.mkdir(); res.mkdir()
        shutil.copytree(HERE / "results" / "D1-E1d", res / "D1-E1d")
        env = dict(os.environ, E1B_ALLOW_NO_GPU="1", E1D_RES=str(res), E1D_TEST_DATA=str(td), E1D_TEST_HOOK=str(HERE / "tests" / "e1d_hook.py"))
        r = subprocess.run([sys.executable, str(HERE / "tools" / "build_test_book.py"), "99050"], env=env, capture_output=True, text=True, timeout=900)
        self.assertEqual(r.returncode, 0, r.stdout[-2000:] + r.stderr[-2000:])
        r = subprocess.run([sys.executable, str(HERE / "run_e1d.py"), "--stage", "T1-E1d"], env=dict(env, E1D_GO="D1-E1d"), capture_output=True, text=True)
        self.assertEqual(r.returncode, 14)                       # no go for T1 -> refused
        r = subprocess.run([sys.executable, str(HERE / "run_e1d.py"), "--stage", "T1-E1d"], env=dict(env, E1D_GO="T1-E1d"), capture_output=True, text=True, timeout=1800)
        self.assertEqual(r.returncode, 0, r.stdout[-3000:] + r.stderr[-3000:])
        S = json.load(open(res / "T1-E1d" / "summary.json"))
        self.assertIn(S["verdict"], ("SUCCESS", "NOT MET")); self.assertEqual(S["protocol_hash"], json.load(open(HERE / "results" / "D1-E1d" / "summary.json"))["protocol_hash"])
        for d in S["directions"].values():
            self.assertEqual((d["status"], d["n_entries"], d["n_messages"]), ("COMPLETE", 160, 640)); self.assertEqual(set(d["gates"]), {"G1", "G2", "G3"})
        self.assertEqual(S["artifact_v1"]["n_core"], 160)
        json.dump(dict(verdict=S["verdict"], art=S["artifact_v1"], gpu_h=S["gpu_h"], d={k: dict(g=v["gates"], cov=v["coverage"], W=v["lifetime"]["W_base"], mt=v["min_traffic_W_base_shape"]) for k, v in S["directions"].items()}),
                  open("/tmp/e1d_t1_dryrun.json", "w"), indent=1, default=str)
        shutil.rmtree(tmp)
    def test_projection_measured(self):
        from e1d.supervisor import test_projection
        p = test_projection(X, "T1-E1d"); self.assertTrue(p["ok"]); self.assertAlmostEqual(p["projected_h"], 2.9744, places=3)
    def test_protocol_hash_unchanged(self):
        from e1d.stages import protocol_hash
        self.assertTrue(protocol_hash(X, cfg).startswith("11d7af03"))
