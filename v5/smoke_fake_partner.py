"""SMOKE ONLY: fabricate a stand-in 'qwen' states file from SmolLM2 states (random rotation + noise) so the box-only smoke test can
exercise negotiation/deliveries/run code paths without running anything on the laptop. Never used for real results."""
from common5 import *
S = load("states_smol.pt"); g = torch.Generator().manual_seed(9); d = S["d"]
Qr = torch.linalg.qr(torch.randn(d, d, generator=g))[0]
def rot(x): return ((x.float() @ Qr) + 0.05 * x.float().std() * torch.randn(x.shape, generator=g)).half()
F = dict(S); F.update({"key": "qwen", "model": ("FAKE-rotated-SmolLM2", "smoke"), "book_states": rot(S["book_states"]), "sender_states": rot(S["sender_states"]),
          "jlens": {k: {**v, "evecs": (Qr.T @ v["evecs"].float())} for k, v in S["jlens"].items()}, "SMOKE_FAKE": True})
save(F, "states_qwen.pt", {"SMOKE_FAKE": True})
