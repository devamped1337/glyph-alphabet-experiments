#!/bin/bash
# detached box orchestrator: runs each remaining box stage once its laptop inputs appear. Markers in v5/logs/*.done make it resumable.
cd /workspace/glyph-exp; R=v5/results; L=v5/logs; mkdir -p $L
log(){ echo "$(date '+%F %T') $*" | tee -a $L/orchestrate.log; }
waitfor(){ while true; do ok=1; for f in "$@"; do [ -s "$f" ] || ok=0; done; [ $ok = 1 ] && return; sleep 60; done; }
jgram_ok(){ .venv/bin/python -c "import torch,sys; s=torch.load('$R/states_qwen.pt',weights_only=False,map_location='cpu'); sys.exit(0 if s['jlens'].get('_meta',{}).get('separate_process') else 1)"; }
if [ ! -f $L/box2.done ]; then
  log "waiting for states_qwen.pt (with J-gram) + MANIFEST_laptop.json"
  while true; do waitfor $R/states_qwen.pt $R/MANIFEST_laptop.json; sleep 30; break; done   # v5.4 run: Qwen J-gram infeasible on the laptop (bf16 too slow, fp32 OOM); jlens basis skipped
  log "box stage 2 start"; bash v5/box.sh 2 > $L/box2.out 2>&1 && touch $L/box2.done; log "box stage 2 end rc=$?"
fi
if [ ! -f $L/box3.done ]; then
  log "waiting for dev_qwen.json"; waitfor $R/dev_qwen.json $R/dev_smol.json
  log "box stage 3 start"; bash v5/box.sh 3 > $L/box3.out 2>&1 && touch $L/box3.done; log "box stage 3 end"
fi
if [ ! -f $L/box4.done ]; then
  log "waiting for test_qwen.json"; waitfor $R/test_qwen.json $R/test_smol.json
  log "box stage 4 start"; bash v5/box.sh 4 > $L/box4.out 2>&1 && touch $L/box4.done; log "box stage 4 end"
fi
log ALL_BOX_STAGES_DONE
