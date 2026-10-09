"""v3 'maths book' shared definitions."""
import numpy as np
PRE = "3+4=7\n8-5=3\n6>2=true\n1>7=false\n"     # fixed format preamble, identical in EVERY condition (states no test equation)
SCAFFOLD = PRE + "? ? ? ?"                       # 4 placeholder tokens = left, op, right, eq slots; result slot = next token
LAYERS = {"qwen": [8, 14], "smol": [11, 19]}     # ~1/3 and ~0.58 depth, inside both lenses' fitted range
OPS = {"add": "+", "sub": "-", "gt": ">"}
def answer(a, op, b):
    return a + b if op == "add" else a - b if op == "sub" else ("true" if a > b else "false")
def equations():
    E = []
    for op in OPS:
        for a in range(10):
            for b in range(10):
                r = answer(a, op, b)
                if op != "gt" and not 0 <= r <= 9: continue
                if (a, OPS[op], b) in [(3, "+", 4), (8, "-", 5), (6, ">", 2), (1, ">", 7)]: continue   # preamble items excluded
                E.append({"a": a, "op": op, "b": b, "r": r, "text": f"{a}{OPS[op]}{b}="})
    rng = np.random.default_rng(0); split = {}
    for op in OPS:
        idx = [i for i, e in enumerate(E) if e["op"] == op]; rng.shuffle(idx)
        for n, i in enumerate(idx): E[i]["split"] = "train" if n < len(idx) // 2 else "test"
    return E
