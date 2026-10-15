"""Authorise the ONE infrastructure retry of an E1c stage (run on the box by hand, after reading the failed
attempt's Kaggle log; the result is committed and overlaid into the retry kernel).
  python tools/authorise_retry.py <stage> <reason> <charged_h> "<note>"
reason must be in config infra_retry_reasons. charged_h = GPU-h already used by attempt 1 (from its ledger or the
Kaggle run time if no results came back); it is added to the stage's cumulative budget."""
import sys, json, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from e1c import load_cfg, RES

def authorise(stage, reason, charged_h, note, res=RES, cfg=None):
    X = (cfg or load_cfg())["e1c"]; d = res / stage
    if reason not in X["infra_retry_reasons"]: raise SystemExit(f"reason {reason!r} is not an infrastructure reason {X['infra_retry_reasons']}")
    for m in (".done", "BUDGET_EXHAUSTED", "CANARY_FAIL", "ATTEMPT_INCOMPLETE"):
        if (d / m).exists(): raise SystemExit(f"{stage}: {m} present -> no retry")
    d.mkdir(parents=True, exist_ok=True); p = d / "e1c_state.json"
    st = json.load(open(p)) if p.exists() else dict(attempts=[], retry=None, cap_h=X["caps_h"][stage])
    if not st["attempts"]:   # attempt 1 left no results: record it from the Kaggle log
        st["attempts"].append(dict(n=1, kind="first", t=None, outcome="no results returned (recorded from Kaggle log)"))
    if len(st["attempts"]) != 1 or st.get("retry"): raise SystemExit("retry already authorised or used")
    if float(charged_h) <= 0: raise SystemExit("charged_h must be > 0")
    st["retry"] = dict(for_attempt=1, reason=reason, charged_h=float(charged_h), note=note, t=time.time())
    json.dump(st, open(p, "w"), indent=1); return st

if __name__ == "__main__":
    print(json.dumps(authorise(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]), indent=1))
