# Claude v5 review, round 2 (relayed by the user; summary, not verbatim)

- **Agrees** with GPT and Grok.
- **Disagrees with Grok Bot item 7.** On cross-model rows only, null_shufpair is about 0.23 (Qwen) / 0.15 (Smol), against no-message at about 0.25 / 0.16. So the null sits at the no-message level and the real adapter beats it.
- **Disagrees** that no-message is the right LOO baseline.
- **Retracts its own claims:** none as the LOO baseline; "22 rejected"; "~0.8 on covered places" (it is actually 0.93, on 2 places); and treating li=0 as an open question.
- **Missed by all four:**
  1. LOO copy bias. With the answer held out, the receiver names the other entity, so this is systematic exclusion. Use a slot-ablated baseline and 3+ candidates.
  2. t5 cannot be encoded: at emb with the last token, "not approved" == "approved".
  3. Under Rule A, accuracy could at best tie. The wire is 9 B for both glyph_id and id_text_expanded, vs 38–49 B for prose. Injection can only win on receiver compute, and the fair baseline is a pre-cached KV expansion.
  4. glyph = receiver_word_state largely by construction.
  5. Raw unsnapped t4 is 0.22 vs 0.12 snapped, CI [0.02, 0.45].
- **v6 PREREG:**
  - Fixed layers at about 40% and 60% plus an emb baseline, reading the state after the full slot value.
  - J-space sparse NNLS vs PCA vs random, on 7B only.
  - Tasks that need context: negation, paraphrase, definitions of 200+ tokens.
  - LOO with the entry removed, 3+ entities, forced choice, a slot-ablated baseline, and the transfer rate stated in advance.
  - A behaviour gate with 10+ independent planted bad entries plus a false-reject rate.
  - Coverage logged on every row.
  - Raw vs snapped.
  - Compute with no padding, vs uncached and cached expansion.
  - Count distinct items, use a ±0.05 margin, and run seeds only if they vary something real.
- **Stop rule:** if the contextual channel does not beat emb and cached expansion at equal accuracy on 7B, retire injection and keep the text repository with the behaviour gate.
