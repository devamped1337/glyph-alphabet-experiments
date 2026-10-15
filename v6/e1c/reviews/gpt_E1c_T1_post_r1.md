# GPT review: E1c T1 forum post r1

Request: tone and accuracy of the T1 forum post draft. Reply verbatim:

NEEDS EDITS

The upbeat tone is fair: three criteria passed in both directions, and the post clearly acknowledges the frozen NOT MET verdict. A few edits are needed to avoid overstating the result.

1. Correct the wrong-ID denominator.
“0 of 480 wrong IDs got through” implies 480 wrong IDs were tested. There were 480 trials and 24 wrong picks.

Replace with:
“Across 480 sender trials (240 per sender), the senders made 24 wrong picks. The verifier rejected all 24; none was accepted. It also rejected 4 correct picks.”

2. Fix the proposed route to passing break-even.
More traffic can eventually amortize the dictionary, but it cannot lower the break-even message count for the same dictionary and per-message savings.

Replace the hypothesis sentence with:
“A hypothesis for next time, not a claim: a smaller dictionary or greater savings per message could bring break-even below 1,000 messages.”

3. Make the opening reflect the full verdict.
“The communication works” is broad for a result that missed its preregistered target.

Suggested opening:
“E1c T1 is in: strong held-out accuracy and payload savings, with one preregistered target missed.”

4. Separate analysis acceptance from experimental success.
“GPT reviewed the analysis and accepted it” could sound like endorsement of an overall pass.

Replace with:
“GPT reviewed and accepted the T1 report at commit 8a9a819, including its NOT MET verdict.”

5. Keep the byte claim explicitly about payload.
The existing bullet correctly says “payload bytes.” Make its relationship to dictionary overhead explicit:

“83–85% fewer message-payload bytes, counting prose fallbacks; the upfront dictionary cost is accounted for separately in break-even.”

6. Verify the hardware and cost wording.
The supplied context supports 3.22 GPU-h against a 5.0 GPU-h cap, but does not establish “single run,” “free,” or “T4.” Keep those only if documented. Otherwise use:
“The run used 3.22 GPU-h, inside the frozen 5.0 GPU-h cap.”

The remaining numbers are consistent with the supplied results, allowing for rounding. The stated break-even counts should come from the report’s unrounded savings; the rounded bytes-per-message figures cannot reproduce them exactly.

Keep the D2 correction, the explicit statement that break-even failed in both directions, and the required TII line unchanged. No personal information appears in the draft.


## Edits applied
- 1, 2, 4, 5: applied as suggested.
- 3: partly applied. The opening keeps "the communication works" (the owner asked for that framing) and now also states that one pre-registered target was missed.
- 6: not changed. The single run, free Kaggle T4 and 3.2 GPU-h are documented in T1_REPORT.md.

## Final posted text

E1c T1 result is in: the communication works, though we missed one pre-registered target.

On the held-out TEST set (240 entries, 960 messages each way), two different 7B models (Qwen2.5-7B and Falcon3-7B) talked to each other through verified dictionary IDs, with prose as the fallback:

- Accuracy matched or beat plain prose in both directions: Qwen→Falcon 960/960 vs 957/960 for prose; Falcon→Qwen 958/960 vs 950/960. Non-inferiority passed in both directions (lower 95% bounds 0.000 and +0.003 vs a −0.05 margin).
- 83–85% fewer message payload bytes, counting the prose fallbacks. The upfront dictionary cost is counted separately, in break-even (below).
- IDs were used for 93–95% of messages.
- 0 wrong IDs got through. Across 480 sender trials (240 per sender) the senders made 24 wrong picks, and the verifier rejected all 24. It also rejected 4 correct picks, which then went out as prose.
- Single run on a free T4, 3.2 GPU-h, inside the frozen 5.0 h cap. GPT reviewed and accepted the T1 report, including its NOT MET verdict.

The official pre-registered verdict is NOT MET, on one criterion: break-even. Our own rule says the shared dictionary must pay for itself within 1,000 messages. It took 1,142 (Qwen→Falcon) and 1,114 (Falcon→Qwen), because the dictionary is 166 KB and each message saves about 147 B. Three of the four criteria passed in both directions; break-even failed in both. We set that line before running, so we won't move it after the fact. A hypothesis for next time, not a claim: a smaller dictionary or bigger savings per message could bring break-even under 1,000 messages.

Correction: in the D2 update I gave break-even as 56/44 messages. That came from a 10-entry dev dictionary and doesn't carry over to full scale. That was my reporting mistake.

Full report: https://github.com/devamped1337/glyph-alphabet-experiments/blob/8a9a819/v6/e1c/T1_REPORT.md

Falcon3-7B-Instruct results were produced using artificial intelligence technology from the Technology Innovation Institute (TII Falcon License).
