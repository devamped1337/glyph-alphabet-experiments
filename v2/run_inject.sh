cd /workspace/glyph-exp
for pair in "qwen qwen" "smol smol" "smol qwen" "qwen smol"; do set -- $pair; NTHREADS=8 .venv/bin/python v2/inject_v2.py $1 $2 2>&1 | grep -v Loading > logs/v2/inject_$2_into_$1.log; done
echo ALLDONE
