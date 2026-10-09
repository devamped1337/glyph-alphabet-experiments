"""Fit a J-lens on CPU. usage: fit_lens.py KEY N_PROMPTS MAX_LEN"""
import sys, time, logging, torch, jlens
from common import *
jlens.configure_logging() if hasattr(jlens, "configure_logging") else None
logging.basicConfig(level=logging.INFO)
key, n, L = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
m, tok, hf = load(key)
nl = m.n_layers
src = list(range(nl // 6, (5 * nl) // 6))   # middle-ish band only (saves backward cost)
print(m, "source layers", src, flush=True)
t = time.time()
lens = jlens.fit(m, fit_prompts()[:n], source_layers=src, dim_batch=16, max_seq_len=L,
                 checkpoint_path=f"lenses/{key}_ckpt.pt", checkpoint_every=4)
lens.save(lens_path(key))
print(f"DONE {key} prompts={lens.n_prompts} L={L} fit_time={time.time()-t:.0f}s", flush=True)
