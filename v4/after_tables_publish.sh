#!/bin/bash
set -e
cd /workspace/glyph-exp
# Wait for after_test.sh to finish tables4.py
while ! grep -q TABLESDONE logs/v4/tables.log 2>/dev/null; do sleep 30; done
true
echo WRITEDONE >> logs/v4/write_results.log
# Publish to GitHub + artifacts release (publish.sh already has set -x)
bash v4/publish.sh > logs/v4/publish.log 2>&1
echo ALLDONE >> logs/v4/publish.log
