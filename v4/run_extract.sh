cd /workspace/glyph-exp/v4
for k in qwen smol pythia; do NTHREADS=3 ../.venv/bin/python extract4.py $k > ../logs/v4/extract_$k.log 2>&1 & done
wait; echo EXDONE > ../logs/v4/extract_done
