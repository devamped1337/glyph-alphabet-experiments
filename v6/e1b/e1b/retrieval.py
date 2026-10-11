"""Selection baselines (PREREG_E1b §9 B3; Claude r1/r3 j): TF-IDF and BM25 over candidate labels (pure Python),
and nearest-label embedding (sentence-transformers all-MiniLM-L6-v2, optional import)."""
import math, re
from collections import Counter
def toks(s): return re.findall(r"[a-z]+|\d+", s.lower())

def tfidf_pick(message, labels):
    docs = [Counter(toks(l)) for l in labels]; N = len(docs)
    df = Counter(w for d in docs for w in d)
    idf = {w: math.log((N + 1) / (df[w] + 1)) + 1 for w in df}
    q = Counter(toks(message))
    def vec(c): return {w: c[w] * idf.get(w, 0) for w in c}
    qv = vec(q)
    def cos(a, b):
        num = sum(a[w] * b.get(w, 0) for w in a); den = math.sqrt(sum(v * v for v in a.values())) * math.sqrt(sum(v * v for v in b.values()))
        return num / den if den else 0.0
    sc = [cos(qv, vec(d)) for d in docs]; return max(range(N), key=lambda i: (sc[i], -i)), sc

def bm25_pick(message, labels, k1=1.5, b=0.75):
    docs = [toks(l) for l in labels]; N = len(docs); avg = sum(map(len, docs)) / N
    df = Counter(w for d in docs for w in set(d)); q = toks(message)
    sc = []
    for d in docs:
        c = Counter(d); s = 0.0
        for w in q:
            if w not in c: continue
            idf = math.log(1 + (N - df[w] + 0.5) / (df[w] + 0.5))
            s += idf * c[w] * (k1 + 1) / (c[w] + k1 * (1 - b + b * len(d) / avg))
        sc.append(s)
    return max(range(N), key=lambda i: (sc[i], -i)), sc

_emb = None
def embed_pick(message, labels, model_name="sentence-transformers/all-MiniLM-L6-v2"):
    global _emb
    from sentence_transformers import SentenceTransformer, util
    if _emb is None: _emb = SentenceTransformer(model_name)
    v = _emb.encode([message] + labels, convert_to_tensor=True)
    sc = util.cos_sim(v[0:1], v[1:])[0].tolist(); return max(range(len(sc)), key=lambda i: (sc[i], -i)), sc

# ------------------------------------------------------------------ A2: order-aware regex number matching
def nums(s): return [int(x) for x in re.findall(r"\d+", s)]

def _lcs(a, b):
    D = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a)):
        for j in range(len(b)): D[i + 1][j + 1] = D[i][j] + 1 if a[i] == b[j] else max(D[i][j + 1], D[i + 1][j])
    return D[-1][-1]

def regex_pick(message, labels):
    """Score each label by the longest common subsequence of the ORDERED digit-numbers in the message and in the
    label, +0.5 if one sequence is a prefix of the other. Highest score wins; ties go to the first candidate. Uses
    no model and no words, so it shows how much of selection number matching alone solves. Spelled-out numbers
    defeat it on purpose."""
    q = nums(message); sc = []
    for l in labels:
        n = nums(l); m = min(len(q), len(n))
        sc.append(_lcs(q, n) + (0.5 if m and q[:m] == n[:m] else 0))
    return max(range(len(labels)), key=lambda i: (sc[i], -i)), sc
