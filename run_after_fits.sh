#!/bin/sh
# waits for the lens-fit chain, then runs extraction, analysis and self-injection
while kill -0 1166260 2>/dev/null; do sleep 20; done
cd /workspace/glyph-exp
date +%s >> logs/timing.txt; for k in qwen smol; do .venv/bin/python extract.py $k > logs/extract_$k.log 2>&1; done; echo "extract $k done" >> logs/timing.txt; date +%s >> logs/timing.txt
.venv/bin/python analyze.py qwen smol > logs/analyze.log 2>&1
date +%s >> logs/timing.txt; .venv/bin/python inject.py smol smol > logs/inject_smol_smol.log 2>&1; echo "inject $k done" >> logs/timing.txt; date +%s >> logs/timing.txt
date +%s >> logs/timing.txt; .venv/bin/python inject.py qwen qwen > logs/inject_qwen_qwen.log 2>&1; echo "inject $k done" >> logs/timing.txt; date +%s >> logs/timing.txt
echo ALLDONE > logs/pipeline.done
