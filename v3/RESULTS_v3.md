# Glyph experiment v3: the "maths book" (closed alphabet, slot glyphs, completion)

**Run:** 10 Oct 2026, Sydney time.
- Same CPU box, same models: A = Qwen2.5-0.5B, B = SmolLM2-360M.
- Same fitted J-lenses and .venv as v1/v2. Nothing was refitted.
- Compute: about 25 min in total. Extraction took 60 s per model. Negotiation took 3 s. The four injection runs took 2–5 min each.

Every number below is in `results/v3/*.json`. The spec was followed except where this file says otherwise.

## Setup
**Shared preamble.** Every condition, text or glyph, starts with the same format preamble:
`3+4=7\n8-5=3\n6>2=true\n1>7=false\n`
- It fixes the answer format: a digit after `=`, or `true`/`false` for `>`.
- It never states the test equation. The 4 preamble equations are excluded from the item pool.

**Items.** Single-digit operands.
- add with result 0–9: 54 items.
- sub with result 0–9: 54 items.
- gt (true/false): 98 items.
- These are split 50/50 per operator. The **train half** is used to build the book and fit the adapters. The **test half** is used for all injection numbers: add n=27, sub n=27, gt n=49.

**Scoring.**
- Digits: argmax over the 10 digit tokens. Chance is 0.10.
- gt: argmax over `true` vs `false`. Chance is 0.50. The no-injection receiver always answers the same label, so it scores 0.408, which is the share of test items with that label.

**Text-equation accuracy, reported first as the spec asks.**
| model | add | sub | gt |
|---|---|---|---|
| Qwen | 1.000 | 1.000 | 0.673 |
| Smol | 1.000 | 0.926 | 0.490 |

- Both models complete add and sub almost perfectly from text.
- **Greater-than is weak even as text.** Qwen manages 0.67. Smol is **at chance (0.49)**. So the gt test cannot show anything for Smol as receiver, and only a little for Qwen.
- In the full 0–9 pool, measured before the split: Qwen add/sub 1.00, gt 0.69; Smol add 0.98, sub 0.95, gt 0.58.

## The book (closed alphabet), negotiated as in v2 (`v3/book_v3.py`, `v3/book_v3.json`)
**Slots.** Four positional slots: **left** digit, **op**, **right** digit, **eq** (`=`). The result slot is the next token, left empty.
- Each slot has its own entries, so slot identity is carried by **position**.
- Entries: left 0–9, op {add, sub, gt}, right 0–9, eq {=}. That is 24 entries, covering 14 symbols.
- An entry is the mean layer-L state at that slot over the train equations that have that symbol there. It is averaged over all partners, so a snapped entry carries no item-specific result.

**Layers.** I used two receiver layers per model, both inside the fitted lens range:
- Qwen L8 and L14.
- Smol L11 and L19.

The v1/v2 late band (Qwen L18 / Smol L24) leaves too little computation after injection for an equation to be completed.

**Adapters.**
1. Centre on the train mean.
2. PCA to 64 dimensions, half-whitened.
3. Generalised Procrustes into a **32-dimensional** canonical space.

The fit uses paired train states: the same text and the same position in both models. The digits and `+ - > =` are single tokens in both tokenizers, so positions align exactly.

**Acceptance checks.**
- Round trip A→B→A and B→A→B, using nearest native entry within the slot.
- Keeper round trip: the shared canonical entry must be nearest to its own entry in both models' canonical sets.
- Decodes: a slot-specific ridge probe, trained on each model's raw train states, must classify the decoded shared entry correctly in both models. The probes score 1.000 on held-out test states for every slot and layer.
- Operators only:
  - The A/B cosine of the op-entry offset must be at least 0.5.
  - The A/B cosine of the op's effect on the `=` state (the place where completion happens) must be at least 0.5.
  - The decoded `+`/`−` glyph must be closer to the native symbol entry than to the receiver's own state at the word `plus`/`minus`.

**Result: all 24 entries pass in round 1 at both layers, so the alphabet is stable after 1 round.**

| op (layer pair) | A/B cos of entry | A/B op-offset cos | A/B cos of op's effect on '=' state | closer to symbol than word (Qwen, Smol) |
|---|---|---|---|---|
| add (Q8/S11) | 0.998 | 0.997 | 0.990 | yes, yes |
| sub (Q8/S11) | 0.998 | 0.997 | 0.987 | yes, yes |
| gt (Q8/S11) | 0.999 | 0.999 | 0.996 | n/a |
| add (Q14/S19) | 0.997 | 0.997 | 0.993 | yes, yes |
| sub (Q14/S19) | 0.999 | 0.997 | 0.994 | yes, yes |
| gt (Q14/S19) | 0.998 | 0.998 | 0.998 | n/a |

**Caveat on the book.** These checks were far too easy to be selective.
- The alphabet is tiny and the states are tightly clustered. Entries are computed on the same train states the adapters were fitted on.
- The `=` slot has a single entry, so it passes trivially.
- I did not put "equal" in the op slot. `=` is the eq-slot glyph.

## Injection protocol (`v3/inject_v3.py`)
**Receiver.** The receiver reads `PRE + "? ? ? ?"`. Its layer-L residual at the four `?` positions is **replaced** by `mu + decoded glyph` for left, op, right and eq. Its next token is then scored.

**Sender.** The sender reads `PRE + "7+2="`. Its states at the 7, + and 2 positions are encoded into canonical space.
- **glyph_snap:** each slot is snapped to the nearest book entry in that slot, and the shared entry is sent. This is the structured glyph.
- **glyph_raw:** the sender's own canonical vectors are sent unsnapped.
- In both cases eq is always the book `=` entry. The sender's own `=` state is never sent, because that is where the answer is computed.

**Snapping was 100% correct in every pairing.** So glyph_snap is identical for self and cross into the same receiver. Only glyph_raw depends on the sender.

**Conditions.**
- **Opponents:**
  1. text equation `7+2=`;
  2. scrambled bag, the same three symbols in a scrambled order before `=` (e.g. `2+7=` → `+72=`);
  3. op-shuffled glyph: add↔sub, and gt→add.
- **Controls:**
  - no injection;
  - same-norm shuffled glyph: canonical coordinates permuted per slot, 2 seeds;
  - native book oracle: the receiver's own entries with no adapter, used as an upper bound;
  - text with the word operator, `7 plus 2=`.

## Main accuracy table (test split; n = 27 add / 27 sub / 49 gt, and same-norm shuffled has 2 seeds so n doubles)
Pairing is sender→receiver. Text rows depend only on the receiver.

### Receiver Qwen, layer 8 (the best configuration)
| condition | A→A add | A→A sub | A→A gt | B→A add | B→A sub | B→A gt |
|---|---|---|---|---|---|---|
| no injection | 0.000 | 0.222 | 0.408 | 0.000 | 0.222 | 0.408 |
| **text `7+2=`** | **1.000** | **1.000** | **0.673** | same | same | same |
| text, scrambled bag | 0.370 | 0.296 | 0.408 | same | same | same |
| text, word op (`7 plus 2=`) | 1.000 | 1.000 | – | same | same | – |
| **glyph (snapped)** | **1.000** | **0.963** | 0.449 | **1.000** | **0.963** | 0.449 |
| glyph raw (unsnapped) | 1.000 | 1.000 | 0.592 | 1.000 | 1.000 | 0.469 |
| native book oracle | 1.000 | 0.889 | 0.592 | same | same | same |
| glyph, op shuffled: still gives original answer | 0.333 | 0.259 | 0.490 | 0.333 | 0.259 | 0.490 |
| glyph, op shuffled: **follows the swapped op** | 0.933 (n15) | 1.000 (n14) | 1.000 (n24, gives a+b) | same | same | same |
| same-norm shuffled glyph | 0.056 | 0.167 | 0.449 | 0.056 | 0.167 | 0.449 |

### Receiver Smol, layer 11
| condition | B→B add | B→B sub | B→B gt | A→B add | A→B sub | A→B gt |
|---|---|---|---|---|---|---|
| no injection | 0.000 | 0.222 | 0.408 | 0.000 | 0.222 | 0.408 |
| **text `7+2=`** | **1.000** | **0.926** | 0.490 (chance) | same | same | same |
| text, scrambled bag | 0.333 | 0.222 | 0.388 | same | same | same |
| text, word op | 1.000 | 0.963 | – | same | same | – |
| **glyph (snapped)** | 0.815 | 0.593 | 0.408 | 0.815 | 0.593 | 0.408 |
| glyph raw | 1.000 | 0.926 | 0.510 | **0.074** | **0.222** | 0.408 |
| native book oracle | 1.000 | 0.741 | 0.449 | same | same | same |
| glyph, op shuffled: original answer | 0.185 | 0.222 | 0.408 | same | same | same |
| glyph, op shuffled: follows swapped op | 0.733 (n15) | 0.929 (n14) | 0.917 (n24) | same | same | same |
| same-norm shuffled glyph | 0.056 | 0.167 | 0.418 | same | same | same |

### Later layers (Qwen L14, Smol L19): the slot glyph mostly stops working
| condition | Qwen L14 add | sub | gt | Smol L19 add | sub | gt |
|---|---|---|---|---|---|---|
| glyph (snapped) | 1.000 | 0.407 | 0.367 | 0.185 | 0.185 | 0.408 |
| native book oracle | 1.000 | 0.407 | 0.408 | 0.444 | 0.370 | 0.449 |
| op shuffled, follows swapped op | 0.400 | 1.000 | 1.000 | 0.067 | 0.286 | 0.292 |
| glyph raw, self / cross | 1.000 / 0.852 | 0.370 / 0.630 | 0.388 / 0.408 | 0.667 / 0.037 | 0.481 / 0.185 | 0.469 / 0.408 |

At Qwen L14, "add" is 1.000 for almost anything, including a blank op slot (0.963). So add there is the receiver's **default** operation, not carried by the glyph.

## The `plus`-word rejection test (op slot only; other slots get the snapped glyph)
| op-slot content | Qwen L8 add | Qwen L8 sub | Smol L11 add | Smol L11 sub |
|---|---|---|---|---|
| op glyph (book) | 1.000 | 0.963 | 0.815 | 0.593 |
| blank (mu, no op) | **0.926** | 0.370 | 0.074 | 0.259 |
| word-token **embedding** ` plus` / ` minus` (scaled to glyph norm) | 0.704 | **0.963** | 0.185 | 0.185 |
| symbol-token embedding `+` / `-` | 0.185 | 0.259 | 0.000 | 0.259 |
| receiver's own layer-L state at the word ` plus` / ` minus` | 0.963 | 0.926 | 1.000 | 0.630 |

Reading this honestly:
- **Smol: the op glyphs pass the spec's test.** Injecting the word embedding of `plus`/`minus` does not reproduce their effect (0.19 vs 0.82 and 0.59).
- **Qwen L8 `sub` fails the spec's literal test.** The ` minus` word-embedding reproduces the glyph exactly (0.963 vs 0.963).
- **Qwen L8 `add` is uninformative.** Qwen adds by default even with a blank op slot (0.926). The real evidence that the add glyph carries a relation is the op-shuffle: sending the sub glyph instead makes Qwen subtract 100% of the time.
- **In both models, the receiver's own mid-layer state at the word `plus`/`minus` works as well as the symbol glyph.** At this depth the operator is represented abstractly. Word and symbol converge on the same relation, which is evidence of carrying the relation rather than a word, but it also means the glyph is not "symbol-only".
- **Raw embeddings at a mid layer are a weak test.** They are off-distribution there, which is why even the `+` embedding fails.
- **Under the book rule** (glyph closer to the symbol state than to the word state), all op glyphs passed.
- **Under the reviewer's causal rule,** Qwen `sub` would be rejected, and Qwen `add` is untestable because add is the default.

## Result-leak check
**1. Is the result token present in the sent glyph?** I measured the J-lens readout rank of the correct result token among the candidates. For every slot (left, op, right, eq), every pairing and every layer, the mean rank is at chance:
- digits: 4.4–6.7, against a chance of 5.5;
- true/false: 1.41–1.69, against a chance of 1.5.

The same holds for the raw, unsnapped sender vectors. This is expected for snapped glyphs, because each entry is averaged over all partners.

**2. Ablation.** I projected the receiver-lens direction of the result token out of every slot (for gt, both true and false).
| | Qwen L8 add | sub | gt | Smol L11 add | sub | gt |
|---|---|---|---|---|---|---|
| glyph snapped | 1.000 | 0.963 | 0.449 | 0.815 | 0.593 | 0.408 |
| glyph snapped, result directions ablated | 1.000 | 0.926 | 0.449 | 0.815 | 0.593 | 0.429 |
| glyph raw | 1.000 | 1.000 | 0.592 | 1.000 | 0.926 | 0.510 |
| glyph raw, result ablated | 1.000 | 1.000 | 0.531 | 1.000 | 0.926 | 0.510 |

**3. Items where the result digit is literally one of the operands** (for example 7−0=7 or 8−4=4; add/sub only).
| | result is an operand (n=15) | result not an operand (n=39) |
|---|---|---|
| Qwen L8 glyph snapped | 1.000 | 0.974 |
| Smol L11 glyph snapped | 0.733 | 0.692 |

**Result-leak conclusion:** the "result already in the glyph" kill condition is not triggered. There is no measurable result signal in the glyph. Ablating it changes at most 1 item. Accuracy is the same whether or not the result is an operand.

## Verdict against the win and kill conditions
- **Qwen receiver, layer 8, add and sub, self and cross: it essentially wins.**
  - The structured glyph matches the text equation: add 1.000 vs 1.000, sub 0.963 vs 1.000.
  - It beats the scrambled bag: 0.37 and 0.30.
  - Swapping the operator predictably changes the answer, which follows the swapped op 93–100% of the time.
  - There is no result leak.
  - **But it ties text rather than beating it**, and Qwen `sub` fails the literal word-embedding test.
- **Smol receiver: it dies.** Text `7+2=` still clearly wins: add 1.000 vs 0.815, sub 0.926 vs 0.593. The op glyph does steer the answer (op-shuffle follows 73–93%), and the word-embedding test is passed.
- **Greater-than: it dies.** Text accuracy is itself only 0.67 (Qwen) and 0.49 (Smol, chance). The gt glyph never beats no-injection by more than noise, so it cannot be judged.
- **Self vs cross:** snapped glyphs are identical for self and cross, because snapping was perfect and the book is shared. Raw unsnapped canonical vectors transfer Smol→Qwen (L8: 1.00/1.00) but **not Qwen→Smol** (0.07/0.22). The negotiated book, not the raw adapter, is what makes cross-model transfer work.
- **Depth matters.** The effect only exists at about one third of model depth. By about 0.6 depth, the slot positions no longer feed the completion.

## Caveats
- **n is small:** 27/27/49 per cell, so differences under about 0.1 are noise. There are no confidence intervals and one train/test split.
- **The book negotiation was trivial.** All 24 entries passed in round 1, with A/B cosines of about 0.998. The closed alphabet gives the arbiter nothing to reject. Entries and adapters share the same train states. The "decodes to symbol" check uses a trained probe, not the J-lens. J-lens readout predicts the *next* token, so it is unsuitable for naming the current symbol.
- **Snapping is trivially perfect.** In this fixed format, each slot's state is nearly determined by its own token, so the snapped glyph equals a label lookup. In effect the communication test reduces to "can a receiver complete an equation from 4 patched slot states". It is not a test of a sender's hidden computation.
- **Replace mode only.** Patching was done at one layer per run. I did not try additive injection or multi-layer patching, and I chose 2 layers by fixed depth fractions.
- **gt uses only true/false tokens.** The op-shuffle for gt swaps to add, which makes the receiver output a digit. That measures "follows the swapped op", not true/false accuracy.
- **Every condition includes the format preamble,** with its 4 worked examples. Without it, the tiny models' answer format is unreliable.
- **Geometry (midpoints and so on) was deliberately not done,** as specified.

## Files
- **Scripts:** `v3/common3.py`, `v3/probe_tok.py`, `v3/extract_v3.py`, `v3/book_v3.py`, `v3/inject_v3.py`, `v3/tables_v3.py`
- **Book:** `v3/book_v3.json` (checks and rounds), `results/v3/book.pt` (adapters, entries, probes)
- **Results:** `results/v3/inject_{sender}_into_{receiver}.json` (rows and leak), `results/v3/tables_v3.json`
- **Logs:** `logs/v3/`
