"""v4 spec: vocabulary, message types, templates, splits, questions. Pure python (no models)."""
import itertools, random, numpy as np
MODELS = {"qwen": "Qwen/Qwen2.5-0.5B", "smol": "HuggingFaceTB/SmolLM2-360M", "pythia": "EleutherAI/pythia-410m"}
FRACS = [0.25, 0.33, 0.42]                       # candidate injection depths; ONE is chosen on dev, then frozen
ENT = ["Alice", "Bob", "Carol", "Dave", "Eve"]; ACT = ["paid", "called", "helped", "thanked"]
EXT_ENT = ["Oscar", "Peggy", "Alicia", "Bobby"]; EXT_ACT = ["warned", "praised", "pushed"]   # delegate-proposal pool (train-only data)
MOD = ["known", "suspected"]; POL = ["indeed", "never"]; ORD = ["before", "after"]; DIG = [str(d) for d in range(10)]
SLOTS = {"t1": ["mod", "agent", "pol", "act", "patient"], "t2": ["a1", "act1", "ord", "a2", "act2"], "t3": ["left", "op", "right", "eq"]}
DOMAIN = {"mod": "MOD", "agent": "ENT", "pol": "POL", "act": "ACT", "patient": "ENT", "a1": "ENT", "act1": "ACT", "ord": "ORD", "a2": "ENT", "act2": "ACT",
          "left": "DIG", "op": "OP", "right": "DIG", "eq": "EQ"}
def T1(t, m):   # book format (also the "prose" opponent)
    if t == "t1": return f"It is {m['mod']} that {m['agent']} {m['pol']} {m['act']} {m['patient']}."
    if t == "t2": return f"{m['a1']} {m['act1']} {m['ord']} {m['a2']} {m['act2']}."
    return f"{m['left']}-{m['right']}="
def T2(t, m):   # sender's own reading: a paraphrase frame never used to build the book
    if t == "t1": return f"Word is, and it is {m['mod']}, that {m['agent']} {m['pol']} {m['act']} {m['patient']}."
    if t == "t2": return f"I heard that {m['a1']} {m['act1']} {m['ord']} {m['a2']} {m['act2']}."
    return f"Compute: {m['left']}-{m['right']}="
def SKEL(t): return {"t1": "It is ? that ? ? ? ?.", "t2": "? ? ? ? ?.", "t3": "? ? ? ?"}[t]
def COMPACT(t, m):
    if t == "t1": return f"{m['act']}({m['agent']},{m['patient']},{m['mod']},{'yes' if m['pol'] == 'indeed' else 'not'})"
    if t == "t2": return f"{m['ord']}({m['a1']}.{m['act1']},{m['a2']}.{m['act2']})"
    return f"sub({m['left']},{m['right']})="
def BAG(t, m, seed):
    w = [m[s] for s in SLOTS[t] if s not in ("op", "eq")] + (["-"] if t == "t3" else [])
    r = random.Random(seed); p = w[:]
    for _ in range(20):
        r.shuffle(p)
        if p != w: break
    return (" ".join(p) + ("=" if t == "t3" else "."))
SUFFIX_POS = {"t1": [3, 5, 6, 7, 8], "t2": None, "t3": None}
QUESTIONS = {"t1": {"agent": "Who did it?", "patient": "Who was it done to?", "pol": "Did it happen?", "mod": "Is it certain?"},
             "t2": {"first": "Who acted first?"}, "t3": {"result": None}}
def answer(t, q, m):
    if t == "t1": return {"agent": m["agent"], "patient": m["patient"], "pol": "yes" if m["pol"] == "indeed" else "no", "mod": "yes" if m["mod"] == "known" else "no"}[q]
    if t == "t2": return m["a1"] if m["ord"] == "before" else m["a2"]
    return str(int(m["left"]) - int(m["right"]))
SHOTS = {"t1": [dict(mod="known", agent="Frank", pol="indeed", act="met", patient="Grace"), dict(mod="suspected", agent="Henry", pol="never", act="sent", patient="Frank"),
                dict(mod="known", agent="Grace", pol="never", act="met", patient="Henry"), dict(mod="suspected", agent="Grace", pol="indeed", act="sent", patient="Henry")],
         "t2": [dict(a1="Frank", act1="met", ord="before", a2="Grace", act2="sent"), dict(a1="Henry", act1="sent", ord="after", a2="Grace", act2="met"),
                dict(a1="Grace", act1="met", ord="after", a2="Frank", act2="sent"), dict(a1="Henry", act1="met", ord="before", a2="Frank", act2="sent")],
         "t3": [dict(left="9", op="-", right="4", eq="="), dict(left="3", op="-", right="8", eq="="), dict(left="6", op="-", right="1", eq="="), dict(left="2", op="-", right="9", eq="=")]}
def render(t, m, fmt, seed=0):
    return {"prose": T1, "compact": COMPACT}[fmt](t, m) if fmt in ("prose", "compact") else BAG(t, m, seed) if fmt == "bag" else SKEL(t)
def prompt(t, q, body, fmt, seed=0):
    """few-shot (format examples with Frank/Grace/Henry, met/sent: no test content) + message body + question"""
    if t == "t3":
        shot_fmt = "compact" if fmt == "compact" else "bag" if fmt == "bag" else "prose"
        pre = "".join(render(t, s, shot_fmt, i) + answer(t, "result", s) + "\n" for i, s in enumerate(SHOTS[t]))
        return pre + body
    shot_fmt = fmt if fmt in ("compact", "bag") else "prose"
    pre = "".join(f"Message: {render(t, s, shot_fmt, 100 + i)}\nQ: {QUESTIONS[t][q]}\nA: {answer(t, q, s)}\n\n" for i, s in enumerate(SHOTS[t]))
    return pre + f"Message: {body}\nQ: {QUESTIONS[t][q]}\nA:"
def messages():
    rng = np.random.default_rng(0); M = []
    # t1: base combos grouped by (unordered pair, action) so role swaps stay in the same split
    groups = [(p, a) for p in itertools.combinations(ENT, 2) for a in ACT]; rng.shuffle(groups)
    for gi, (p, a) in enumerate(groups):
        sp = "train" if gi < 20 else "dev" if gi < 26 else "test"
        for x, y in (p, p[::-1]):
            for mo in MOD:
                for po in POL: M.append({"t": "t1", "split": sp, "group": f"t1g{gi}", "agent": x, "patient": y, "act": a, "mod": mo, "pol": po})
    # extension data (train only): combos with at least one proposal-pool entity or action
    E2, A2 = ENT + EXT_ENT, ACT + EXT_ACT; ext = [(x, y, a) for x in E2 for y in E2 for a in A2 if x != y and (x in EXT_ENT or y in EXT_ENT or a in EXT_ACT)]
    for k in rng.choice(len(ext), 160, replace=False):
        x, y, a = ext[k]; M.append({"t": "t1", "split": "train", "group": "ext", "agent": x, "patient": y, "act": a, "mod": MOD[k % 2], "pol": POL[(k // 2) % 2], "ext": True})
    # t2: groups = unordered pair of events; 4 messages each (2 orders x 2 order words)
    ev = [(e, a) for e in ENT for a in ACT]; pairs = [(u, v) for u, v in itertools.combinations(ev, 2) if u[0] != v[0] and u[1] != v[1]]
    sel = rng.choice(len(pairs), 80, replace=False)
    for gi, k in enumerate(sel):
        u, v = pairs[k]; sp = "train" if gi < 40 else "dev" if gi < 50 else "test"
        for (e1, ac1), (e2, ac2) in ((u, v), (v, u)):
            for o in ORD: M.append({"t": "t2", "split": sp, "group": f"t2g{gi}", "a1": e1, "act1": ac1, "ord": o, "a2": e2, "act2": ac2})
    # t3: subtract, groups = unordered digit pair {a,b} (role swap 7-2 vs 2-7); shots excluded
    shot = {(s["left"], s["right"]) for s in SHOTS["t3"]}
    dp = list(itertools.combinations(range(10), 2)); rng.shuffle(dp)
    for gi, (a, b) in enumerate(dp):
        sp = "train" if gi < 20 else "dev" if gi < 25 else "test"
        for x, y in ((a, b), (b, a)):
            if (str(x), str(y)) in shot: continue
            M.append({"t": "t3", "split": sp, "group": f"t3g{gi}", "left": str(x), "op": "-", "right": str(y), "eq": "="})
    for i, m in enumerate(M): m["id"] = i
    return M
def queries(M, split):
    Q = []
    for m in M:
        if m["split"] != split or m.get("ext"): continue
        for q in QUESTIONS[m["t"]]: Q.append((m["id"], q))
    return Q
if __name__ == "__main__":
    M = messages(); import collections
    print(collections.Counter((m["t"], m["split"]) for m in M)); print({s: len(queries(M, s)) for s in ("dev", "test")})
    m = M[0]; print(prompt("t1", "agent", render("t1", m, "prose"), "prose")); print(prompt("t1", "pol", SKEL("t1"), "glyph"))
    t3 = [x for x in M if x["t"] == "t3"][0]; print(prompt("t3", "result", COMPACT("t3", t3), "compact"))
