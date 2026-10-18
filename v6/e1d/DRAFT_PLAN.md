# E1d: design sketch (DRAFT, not frozen)

Status: draft for discussion only. No code, no Kaggle runs, no GPT or Grok review yet. Nothing here is pre-registered. Every number is a placeholder until measured or justified as below.

## 1. Motivation
E1c T1 (report at 8a9a819) was NOT MET only on break-even.
- Accuracy was non-inferior in both directions (hybrid 960/960 and 958/960; prose 957 and 950).
- Coverage was 93–95%.
- Payload saving, fallback included, was 83–85%.
- No wrong ID was accepted (24/24 rejected).
- Break-even was 1,142 and 1,114 messages, against a fixed 1,000-message line. The cost came from a 166 KB dictionary, at about 147 B saved per message.

A fixed message count does not say whether the scheme pays off in a realistic deployment. E1d replaces it with a pre-declared workload criterion, as GPT proposed.

## 2. Carried over from E1c (unchanged unless noted)
- Mechanism: verified ID with prose fallback. The sender picks an entry ID, a verifier checks it, and on rejection the message goes as prose.
- Models: Qwen2.5-7B and Falcon3-7B, both directions, on a free Kaggle T4 (4-bit). No other models.
- Gates kept, required in both directions:
  1. accuracy non-inferiority: lower 95% bound of hybrid − prose > −0.05, paired bootstrap stratified by family and clustered by entry;
  2. ID coverage ≥ 85%;
  3. wrong IDs accepted: ≤ 1% of picks. The E1c diagnostic is promoted to a gate; the threshold is open (Q4).
- Process: a D-stage on the dev book measures costs, then freeze tags plus check_freeze, then one TEST run. Same supervisor, ledger and `.done` rules.

## 3. New primary criterion: total bytes under a declared workload
- **Workload W**, fixed before any E1d run: number of agents, conversations, messages per conversation, dictionary copies, and update schedule (how often and how large).
- **Justification:** W comes from a documented conservative forecast, written down with its sources and reasoning before seeing results. It is not tuned to make the criterion pass. "Conservative" means low traffic and frequent updates, which both hurt the ID scheme.
- **Cost under W:**
  - total_hybrid = dictionary distribution (every copy) + updates + IDs + verification traffic + fallback prose;
  - total_prose = prose for the same messages.
- **Primary:** saving S = 1 − total_hybrid / total_prose. Required: S ≥ 20% and a one-sided 95% lower bound > 20%, in both directions. The bound uses the same entry-clustered bootstrap, applied to the per-message terms.
- **Secondary only:** the break-even message count and a lifetime-cost curve (bytes vs messages, both arms).

## 4. Byte accounting (credit: swift-lantern, 1f916 #8349)
(a) **Every byte surface is named and counted separately.**
- Disk: dictionary stored per agent.
- Transmitted, one-off: dictionary distribution and updates.
- Transmitted, per conversation: setup or handshake, if any.
- Transmitted, per message: ID, verification, and fallback.
- The primary criterion states which surfaces it sums. Disk is reported but not summed with transmitted bytes unless W says so.

(b) **The read-time of any growing-store denominator is named.** Wherever a ratio uses a store that grows (dictionary, ledger, history), the report says when it was read: at freeze, at run start, or at run end. Example: "dictionary size read at freeze, 240 entries plus neighbours".

## 5. Measure, don't assume (D1 lesson)
D1 ran out of budget because its time estimate was assumed. For E1d:
- every cost input (bytes per ID, verifier tokens and bytes, fallback rate, dictionary size, GPU-s per message) is measured in a D-stage and recorded with its source row;
- every number in the plan and report says where it came from: measured (stage plus file), declared (W), or derived (formula).
- The GPU cap is set from D-stage measurements plus a stated margin.

## 6. Open questions (for Stefan, GPT, Grok)
1. Is a smaller dictionary worth testing as an arm? For example, top-k frequent entries or no neighbours. This is a hypothesis from E1c, not a claim. The arm would need its own coverage gate.
2. What forecast source justifies W, and who signs it off before freeze?
3. Should verification traffic count when the verifier runs locally at the receiver?
4. What wrong-ID threshold, and should it be on the Clopper–Pearson upper bound?
5. Is 20% the right primary margin? E1c's payload saving was 83–85%, but dictionary distribution dominates at low traffic.
6. Should E1d reuse the E1c TEST book (no longer fresh) or generate a new one?
7. Is one D-stage enough to measure update costs, or is a simulated update needed?

Falcon3-7B-Instruct results will be produced using artificial intelligence technology from the Technology Innovation Institute (TII Falcon License).
