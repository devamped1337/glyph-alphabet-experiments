"""(0) cross-machine determinism check.
  det5.py make            (box, once)  -> results/det_state.pt : fixed seeded unit directions [5, 2048], plus the fixed prompt
  det5.py run MODEL       (each machine) -> results/det_MODEL_HOST.pt : logits with the fixed state injected (emb + each read layer),
                                            run twice in-process, then the state file is re-read from disk and run again (reload check)
  det5.py compare         (box) -> results/det_report.json : same model across machines (smol: box vs laptop) + within-machine checks
Tolerance (pre-registered): cross-machine max |dlogit| <= 1e-2 and identical top-1 and top-10 sets; within-machine reload: bitwise equal."""
import sys
from common5 import *
TOL_X, PROMPT = 1e-2, ("t1", "agent", "It is ? that ? ? ? ?.")
def make():
    g = torch.Generator().manual_seed(20261010); H = torch.randn(5, 8192, generator=g); H = H / H.norm(dim=1, keepdim=True)
    save({"H": H, "prompt": PROMPT, "note": "unit directions; scaled per model/layer by the median state norm of the fixed prompt"}, "det_state.pt")
def run(key):
    R = Runner(key); D = load("det_state.pt"); t, q, msg = D["prompt"]; ids, off, core = R.ids64(t, q, msg, "glyph")
    pos = torch.tensor(R.positions(ids, off, core, ["?"] * 5)); X = torch.tensor([ids])
    base = R.read([ids], [list(range(CTX))], R.L)[0]                      # [64, nkeys, d]
    out = {"env": env_info(), "model": MODELS[key], "keys": R.L, "base_logits": R.logits(X)[0]}
    def inj(H):
        res = {}
        for ki, k in enumerate(R.L):
            sc = base[:, ki].norm(dim=-1).median(); Hk = (H * sc)[None]
            res[str(k)] = R.logits(X, [(k, torch.tensor([0]), pos, Hk)])[0]
        return res
    Hd = lambda H: (lambda x: x / x.norm(dim=1, keepdim=True))(H.float()[:, :R.d])   # v5k: fixed 8192-dim directions, truncated to d and renormalised
    a = inj(Hd(D["H"])); b = inj(Hd(D["H"]))
    torch.save(D["H"], os.path.join(OUT, "_det_reload.pt")); c = inj(Hd(torch.load(os.path.join(OUT, "_det_reload.pt"))))
    X4 = X.repeat(4, 1); k = R.L[1]; sc = base[:, 1].norm(dim=-1).median()
    b4 = R.logits(X4, [(k, torch.arange(4), pos, (Hd(D["H"]) * sc)[None].repeat(4, 1, 1))])
    out.update({"inj": a, "repeat_bitwise": all(torch.equal(a[x], b[x]) for x in a), "reload_bitwise": all(torch.equal(a[x], c[x]) for x in a),
                "batch4_vs_batch1_maxabs": float((b4 - a[str(k)][None]).abs().max())})
    print({x: out[x] for x in ("repeat_bitwise", "reload_bitwise", "batch4_vs_batch1_maxabs")}, flush=True)
    save(out, f"det_{key}_{HOST}.pt")
def compare():
    rep = {"tolerance_abs": TOL_X, "within": {}, "cross": {}}
    for f in sorted(glob.glob(os.path.join(OUT, "det_*_*.pt"))):
        n = os.path.basename(f); 
        if n == "det_state.pt": continue
        d = load(n); rep["within"][n] = {x: d[x] for x in ("repeat_bitwise", "reload_bitwise", "batch4_vs_batch1_maxabs")} | {"env": d["env"]}
    for key in MODELS:
        fs = sorted(glob.glob(os.path.join(OUT, f"det_{key}_*.pt")))
        if len(fs) < 2: rep["cross"][key] = "only one machine ran this model"; continue
        A, B = load(os.path.basename(fs[0])), load(os.path.basename(fs[1])); r = {}
        for k in ["base"] + list(A["inj"]):
            la, lb = (A["base_logits"], B["base_logits"]) if k == "base" else (A["inj"][k], B["inj"][k])
            r[k] = {"maxabs": float((la - lb).abs().max()), "top1_same": int(la.argmax() == lb.argmax()),
                    "top10_same_set": int(set(la.topk(10).indices.tolist()) == set(lb.topk(10).indices.tolist()))}
        r["PASS"] = all(v["maxabs"] <= TOL_X and v["top1_same"] and v["top10_same_set"] for v in r.values())
        rep["cross"][key] = {"files": [os.path.basename(x) for x in fs[:2]], **r}
    save(rep, "det_report.json"); print(json.dumps(rep["cross"], indent=1, default=str)[:3000])
if __name__ == "__main__":
    {"make": make, "run": lambda: run(sys.argv[2]), "compare": compare}[sys.argv[1]]()
