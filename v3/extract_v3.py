"""states at the 4 equation positions (left, op, right, '=') for every equation, at the v3 layers. -> results/v3/states_KEY.pt"""
import sys, os, json, time, torch
HERE = "/workspace/glyph-exp"; sys.path[:0] = [HERE, HERE + "/v3"]; os.chdir(HERE)
from common import *; from common3 import *
import jlens
key = sys.argv[1]; t0 = time.time(); m, tok, hf = load(key); Ls = LAYERS[key]; E = equations()
@torch.no_grad()
def st(p, npos=4):
    ids = m.encode(p)
    with jlens.ActivationRecorder(m.layers, at=Ls) as rec:
        m.forward(ids); return torch.stack([rec.activations[l][0, -npos:].float().clone() for l in Ls], 1)   # [4, nL, d]
S = torch.stack([st(PRE + e["text"]) for e in E])
# word-glyph controls: receiver's own state at the ' plus' / ' minus' / ' greater' word tokens in "a plus b" style prompts (op position)
W = {}
for w in ("plus", "minus"):
    wid = tok.encode(" " + w, add_special_tokens=False)[0]; acc = []
    for e in E:
        if e["split"] != "train": continue
        ids = m.encode(PRE + f"{e['a']} {w} {e['b']}="); pos = (ids[0] == wid).nonzero()[-1].item()
        with torch.no_grad(), jlens.ActivationRecorder(m.layers, at=Ls) as rec:
            m.forward(ids); acc.append(torch.stack([rec.activations[l][0, pos].float() for l in Ls]))
    W[w] = torch.stack(acc).mean(0)   # [nL, d] state at the word token
emb = {w: hf.get_input_embeddings().weight[tok.encode(w, add_special_tokens=False)[0]].float().detach()
       for w in (" plus", " minus", "+", "-")}
torch.save({"key": key, "layers": Ls, "eqs": E, "states": S, "word_states": W, "emb": emb, "runtime_s": time.time() - t0}, f"results/v3/states_{key}.pt")
print(key, S.shape, f"{time.time()-t0:.0f}s")
