"""Frozen case / probe generator (PREREG_E1b §5, §7, §9; A1.5).

Everything is a pure function of config seeds. `build(cfg)` returns the full book; `verify(book, cfg)` re-runs
every builder assertion (also called by the validator). Any violation raises AssertionError -> build aborts.

Entry semantics ("sem") are what a faithful reader of the entry text can conclude; None = not stated / not
determinable. Planted (corrupted) entries carry their own rendered text and sem; honest gold always comes
from the honest entry.
"""
import random, copy, math
from . import sha256_text, norm

NOUNS = ["Brindle", "Corvel", "Dunmar", "Elsworth", "Fenrow", "Galtry", "Hesper", "Iselin", "Jorvik", "Kelmar",
         "Lumsk", "Morvane", "Nethra", "Orsk", "Pellan", "Quillon", "Rastor", "Selmet", "Tovrin", "Ulvar",
         "Vantrel", "Wexley", "Yarrow", "Zelmo", "Ambrel", "Caskel", "Dovrin", "Ferro", "Gildra", "Harrow"]
ROLES = [("plenter", "taker"), ("lodger", "keeper"), ("sender", "courier"), ("vendor", "fetcher"),
         ("drover", "stabler"), ("tutor", "ward"), ("brewer", "carter"), ("donor", "clerk"),
         ("miller", "hauler"), ("weaver", "dyer")]
NAMES = ["Ana", "Bo", "Cy", "Dee", "Eli", "Fay", "Gus", "Ivy", "Jo", "Kai", "Lu", "Max", "Ned", "Ola", "Pia",
         "Rex", "Sol", "Tam", "Uma", "Vic", "Wes", "Xan", "Yul", "Zed"]
UNITS = ["crate", "kilogram", "hour", "ticket", "parcel", "litre", "seat", "page", "bale", "sack"]
F3_FILLER = ("This schedule applies to every booking recorded in the shared ledger, whether it was made "
             "in person, by phone or through the portal. Staff must record the booking date, the start date "
             "and the name of the person responsible before any charge is calculated. Charges are always "
             "expressed in whole credits, and no rounding is applied at any step. Bookings that were cancelled "
             "before the start date are handled under a separate schedule and are out of scope here. Where this "
             "schedule and an older notice disagree, this schedule takes precedence. Questions about a charge should be "
             "raised with the ledger office within thirty days of the end of the stay. ")
NOT_STATED = "Not stated by the rule"

# ------------------------------------------------------------------ entries
class IdAlloc:
    def __init__(self, rng): self.rng, self.used = rng, set()
    def new(self, fam):
        while True:
            i = f"{fam}-{self.rng.randrange(10000):04d}"
            if i not in self.used: self.used.add(i); return i

def honest_params(fam, rng):
    if fam == "F1":
        a = rng.randint(2, 9); b = rng.choice([v for v in range(2, 10) if v != a])
        return dict(g=rng.choice(NOUNS), unit=rng.choice(UNITS), sem=dict(mem=a, non=b))
    if fam == "F2":
        x, y = rng.choice(ROLES); a = rng.randint(2, 9); b = rng.choice([v for v in range(2, 10) if v != a])
        return dict(x=x, y=y, sem=dict(xr=a, yr=b))
    a = rng.randint(3, 9); c = rng.choice([v for v in range(2, 12) if v != a])
    return dict(g=rng.choice(NOUNS), sem=dict(a=a, t=rng.randint(3, 6), c=c, s=rng.randint(10, 19), waive=True))

def render_def(e):
    """Agreed definition text from sem (honest or neighbour entries)."""
    f, s = e["fam"], e["sem"]
    if f == "F1":
        return (f"Pricing rule. {e['g']} members are charged {s['mem']} credits per {e['unit']}. "
                f"Customers who are not {e['g']} members are charged {s['non']} credits per {e['unit']}.")
    if f == "F2":
        return (f"Hand-over rule. When a {e['x']} hands items to a {e['y']}, the {e['x']} pays {s['xr']} credits per item "
                f"and the {e['y']} pays {s['yr']} credits per item. The {e['y']} does not pay the {e['x']}'s share.")
    core = (f"The daily charge is {s['a']} credits for each of the first {s['t']} days. "
            f"Every day beyond the first {s['t']} days is charged {s['c']} credits instead. "
            f"Holders of a {e['g']} permit are not charged the {s['s']}-credit service fee; everyone else pays it once per booking.")
    if f == "F3s": return "Booking charge schedule. " + core
    return "Booking charge schedule. " + F3_FILLER + core + " " + F3_FILLER.split(". ")[1] + "."

WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
         "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty"]
def spell(n): return WORDS[n] if 0 <= n < len(WORDS) else str(n)
MSG_STYLES = ["spelled", "reordered", "derived"]

def render_message(e):
    """Natural-language original message (paraphrase; what the sender reads and the prose arm receives).
    A2: >=1/3 of TEST entries (frozen seed) get a harder style: spelled-out numbers, reordered clauses, or a
    derived (relative) form."""
    st = e.get("msg_style", "plain")
    if st != "plain": return render_message_hard(e, st)
    f, s = e["fam"], e["sem"]
    if f == "F1":
        return (f"Belonging to the {e['g']} scheme gets a customer a rate of {s['mem']} credits for each {e['unit']}; "
                f"anybody lacking {e['g']} membership pays {s['non']} credits for each {e['unit']} instead.")
    if f == "F2":
        return (f"In a hand-over, whoever gives the items (the {e['x']}) is billed {s['xr']} credits for each item, "
                f"while whoever takes them (the {e['y']}) is billed {s['yr']} credits for each item; neither covers the other's bill.")
    return (f"A stay costs {s['a']} credits a day up to day {s['t']}; from day {s['t']+1} onward each day costs {s['c']} credits. "
            f"There is also a one-off {s['s']}-credit service fee, waived for anyone holding a {e['g']} permit.")

def render_message_hard(e, st):
    f, s = e["fam"], e["sem"]; N = spell if st == "spelled" else str
    if f == "F1":
        a, b, g, u = s["mem"], s["non"], e["g"], e["unit"]
        if st == "derived":
            rel = "less" if a < b else "more"
            return (f"Anybody lacking {g} membership pays {b} credits for each {u}; belonging to the {g} scheme means paying "
                    f"{abs(a - b)} credits {rel} than that for each {u}.")
        if st == "reordered":
            return f"Anybody lacking {g} membership pays {b} credits for each {u}, whereas a customer in the {g} scheme gets a rate of {a} credits for each {u}."
        return (f"Belonging to the {g} scheme gets a customer a rate of {N(a)} credits for each {u}; "
                f"anybody lacking {g} membership pays {N(b)} credits for each {u} instead.")
    if f == "F2":
        a, b, x, y = s["xr"], s["yr"], e["x"], e["y"]
        if st == "derived":
            rel = "less" if b < a else "more"
            return (f"In a hand-over, whoever gives the items (the {x}) is billed {a} credits for each item, and whoever takes them "
                    f"(the {y}) is billed {abs(a - b)} credits {rel} per item than the {x}; neither covers the other's bill.")
        if st == "reordered":
            return (f"In a hand-over, whoever takes the items (the {y}) is billed {b} credits for each item, while whoever gives them "
                    f"(the {x}) is billed {a} credits for each item; neither covers the other's bill.")
        return (f"In a hand-over, whoever gives the items (the {x}) is billed {N(a)} credits for each item, "
                f"while whoever takes them (the {y}) is billed {N(b)} credits for each item; neither covers the other's bill.")
    a, t, c, fee, g = s["a"], s["t"], s["c"], s["s"], e["g"]
    if st == "derived":
        rel = "less" if c < a else "more"
        return (f"A stay costs {a} credits a day up to day {t}; from day {t+1} onward each day costs {abs(c - a)} credits {rel} than that. "
                f"There is also a one-off {fee}-credit service fee, waived for anyone holding a {g} permit.")
    if st == "reordered":
        return (f"There is a one-off {fee}-credit service fee, waived for anyone holding a {g} permit. From day {t+1} onward each day "
                f"costs {c} credits; up to day {t} a stay costs {a} credits a day.")
    return (f"A stay costs {N(a)} credits a day up to day {N(t)}; from day {N(t+1)} onward each day costs {N(c)} credits. "
            f"There is also a one-off {N(fee)}-credit service fee, waived for anyone holding a {g} permit.")

def render_label(e):
    """One-line candidate label shown to the sender (compact form; carries the load-bearing constants)."""
    f, s = e["fam"], e["sem"]
    if f == "F1": return f"{e['g']} member {s['mem']}/{e['unit']}; non-member {s['non']}/{e['unit']}"
    if f == "F2": return f"hand-over: {e['x']} pays {s['xr']}/item, {e['y']} pays {s['yr']}/item"
    return f"stay: {s['a']}/day to day {s['t']}, then {s['c']}/day; fee {s['s']} waived with {e['g']} permit"

_FORBID = set()   # A9: normalised entry texts of an earlier book; empty for the frozen book (unchanged behaviour)
def mk_entry(fam, ids, rng, params=None):
    for _ in range(1000):
        e = dict(fam=fam, id=ids.new(fam), ver=1, **copy.deepcopy(params or honest_params(fam, rng)))
        e["text"] = render_def(e); e["hash"] = sha256_text(e["text"]); e["kind"] = "honest"
        if params is not None or norm(e["text"]) not in _FORBID: return e
    raise RuntimeError("A9: could not make an entry text unseen in the earlier book")

# ------------------------------------------------------------------ neighbours (confusable, load-bearing)
def neighbour_params(e, k, rng):
    p = {kk: copy.deepcopy(v) for kk, v in e.items() if kk in ("g", "unit", "x", "y", "sem")}
    s = p["sem"]
    if e["fam"] == "F1": keys = ("mem", "non")
    elif e["fam"] == "F2": keys = ("xr", "yr")
    else: keys = ("a", "c")
    u, v = keys
    if k == 0: s[u], s[v] = s[v], s[u]                       # polarity / role direction swapped
    elif k == 1: s[u] += rng.randint(1, 3); s[v] += rng.randint(1, 3)   # constants shifted
    else:
        s[u], s[v] = s[v] + rng.randint(1, 3), s[u] + rng.randint(1, 3)  # swapped and shifted
    if e["fam"] in ("F3s", "F3L") and k == 1: s["s"] += rng.randint(1, 4)
    return p

# ------------------------------------------------------------------ planted corruptions
def planted_entry(honest, ctype, ids, rng, donor=None, strong=False):
    """Return a planted entry: same ID-space semantics, corrupted text; sem = what the text actually says.
    A5 (2026-10-12): strong=True (calibration plants only) makes changed_constant change BOTH stated rates (+3),
    so >= 0.30 of the probes flip. No extra rng draws, so every other group is byte-identical."""
    f = honest["fam"]; assert f in ("F1", "F2"), "planted entries are core-family only"
    e = copy.deepcopy(honest); e["id"] = ids.new(f); e["kind"] = "planted"; e["corruption"] = ctype
    e["honest_id"] = honest["id"]; s = dict(honest["sem"]); txt = render_def(honest)
    if f == "F1":
        a, b, g, u = s["mem"], s["non"], honest["g"], honest["unit"]
        P = f"{g} members are charged {a} credits per {u}."; N = f"Customers who are not {g} members are charged {b} credits per {u}."
        if ctype == "changed_constant":
            s["mem"] = a + 3; P = P.replace(f" {a} ", f" {a+3} ")
            if strong: s["non"] = b + 3; N = N.replace(f" {b} ", f" {b+3} ")
        elif ctype == "deleted_negation": N = N.replace(" not ", " "); s["mem"] = None; s["non"] = None
        elif ctype == "near_miss_polarity": P = f"{g} members are not charged {a} credits per {u}."; s["mem"] = None
        elif ctype == "swapped_roles":
            P = f"{g} members are charged {b} credits per {u}."; N = f"Customers who are not {g} members are charged {a} credits per {u}."
            s["mem"], s["non"] = b, a
        elif ctype == "inverted_comparison":
            d = abs(b - a); word = "less" if b > a else "more"   # true direction inverted
            N = f"Customers who are not {g} members are charged {d} credits {word} per {u} than members."
            s["non"] = a - d if b > a else a + d
        elif ctype == "dropped_clause": N = ""; s["non"] = None
        elif ctype == "mismatched_definition":
            txt = donor["text"]; s = dict(mem=None, non=None)
        if ctype != "mismatched_definition": txt = f"Pricing rule. {P} {N}".strip()
    else:
        a, b, x, y = s["xr"], s["yr"], honest["x"], honest["y"]
        S1 = f"When a {x} hands items to a {y}, the {x} pays {a} credits per item"
        S2 = f" and the {y} pays {b} credits per item."; S3 = f" The {y} does not pay the {x}'s share."
        if ctype == "changed_constant":
            s["xr"] = a + 3; S1 = S1.replace(f" {a} ", f" {a+3} ")
            if strong: s["yr"] = b + 3; S2 = S2.replace(f" {b} ", f" {b+3} ")
        elif ctype == "deleted_negation": S3 = f" The {y} pays the {x}'s share."; s["yr"] = a + b
        elif ctype == "near_miss_polarity": S2 = f" and the {y} does not pay {b} credits per item."; s["yr"] = None
        elif ctype == "swapped_roles":
            S1 = f"When a {x} hands items to a {y}, the {x} pays {b} credits per item"; S2 = f" and the {y} pays {a} credits per item."
            s["xr"], s["yr"] = b, a
        elif ctype == "inverted_comparison":
            d = abs(b - a); word = "less" if b > a else "more"
            S2 = f" and the {y} pays {d} credits {word} per item than the {x}."; s["yr"] = a - d if b > a else a + d
        elif ctype == "dropped_clause": S2 = "."; s["yr"] = None
        elif ctype == "mismatched_definition": txt = donor["text"]; s = dict(xr=None, yr=None)
        if ctype != "mismatched_definition": txt = "Hand-over rule. " + S1 + S2 + S3
    e["text"], e["sem"], e["hash"] = txt, s, sha256_text(txt)
    return e

def planted_ok(honest, ctype):
    s = honest["sem"]
    if ctype == "inverted_comparison":
        a, b = (s["mem"], s["non"]) if honest["fam"] == "F1" else (s["xr"], s["yr"])
        return (a - abs(b - a) if b > a else a + abs(b - a)) >= 1
    return True

# ------------------------------------------------------------------ probes (rule comprehension, 4-way)
PROBE_KINDS = {   # A2: + "unstated" (honest gold = Not stated) so "Not stated" is not always eliminable
    "F1": ["mem", "non", "higher", "lower", "unstated"],
    "F2": ["xr", "yr", "higher", "lower", "unstated"],
    "F3s": ["a", "c", "t", "s", "waive", "unstated"], "F3L": ["a", "c", "t", "s", "waive", "unstated"],
}
FRAMES = {  # 5 phrasing variants per kind (F1/F2) -> 20 templates; F3 4 variants x 5 kinds = 20
    "F1": {
        "mem": ["How many credits per {unit} is a {g} member charged?", "{n} holds {g} membership. What is {n}'s rate per {unit}?",
                "Per {unit}, what does the rule charge someone who is a {g} member?", "What rate per {unit} applies to {g} members?",
                "{n}, a {g} member, asks for the per-{unit} price. What is it?"],
        "non": ["How many credits per {unit} is a customer who is not a {g} member charged?", "{n} has no {g} membership. What is {n}'s rate per {unit}?",
                "Per {unit}, what does the rule charge someone outside the {g} scheme?", "What rate per {unit} applies to non-members of {g}?",
                "{n}, who is not a {g} member, asks for the per-{unit} price. What is it?"],
        "higher": ["Which group pays more per {unit}?", "Under this rule, who is charged the higher rate per {unit}?",
                   "{n} wants the cheaper rate per {unit} to be avoided. Which group pays the higher one?", "Whose per-{unit} rate is larger?",
                   "Which customers face the larger charge per {unit}?"],
        "lower": ["Which group pays less per {unit}?", "Under this rule, who is charged the lower rate per {unit}?",
                  "{n} wants the cheaper rate per {unit}. Which group gets it?", "Whose per-{unit} rate is smaller?",
                  "Which customers face the smaller charge per {unit}?"],
    },
    "F2": {
        "xr": ["How many credits per item does the {x} pay?", "{n} is the {x} in a hand-over. What does {n} pay per item?",
               "Per item, what is the {x} billed?", "What per-item charge falls on the {x}?", "{n} hands items over as the {x}. Rate per item?"],
        "yr": ["How many credits per item does the {y} pay?", "{n} is the {y} in a hand-over. What does {n} pay per item?",
               "Per item, what is the {y} billed?", "What per-item charge falls on the {y}?", "{n} receives items as the {y}. Rate per item?"],
        "higher": ["Who pays more per item?", "Which party is billed the higher per-item amount?", "{n} wants to know who pays the larger per-item share. Who?",
                   "Whose per-item charge is larger?", "Which role faces the bigger per-item bill?"],
        "lower": ["Who pays less per item?", "Which party is billed the lower per-item amount?", "{n} wants to know who pays the smaller per-item share. Who?",
                  "Whose per-item charge is smaller?", "Which role faces the smaller per-item bill?"],
    },
}
_F3 = {
    "a": ["What is the daily charge during the first days of a stay?", "{n} stays one day. What is that day's charge (excluding fees)?",
          "Per day, what does the schedule charge at the start of a stay?", "What is the opening daily rate?"],
    "c": ["What is the daily charge after the initial period?", "{n}'s stay runs long. What is the charge for each later day?",
          "Per day, what does the schedule charge beyond the initial days?", "What is the later daily rate?"],
    "t": ["For how many days does the initial daily rate apply?", "How long is the initial-rate period, in days?",
          "{n} asks when the daily rate changes. After how many days?", "How many opening days use the first rate?"],
    "s": ["How large is the service fee, in credits?", "What is the one-off fee in credits?",
          "{n} must pay the service fee. How many credits is it?", "What fee is charged once per booking?"],
    "waive": ["Who does not pay the service fee?", "Which bookers are exempt from the fee?",
              "{n} wants to avoid the service fee. Who qualifies?", "The fee is waived for whom?"],
}
_F3["unstated"] = ["What is the cancellation charge in credits?", "{n} asks what the late-checkout charge is. How many credits?",
                    "How many credits does the deposit cost?", "What is the per-night cleaning charge?"]
FRAMES["F1"]["unstated"] = ["What one-off joining fee does the rule set, in credits?", "{n} asks about the delivery charge per order. How many credits?",
                            "How many credits does a {g} membership card cost?", "What discount per {unit} applies on holidays?"]
FRAMES["F2"]["unstated"] = ["How many credits per item does a third-party inspector pay?", "{n} asks about the storage charge per item. How many credits?",
                            "What insurance charge per hand-over does the rule set?", "How many credits does a late hand-over cost?"]
FRAMES["F3s"] = _F3; FRAMES["F3L"] = _F3

RESERVE_PREFIXES = ["According to the rule, ", "Going only by the rule: ", "Based on the rule text, "]

def templates(fam):
    return [(f"{fam}-{k}-v{v}", k, fr) for k in PROBE_KINDS[fam] for v, fr in enumerate(FRAMES[fam][k])]

def reserve_templates(fam):
    """Frozen replacement list (A1.5): for a flagged template the next unused reserve of the SAME kind is used."""
    out = []
    for r, pre in enumerate(RESERVE_PREFIXES):
        for k in PROBE_KINDS[fam]:
            fr = FRAMES[fam][k][r % len(FRAMES[fam][k])]
            out.append((f"{fam}-{k}-r{r}", k, pre + fr[0].lower() + fr[1:]))
    return out

def _probe_truth(e_ref, sem, kind):
    """Correct answer (string) given the semantics of the text the model reads; e_ref gives names."""
    f = e_ref["fam"]
    if kind == "unstated": return NOT_STATED
    if f == "F1":
        if kind in ("mem", "non"): return NOT_STATED if sem.get(kind) is None else str(sem[kind])
        m, n = sem.get("mem"), sem.get("non")
        if m is None or n is None: return NOT_STATED
        hi = f"{e_ref['g']} members" if m > n else f"Customers who are not {e_ref['g']} members"
        lo = f"Customers who are not {e_ref['g']} members" if m > n else f"{e_ref['g']} members"
        return hi if kind == "higher" else lo
    if f == "F2":
        if kind in ("xr", "yr"): return NOT_STATED if sem.get(kind) is None else str(sem[kind])
        a, b = sem.get("xr"), sem.get("yr")
        if a is None or b is None: return NOT_STATED
        hi, lo = (f"The {e_ref['x']}", f"The {e_ref['y']}") if a > b else (f"The {e_ref['y']}", f"The {e_ref['x']}")
        return hi if kind == "higher" else lo
    if kind == "waive": return f"Holders of a {e_ref['g']} permit"
    return str(sem[kind])

def _probe_options(e_ref, kind, truth, rng):
    f, s = e_ref["fam"], e_ref["sem"]
    if f == "F1" and kind in ("higher", "lower"):
        opts = [f"{e_ref['g']} members", f"Customers who are not {e_ref['g']} members", "Both pay the same", NOT_STATED]
    elif f == "F2" and kind in ("higher", "lower"):
        opts = [f"The {e_ref['x']}", f"The {e_ref['y']}", "Both pay the same", NOT_STATED]
    elif kind == "waive":
        opts = [f"Holders of a {e_ref['g']} permit", f"People without a {e_ref['g']} permit", "Everyone", NOT_STATED]
    else:
        # A2 plausible distractors: the entry's other constants first, then truth +/- 1..2 (never random 2-20)
        nums = [str(v) for k, v in s.items() if isinstance(v, int) and not isinstance(v, bool) and k != kind]
        rng.shuffle(nums)
        pick = [truth] if truth != NOT_STATED else []
        for z in nums:
            if len(pick) >= 2: break
            if z not in pick: pick.append(z)
        base = int(truth) if truth != NOT_STATED else int(nums[0]) if nums else 5
        for dlt in rng.sample([1, -1, 2, -2, 3], 5):
            if len(pick) >= 3: break
            z = str(base + dlt)
            if z not in pick and base + dlt >= 1: pick.append(z)
        opts = pick[:3] + [NOT_STATED]
    rng.shuffle(opts)
    return opts

def make_probes(e_text_entry, e_ref, rng, fam=None, tpl=None):
    """Probes for one entry: e_text_entry is what the model reads (honest or planted); e_ref supplies names/
    honest options. Gold = truth under the text actually shown; honest_gold = truth under the honest entry."""
    out = []
    for tid, kind, frame in (tpl or templates(fam or e_ref["fam"])):
        q = frame.format(n=rng.choice(NAMES), **{k: e_ref[k] for k in ("g", "unit", "x", "y") if k in e_ref})
        truth = _probe_truth(e_ref, e_text_entry["sem"], kind)
        h_truth = _probe_truth(e_ref, e_ref["sem"], kind)
        opts = _probe_options(e_ref, kind, h_truth, rng)
        if truth not in opts: opts[opts.index(NOT_STATED) if truth != NOT_STATED else 0] = truth
        if h_truth not in opts:
            j = next(i for i, o in enumerate(opts) if o not in (truth,)); opts[j] = h_truth
        L = "ABCD"
        out.append(dict(template=tid, kind=kind, question=q, options=opts,
                        gold=L[opts.index(truth)], honest_gold=L[opts.index(h_truth)]))
    return out

# ------------------------------------------------------------------ arithmetic cases
def mk_case(e, rng, seen, case_sem=None, branch=None):
    """Case + honest gold (from e['sem']); planted gold from case_sem if given. Globally unique text."""
    f = e["fam"]; s = e["sem"]
    for _ in range(500):
        if f == "F1":
            mem = rng.random() < 0.5; n = rng.randint(2, 12); nm = rng.choice(NAMES)
            if branch is not None: mem = bool(branch)   # A9 round 4b: forced answer branch (None = frozen behaviour)
            txt = (f"{nm} {'is' if mem else 'is not'} a {e['g']} member and buys {n} {e['unit']}s. "
                   f"How many credits is {nm} charged in total?")
            key = "mem" if mem else "non"; gold = n * s[key]
            pg = None if case_sem is None else (None if case_sem.get(key) is None else n * case_sem[key])
            meta = dict(n=n, mem=mem)
        elif f == "F2":
            n = rng.randint(2, 12); n1, n2 = rng.sample(NAMES, 2); ask_y = rng.random() < 0.5
            if branch is not None: ask_y = bool(branch)
            txt = rng.choice([f"{n1}, acting as {e['x']}, hands {n} items to {n2}, the {e['y']}. ",
                              f"{n2} (the {e['y']}) receives {n} items from {n1} (the {e['x']}). "])
            txt += f"How many credits does {n2 if ask_y else n1} pay in total?"
            key = "yr" if ask_y else "xr"; gold = n * s[key]
            pg = None if case_sem is None else (None if case_sem.get(key) is None else n * case_sem[key])
            meta = dict(n=n, ask_y=ask_y)
        else:
            d = rng.randint(1, s["t"] + 5); perm = rng.random() < 0.5; nm = rng.choice(NAMES)
            if branch is not None: perm = bool(branch)
            txt = (f"{nm} books a stay of {d} days and {'holds' if perm else 'does not hold'} a {e['g']} permit. "
                   f"What is the total charge in credits?")
            gold = f3_total(s, d, perm); pg = None; meta = dict(d=d, perm=perm)
        k = norm(txt)
        blob = render_def(e) + render_message(e) + txt
        if k in seen or str(gold) in blob.replace(txt, "") or str(gold) in txt: continue
        seen.add(k)
        c = dict(entry=e["id"], fam=f, text=txt, gold=str(gold), meta=meta)
        if case_sem is not None: c["planted_gold"] = "UNKNOWN" if pg is None else str(pg)
        return c
    raise RuntimeError("could not make unique leak-free case")

def f3_total(s, d, perm):
    return s["a"] * min(d, s["t"]) + s["c"] * max(0, d - s["t"]) + (0 if perm else s["s"])

def gold_of(sem, fam, meta):
    if fam == "F1": return meta["n"] * sem["mem" if meta["mem"] else "non"]
    if fam == "F2": return meta["n"] * sem["yr" if meta["ask_y"] else "xr"]
    return f3_total(sem, meta["d"], meta["perm"])

# ------------------------------------------------------------------ book
POOLS = ["stageA_A1", "stageA_A4", "stageA_A6", "cache_fixed", "cache_stress", "qualification", "pilot",
         "canary", "manip_B1", "test"]

def build(cfg, seen_init=(), ids_init=(), forbid_texts=()):
    """A9: seen_init / ids_init pre-reserve case texts and entry ids of an earlier book (fresh-pool build);
    both default to empty, so the frozen book is reproduced unchanged."""
    rng = random.Random(cfg["seeds"]["generator"]); ids = IdAlloc(random.Random(cfg["seeds"]["generator"] + 1))
    ids.used |= set(ids_init); seen = set(seen_init); _FORBID.clear(); _FORBID.update(forbid_texts); B = dict(entries={}, groups={}, cases={p: [] for p in POOLS}, probes={}, neighbours={},
                           unknown_msgs=[], meta=dict(seeds=cfg["seeds"]))
    def add(e): B["entries"][e["id"]] = e; return e
    def group(name, fam, n): B["groups"][name] = [add(mk_entry(fam, ids, rng))["id"] for _ in range(n)]; return B["groups"][name]
    A = cfg["stageA"]; core = cfg["families_core"]; cmax = max(c["core_per_family"] for c in cfg["configs"].values())
    # --- Stage A entries
    for f in core + ["F3s"]: group(f"A1_{f}", f, A["entries_per_family_A1"])
    for f in core + ["F3s"]: group(f"A2_{f}", f, A["honest_per_family_A2"])
    for f in core + ["F3s"]: group(f"cache_{f}", f, 10)
    # --- Stage B entries (core built at C100 size; C60 = first 30 per family)
    for f in core: group(f"core_{f}", f, cmax)
    group("F3L", "F3L", cfg["f3l_entries"])
    for f in core + ["F3L"]: group(f"qual_{f}", f, cfg["qualification"]["entries_per_family"])
    for f in core + ["F3L"]: group(f"pilot_{f}", f, cfg["pilot"]["entries_per_family"])
    for f in core + ["F3L"]: group(f"probediag_{f}", f, cfg["probe_diag"]["entries_per_family"])
    group("canary_F1", "F1", 4)
    # --- planted entries
    def plant(name, types, n_total, src_groups, strong=False):
        out = []; srcs = [x for g in src_groups for x in B["groups"][g]]
        i = 0
        while len(out) < n_total:
            ty = types[len(out) % len(types)]; fam = core[(len(out) // len(types)) % len(core)]
            h = add(mk_entry(fam, ids, rng)); h["kind"] = "planted_source"
            if not planted_ok(h, ty): continue
            donor = B["entries"][rng.choice([s for s in srcs if B["entries"][s]["fam"] == fam])]
            if strong and ty == "deleted_negation" and fam == "F2" and h["sem"]["xr"] <= h["sem"]["yr"]:
                # A5: explicit-wrong F2 plant ("the y pays the x's share"): orient the calibration-only source so the
                # higher/lower probes also flip (rng-free; the source entry is used only as this plant's honest reference)
                h["sem"]["xr"], h["sem"]["yr"] = h["sem"]["yr"], h["sem"]["xr"]; h["text"] = render_def(h); h["hash"] = sha256_text(h["text"])
            p = planted_entry(h, ty, ids, rng, donor, strong=strong)
            if _FORBID and (norm(h["text"]) in _FORBID or norm(p["text"]) in _FORBID):   # A9 only (empty for the frozen book)
                B["entries"].pop(h["id"]); continue
            p = add(p); out.append(p["id"]); i += 1
        B["groups"][name] = out
    plant("A2_planted", cfg["corruptions_calib"], A["planted_A2"], ["A2_F1", "A2_F2"])
    plant("A4_planted", cfg["corruptions_calib"] + cfg["corruptions_test"], A["planted_A4"], ["A2_F1", "A2_F2"])
    plant("planted_calib", cfg["corruptions_calib"], max(c["planted_calib"] for c in cfg["configs"].values()), ["core_F1", "core_F2"], strong=True)
    plant("planted_testgate", cfg["corruptions_test"], cfg["planted_testgate"], ["core_F1", "core_F2"])
    # --- probes: calibration instances (core+planted_calib+qual+A2), fresh instances for TEST-gate
    prng = random.Random(cfg["seeds"]["generator"] + 2); frng = random.Random(cfg["seeds"]["probes_fresh"])
    def probes_for(eid, r):
        e = B["entries"][eid]; ref = B["entries"][e["honest_id"]] if e["kind"] == "planted" else e
        return make_probes(e, ref, r)
    for g in ["A2_F1", "A2_F2", "A2_F3s", "A2_planted", "core_F1", "core_F2", "planted_calib", "F3L",
              "qual_F1", "qual_F2", "qual_F3L", "probediag_F1", "probediag_F2", "probediag_F3L"]:
        for eid in B["groups"][g]: B["probes"].setdefault("calib", {})[eid] = probes_for(eid, prng)
    for g in ["core_F1", "core_F2", "planted_testgate"]:
        for eid in B["groups"][g]: B["probes"].setdefault("testgate", {})[eid] = probes_for(eid, frng)
    # --- cases
    def cases(pool, gname, n, planted=False, balance=False):
        for eid in B["groups"][gname]:
            e = B["entries"][eid]
            src = B["entries"][e["honest_id"]] if planted else e
            for i in range(n):
                c = mk_case(src, rng, seen, case_sem=e["sem"] if planted else None, branch=(i % 2 == 0) if balance else None); c["entry"] = eid
                B["cases"][pool].append(c)
    for f in core + ["F3s"]: cases("stageA_A1", f"A1_{f}", A["cases_A1"])
    cases("stageA_A4", "A4_planted", A["cases_A4"], planted=True)
    for f in core: cases("stageA_A6", f"A2_{f}", A["cases_A6"])
    for f in core + ["F3s"]: cases("cache_fixed", f"cache_{f}", 4)
    for f in core + ["F3L"]:
        cases("qualification", f"qual_{f}", cfg["qualification"]["cases_per_entry"])
        cases("pilot", f"pilot_{f}", cfg["pilot"]["cases_per_entry"])
    cases("canary", "canary_F1", 5)
    cases("manip_B1", "planted_calib", 5, planted=True)
    # A2: harder original messages for >= 1/3 of TEST entries per family group, frozen seed, styles cycled
    hrng = random.Random(cfg["seeds"]["hard_messages"])
    for g in ["core_F1", "core_F2", "F3L"]:
        # sampled separately in the C60 block (first 30 per core family) and the C100-only block, so the share
        # holds under either configuration
        ids_g = list(B["groups"][g]); cut = cfg["configs"]["C60"]["core_per_family"] if g != "F3L" else len(ids_g); i = 0
        for blk in (ids_g[:cut], ids_g[cut:]):
            for eid in sorted(hrng.sample(blk, math.ceil(cfg["hard_message_share"] * len(blk) - 1e-9))):
                B["entries"][eid]["msg_style"] = MSG_STYLES[i % 3]; i += 1
    for g in ["core_F1", "core_F2", "F3L"]: cases("test", g, cfg["test_cases_per_entry"], balance=cfg.get("test_branch_balance", False))   # A9 4b
    # --- neighbours for core + F3L (TEST) entries: built AFTER the TEST cases so that each neighbour can be
    # regenerated (same ID slot) until it is distinct and changes gold on >= threshold of that entry's TEST cases
    thr = cfg["neighbour_gold_change_min"]
    by_e = {}
    for c in B["cases"]["test"] + B["cases"]["pilot"]: by_e.setdefault(c["entry"], []).append(c)
    # GPT code r1: pilot entries get neighbours too (checked against their PILOT cases), so pilot sender timing
    # never touches TEST entries
    for gname in [f"core_{f}" for f in core] + ["F3L"] + [f"pilot_{f}" for f in core]:
        for eid in B["groups"][gname]:
            e = B["entries"][eid]; nb = []; labels = {render_label(e)}
            for k in range(cfg["n_neighbours"]):
                for attempt in range(200):
                    n = mk_entry(e["fam"], ids, rng, neighbour_params(e, k if attempt < 100 else attempt % 3, rng))
                    ch = sum(str(gold_of(n["sem"], n["fam"], c["meta"])) != c["gold"] for c in by_e[eid]) / len(by_e[eid])
                    if render_label(n) not in labels and ch >= thr and norm(n["text"]) not in _FORBID: break
                    ids.used.discard(n["id"])
                else: raise AssertionError(f"could not build load-bearing neighbour {k} for {eid}")
                n["kind"] = "neighbour"; n["of"] = eid; n["ntype"] = ["swap", "shift", "swap+shift"][k if attempt < 100 else attempt % 3]; add(n); nb.append(n["id"]); labels.add(render_label(n))
            B["neighbours"][eid] = nb
    # GPT code r1: neighbours are calibrated like any other candidate (calibration probes), so a gated pipeline
    # treats all candidates consistently; the published TEST dictionary = core + F3L entries + their neighbours
    for gname in [f"core_{f}" for f in core] + ["F3L"]:
        for eid in B["groups"][gname]:
            for nid in B["neighbours"][eid]: B["probes"]["calib"][nid] = probes_for(nid, prng)
    B["dictionary"] = sorted(x for g in [f"core_{f}" for f in core] + ["F3L"] for e in B["groups"][g] for x in [e] + B["neighbours"][e])
    # cache: 100 fixed sampled at random from cache_fixed candidates; 20 multi-step STRESS prompts (F3s, fixed rule)
    crng = random.Random(cfg["seeds"]["cache_sample"])
    cand = B["cases"]["cache_fixed"]; crng.shuffle(cand)
    B["cases"]["cache_fixed"] = cand[:cfg["cache"]["fixed_per_model"]]
    hard = []
    for eid in B["groups"]["cache_F3s"]:
        e = B["entries"][eid]
        while sum(1 for h in hard if h["entry"] == eid) < cfg["cache"]["stress_per_model"] // 10:
            c = mk_case(e, rng, seen)
            if c["meta"]["d"] > e["sem"]["t"] and not c["meta"]["perm"]: hard.append(c)
    B["cases"]["cache_stress"] = hard
    # --- sanity subset (pre-registered by seed, C60-compatible: drawn from the first 30 per family)
    srng = random.Random(cfg["seeds"]["sanity_subset"]); c60 = cfg["configs"]["C60"]["core_per_family"]
    B["groups"]["sanity"] = [x for f in core for x in srng.sample(B["groups"][f"core_{f}"][:c60], cfg["sanity_subset_per_family"])]
    # --- unknown / stale / wrong-hash messages
    urng = random.Random(cfg["seeds"]["generator"] + 3); test_ids = B["groups"]["core_F1"] + B["groups"]["core_F2"]
    used_e = set()   # A3: one message per entry so all 48 messages are distinct (a duplicate was found by the dry run)
    for i in range(cfg["unknown_id_messages"]):
        e = B["entries"][urng.choice([x for x in test_ids if x not in used_e])]; used_e.add(e["id"]); kind = ["unknown", "stale", "wronghash"][i % 3]
        if kind == "unknown": m = f"{e['fam']}-X{i:03d}@v1#{e['hash'][:8]}"
        elif kind == "stale": m = f"{e['id']}@v{e['ver']+1}#{e['hash'][:8]}"
        else: m = f"{e['id']}@v{e['ver']}#{'0' * 8 if e['hash'][:8] != '0' * 8 else '1' * 8}"
        B["unknown_msgs"].append(dict(msg=m, kind=kind, ref=e["id"]))
    verify(B, cfg)
    return B

def entries_for_config(B, cfg, name):
    n = cfg["configs"][name]["core_per_family"]
    return {f: B["groups"][f"core_{f}"][:n] for f in cfg["families_core"]}

# ------------------------------------------------------------------ assertions
def verify(B, cfg):
    E = B["entries"]
    # 1. disjoint + unique case text across ALL pools (normalised text and (entry,text))
    seen_t, seen_et = {}, set()
    for pool, cs in B["cases"].items():
        for c in cs:
            k = norm(c["text"])
            assert k not in seen_t, f"case text shared/duplicated: pool {pool} vs {seen_t.get(k)}: {c['text']}"
            seen_t[k] = pool; et = (c["entry"], k); assert et not in seen_et; seen_et.add(et)
    # 2. gold recomputed independently from the parsed entry semantics
    for pool, cs in B["cases"].items():
        for c in cs:
            e = E[c["entry"]]; src = E[e["honest_id"]] if e["kind"] == "planted" else e
            assert str(gold_of(src["sem"], src["fam"], c["meta"])) == c["gold"], f"gold mismatch {pool} {c}"
            assert parse_check_text(src, c), f"entry text does not state its own semantics: {src['id']}"
            if e["kind"] != "planted":   # GPT code r1: gold recomputed from the TEXTS alone (role-bound rates + question quantities)
                assert str(gold_from_text(src, c["text"])) == c["gold"], f"text-derived gold mismatch {pool} {c['text']}"
    # 3. entries: hash matches text, ids unique (dict), TEST entries not used elsewhere
    for e in E.values(): assert e["hash"] == sha256_text(e["text"])
    test_entries = {c["entry"] for c in B["cases"]["test"]}
    for pool, cs in B["cases"].items():
        if pool != "test": assert not (test_entries & {c["entry"] for c in cs}), f"TEST entry reused in {pool}"
    # 4. wrong neighbours change gold on >= threshold of that entry's TEST cases
    thr = cfg["neighbour_gold_change_min"]
    by_e = {}
    for c in B["cases"]["test"]: by_e.setdefault(c["entry"], []).append(c)
    for c in B["cases"]["pilot"]: by_e.setdefault(c["entry"], []).append(c)
    for eid, nbs in B["neighbours"].items():
        cs = by_e[eid]
        for nid in nbs:
            n = E[nid]; ch = sum(str(gold_of(n["sem"], n["fam"], c["meta"])) != c["gold"] for c in cs) / len(cs)
            assert ch >= thr, f"neighbour {nid} of {eid} changes gold on only {ch:.2f}"
        labels = {render_label(E[x]) for x in nbs + [eid]}; assert len(labels) == len(nbs) + 1, "duplicate candidate labels"
    # 5. each planted corruption flips >= 1 probe gold
    for pset in B["probes"].values():
        for eid, ps in pset.items():
            assert len(ps) >= cfg["probes_per_entry_min"], f"too few probes for {eid}"
            for p in ps: assert len(set(p["options"])) == 4 and p["gold"] in "ABCD"
            if E[eid]["kind"] == "planted":
                assert any(p["gold"] != p["honest_gold"] for p in ps), f"planted {eid} flips no probe"
                # GPT code r1: a perfect reader of the SHOWN text must fall below the probe bar vs honest_gold
                nf = sum(p["gold"] != p["honest_gold"] for p in ps)
                assert (len(ps) - nf) / len(ps) < cfg["gate"]["probe_bar"], f"planted {eid}: only {nf}/{len(ps)} probes flipped; a perfect reader would pass"
    # 5b. A5 (2026-10-12): explicit-wrong-rule calibration plants flip >= 0.30 of their ordinary probes; and every
    # calibration corruption type has >= 3 plants meeting that bar. TEST-gate plants are not touched by this rule.
    a5 = cfg["a5_plants"]; strong_n = {}
    for eid in B["groups"]["planted_calib"]:
        e = E[eid]; ps = B["probes"]["calib"][eid]; nf = sum(p["gold"] != p["honest_gold"] for p in ps if not p["kind"].endswith("unstated"))
        ok = nf / len(ps) >= a5["min_flip_frac"]; strong_n[e["corruption"]] = strong_n.get(e["corruption"], 0) + ok
        if (e["fam"], e["corruption"]) in {tuple(x) for x in a5["explicit_wrong"]}:
            assert ok, f"A5: explicit-wrong calibration plant {eid} flips only {nf}/{len(ps)}"
    for ty in cfg["corruptions_calib"]: assert strong_n.get(ty, 0) >= a5["min_per_type"], f"A5: <{a5['min_per_type']} strong {ty} plants"
    # 6. probe templates: >= 20 per family
    for f in ("F1", "F2", "F3s", "F3L"): assert len(templates(f)) >= cfg["probes_per_entry_min"]
    # 7. unknown messages all fail the delegate check
    from .protocol import Dictionary
    D = Dictionary(B)
    assert all(E[x]["kind"] in ("honest", "neighbour") for x in B["dictionary"]), "dictionary holds only honest entries + neighbours"
    assert len({u["msg"] for u in B["unknown_msgs"]}) == len(B["unknown_msgs"]) == cfg["unknown_id_messages"], "unknown-ID messages not distinct"
    for u in B["unknown_msgs"]: assert D.resolve(u["msg"])[0] is None, f"unknown msg resolved: {u}"
    return True

def parse_rule_text(e):
    """GPT code r1: role -> rate binding parsed from the agreed definition text (not from sem)."""
    import re
    T, f = e["text"], e["fam"]
    if f == "F1":
        mem = re.search(r"\. (\S+) members are charged (\d+) credits per", T); non = re.search(r"who are not \S+ members are charged (\d+) credits", T)
        return dict(mem=int(mem.group(2)), non=int(non.group(1)), g=mem.group(1))
    if f == "F2":
        m = re.search(r"When a (.+?) hands items to a (.+?), the (.+?) pays (\d+) credits per item and the (.+?) pays (\d+) credits per item", T)
        assert m.group(1) == m.group(3) and m.group(2) == m.group(5), "role names inconsistent in F2 text"
        return dict(x=m.group(1), y=m.group(2), xr=int(m.group(4)), yr=int(m.group(6)))
    a = re.search(r"daily charge is (\d+) credits for each of the first (\d+) days", T)
    c = re.search(r"beyond the first (\d+) days is charged (\d+) credits", T); s = re.search(r"charged the (\d+)-credit service fee", T)
    assert a.group(2) == c.group(1)
    return dict(a=int(a.group(1)), t=int(a.group(2)), c=int(c.group(2)), s=int(s.group(1)))

def parse_question(e, q):
    """GPT code r1: quantities and roles parsed from the case question text."""
    import re
    f = e["fam"]
    if f == "F1":
        m = re.match(r"(\S+) (is|is not) a .+? member and buys (\d+) ", q); return dict(n=int(m.group(3)), mem=m.group(2) == "is")
    if f == "F2":
        m = re.match(r"(\S+), acting as (.+?), hands (\d+) items to (\S+), the (.+?)\. ", q)
        if m: roles = {m.group(1): m.group(2), m.group(4): m.group(5)}; n = int(m.group(3))
        else:
            m = re.match(r"(\S+) \(the (.+?)\) receives (\d+) items from (\S+) \(the (.+?)\)\. ", q)
            roles = {m.group(1): m.group(2), m.group(4): m.group(5)}; n = int(m.group(3))
        who = re.search(r"How many credits does (\S+) pay", q).group(1)
        return dict(n=n, role=roles[who])
    m = re.match(r"\S+ books a stay of (\d+) days and (holds|does not hold) a ", q); return dict(d=int(m.group(1)), perm=m.group(2) == "holds")

def gold_from_text(e, q):
    r, k = parse_rule_text(e), parse_question(e, q)
    if e["fam"] == "F1": return k["n"] * (r["mem"] if k["mem"] else r["non"])
    if e["fam"] == "F2":
        assert k["role"] in (r["x"], r["y"]), "question role not in rule"
        return k["n"] * (r["xr"] if k["role"] == r["x"] else r["yr"])
    return f3_total(r, k["d"], k["perm"])

def parse_check_text(e, c):
    """Independent check: the constants in the entry's text are the ones in its sem (honest/neighbour only)."""
    if e["kind"] not in ("honest", "neighbour", "planted_source"): return True
    import re
    nums = [int(x) for x in re.findall(r"\b\d+\b", e["text"])]
    want = [v for k, v in e["sem"].items() if isinstance(v, int) and not isinstance(v, bool)]
    return all(w in nums for w in want)
