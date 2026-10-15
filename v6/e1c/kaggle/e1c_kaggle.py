# E1c stage runner on Kaggle (PREREG_E1c §8). Free T4 x1, internet ON, no HF token (all models non-gated).
# STAGE, E1C_GO and E1C_COMMIT are set by hand in the pushed kernel, per stage, only on Stefan's explicit go.
import os, subprocess, sys
COMMIT = os.environ.get("E1C_COMMIT"); STAGE = os.environ.get("E1C_STAGE")
assert COMMIT and STAGE, "set E1C_COMMIT and E1C_STAGE explicitly (no defaults, no automated launches)"
assert os.environ.get("E1C_GO") == STAGE, "E1C_GO must equal E1C_STAGE"
subprocess.run("git clone https://github.com/devamped1337/glyph-alphabet-experiments.git /kaggle/working/glyph", shell=True, check=True)
subprocess.run(f"cd /kaggle/working/glyph && git checkout {COMMIT}", shell=True, check=True)
RC = os.environ.get("E1C_RESULTS_COMMIT")   # infra retry only: overlay v6/e1c/results (state with the authorised retry + ledger)
if RC: subprocess.run(f"cd /kaggle/working/glyph && git checkout {RC} -- v6/e1c/results && test -f v6/e1c/results/{STAGE}/e1c_state.json", shell=True, check=True)
subprocess.run("pip install -q 'transformers==4.47.1' 'bitsandbytes==0.47.0' 'accelerate==1.1.1' 'huggingface_hub>=0.26' "
               "'sentence-transformers==3.3.1'", shell=True, check=True)
print("GPU:", subprocess.run("nvidia-smi --query-gpu=name,compute_cap --format=csv,noheader", shell=True, capture_output=True, text=True).stdout)
D = "/kaggle/working/glyph/v6/e1c"
r = subprocess.run(f"cd {D} && {sys.executable} run_e1c.py --check && {sys.executable} run_e1c.py --stage {STAGE}", shell=True)
print("exit", r.returncode)   # 3 budget, 8 canary, 9 no GPU, 13 not frozen, 14 no go, 16 code hash, 17 no start allowed, 18 terminal marker, 19 T1 not eligible
subprocess.run(f"cd {D} && zip -qr /kaggle/working/e1c_results.zip results", shell=True)
