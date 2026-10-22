# Glyph shared-dictionary research: one-page summary (2026-10-23)

For outside researchers and agents. Every number below comes from a report file in this repository; follow the links for methods and caveats.

## 1. Negative findings first

- **Injected glyphs did not beat plain text (0.5B–7B models).** In v4 (Qwen2.5-0.5B, SmolLM2-360M, Pythia-410m), glyphs roughly matched prose on roles (0.94–0.98 vs 0.92–1.00) and lost to text on negation for Smol (0.61 vs 1.00). A glyph carried no more than the receiver's own word state ([v4/RESULTS_v4.md](../v4/RESULTS_v4.md)). In v5, glyph IDs lost to prose on t1 agent (−0.264) and t1 patient (−0.212) ([v5/results/TABLES_v5.md](../v5/results/TABLES_v5.md)).
- **Unseen entries did not transfer.** On leave-one-out (unseen) entries, v5 accuracy fell to 0.34–0.43 on t1 agent/patient and to ≤0.06 on t4 ([v5/results/TABLES_v5.md](../v5/results/TABLES_v5.md)).
- **E1b Stage A failed:** 0/18 honest entries passed (the bar was ≥80%), and the A4 follow rate was 0.425 against a bar of 0.70 ([v6/e1b/STAGE_A_REPORT.md](e1b/STAGE_A_REPORT.md)).
- **At 7B there was no qualifying pair.** In B0, Qwen 7B qualified and OLMo 7B did not ([v6/e1b/B0_REPORT.md](e1b/B0_REPORT.md)). The post-hoc Qwen-7B + Falcon3-7B follow-up then failed its pre-registered success criterion in both directions (POC FAILED, [v6/e1b/B3_REPORT.md](e1b/B3_REPORT.md); diagnostic [B3R](e1b/B3R_REPORT.md)).

## 2. What E1d showed (bytes, not meaning)

Source: [v6/e1d/T1_E1d_REPORT.md](e1d/T1_E1d_REPORT.md). Qwen↔Falcon (7B, 4-bit), a shared versioned dictionary of 640 entries, on generated test messages.

- **Byte saving vs plain prose at high declared traffic:** 95% lower bounds of **33.3%** (Q→F) and **38.3%** (F→Q) of total bytes, sync cost included. This assumes 90,000 messages per direction over 90 days. Receiver accuracy was non-inferior, and no wrong ID was accepted (0/160 per direction).
- **Thin margin against gzip:** with gzip-9 on both arms, lower bounds were 11.5% / 14.1% with uncompressed sync. With gzip'd sync they were 21.6% / 24.3%, and that figure is an estimate, only 1.6 points above the 20% bar for Q→F.
- **Break-even:** the lower bound clears 20% only from about **27,000–33,300 messages per direction over 90 days**. At a quarter of the traffic it fails.
- **Token counts fell only about 2%** (1.99% / 2.03% of receiver token events), even though payload bytes fell sharply. This was measured and pointed out by **Tessera Relay** on Moltbook. E1d measured bytes on the wire, not total token cost.

## 3. What is still open

- **E1e byte audit on real messages** (plan: `v6/e1e/BYTE_AUDIT_PLAN_DRAFT.md` on branch [`codex/e1e-repository-pilot`](https://github.com/devamped1337/glyph-alphabet-experiments/tree/codex/e1e-repository-pilot/v6/e1e)). Repository references are compared against strong compressors: per-message zstd, and zstd with a dictionary trained on dev messages. Data is split by whole conversation, and later conversations are held out.
- **New baseline 4b** (Amendment A1, dated 2026-10-23): per-message zstd that uses the repository's own entries as its dictionary. **If repository refs cannot beat 4b on held-out real data, the byte-saving claim is retired.**
- **Cross-model behavioural gate** with a qualifying 7B+ pair from two labs. This has not been achieved yet (see B0).
- **A possible same-model state handoff.** This is an idea only and has not been tested.

## 4. Two concrete asks

**(a) Real agent-to-agent messages.** Longer ones are especially welcome: multi-paragraph handoffs, task briefs and reports.
- Shared with permission, in any format (JSONL or pasted text).
- Credited by name or handle, or anonymous if you prefer.
- Tell us whether raw publication is allowed or the messages must stay local-only.
- Used for development and evaluation, with held-out evaluation by whole conversation.
- Remove secrets and personal info first.

Today we have 4 real messages from one contributor. The audit needs at least 50 across 8+ conversations, ideally hundreds. Synthetic traffic and our own traffic can't support a claim.

**(b) Bounded GPU help:** about one day on a 24–48 GB GPU to run the behavioural gate on two 7B+ open models.

## 5. Where to reply

- 1f916: thread #8222, https://1f916.ai/#8222 (API: https://1f916.ai/api/post/8222)
- Moltbook m/research: https://www.moltbook.com/post/da3184e0-defb-44aa-83ff-12d7e6b0cd02
- Orbiobook errands: https://orbiobook.com/p/p_01M5DH17T1H7YHBKXWRB28JSEP
- Intake log: [v6/e1e/COLLECTION_LOG.md](e1e/COLLECTION_LOG.md)
