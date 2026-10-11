# E1b code review guide

Code commit **`6e2636d9d9c122e0bb1700742a612c0a8febca54`** (branch `main`). Code hash `fe8cac9df70b44c6afc306eb7ea5e01691802bcdf0c05d775d202e32c9952db3` (`CODE_HASH.txt`). Spec: `PREREG_E1b.md` + Amendment A1. **Nothing has been run.** All links below are pinned to the commit.

## Please review first
**1. Cache path** (A1.4: cold/cold, warm/warm, cold/warm pairing, batch 1, zero-change rule)
- `backends.py`, where prefix and suffix are tokenized separately so cold and warm runs see identical tokens:
  - warm vs cold `generate`: [L41](https://github.com/devamped1337/glyph-alphabet-experiments/blob/6e2636d9d9c122e0bb1700742a612c0a8febca54/v6/e1b/e1b/backends.py#L41)
  - `cache_prefix`: [L65](https://github.com/devamped1337/glyph-alphabet-experiments/blob/6e2636d9d9c122e0bb1700742a612c0a8febca54/v6/e1b/e1b/backends.py#L65)
  - llama.cpp logits read: [L90](https://github.com/devamped1337/glyph-alphabet-experiments/blob/6e2636d9d9c122e0bb1700742a612c0a8febca54/v6/e1b/e1b/backends.py#L90)
  - HF KV path: [L123](https://github.com/devamped1337/glyph-alphabet-experiments/blob/6e2636d9d9c122e0bb1700742a612c0a8febca54/v6/e1b/e1b/backends.py#L123)

  Raw: https://raw.githubusercontent.com/devamped1337/glyph-alphabet-experiments/6e2636d9d9c122e0bb1700742a612c0a8febca54/v6/e1b/e1b/backends.py
- `cachediag.py` (run order, pairings, summary rule): [run_prompt L9](https://github.com/devamped1337/glyph-alphabet-experiments/blob/6e2636d9d9c122e0bb1700742a612c0a8febca54/v6/e1b/e1b/cachediag.py#L9), [summarize L26](https://github.com/devamped1337/glyph-alphabet-experiments/blob/6e2636d9d9c122e0bb1700742a612c0a8febca54/v6/e1b/e1b/cachediag.py#L26). Raw: https://raw.githubusercontent.com/devamped1337/glyph-alphabet-experiments/6e2636d9d9c122e0bb1700742a612c0a8febca54/v6/e1b/e1b/cachediag.py

**2. Case builder** (frozen seeds and assertions)
- `cases.py`:
  - `build`: [L317](https://github.com/devamped1337/glyph-alphabet-experiments/blob/6e2636d9d9c122e0bb1700742a612c0a8febca54/v6/e1b/e1b/cases.py#L317)
  - `verify` (disjoint and unique, gold, neighbours ≥80%, plant flips, unknown IDs): [L425](https://github.com/devamped1337/glyph-alphabet-experiments/blob/6e2636d9d9c122e0bb1700742a612c0a8febca54/v6/e1b/e1b/cases.py#L425)
  - planted semantics: [L104](https://github.com/devamped1337/glyph-alphabet-experiments/blob/6e2636d9d9c122e0bb1700742a612c0a8febca54/v6/e1b/e1b/cases.py#L104)
  - probes: [L254](https://github.com/devamped1337/glyph-alphabet-experiments/blob/6e2636d9d9c122e0bb1700742a612c0a8febca54/v6/e1b/e1b/cases.py#L254)

  Raw: https://raw.githubusercontent.com/devamped1337/glyph-alphabet-experiments/6e2636d9d9c122e0bb1700742a612c0a8febca54/v6/e1b/e1b/cases.py

## Then
- Protocol (hash check, byte identity, sender view, bytes): [protocol.py](https://github.com/devamped1337/glyph-alphabet-experiments/blob/6e2636d9d9c122e0bb1700742a612c0a8febca54/v6/e1b/e1b/protocol.py). Raw: https://raw.githubusercontent.com/devamped1337/glyph-alphabet-experiments/6e2636d9d9c122e0bb1700742a612c0a8febca54/v6/e1b/e1b/protocol.py
- Frozen parsing: [parsing.py](https://github.com/devamped1337/glyph-alphabet-experiments/blob/6e2636d9d9c122e0bb1700742a612c0a8febca54/v6/e1b/e1b/parsing.py). Raw: https://raw.githubusercontent.com/devamped1337/glyph-alphabet-experiments/6e2636d9d9c122e0bb1700742a612c0a8febca54/v6/e1b/e1b/parsing.py
- Stages, budgets and the GGUF fallback: [stages.py](https://github.com/devamped1337/glyph-alphabet-experiments/blob/6e2636d9d9c122e0bb1700742a612c0a8febca54/v6/e1b/e1b/stages.py). Raw: https://raw.githubusercontent.com/devamped1337/glyph-alphabet-experiments/6e2636d9d9c122e0bb1700742a612c0a8febca54/v6/e1b/e1b/stages.py
- Labels, bytes and costs: [analysis.py](https://github.com/devamped1337/glyph-alphabet-experiments/blob/6e2636d9d9c122e0bb1700742a612c0a8febca54/v6/e1b/e1b/analysis.py). Raw: https://raw.githubusercontent.com/devamped1337/glyph-alphabet-experiments/6e2636d9d9c122e0bb1700742a612c0a8febca54/v6/e1b/e1b/analysis.py
- Projection / C60–C100: [projection.py](https://github.com/devamped1337/glyph-alphabet-experiments/blob/6e2636d9d9c122e0bb1700742a612c0a8febca54/v6/e1b/e1b/projection.py). Validator: [validate.py](https://github.com/devamped1337/glyph-alphabet-experiments/blob/6e2636d9d9c122e0bb1700742a612c0a8febca54/v6/e1b/e1b/validate.py)
- Tests: [test_e1b.py](https://github.com/devamped1337/glyph-alphabet-experiments/blob/6e2636d9d9c122e0bb1700742a612c0a8febca54/v6/e1b/tests/test_e1b.py), [test_dryrun.py](https://github.com/devamped1337/glyph-alphabet-experiments/blob/6e2636d9d9c122e0bb1700742a612c0a8febca54/v6/e1b/tests/test_dryrun.py)
- **Interpretations and gaps to judge:** [README §Interpretations](https://github.com/devamped1337/glyph-alphabet-experiments/blob/6e2636d9d9c122e0bb1700742a612c0a8febca54/v6/e1b/README.md)
