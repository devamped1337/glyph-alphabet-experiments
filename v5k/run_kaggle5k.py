"""v5k resumable stage driver (Kaggle GPU). Each step runs in its OWN subprocess (one model in memory at a time) and leaves a
marker in $GLYPH_OUT/.stages/<step>.done; finished steps are skipped on re-run, so a new session continues where the last stopped.
usage: run_kaggle5k.py [STEP ...|all] [--budget-h 11]      env: GLYPH_OUT, SMOKE (passes through), HF_HOME (model cache, NOT in /kaggle/working)
Steps (in order): see STEPS below.  'est_min' is a rough 2x T4 estimate used by the session-budget guard."""
import os, sys, time, json, shutil, subprocess, glob
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from spec5 import MODELS
K = list(MODELS); PY = sys.executable
OUT = os.environ.setdefault("GLYPH_OUT", os.path.join(HERE, "results")); MK = os.path.join(OUT, ".stages"); LOG = os.path.join(OUT, "logs")
os.makedirs(MK, exist_ok=True); os.makedirs(LOG, exist_ok=True)
JENV = {"JPROMPTS": os.environ.get("JPROMPTS", "32"), "JPROBES": os.environ.get("JPROBES", "8"), "JBATCH": os.environ.get("JBATCH", "2")}  # GPU: 4x the v5 J-gram prompts, 2x probes
STEPS = [("det_make", ["det5.py", "make"], {}, 1)]
STEPS += [(f"det_{k}", ["det5.py", "run", k], {}, 10) for k in K]
for k in K: STEPS += [(f"extract_{k}", ["extract5.py", k], {"JPROMPTS": "0", "BS": "16"}, 25), (f"jgram_{k}", ["jgram5.py", k], JENV, 15), (f"free_{k}", None, {}, 0)]
STEPS += [("det_compare", ["det5.py", "compare"], {}, 1), ("negotiate", ["negotiate5.py"], {}, 30)]
STEPS += [(f"dev_{k}", ["run5.py", k, "dev"], {"N_DEV": "40", "DEV_ID_LI": "1", "RB": "32"}, 45) for k in K]
STEPS += [("prereg", ["prereg5.py"], {}, 1)]
STEPS += [(f"test_{k}", ["run5.py", k, "test"], {"RB": "32", "TEST_SEEDS": os.environ.get("TEST_SEEDS", "0,1,2")}, 90) for k in K]
STEPS += [("analyze", ["analyze5.py"], {}, 2), ("jlens_compare", ["jlens_compare5k.py"], {}, 2)]
NAMES = [s[0] for s in STEPS]
def free_cache(k):
    if shutil.disk_usage(os.environ.get("HF_HOME", os.path.expanduser("~"))).free > 40e9: print("disk ok, keeping cache for", k); return   # drop a model's weights from the HF cache once its last pre-negotiation step is done (disk), it is re-downloaded for dev/test
    hub = os.path.join(os.environ.get("HF_HOME", os.path.expanduser("~/.cache/huggingface")), "hub")
    for d in glob.glob(os.path.join(hub, "models--" + MODELS[k][0].replace("/", "--"))): shutil.rmtree(d, ignore_errors=True); print("freed", d)
MODEL_OF = {n: next((k for k in K if n.endswith("_" + k)), None) for n in NAMES}
def ensure_model(k):
    """download (or verify cached) weights with visible per-file progress, before the step process loads them"""
    name, rev = MODELS[k]
    if os.path.isdir(name): print(f"[model] {k}: local path {name}", flush=True); return
    from huggingface_hub import HfApi, hf_hub_download
    files = [x for x in HfApi().list_repo_files(name, revision=rev) if x.endswith((".json", ".safetensors", ".model", ".txt", ".tiktoken")) or "token" in x]
    t = time.time(); tot = 0
    print(f"[model] {k}: {name}@{rev[:10]}, {len(files)} files", flush=True)
    for i, x in enumerate(files, 1):
        p = hf_hub_download(name, x, revision=rev); sz = os.path.getsize(p); tot += sz
        print(f"[model] {k}: {i}/{len(files)} {x} {sz/1e9:.2f} GB (total {tot/1e9:.1f} GB, {time.time()-t:.0f}s)", flush=True)
def parse(argv):
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("steps", nargs="*", default=["all"]); ap.add_argument("--budget-h", type=float, default=11.0)
    ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args(argv)
    want = NAMES if a.steps in ([], ["all"]) else a.steps
    bad = [x for x in want if x not in NAMES]
    if bad: raise SystemExit(f"unknown step(s) {bad}; valid: {NAMES}")
    return a, want
def status(n): return "DONE" if os.path.exists(os.path.join(MK, n + ".done")) else "todo"
def plan(want, bud):
    import torch
    print(f"[plan] GLYPH_OUT={OUT}  python={PY}  budget={bud} h  SMOKE={os.environ.get('SMOKE')}  GLYPH_MODELS override={'yes' if os.environ.get('GLYPH_MODELS') else 'no'}")
    print(f"[plan] cuda={torch.cuda.is_available()} gpus={torch.cuda.device_count()} {[torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())]}")
    print(f"[plan] models: {MODELS}")
    todo = 0
    for name, cmd, env, est in STEPS:
        if name not in want: continue
        st = status(name); todo += est if st == "todo" else 0
        print(f"[plan] {st:4s} {name:16s} ~{est:3d} min  {' '.join(cmd) if cmd else '(free HF cache if disk low)'}  {env or ''}")
    print(f"[plan] {sum(status(n) == 'todo' for n in want)} of {len(want)} steps to run, ~{todo/60:.1f} h estimated")
    if not want: raise SystemExit("[plan] no steps selected")
def main():
    a, want = parse(sys.argv[1:]); bud = a.budget_h; plan(want, bud)
    if a.dry_run: return 0
    import torch
    if os.environ.get("GLYPH_DEVICE", "cuda") == "cuda" and not torch.cuda.is_available(): print("[FAILED] GLYPH_DEVICE=cuda but no GPU visible", flush=True); return 1
    t0 = time.time()
    for name, cmd, env, est in STEPS:
        if name not in want: continue
        if status(name) == "DONE": print(f"[skip] {name} (done)", flush=True); continue
        used = (time.time() - t0) / 3600 + float(os.environ.get("SESSION_USED_H", 0))
        if used + est / 60 > bud: print(f"[STOP] {used:.2f} h used, {name} needs ~{est} min > budget {bud} h. Save Version, then resume.", flush=True); return 2
        print(f"[start] {name} at {time.strftime('%H:%M:%S')} (est {est} min, {used:.2f} h used)", flush=True); ts = time.time()
        if cmd is None: free_cache(MODEL_OF[name])
        else:
            if MODEL_OF[name]: ensure_model(MODEL_OF[name])
            tail = []
            with open(os.path.join(LOG, name + ".log"), "a") as lf:
                p = subprocess.Popen([PY, "-u", os.path.join(HERE, cmd[0])] + cmd[1:], env={**os.environ, **env}, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
                for line in p.stdout: print(f"  {line}", end="", flush=True); lf.write(line); tail = (tail + [line])[-60:]
                rc = p.wait()
            if rc != 0:
                print(f"[FAILED] {name} exit {rc} after {(time.time()-ts)/60:.1f} min. Last output:\n" + "".join(tail), flush=True); return 1
            if not glob.glob(os.path.join(OUT, "*")): print(f"[FAILED] {name} exited 0 but {OUT} is empty", flush=True); return 1
        json.dump({"step": name, "minutes": (time.time() - ts) / 60, "end": time.strftime("%Y-%m-%dT%H:%M:%S%z")}, open(os.path.join(MK, name + ".done"), "w"))
        print(f"[end] {name} at {time.strftime('%H:%M:%S')} ({(time.time()-ts)/60:.1f} min)", flush=True)
    missing = [n for n in want if status(n) != "DONE"]
    if missing: print(f"[FAILED] steps not done: {missing}", flush=True); return 1
    print(f"[ok] ALL {len(want)} REQUESTED STEPS DONE", flush=True); return 0
if __name__ == "__main__": sys.exit(main())
