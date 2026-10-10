cd /workspace/glyph-exp/v4
for r in qwen smol pythia; do NTHREADS=8 ../.venv/bin/python run4.py $r dev > ../logs/v4/dev_$r.log 2>&1; done
../.venv/bin/python select4.py > ../logs/v4/select.log 2>&1
for r in qwen smol pythia; do NTHREADS=8 ../.venv/bin/python run4.py $r test > ../logs/v4/test_$r.log 2>&1; done
echo PIPEDONE > ../logs/v4/pipe_done
