"""Apply the pre-registered rules (PREREG.md) to the DEV results only and freeze test settings -> results/frozen5.json
  rule A (task gate): task|question counts on receiver R only if dev text_prose >= PROSE_GATE on R (and is not at ceiling for 'none' >= 0.9)
  rule B (depth):     li = argmax over the candidate depth indices (incl. emb) of mean dev glyph_id (pca, seed 0) accuracy,
                      pooled over both receivers, both senders and all COUNTED task|questions; ties -> shallower."""
from common5 import *
dev = {rk: load(f"dev_{rk}.json") for rk in MODELS}; counted = {}; detail = {}
for rk, d in dev.items():
    by = {}
    for r in d["rows"]:
        if "correct" in r: by.setdefault((f"{r['t']}|{r['q']}", r["cond"]), []).append(r["correct"])
    tq = sorted({k[0] for k in by})
    detail[rk] = {x: {"prose": float(np.mean(by.get((x, "text_prose"), [0]))), "none": float(np.mean(by.get((x, "none"), [0]))),
                      "n": len(by.get((x, "text_prose"), []))} for x in tq}
    counted[rk] = [x for x in tq if detail[rk][x]["prose"] >= PROSE_GATE and detail[rk][x]["none"] < 0.9]
acc = {}
for rk, d in dev.items():
    for r in d["rows"]:
        if r["cond"] == "glyph_id" and "correct" in r and f"{r['t']}|{r['q']}" in counted[rk]: acc.setdefault(r["li"], []).append(r["correct"])
sc = {li: float(np.mean(v)) for li, v in acc.items()}; li = max(sorted(sc), key=lambda k: (sc[k], -k))
save({"li": li, "layer_keys": dev[list(MODELS)[0]].get("keys"), "dev_glyph_id_by_li": sc, "counted": counted, "task_gate_detail": detail,
      "prose_gate": PROSE_GATE, "rules": "see PREREG.md", "frozen_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}, "frozen5.json")
print("frozen li", li, sc); print(json.dumps(counted, indent=1))
