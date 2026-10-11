#!/bin/bash
# E1b single entrypoint per stage (PREREG_E1b §11). Usage: bash v6/e1b/run.sh <build|A|B0|B0b|B1|B2|B3|validate|test>
# Stage A runs on the box CPU (llama.cpp). Stage B runs on Kaggle (see kaggle/e1b_kaggle.py). Detached on the box:
#   setsid nohup bash v6/e1b/run.sh A > v6/e1b/logs/A.log 2>&1 &
set -euo pipefail; cd "$(dirname "$0")"; mkdir -p logs
PY=${E1B_PY:-/workspace/e1venv/bin/python}; [ -x "$PY" ] || PY=python3
st=${1:?stage}
echo "== $st start $(date)"; git rev-parse HEAD 2>/dev/null || true; cat CODE_HASH.txt; sha256sum config_e1b.json
case "$st" in
  test) $PY -m unittest discover -s tests -v ;;
  validate) $PY ../checks/validate_v6.py --e1b --results-dir . ;;
  manifest) $PY -c "import sys; sys.path.insert(0,'.'); from e1b.validate import write_manifest; print(write_manifest('.'))" ;;
  *) $PY tools/code_hash.py --check && $PY run_e1b.py --stage "$st" ;;
esac
echo "== $st end $(date)"
