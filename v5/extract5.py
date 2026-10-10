"""Extract slot states (book format inside a 64-token receiver prompt; sender reading in a 64-token sender prompt) at
emb + candidate layers, and a J-lens-inspired subspace per layer.  usage: extract5.py MODEL   -> results/states_MODEL.pt
env: BS (batch, default 8), JPROMPTS (default 8, 0 = skip), JPROBES (cotangent draws per batch, default 4), JBATCH (default 2), SMOKE=N (first N msgs per task)"""
import sys
from common5 import *
key = sys.argv[1]; t0 = time.time(); R = Runner(key); M = messages()
if os.environ.get("SMOKE"):
    n = int(os.environ["SMOKE"]); keep = []; rs = np.random.default_rng(0)
    for t in SLOTS:
        for sp, k in (("train", n), ("dev", 4), ("test", 4)):
            pool = [m for m in M if m["t"] == t and m["split"] == sp]; keep += [pool[i] for i in sorted(rs.choice(len(pool), min(k, len(pool)), replace=False))]
    M = keep
OLD = None
if os.environ.get("ONLY_NEW"):   # append messages missing from an existing states file (prompts/layers unchanged for the old ones)
    OLD = load(f"states_{key}.pt"); have = set(OLD["mids"]); M = [m for m in M if m["id"] not in have]; print("ONLY_NEW: extracting", len(M), "new messages", flush=True)
BS = int(os.environ.get("BS", 8)); P = 5
def sender64(m):
    core = sender_prompt(m["t"], m); cids = R.tok.encode(core, add_special_tokens=False); assert len(cids) <= CTX
    fill = R.tok.encode(FILLER, add_special_tokens=False)[: CTX - len(cids)]; ids = fill + cids
    return ids, R.positions(ids, len(fill), core, sender_values(m["t"], m))
def book64(m):
    t = m["t"]; q = list(QUESTIONS[t])[0]; ids, off, core = R.ids64(t, q, body(t, m), "prose")
    return ids, R.positions(ids, off, core, [m[s] for s in SLOTS[t]])
pad = lambda p: p + [p[-1]] * (P - len(p))
book = torch.zeros(len(M), P, len(R.L), R.d, dtype=torch.float16); send = torch.zeros_like(book); tfwd = []
for kind, fn, dst in (("book", book64, book), ("sender", sender64, send)):
    for b0 in range(0, len(M), BS):
        chunk = M[b0:b0 + BS]; built = [fn(m) for m in chunk]
        ts = time.perf_counter(); S = R.read([x[0] for x in built], [pad(x[1]) for x in built], R.L); tfwd.append((time.perf_counter() - ts) / len(chunk))
        dst[b0:b0 + len(chunk)] = S.half(); pass
        if b0 % (BS * 25) == 0: print(kind, b0, len(M), f"{time.time()-t0:.0f}s RSS {guard(kind):.1f} GB", flush=True)
jl = OLD["jlens"] if OLD is not None else {}
def pack(jl):
    mids = [m["id"] for m in M]; b, sd = book, send
    if OLD is not None: mids = OLD["mids"] + mids; b = torch.cat([OLD["book_states"], book]); sd = torch.cat([OLD["sender_states"], send])
    return {"key": key, "model": MODELS[key], "keys": R.L, "n_layers": R.nl, "d": R.d, "mids": mids, "book_states": b, "sender_states": sd,
            "jlens": jl, "sender_forward_s_median": float(np.median(tfwd)), "runtime_s": time.time() - t0, "env": env_info(), "peak_rss_gb": PEAK[0],
            "weights_dtype": "float32", "batch": BS, "appended_from": (OLD or {}).get("env", {}).get("commit")}
PEAK = [hwm_gb()]
save(pack(jl), f"states_{key}.pt", {"model": MODELS[key], "stage": "states (before J-gram)"})   # saved before the backward pass so an OOM cannot lose it
NJ = int(os.environ.get("JPROMPTS", 8)) if OLD is None else 0
if NJ:
    JD = os.environ.get("JGRAM_DTYPE", "float32")
    if JD != "float32":   # RAM: the fp32 backward pass peaked at 17.5 GB on the 17 GB laptop, so the J-gram reloads weights in bf16 (forward states stay fp32)
        del R.hf; import gc; gc.collect(); R = Runner(key, dtype=getattr(torch, JD))
    tj = time.time(); rng = np.random.default_rng(0); tr = [m for m in M if m["split"] == "train"]
    pick = [tr[i] for i in rng.choice(len(tr), min(NJ, len(tr)), replace=False)]; JB = int(os.environ.get("JBATCH", 2)); G = None
    for b0 in range(0, len(pick), JB):
        g = R.jgram([book64(m)[0] for m in pick[b0:b0 + JB]], R.L, int(os.environ.get("JPROBES", 4)), seed=b0)
        G = g if G is None else {k: G[k] + g[k] for k in G}; PEAK[0] = hwm_gb()
    for k in R.L:
        w, V = torch.linalg.eigh(G[k]); jl[k] = {"evecs": V[:, -KP:].flip(1).float(), "evals": w[-KP:].flip(0).float(), "trace": float(w.sum())}
    print("jgram", f"{time.time()-tj:.0f}s, peak RSS {hwm_gb():.2f} GB", flush=True)
    jl["_meta"] = {"jgram_weights_dtype": os.environ.get("JGRAM_DTYPE", "float32"), "prompts": NJ, "probes": int(os.environ.get("JPROBES", 4)), "jbatch": JB}
    save(pack(jl), f"states_{key}.pt", {"model": MODELS[key], "stage": "states + J-gram", "peak_rss_gb": PEAK[0], "jgram_weights_dtype": jl["_meta"]["jgram_weights_dtype"]})
print("done", key, f"{time.time()-t0:.0f}s")
