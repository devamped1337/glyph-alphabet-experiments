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
def main():
    a = [x for x in sys.argv[1:] if not x.startswith("--")]; bud = float(sys.argv[sys.argv.index("--budget-h") + 1]) if "--budget-h" in sys.argv else 11.0
    want = NAMES if not a or a == ["all"] else a; t0 = time.time()
    for name, cmd, env, est in STEPS:
        if name not in want: continue
        if os.path.exists(os.path.join(MK, name + ".done")): print("skip (done)", name); continue
        used = (time.time() - t0) / 3600 + float(os.environ.get("SESSION_USED_H", 0))
        if used + est / 60 > bud: print(f"STOP: {used:.2f} h used, {name} needs ~{est} min > budget {bud} h. Save Version, then resume."); return 2
        print(f"=== {name}  (est {est} min, {used:.2f} h used)", flush=True); ts = time.time()
        if cmd is None: free_cache(name.split("_", 1)[1])
        else:
            with open(os.path.join(LOG, name + ".log"), "a") as lf:
                p = subprocess.Popen([PY, os.path.join(HERE, cmd[0])] + cmd[1:], env={**os.environ, **env}, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                for line in p.stdout: print(line, end="", flush=True); lf.write(line)
                if p.wait() != 0: print(f"FAILED {name} (exit {p.returncode}); log {lf.name}. Fix and re-run: done steps are skipped."); return 1
        json.dump({"step": name, "minutes": (time.time() - ts) / 60, "end": time.strftime("%Y-%m-%dT%H:%M:%S%z")}, open(os.path.join(MK, name + ".done"), "w"))
    print("ALL REQUESTED STEPS DONE"); return 0
if __name__ == "__main__": sys.exit(main())
