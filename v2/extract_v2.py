"""v2 extraction: last-position residuals at the v1 band layers for every concept probe and every test prompt.
usage: extract_v2.py KEY -> results/v2/states_KEY.pt"""
import sys, os, json, time, torch
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import *; from prompts import *; from concepts import C
import jlens
key = sys.argv[1]; t0 = time.time()
m, tok, hf = load(key)
band = torch.load(f"results/feat_{key}.pt", weights_only=False)["band"]
TEMPL = ["Fact: The name of {g} is", "Q: What is {g}?\nA:", "{w}. {w}. {w}.", "In one word, {g} is called",
         "I am thinking of {w}. The thing I am thinking of is", "Topic: {w}\nKeyword:",
         "Everyone has heard of {w}. When people mention {g}, they mean", "The answer is {w}. To repeat, the answer is",
         "Word association. {g}:", "Here is a word: {w}. Say it again:"]
@torch.no_grad()
def st(p):
    ids = m.encode(p.rstrip(), max_length=128)
    with jlens.ActivationRecorder(m.layers, at=band) as rec:
        m.forward(ids); return torch.stack([rec.activations[l][0, -1].float().clone() for l in band])
P = torch.stack([torch.stack([st(t.format(w=c["word"], g=c["gloss"])) for t in TEMPL]) for c in C])  # [nc, nt, 3, d]
print("concepts", P.shape, f"{time.time()-t0:.0f}s", flush=True)
D = "jacobian-lens/data/evaluations/"
sets = {"para": [p for pr in PARAPHRASES for p in pr], "minimal": [p for pr in MINIMAL for p in pr[:2]],
        "multihop": [it["prompt"] for it in json.load(open(D + "lens-eval-multihop.json"))["items"]],
        "assoc": [it["prompt"] for it in json.load(open(D + "lens-eval-association.json"))["items"]],
        "wiki": fit_prompts()[40:100], "bridge_src": [SRC_TMPL.format(desc=v[0]) for v in BRIDGES.values()]}
S = {s: torch.stack([st(p) for p in ps]) for s, ps in sets.items()}
torch.save({"key": key, "band": band, "templates": TEMPL, "concepts": [c["word"] for c in C], "probe": P, "sets": S,
            "runtime_s": time.time() - t0}, f"results/v2/states_{key}.pt")
print("done", key, f"{time.time()-t0:.0f}s")
