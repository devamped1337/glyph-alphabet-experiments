"""Test-only hook for the stage CHILD (honoured only with E1B_ALLOW_NO_GPU=1 and E1C_TEST_HOOK=<this file>).
Installs a fake backend and the fault named by E1C_TEST_MODE:
  ok | sleep_send (first sender call sleeps 120 s) | complete_then_sleep (CHILD_COMPLETE, then sleep 120 s) |
  crash_send:N (N-th sender call raises) | readonly_then_sleep (results dirs made read-only, then sleep 120 s)."""
import os, re, sys, json, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "e1b" / "tests"))
from test_e1b import FakeBackend
from e1b.protocol import render_message
from e1c import verifier as V

class Fake(FakeBackend):
    """Sender names the TRUE candidate (a NEIGHBOUR for entries in `wrong`); verifier returns the picked entry's
    spec (off by one for `bad`); receiver: toy output. Records generate_batch sizes."""
    def __init__(self, B, bad=(), wrong=(), name="", log=None, attempt=0):
        super().__init__(False); self.info = dict(backend="fake"); self.bad = set(bad); self.wrong = dict(wrong); self.B = B
        self.msg = {render_message(B["entries"][k]): B["entries"][k] for f in ("F1", "F2") for k in B["e1c_core"][f]}
        self.name, self.logp, self.attempt = name, log, attempt
    def _log(self, kind, n=1):
        if self.logp:
            with open(self.logp, "a") as fh: fh.write(json.dumps(dict(attempt=self.attempt, model=self.name, kind=kind, n=n)) + "\n")
    def _fix(self, j, r):
        s, p, u = j
        if u.startswith("Message:") and "Candidates:" in u:
            self._log("send"); e = self.msg[u.split("\n\nCandidates:")[0][len("Message:\n"):]]; tgt = self.wrong.get(e["id"], e["id"])
            L = next(l[0] for l in u.splitlines() if re.match(r"^[ABCD]\) ", l) and l[3:].startswith(tgt + "@"))
            return dict(r, text=f"{L}) F1")
        if u.startswith("Message:"):
            e = self.msg[u.split("\n\nReply in exactly")[0][len("Message:\n"):]]
            sp = dict(V.expected_spec(self.B["entries"][self.wrong.get(e["id"], e["id"])]))
            if e["id"] in self.bad: k = [k for k in sp if isinstance(sp[k], int)][0]; sp[k] += 1
            return dict(r, text=" ".join(f"{k}={v}" for k, v in sp.items()))
        return r
    def generate(self, s, p, u, max_new, warm=False, mode=None): return self._fix((s, p, u), super().generate(s, p, u, max_new, warm=warm, mode=mode))
    def generate_batch(self, jobs, max_new): self._log("batch", len(jobs)); return [self._fix(j, r) for j, r in zip(jobs, super().generate_batch(jobs, max_new))]

def install(ST, B, a):
    mode = os.environ.get("E1C_TEST_MODE", "ok"); log = os.environ.get("E1C_TEST_LOG")
    bad = B["e1c_core"]["F2"][1]; wr = B["e1c_core"]["F1"][2]; nb = B["neighbours"][wr][0]; calls = dict(n=0)
    def lb(name, cfg, S):
        f = Fake(B, [bad], {wr: nb}, name, log, a["n"]); g = f.generate
        def gen(*x, **kw):
            if "Candidates:" in x[2]: calls["n"] += 1
            if mode.startswith("crash_send:") and calls["n"] == int(mode.split(":")[1]): raise RuntimeError("simulated CUDA error")
            if mode == "sleep_send" and "Candidates:" in x[2]: time.sleep(120)
            return g(*x, **kw)
        f.generate = gen; return f, "fake"
    ST.load_B = lb; ST.require_canaries = lambda *x: None
    if mode in ("complete_then_sleep", "readonly_then_sleep"):
        fin = ST.finish_child
        def late(S, out):
            fin(S, out)
            if mode == "readonly_then_sleep":
                for p in (S.dir, S.dir.parent): os.chmod(p, 0o555)
            time.sleep(120)
        ST.finish_child = late
