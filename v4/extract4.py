"""book-format (T1, inside the prose prompt) and sender-reading (T2, alone) slot states at the FRACS layers. -> results/v4/states_KEY.pt"""
import sys, os, time, torch, numpy as np
sys.path.insert(0, "/workspace/glyph-exp/v4"); os.chdir("/workspace/glyph-exp")
from common4 import *
key = sys.argv[1]; t0 = time.time(); R = Runner(key); L = layer_ids(key, R.nl); M = messages()
S1, S2, tenc = [], [], []
for m in M:
    t = m["t"]; vals = [m[s] for s in SLOTS[t]]; q0 = list(QUESTIONS[t])[0]
    b1 = T1(t, m); ids, pos = encode_positions(R.tok, prompt(t, q0, b1, "prose"), b1, vals); S1.append(R.states(ids, pos, L))
    b2 = "Message: " + T2(t, m); ids, pos = encode_positions(R.tok, b2, b2, vals)
    ts = time.perf_counter(); S2.append(R.states(ids, pos, L)); tenc.append(time.perf_counter() - ts)
pad = lambda X: torch.stack([torch.cat([x, torch.zeros(5 - len(x), *x.shape[1:])]) for x in X])   # t3 has 4 slots
torch.save({"key": key, "layers": L, "n_layers": R.nl, "book_states": pad(S1), "sender_states": pad(S2), "sender_forward_s": tenc,
            "runtime_s": time.time() - t0}, f"results/v4/states_{key}.pt")
print(key, L, len(M), f"{time.time()-t0:.0f}s, sender forward median {np.median(tenc)*1000:.1f} ms")
