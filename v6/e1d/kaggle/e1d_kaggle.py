# E1d stage runner on Kaggle (DRAFT_PLAN §8). Free T4 x1, internet ON, no HF token (Qwen2.5-7B / Falcon3-7B, non-gated).
# E1D_STAGE, E1D_GO and E1D_COMMIT are set by hand in the pushed kernel header, only on Stefan's explicit go.
import os, subprocess, sys
COMMIT = os.environ.get("E1D_COMMIT"); STAGE = os.environ.get("E1D_STAGE")
assert COMMIT and STAGE, "set E1D_COMMIT and E1D_STAGE explicitly (no defaults, no automated launches)"
assert os.environ.get("E1D_GO") == STAGE, "E1D_GO must equal E1D_STAGE"
assert STAGE == "D1-E1d", "only the dev stage is launchable from this code"
subprocess.run("git clone https://github.com/devamped1337/glyph-alphabet-experiments.git /kaggle/working/glyph", shell=True, check=True)
subprocess.run(f"cd /kaggle/working/glyph && git checkout {COMMIT}", shell=True, check=True)
subprocess.run("pip install -q 'transformers==4.47.1' 'bitsandbytes==0.47.0' 'accelerate==1.1.1' 'huggingface_hub>=0.26' "
               "'sentence-transformers==3.3.1'", shell=True, check=True)
print("GPU:", subprocess.run("nvidia-smi --query-gpu=name,compute_cap --format=csv,noheader", shell=True, capture_output=True, text=True).stdout)
D = "/kaggle/working/glyph/v6/e1d"
r = subprocess.run(f"cd {D} && {sys.executable} run_e1d.py --check && {sys.executable} run_e1d.py --stage {STAGE}", shell=True)
print("exit", r.returncode)   # 3 budget, 8 canary, 9 no GPU, 13 not dev, 14 no go, 16 code hash, 17 no start allowed, 18 terminal, 19 projection > cap
subprocess.run(f"cd {D} && zip -qr /kaggle/working/e1d_results.zip results", shell=True)
