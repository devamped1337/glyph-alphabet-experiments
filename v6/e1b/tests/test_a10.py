"""A10 (DRAFT): sender parser fix (unit tests), offline pilot invariants on the archived replies, launch gates,
pinned reuse, one start, cap accounting, and a fake-backend dry run of B3f -> B3r -> validator on the real archived
A9 results. No model, no GPU, no network."""
import sys, os, json, shutil, tempfile, unittest, io, contextlib, hashlib
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tests"))
from e1b import load_cfg
from e1b.parsing import parse_letter, parse_letter_a10 as P
import e1b.stages as S
from test_a9 import Fake

class A10Parser(unittest.TestCase):
    def test_unambiguous(self):
        for t, L in [("B", "B"), ("B)", "B"), (" C ", "C"), ("Answer: D", "D"), ("A) Corvel member 4/seat", "A")]: self.assertEqual(P(t)[0], L, t)
    def test_candidate_id_fragments(self):
        for t, L in [("B) F1", "B"), ("C) F2", "C"), ("A) F3L", "A"), ("D) F1-1434", "D"), ("B) F1-1434@v1#ed92089f", "B"), ("A) F2-14", "A"), ("B) F1-", "B")]:
            self.assertEqual(P(t), (L, "letter"), t)
        for t in ("F1", "F2", "F3L", "F1-1434", "F2-0023@v1#ab12cd34"): self.assertEqual(P(t), (None, "invalid_none"), t)   # a bare ID fragment is not a choice
        self.assertEqual(P("F"), (None, "invalid_letter")); self.assertEqual(P("E"), (None, "invalid_letter"))
    def test_conflicting_choices_rejected(self):
        for t in ("B or C", "B) F1 C)", "A) F1-1434 or D) F2-9", "B, then C", "B) F12", "B) F1 X"): self.assertIsNone(P(t)[0], t)
    def test_never_changes_a_frozen_accepted_decision(self):
        for t in ("A", "B)", "C.", "D) label", "Answer: B"): self.assertEqual(P(t), parse_letter(t))

class A10Offline(unittest.TestCase):
    def test_archived_replies(self):
        rows = [json.loads(l) for l in open(ROOT / "results" / "B3" / "select_falcon7b.jsonl")]
        self.assertEqual(len(rows), 60); self.assertTrue(all(parse_letter(r["raw"])[0] is None for r in rows))
        picks = [(r["sender_view"]["candidates"]["ABCD".index(P(r["raw"])[0])], r["entry"]) for r in rows]
        self.assertEqual(sum(a == b for a, b in picks), 56)
        for f in sorted((ROOT / "results").glob("*/*.jsonl")):
            if f.parent.name not in ("B0x", "B1c", "B1", "B3") or f.name.startswith(("prompts_", "stage_log")): continue
            for l in open(f):
                r = json.loads(l)
                if isinstance(r.get("raw"), str) and str(r.get("parse_path", "")).startswith(("letter", "invalid_")):
                    o = parse_letter(r["raw"])
                    if o[0] is not None: self.assertEqual(P(r["raw"]), o, (f.name, r["raw"]))   # 0 changed decisions anywhere

class A10Stages(unittest.TestCase):
    def setUp(self):
        self.old = (S.RES, S.load_B); self.tmp = Path(tempfile.mkdtemp()); self.res = self.tmp / "results"
        shutil.copytree(ROOT / "results", self.res, ignore=shutil.ignore_patterns("B3f", "B3r"))
        json.dump({}, open(self.res / "B0x" / "canaries_ref.json", "w"))
        shutil.copyfile(ROOT / "config_e1b.json", self.tmp / "config_e1b.json"); (self.tmp / "data").symlink_to(ROOT / "data")
        for x in ("PREREG_E1b.md",): shutil.copyfile(ROOT / x, self.tmp / x)
        os.environ["E1B_ALLOW_NO_GPU"] = "1"; os.environ.pop("E1B_GO", None); self.calls = []
        def lb(name, cfg, St): self.calls.append(name); return Fake(name), "nf4"
        S.load_B = lb
    def tearDown(self): S.RES, S.load_B = self.old; os.environ.pop("E1B_GO", None); shutil.rmtree(self.tmp, ignore_errors=True); S._A9.clear()
    def _cfg(self, status="frozen"): c = load_cfg(); c["a10"]["status"] = status; return c
    def _run(self, st, cfg, go=True):
        if go: os.environ["E1B_GO"] = st
        else: os.environ.pop("E1B_GO", None)
        S.RES = self.res
        try: S.STAGES[st](cfg); return None
        except SystemExit as e: return e.code
    def test_config(self):
        X = load_cfg()["a10"]; self.assertEqual(X["status"], "draft"); self.assertEqual(X["direction"], ["falcon7b", "qwen7b"])
        self.assertLessEqual(sum(X["caps_h"].values()), X["total_cap_h"]); self.assertLessEqual(X["total_cap_h"], 1.0); self.assertEqual(X["max_starts"], 1)
        self.assertNotIn("mistral", json.dumps(X).lower()); self.assertIn("POST-HOC", X["label"])
    def test_gates(self):
        self.assertEqual(self._run("B3r", self._cfg("draft")), 13)
        self.assertEqual(self._run("B3r", self._cfg(), go=False), 14); self.assertEqual(self._run("B3f", self._cfg("draft"), go=False), 14)
        self.assertEqual(self._run("B3r", self._cfg()), 19)   # B3f first
        os.environ["E1B_GO"] = "B3f"; S.RES = self.res
        with self.assertRaises(SystemExit) as cm: S.STAGES["B3r"](self._cfg())
        self.assertEqual(cm.exception.code, 14)
    def test_tampered_reuse_refused(self):
        p = self.res / "B3" / "select_falcon7b.jsonl"; p.write_text(p.read_text().replace('"B) F1"', '"B"', 1))
        self.assertEqual(self._run("B3f", self._cfg("draft")), 15); self.assertFalse((self.res / "B3f" / "a10_state.json").exists())
    def test_one_start_and_caps(self):
        L = json.load(open(self.res / "budget_ledger.json")); L["A10_B3f"] = 0.9 * 3600; json.dump(L, open(self.res / "budget_ledger.json", "w"))
        self.assertEqual(self._run("B3f", self._cfg("draft")), 6)   # 0.9 used + 0.25 > 1.0 h A10 cap
        L["A10_B3f"] = 0; L["A9_B2"] = 11.9 * 3600; json.dump(L, open(self.res / "budget_ledger.json", "w"))
        self.assertEqual(self._run("B3f", self._cfg("draft")), 6)   # A9 + A10 > 12 h
    def test_dry_run_B3f_B3r_validator(self):
        from e1b import validate
        self.assertIn(self._run("B3f", self._cfg("draft")), (None, 0)); self.assertTrue((self.res / "B3f" / ".done").exists())
        fm = [json.loads(l) for l in open(self.res / "B3f" / "format_falcon7b.jsonl")]; B = json.load(open(ROOT / "data" / "cases_e1b_a9.json"))
        T = {c["entry"] for c in B["cases"]["test"]}; self.assertEqual(len(fm), 24); self.assertFalse(any(r["entry"] in T for r in fm))   # non-TEST only
        self.assertIn(self._run("B3r", self._cfg()), (None, 0)); self.assertEqual(self.calls, ["qwen7b", "falcon7b", "qwen7b"])   # B3r loads ONLY the receiver
        sel = [json.loads(l) for l in open(self.res / "B3r" / "select_falcon7b.jsonl")]
        old = {json.loads(l)["key"]: json.loads(l) for l in open(self.res / "B3" / "select_falcon7b.jsonl")}
        self.assertEqual(len(sel), 60); self.assertTrue(all(r["raw"] == old[r["key"]]["raw"] for r in sel)); self.assertEqual(sum(r["correct"] for r in sel), 56)
        ex = [json.loads(l) for l in open(self.res / "B3r" / "exchange_falcon7b_to_qwen7b.jsonl")]
        oldx = {json.loads(l)["key"]: json.loads(l) for l in open(self.res / "B3" / "exchange_falcon7b_to_qwen7b.jsonl")}
        pro = [r for r in ex if r["cond"] == "prose"]; ids = [r for r in ex if r["cond"] == "id_selected"]
        self.assertEqual((len(pro), len(ids)), (240, 240))
        self.assertTrue(all({k: v for k, v in r.items() if k != "reused_from"} == oldx[r["key"]] for r in pro))   # prose reused verbatim
        self.assertTrue(all(r["model_called"] is not False for r in ids))
        sm = json.load(open(self.res / "B3r" / "summary.json")); self.assertIn("POC FAILED", sm["primary_result_unchanged"]); self.assertEqual(sm["result"]["headline"]["n_items"], 240)
        self.assertEqual(json.load(open(self.res / "B3" / "summary.json")), json.load(open(ROOT / "results" / "B3" / "summary.json")))   # A9 result untouched
        self.assertFalse((self.res / ".B3r_view").exists())
        self.assertEqual(self._run("B3r", self._cfg()), 0)
        L = json.load(open(self.res / "budget_ledger.json")); self.assertTrue({"A10_B3f", "A10_B3r"} <= set(L))
        validate.write_manifest(self.tmp); buf = io.StringIO()
        with contextlib.redirect_stdout(buf): rc = validate.run(self.tmp)
        self.assertEqual(rc, 0, [l for l in buf.getvalue().splitlines() if l.startswith("FAIL")])

    def _done_and_validate_after(self, mutate):
        """GPT A10 r1: run B3f -> B3r, apply one mutation, regenerate the manifest, and return (rc, FAIL lines)."""
        from e1b import validate
        self.assertIn(self._run("B3f", self._cfg("draft")), (None, 0)); self.assertIn(self._run("B3r", self._cfg()), (None, 0))
        mutate(); validate.write_manifest(self.tmp); buf = io.StringIO()
        with contextlib.redirect_stdout(buf): rc = validate.run(self.tmp)
        return rc, [l for l in buf.getvalue().splitlines() if l.startswith("FAIL")]
    def _edit(self, rel, fn):
        p = self.res / rel; rows = [json.loads(l) for l in open(p)]; rows = fn(rows)
        p.write_text("".join(json.dumps(r) + "\n" for r in rows))
    def _first(self, cond):
        return lambda rows: [r for i, r in enumerate(rows) if not (r.get("cond") == cond and i == next(j for j, x in enumerate(rows) if x.get("cond") == cond))]
    def test_missing_prose_row_fails(self):
        rc, f = self._done_and_validate_after(lambda: self._edit("B3r/exchange_falcon7b_to_qwen7b.jsonl", self._first("prose")))
        self.assertNotEqual(rc, 0); self.assertTrue(any("prose has exactly 240" in l for l in f), f)
    def test_missing_id_selected_row_fails(self):
        rc, f = self._done_and_validate_after(lambda: self._edit("B3r/exchange_falcon7b_to_qwen7b.jsonl", self._first("id_selected")))
        self.assertNotEqual(rc, 0); self.assertTrue(any("id_selected has exactly 240" in l for l in f), f)
    def test_altered_copied_prose_fails(self):
        def alt(rows):
            i = next(j for j, r in enumerate(rows) if r.get("cond") == "prose"); rows[i] = dict(rows[i], correct=not rows[i]["correct"]); return rows
        rc, f = self._done_and_validate_after(lambda: self._edit("B3r/exchange_falcon7b_to_qwen7b.jsonl", alt))
        self.assertNotEqual(rc, 0); self.assertTrue(any("equals its pinned B3 source row" in l for l in f), f)
    def test_extra_field_on_copied_prose_fails(self):
        def alt(rows):
            i = next(j for j, r in enumerate(rows) if r.get("cond") == "prose"); rows[i] = dict(rows[i], note="x"); return rows
        rc, f = self._done_and_validate_after(lambda: self._edit("B3r/exchange_falcon7b_to_qwen7b.jsonl", alt))
        self.assertNotEqual(rc, 0)
    def test_missing_selection_fails(self):
        rc, f = self._done_and_validate_after(lambda: self._edit("B3r/select_falcon7b.jsonl", lambda rows: rows[1:]))
        self.assertNotEqual(rc, 0); self.assertTrue(any("exactly 60 unique archived selections" in l for l in f), f)
    def test_missing_format_view_fails(self):
        rc, f = self._done_and_validate_after(lambda: self._edit("B3f/format_qwen7b.jsonl", lambda rows: rows[1:]))
        self.assertNotEqual(rc, 0); self.assertTrue(any("exactly 24 scheduled non-TEST views" in l for l in f), f)
    def test_clean_run_passes(self):
        rc, f = self._done_and_validate_after(lambda: None); self.assertEqual(rc, 0, f)

if __name__ == "__main__": unittest.main()
