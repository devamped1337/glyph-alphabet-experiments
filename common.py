"""Shared helpers for the glyph experiment (CPU only)."""
import os, json, torch, transformers, jlens
torch.set_num_threads(int(os.environ.get("NTHREADS", 8)))
HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = {
    "qwen": "Qwen/Qwen2.5-0.5B",
    "smol": "HuggingFaceTB/SmolLM2-360M",
}
def load(key):
    name = MODELS[key]
    tok = transformers.AutoTokenizer.from_pretrained(name)
    hf = transformers.AutoModelForCausalLM.from_pretrained(name, dtype=torch.float32)
    hf.eval()
    return jlens.from_hf(hf, tok), tok, hf

def lens_path(key):
    return os.path.join(HERE, "lenses", f"{key}_lens{os.environ.get('LENS_SUFFIX', '')}.pt")

def fit_prompts():
    return json.load(open(os.path.join(HERE, "data", "fit_prompts.json")))
