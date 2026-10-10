"""v5 shared runtime: pinned model loading, 64-token batched forwards with per-row patching (embedding or block output),
state recording, RAM guard, sha256 manifests and code-commit pinning."""
import os, sys, json, time, glob, socket, hashlib, platform, resource
import numpy as np, torch, transformers
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from spec5 import *
OUT = os.environ.get("GLYPH_OUT", os.path.join(HERE, "results")); os.makedirs(OUT, exist_ok=True)
HOST = os.environ.get("GLYPH_HOST", "box" if os.path.exists("/workspace/glyph-exp") else "laptop")
torch.set_num_threads(int(os.environ.get("NTHREADS", os.cpu_count() or 4)))
MAX_RSS_GB = float(os.environ.get("MAX_RSS_GB", 15.0))

# ---------- provenance ----------
def code_hash(d=HERE):
    h = hashlib.sha256()
    for f in sorted(glob.glob(os.path.join(d, "*.py")) + glob.glob(os.path.join(d, "*.sh"))):
        h.update(os.path.basename(f).encode()); h.update(open(f, "rb").read())
    return h.hexdigest()
def commit():
    c = open(os.path.join(HERE, "COMMIT")).read().strip()
    if not c.startswith("$Format"): return c                     # git archive (export-subst) fills this in
    repo = "/workspace/glyph-repo"
    try:                                                          # box working copy: accept only if identical to the committed v5/
        import subprocess
        head = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        here = code_hash(); there = code_hash(os.path.join(repo, "v5"))
        if head and here == there and not subprocess.run(["git", "-C", repo, "status", "--porcelain", "v5"], capture_output=True, text=True).stdout.strip():
            return head
    except Exception: pass
    return "UNCOMMITTED-" + code_hash()[:12]
def env_info():
    return {"host": HOST, "hostname": socket.gethostname(), "python": platform.python_version(), "torch": torch.__version__,
            "transformers": transformers.__version__, "numpy": np.__version__, "threads": torch.get_num_threads(), "machine": platform.machine(),
            "cpu": _cpu(), "commit": commit(), "code_sha256": code_hash(), "time": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
def _cpu():
    try: return [l.split(":", 1)[1].strip() for l in open("/proc/cpuinfo") if l.startswith("model name")][0]
    except Exception: return platform.processor()
def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()
def manifest_add(path, extra=None):
    mf = os.path.join(OUT, f"MANIFEST_{HOST}.json"); D = json.load(open(mf)) if os.path.exists(mf) else {}
    D[os.path.basename(path)] = {"sha256": sha256(path), "bytes": os.path.getsize(path), "commit": commit(), "code_sha256": code_hash(),
                                 "host": HOST, "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"), **(extra or {})}
    json.dump(D, open(mf, "w"), indent=1)
def save(obj, name, extra=None):
    p = os.path.join(OUT, name)
    if name.endswith(".json"): json.dump(obj, open(p, "w"), default=str)
    else: torch.save(obj, p)
    manifest_add(p, extra); print("saved", p, os.path.getsize(p), "bytes", flush=True); return p
def load(name):
    """load a result file only if its sha256 matches an entry in some MANIFEST_*.json in OUT (files are moved between machines)"""
    p = os.path.join(OUT, name); s = sha256(p); ok = False
    for mf in glob.glob(os.path.join(OUT, "MANIFEST_*.json")):
        e = json.load(open(mf)).get(name)
        if e and e["sha256"] == s: ok = True
    if not ok and not os.environ.get("ALLOW_UNVERIFIED"): raise RuntimeError(f"{name}: sha256 {s[:12]} not in any manifest")
    return json.load(open(p)) if name.endswith(".json") else torch.load(p, weights_only=False)
def rss_gb():
    try:
        for l in open("/proc/self/status"):
            if l.startswith("VmRSS"): return int(l.split()[1]) / 1e6
    except Exception: return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6
def hwm_gb():
    try:
        for l in open("/proc/self/status"):
            if l.startswith("VmHWM"): return int(l.split()[1]) / 1e6
    except Exception: return rss_gb()
def guard(where=""):
    r = rss_gb()
    if r > MAX_RSS_GB: raise MemoryError(f"RSS {r:.1f} GB > {MAX_RSS_GB} GB at {where}")
    return r
def layer_keys(nl): return ["emb"] + [int(round(f * nl)) for f in FRACS]

# ---------- model runner ----------
class Runner:
    def __init__(self, key):
        name, rev = MODELS[key]; self.key = key
        self.tok = transformers.AutoTokenizer.from_pretrained(name, revision=rev)
        self.hf = transformers.AutoModelForCausalLM.from_pretrained(name, revision=rev, dtype=torch.float32, low_cpu_mem_usage=True).eval()
        for p in self.hf.parameters(): p.requires_grad_(False)
        self.layers = self.hf.model.layers; self.nl = len(self.layers); self.L = layer_keys(self.nl); self.d = self.hf.config.hidden_size
        self.patches = []; self.rec = None; self.grad_taps = None
        self.hf.model.embed_tokens.register_forward_hook(self._mk("emb"))
        for li, l in enumerate(self.layers): l.register_forward_hook(self._mk(li))
        print(key, name, rev[:10], "layers", self.nl, "d", self.d, "patch/read keys", self.L, f"RSS {guard('load'):.1f} GB", flush=True)
    def _mk(self, lk):
        def hook(mod, inp, out):
            h = out[0] if isinstance(out, tuple) else out
            if self.grad_taps is not None and lk == "emb":
                h = h.detach().requires_grad_(True); self.grad_taps["emb"] = h
                return h
            for (pl, rows, pos, H) in self.patches:
                if pl == lk: h[rows[:, None], pos[None, :]] = H.to(h.dtype)
            if self.grad_taps is not None and lk in self.grad_taps.get("want", ()): self.grad_taps[lk] = h
            if self.rec is not None and lk in self.rec[0]: self.rec[1][lk] = h.detach()[:, self.rec[2]].clone() if self.rec[2] is not None else h.detach().clone()
            return out
        return hook
    def ids64(self, t, q, text, fmt):
        ids, off, core = fit64(self.tok, t, q, text, fmt); assert len(ids) == CTX; return ids, off, core
    def positions(self, ids, off, core, values):
        """last token of each value string (searched left to right inside the message part of core)"""
        enc = self.tok(core, add_special_tokens=False, return_offsets_mapping=True); om = enc["offset_mapping"]
        assert enc["input_ids"] == ids[off:], "core re-tokenisation mismatch"
        st = core.rfind("Message: ") + 9 if "Message: " in core else core.rfind("\n") + 1; pos, cur = [], st
        for v in values:
            i = core.find(v, cur); assert i >= 0, (core, v); a, b = i, i + len(v); cur = b
            cand = [k for k, (x, y) in enumerate(om) if x < b and y > a]; pos.append(off + cand[-1])
        return pos
    @torch.no_grad()
    def read(self, batch_ids, batch_pos, keys):
        """batch_ids [B,64]; batch_pos list of position lists (same length P); returns [B, P, len(keys), d] float32"""
        ids = torch.tensor(batch_ids); self.rec = (set(keys), {}, None); self.hf(input_ids=ids, use_cache=False); R = self.rec[1]; self.rec = None
        bp = torch.tensor(batch_pos); ar = torch.arange(len(batch_ids))[:, None]
        return torch.stack([R[k][ar, bp] for k in keys], 2).float()
    @torch.no_grad()
    def logits(self, ids, patches=()):
        """ids [B,T] tensor; patches: list of (layer_key, rows LongTensor, pos LongTensor, H [len(rows), P, d]). Last-position logits [B,V]."""
        self.patches = list(patches)
        try: return self.hf(input_ids=ids, use_cache=False).logits[:, -1].float()
        finally: self.patches = []
    def jgram(self, batch_ids, keys, nprobe, seed):
        """J-lens-inspired: E_v[(J^T v)(J^T v)^T] with Gaussian cotangents v on the final hidden state (all positions), summed over source positions.
        Its top eigenvectors span the directions at layer k that most move the final residual stream. Returns {k: [d,d] float64}."""
        g = torch.Generator().manual_seed(seed); G = {k: torch.zeros(self.d, self.d, dtype=torch.float64) for k in keys}
        ids = torch.tensor(batch_ids)
        for _ in range(nprobe):
            self.grad_taps = {"want": set(k for k in keys if k != "emb")}
            with torch.enable_grad():
                out = self.hf.model(input_ids=ids, use_cache=False).last_hidden_state
                v = torch.randn(out.shape, generator=g); taps = [self.grad_taps[k] for k in keys]
                grads = torch.autograd.grad((out * v).sum(), taps)
            self.grad_taps = None
            for k, gr in zip(keys, grads): gg = gr.reshape(-1, self.d).double(); G[k] += gg.T @ gg
            guard("jgram")
        return G
    def first_tids(self, words): return [self.tok.encode(" " + w, add_special_tokens=False)[0] for w in words]
