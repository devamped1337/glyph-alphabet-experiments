"""v5 spec: models, vocabulary, messages, splits, 64-token prompts, scoring. Pure python (no torch)."""
import itertools, random, re
import numpy as np

MODELS = {"smol": ("HuggingFaceTB/SmolLM2-1.7B", "effd688a12921b4cc83e3312b6feb579f70f9c71"),   # box
          "qwen": ("Qwen/Qwen2.5-3B", "3aab1f1954e9cc14eb9509a215f9e5ca08227a9b")}          # laptop (WSL)
HOME = {"smol": "box", "qwen": "laptop"}
CTX = 64                         # every prompt (sender reading and receiver test) is exactly 64 tokens
FRACS = [0.25, 0.33]             # candidate patch depths (+ "emb" = embedding output). ONE depth is frozen on dev.
KP, KC = 64, 32                  # per-model basis dim, shared canonical dim
SEEDS = [0, 1, 2]                # adapter-fit seeds (80% train subsample, random-basis draw, null draws)
BASES = ["pca", "jlens", "random"]
PROSE_GATE = 0.9                 # pre-registered: a task counts on a receiver only if dev prose >= 0.9 there

ENT = ["Alice", "Bob", "Carol", "Dave", "Eve", "Mallory", "Oscar", "Peggy"]
ACT = ["paid", "called", "helped", "thanked"]
MOD = ["known", "suspected"]; POL = ["indeed", "never"]; ORD = ["before", "after"]; DIG = [str(d) for d in range(10)]
PLACES = ["Germany", "Munich", "Berlin", "Hamburg", "France", "Paris", "Lyon", "Italy", "Rome", "Milan",
          "Austria", "Vienna", "Spain", "Madrid", "Barcelona"]
COUNTRY = {"Germany": "Germany", "Munich": "Germany", "Berlin": "Germany", "Hamburg": "Germany", "France": "France", "Paris": "France",
           "Lyon": "France", "Italy": "Italy", "Rome": "Italy", "Milan": "Italy", "Austria": "Austria", "Vienna": "Austria",
           "Spain": "Spain", "Madrid": "Spain", "Barcelona": "Spain"}
CLUES = {"Germany": ["the country that hosts the Bundestag", "the largest economy in the EU"],
         "Munich": ["the Bavarian capital", "the city of Oktoberfest"],
         "Berlin": ["the German capital", "the city of the Brandenburg Gate"],
         "Hamburg": ["Germany's biggest port city", "the city on the Elbe with the Reeperbahn"],
         "France": ["the country of the Loire valley", "the land of Bastille Day"],
         "Paris": ["the French capital", "the city of the Eiffel Tower"],
         "Lyon": ["France's gastronomic capital", "the city where the Rhone meets the Saone"],
         "Italy": ["the boot-shaped country", "the country of the Dolomites and Tuscany"],
         "Rome": ["the Italian capital", "the city of the Colosseum"],
         "Milan": ["Lombardy's capital", "the city of La Scala"],
         "Austria": ["the Alpine republic south of Bavaria", "the country of the Habsburgs"],
         "Vienna": ["the Austrian capital", "the city of the Vienna State Opera on the Ringstrasse"],
         "Spain": ["the country of flamenco and the Iberian kingdom", "the land of La Liga"],
         "Madrid": ["the Spanish capital", "the city of the Prado museum"],
         "Barcelona": ["the Catalan capital", "the city of the Sagrada Familia"]}
PLACE_FRAMES = ["We flew to {p} last week.", "Our office in {p} is closing.", "She grew up in {p}.", "The parcel was shipped from {p}.",
                "Tickets to {p} sold out.", "He studied in {p} for a year.", "The conference moved to {p}.", "I just got back from {p}.",
                "My cousin works in {p}.", "The train to {p} was late.", "They opened a shop in {p}.", "Prices in {p} went up.",
                "The team trained in {p}.", "A storm hit {p} yesterday.", "Her book is set in {p}.", "We met friends in {p}.",
                "The band toured {p} in May.", "His company moved to {p}.", "The flight from {p} landed early.", "Rents in {p} are high.",
                "The wedding was held in {p}.", "Our supplier is based in {p}."]
PF_SPLIT = {"train": range(0, 8), "dev": range(8, 10), "test": range(10, 22)}

STATUS = ["requested", "authorized", "approved", "not approved", "valid now", "expired", "absent", "omitted"]   # minimal pairs (tantive-space)
REC_IDS = ["A17", "B42", "C08", "D93", "E25", "F61", "G34", "H70", "J12", "K88", "L53", "M29", "N46", "P05", "Q77", "R31", "S64", "T19", "U82", "V40",
           "W57", "X13", "Y96", "Z38", "Q11"]
UNRECOGNIZED = "UNRECOGNIZED"
SLOTS = {"t1": ["mod", "agent", "pol", "act", "patient"], "t2": ["a1", "act1", "ord", "a2", "act2"], "t3": ["left", "right"], "t4": ["place"], "t5": ["status"]}
DOMAIN = {"mod": MOD, "agent": ENT, "pol": POL, "act": ACT, "patient": ENT, "a1": ENT, "act1": ACT, "ord": ORD, "a2": ENT, "act2": ACT,
          "left": DIG, "right": DIG, "place": PLACES, "status": STATUS}
QUESTIONS = {"t1": {"agent": "Who did it?", "patient": "Who was it done to?", "pol": "Did it happen?", "mod": "Is it certain?"},
             "t2": {"first": "Who acted first?"}, "t3": {"result": None}, "t4": {"where": "Where?"}, "t5": {"status": "What is the status?"}}
SHOT_ENT = ["Victor", "Wendy", "Trent"]; SHOT_ACT = ["met", "sent"]; SHOT_PLACE = ["Oslo", "Lisbon", "Prague"]

def body(t, m):
    """book format / receiver prose (also what the glyph skeleton replaces)"""
    if t == "t1": return f"It is {m['mod']} that {m['agent']} {m['pol']} {m['act']} {m['patient']}."
    if t == "t2": return f"{m['a1']} {m['act1']} {m['ord']} {m['a2']} {m['act2']}."
    if t == "t3": return f"{m['left']}-{m['right']}="
    if t == "t5": return f"Record {m['rec']} is {m['status']}."
    return PLACE_FRAMES[m.get("frame", 0)].format(p=m["place"])
def sender_text(t, m):
    """the sender's own reading: a paraphrase frame never used to build receiver prompts (t4: frame or clue)"""
    if t == "t1": return f"Word is, and it is {m['mod']}, that {m['agent']} {m['pol']} {m['act']} {m['patient']}."
    if t == "t2": return f"I heard that {m['a1']} {m['act1']} {m['ord']} {m['a2']} {m['act2']}."
    if t == "t3": return ["Compute: {l}-{r}=", "Work out {l}-{r}=", "Quick sum: {l}-{r}=", "Now {l}-{r}="][m["frame"] % 4].format(l=m["left"], r=m["right"])
    if t == "t5": return f"Update from the registry: record {m['rec']} is now {m['status']}."
    return PLACE_FRAMES[m["frame"]].format(p=m["clue"] if m.get("clue") else m["place"])
def sender_values(t, m):
    """surface strings whose LAST token is read in sender_text (clue => last token of the clue phrase)"""
    if t == "t4": return [m["clue"] or m["place"]]
    return [m[s] for s in SLOTS[t]]
def skel(t, m):
    if t == "t1": return "It is ? that ? ? ? ?."
    if t == "t2": return "? ? ? ? ?."
    if t == "t3": return "?-?="
    if t == "t5": return f"Record {m['rec']} is ?."
    return PLACE_FRAMES[m.get("frame", 0)].format(p="?")
def compact(t, m):
    if t == "t1": return f"{m['act']}({m['agent']},{m['patient']},{m['mod']},{'yes' if m['pol'] == 'indeed' else 'not'})"
    if t == "t2": return f"{m['ord']}({m['a1']}.{m['act1']},{m['a2']}.{m['act2']})"
    if t == "t3": return f"sub({m['left']},{m['right']})="
    if t == "t5": return f"rec({m['rec']},{m['status'].replace(' ', '_')})"
    return f"loc({m['place']})"
def answer(t, q, m):
    if t == "t1": return {"agent": m["agent"], "patient": m["patient"], "pol": "yes" if m["pol"] == "indeed" else "no", "mod": "yes" if m["mod"] == "known" else "no"}[q]
    if t == "t2": return m["a1"] if m["ord"] == "before" else m["a2"]
    if t == "t3": return str(int(m["left"]) - int(m["right"]))
    if t == "t5": return m["status"]
    return m["place"]
def candidates(t, q):
    if t == "t3": return None
    if t == "t4": return PLACES
    if t == "t5": return STATUS
    return ENT if (t == "t2" or q in ("agent", "patient")) else ["yes", "no"]
SHOTS = {"t1": [dict(mod="known", agent="Victor", pol="indeed", act="met", patient="Wendy"), dict(mod="suspected", agent="Trent", pol="never", act="sent", patient="Victor"),
                dict(mod="known", agent="Wendy", pol="never", act="sent", patient="Trent")],
         "t2": [dict(a1="Victor", act1="met", ord="before", a2="Wendy", act2="sent"), dict(a1="Trent", act1="sent", ord="after", a2="Wendy", act2="met"),
                dict(a1="Wendy", act1="met", ord="after", a2="Victor", act2="sent")],
         "t3": [dict(left="9", right="4"), dict(left="3", right="8"), dict(left="6", right="1"), dict(left="2", right="9"), dict(left="7", right="7")],
         "t4": [dict(place="Oslo", frame=3), dict(place="Lisbon", frame=5), dict(place="Prague", frame=1)],
         "t5": [dict(rec="AA1", status="pending"), dict(rec="BB2", status="rejected")]}
FILLER = ("Below are short messages, each followed by a question and its answer. Read each message carefully and answer briefly. " * 4)
def prompt_core(t, q, msg_text, fmt, nshots):
    """few-shot core WITHOUT filler. fmt: prose|compact|glyph|none|idraw. Shots use names/words outside the test vocabulary."""
    sf = "compact" if fmt == "compact" else "prose"
    rend = (lambda tt, s: compact(tt, s)) if sf == "compact" else (lambda tt, s: body(tt, s))
    if t == "t3":
        return "".join(rend(t, s) + answer(t, "result", s) + "\n" for s in SHOTS[t][:nshots]) + msg_text
    qq = QUESTIONS[t][q] if q in QUESTIONS[t] else list(QUESTIONS[t].values())[0]
    pre = "".join(f"Message: {rend(t, s)}\nQ: {qq}\nA: {answer(t, q, s)}\n" for s in SHOTS[t][:nshots])
    return pre + f"Message: {msg_text}\nQ: {qq}\nA:"
def fit64(tok, t, q, msg_text, fmt, ctx=CTX):
    """token ids of exactly ctx tokens: as many shots as fit, then left-filled with FILLER tokens. Returns (ids list, core_offset, core_text)."""
    for ns in range(len(SHOTS.get(t, [])), -1, -1):
        core = prompt_core(t, q, msg_text, fmt, ns); cids = tok.encode(core, add_special_tokens=False)
        if len(cids) <= ctx: break
    else: raise ValueError("prompt does not fit")
    fill = tok.encode(FILLER, add_special_tokens=False)[: ctx - len(cids)]
    return fill + cids, len(fill), core
def sender_prompt(t, m): return "Message: " + sender_text(t, m)
def bag(t, m, seed):
    w = [m[s] for s in SLOTS[t]]; r = random.Random(seed); p = w[:]
    for _ in range(20):
        r.shuffle(p)
        if p != w: break
    return " ".join(p) + "."

def messages():
    rng = np.random.default_rng(0); M = []
    groups = [(p, a) for p in itertools.combinations(ENT, 2) for a in ACT]; rng.shuffle(groups); ng = len(groups)
    for gi, (p, a) in enumerate(groups):          # role swaps stay inside a group
        sp = "train" if gi < 0.5 * ng else "dev" if gi < 0.62 * ng else "test"
        for x, y in (p, p[::-1]):
            for mo in MOD:
                for po in POL: M.append({"t": "t1", "split": sp, "group": f"t1g{gi}", "agent": x, "patient": y, "act": a, "mod": mo, "pol": po})
    combos = [(a1, x1, o, a2, x2) for a1 in ENT for a2 in ENT if a1 != a2 for x1 in ACT for x2 in ACT if x1 != x2 for o in ORD]
    pairs = sorted({tuple(sorted((c[0], c[3]))) + (tuple(sorted((c[1], c[4]))),) for c in combos}); rng.shuffle(pairs)
    pg = {p: ("train" if i < 0.5 * len(pairs) else "dev" if i < 0.62 * len(pairs) else "test") for i, p in enumerate(pairs)}
    for k in rng.choice(len(combos), 900, replace=False):
        a1, x1, o, a2, x2 = combos[k]; key = tuple(sorted((a1, a2))) + (tuple(sorted((x1, x2))),)
        M.append({"t": "t2", "split": pg[key], "group": "t2g" + "_".join(key[:2]) + "_" + "_".join(key[2]), "a1": a1, "act1": x1, "ord": o, "a2": a2, "act2": x2})
    dp = [(l, r) for l in DIG for r in DIG]; rng.shuffle(dp)          # maths: split by UNORDERED pair so 7-2 and 2-7 share a split
    up = sorted({tuple(sorted(p)) for p in dp}); rng.shuffle(up)
    us = {p: ("train" if i < 0.4 * len(up) else "dev" if i < 0.52 * len(up) else "test") for i, p in enumerate(up)}
    for l, r in dp:
        for f in range(4): M.append({"t": "t3", "split": us[tuple(sorted((l, r)))], "group": f"t3g{min(l, r)}{max(l, r)}", "left": l, "right": r, "frame": f})
    for p in PLACES:
        for sp, fr in PF_SPLIT.items():
            for f in fr: M.append({"t": "t4", "split": sp, "group": f"t4{p}", "place": p, "frame": f, "clue": None})
        for ci, c in enumerate(CLUES[p]): M.append({"t": "t4", "split": "test", "group": f"t4{p}", "place": p, "frame": 2 + ci, "clue": c})
    for k, st in enumerate(STATUS):            # t5 appended last so earlier message ids are unchanged
        for ri, rec in enumerate(REC_IDS):
            M.append({"t": "t5", "split": "train" if ri < 10 else "dev" if ri < 13 else "test", "group": f"t5{rec}", "rec": rec, "status": st})
    for m in M:                                 # audit fix: demo (few-shot) maths pairs and their reversals never enter evaluation
        if m["t"] == "t3" and tuple(sorted((m["left"], m["right"]))) in DEMO_PAIRS and m["split"] != "train": m["split"] = "excluded_demo"
    for i, m in enumerate(M): m["id"] = i
    return M
DEMO_PAIRS = {tuple(sorted((s["left"], s["right"]))) for s in SHOTS["t3"]}
def queries(M, split):
    assert split in ("dev", "test"); Q = []
    for m in M:
        if m["split"] != split: continue
        for q in QUESTIONS[m["t"]]:
            assert not (m["t"] == "t3" and tuple(sorted((m["left"], m["right"]))) in DEMO_PAIRS), "demo pair in evaluation"
            Q.append((m["id"], q))
    return Q
def parse_int(s):
    mm = re.match(r"\s*(-?\d+)", s); return int(mm.group(1)) if mm else None
def score_maths(pred, gold):
    g = int(gold); p = parse_int(pred); sg = (g > 0) - (g < 0)
    if p is None: return {"exact": 0, "magnitude": 0, "sign": 0}
    return {"exact": int(p == g), "magnitude": int(abs(p) == abs(g)), "sign": int(((p > 0) - (p < 0)) == sg)}
def string_match(text, names=PLACES):
    """baseline for selection: exact substring (longest wins) else best char-trigram Jaccard"""
    hits = [n for n in names if re.search(r"\b" + re.escape(n) + r"\b", text)]
    if hits: return sorted(hits, key=len)[-1], "substring"
    tri = lambda s: {s.lower()[i:i + 3] for i in range(max(1, len(s) - 2))}
    T = tri(text); sc = [len(T & tri(n)) / len(T | tri(n)) for n in names]
    return names[int(np.argmax(sc))], "trigram"
