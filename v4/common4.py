import os, torch, transformers, numpy as np
from spec import *
torch.set_num_threads(int(os.environ.get("NTHREADS", 8)))
def load(key):
    tok = transformers.AutoTokenizer.from_pretrained(MODELS[key]); hf = transformers.AutoModelForCausalLM.from_pretrained(MODELS[key], dtype=torch.float32).eval()
    layers = hf.gpt_neox.layers if key == "pythia" else hf.model.layers
    return tok, hf, layers
def layer_ids(key, nl): return [int(round(f * nl)) for f in FRACS]
def spans(body, values, start):
    out, cur = [], 0
    for v in values:
        i = body.find(v, cur); assert i >= 0, (body, v); out.append((start + i, start + i + len(v))); cur = i + len(v)
    return out
def encode_positions(tok, full, body, values):
    enc = tok(full, return_offsets_mapping=True); off = enc["offset_mapping"]; st = full.rfind(body)
    pos = []
    for a, b in spans(body, values, st):
        cand = [i for i, (x, y) in enumerate(off) if x < b and y > a]; pos.append(cand[-1])
    return torch.tensor([enc["input_ids"]]), pos
class Runner:
    def __init__(self, key):
        self.key = key; self.tok, self.hf, self.layers = load(key); self.nl = len(self.layers); self.patch = None; self.rec = None
        for li, l in enumerate(self.layers): l.register_forward_hook(self._mk(li))
    def _mk(self, li):
        def hook(mod, inp, out):
            h = out[0] if isinstance(out, tuple) else out
            if self.patch is not None and self.patch[0] == li:
                _, pos, H = self.patch; h[:, pos] = H.to(h.dtype)
            if self.rec is not None and li in self.rec[0]: self.rec[1][li] = h[:, self.rec[2]].detach().clone()
            return out
        return hook
    @torch.no_grad()
    def states(self, ids, pos, lids):
        self.rec = (set(lids), {}, pos); self.hf(input_ids=ids, use_cache=False); r = self.rec[1]; self.rec = None
        return torch.stack([r[l][0] for l in lids], 1)        # [nslots, nlayers, d]
    @torch.no_grad()
    def logits(self, ids, layer=None, pos=None, H=None):
        """H: [B, nslots, d] patches (replace) at layer; returns last-position logits [B, V]"""
        if H is None: return self.hf(input_ids=ids, use_cache=False).logits[:, -1].float()
        self.patch = (layer, pos, torch.as_tensor(H, dtype=torch.float32)); B = H.shape[0]
        if ids.shape[0] != B: ids = ids.repeat(B, 1)
        out = self.hf(input_ids=ids, use_cache=False).logits[:, -1].float(); self.patch = None; return out
    def tid(self, w): return self.tok.encode(w, add_special_tokens=False)[0]
