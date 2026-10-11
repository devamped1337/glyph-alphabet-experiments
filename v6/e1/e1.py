#!/usr/bin/env python3
"""v6 E1: text repository test (PREREG_v6.md §2, §4, §5, §6, §7).

Stages:  build | calib <model> | freeze_gate | test <model> | analyze | smoke <model>
Sender emits an entry ID text ("F1-03@v1"); the receiver's delegate expands it from the
versioned dictionary into the agreed definition; the receiver model answers.
"""
import json, os, random, re, sys, time, hashlib, math
from pathlib import Path

HERE = Path(__file__).resolve().parent
CFG = json.load(open(HERE / "config_e1.json"))
DATA = HERE / "data"; RES = HERE / "results"; DATA.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)

# ----------------------------------------------------------------- entries
NOUNS = ["Harbor", "Cedar", "Quartz", "Lantern", "Falcon", "Meadow", "Copper", "Juniper",
         "Basalt", "Willow", "Orchid", "Granite", "Saffron", "Tundra", "Pebble", "Cobalt",
         "Marigold", "Summit", "Thistle", "Ember", "Glacier", "Hazel", "Indigo", "Kestrel"]
ROLES = [("supplier", "buyer"), ("lender", "borrower"), ("host", "guest"), ("sender", "courier"),
         ("landlord", "tenant"), ("coach", "trainee"), ("seller", "agent"), ("donor", "clinic")]
NAMES = ["Ana", "Bo", "Cy", "Dee", "Eli", "Fay", "Gus", "Ivy", "Jo", "Kai", "Lu", "Max", "Ned", "Ola", "Pia", "Rex"]
UNITS = ["crate", "kilogram", "hour", "ticket", "parcel", "litre", "seat", "page"]
F3_FILLER = ("This schedule applies to every booking recorded in the shared ledger, whether it was made "
             "in person, by phone or through the portal. Staff must record the booking date, the start date "
             "and the name of the person responsible before any charge is calculated. Charges are always "
             "expressed in whole credits, and no rounding is applied at any step. Bookings that were cancelled "
             "before the start date are handled under a separate schedule and are out of scope here. Where this "
             "schedule and an older notice disagree, this schedule takes precedence. Questions about a charge should be "
             "raised with the ledger office within thirty days of the end of the stay. ")

def mk_entry(fam, k, rng, eid=None):
    e = {"fam": fam, "k": k, "id": eid or f"{fam}-{k:02d}", "ver": 1}
    if fam == "F1":   # negation family
        e.update(g=NOUNS[rng.randrange(24)], unit=UNITS[rng.randrange(8)], a=rng.randint(2, 9))
        e["b"] = rng.choice([x for x in range(2, 10) if x != e["a"]])
    elif fam == "F2":  # roles / paraphrase family
        x, y = ROLES[rng.randrange(8)]
        e.update(x=x, y=y, a=rng.randint(2, 9)); e["b"] = rng.choice([v for v in range(2, 10) if v != e["a"]])
    else:              # F3 long definitions (200+ tokens)
        e.update(g=NOUNS[rng.randrange(24)], a=rng.randint(3, 9), t=rng.randint(3, 6), s=rng.randint(10, 19))
        e["c"] = rng.choice([v for v in range(2, 12) if v != e["a"]])
    return e

def render(e, style="def", corr=None):
    """Text of an entry. style: def (agreed definition) | prose | compact. corr: corruption type."""
    e = dict(e); f = e["fam"]
    if corr == "changed_constant": e["a"] = e["a"] + 3
    if corr == "swapped_roles" and f == "F2": e["x"], e["y"] = e["y"], e["x"]
    if f == "F1":
        pos = f"{e['g']} members are charged {e['a']} credits per {e['unit']}."
        neg = f"Customers who are not {e['g']} members are charged {e['b']} credits per {e['unit']}."
        if corr == "deleted_negation": neg = neg.replace(" not ", " ")
        if corr == "near_miss_polarity": pos = f"{e['g']} members are not charged {e['a']} credits per {e['unit']}."
        if corr == "swapped_roles": pos, neg = (f"{e['g']} members are charged {e['b']} credits per {e['unit']}.",
                                                f"Customers who are not {e['g']} members are charged {e['a']} credits per {e['unit']}.")
        if corr == "dropped_clause": neg = ""
        if style == "prose":
            return (f"Belonging to the {e['g']} scheme gets a customer a rate of {e['a']} credits for each {e['unit']}; "
                    f"anybody lacking {e['g']} membership pays {e['b']} credits for each {e['unit']} instead.")
        if style == "compact": return f"{e['g']}:{e['a']}/{e['unit']}; non-{e['g']}:{e['b']}/{e['unit']}"
        return f"Pricing rule. {pos} {neg}".strip()
    if f == "F2":
        s1 = f"When a {e['x']} hands items to a {e['y']}, the {e['x']} pays {e['a']} credits per item"
        s2 = f" and the {e['y']} pays {e['b']} credits per item."
        s3 = f" The {e['y']} does not pay the {e['x']}'s share."
        if corr == "deleted_negation": s3 = s3.replace(" does not pay ", " pays ")
        if corr == "near_miss_polarity": s2 = f" and the {e['y']} does not pay {e['b']} credits per item."
        if corr == "dropped_clause": s2 = "."
        if style == "prose":
            return (f"In a hand-over, whoever gives the items (the {e['x']}) is billed {e['a']} credits for each item, "
                    f"while whoever takes them (the {e['y']}) is billed {e['b']} credits for each item; neither covers the other's bill.")
        if style == "compact": return f"handover {e['x']}->{e['y']}: {e['x']} {e['a']}/item, {e['y']} {e['b']}/item"
        return "Hand-over rule. " + s1 + s2 + s3
    # F3
    r1 = f"The daily charge is {e['a']} credits for each of the first {e['t']} days."
    r2 = f" Every day beyond the first {e['t']} days is charged {e['c']} credits instead."
    r3 = f" Holders of a {e['g']} permit are not charged the {e['s']}-credit service fee; everyone else pays it once per booking."
    if corr == "deleted_negation": r3 = r3.replace(" are not charged ", " are charged ")
    if corr == "near_miss_polarity": r3 = f" Holders of a {e['g']} permit are charged the {e['s']}-credit service fee; everyone else does not pay it."
    if corr == "inverted_comparison": r2 = f" Every day within the first {e['t']} days is charged {e['c']} credits instead."
    if corr == "dropped_clause": r2 = ""
    if style == "prose":
        return (f"A stay costs {e['a']} credits a day up to day {e['t']}; from day {e['t']+1} onward each day costs {e['c']} credits. "
                f"There is also a one-off {e['s']}-credit service fee, waived for anyone holding a {e['g']} permit.")
    if style == "compact":
        return f"day<= {e['t']}:{e['a']}; day>{e['t']}:{e['c']}; fee {e['s']} once, waived if {e['g']} permit"
    return "Booking charge schedule. " + F3_FILLER + r1 + r2 + r3 + " " + F3_FILLER.split(". ")[1] + "."

def placebo(e, case):
    """Prose with the answer-determining token(s) removed (the constants this case's answer uses)."""
    p = render(e, "prose")
    for key in case["uses"]:
        p = re.sub(rf"\b{e[key]}\b", "___", p, count=1)
    return p

def mk_case(e, rng, honest=None):
    """Case text + gold computed from the HONEST entry (honest=e unless a planted copy)."""
    h = honest or e; f = h["fam"]
    for _ in range(200):
        if f == "F1":
            mem = rng.random() < 0.5; n = rng.randint(2, 12)
            nm = rng.choice(NAMES)
            txt = (f"{nm} {'is' if mem else 'is not'} a {h['g']} member and buys {n} {h['unit']}s. "
                   f"How many credits is {nm} charged in total?")
            gold = n * (h["a"] if mem else h["b"]); uses = ["a"] if mem else ["b"]
        elif f == "F2":
            n = rng.randint(2, 12); n1, n2 = rng.sample(NAMES, 2); ask_y = rng.random() < 0.5
            txt = rng.choice([f"{n1}, acting as {h['x']}, hands {n} items to {n2}, the {h['y']}. ",
                              f"{n2} (the {h['y']}) receives {n} items from {n1} (the {h['x']}). "])
            who = n2 if ask_y else n1
            txt += f"How many credits does {who} pay in total?"
            gold = n * (h["b"] if ask_y else h["a"]); uses = ["b"] if ask_y else ["a"]
        else:
            d = rng.randint(1, h["t"] + 5); perm = rng.random() < 0.5; nm = rng.choice(NAMES)
            txt = (f"{nm} books a stay of {d} days and {'holds' if perm else 'does not hold'} a {h['g']} permit. "
                   f"What is the total charge in credits?")
            gold = h["a"] * min(d, h["t"]) + h["c"] * max(0, d - h["t"]) + (0 if perm else h["s"])
            uses = ["a"] + (["c"] if d > h["t"] else []) + ([] if perm else ["s"])
        c = {"text": txt, "gold": str(gold), "uses": uses}
        # no gold string anywhere in any condition's prompt material (§2)
        blob = txt + render(h, "prose") + render(h, "def") + render(e, "def") + render(h, "compact")
        if c["gold"] not in blob: return c
    raise RuntimeError("could not make leak-free case")

def build():
    rng = random.Random(CFG["seed"])
    honest = [mk_entry(f, k, rng) for f in ("F1", "F2", "F3") for k in range(CFG["entries_per_family"])]
    def planted(types, tag):
        out = []
        for i, ty in enumerate(types):
            fams = ["F1", "F2"] if ty == "swapped_roles" else (["F3"] if ty == "inverted_comparison" else ["F1", "F2", "F3"])
            fam = fams[i % len(fams)]
            base = mk_entry(fam, 90 + i, rng, eid=f"{fam}-{tag}{i:02d}")
            corr = "swapped_roles" if ty.startswith("swapped_roles") else ty
            p = dict(base, corr=corr)
            if corr == "mismatched_definition":
                other = mk_entry(fam, 99, rng); p["shown"] = render(other, "def")
            else:
                p["shown"] = render(base, "def", corr)
            out.append(p)
        return out
    cal_p = planted([t for t in CFG["calib_corruptions"] for _ in range(CFG["planted_per_type_calib"])], "C")
    test_p = planted([t for t in CFG["test_corruptions"] for _ in range(CFG["planted_per_type_test"])], "T")
    for e in honest: e["shown"] = render(e, "def")
    def cases(ents, n, tag):
        return {e["id"]: [mk_case(e, random.Random(f"{CFG['seed']}-{tag}-{e['id']}-{j}")) for j in range(n)] for e in ents}
    book = {"version": CFG["book_version"], "entries": {f"{e['id']}@v{e['ver']}": e for e in honest + cal_p + test_p}}
    json.dump(book, open(DATA / "book.json", "w"), indent=1)
    json.dump({"honest": [e["id"] for e in honest], "calib_planted": [e["id"] for e in cal_p],
               "test_planted": [e["id"] for e in test_p],
               "calib_cases": cases(honest + cal_p, CFG["N_calib"], "cal"),
               "test_gate_cases": cases(honest + test_p, CFG["N_test_gate"], "tgate"),
               "main_cases": cases(honest, CFG["N_main_per_entry"], "main")}, open(DATA / "cases.json", "w"), indent=1)
    lens = [len(render(e, "def").split()) for e in honest if e["fam"] == "F3"]
    print(f"built {len(honest)} honest, {len(cal_p)} calib-planted, {len(test_p)} test-planted; F3 def words {min(lens)}-{max(lens)}")

# ----------------------------------------------------------------- receiver
SYS = ("You apply shared dictionary entries to cases. Work it out in at most three short lines, then finish "
       "with a final line of the form 'Answer: <integer>'. If the information given does not determine the "
       "answer, finish with 'Answer: UNKNOWN'.")
_llm = {}
def llm(model):
    if model not in _llm:
        from llama_cpp import Llama
        _llm.clear()
        _llm[model] = Llama(model_path=CFG["models"][model]["path"], n_ctx=2048, n_threads=CFG["n_threads"],
                            n_batch=512, seed=0, verbose=False)
    return _llm[model]

def delegate_expand(msg, book):
    """Receiver-side delegate: deterministic parser ID -> agreed definition. Returns (coverage, selection, text)."""
    m = re.fullmatch(r"\s*([A-Z0-9]+-[A-Z]?\d+)@v(\d+)\s*", msg)
    if not m: return False, None, None
    key = f"{m.group(1)}@v{m.group(2)}"
    if key not in book["entries"]: return False, None, None
    return True, key, book["entries"][key]["shown"]

def ask(model, context, question, cold):
    L = llm(model)
    if cold: L.reset()
    msgs = [{"role": "system", "content": SYS}, {"role": "user", "content": f"{context}\n\nCase: {question}\nAnswer:"}]
    t0 = time.perf_counter()
    out = L.create_chat_completion(msgs, max_tokens=CFG["max_new_tokens"], temperature=0.0, top_k=1, seed=0)
    dt = time.perf_counter() - t0
    txt = out["choices"][0]["message"]["content"].strip()
    am = re.findall(r"answer\s*[:=]\s*\**\s*(-?\d[\d,]*|unknown)", txt, re.I)
    if am:
        a = am[-1].replace(",", "")
        pred, abst = ("UNKNOWN", True) if a.lower() == "unknown" else (a, False)
    else:   # fallback: last integer in the reply; else UNKNOWN keyword; else invalid
        ints = re.findall(r"-?\d+", txt.replace(",", ""))
        if ints: pred, abst = ints[-1], False
        elif "UNKNOWN" in txt.upper(): pred, abst = "UNKNOWN", True
        else: pred, abst = None, False   # invalid (logged, counted wrong)
    return dict(raw=txt, parse_path="answer_line" if am else ("fallback" if pred else "invalid"), pred=pred, abstained=abst, prompt_tokens=out["usage"]["prompt_tokens"],
                gen_tokens=out["usage"]["completion_tokens"], latency_s=round(dt, 4))

def sender(eid):
    t0 = time.perf_counter(); msg = f"{eid}@v1"; return msg, time.perf_counter() - t0

def row(model, stage, cond, e, ci, case, context, cold, cov, sel, extra=None):
    r = ask(model, context, case["text"], cold)
    out = dict(model=model, stage=stage, cond=cond, task=e["fam"], entry=e["id"], message_group=e["id"],
               semantic_item=f"{e['id']}#{ci}", planted=bool(e.get("corr")), corruption=e.get("corr"),
               coverage=cov, selection=sel, decoding=CFG["decoding"],
               gold=case["gold"], prompt=f"{context}\n\nCase: {case['text']}", cold_cache=cold,
               model_called=True, **r)
    out["correct"] = (out["pred"] == out["gold"]); out.update(extra or {})
    return out

def run_gate(model, stage, ids, casekey, fh, limit=None):
    book = json.load(open(DATA / "book.json")); C = json.load(open(DATA / "cases.json"))[casekey]
    for eid in ids:
        e = book["entries"][f"{eid}@v1"]
        msg, st = sender(eid); cov, sel, txt = delegate_expand(msg, book)
        for ci, case in enumerate(C[eid][:limit]):
            fh.write(json.dumps(row(model, stage, "gate_id_expanded", e, ci, case, f"Dictionary entry {sel}:\n{txt}",
                                    False, cov, sel, {"message": msg, "sender_s": st})) + "\n"); fh.flush()

def run_main(model, fh, limit_entries=None, limit_cases=None):
    book = json.load(open(DATA / "book.json")); D = json.load(open(DATA / "cases.json"))
    for eid in D["honest"][:limit_entries]:
        e = book["entries"][f"{eid}@v1"]; msg, st = sender(eid); cov, sel, txt = delegate_expand(msg, book)
        for ci, case in enumerate(D["main_cases"][eid][:limit_cases]):
            ex = {"message": msg, "sender_s": st}
            conds = [("id_expanded", f"Dictionary entry {sel}:\n{txt}", True, cov, sel),
                     ("id_expanded_cached", f"Dictionary entry {sel}:\n{txt}", False, cov, sel),
                     ("prose", f"Note from the sender:\n{render(e, 'prose')}", True, True, None),
                     ("placebo_prose", f"Note from the sender:\n{placebo(e, case)}", True, True, None),
                     ("compact", f"Note from the sender:\n{render(e, 'compact')}", True, True, None),
                     ("id_raw", f"Message from the sender: {msg}", True, True, None)]
            for cond, ctx, cold, cv, sl in conds:
                fh.write(json.dumps(row(model, "test_main", cond, e, ci, case, ctx, cold, cv, sl, ex)) + "\n"); fh.flush()
    # unknown-ID: (a) deterministic parser test, (b) model-abstention test
    rng = random.Random(7)
    for j, eid in enumerate(D["honest"][:limit_entries]):
        e = book["entries"][f"{eid}@v1"]; case = D["main_cases"][eid][0]
        for bad in (f"{eid}@v9", f"{e['fam']}-77@v1"):
            cov, sel, txt = delegate_expand(bad, book)
            assert cov is False
            fh.write(json.dumps(dict(model=model, stage="test_unknown", cond="unknown_id_parser_test", task=e["fam"],
                     entry=bad, message_group=bad, semantic_item=f"{bad}#0", coverage=False, selection=None,
                     decoding="deterministic_parser", gold="UNKNOWN", pred="UNKNOWN", correct=True,
                     fixed_pred="UNKNOWN", model_called=False, label="deterministic parser test")) + "\n")
            r = row(model, "test_unknown", "unknown_id_model_abstention", e, 0, dict(case, gold="UNKNOWN"),
                    f"Dictionary entry {bad}: [no entry with this ID exists in your dictionary]", True, False, None,
                    {"message": bad})
            r["entry"] = bad; fh.write(json.dumps(r) + "\n"); fh.flush()

def main():
    st = sys.argv[1]
    if st == "build": return build()
    if st == "freeze_gate": return freeze_gate()
    if st == "analyze":
        import analyze_e1; return analyze_e1.main()
    model = sys.argv[2]; D = json.load(open(DATA / "cases.json"))
    t0 = time.time()
    if st == "smoke":
        with open(RES / f"smoke_{model}.jsonl", "w") as fh:
            run_gate(model, "smoke", D["honest"][::4] + D["calib_planted"][:2], "calib_cases", fh, limit=2)
            run_main(model, fh, limit_entries=2, limit_cases=1)
    elif st == "calib":
        with open(RES / f"predictions_calib_{model}.jsonl", "w") as fh:
            run_gate(model, "calib", D["honest"] + D["calib_planted"], "calib_cases", fh)
    elif st == "test":
        assert (RES / "gate_frozen.json").exists(), "freeze gate first"
        with open(RES / f"predictions_testgate_{model}.jsonl", "w") as fh:
            run_gate(model, "test_gate", D["honest"] + D["test_planted"], "test_gate_cases", fh)
        with open(RES / f"predictions_main_{model}.jsonl", "w") as fh:
            run_main(model, fh)
    print(f"{st} {model} done in {time.time()-t0:.0f}s", flush=True)

def gate_scores(rows_by_model, ids):
    from collections import defaultdict
    ms = sorted(rows_by_model); sc = {}
    for eid in ids:
        per = {m: {r["semantic_item"]: r for r in rows_by_model[m] if r["entry"] == eid} for m in ms}
        items = sorted(set.intersection(*[set(p) for p in per.values()]))
        if not items: continue
        acc = {m: sum(per[m][i]["correct"] for i in items) / len(items) for m in ms}
        agr = sum(len({per[m][i]["pred"] for m in ms}) == 1 for i in items) / len(items)
        sc[eid] = dict(acc=acc, agree=agr, n=len(items), score=min(min(acc.values()), agr))
    return sc

def load(p): return [json.loads(l) for l in open(p) if l.strip()]

def freeze_gate():
    D = json.load(open(DATA / "cases.json"))
    rb = {m: load(RES / f"predictions_calib_{m}.jsonl") for m in CFG["gate_models"]}
    sc = gate_scores(rb, D["honest"] + D["calib_planted"])
    hon = [sc[i]["score"] for i in D["honest"] if i in sc]; pl = [sc[i]["score"] for i in D["calib_planted"] if i in sc]
    # Threshold rule (frozen in config before calibration): prereg value 0.90 unless it fails to separate;
    # the calibrated threshold is the grid value maximising (honest acceptance + planted rejection), ties -> closest to 0.90.
    grid = [round(0.5 + 0.01 * k, 2) for k in range(50)]
    best = max(grid, key=lambda t: (sum(h >= t for h in hon) / len(hon) + sum(p < t for p in pl) / len(pl), -abs(t - 0.90)))
    ja = lambda t: (sum(h >= t for h in hon) / len(hon), sum(p < t for p in pl) / len(pl))
    sep = ja(0.90)[0] > 0 and ja(0.90)[1] > 0 and (ja(0.90)[0] + ja(0.90)[1]) > 1.0
    out = dict(threshold=0.90, calibrated_best=best, calib_honest_accept_at_090=ja(0.90)[0],
               calib_planted_reject_at_090=ja(0.90)[1], separates=sep, gate_frozen=sep, scores=sc,
               rule="entry passes iff each gate model acc>=0.90 vs gold AND inter-model agreement>=0.90")
    json.dump(out, open(RES / "gate_frozen.json", "w"), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "scores"}, indent=1))

if __name__ == "__main__":
    main()
