"""Model backends with explicit cold/warm prefix handling and top-2 logit gaps (PREREG_E1b §4, §8, A1.4).

Both backends tokenize PREFIX and SUFFIX separately and concatenate, so cold and warm runs see the identical
token sequence; warm = restore the saved prefix state, then process only the suffix. Batch size 1 throughout
the cache path. Greedy decoding with a manual argmax loop.

  LlamaCppBackend : GGUF via llama-cpp-python (Stage A CPU; Stage B fallback with CUDA, n_gpu_layers=-1)
  HFBackend       : transformers + bitsandbytes nf4 (Stage B primary)
"""
import time, math
import numpy as np

SPLIT = "\u241eE1B_SPLIT\u241e"
TEMPLATES = {
    "chatml": ("<|im_start|>system\n{sys}<|im_end|>\n<|im_start|>user\n{user}<|im_end|>\n<|im_start|>assistant\n", ["<|im_end|>"]),
    "llama3": ("<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n{sys}<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n{user}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n", ["<|eot_id|>"]),
    "mistral": ("<s>[INST] {sys}\n\n{user}[/INST]", ["</s>"]),
    "olmo2": ("<|endoftext|><|system|>\n{sys}\n<|user|>\n{user}\n<|assistant|>\n", ["<|endoftext|>"]),
}
MODEL_TEMPLATE = {"qwen3b": "chatml", "smol17": "chatml", "qwen7b": "chatml", "llama8b": "llama3",
                  "olmo7b": "olmo2", "mistral7b": "mistral"}

class NonFinite(RuntimeError): pass

def _gap(logits):
    l = np.asarray(logits, dtype=np.float64)
    if not np.all(np.isfinite(l)): raise NonFinite("non-finite logits (fail-loud, PREREG §4)")
    i2 = np.argpartition(-l, 1)[:2]; a, b = sorted(l[i2], reverse=True)
    return int(np.argmax(l)), float(a - b)

class _Base:
    def split_render(self, system, prefix_user, suffix_user):
        full = self.render(system, prefix_user + SPLIT + suffix_user)
        p, s = full.split(SPLIT); return p, s
    def _finish(self, out_ids, gaps, ans_gap, t0, n_new_prompt, n_prompt, warm):
        txt = self.detok(out_ids)
        return dict(text=txt, gen_tokens=len(out_ids), prompt_tokens=n_prompt, new_prompt_tokens=n_new_prompt,
                    latency_s=round(time.perf_counter() - t0, 4), first_gap=gaps[0] if gaps else None,
                    answer_gap=ans_gap, out_ids=[int(x) for x in out_ids], warm=warm, batch=1)

    def system_turn_sha(self, system):
        """A2: hash of the rendered system turn (template + system prompt) for this backend."""
        import hashlib
        return hashlib.sha256(self.split_render(system, "", "")[0].encode("utf-8")).hexdigest()

    def generate(self, system, prefix_user, suffix_user, max_new, warm=False, mode=None):
        """mode 'cold': fresh context, prefix+suffix in ONE evaluation. 'coldsplit' (A2): fresh context, prefix
        then suffix as TWO evaluations, no state restore. 'warm': restore the cached prefix state, process the
        suffix only (prefix cached via cache_prefix with identical arguments). warm=True is shorthand for 'warm'."""
        mode = mode or ("warm" if warm else "cold")
        ptxt, stxt = self.split_render(system, prefix_user, suffix_user)
        pt, st = self.tok(ptxt, first=True), self.tok(stxt, first=False)
        t0 = time.perf_counter()
        if mode == "warm":
            key = (system, prefix_user)
            assert key in self._states, "warm run without cached prefix"
            self._restore(self._states[key]); logits = self._feed(st); n_new = len(st)
        elif mode == "coldsplit":
            self._reset(); self._feed(pt); logits = self._feed(st); n_new = len(pt) + len(st)
        else:
            self._reset(); logits = self._feed(pt + st); n_new = len(pt) + len(st)
        out, gaps, ans_gap = [], [], None
        for _ in range(max_new):
            tok, g = _gap(logits); gaps.append(g)
            if ans_gap is None and "Answer:" in self.detok(out) and out: ans_gap = g
            if tok in self.stop_ids: break
            out.append(tok)
            if any(s in self.detok(out[-8:]) for s in self.stop_str): break
            logits = self._feed([tok])
        r = self._finish(out, gaps, ans_gap if ans_gap is not None else (gaps[0] if gaps else None), t0, n_new, len(pt) + len(st), mode == "warm")
        r["answer_gap_source"] = "after_answer_line" if ans_gap is not None else "first_token_fallback"   # A2
        r["mode"] = mode; r["rendered_prompt"] = ptxt + stxt
        import hashlib
        r["prompt_sha"] = hashlib.sha256((ptxt + stxt).encode("utf-8")).hexdigest(); r["system_turn_sha"] = self.system_turn_sha(system)
        for s in self.stop_str: r["text"] = r["text"].split(s)[0]
        r["text"] = r["text"].strip(); return r

    def cache_prefix(self, system, prefix_user):
        """Process the prefix once from a fresh context and save its state. Returns setup seconds/tokens."""
        ptxt, _ = self.split_render(system, prefix_user, "")
        pt = self.tok(ptxt, first=True); t0 = time.perf_counter()
        self._reset(); self._feed(pt); self._states[(system, prefix_user)] = self._save()
        return dict(prefix_tokens=len(pt), setup_s=round(time.perf_counter() - t0, 4))
    def drop_cache(self): self._states.clear()

class LlamaCppBackend(_Base):
    def __init__(self, name, path, n_ctx=2048, n_threads=8, n_gpu_layers=0, template=None):
        from llama_cpp import Llama
        self.name = name; self.template = template or MODEL_TEMPLATE[name]
        self.L = Llama(model_path=path, n_ctx=n_ctx, n_threads=n_threads, n_gpu_layers=n_gpu_layers,
                       n_batch=512, seed=0, logits_all=False, verbose=False)
        self.stop_str = TEMPLATES[self.template][1]
        self.stop_ids = {self.L.token_eos()}
        for s in self.stop_str:
            t = self.L.tokenize(s.encode(), add_bos=False, special=True)
            if len(t) == 1: self.stop_ids.add(t[0])
        self._states = {}
        self.info = dict(backend="llama.cpp", path=path, n_gpu_layers=n_gpu_layers, template=self.template)
    def render(self, system, user): return TEMPLATES[self.template][0].format(sys=system, user=user)
    def tok(self, s, first): return self.L.tokenize(s.encode("utf-8"), add_bos=False, special=True)
    def detok(self, ids): return self.L.detokenize(list(ids), special=True).decode("utf-8", "ignore") if ids else ""
    def _reset(self): self.L.reset()
    def _feed(self, toks):
        # llama-cpp-python >=0.3 no longer copies logits into .scores unless logits_all=True; read the last
        # token's logits directly from the context (row -1 of the last decoded batch).
        self.L.eval(toks)
        return np.ctypeslib.as_array(self.L._ctx.get_logits_ith(-1), shape=(self.L.n_vocab(),)).copy()
    def _save(self): return self.L.save_state()
    def _restore(self, st): self.L.load_state(st)

class HFBackend(_Base):
    def __init__(self, name, repo, nf4_cfg, revision=None, device="cuda:0"):
        """nf4_cfg=None -> no quantization (A2: CPU smoke test of the cache path with a tiny model, fp32)."""
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.torch = torch; self.name = name; self.device = device
        self.tk = AutoTokenizer.from_pretrained(repo, revision=revision)
        if nf4_cfg is None:
            self.m = AutoModelForCausalLM.from_pretrained(repo, revision=revision, torch_dtype=torch.float32).to(device)
        else:
            from transformers import BitsAndBytesConfig
            q = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type=nf4_cfg["bnb_4bit_quant_type"],
                                   bnb_4bit_compute_dtype=getattr(torch, nf4_cfg["bnb_4bit_compute_dtype"]),
                                   bnb_4bit_use_double_quant=nf4_cfg["bnb_4bit_use_double_quant"])
            self.m = AutoModelForCausalLM.from_pretrained(repo, revision=revision, quantization_config=q, device_map=device)
        self.m.eval(); self._states = {}; self._past = None
        self.stop_ids = {i for i in [self.tk.eos_token_id] if i is not None}
        for t in ("<|im_end|>", "<|eot_id|>", "<|endoftext|>"):
            i = self.tk.convert_tokens_to_ids(t)
            if isinstance(i, int) and i != self.tk.unk_token_id: self.stop_ids.add(i)
        self.stop_str = []
        self.info = dict(backend="hf-nf4" if nf4_cfg else "hf-fp32", repo=repo, revision=revision, nf4=nf4_cfg, device=device)
    def render(self, system, user):
        msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        try: return self.tk.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        except Exception:  # templates without a system role (e.g. Mistral): fold into user turn
            return self.tk.apply_chat_template([{"role": "user", "content": system + "\n\n" + user}], tokenize=False, add_generation_prompt=True)
    def tok(self, s, first): return self.tk(s, add_special_tokens=False)["input_ids"]
    def detok(self, ids): return self.tk.decode(list(ids), skip_special_tokens=False) if ids else ""
    def _reset(self): self._past = None
    def _feed(self, toks):
        t = self.torch
        with t.no_grad():
            ids = t.tensor([toks], device=self.device)
            o = self.m(input_ids=ids, past_key_values=self._past, use_cache=True)
            self._past = o.past_key_values
            return o.logits[0, -1].float().cpu().numpy()
    def _save(self):
        import copy; return copy.deepcopy(self._past)
    def _restore(self, st):
        import copy; self._past = copy.deepcopy(st)

def verify_gguf(path, want):
    """A2 (GPT code r1): refuse to load a GGUF whose sha256 differs from the pinned LFS oid in the config."""
    import hashlib, os
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 24), b""): h.update(blk)
    got = h.hexdigest()
    if got != want: raise RuntimeError(f"GGUF sha256 mismatch for {os.path.basename(path)}: {got} != pinned {want}")
    return got

def verify_gguf_set(d, shas):
    import os
    return {f: verify_gguf(os.path.join(d, f), s) for f, s in shas.items()}

def gpu_name():
    try:
        import torch
        return torch.cuda.get_device_name(0), torch.cuda.get_device_capability(0)
    except Exception: return None, None

def load_stageB(name, cfg, prefer="nf4", gguf_path=None):
    """B0 4-bit load test with pre-registered fallback (PREREG §9 B0, Claude r3 i): try nf4; on any failure
    (e.g. P100, compute capability 6.0) fall back to GGUF Q4_K_M via llama.cpp CUDA. The caller must then use
    the same backend kind for ALL Stage B models and stages (enforced in stages.py via results/B/backend.json)."""
    m = cfg["models"]["stageB"][name]
    if prefer == "nf4":
        try:
            b = HFBackend(name, m["hf"], cfg["models"]["nf4"], m.get("revision"))
            r = b.generate("Reply with one word.", "", "Say OK.", 4)   # trivial load check
            if not r["text"]: raise RuntimeError("empty output on load check")
            return b, "nf4"
        except NonFinite: raise
        except Exception as ex:
            print(f"[load_stageB] nf4 failed for {name}: {ex!r} -> GGUF/llama.cpp CUDA fallback")
    import os
    verify_gguf_set(os.path.dirname(gguf_path), m["gguf_sha256"])   # A2: pinned GGUF verified before GPU use
    return LlamaCppBackend(name, gguf_path, n_ctx=cfg["n_ctx"], n_gpu_layers=-1), "gguf_cuda"
