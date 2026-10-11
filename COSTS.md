# Compute costs, per run (failed runs included)

**No paid compute and no paid APIs were used for any run in this repository.** Everything ran on (a) the "box", a cloud VM CPU (Intel Xeon, 8 threads, ~15 GB RAM, no GPU), (b) a laptop CPU (under WSL, v5 only), or (c) free Kaggle notebooks (2× Tesla T4).

How the numbers were derived: only from runtimes printed in logs (`fit_time`, `done ... Ns`, `runtime_s`), log start/end timestamps, Kaggle execution-log timestamps, and file mtimes in the original run directory. Where only mtimes exist, the figure is a **wall-clock span estimate** (first to last output file; it may include idle gaps and excludes time before the first file was written). Anything not recoverable is marked **unknown**. All times AEDT (UTC+11).

| Run | Hardware | Time | Source | Outcome |
|---|---|---|---|---|
| v1 (J-lens fits, extract, inject; Qwen2.5-0.5B + SmolLM2-360M) | box CPU | lens fits 3022 s (Qwen) + 1986 s (Smol); whole pipeline ≈1.7 h wall (est., ~21:07–22:46 Oct 9) | `logs/fit_*.log`, mtimes, `logs/timing.txt` | Completed; see RESULTS.md |
| v2 (concept book, 183 entries) | box CPU | ≈0.3 h wall (est., 07:31–07:53 Oct 10) | mtimes | Completed; see RESULTS_v2.md |
| v3 (maths book) | box CPU | ≈0.3–0.4 h wall (est., first output 08:02, last 08:22 Oct 10; extraction start unknown) | mtimes | Completed; see RESULTS_v3.md |
| v4 (three-party repository, + Pythia-410m) | box CPU | ≈3.4 h wall (est., 08:40–12:03 Oct 10, includes gaps between stages) | mtimes | Completed; see RESULTS_v4.md |
| v5 box side (SmolLM2-1.7B) | box CPU | extract 1571 s; t5 append ≈2 min; negotiation 1348 s; dev 1219 s; test 9075 s; analysis ≈0.1 h | `v5/logs/box*.out`, `results/*.json` runtime_s, STATE.txt | Completed (glyph lost to prose; see RESULTS_v5.md) |
| v5 laptop side (Qwen2.5-3B) | laptop CPU | determinism check ≈0.15 h; state extraction ≈4.1 h (14:33–18:38 Oct 10); **J-gram killed after 98 min, no batch done (failed)**; dev 12,763 s (3.5 h); test 43,260 s (12.0 h) | STATE.txt, MANIFEST_laptop.json, `runtime_s` | Completed except J-lens basis, which was **dropped** (fp32 OOM at 17.5 GB, bf16 too slow) |
| Kaggle 7B v1 (Qwen2.5-7B × OLMo-2-7B) | Kaggle 2× T4 (free) | unknown | no log retained | unknown |
| Kaggle 7B v2 | Kaggle 2× T4 (free) | 13,990 s ≈ 3.9 GPU-session-hours | execution-log timestamps (`kernel_v2_error.log`) | **Failed**: non-finite logits in fp16 (OLMo-7B TEST) |
| Kaggle 7B v3 | Kaggle 2× T4 (free) | 17,263 s ≈ 4.8 GPU-session-hours | execution-log timestamps | **Failed** in final analyze step (TypeError); all stages done, partial post-hoc analysis in RESULTS_v5k_7B_partial.md |
| Kaggle 7B v4 | Kaggle 2× T4 (free) | unknown | not retrieved | Relaunched by a stale watcher against instructions; nothing from it is used |
| v6 E1 calibration | box CPU | 5788 s (Qwen2.5-3B) + 2733 s (SmolLM2-1.7B) ≈ 2.4 h | `v6/e1/logs/run.log` | **Failed**: gate rejected every entry, honest ones included |
| v6 E1 main (oracle-ID receiver) | box CPU | 14,563 s + 5275 s ≈ 5.5 h; whole E1 job 16:22 Oct 11 – 00:15 Oct 12 (≈7.9 h wall) | `v6/e1/logs/run.log` | Completed; see RESULTS_E1.md |
| E1b Stage A, attempt 1 | box CPU (llama.cpp, Q4_K_M) | 09:56–10:20 Oct 12 (≈0.4 h wall) | STAGE_A_REPORT.md | **Stopped** by its pre-registered budget check (projected 4.99 h > 2 h cap) |
| E1b Stage A, resumed under A4 (cap 5.5 h) | box CPU | **in progress** | — | in progress |

Kaggle "GPU-session-hours" are notebook wall-clock from the execution log, not billed GPU time; Kaggle's free tier was used. Box and laptop CPU time was not billed per run.
