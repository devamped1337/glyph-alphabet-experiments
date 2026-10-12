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
    "olmo2": ("<|endoftext|><|system|>\n{sys}\n<|user|>\n{user}\n<|assistant|>\n", ["<|endoftext|>"]),
}
MODEL_TEMPLATE = {"qwen3b": "chatml", "smol17": "chatml", "qwen7b": "chatml", "llama8b": "llama3",
                  "olmo7b": "olmo2"}   # A7: Mistral removed entirely

class NonFinite(RuntimeError): pass
class GPUPreflightFail(RuntimeError): pass

def gpu_preflight(b):
    """A7: hard preflight for Stage B. The model must actually run on CUDA: HF -> torch sees a GPU, every
    parameter/buffer is on cuda (none on cpu/meta/disk) and the 4-bit layers are bitsandbytes Linear4bit;
    GGUF -> llama.cpp was built with GPU offload and all layers are offloaded (n_gpu_layers=-1).
    Anything else aborts the stage (never a silent CPU run)."""
    if isinstance(b, LlamaCppBackend):
        import llama_cpp
        if not llama_cpp.llama_supports_gpu_offload(): raise GPUPreflightFail("llama.cpp build has no GPU offload (CPU-only wheel)")
        if b.info.get("n_gpu_layers") != -1: raise GPUPreflightFail(f"GGUF n_gpu_layers={b.info.get('n_gpu_layers')} (must be -1: all layers offloaded)")
        return dict(ok=True, backend="llama.cpp", gpu_offload=True, n_gpu_layers=-1)
    t = b.torch
    if not t.cuda.is_available(): raise GPUPreflightFail("torch.cuda.is_available() is False")
    devs = {str(x.device.type) for x in list(b.m.parameters()) + list(b.m.buffers())}
    if devs != {"cuda"}: raise GPUPreflightFail(f"model tensors not all on CUDA: {sorted(devs)}")
    dm = getattr(b.m, "hf_device_map", None) or {}
    if any(str(v) in ("cpu", "disk", "meta") for v in dm.values()): raise GPUPreflightFail(f"hf_device_map offloads to cpu/disk: {dm}")
    if b.info.get("nf4"):
        import bitsandbytes as bnb
        n4 = sum(isinstance(m, bnb.nn.Linear4bit) for m in b.m.modules())
        if n4 == 0: raise GPUPreflightFail("no bitsandbytes Linear4bit layers (4-bit quantization not applied)")
    else: n4 = 0
    return dict(ok=True, backend=b.info.get("backend"), gpu=t.cuda.get_device_name(0), capability=list(t.cuda.get_device_capability(0)),
                linear4bit_layers=n4, param_devices=sorted(devs))

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

    def generate_batch(self, jobs, max_new):
        """PREREG §9 'batched generation for B1-B3' (A5 conformance fix). jobs = [(system, prefix_user, suffix_user)].
        Cold mode only (the cache test stays batch-1). Base implementation = sequential batch-1 (llama.cpp);
        HFBackend overrides it with true left-padded batched greedy decoding."""
        return [self.generate(s, p, u, max_new) for s, p, u in jobs]

    def _post(self, out, gaps, ans_gap, ptxt, stxt, system, n_prompt, latency, batch):
        import hashlib
        txt = self.detok(out)
        r = dict(text=txt, gen_tokens=len(out), prompt_tokens=n_prompt, new_prompt_tokens=n_prompt, latency_s=round(latency, 4),
                 first_gap=gaps[0] if gaps else None, answer_gap=ans_gap if ans_gap is not None else (gaps[0] if gaps else None),
                 answer_gap_source="after_answer_line" if ans_gap is not None else "first_token_fallback",
                 out_ids=[int(x) for x in out], warm=False, batch=batch, mode="cold", rendered_prompt=ptxt + stxt,
                 prompt_sha=hashlib.sha256((ptxt + stxt).encode("utf-8")).hexdigest(), system_turn_sha=self.system_turn_sha(system))
        for s in self.stop_str: r["text"] = r["text"].split(s)[0]
        r["text"] = r["text"].strip(); return r

    def cache_prefix(self, system, prefix_user):
        """Process the prefix once from a fresh context and save its state. Returns setup seconds/tokens."""
        ptxt, _ = self.split_render(system, prefix_user, "")
        pt = self.tok(ptxt, first=True); t0 = time.perf_counter()
        self._reset(); self._feed(pt); self._states[(system, prefix_user)] = self._save()
        return dict(prefix_tokens=len(pt), setup_s=round(time.perf_counter() - t0, 4))
    def drop_cache(self): self._states.clear()

# GPT A5 review (bug): HF generate() otherwise inherits the model's generation_config (Qwen2.5-7B ships
# repetition_penalty=1.05, top_k/top_p/temperature), while the batch-1 decoder applies none. Pin every knob neutral.
NEUTRAL_GEN = dict(temperature=1.0, top_p=1.0, top_k=0, repetition_penalty=1.0, no_repeat_ngram_size=0,
                   length_penalty=1.0, encoder_repetition_penalty=1.0, min_new_tokens=0, typical_p=1.0, epsilon_cutoff=0.0,
                   eta_cutoff=0.0, diversity_penalty=0.0, bad_words_ids=None, suppress_tokens=None, begin_suppress_tokens=None,
                   forced_bos_token_id=None, forced_eos_token_id=None, sequence_bias=None, renormalize_logits=False)

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
    def generate_batch(self, jobs, max_new):
        """True batched greedy decoding: left padding + attention mask, identical token sequences to the batch-1
        cold path (prefix and suffix tokenized separately and concatenated), per-row stop handling, per-step top-2
        gaps (fail-loud on non-finite logits). Latency is the batch wall time divided by the batch size."""
        t = self.torch
        if len(jobs) == 1: return [self.generate(*jobs[0], max_new)]
        rend = [self.split_render(s, p, u) for s, p, u in jobs]
        toks = [self.tok(pt, True) + self.tok(st, False) for pt, st in rend]
        L = max(len(x) for x in toks); pad = self.tk.pad_token_id if self.tk.pad_token_id is not None else (self.tk.eos_token_id or 0)
        ids = t.tensor([[pad] * (L - len(x)) + x for x in toks], device=self.device)
        mask = t.tensor([[0] * (L - len(x)) + [1] * len(x) for x in toks], device=self.device)
        # Claude A5 review: padding checks (left padding, mask covers exactly the real tokens, real tokens intact)
        assert self.m.config.is_encoder_decoder is False, "decoder-only models only"
        for i, x in enumerate(toks):
            assert int(mask[i].sum()) == len(x) and int(mask[i, :L - len(x)].sum()) == 0, "left padding / mask mismatch"
            assert ids[i, L - len(x):].tolist() == list(x), "real tokens altered by padding"
        self.info.setdefault("pad_token_id", int(pad)); self.info.setdefault("pad_source", "tokenizer_pad" if self.tk.pad_token_id is not None else "eos_fallback")
        # positions: HF Qwen2/Llama derive position_ids from attention_mask (cumsum-1) in generate(); equality with
        # batch-1 tokens is checked by tools/smoke_hf_batch.py (mixed lengths, per-row stops)
        t0 = time.perf_counter()
        with t.no_grad():
            g = self.m.generate(input_ids=ids, attention_mask=mask, max_new_tokens=max_new, do_sample=False, num_beams=1,
                                eos_token_id=sorted(self.stop_ids), pad_token_id=pad, output_scores=True, return_dict_in_generate=True,
                                **NEUTRAL_GEN)
        lat = (time.perf_counter() - t0) / len(jobs); outs = []
        for i, (s, p, u) in enumerate(jobs):
            out, gaps, ans_gap = [], [], None
            for step, sc in enumerate(g.scores):
                tok, gp = _gap(sc[i].float().cpu().numpy()); gaps.append(gp)
                if ans_gap is None and out and "Answer:" in self.detok(out): ans_gap = gp
                if tok in self.stop_ids: break
                out.append(tok)
                if any(x in self.detok(out[-8:]) for x in self.stop_str): break
            outs.append(self._post(out, gaps, ans_gap, rend[i][0], rend[i][1], s, len(toks[i]), lat, len(jobs)))
        return outs
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
