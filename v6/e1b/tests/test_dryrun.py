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
        cfg = load_cfg(); import os; os.environ["E1B_ALLOW_NO_GPU"] = "1"   # fake backend has no GPU (dry run only)
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
