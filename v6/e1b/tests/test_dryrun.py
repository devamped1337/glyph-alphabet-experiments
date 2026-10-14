"""Dry run of every stage with a deterministic FAKE backend (no model, no inference) into a temp results dir.
Exercises the full code paths, checkpoint files, analysis and the --e1b validator."""
import sys, json, shutil, tempfile, unittest, importlib
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tests"))
from e1b import load_cfg
import e1b.stages as S
import e1b.backends as BK
from test_e1b import FakeBackend

class Fake(FakeBackend):
    def __init__(self, name="fake", *a, **k): super().__init__(False); self.info = dict(backend="fake"); self.name = name

class DryRun(unittest.TestCase):
    def test_all_stages(self):
        tmp = Path(tempfile.mkdtemp()); old_res = S.RES; S.RES = tmp / "results"
        BK.LlamaCppBackend = Fake
        real_verify = BK.verify_gguf
        BK.verify_gguf = lambda path, want: "stubbed-in-dryrun"   # real runs keep the sha256 pin check (gpt_code_2 #1)
        S.load_B = lambda name, cfg, St: (Fake(name), "fake")
        cfg = load_cfg(); cfg.pop("a9", None); import os; os.environ["E1B_ALLOW_NO_GPU"] = "1"   # legacy (pre-A9) path; A9 has its own dry run (test_a9.py)
        try:
            for st in ("A",):
                try: S.STAGES[st](cfg)
                except SystemExit as e: self.fail(f"stage {st} exit {e.code}")
            self.assertTrue((S.RES / "A" / ".done").exists())
            sm = json.load(open(S.RES / "A" / "summary.json")); self.assertIn("exit", sm)
            # B0 needs access + qualification; emulate with fake (qualification will fail -> NO_QUALIFYING_PAIR exit 5)
            S.RES.joinpath("B0").mkdir(parents=True, exist_ok=True)
            try: S.STAGES["B0"](cfg)
            except SystemExit as e: self.assertIn(e.code, (5, 6, None))
            # force a pair + C60 to exercise B1-B3
            json.dump(dict(pair=["qwen7b", "olmo7b"], choice=dict(choice="C60"), leak=dict(flagged=[])), open(S.RES / "B0" / "config_choice.json", "w"))
            # canary refs: per-case dicts as written by the real B0 (gpt_code_2 #1); the fake B0 wrote them for the models it loaded
            ref = json.load(open(S.RES / "B0" / "canaries_ref.json"))
            self.assertTrue(ref and all(isinstance(v, dict) and all({"pred", "correct"} <= set(x) for x in v.values()) for v in ref.values()), ref)
            fake_ref = next(iter(ref.values())); json.dump({"qwen7b": fake_ref, "olmo7b": fake_ref}, open(S.RES / "B0" / "canaries_ref.json", "w"))
            for q in (S.RES / "B0").glob("qualification_*.json"): q.unlink()   # fake models fail qualification; test the headline path
            for st in ("B1", "B2", "B3"):
                try: S.STAGES[st](cfg)
                except SystemExit as e: self.fail(f"stage {st} exit {e.code}")
                self.assertTrue((S.RES / st / ".done").exists(), st)
            b3 = json.load(open(S.RES / "B3" / "summary.json")); self.assertIn("poc_success", b3)
            # validator over the dry-run results
            from e1b import validate
            root = tmp / "root"; root.mkdir(); (root / "data").symlink_to(ROOT / "data"); (root / "results").symlink_to(S.RES)
            shutil.copy(ROOT / "config_e1b.json", root)
            validate.write_manifest(root); self.assertEqual(validate.run(root), 0)
        finally:
            S.RES = old_res; BK.verify_gguf = real_verify; shutil.rmtree(tmp, ignore_errors=True)

    def test_real_hash_check_still_active(self):
        import inspect
        self.assertIn("verify_gguf", inspect.getsource(S.stage_A)); self.assertIn("require_canaries", inspect.getsource(S.stage_B1))

if __name__ == "__main__": unittest.main()


class GPUPreflight(unittest.TestCase):
    """A7: Stage B must never run silently on the CPU."""
    def test_hf_on_cpu_fails(self):
        from types import SimpleNamespace as N
        class M:
            def __init__(self, dev): self.dev = dev
            def parameters(self): return [N(device=N(type=self.dev))]
            def buffers(self): return []
        for avail, dev in ((False, "cuda"), (True, "cpu"), (True, "meta")):
            b = BK.HFBackend.__new__(BK.HFBackend); b.torch = N(cuda=N(is_available=lambda a=avail: a)); b.m = M(dev); b.info = dict(backend="hf-nf4", nf4=None)
            with self.assertRaises(BK.GPUPreflightFail): BK.gpu_preflight(b)
    def test_b0_without_gpu_aborts_exit9(self):
        import os
        os.environ.pop("E1B_ALLOW_NO_GPU", None)
        tmp = Path(tempfile.mkdtemp()); old = S.RES; S.RES = tmp / "results"
        try:
            with self.assertRaises(SystemExit) as cm: S.STAGES["B0"](load_cfg())
            self.assertEqual(cm.exception.code, 9); self.assertTrue((S.RES / "B0" / "GPU_PREFLIGHT_FAIL").exists())
        finally: S.RES = old; shutil.rmtree(tmp, ignore_errors=True)
    def test_order_has_no_mistral(self):
        cfg = load_cfg(); self.assertEqual(cfg["models"]["stageB_order"], ["qwen7b", "olmo7b"])
        self.assertNotIn("mistral7b", cfg["models"]["stageB"]); self.assertEqual(cfg["b0_resume"]["alloc"], "reserve")


class B0xExtension(unittest.TestCase):
    """A8 (draft): refusal while draft; byte-identical, pin-verified Qwen reuse incl. prompt log; one candidate;
    absolute deadline persisted across restarts; single infra retry with fallback; scored-then-interrupted = incomplete;
    full B0x -> validator path (missing files, duplicates)."""
    def _env(self, reserve=4968.9):
        import os; os.environ["E1B_ALLOW_NO_GPU"] = "1"
        tmp = Path(tempfile.mkdtemp()); res = tmp / "results"; res.mkdir()
        shutil.copytree(ROOT / "results" / "B0", res / "B0")
        for f in ("config_e1b.json",): shutil.copyfile(ROOT / f, tmp / f)
        (tmp / "data").symlink_to(ROOT / "data")
        json.dump({"reserve": reserve}, open(res / "budget_ledger.json", "w"))
        return tmp, res
    def _cfg(self):
        cfg = load_cfg(); cfg["b0_ext"]["status"] = "frozen"; return cfg
    def _run(self, cfg):
        with self.assertRaises(SystemExit) as cm: S.STAGES["B0x"](cfg)
        return cm.exception.code
    def setUp(self): self.old = (S.RES, S.load_B); self.tmp, self.res = self._env(); S.RES = self.res
    def tearDown(self): S.RES, S.load_B = self.old; shutil.rmtree(self.tmp, ignore_errors=True)
    def _state(self): return json.load(open(self.res / "B0x" / "b0x_state.json"))

    def test_refuses_when_draft(self):
        cfg = load_cfg(); cfg["b0_ext"]["status"] = "draft"; self.assertEqual(self._run(cfg), 10)   # any non-frozen status refuses
    def test_reuse_pins_match_immutable_commit(self):
        import subprocess, hashlib
        for f, h in load_cfg()["b0_ext"]["reuse_sha256"].items():
            b = subprocess.run(["git", "-C", str(ROOT), "show", f"7873596:v6/e1b/results/B0/{f}"], capture_output=True).stdout
            if b: self.assertEqual(hashlib.sha256(b).hexdigest(), h, f)
    def test_hash_mismatch_refuses(self):
        with open(self.res / "B0" / "qual_qwen7b.jsonl", "a") as f: f.write("\n")
        self.assertEqual(self._run(self._cfg()), 12)
    def test_full_run_reuse_and_validator(self):
        import hashlib, io, contextlib
        from e1b import validate
        S.load_B = lambda name, cfg, St: (Fake(name), "nf4")
        self.assertIn(self._run(self._cfg()), (5, 6, None))
        d = self.res / "B0x"
        for f in ("qual_qwen7b.jsonl", "probediag_qwen7b.jsonl", "prompts_qwen7b.jsonl", "canary_qwen7b.jsonl"):
            self.assertEqual(hashlib.sha256((d / f).read_bytes()).hexdigest(), load_cfg()["b0_ext"]["reuse_sha256"][f])
        self.assertTrue((d / "qual_falcon7b.jsonl").exists())
        self.assertFalse(any((d / f"qual_{m}.jsonl").exists() for m in ("olmo7b", "mistral7b")))
        log = [json.loads(l) for l in open(d / "stage_log.jsonl")]
        self.assertEqual([x for x in log if x["ev"] == "start"][0]["alloc"], "reserve")
        def val():
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf): rc = validate.run(self.tmp)
            return rc, buf.getvalue()
        rc, out = val(); self.assertEqual(rc, 0, [l for l in out.splitlines() if l.startswith("FAIL")])
        self.assertIn("B0x/qual_qwen7b.jsonl: byte-identical to 7873596 pin", out)
        self.assertIn("B0x/qual_qwen7b.jsonl: rendered prompts logged (A2)", out)
        # duplicate key -> FAIL
        L = open(d / "qual_falcon7b.jsonl").readline()
        with open(d / "qual_falcon7b.jsonl", "a") as f: f.write(L)
        rc, out = val(); self.assertEqual(rc, 1); self.assertIn("FAIL B0x/qual_falcon7b.jsonl: unique keys", out)
        # missing reused prompt log -> FAIL (expected file + prompt_sha resolution)
        (d / "prompts_qwen7b.jsonl").unlink()
        rc, out = val(); self.assertIn("missing ['prompts_qwen7b.jsonl']", out)
        # tampered reused file -> FAIL
        rows = open(self.res / "B0" / "qual_qwen7b.jsonl").read().splitlines(); r0 = json.loads(rows[0]); r0["correct"] = not r0["correct"]
        open(d / "qual_qwen7b.jsonl", "w").write("\n".join([json.dumps(r0)] + rows[1:]) + "\n")   # silently edited score
        rc, out = val(); self.assertIn("FAIL B0x/qual_qwen7b.jsonl: byte-identical to 7873596 pin", out)
    def test_deadline_fixed_across_restart_and_single_retry(self):
        def abort(name, cfg, St): sys.exit(9)   # infra abort before any probe is scored
        S.load_B = abort
        self.assertEqual(self._run(self._cfg()), 9)
        st1 = self._state(); self.assertEqual(st1["starts"], 1); self.assertFalse(st1["retry_used"])
        self.assertAlmostEqual(st1["deadline_reserve_s"], 4968.9 + 1.2 * 3600, places=3)
        # 0.5 h more reserve spent before the restart: the deadline must NOT move (GPT A8 #1)
        L = json.load(open(self.res / "budget_ledger.json")); L["reserve"] = L["reserve"] + 1800; json.dump(L, open(self.res / "budget_ledger.json", "w"))
        seen = {}
        def ok(name, cfg, St): seen["dtype"] = cfg["models"]["nf4"]["bnb_4bit_compute_dtype"]; return Fake(name), "nf4"
        S.load_B = ok
        self.assertIn(self._run(self._cfg()), (5, 6, None))
        st2 = self._state(); self.assertEqual(st2["deadline_reserve_s"], st1["deadline_reserve_s"]); self.assertTrue(st2["retry_used"])
        self.assertEqual(seen["dtype"], "float32")   # pre-registered fallback on the retry only
        log = [json.loads(l) for l in open(self.res / "B0x" / "stage_log.jsonl")]
        self.assertTrue(any(x["ev"] == "infra_retry_fallback" for x in log))
        self.assertEqual(self._run(self._cfg()), 0)   # finished: one attempt only
    def test_second_infra_abort_and_scored_interrupt_are_incomplete(self):
        def abort(name, cfg, St): sys.exit(9)
        S.load_B = abort
        self.assertEqual(self._run(self._cfg()), 9); self.assertEqual(self._run(self._cfg()), 9)
        self.assertEqual(self._run(self._cfg()), 5); self.assertTrue((self.res / "B0x" / "ATTEMPT_INCOMPLETE").exists())
    def test_scored_then_interrupted_counts_as_not_qualified(self):
        def abort(name, cfg, St): sys.exit(9)
        S.load_B = abort; self.assertEqual(self._run(self._cfg()), 9)
        with open(self.res / "B0x" / "qual_falcon7b.jsonl", "w") as f: f.write(json.dumps(dict(key="x", step="qual_probe")) + "\n")
        self.assertEqual(self._run(self._cfg()), 5)
        self.assertIn("not qualified", (self.res / "B0x" / "ATTEMPT_INCOMPLETE").read_text())
        self.assertEqual(json.load(open(self.res / "B0x" / "summary.json"))["pair"], None)


class B0xFinal(B0xExtension):
    """A8 final (Claude): access errors are never retried; load/OOM/non-finite/crash get the single fp32 retry; dtype recorded."""
    def test_access_error_not_retried(self):
        class GatedRepoError(Exception): pass
        def gated(name, cfg, St): raise GatedRepoError("401 Client Error: gated repo")
        S.load_B = gated
        self.assertEqual(self._run(self._cfg()), 5)
        d = self.res / "B0x"; self.assertTrue((d / "NO_ACCESS").exists()); self.assertTrue(self._state()["finished"])
        self.assertFalse(self._state()["retry_used"]); self.assertEqual(self._run(self._cfg()), 0)   # no retry afterwards
    def test_oom_before_scoring_gets_fp32_retry(self):
        def oom(name, cfg, St): raise RuntimeError("CUDA out of memory")
        S.load_B = oom
        with self.assertRaises(RuntimeError): S.STAGES["B0x"](self._cfg())
        self.assertFalse(self._state()["finished"])
        seen = {}
        def ok(name, cfg, St): seen["dt"] = cfg["models"]["nf4"]["bnb_4bit_compute_dtype"]; return Fake(name), "nf4"
        S.load_B = ok; self.assertIn(self._run(self._cfg()), (5, 6, None)); self.assertEqual(seen["dt"], "float32")
        cd = json.load(open(self.res / "B0x" / "compute_dtype.json"))
        self.assertEqual(cd["falcon7b"], {"bnb_4bit_compute_dtype": "float32", "infra_retry": True}); self.assertEqual(cd["qwen7b"]["bnb_4bit_compute_dtype"], "float16")
    def test_dtype_recorded_first_attempt(self):
        S.load_B = lambda name, cfg, St: (Fake(name), "nf4"); self._run(self._cfg())
        self.assertEqual(json.load(open(self.res / "B0x" / "compute_dtype.json"))["falcon7b"]["bnb_4bit_compute_dtype"], "float16")
