I checked the code and independently recomputed the headline accuracies from both prediction files. Bot's main conclusion holds: this implementation hasn't earned the extra machinery of vector injection. But I found several important qualifications.

The biggest one: v5 selected the embedding layer. The frozen depth is li=0, which the code maps to emb—before contextual processing. It also reads only the last token of each slot value. That severely limits what this run can demonstrate. For example, reading the final token of "approved" and "not approved" at the embedding layer cannot capture the preceding negation. Likewise, the final word of a geographical clue isn't a contextual representation of the place it describes. So this is chiefly an embedding/codebook experiment. It hasn't tested the proposed contextual J-space channel.

The place result is mostly dictionary rejection—and we can recover the missing coverage without another model run. Reconstructed original-message coverage: Qwen place messages covered 14/110, correct among covered 13/14 (92.9%), overall 11.8%; SmolLM2 28/210, 26/28 (92.9%), overall 12.4%. Only Lyon and Spain survived negotiation. Those conditional results are small and restricted to two places; they don't establish broad transfer. But describing the entire collapse as poor injection would misdiagnose it.

There's also a counting correction: 23 of 93 entries were ultimately rejected, leaving 70. Twenty-two disappeared in round zero, then Paris disappeared in round one.

Sender independence is largely built into the snapped channel. I reproduced 638/646 matching sender predictions for Qwen and 1040/1056 for SmolLM2. But the code explains why: after selecting an entry, it retrieves that entry's fixed shared vector. Whenever both senders choose the same ID, the receiver receives the same vector. That establishes the behaviour of this lookup architecture; it doesn't establish that activation transfer generally cannot work.

The strongest negative result is the fair ID comparison. For Qwen, using the same selected IDs: Who acted: injection 85.5%, prose expansion 100%. Who acted first: injection 94.5%, prose expansion 100%. Status: injection 62.5%, prose expansion 75%. Same transmitted ID payload; different receiver representation. Ordinary text expansion wins.

The gate needs a more precise verdict too. Six planted rejections represent two bad-entry designs tested at three depths. Meanwhile, only 4/141 held-out entry/depth cases passed. That shows weak generalization to held-out entries—not a demonstrated selective validator.

For the pending 7B run, I'd want embedding and contextual-layer results reported separately, raw transfer separated from snapped lookup, and coverage reconstructed before interpreting failures. Every receiver prompt here was padded to 64 tokens, so v5 also hasn't demonstrated a receiver-compute saving.

Your shared repository remains a viable protocol idea. What v5 removed is the evidence that injecting its vectors improves on expanding its IDs into text. That's a useful, concrete result—even with rocket parts scattered everywhere.
