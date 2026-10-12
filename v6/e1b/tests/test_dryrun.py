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
        cfg = load_cfg()
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
