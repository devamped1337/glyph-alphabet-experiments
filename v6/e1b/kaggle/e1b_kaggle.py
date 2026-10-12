# E1b Stage B on Kaggle (PREREG_E1b §2, §4, §9). One notebook = one sub-stage; run cells in order.
# Accelerator: GPU T4 x1 (or P100). Internet ON. No HF token needed (A6: all Stage B models are non-gated); an optional HF_TOKEN Kaggle secret is used if present.
# Results land in /kaggle/working/glyph/v6/e1b/results/<stage>/ ; download them and commit to the repo.
# %% 1. code at the pinned commit (set COMMIT to the commit that recorded CODE_HASH.txt)
import os, subprocess, sys
COMMIT = os.environ.get("E1B_COMMIT", "prereg-e1b-a7"); STAGE = os.environ.get("E1B_STAGE", "B0")   # pinned: tag prereg-e1b-a7 (A7)
subprocess.run("git clone https://github.com/devamped1337/glyph-alphabet-experiments.git /kaggle/working/glyph", shell=True, check=True)
subprocess.run(f"cd /kaggle/working/glyph && git checkout {COMMIT}", shell=True, check=True)
# %% 2. pinned dependencies (nf4 path) + llama.cpp CUDA wheel (pre-registered GGUF fallback, e.g. P100)
subprocess.run("pip install -q 'transformers==4.47.1' 'bitsandbytes==0.47.0' 'accelerate==1.1.1' 'huggingface_hub>=0.26' "
               "'sentence-transformers==3.3.1'", shell=True, check=True)
cap = subprocess.run("nvidia-smi --query-gpu=name,compute_cap --format=csv,noheader", shell=True, capture_output=True, text=True).stdout
print("GPU:", cap)
subprocess.run("pip install -q llama-cpp-python==0.3.2 --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121", shell=True)
# %% 3. optional HF token (A6: not required; never printed), GGUF fallback files only if the B0 load test selects the fallback
try:
    from kaggle_secrets import UserSecretsClient; os.environ["HF_TOKEN"] = UserSecretsClient().get_secret("HF_TOKEN")
except Exception: print("no HF secret (fine: models are non-gated)")
os.environ.setdefault("E1B_GGUF_DIR", "/kaggle/working/gguf")
def fetch_gguf():
    import json; from huggingface_hub import hf_hub_download
    cfg = json.load(open("/kaggle/working/glyph/v6/e1b/config_e1b.json"))
    for n in cfg["models"]["stageB_order"]:
        m = cfg["models"]["stageB"][n]
        try:
            files = [m["gguf_file"]] + ([m["gguf_file"].replace("00001-of", "00002-of")] if "00001-of" in m["gguf_file"] else [])
            for f in files: hf_hub_download(m["gguf_repo"], f, revision=m["gguf_revision"], local_dir=os.environ["E1B_GGUF_DIR"])   # A2 pinned
        except Exception as ex: print("gguf fetch failed", n, ex)
bk = "/kaggle/working/glyph/v6/e1b/results/B0/backend.json"
if os.path.exists(bk) and '"gguf_cuda"' in open(bk).read(): fetch_gguf()
# %% 4. run the stage (results from earlier sub-stages must be copied into results/ first, e.g. from a Kaggle dataset)
r = subprocess.run(f"cd /kaggle/working/glyph/v6/e1b && E1B_PY={sys.executable} bash run.sh {STAGE}", shell=True)
print("exit", r.returncode)   # 7 = nf4 failed -> fallback chosen (cell 5), 3 = budget exhausted (stop & report), 4 = canary fail, 5 = no qualifying pair, 6 = insufficient budget
# %% 5. if B0 chose the GGUF fallback mid-way (nf4 failed), fetch GGUF files and re-run B0 (reserve use (a)/(b))
if STAGE == "B0" and os.path.exists(bk) and '"gguf_cuda"' in open(bk).read() and r.returncode == 7:
    fetch_gguf(); subprocess.run(f"cd /kaggle/working/glyph/v6/e1b && E1B_PY={sys.executable} bash run.sh B0", shell=True)
# %% 6. validate + manifest, then zip results for download
subprocess.run(f"cd /kaggle/working/glyph/v6/e1b && E1B_PY={sys.executable} bash run.sh manifest && E1B_PY={sys.executable} bash run.sh validate", shell=True)
subprocess.run("cd /kaggle/working/glyph/v6/e1b && zip -qr /kaggle/working/e1b_results.zip results", shell=True)
