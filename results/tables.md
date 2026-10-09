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
