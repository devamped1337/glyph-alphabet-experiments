#!/bin/bash
# Full E1 run on the box (CPU, llama.cpp Q4_K_M). Detached launch: setsid nohup v6/e1/run_e1.sh > v6/e1/logs/run.log 2>&1 &
set -euo pipefail; cd "$(dirname "$0")"; PY=/workspace/e1venv/bin/python; mkdir -p logs
echo "start $(date)"; git rev-parse HEAD 2>/dev/null || true; sha256sum config_e1.json data/book.json data/cases.json
for m in qwen3b smol17; do echo "== calib $m $(date)"; $PY e1.py calib $m; done
echo "== freeze_gate $(date)"; $PY e1.py freeze_gate
for m in qwen3b smol17; do echo "== test $m $(date)"; $PY e1.py test $m; done
echo "== analyze $(date)"; $PY analyze_e1.py || echo "analyze failed"
echo "== validate $(date)"; $PY ../checks/validate_v6.py --results-dir results --prereg ../PREREG_v6.md && touch logs/VALIDATED || echo "VALIDATION FAILED"
echo "done $(date)"; touch logs/DONE
