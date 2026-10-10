#!/bin/bash
# laptop (WSL) stages. usage: bash laptop.sh 1|2|3   from the extracted code dir, e.g. /mnt/c/Users/Admin/glyph/v5
set -euo pipefail; cd "$(dirname "$0")"; PY=~/glyph/.venv/bin/python; mkdir -p logs results
export GLYPH_HOST=laptop MAX_RSS_GB=15 NTHREADS=$(nproc) BS=4 JBATCH=1 RB=8
$PY -c "import sys,torch,transformers; print(sys.version, torch.__version__, transformers.__version__)"; cat COMMIT
case "$1" in
 1) $PY det5.py run smol 2>&1 | tee logs/det_smol_laptop.log                   # SmolLM2-1.7B: cross-machine determinism partner (~7 GB)
    $PY det5.py run qwen 2>&1 | tee logs/det_qwen_laptop.log                   # Qwen2.5-3B fp32 (~12.5 GB), separate process
    $PY extract5.py qwen 2>&1 | tee logs/extract_qwen.log ;;
 2) $PY run5.py qwen dev 2>&1 | tee logs/dev_qwen.log ;;
 3) $PY run5.py qwen test 2>&1 | tee logs/test_qwen.log ;;
esac
( cd results && sha256sum *.pt *.json > SHA256SUMS_laptop.txt ); echo LAPTOP_STAGE_$1_DONE
