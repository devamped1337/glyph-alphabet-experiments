"""Build shared anchor vocabulary: words that are a single ' word' token in BOTH tokenizers,
ranked by wikitext frequency, minus function words."""
import json, re, collections, pyarrow.parquet as pq, transformers
from common import MODELS
toks = {k: transformers.AutoTokenizer.from_pretrained(v) for k, v in MODELS.items()}
text = " ".join(pq.read_table("data/wikitext-103-raw-v1/validation-00000-of-00001.parquet").column("text").to_pylist())
freq = collections.Counter(re.findall(r"\b[A-Za-z][a-z]{2,}\b", text))
STOP = set("""the and for that with was were are this from but not have has had his her its they them their there
then than which who whom whose what when where why how will would could should can may might must shall been being
into onto upon about also over under after before while during between through each other some such only very more most
all any both few many much one two own same so too just did does doing our out off you your yours she him himself herself
itself themselves ourselves these those because until against above below again further once here here's isn't wasn't aren't
""".split())
# concept words used by our tests -> force-include if single-token in both
FORCE = json.load(open("data/force_words.json")) if __import__("os").path.exists("data/force_words.json") else []
def single(tok, w):
    ids = tok.encode(" " + w, add_special_tokens=False)
    return ids[0] if len(ids) == 1 else None
anchors, ids = [], {k: [] for k in toks}
cands = list(dict.fromkeys(FORCE + [w for w, c in freq.most_common(20000) if w.lower() not in STOP]))
for w in cands:
    t = {k: single(tok, w) for k, tok in toks.items()}
    if all(v is not None for v in t.values()):
        anchors.append(w); [ids[k].append(t[k]) for k in toks]
    if len(anchors) >= 2000: break
missing = [w for w in FORCE if w not in anchors]
json.dump({"words": anchors, "ids": ids}, open("data/anchors.json", "w"))
print("anchors", len(anchors), "forced missing:", missing)
print(anchors[:40], anchors[-20:])
