"""r5 (GPT r4): the E1c stage SUPERVISOR (run_e1c.py --stage). It is the only writer of the attempt state, the
budget ledger, the terminal markers, summary.json and .done. It
  1. runs the gates (go, frozen, D1 eligibility, code hash, book) and checks terminal markers BEFORE .done;
  2. computes the remaining budget from the cumulative ledger and durably records the attempt (token, started_wall,
     deadline_wall) BEFORE launching; if that write fails, nothing is launched;
  3. launches the stage child in its own process group and waits until the deadline; at the deadline the whole
     group is SIGKILLed;
  4. decides the outcome: .done only if the child exited 0, CHILD_COMPLETE exists and the exit was <= the deadline;
  5. adds the elapsed wall time to the ledger, writes the marker / summary / .done, and LAST the attempt outcome.
Fail-closed: if bookkeeping fails, the attempt stays 'running'. A 'running' attempt is never retried (no evidence
of how it ended is trusted): the next start writes ATTEMPT_INCOMPLETE and authorise_retry refuses it."""
import os, sys, json, time, signal, subprocess, uuid
from . import RES, HERE
from . import stages as ST
from .book import load_book

RUN = HERE / "run_e1c.py"
OUTCOME = {3: ("budget_admission", "BUDGET_EXHAUSTED", 3), 8: ("canary_fail", "CANARY_FAIL", 8), 9: ("no_gpu rc=9", None, 9)}

def atomic(p, text):
    tmp = p.with_name(p.name + f".{os.getpid()}.tmp")
    with open(tmp, "w") as fh: fh.write(text); fh.flush(); os.fsync(fh.fileno())
    os.replace(tmp, p)

def ledger(): p = RES / "budget_ledger.json"; return json.load(open(p)) if p.exists() else {}

def decide(rc, end, deadline, complete):
    """Pure terminal decision. rc None = killed at the deadline. Deadline wins over a late or concurrent finish."""
    if rc is None or end > deadline: return "deadline", "BUDGET_EXHAUSTED", 3
    if rc == 0 and complete: return "done", None, 0
    if rc in OUTCOME: return OUTCOME[rc]
    return f"crash rc={rc}", None, 10

def gates(cfg, name):
    X = cfg["e1c"]
    if name not in X["caps_h"]: print(f"unknown E1c stage {name}"); sys.exit(2)
    if os.environ.get("E1C_GO") != name: print(f"{name} refused: no explicit go (E1C_GO must equal '{name}')"); sys.exit(14)
    if name == "T1":
        if X["status"] != "frozen": print("T1 refused: E1c is not frozen"); sys.exit(13)
        ok, why = ST.t1_eligibility(X, cfg)
        if not ok: print(f"T1 refused: {why}"); sys.exit(19)
    p = HERE / "CODE_HASH.txt"; pin = p.read_text().strip() if p.exists() else None
    if pin != ST.code_hash(): print(f"{name} refused: code hash != CODE_HASH.txt"); sys.exit(16)
    load_book(cfg, "dev" if name == "D1" else "test")
    return X

def supervise(cfg, name):
    X = gates(cfg, name); d = RES / name; d.mkdir(parents=True, exist_ok=True); stp = d / "e1c_state.json"
    term = [m for m in ST.TERMINAL if (d / m).exists()]           # r5: terminal markers BEFORE .done
    if term: print(f"{name}: terminal marker {term} -> stop and report"); sys.exit(18)
    if (d / ".done").exists(): print(f"{name} already finished"); sys.exit(0)
    cap_s = X["caps_h"][name] * 3600; key = f"E1C_{name}"
    st = json.load(open(stp)) if stp.exists() else dict(attempts=[], retry=None, cap_h=X["caps_h"][name])
    A, R = st["attempts"], st.get("retry")
    if any(a.get("outcome") == "running" for a in A):
        atomic(d / "ATTEMPT_INCOMPLETE", f"{name}: an attempt has no recorded end (fail-closed); INCOMPLETE\n"); print(f"{name}: unresolved attempt -> INCOMPLETE"); sys.exit(17)
    L = ledger(); used = L.get(key, 0.0)
    if len(A) == 0: kind = "first"
    elif len(A) == 1 and R and R.get("for_attempt") == 1 and R.get("reason") in X["infra_retry_reasons"]:
        kind = "infra_retry"; old = A[0]
        rows = any(d.glob("select_*.jsonl")) or any(d.glob("exchange_*.jsonl"))
        if rows and (old.get("code_hash") != ST.code_hash() or old.get("protocol_hash") != ST.protocol_hash(X, cfg)):
            atomic(d / "ATTEMPT_INCOMPLETE", f"{name}: attempt-1 rows exist from a different code/protocol; cannot resume\n"); sys.exit(17)
        if (d / "GPU_PREFLIGHT_FAIL").exists(): (d / "GPU_PREFLIGHT_FAIL").rename(d / "GPU_PREFLIGHT_FAIL.attempt1")
        used = max(used, float(R["charged_h"]) * 3600)
    else:
        atomic(d / "ATTEMPT_INCOMPLETE", f"{name}: no further start allowed (attempts={len(A)}, retry={R}); INCOMPLETE\n"); sys.exit(17)
    if used >= cap_s:
        L[key] = used; atomic(RES / "budget_ledger.json", json.dumps(L))
        atomic(d / "BUDGET_EXHAUSTED", f"{name}: ledger shows the cap used ({used/3600:.3f} h)\n"); print(f"{name}: cap already used"); sys.exit(3)
    for f in ("CHILD_COMPLETE", "summary.child.json"):
        if (d / f).exists(): (d / f).unlink()
    t0 = time.time(); a = dict(n=len(A) + 1, kind=kind, token=uuid.uuid4().hex, started_wall=t0, budget_s=cap_s - used,
                               deadline_wall=t0 + cap_s - used, prior_used_s=used, code_hash=ST.code_hash(),
                               protocol_hash=ST.protocol_hash(X, cfg), outcome="running")
    A.append(a); atomic(stp, json.dumps(st, indent=1))            # durable BEFORE launch; raises -> nothing launched
    env = dict(os.environ, E1C_ATTEMPT_TOKEN=a["token"])
    p = subprocess.Popen([sys.executable, str(RUN), "--child", name], env=env, start_new_session=True)
    try: rc = p.wait(timeout=max(0.0, a["deadline_wall"] - time.time()))
    except subprocess.TimeoutExpired:
        try: os.killpg(p.pid, signal.SIGKILL)
        except ProcessLookupError: pass
        p.wait(); rc = None
    end = time.time(); complete = (d / "CHILD_COMPLETE").exists()
    outcome, marker, code = decide(rc, end, a["deadline_wall"], complete)
    try:
        el = min(end, a["deadline_wall"]) - t0 if outcome == "deadline" else end - t0
        L = ledger(); L[key] = used + (cap_s - used if outcome == "deadline" else el); atomic(RES / "budget_ledger.json", json.dumps(L))
        if marker: atomic(d / marker, f"{name}: {outcome} (attempt {a['n']}, child rc={rc})\n")
        if outcome == "done":
            S = json.load(open(d / "summary.child.json")); S["gpu_h"] = L[key] / 3600; S["attempt"] = a["n"]
            atomic(d / "summary.json", json.dumps(S, indent=1)); atomic(d / ".done", time.strftime("%Y-%m-%d %H:%M:%S %Z") + "\n")
        a.update(outcome=outcome, rc=rc, ended_wall=end, elapsed_s=el); atomic(stp, json.dumps(st, indent=1))
    except Exception as e:
        print(f"{name}: bookkeeping failed ({type(e).__name__}); attempt stays 'running' (fail-closed)"); sys.exit(70)
    print(f"{name}: {outcome} (rc={rc})"); sys.exit(code)
