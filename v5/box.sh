#!/bin/bash
# box stages. usage: v5/box.sh 1|2|3|4   (run from anywhere; logs in v5/logs)
set -euo pipefail; cd "$(dirname "$0")/.."; PY=/workspace/glyph-exp/.venv/bin/python; V=v5; mkdir -p $V/logs
export GLYPH_HOST=box MAX_RSS_GB=14 NTHREADS=8
case "$1" in
 1) $PY $V/det5.py make; $PY $V/det5.py run smol 2>&1 | tee $V/logs/det_smol_box.log
    $PY $V/extract5.py smol 2>&1 | tee $V/logs/extract_smol.log ;;                      # then copy det_state.pt + MANIFEST_box.json to the laptop
 2) $PY $V/det5.py compare | tee $V/logs/det_compare.log                                # needs laptop det_*_laptop.pt, states_qwen.pt, MANIFEST_laptop.json
    $PY $V/negotiate5.py 2>&1 | tee $V/logs/negotiate.log
    N_DEV=40 DEV_ID_LI=1 $PY $V/run5.py smol dev 2>&1 | tee $V/logs/dev_smol.log ;;                          # then copy deliveries_qwen.pt + MANIFEST_box.json to the laptop
 3) $PY $V/prereg5.py | tee $V/logs/prereg.log                                          # needs laptop dev_qwen.json; then copy frozen5.json + MANIFEST_box.json to laptop
    $PY $V/run5.py smol test 2>&1 | tee $V/logs/test_smol.log ;;
 4) $PY $V/analyze5.py | tee $V/logs/analyze.log ;;                                     # needs laptop test_qwen.json
esac
