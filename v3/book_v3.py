"""v3 negotiation of the closed 'maths book' alphabet. -> results/v3/book.pt, v3/book_v3.json"""
import sys, os, json, time, torch, numpy as np
HERE = "/workspace/glyph-exp"; sys.path[:0] = [HERE, HERE + "/v3"]; os.chdir(HERE)
from common3 import *
KEYS = ["qwen", "smol"]; KP, KC = 64, 32; t0 = time.time()
ST = {k: torch.load(f"results/v3/states_{k}.pt", weights_only=False) for k in KEYS}
E = ST["qwen"]["eqs"]; tr = np.array([e["split"] == "train" for e in E]); te = ~tr
SLOTS = ["left", "op", "right", "eq"]
SYM = {"left": [str(d) for d in range(10)], "op": list(OPS), "right": [str(d) for d in range(10)], "eq": ["="]}
def lab(e, s): return {"left": str(e["a"]), "op": e["op"], "right": str(e["b"]), "eq": "="}[s]
LAB = {s: np.array([lab(e, s) for e in E]) for s in SLOTS}
unit = lambda x: x / (np.linalg.norm(x, axis=-1, keepdims=True) + 1e-12)
book = {"version": "maths-book-v3.0", "layers": {}}; report = {"version": "maths-book-v3.0", "layers": {}}
for li in range(2):
    X = {k: ST[k]["states"][:, :, li].double().numpy() for k in KEYS}                 # [neq, 4, d]
    mu = {k: X[k][tr].reshape(-1, X[k].shape[-1]).mean(0) for k in KEYS}
    native = {k: {s: {y: X[k][tr & (LAB[s] == y), si].mean(0) - mu[k] for y in SYM[s]} for si, s in enumerate(SLOTS)} for k in KEYS}
    # slot-specific ridge probes ("does it decode to the right symbol"), trained on raw train states, scored on test states
    probes, probe_acc = {}, {}
    for k in KEYS:
        for si, s in enumerate(SLOTS):
            if len(SYM[s]) < 2: continue
            Xt = X[k][tr, si] - mu[k]; Y = np.stack([(LAB[s][tr] == y).astype(float) for y in SYM[s]], 1) * 2 - 1
            Wp = np.linalg.solve(Xt.T @ Xt + 10.0 * np.eye(Xt.shape[1]), Xt.T @ Y); probes[(k, s)] = Wp
            pr = np.array(SYM[s])[((X[k][te, si] - mu[k]) @ Wp).argmax(1)]; probe_acc[f"{k}|{s}"] = float((pr == LAB[s][te]).mean())
    accepted = {s: set(SYM[s]) for s in SLOTS}; rounds = []
    for rnd in range(1, 6):
        # (a) adapters on train states at accepted (slot, symbol) positions; PCA64 half-whitened -> generalised Procrustes to 32
        mask = np.stack([np.isin(LAB[s], list(accepted[s])) for s in SLOTS], 1) & tr[:, None]
        Z0 = {k: (X[k] - mu[k])[mask] for k in KEYS}; PCA = {}
        for k in KEYS:
            _, Sv, Vt = np.linalg.svd(Z0[k], full_matrices=False); PCA[k] = (Vt[:KP].T, (Sv[:KP] / np.sqrt(len(Z0[k]))) ** 0.5)
        zs = lambda k, x: (x @ PCA[k][0]) / PCA[k][1]
        Z = {k: zs(k, Z0[k]) for k in KEYS}; _, _, vt = np.linalg.svd(Z["qwen"], full_matrices=False); Cn = Z["qwen"] @ vt[:KC].T
        for _ in range(30):
            Q = {}
            for k in KEYS: u, _, v2 = np.linalg.svd(Z[k].T @ Cn, full_matrices=False); Q[k] = u @ v2
            Cn = np.mean([Z[k] @ Q[k] for k in KEYS], 0)
        enc = lambda k, x: zs(k, x) @ Q[k]; dec = lambda k, c: ((c @ Q[k].T) * PCA[k][1]) @ PCA[k][0].T
        can = {k: {s: {y: enc(k, native[k][s][y]) for y in SYM[s]} for s in SLOTS} for k in KEYS}
        shared = {s: {y: (can["qwen"][s][y] + can["smol"][s][y]) / 2 for y in SYM[s]} for s in SLOTS}
        # (b) checks
        res = {}
        for s in SLOTS:
            ys = [y for y in SYM[s] if y in accepted[s]] or SYM[s]
            for y in SYM[s]:
                gal = ys if y in ys else ys + [y]
                def nn_native(k, v): return gal[int((unit(v) @ unit(np.stack([native[k][s][g] for g in gal])).T).argmax())]
                def nn_can(k, c): return gal[int((unit(c) @ unit(np.stack([can[k][s][g] for g in gal])).T).argmax())]
                jb = nn_native("smol", dec("smol", can["qwen"][s][y])); ja = nn_native("qwen", dec("qwen", can["smol"][s][jb]))
                ja2 = nn_native("qwen", dec("qwen", can["smol"][s][y])); jb2 = nn_native("smol", dec("smol", can["qwen"][s][ja2]))
                keeper = nn_can("qwen", shared[s][y]) == y and nn_can("smol", shared[s][y]) == y
                rt = (ja == y) and (jb2 == y) and keeper
                if (("qwen", s)) in probes:
                    decodes = all(np.array(SYM[s])[int(dec(k, shared[s][y]) @ probes[(k, s)] @ np.ones(1) if False else (dec(k, shared[s][y]) @ probes[(k, s)]).argmax())] == y for k in KEYS)
                else: decodes = True        # single-entry slot ('='): trivially decodes
                r = {"roundtrip_AtoBtoA": bool(ja == y), "roundtrip_BtoAtoB": bool(jb2 == y), "keeper": bool(keeper), "decodes": bool(decodes),
                     "cos_A_B": float(unit(can["qwen"][s][y]) @ unit(can["smol"][s][y]))}
                if s == "op":
                    mo = {k: np.mean([can[k]["op"][o] for o in SYM["op"]], 0) for k in KEYS}
                    r["op_entry_offset_cos_AB"] = float(unit(can["qwen"]["op"][y] - mo["qwen"]) @ unit(can["smol"]["op"][y] - mo["smol"]))
                    # relation direction: how this operator moves the '=' state (where completion happens), A vs B in canonical space
                    eqc = {k: enc(k, X[k][tr, 3] - mu[k]) for k in KEYS}; opl = LAB["op"][tr]
                    off = {k: eqc[k][opl == y].mean(0) - eqc[k].mean(0) for k in KEYS}
                    r["eq_state_offset_cos_AB"] = float(unit(off["qwen"]) @ unit(off["smol"]))
                    # per-equation: same operand pair, op y vs mean -> cosine agreement
                    # plus-word check: decoded op glyph closer to receiver's native '+'/'-' entry than to its ' plus'/' minus' word state?
                    wmap = {"add": "plus", "sub": "minus"}
                    if y in wmap:
                        r["closer_to_symbol_than_word"] = {k: bool(unit(dec(k, shared[s][y])) @ unit(native[k]["op"][y]) >
                            unit(dec(k, shared[s][y])) @ unit(ST[k]["word_states"][wmap[y]][li].double().numpy() - mu[k])) for k in KEYS}
                    r["direction_ok"] = r["op_entry_offset_cos_AB"] >= 0.5 and r["eq_state_offset_cos_AB"] >= 0.5
                ok = rt and decodes and r.get("direction_ok", True) and all(r.get("closer_to_symbol_than_word", {}).values())
                r["pass"] = bool(ok); res[f"{s}:{y}"] = r
        new = {s: {y for y in SYM[s] if res[f"{s}:{y}"]["pass"]} for s in SLOTS}
        rounds.append({"round": rnd, "accepted": {s: sorted(new[s]) for s in SLOTS}, "n_accepted": sum(len(v) for v in new.values()),
                       "rate_roundtrip": float(np.mean([r["roundtrip_AtoBtoA"] and r["roundtrip_BtoAtoB"] for r in res.values()])),
                       "rate_keeper": float(np.mean([r["keeper"] for r in res.values()])), "rate_decodes": float(np.mean([r["decodes"] for r in res.values()])),
                       "op": {k: v for k, v in res.items() if k.startswith("op:")}})
        print(f"layer idx {li} R{rnd}: accepted {rounds[-1]['n_accepted']}/24 rt={rounds[-1]['rate_roundtrip']:.2f} keeper={rounds[-1]['rate_keeper']:.2f} "
              f"decodes={rounds[-1]['rate_decodes']:.2f} rejected={[k for k, r in res.items() if not r['pass']]}", flush=True)
        for k, v in res.items():
            if k.startswith("op:"): print("    ", k, {a: (round(b, 3) if isinstance(b, float) else b) for a, b in v.items()})
        stable = new == accepted; accepted = new
        if stable: break
    Ls = {k: ST[k]["layers"][li] for k in KEYS}
    book["layers"][li] = {"layer": Ls, "mu": mu, "PCA": PCA, "Q": Q, "shared": shared, "can": can, "native": native,
                          "accepted": {s: sorted(accepted[s]) for s in SLOTS}, "probes": probes}
    report["layers"][str(li)] = {"layer": Ls, "probe_heldout_acc": probe_acc, "rounds": rounds, "final_checks": res,
                                 "accepted": {s: sorted(accepted[s]) for s in SLOTS}}
torch.save(book, "results/v3/book.pt"); json.dump(report, open("v3/book_v3.json", "w"), indent=1)
print("probe acc", {li: report["layers"][li]["probe_heldout_acc"] for li in report["layers"]}, f"{time.time()-t0:.0f}s")
