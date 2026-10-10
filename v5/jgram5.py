"""J-gram as a SEPARATE process (review fix v5.4): loads only the model in JGRAM_DTYPE (default float32) and updates the jlens field of an
existing states file. Forward extraction stays fp32 in extract5.py (run with JPROMPTS=0).  usage: jgram5.py MODEL"""
import sys
from common5 import *
key = sys.argv[1]; t0 = time.time(); S = load(f"states_{key}.pt"); JD = os.environ.get("JGRAM_DTYPE", "float32")
R = Runner(key, dtype=getattr(torch, JD)); M = messages(); have = set(S["mids"])
NJ, JB, NP = int(os.environ.get("JPROMPTS", 8)), int(os.environ.get("JBATCH", 2)), int(os.environ.get("JPROBES", 4))
tr = [m for m in M if m["split"] == "train" and m["id"] in have]; rng = np.random.default_rng(0); pick = [tr[i] for i in rng.choice(len(tr), min(NJ, len(tr)), replace=False)]
def ids_of(m): t = m["t"]; return R.ids64(t, list(QUESTIONS[t])[0], body(t, m), "prose")[0]
G = None
for b0 in range(0, len(pick), JB):
    g = R.jgram([ids_of(m) for m in pick[b0:b0 + JB]], R.L, NP, seed=b0); G = g if G is None else {k: G[k] + g[k] for k in G}
    print("jgram batch", b0, f"{time.time()-t0:.0f}s RSS {rss_gb():.1f} peak {hwm_gb():.1f} GB", flush=True)
jl = {}
for k in R.L:
    w, V = torch.linalg.eigh(G[k]); jl[k] = {"evecs": V[:, -KP:].flip(1).float(), "evals": w[-KP:].flip(0).float(), "trace": float(w.sum())}
jl["_meta"] = {"jgram_weights_dtype": JD, "separate_process": True, "prompts": NJ, "probes": NP, "jbatch": JB, "peak_rss_gb": hwm_gb(), "commit": commit()}
S["jlens"] = jl; S["jgram_env"] = env_info()
save(S, f"states_{key}.pt", {"model": MODELS[key], "stage": "states + J-gram (separate process)", "jgram_weights_dtype": JD, "jgram_peak_rss_gb": hwm_gb()})
print("done jgram", key, JD, f"{time.time()-t0:.0f}s peak {hwm_gb():.1f} GB")
