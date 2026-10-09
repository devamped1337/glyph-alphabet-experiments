"""v2 negotiation: model A (Qwen), model B (SmolLM2) and the arbiter (this script) iterate on concepts,
probes, adapters and relation operators until the accepted set stabilises.
-> results/v2/negotiation.json, results/v2/dictionary_v2.pt, dictionary_v2.json"""
import sys, os, json, time, copy, torch, numpy as np
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, HERE); sys.path.insert(0, HERE + "/v2"); os.chdir(HERE)
def spearmanr(a, b):
    ra = np.argsort(np.argsort(a)).astype(float); rb = np.argsort(np.argsort(b)).astype(float)
    return (np.corrcoef(ra, rb)[0, 1],)
from concepts import C, RELATIONS
import transformers, jlens
from common import MODELS, lens_path
t0 = time.time(); rng = np.random.default_rng(0)
KEYS = ["qwen", "smol"]; KPCA, KCAN = 128, int(os.environ.get("KCAN", 96)); NT0 = 5; MAXR = 10; TOPR = 20
LI = 1  # index into band -> centre layer L (the v1 injection layer)
ST = {k: torch.load(f"results/v2/states_{k}.pt", weights_only=False) for k in KEYS}
words = [c["word"] for c in C]; NC = len(C); NTPL = len(ST["qwen"]["templates"])
# centre on the centroid of ALL candidate probe states (wiki-mean centring left a shared "concept-probe" direction that swamped NN/readout; see RESULTS_v2 caveats)
mu = {k: ST[k]["probe"][:, :, LI].double().numpy().reshape(-1, ST[k]["probe"].shape[-1]).mean(0) for k in KEYS}
X = {k: ST[k]["probe"][:, :, LI].double().numpy() - mu[k] for k in KEYS}        # [NC, NT, d] centred
# ---- arbiter's readout vocab: v1 anchors + first tokens of all concept words / synonyms
anchors = json.load(open("data/anchors.json"))
RD = {}
for k in KEYS:
    tok = transformers.AutoTokenizer.from_pretrained(MODELS[k])
    hf = transformers.AutoModelForCausalLM.from_pretrained(MODELS[k], dtype=torch.float32)
    lens = jlens.JacobianLens.load(lens_path(k)); L = ST[k]["band"][LI]
    ids = list(anchors["ids"][k]); fid = lambda w: tok.encode(" " + w, add_special_tokens=False)[0]
    for c in C:
        for w in [c["word"]] + c["syn"]: ids.append(fid(w))
    ids = sorted(set(ids)); idt = torch.tensor(ids)
    W = (hf.lm_head.weight[idt].float() * hf.model.norm.weight.float()) @ lens.jacobians[L].float()
    strs = [tok.decode([i]).strip().lower() for i in ids]
    ok = np.zeros((NC, len(ids)), bool)          # token j counts as "naming" concept i
    for i, c in enumerate(C):
        names = {w.lower() for w in [c["word"]] + c["syn"]}; f = {fid(w) for w in [c["word"]] + c["syn"]}
        ok[i] = [(s in names) or (t in f) for s, t in zip(strs, ids)]
    RD[k] = {"W": W.detach().double().numpy(), "ok": ok, "strs": strs}
    del hf
print("readout vocab", {k: RD[k]["W"].shape for k in KEYS}, f"{time.time()-t0:.0f}s", flush=True)

# ---- adapters: per-model PCA(128, whitened) + semi-orthogonal Procrustes into a shared KCAN-dim canonical space
PCA = {}
for k in KEYS:
    Z = X[k].reshape(-1, X[k].shape[-1]); U, S, Vt = np.linalg.svd(Z - 0, full_matrices=False)
    PCA[k] = {"P": Vt[:KPCA].T, "s": (S[:KPCA] / np.sqrt(len(Z))) ** 0.5}   # half-whitening (chosen on a held-out diagnostic, see caveats)
def zsp(k, x): return (x @ PCA[k]["P"]) / PCA[k]["s"]
def fit_adapters(V, idx, iters=30):
    Z = {k: zsp(k, V[k][idx]) for k in KEYS}
    Ua, Sa, Vta = np.linalg.svd(Z["qwen"], full_matrices=False); Cn = Z["qwen"] @ Vta[:KCAN].T   # init: A's own top dirs
    for _ in range(iters):
        Q = {}
        for k in KEYS:
            u, _, vt = np.linalg.svd(Z[k].T @ Cn, full_matrices=False); Q[k] = u @ vt          # [KPCA, KCAN]
        Cn = np.mean([Z[k] @ Q[k] for k in KEYS], 0)
    return Q
def enc(k, Q, x): return zsp(k, x) @ Q[k]
def dec(k, Q, c): return ((c @ Q[k].T) * PCA[k]["s"]) @ PCA[k]["P"].T          # centred residual in model k
def unit(x): return x / (np.linalg.norm(x, axis=-1, keepdims=True) + 1e-12)
def nn(q, G): return (unit(q) @ unit(G).T).argmax(-1)

def readout_pass(k, Q, c, cid):
    R = dec(k, Q, c) @ RD[k]["W"].T                                   # [n, vocab]
    R = (R - R.mean(0)) / (R.std(0) + 1e-9)                           # arbiter rule: distinctive tokens vs other concepts
    top = np.argsort(-R, 1)[:, :TOPR]
    return np.array([RD[k]["ok"][cid[n], top[n]].any() for n in range(len(c))]), top

# ---- negotiation state
probes = {i: list(range(NT0)) for i in range(NC)}      # active probe templates per concept
groups = {i: [i] for i in range(NC)}                    # merged synonym groups (representative -> members)
status = {i: "candidate" for i in range(NC)}; fails = {i: 0 for i in range(NC)}
accepted = list(range(NC))   # round 1: adapters fit on all candidates (nothing accepted yet)
def concept_vecs():
    return {k: np.stack([np.concatenate([X[k][j][probes[i]] for j in groups[i]]).mean(0) for i in range(NC)]) for k in KEYS}
LOG = []; relkeep = {}
for rnd in range(1, MAXR + 1):
    V = concept_vecs(); live = [i for i in range(NC) if status[i] != "dropped" and status[i] != "merged"]
    acc_idx = [i for i in accepted if i in live]
    if len(acc_idx) < 120: acc_idx = list(live)   # too few to fit 128->96 adapters: fall back to all live candidates (logged)
    # (a) 5-fold CV adapters over the accepted set; non-accepted candidates encoded with the full-set adapter
    Qfull = fit_adapters(V, acc_idx)
    E = {k: enc(k, Qfull, V[k]) for k in KEYS}
    folds = np.array_split(rng.permutation(acc_idx), 5)
    for f in folds:
        tr = [i for i in acc_idx if i not in set(f)]; Qf = fit_adapters(V, tr)
        # align the fold's canonical frame to the full-fit frame (orthogonal Procrustes on training concepts)
        Cf = np.mean([enc(k, Qf, V[k][tr]) for k in KEYS], 0); Cg = np.mean([enc(k, Qfull, V[k][tr]) for k in KEYS], 0)
        u, _, vt = np.linalg.svd(Cf.T @ Cg); Rf = u @ vt; Qf = {k: Qf[k] @ Rf for k in KEYS}
        for k in KEYS: E[k][f] = enc(k, Qf, V[k][f])
    Qfold = {}; [Qfold.update({int(i): fi}) for fi, f in enumerate(folds) for i in f]
    lv = np.array(live)
    # (b) checks against the gallery of live candidates
    nAB = lv[nn(E["qwen"][lv], E["smol"][lv])]; nBA = lv[nn(E["smol"][lv], E["qwen"][lv])]
    meaning = {int(i): bool(a == i and b == i) for i, a, b in zip(lv, nAB, nBA)}
    # round trip: A -> canonical -> B residual -> B's nearest own concept (raw B space) -> canonical -> A residual -> A's nearest (raw A space)
    rt = {}
    for i in lv:
        xb = dec("smol", Qfull, E["qwen"][i]); jb = lv[nn(xb, V["smol"][lv])]
        xa = dec("qwen", Qfull, E["smol"][jb]); ja = lv[nn(xa, V["qwen"][lv])]
        xa2 = dec("qwen", Qfull, E["smol"][i]); ja2 = lv[nn(xa2, V["qwen"][lv])]
        xb2 = dec("smol", Qfull, E["qwen"][ja2]); jb2 = lv[nn(xb2, V["smol"][lv])]
        rt[int(i)] = bool(ja == i and jb2 == i)
    # geometry per concept: RSA of its distance profile (raw spaces, adapter-free) over live concepts
    DA = 1 - unit(V["qwen"][lv]) @ unit(V["qwen"][lv]).T; DB = 1 - unit(V["smol"][lv]) @ unit(V["smol"][lv]).T
    iu = np.triu_indices(len(lv), 1); rsa_global = float(spearmanr(DA[iu], DB[iu])[0])
    rsa_c = {int(i): float(spearmanr(np.delete(DA[n], n), np.delete(DB[n], n))[0]) for n, i in enumerate(lv)}
    # relation offsets in canonical space (A vs B), per pair and per relation
    widx = {w: i for i, w in enumerate(words)}
    rel_stats = {}; pair_cos = {}
    for r, pairs in RELATIONS.items():
        P_ = [(widx[a], widx[b]) for a, b in pairs if widx[a] in lv and widx[b] in lv]
        if len(P_) < 3: continue
        oA = np.stack([E["qwen"][b] - E["qwen"][a] for a, b in P_]); oB = np.stack([E["smol"][b] - E["smol"][a] for a, b in P_])
        pc = (unit(oA) * unit(oB)).sum(1); mA, mB = oA.mean(0), oB.mean(0)
        # cross-model LOO analogy: B source + mean A offset (excluding pair) -> nearest B target among relation targets
        tg = np.array([b for _, b in P_]); hits = []
        for n, (a, b) in enumerate(P_):
            off = np.delete(oA, n, 0).mean(0); q = E["smol"][a] + off
            hits.append(tg[nn(q, E["smol"][tg])] == b)
            off = np.delete(oB, n, 0).mean(0); q = E["qwen"][a] + off
            hits.append(tg[nn(q, E["qwen"][tg])] == b)
        within = float(np.mean([unit(oA[n]) @ unit(np.delete(oA, n, 0).mean(0)) for n in range(len(P_))]))
        rel_stats[r] = {"n_pairs": len(P_), "mean_offset_cos_AB": float(unit(mA) @ unit(mB)), "per_pair_offset_cos_AB": float(pc.mean()),
                        "cross_model_LOO_analogy_acc": float(np.mean(hits)), "within_A_consistency": within,
                        "chance_analogy": 1 / len(P_)}
        for (a, b), v in zip(P_, pc): pair_cos.setdefault(a, []).append(float(v)); pair_cos.setdefault(b, []).append(float(v))
    relkeep = {r: s for r, s in rel_stats.items() if s["mean_offset_cos_AB"] >= 0.5 and s["cross_model_LOO_analogy_acc"] >= 2 * s["chance_analogy"]}
    kept_members = {widx[w] for r in relkeep for p in RELATIONS[r] for w in p}
    geom = {}
    for i in lv:
        g_ok = rsa_c[int(i)] >= 0.3
        if int(i) in kept_members and int(i) in pair_cos: g_ok = g_ok and np.mean(pair_cos[int(i)]) >= 0.3
        geom[int(i)] = bool(g_ok)
    # readability: the canonical vector (mean of A and B encodings) decoded into each model, read through its J-lens
    Cc = (E["qwen"] + E["smol"]) / 2
    rdA, topA = readout_pass("qwen", Qfull, Cc[lv], lv); rdB, topB = readout_pass("smol", Qfull, Cc[lv], lv)
    read = {int(i): bool(a and b) for i, a, b in zip(lv, rdA, rdB)}
    # (c) accept / revise / merge / drop
    passed = [int(i) for i in lv if meaning[int(i)] and rt[int(i)] and geom[int(i)] and read[int(i)]]
    new_acc = sorted(passed); revised, merged, dropped = [], [], []
    for n, i in enumerate(lv):
        i = int(i)
        if i in passed: status[i] = "accepted"; fails[i] = 0; continue
        if status[i] == "accepted":          # hysteresis: an accepted entry gets one round of probation before demotion
            status[i] = "probation"; new_acc.append(i); continue
        fails[i] += 1
        # merge rule: cross-model NN is a listed synonym of i (or vice versa) -> fold into one entry
        j = int(nAB[n])
        if j != i and status[j] not in ("merged", "dropped") and (words[j] in C[i]["syn"] or words[i] in C[j]["syn"]) and not meaning[i]:
            rep, oth = (i, j) if len(groups[i]) >= len(groups[j]) else (j, i)
            groups[rep] = groups[rep] + groups[oth]; status[oth] = "merged"; merged.append((words[rep], words[oth])); continue
        if fails[i] >= 3: status[i] = "dropped"; dropped.append(words[i]); continue
        # probe revision: drop the probe whose vector is least typical (summed over both models), add the next unused template
        cur = probes[i]
        typ = [sum(float(unit(X[k][i][t]) @ unit(V[k][i])) for k in KEYS) for t in cur]
        unused = [t for t in range(NTPL) if t not in cur]
        if unused:
            cur = [t for t in cur if t != cur[int(np.argmin(typ))]] + [unused[0]]
            if len(unused) > 1: cur.append(unused[1])        # grow by one: more probes = less noise
        probes[i] = cur; status[i] = "revising"; revised.append(words[i])
    new_acc = sorted(new_acc); n_live = len(lv)
    log = {"round": rnd, "n_live_candidates": n_live, "n_adapter_fit_on": len(acc_idx), "n_accepted": len(new_acc), "n_passed_all_checks": len(passed), "n_on_probation": sum(status[i] == "probation" for i in new_acc),
           "rate_meaning": float(np.mean(list(meaning.values()))), "rate_roundtrip": float(np.mean(list(rt.values()))),
           "rate_geometry": float(np.mean(list(geom.values()))), "rate_readability": float(np.mean(list(read.values()))),
           "rate_readability_A": float(rdA.mean()), "rate_readability_B": float(rdB.mean()),
           "rsa_global_spearman": rsa_global, "relations": rel_stats, "kept_relations": sorted(relkeep),
           "n_revised": len(revised), "merged": merged, "dropped": dropped,
           "accepted_changed": sorted(set(new_acc) ^ set(accepted)).__len__()}
    LOG.append(log)
    print(f"R{rnd}: live={n_live} fit_on={len(acc_idx)} accepted={len(new_acc)} passed={len(passed)} probation={log['n_on_probation']} meaning={log['rate_meaning']:.3f} rt={log['rate_roundtrip']:.3f} "
          f"geom={log['rate_geometry']:.3f} read={log['rate_readability']:.3f} (A {rdA.mean():.2f} B {rdB.mean():.2f}) RSA={rsa_global:.3f} "
          f"kept_rel={sorted(relkeep)} merged={merged} dropped={len(dropped)} {time.time()-t0:.0f}s", flush=True)
    for r, s in rel_stats.items(): print("   ", r, {a: round(b, 3) if isinstance(b, float) else b for a, b in s.items()})
    stable = rnd > 2 and set(new_acc) == set(accepted)
    accepted = new_acc
    last = dict(E=E, Qfull=Qfull, lv=lv, meaning=meaning, rt=rt, geom=geom, read=read, rsa_c=rsa_c, topA=topA, topB=topB, pair_cos=pair_cos, V=V)
    if stable: print("accepted set stable -> stop"); break

# ---- final repository: refit adapters on the final accepted set (full), canonical = mean of A and B encodings
acc = accepted; V = concept_vecs(); Q = fit_adapters(V, acc if len(acc) >= 120 else [i for i in range(NC) if status[i] not in ("merged","dropped")])
EA, EB = enc("qwen", Q, V["qwen"]), enc("smol", Q, V["smol"]); Cfin = (EA + EB) / 2
ops = {}
widx = {w: i for i, w in enumerate(words)}
for r in relkeep:
    P_ = [(widx[a], widx[b]) for a, b in RELATIONS[r] if widx[a] in acc and widx[b] in acc]
    if P_: ops[r] = {"pairs": [(words[a], words[b]) for a, b in P_], "offset": (Cfin[[b for _, b in P_]] - Cfin[[a for a, _ in P_]]).mean(0)}
lvpos = {int(i): n for n, i in enumerate(last["lv"])}
entries = []
for i in acc:
    n = lvpos[i]
    entries.append({"id": len(entries), "word": words[i], "members": [words[j] for j in groups[i]], "type": C[i]["type"], "gloss": C[i]["gloss"],
        "synonyms": C[i]["syn"], "probe_templates": [ST["qwen"]["templates"][t] for t in probes[i]],
        "agreement": {"meaning": last["meaning"][i], "roundtrip": last["rt"][i], "geometry_rsa_spearman": round(last["rsa_c"][i], 4),
                      "relation_offset_cos": round(float(np.mean(last["pair_cos"][i])), 4) if i in last["pair_cos"] else None,
                      "readability": last["read"][i], "cos_A_B_canonical": round(float(unit(EA[i]) @ unit(EB[i])), 4),
                      "lens_top_A": [RD["qwen"]["strs"][t] for t in last["topA"][n][:8]], "lens_top_B": [RD["smol"]["strs"][t] for t in last["topB"][n][:8]]}})
torch.save({"version": "glyph-dict-v2.0", "words": [words[i] for i in acc], "concept_index": acc, "canonical": torch.tensor(Cfin[acc]),
            "canonical_A": torch.tensor(EA[acc]), "canonical_B": torch.tensor(EB[acc]),
            "all_candidates_canonical": torch.tensor(Cfin), "all_words": words,
            "adapters": {k: {"mu": torch.tensor(mu[k]), "P": torch.tensor(PCA[k]["P"]), "s": torch.tensor(PCA[k]["s"]), "Q": torch.tensor(Q[k]),
                             "layer": ST[k]["band"][LI]} for k in KEYS},
            "operators": {r: torch.tensor(o["offset"]) for r, o in ops.items()}}, "results/v2/dictionary_v2.pt")
json.dump({"version": "glyph-dict-v2.0", "created": time.strftime("%Y-%m-%d %H:%M %Z"), "models": {k: MODELS[k] for k in KEYS},
           "canonical_dim": KCAN, "vectors_file": "results/v2/dictionary_v2.pt",
           "adapters": {k: {"type": f"centre(centroid of all candidate probe states) -> PCA{KPCA} half-whitened (s^0.5) -> semi-orthogonal Procrustes {KPCA}x{KCAN} (generalised Procrustes, 30 iters)",
                            "layer": ST[k]["band"][LI], "version": "adapter-v2.0-" + k} for k in KEYS},
           "acceptance_rule": {"meaning": "mutual cross-model NN in canonical space (5-fold CV adapters) among all live candidates",
                               "roundtrip": "A->canon->B space->B NN concept->canon->A space NN == self (and B->A->B)",
                               "geometry": "per-concept RSA Spearman >=0.3 (raw spaces); if in a kept relation, mean pair offset cos A/B >=0.3",
                               "readability": f"canonical vector decoded into each model, J-lens readout over v1 anchors+concept tokens, column z-scored; concept word/synonym in top {TOPR} for BOTH models"},
           "relation_operators": {r: {"pairs": o["pairs"], "stats_last_round": LOG[-1]["relations"][r]} for r, o in ops.items()},
           "n_concepts": len(entries), "concepts": entries, "rounds": LOG}, open("dictionary_v2.json", "w"), indent=1)
json.dump(LOG, open("results/v2/negotiation.json", "w"), indent=1)
print("final accepted", len(acc), "operators", list(ops), f"{time.time()-t0:.0f}s")
