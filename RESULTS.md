# Shared glyph alphabet: first CPU-only pass (v0, anchor words)

Run date: 9 Oct 2026, Sydney time. Machine: 8 CPU cores, about 6 GB of free RAM, no GPU. Every number below comes from the files in `results/`. The full auto-generated tables are in the appendix and in `results/tables.md`.

## Setup
- **Model A:** Qwen/Qwen2.5-0.5B (24 layers, d=896). **Model B:** HuggingFaceTB/SmolLM2-360M (32 layers, d=960). Both ran in float32 on CPU with 8 threads. Neither model is gated and no HF token was used.
- **J-lens:** the `anthropics/jacobian-lens` reference code with `jlens.fit` and `dim_batch=16`.
  - **Corpus:** 32 WikiText-103 validation paragraphs, each truncated to **64 tokens**.
  - **Fitted layers:** the middle range only. That is Qwen 4–19 and Smol 5–25, which cuts backward cost.
  - **Why it was reduced:** one 128-token prompt over all layers took 168 s on Qwen, which would have meant about 2.3 h for 50 prompts. 64 tokens took about 68 s per prompt.
  - **Fit time:** Qwen **3022 s** (about 50 min). That figure includes roughly 10 min lost while a debug job competed for the CPU, during which one prompt took 704 s. SmolLM2 took **1986 s** (about 33 min).
  - **Convergence:** the relative change in the running mean per prompt dropped to about 4–6e-2 by the end.
- **Anchors:** **2000** words that are a single " word" token in both tokenizers. They were ranked by WikiText frequency with function words removed, and test concept words were force-included. " Ankara" was the only forced word missing.
- **Glyph:** J-lens logits restricted to the anchors, at the last prompt position. The logits are z-scored over the anchors, averaged over a 3-layer band, and centred by subtracting the mean glyph of 60 held-out WikiText prompts. "Dense" uses all 2000 dimensions. "Top-32" keeps only the 32 largest values. Both are L2-normalised.
  - **Band choice:** I picked the band that maximised J-lens pass@50 on the repo's multihop and association eval sets. That gave Qwen **L17–19** and Smol **L23–25**. Both sit at the top edge of the fitted range, at about 75% depth, which is later than a "workspace band" would ideally be.
  - **Mid-depth variant:** I also ran a fixed mid-depth band, Qwen L11–13 and Smol L15–17.
  - **Baselines:** the same glyph built from the plain logit lens, and from the model's **final output logits**.
- **Test prompts:**
  - 40 hand-written paraphrase pairs (80 prompts)
  - 30 minimal pairs
  - the repo's lens-eval-multihop (N=93) and lens-eval-association (N=102) prompt sets
  - 14 country "bridges" × 2 relations (capital, language) for injection
- **Runtimes:** feature extraction took 92 s for Qwen and 67 s for Smol. Each injection run took 87–176 s. Total wall time was about 1 h 50 min, mostly lens fitting.

## Step 2: lens sanity check
- **"The capital of France is":** the Qwen J-lens gives ' Paris' as top-1 at L8 and L12. At L17–19, though, it is dominated by blank tokens (' ______'), which mirrors the model's own output. For Smol, L24–25 gives ' Madrid', ' city', ' Barcelona', ' Paris'.
- **"Capital city of the country where the Eiffel Tower stands is":** the Qwen J-lens gives ' Paris' as top-1 at L17–19. For Smol, ' Paris' is #1 at L25.
- **Two-hop bridge detection is weak in these tiny models:**
  - Multihop "bridge entity in the top 10 at some fitted layer" was 0.172 with the J-lens versus 0.108 with the logit lens on Qwen. On SmolLM2, both lenses gave 0.075.
  - The best single-layer multihop pass@10 was 0.118 for Qwen and 0.065 for Smol.
  - On the association set (concepts that are never named), pass@10 was 0.000 for both lenses and both models.
  - Qualitatively, the logit lens mostly reads junk tokens at middle layers, while the J-lens gives on-topic words.
  - The full per-layer table is in the appendix.

## (a) Paraphrase vs random prompts within each model (40 pairs; J-lens glyph from the chosen band, centred, dense)
| model | paraphrase cos | random-pair cos | partner retrieved @1 among 79 (chance 0.013) |
|---|---|---|---|
| Qwen | 0.911 | 0.757 | 0.66 |
| SmolLM2 | 0.937 | 0.723 | 0.89 |

Paraphrases are clearly more similar than random pairs. The final-output baseline is about as good: Qwen 0.902 vs 0.700 with retrieval 0.78, and Smol 0.941 vs 0.706 with retrieval 0.93. A model-free word-overlap glyph scores 0.479 vs 0.004 with retrieval 0.625.

## (b) Cross-model: Qwen glyph vs SmolLM2 glyph for the same prompt (J-lens, centred, dense)
| prompt set | N | A→B @1 | B→A @1 | A→B @5 | chance @1 | shuffled-anchor control @1 (mean of 20) | matched / mismatched cos |
|---|---|---|---|---|---|---|---|
| multihop | 93 | **0.624** | 0.624 | 0.860 | 0.011 | 0.009 | 0.768 / 0.313 |
| association | 102 | **0.490** | 0.461 | 0.735 | 0.010 | 0.007 | 0.859 / 0.810 |
| paraphrase prompts | 80 | **0.588** | 0.525 | 0.925 | 0.013 | 0.020 | 0.832 / 0.674 |

- **Against chance and the shuffled control:** retrieval is 45–60× chance. Shuffling the anchor correspondence drops it to chance.
- **Sparse version is weaker:** top-32 gives multihop 0.473 and association 0.098.
- **Final-output baseline is as good or better:** multihop 0.763, association 0.608, paraphrase 0.688. So at this late band, much of the shared signal is "what word comes next".
- **Mid-depth band is weaker but still well above chance:** multihop 0.376, association 0.186, paraphrase 0.463. The controls there are 0.010–0.013.
- **Not just word overlap:** a glyph built only from which anchor words literally appear in the prompt retrieves the model's own glyph at only 0.08–0.40 with the J-lens. That is below the 0.49–0.62 model-to-model figure.

## (c) Minimal pairs (30 pairs, for example France/Germany capital; 29 scored for direction; dense centred glyph)
| glyph | model | mean pair cos | concept 1 in top 10 of the difference | concept 2 in top 10 of the negative difference | both in top 10 | median rank w1 / w2 (of 2000) |
|---|---|---|---|---|---|---|
| J-lens band | Qwen | 0.909 | 0.345 | 0.448 | 0.172 | 129 / 80 |
| J-lens band | Smol | 0.912 | 0.448 | 0.517 | 0.276 | 29 / 10 |
| final output | Qwen | 0.833 | 0.621 | 0.724 | 0.483 | 4 / 2 |
| final output | Smol | 0.846 | 0.621 | 0.793 | 0.483 | 5 / 1 |

- **The two models' difference vectors agree:** the matched pair has cosine 0.402 against 0.006 for mismatched pairs. Matching each pair's A difference to the right B difference succeeds 0.767 of the time (chance 0.033).
- **Distinguishable, but the direction only sometimes names the right words:** pairs are mostly distinguishable, but the difference points at the right anchor words in only a minority of cases with the J-lens band. The final-output glyph does better. At mid-depth this gets worse: "both in top 10" is 0.034 for Qwen and 0.000 for Smol.

## Causal injection (the reviewer's add-on)
**Design:**
- **Hop-1 prompt:** "Fact: The name of <descriptor> is", for example "…famous for Oktoberfest and the city of Munich…". The bundle is the top-16 anchors of that prompt's J-lens glyph, weighted by score.
- **Target prompt:** the bridge is omitted, so the answer can't be derived from it. Examples are "Fact: The capital city of this country is" and "…main language spoken in this country is".
- **Injection:** I add Σ w·v_c at the target model's band-centre layer at all non-BOS positions. Here v_c = J_L^T(g⊙u_c), normalised, and α is a multiple of the median residual norm.
- **Scoring:** accuracy is argmax over the candidate answers' first tokens. That is 14 capitals (chance 0.071) and 13 languages (chance 0.077). The margin is the log-prob of the correct answer minus the mean of the other candidates. n=28 per condition.

**Accuracy (best α in brackets; full α sweep in the appendix):**
| condition | Smol→Smol (B→B) | Qwen→Qwen | Qwen glyph → Smol | Smol glyph → Qwen |
|---|---|---|---|---|
| no injection | 0.071 | 0.071 | 0.071 | 0.071 |
| shuffled bundle, same weights and norm (5 seeds) | 0.036–0.093 | 0.057–0.086 | 0.050–0.071 | 0.057–0.071 |
| **real bundle** | **0.25–0.32** (0.321 at α=1, 4, 8; margin +2.29 at α=8) | **0.39–0.57** (0.571 at α=8, margin +3.92) | **0.29–0.50** (0.500 at α=8, margin +4.97) | **0.14–0.29** (0.286 at α=4) |
| real bundle with all answer words (capitals and languages) removed | 0.21–0.25 | 0.21–0.29 | 0.21–0.25 | 0.14–0.25 |
| bag-of-words text: the same 16 words prepended | **0.464** | **0.750** | **0.643** | **0.464** |
| bag-of-words text without answer words | 0.536 | 0.571 | 0.643 | 0.679 |
| *reference:* bridge word as text ("Germany.\n…") | 1.000 | 0.857 | 1.000 | 0.857 |
| *reference:* inject only the true bridge word's direction (uses ground truth, not the glyph) | 0.86–0.96 | 0.96–1.00 | 0.86–0.96 | 0.96–1.00 |
| *reference:* full two-hop prompt | 1.000 | 1.000 | 1.000 | 1.000 |

**Ablation on the full two-hop prompt** (project the bundle's directions out of the residual stream; baseline 1.000):
| projected out | Smol, band layers | Smol, all fitted layers | Qwen, band layers | Qwen, all fitted layers |
|---|---|---|---|---|
| bundle (16 directions) | 0.964 | 0.893 | 0.964 | **0.464** |
| bundle without answer words | 1.000 | 0.893 | 0.964 | 0.714 |
| bridge word only | 1.000 | 0.929 | 0.893 | 0.750 |
| 16 random anchors (5 seeds) | 1.000 | 0.993 | 1.000 | 0.964 |

**Reading these results:**
- **Self-injection works in a weak but real way.** The real bundle beats both the shuffled bundle and no injection in every pairing, by about 3–8× over chance accuracy, and shuffled stays at chance.
- **Cross-model injection also works,** and Qwen's glyph into SmolLM2 does better than SmolLM2's own glyph (0.50 vs 0.32). This is probably because Qwen resolves hop 1 better: the bridge is ranked 1–7 in Qwen's bundle versus 5–48 in Smol's.
- **Plain bag-of-words text beats the injected bundle in all four pairings.**
- Part of the bundle effect comes from answer words leaking into it (for example "Paris" or "French"). Removing them lowers the effect but leaves it above chance.
- **Ablation:** removing the bundle at all fitted layers clearly hurts Qwen (1.00 → 0.46 vs 0.96 for random directions). It only mildly hurts Smol (0.89 vs 0.99). Band-only ablation does almost nothing.

## Verdict
"a = a" shows real but limited signal at this scale.
- **Glyphs are anchored and shared:** the two models' anchor-word glyphs for the same prompt match far above chance (49–62% top-1 among about 100, against roughly 1%), and the shuffled-anchor control collapses to chance.
- **But they mostly encode the next-token prediction:** a glyph from the models' final output does as well or better.
- **Injection is causal but beaten by text:** an injected bundle shifts answers causally, within and across models, beating both shuffled and no-injection controls. Plain bag-of-words text of the same 16 words beats it every time.

## Caveats
- Both models are tiny (0.36B and 0.5B) and run on CPU.
- The lenses are fitted on only 32 prompts × 64 tokens. The README suggests about 100 prompts, and the paper used 1000 × 128.
- The chosen band is late, near 75% depth, because mid-layer readouts were weak. Mid-band glyphs share less across models.
- The injection set is small: 14 bridges × 2 relations, n=28. α, layer, and the all-positions injection mode were not tuned on a separate split.
- Answer words leak into bundles.
- The ablation reuses layer-L directions at other layers, which is an approximation.
- Paraphrases and minimal pairs are hand-written and few.
- There are no confidence intervals and only one lens fit per model.

## Next steps
- Fit lenses with 100–200 prompts × 128 tokens. This is feasible overnight on CPU, or quickly on a GPU. Then recheck whether a true mid-depth workspace band appears.
- Build glyphs from non-final positions, or subtract the final-output glyph, to isolate "workspace" content from next-token prediction.
- Use a pseudo-inverse decoder (D_m) instead of the gradient direction, and sweep the injection layer.
- Add a text-handoff baseline at an equal byte budget, which is already partly done via bag-of-words. Add bigger models, and tune α on a held-out split.

## Files
- **Scripts:** `common.py`, `fit_lens.py`, `build_anchors.py`, `prompts.py`, `extract.py`, `analyze.py`, `lexical_baseline.py`, `inject.py`, `make_tables.py`, `run_after_fits.sh`
- **Lenses:** `lenses/{qwen,smol}_lens.pt`
- **Logs:** `logs/`
- **Raw results:** `results/*.json`

## Appendix: full tables (generated by make_tables.py)
### Lens sanity: bridge/concept rank metrics per layer (J-lens vs logit lens)

**Qwen/Qwen2.5-0.5B** (24 layers, fitted source layers 4-19, chosen band [17, 18, 19], extraction 92s)

| layer | multihop J pass@10 | multihop logit pass@10 | assoc J pass@10 | assoc logit pass@10 | multihop J median rank |
|---|---|---|---|---|---|
| 4 | 0.000 | 0.000 | 0.000 | 0.000 | 2847 |
| 5 | 0.011 | 0.000 | 0.000 | 0.000 | 1343 |
| 6 | 0.011 | 0.000 | 0.000 | 0.000 | 1823 |
| 7 | 0.011 | 0.000 | 0.000 | 0.000 | 1967 |
| 8 | 0.011 | 0.000 | 0.000 | 0.000 | 1041 |
| 9 | 0.000 | 0.000 | 0.000 | 0.000 | 1174 |
| 10 | 0.000 | 0.000 | 0.000 | 0.000 | 1067 |
| 11 | 0.000 | 0.000 | 0.000 | 0.000 | 1317 |
| 12 | 0.000 | 0.000 | 0.000 | 0.000 | 2583 |
| 13 | 0.011 | 0.000 | 0.000 | 0.000 | 2467 |
| 14 | 0.022 | 0.000 | 0.000 | 0.000 | 3841 |
| 15 | 0.022 | 0.022 | 0.000 | 0.000 | 4878 |
| 16 | 0.043 | 0.032 | 0.000 | 0.000 | 1465 |
| 17 | 0.108 | 0.043 | 0.000 | 0.000 | 566 |
| 18 | 0.075 | 0.043 | 0.000 | 0.000 | 1002 |
| 19 | 0.118 | 0.086 | 0.000 | 0.000 | 287 |

Any-layer pass@10: multihop J=0.172, logit=0.108; association J=0.000, logit=0.000

**HuggingFaceTB/SmolLM2-360M** (32 layers, fitted source layers 5-25, chosen band [23, 24, 25], extraction 67s)

| layer | multihop J pass@10 | multihop logit pass@10 | assoc J pass@10 | assoc logit pass@10 | multihop J median rank |
|---|---|---|---|---|---|
| 5 | 0.000 | 0.000 | 0.000 | 0.000 | 14983 |
| 6 | 0.000 | 0.000 | 0.000 | 0.000 | 15775 |
| 7 | 0.000 | 0.000 | 0.000 | 0.000 | 12214 |
| 8 | 0.000 | 0.000 | 0.000 | 0.000 | 9909 |
| 9 | 0.000 | 0.000 | 0.000 | 0.000 | 8525 |
| 10 | 0.000 | 0.000 | 0.000 | 0.000 | 15835 |
| 11 | 0.000 | 0.000 | 0.000 | 0.000 | 15130 |
| 12 | 0.011 | 0.000 | 0.000 | 0.000 | 16743 |
| 13 | 0.000 | 0.000 | 0.000 | 0.000 | 16389 |
| 14 | 0.000 | 0.000 | 0.000 | 0.000 | 10981 |
| 15 | 0.000 | 0.000 | 0.000 | 0.000 | 10218 |
| 16 | 0.011 | 0.000 | 0.000 | 0.000 | 9134 |
| 17 | 0.011 | 0.000 | 0.000 | 0.000 | 9142 |
| 18 | 0.011 | 0.000 | 0.000 | 0.000 | 11317 |
| 19 | 0.011 | 0.000 | 0.000 | 0.000 | 11865 |
| 20 | 0.022 | 0.000 | 0.000 | 0.000 | 10840 |
| 21 | 0.022 | 0.011 | 0.000 | 0.000 | 13432 |
| 22 | 0.011 | 0.000 | 0.000 | 0.000 | 12687 |
| 23 | 0.032 | 0.011 | 0.000 | 0.000 | 2953 |
| 24 | 0.032 | 0.032 | 0.000 | 0.000 | 2435 |
| 25 | 0.065 | 0.065 | 0.000 | 0.000 | 942 |

Any-layer pass@10: multihop J=0.075, logit=0.075; association J=0.000, logit=0.000

### (a) Within-model paraphrase consistency (40 pairs; random = all cross-pair combinations)

| model | glyph variant | paraphrase cos | random cos | partner retrieval @1 (chance 0.013) |
|---|---|---|---|---|
| qwen | jlens-raw-dense | 0.903 ± 0.077 | 0.734 ± 0.144 | 0.675 |
| qwen | jlens-raw-top32 | 0.781 ± 0.113 | 0.609 ± 0.217 | 0.425 |
| qwen | jlens-centred-dense | 0.911 ± 0.077 | 0.757 ± 0.139 | 0.662 |
| qwen | jlens-centred-top32 | 0.839 ± 0.104 | 0.712 ± 0.219 | 0.325 |
| qwen | logit-raw-dense | 0.855 ± 0.096 | 0.663 ± 0.168 | 0.588 |
| qwen | logit-raw-top32 | 0.575 ± 0.156 | 0.349 ± 0.162 | 0.375 |
| qwen | logit-centred-dense | 0.840 ± 0.110 | 0.630 ± 0.190 | 0.600 |
| qwen | logit-centred-top32 | 0.582 ± 0.158 | 0.358 ± 0.155 | 0.438 |
| qwen | final-raw-dense | 0.904 ± 0.068 | 0.697 ± 0.154 | 0.775 |
| qwen | final-raw-top32 | 0.743 ± 0.144 | 0.535 ± 0.204 | 0.425 |
| qwen | final-centred-dense | 0.902 ± 0.083 | 0.700 ± 0.179 | 0.775 |
| qwen | final-centred-top32 | 0.780 ± 0.121 | 0.601 ± 0.207 | 0.500 |
| smol | jlens-raw-dense | 0.940 ± 0.052 | 0.741 ± 0.144 | 0.887 |
| smol | jlens-raw-top32 | 0.882 ± 0.044 | 0.692 ± 0.234 | 0.625 |
| smol | jlens-centred-dense | 0.937 ± 0.053 | 0.723 ± 0.148 | 0.887 |
| smol | jlens-centred-top32 | 0.886 ± 0.065 | 0.714 ± 0.240 | 0.588 |
| smol | logit-raw-dense | 0.902 ± 0.070 | 0.645 ± 0.152 | 0.863 |
| smol | logit-raw-top32 | 0.668 ± 0.134 | 0.364 ± 0.149 | 0.588 |
| smol | logit-centred-dense | 0.894 ± 0.075 | 0.618 ± 0.167 | 0.863 |
| smol | logit-centred-top32 | 0.637 ± 0.147 | 0.346 ± 0.147 | 0.575 |
| smol | final-raw-dense | 0.950 ± 0.054 | 0.743 ± 0.193 | 0.925 |
| smol | final-raw-top32 | 0.800 ± 0.128 | 0.521 ± 0.191 | 0.775 |
| smol | final-centred-dense | 0.941 ± 0.070 | 0.706 ± 0.240 | 0.925 |
| smol | final-centred-top32 | 0.823 ± 0.140 | 0.585 ± 0.203 | 0.613 |

### (b) Cross-model retrieval (A = Qwen, B = SmolLM2)

| prompt set | glyph variant | N | A→B @1 | B→A @1 | A→B @5 | chance @1 | shuffled-anchor ctrl @1 (mean / max of 20) | matched cos | mismatched cos |
|---|---|---|---|---|---|---|---|---|---|
| multihop | jlens-raw-dense | 93 | 0.570 | 0.656 | 0.892 | 0.011 | 0.008 / 0.022 | 0.723 | 0.272 |
| multihop | jlens-raw-top32 | 93 | 0.495 | 0.452 | 0.828 | 0.011 | 0.011 / 0.032 | 0.520 | 0.089 |
| multihop | jlens-centred-dense | 93 | 0.624 | 0.624 | 0.860 | 0.011 | 0.009 / 0.032 | 0.768 | 0.313 |
| multihop | jlens-centred-top32 | 93 | 0.473 | 0.462 | 0.806 | 0.011 | 0.016 / 0.032 | 0.581 | 0.101 |
| multihop | logit-raw-dense | 93 | 0.570 | 0.484 | 0.892 | 0.011 | 0.012 / 0.065 | 0.403 | 0.176 |
| multihop | logit-raw-top32 | 93 | 0.301 | 0.226 | 0.591 | 0.011 | 0.011 / 0.032 | 0.278 | 0.090 |
| multihop | logit-centred-dense | 93 | 0.581 | 0.516 | 0.903 | 0.011 | 0.012 / 0.032 | 0.448 | 0.198 |
| multihop | logit-centred-top32 | 93 | 0.333 | 0.301 | 0.720 | 0.011 | 0.011 / 0.043 | 0.319 | 0.103 |
| multihop | final-raw-dense | 93 | 0.763 | 0.785 | 0.957 | 0.011 | 0.008 / 0.022 | 0.779 | 0.451 |
| multihop | final-raw-top32 | 93 | 0.484 | 0.538 | 0.796 | 0.011 | 0.011 / 0.032 | 0.648 | 0.153 |
| multihop | final-centred-dense | 93 | 0.763 | 0.731 | 0.946 | 0.011 | 0.013 / 0.032 | 0.672 | 0.238 |
| multihop | final-centred-top32 | 93 | 0.484 | 0.516 | 0.839 | 0.011 | 0.008 / 0.043 | 0.593 | 0.104 |
| assoc | jlens-raw-dense | 102 | 0.480 | 0.451 | 0.725 | 0.010 | 0.008 / 0.020 | 0.843 | 0.793 |
| assoc | jlens-raw-top32 | 102 | 0.167 | 0.049 | 0.353 | 0.010 | 0.012 / 0.029 | 0.736 | 0.697 |
| assoc | jlens-centred-dense | 102 | 0.490 | 0.461 | 0.735 | 0.010 | 0.007 / 0.020 | 0.859 | 0.810 |
| assoc | jlens-centred-top32 | 102 | 0.098 | 0.078 | 0.245 | 0.010 | 0.010 / 0.039 | 0.796 | 0.766 |
| assoc | logit-raw-dense | 102 | 0.206 | 0.255 | 0.422 | 0.010 | 0.008 / 0.029 | 0.378 | 0.320 |
| assoc | logit-raw-top32 | 102 | 0.088 | 0.059 | 0.196 | 0.010 | 0.010 / 0.020 | 0.302 | 0.254 |
| assoc | logit-centred-dense | 102 | 0.225 | 0.206 | 0.431 | 0.010 | 0.007 / 0.029 | 0.378 | 0.312 |
| assoc | logit-centred-top32 | 102 | 0.078 | 0.049 | 0.284 | 0.010 | 0.012 / 0.029 | 0.269 | 0.218 |
| assoc | final-raw-dense | 102 | 0.627 | 0.461 | 0.853 | 0.010 | 0.009 / 0.020 | 0.872 | 0.809 |
| assoc | final-raw-top32 | 102 | 0.255 | 0.167 | 0.480 | 0.010 | 0.010 / 0.029 | 0.685 | 0.539 |
| assoc | final-centred-dense | 102 | 0.608 | 0.490 | 0.853 | 0.010 | 0.010 / 0.020 | 0.880 | 0.821 |
| assoc | final-centred-top32 | 102 | 0.225 | 0.235 | 0.529 | 0.010 | 0.007 / 0.029 | 0.711 | 0.580 |
| para | jlens-raw-dense | 80 | 0.613 | 0.512 | 0.950 | 0.013 | 0.013 / 0.037 | 0.797 | 0.638 |
| para | jlens-raw-top32 | 80 | 0.263 | 0.163 | 0.537 | 0.013 | 0.010 / 0.037 | 0.746 | 0.622 |
| para | jlens-centred-dense | 80 | 0.588 | 0.525 | 0.925 | 0.013 | 0.020 / 0.050 | 0.832 | 0.674 |
| para | jlens-centred-top32 | 80 | 0.225 | 0.163 | 0.525 | 0.013 | 0.013 / 0.037 | 0.804 | 0.688 |
| para | logit-raw-dense | 80 | 0.350 | 0.250 | 0.713 | 0.013 | 0.015 / 0.050 | 0.375 | 0.264 |
| para | logit-raw-top32 | 80 | 0.125 | 0.113 | 0.325 | 0.013 | 0.013 / 0.037 | 0.316 | 0.216 |
| para | logit-centred-dense | 80 | 0.325 | 0.212 | 0.750 | 0.013 | 0.011 / 0.025 | 0.381 | 0.261 |
| para | logit-centred-top32 | 80 | 0.150 | 0.163 | 0.375 | 0.013 | 0.010 / 0.025 | 0.287 | 0.192 |
| para | final-raw-dense | 80 | 0.675 | 0.475 | 0.975 | 0.013 | 0.014 / 0.050 | 0.839 | 0.670 |
| para | final-raw-top32 | 80 | 0.263 | 0.400 | 0.562 | 0.013 | 0.013 / 0.037 | 0.686 | 0.495 |
| para | final-centred-dense | 80 | 0.688 | 0.475 | 0.963 | 0.013 | 0.011 / 0.025 | 0.832 | 0.653 |
| para | final-centred-top32 | 80 | 0.263 | 0.350 | 0.625 | 0.013 | 0.014 / 0.037 | 0.727 | 0.566 |

### (c) Minimal pairs (30 pairs, 29 scored for direction; dense centred glyph)

| glyph | model | mean pair cos | frac pairs cos<0.9 | w1 in top10 of diff | w2 in top10 of -diff | both top10 | both top50 | median rank w1 / w2 |
|---|---|---|---|---|---|---|---|---|
| jlens | qwen | 0.909 | 0.367 | 0.345 | 0.448 | 0.172 | 0.207 | 129 / 80 |
| jlens | smol | 0.912 | 0.300 | 0.448 | 0.517 | 0.276 | 0.414 | 29 / 10 |
| logit | qwen | 0.895 | 0.433 | 0.276 | 0.241 | 0.172 | 0.172 | 165 / 158 |
| logit | smol | 0.895 | 0.300 | 0.276 | 0.241 | 0.138 | 0.207 | 81 / 122 |
| final | qwen | 0.833 | 0.700 | 0.621 | 0.724 | 0.483 | 0.552 | 4 / 2 |
| final | smol | 0.846 | 0.700 | 0.621 | 0.793 | 0.483 | 0.690 | 5 / 1 |

| glyph | cross-model diff-vector cos, matched pair | mismatched pairs | diff retrieval A→B @1 (chance 0.033) |
|---|---|---|---|
| jlens | 0.402 | 0.006 | 0.767 |
| logit | 0.216 | 0.001 | 0.800 |
| final | 0.366 | 0.001 | 0.967 |

### Injection: bundle from Qwen/Qwen2.5-0.5B → into Qwen/Qwen2.5-0.5B (layer 18, band [17, 18, 19], k=16, runtime 176s)

| condition | acc (both) | acc capital | acc language | mean log-prob margin vs other candidates | n |
|---|---|---|---|---|---|
| none | 0.071 | 0.071 | 0.071 | -0.00 | 28 |
| oracle_text_bridge_named | 1.000 | 1.000 | 1.000 | +9.83 | 28 |
| full_twohop_prompt | 1.000 | 1.000 | 1.000 | +7.32 | 28 |
| text_bow_k16 | 0.750 | 0.786 | 0.714 | +5.06 | 28 |
| text_bow_noanswers_k16 | 0.571 | 0.500 | 0.643 | +3.86 | 28 |
| text_bridge_word_only | 0.857 | 0.857 | 0.857 | +5.89 | 28 |
| inj_real_a1.0 | 0.429 | 0.357 | 0.500 | +1.92 | 28 |
| inj_real_noanswers_a1.0 | 0.250 | 0.143 | 0.357 | +1.18 | 28 |
| inj_bridge_only_a1.0 | 0.964 | 0.929 | 1.000 | +4.94 | 28 |
| inj_shuffled_a1.0 | 0.071 | 0.071 | 0.071 | +0.00 | 140 |
| inj_real_a2.0 | 0.393 | 0.214 | 0.571 | +2.10 | 28 |
| inj_real_noanswers_a2.0 | 0.214 | 0.143 | 0.286 | +1.27 | 28 |
| inj_bridge_only_a2.0 | 0.964 | 0.929 | 1.000 | +5.58 | 28 |
| inj_shuffled_a2.0 | 0.057 | 0.086 | 0.029 | -0.05 | 140 |
| inj_real_a4.0 | 0.500 | 0.357 | 0.643 | +2.62 | 28 |
| inj_real_noanswers_a4.0 | 0.286 | 0.143 | 0.429 | +1.51 | 28 |
| inj_bridge_only_a4.0 | 0.964 | 0.929 | 1.000 | +7.47 | 28 |
| inj_shuffled_a4.0 | 0.086 | 0.086 | 0.086 | -0.04 | 140 |
| inj_real_a8.0 | 0.571 | 0.571 | 0.571 | +3.92 | 28 |
| inj_real_noanswers_a8.0 | 0.214 | 0.143 | 0.286 | +2.12 | 28 |
| inj_bridge_only_a8.0 | 1.000 | 1.000 | 1.000 | +11.35 | 28 |
| inj_shuffled_a8.0 | 0.064 | 0.071 | 0.057 | -0.07 | 140 |
| abl_none | 1.000 | 1.000 | 1.000 | +7.32 | 28 |
| abl_band_bundle_k16 | 0.964 | 1.000 | 0.929 | +7.79 | 28 |
| abl_band_bundle_noanswers_k16 | 0.964 | 0.929 | 1.000 | +8.23 | 28 |
| abl_band_random_k16 | 1.000 | 1.000 | 1.000 | +8.59 | 140 |
| abl_band_bridge_only | 0.893 | 0.929 | 0.857 | +6.63 | 28 |
| abl_band_random_1 | 1.000 | 1.000 | 1.000 | +7.44 | 28 |
| abl_all_fitted_bundle_k16 | 0.464 | 0.357 | 0.571 | +4.12 | 28 |
| abl_all_fitted_bundle_noanswers_k16 | 0.714 | 0.571 | 0.857 | +4.81 | 28 |
| abl_all_fitted_random_k16 | 0.964 | 0.971 | 0.957 | +7.11 | 140 |
| abl_all_fitted_bridge_only | 0.750 | 0.857 | 0.643 | +4.65 | 28 |
| abl_all_fitted_random_1 | 1.000 | 1.000 | 1.000 | +7.28 | 28 |

Bridge rank in source glyph: {'France': 1, 'Germany': 2, 'Japan': 1, 'Italy': 1, 'Spain': 3, 'Russia': 1, 'China': 1, 'Egypt': 1, 'Greece': 2, 'Portugal': 1, 'Turkey': 4, 'Sweden': 7, 'Netherlands': 1, 'Poland': 3}

### Injection: bundle from Qwen/Qwen2.5-0.5B → into HuggingFaceTB/SmolLM2-360M (layer 24, band [23, 24, 25], k=16, runtime 87s)

| condition | acc (both) | acc capital | acc language | mean log-prob margin vs other candidates | n |
|---|---|---|---|---|---|
| none | 0.071 | 0.071 | 0.071 | -0.00 | 28 |
| oracle_text_bridge_named | 1.000 | 1.000 | 1.000 | +10.57 | 28 |
| full_twohop_prompt | 1.000 | 1.000 | 1.000 | +8.42 | 28 |
| text_bow_k16 | 0.643 | 0.714 | 0.571 | +4.69 | 28 |
| text_bow_noanswers_k16 | 0.643 | 0.786 | 0.500 | +3.62 | 28 |
| text_bridge_word_only | 1.000 | 1.000 | 1.000 | +9.07 | 28 |
| inj_real_a1.0 | 0.286 | 0.214 | 0.357 | +1.99 | 28 |
| inj_real_noanswers_a1.0 | 0.250 | 0.143 | 0.357 | +1.32 | 28 |
| inj_bridge_only_a1.0 | 0.893 | 0.786 | 1.000 | +4.96 | 28 |
| inj_shuffled_a1.0 | 0.064 | 0.071 | 0.057 | -0.01 | 140 |
| inj_real_a2.0 | 0.393 | 0.214 | 0.571 | +2.81 | 28 |
| inj_real_noanswers_a2.0 | 0.250 | 0.143 | 0.357 | +1.80 | 28 |
| inj_bridge_only_a2.0 | 0.857 | 0.786 | 0.929 | +6.88 | 28 |
| inj_shuffled_a2.0 | 0.071 | 0.071 | 0.071 | -0.07 | 140 |
| inj_real_a4.0 | 0.429 | 0.357 | 0.500 | +3.90 | 28 |
| inj_real_noanswers_a4.0 | 0.214 | 0.143 | 0.286 | +2.27 | 28 |
| inj_bridge_only_a4.0 | 0.964 | 1.000 | 0.929 | +11.64 | 28 |
| inj_shuffled_a4.0 | 0.071 | 0.086 | 0.057 | -0.08 | 140 |
| inj_real_a8.0 | 0.500 | 0.500 | 0.500 | +4.97 | 28 |
| inj_real_noanswers_a8.0 | 0.250 | 0.143 | 0.357 | +2.68 | 28 |
| inj_bridge_only_a8.0 | 0.964 | 1.000 | 0.929 | +17.01 | 28 |
| inj_shuffled_a8.0 | 0.050 | 0.043 | 0.057 | -0.02 | 140 |

Bridge rank in source glyph: {'France': 1, 'Germany': 2, 'Japan': 1, 'Italy': 1, 'Spain': 3, 'Russia': 1, 'China': 1, 'Egypt': 1, 'Greece': 2, 'Portugal': 1, 'Turkey': 4, 'Sweden': 7, 'Netherlands': 1, 'Poland': 3}

### Injection: bundle from HuggingFaceTB/SmolLM2-360M → into Qwen/Qwen2.5-0.5B (layer 18, band [17, 18, 19], k=16, runtime 114s)

| condition | acc (both) | acc capital | acc language | mean log-prob margin vs other candidates | n |
|---|---|---|---|---|---|
| none | 0.071 | 0.071 | 0.071 | -0.00 | 28 |
| oracle_text_bridge_named | 1.000 | 1.000 | 1.000 | +9.83 | 28 |
| full_twohop_prompt | 1.000 | 1.000 | 1.000 | +7.32 | 28 |
| text_bow_k16 | 0.464 | 0.500 | 0.429 | +3.13 | 28 |
| text_bow_noanswers_k16 | 0.679 | 0.714 | 0.643 | +4.26 | 28 |
| text_bridge_word_only | 0.857 | 0.857 | 0.857 | +5.89 | 28 |
| inj_real_a1.0 | 0.143 | 0.071 | 0.214 | +1.02 | 28 |
| inj_real_noanswers_a1.0 | 0.143 | 0.143 | 0.143 | +1.05 | 28 |
| inj_bridge_only_a1.0 | 0.964 | 0.929 | 1.000 | +4.94 | 28 |
| inj_shuffled_a1.0 | 0.071 | 0.071 | 0.071 | +0.08 | 140 |
| inj_real_a2.0 | 0.214 | 0.143 | 0.286 | +1.09 | 28 |
| inj_real_noanswers_a2.0 | 0.179 | 0.143 | 0.214 | +1.11 | 28 |
| inj_bridge_only_a2.0 | 0.964 | 0.929 | 1.000 | +5.58 | 28 |
| inj_shuffled_a2.0 | 0.057 | 0.071 | 0.043 | +0.01 | 140 |
| inj_real_a4.0 | 0.286 | 0.214 | 0.357 | +1.30 | 28 |
| inj_real_noanswers_a4.0 | 0.250 | 0.214 | 0.286 | +1.32 | 28 |
| inj_bridge_only_a4.0 | 0.964 | 0.929 | 1.000 | +7.47 | 28 |
| inj_shuffled_a4.0 | 0.064 | 0.071 | 0.057 | -0.03 | 140 |
| inj_real_a8.0 | 0.214 | 0.214 | 0.214 | +1.81 | 28 |
| inj_real_noanswers_a8.0 | 0.214 | 0.143 | 0.286 | +1.77 | 28 |
| inj_bridge_only_a8.0 | 1.000 | 1.000 | 1.000 | +11.35 | 28 |
| inj_shuffled_a8.0 | 0.071 | 0.071 | 0.071 | -0.05 | 140 |

Bridge rank in source glyph: {'France': 19, 'Germany': 13, 'Japan': 19, 'Italy': 10, 'Spain': 14, 'Russia': 11, 'China': 10, 'Egypt': 7, 'Greece': 5, 'Portugal': 12, 'Turkey': 15, 'Sweden': 29, 'Netherlands': 15, 'Poland': 48}

### Injection: bundle from HuggingFaceTB/SmolLM2-360M → into HuggingFaceTB/SmolLM2-360M (layer 24, band [23, 24, 25], k=16, runtime 144s)

| condition | acc (both) | acc capital | acc language | mean log-prob margin vs other candidates | n |
|---|---|---|---|---|---|
| none | 0.071 | 0.071 | 0.071 | -0.00 | 28 |
| oracle_text_bridge_named | 1.000 | 1.000 | 1.000 | +10.57 | 28 |
| full_twohop_prompt | 1.000 | 1.000 | 1.000 | +8.42 | 28 |
| text_bow_k16 | 0.464 | 0.571 | 0.357 | +2.66 | 28 |
| text_bow_noanswers_k16 | 0.536 | 0.571 | 0.500 | +3.10 | 28 |
| text_bridge_word_only | 1.000 | 1.000 | 1.000 | +9.07 | 28 |
| inj_real_a1.0 | 0.321 | 0.214 | 0.429 | +1.33 | 28 |
| inj_real_noanswers_a1.0 | 0.214 | 0.214 | 0.214 | +1.29 | 28 |
| inj_bridge_only_a1.0 | 0.893 | 0.786 | 1.000 | +4.96 | 28 |
| inj_shuffled_a1.0 | 0.093 | 0.071 | 0.114 | +0.02 | 140 |
| inj_real_a2.0 | 0.250 | 0.143 | 0.357 | +1.68 | 28 |
| inj_real_noanswers_a2.0 | 0.250 | 0.286 | 0.214 | +1.56 | 28 |
| inj_bridge_only_a2.0 | 0.857 | 0.786 | 0.929 | +6.88 | 28 |
| inj_shuffled_a2.0 | 0.071 | 0.086 | 0.057 | -0.03 | 140 |
| inj_real_a4.0 | 0.321 | 0.286 | 0.357 | +1.98 | 28 |
| inj_real_noanswers_a4.0 | 0.214 | 0.214 | 0.214 | +1.78 | 28 |
| inj_bridge_only_a4.0 | 0.964 | 1.000 | 0.929 | +11.64 | 28 |
| inj_shuffled_a4.0 | 0.036 | 0.057 | 0.014 | -0.07 | 140 |
| inj_real_a8.0 | 0.321 | 0.357 | 0.286 | +2.29 | 28 |
| inj_real_noanswers_a8.0 | 0.214 | 0.214 | 0.214 | +1.99 | 28 |
| inj_bridge_only_a8.0 | 0.964 | 1.000 | 0.929 | +17.01 | 28 |
| inj_shuffled_a8.0 | 0.079 | 0.086 | 0.071 | -0.13 | 140 |
| abl_none | 1.000 | 1.000 | 1.000 | +8.42 | 28 |
| abl_band_bundle_k16 | 0.964 | 1.000 | 0.929 | +8.49 | 28 |
| abl_band_bundle_noanswers_k16 | 1.000 | 1.000 | 1.000 | +8.49 | 28 |
| abl_band_random_k16 | 1.000 | 1.000 | 1.000 | +8.59 | 140 |
| abl_band_bridge_only | 1.000 | 1.000 | 1.000 | +7.68 | 28 |
| abl_band_random_1 | 1.000 | 1.000 | 1.000 | +8.32 | 28 |
| abl_all_fitted_bundle_k16 | 0.893 | 0.857 | 0.929 | +6.80 | 28 |
| abl_all_fitted_bundle_noanswers_k16 | 0.893 | 0.929 | 0.857 | +6.54 | 28 |
| abl_all_fitted_random_k16 | 0.993 | 0.986 | 1.000 | +8.28 | 140 |
| abl_all_fitted_bridge_only | 0.929 | 0.857 | 1.000 | +6.93 | 28 |
| abl_all_fitted_random_1 | 1.000 | 1.000 | 1.000 | +8.37 | 28 |

Bridge rank in source glyph: {'France': 19, 'Germany': 13, 'Japan': 19, 'Italy': 10, 'Spain': 14, 'Russia': 11, 'China': 10, 'Egypt': 7, 'Greece': 5, 'Portugal': 12, 'Turkey': 15, 'Sweden': 29, 'Netherlands': 15, 'Poland': 48}
