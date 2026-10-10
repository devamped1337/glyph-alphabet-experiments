cd /workspace/glyph-exp
while [ ! -f logs/v4/pipe_done ]; do sleep 30; done
.venv/bin/python v4/tables4.py > logs/v4/tables.log 2>&1
echo TABLESDONE >> logs/v4/tables.log
