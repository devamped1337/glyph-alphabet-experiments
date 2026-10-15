"""Authorise the ONE infrastructure retry of an E1c stage (run on the box by hand, after reading the failed
attempt's Kaggle log; the result is committed and overlaid into the retry kernel).
  python tools/authorise_retry.py <stage> <reason> <charged_h> "<note citing the log>"
r3 (GPT r2 #3): the reason must be CONSISTENT with the recorded failure:
  GPU_PREFLIGHT_FAIL marker or outcome 'exit 9'          -> reason must be no_gpu (and no_gpu needs one of them)
  outcome 'crash <type>' / 'running' (killed, no record)  -> install_or_network | kernel_crash | oom_at_load
  no attempt recorded (no results came back)              -> install_or_network | kernel_crash | oom_at_load,
                                                             attempt 1 recorded as 'manual: from Kaggle log'
  any other 'exit N' (budget, canary, gates, ...)         -> refused (not an infrastructure failure)
charged_h must be finite, > 0 and < the stage cap (r4: a deadline hit is terminal); it is added to the stage's cumulative budget. The note is
mandatory (the log evidence)."""
import sys, json, time, math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from e1c import load_cfg, RES

NON_GPU = {"install_or_network", "kernel_crash", "oom_at_load"}

def allowed_reasons(outcome, gpu_marker):
    if gpu_marker or outcome == "exit 9": return {"no_gpu"}
    if outcome is None or outcome == "running" or outcome.startswith("crash ") or outcome.startswith("manual:"): return set(NON_GPU)
    return set()

def authorise(stage, reason, charged_h, note, res=RES, cfg=None):
    X = (cfg or load_cfg())["e1c"]; d = res / stage
    if reason not in X["infra_retry_reasons"]: raise SystemExit(f"reason {reason!r} is not an infrastructure reason {X['infra_retry_reasons']}")
    for m in (".done", "BUDGET_EXHAUSTED", "CANARY_FAIL", "ATTEMPT_INCOMPLETE"):
        if (d / m).exists(): raise SystemExit(f"{stage}: {m} present -> no retry")
    try: ch = float(charged_h)
    except (TypeError, ValueError): raise SystemExit("charged_h must be a number")
    if not math.isfinite(ch) or ch <= 0 or ch >= X["caps_h"][stage]: raise SystemExit(f"charged_h must be finite, > 0 and < cap {X['caps_h'][stage]}")
    Lp = res / "budget_ledger.json"; used = (json.load(open(Lp)) if Lp.exists() else {}).get(f"E1C_{stage}", 0.0) / 3600
    if max(used, ch) >= X["caps_h"][stage]: raise SystemExit(f"{stage}: cap already used ({max(used, ch):.3f} h) -> deadline is terminal, no retry")
    if not str(note).strip(): raise SystemExit("a note citing the failed attempt's log is required")
    d.mkdir(parents=True, exist_ok=True); p = d / "e1c_state.json"
    st = json.load(open(p)) if p.exists() else dict(attempts=[], retry=None, cap_h=X["caps_h"][stage])
    if not st["attempts"]:
        st["attempts"].append(dict(n=1, kind="first", t=None, outcome="manual: no results returned (from Kaggle log)"))
    if len(st["attempts"]) != 1 or st.get("retry"): raise SystemExit("retry already authorised or used")
    out = st["attempts"][0].get("outcome"); ok = allowed_reasons(out, (d / "GPU_PREFLIGHT_FAIL").exists())
    if reason not in ok: raise SystemExit(f"reason {reason!r} inconsistent with recorded failure {out!r} (allowed: {sorted(ok)})")
    st["retry"] = dict(for_attempt=1, reason=reason, charged_h=ch, note=note, recorded_outcome=out, t=time.time())
    json.dump(st, open(p, "w"), indent=1); return st

if __name__ == "__main__":
    print(json.dumps(authorise(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]), indent=1))
