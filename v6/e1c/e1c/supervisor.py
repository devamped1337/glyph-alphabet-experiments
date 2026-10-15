"""r5/r6: the E1c stage SUPERVISOR (run_e1c.py --stage). It is the only writer of the attempt state, the budget
ledger, the terminal markers, summary.json and .done. It
  1. runs the gates (go, frozen, D1 eligibility, code hash, book); checks terminal markers, then unresolved
     ('running') attempts, then completion (.done + recorded 'done' outcome);
  2. computes the remaining budget from the cumulative ledger and durably records the attempt (token, deadline)
     BEFORE launching (file fsync + atomic replace + directory fsync); if that write fails, nothing is launched;
  3. launches the stage child in its own process group (killed by the kernel if the supervisor dies) and waits
     until the deadline; at the deadline it SIGKILLs the group;
  4. decides the outcome: done only if the child exited 0, CHILD_COMPLETE exists and the exit was <= the deadline;
  5. writes the ledger, the marker, summary.json + .done, and LAST the attempt outcome.
Clock (r6): the deadline, the wait, the elapsed charge and the completion decision all use CLOCK_MONOTONIC
(time.monotonic, system-wide on Linux, shared with the child); wall times are recorded for audit only.
Fail-closed: if bookkeeping fails BEFORE the final state replace, the attempt stays 'running', which is terminal. If
the final os.replace succeeds but the directory fsync after it fails (exit 70), the visible state may already say
'done' with uncertain crash durability (disclosed limitation; no transactional machinery for this pilot). Otherwise (no retry; .done without a recorded
'done' outcome is not completion). The SIGKILL is issued by a running supervisor; OS scheduling and uninterruptible
waits can delay the actual termination, so the deadline is an enforced kill, not a hard real-time bound."""
import os, sys, json, time, signal, subprocess, uuid, ctypes
from . import RES, HERE
from . import stages as ST
from .book import load_book

RUN = HERE / "run_e1c.py"
OUTCOME = {3: ("budget_admission", "BUDGET_EXHAUSTED", 3), 8: ("canary_fail", "CANARY_FAIL", 8), 9: ("no_gpu rc=9", None, 9)}
_TEST = os.environ.get("E1B_ALLOW_NO_GPU") == "1"

def fsync_dir(d):
    fd = os.open(str(d), os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)

def mkdir_durable(d):
    if not d.exists(): d.mkdir(parents=True); fsync_dir(d.parent)

def atomic(p, text):
    """r6 (GPT r5): file fsync, os.replace, then fsync of the containing directory (the rename is durable)."""
    tmp = p.with_name(p.name + f".{os.getpid()}.tmp")
    with open(tmp, "w") as fh: fh.write(text); fh.flush(); os.fsync(fh.fileno())
    os.replace(tmp, p); fsync_dir(p.parent)

def ledger(): p = RES / "budget_ledger.json"; return json.load(open(p)) if p.exists() else {}

def decide(rc, end, deadline, complete):
    """Pure terminal decision on MONOTONIC times. rc None = killed at the deadline. Deadline wins over a late finish."""
    if rc is None or end > deadline: return "deadline", "BUDGET_EXHAUSTED", 3
    if rc == 0 and complete: return "done", None, 0
    if rc in OUTCOME: return OUTCOME[rc]
    return f"crash rc={rc}", None, 10

def _pdeathsig():
    """In the child, before exec: SIGKILL it if the supervisor dies (Linux prctl PR_SET_PDEATHSIG). Best effort,
    disclosed limits: errors and the prctl return value are ignored; no parent-identity check covers a supervisor death
    before registration; the signal reaches the child only, not its descendants."""
    try: ctypes.CDLL("libc.so.6", use_errno=True).prctl(1, signal.SIGKILL, 0, 0, 0)
    except Exception: pass

def _killpg(pid):
    try: os.killpg(pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError): pass

def gates(cfg, name):
    X = cfg["e1c"]
    if name not in X["caps_h"]: print(f"unknown E1c stage {name}"); sys.exit(2)
    if name in X.get("closed_stages", []): print(f"{name} refused: closed by amendment (kept as recorded)"); sys.exit(20)
    if os.environ.get("E1C_GO") != name: print(f"{name} refused: no explicit go (E1C_GO must equal '{name}')"); sys.exit(14)
    if name == "T1":
        if X["status"] != "frozen": print("T1 refused: E1c is not frozen"); sys.exit(13)
        ok, why = ST.t1_eligibility(X, cfg)
        if not ok: print(f"T1 refused: {why}"); sys.exit(19)
    p = HERE / "CODE_HASH.txt"; pin = p.read_text().strip() if p.exists() else None
    if pin != ST.code_hash(): print(f"{name} refused: code hash != CODE_HASH.txt"); sys.exit(16)
    load_book(cfg, "dev" if ST.is_dev(X, name) else "test")
    return X

def supervise(cfg, name):
    X = gates(cfg, name); d = RES / name; mkdir_durable(RES); mkdir_durable(d); stp = d / "e1c_state.json"
    term = [m for m in ST.TERMINAL if (d / m).exists()]           # 1. terminal markers
    if term: print(f"{name}: terminal marker {term} -> stop and report"); sys.exit(18)
    st = json.load(open(stp)) if stp.exists() else dict(attempts=[], retry=None, cap_h=X["caps_h"][name])
    A, R = st["attempts"], st.get("retry")
    if any(a.get("outcome") == "running" for a in A):              # 2. unresolved attempt (before .done, r6)
        atomic(d / "ATTEMPT_INCOMPLETE", f"{name}: an attempt has no recorded end (fail-closed); INCOMPLETE\n"); print(f"{name}: unresolved attempt -> INCOMPLETE"); sys.exit(17)
    if ST.finished(d): print(f"{name} already finished"); sys.exit(0)   # 3. .done AND recorded 'done'
    if (d / ".done").exists():
        atomic(d / "ATTEMPT_INCOMPLETE", f"{name}: .done without a recorded 'done' outcome; INCOMPLETE\n"); sys.exit(17)
    cap_s = X["caps_h"][name] * 3600; key = f"E1C_{name}"; L = ledger(); used = L.get(key, 0.0)
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
    m0 = time.monotonic(); budget = cap_s - used
    a = dict(n=len(A) + 1, kind=kind, token=uuid.uuid4().hex, started_wall=time.time(), started_mono=m0, budget_s=budget,
             deadline_mono=m0 + budget, prior_used_s=used, code_hash=ST.code_hash(), protocol_hash=ST.protocol_hash(X, cfg), outcome="running")
    A.append(a); atomic(stp, json.dumps(st, indent=1))            # durable BEFORE launch; raises -> nothing launched
    p = subprocess.Popen([sys.executable, str(RUN), "--child", name], env=dict(os.environ, E1C_ATTEMPT_TOKEN=a["token"]),
                         start_new_session=True, preexec_fn=_pdeathsig)
    try: rc = p.wait(timeout=max(0.0, a["deadline_mono"] - time.monotonic()))
    except subprocess.TimeoutExpired: _killpg(p.pid); p.wait(); rc = None
    end = time.monotonic(); _killpg(p.pid)                         # r6: also reap surviving grandchildren in the group
    complete = (d / "CHILD_COMPLETE").exists()
    outcome, marker, code = decide(rc, end, a["deadline_mono"], complete)
    el = budget if outcome == "deadline" else end - m0               # elapsed charge, monotonic, >= 0
    try:
        L = ledger(); L[key] = used + el; atomic(RES / "budget_ledger.json", json.dumps(L))
        if marker: atomic(d / marker, f"{name}: {outcome} (attempt {a['n']}, child rc={rc})\n")
        if outcome == "done":
            S = json.load(open(d / "summary.child.json")); S["gpu_h"] = L[key] / 3600; S["attempt"] = a["n"]
            atomic(d / "summary.json", json.dumps(S, indent=1)); atomic(d / ".done", time.strftime("%Y-%m-%d %H:%M:%S %Z") + "\n")
        if _TEST and os.environ.get("E1C_TEST_FAIL_FINAL_STATE") == "1": raise OSError("test: final state write fails")
        a.update(outcome=outcome, rc=rc, ended_wall=time.time(), ended_mono=end, elapsed_s=el,
                 finalise_s=time.monotonic() - end)                # r6: post-run bookkeeping before the final state write (excludes that write), reported, not charged
        atomic(stp, json.dumps(st, indent=1))
    except Exception as e:
        print(f"{name}: bookkeeping failed ({type(e).__name__}); attempt stays 'running' (fail-closed)"); sys.exit(70)
    print(f"{name}: {outcome} (rc={rc})"); sys.exit(code)
