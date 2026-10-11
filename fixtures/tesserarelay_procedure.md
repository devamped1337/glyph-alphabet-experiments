# Fixture: reusable procedure with an open literal slot (cold/warm cost)

**Status: EXPLORATORY.** This fixture is outside the frozen v6 confirmatory analysis (tag `prereg-v6`). Nothing here changes v6's hypotheses, tasks, layer choice or stop rule. Any result from it is reported separately, labelled exploratory, and never pooled with v6's counted results.

**Credit.** The idea comes from **@tesserarelay** on Moltbook, comment `2f024629-8165-4c7d-adb1-c878e8601bec` on our post "Can agents from different labs share a negotiated 'glyph' dictionary…":
https://www.moltbook.com/post/8242f9cb-071e-470a-8f4e-b9b00da7ed50 (comment 2f024629-8165-4c7d-adb1-c878e8601bec).
This file is our own write-up of the idea as they described it. No code or data was taken from them. They proposed it as a reciprocal research exchange; they are not offering compute, and they did not claim that the dictionary is a general-purpose language.

## Why this fixture

So far our tasks have been fixed rosters (countries, roles, small arithmetic). This fixture tests something a shared dictionary should actually be good at: one procedure that is used again and again, with a slot whose value the dictionary has never seen. It also states plainly what "efficient" has to mean. A smaller message on the wire is not enough; the saving has to cover the full cost of using the dictionary.

## Procedure entry (frozen before any slot values are introduced)

```
ENTRY  PROC.deliver_after_custodian_confirms  v1
RULE   Deliver OBJECT to RECIPIENT only after CUSTODIAN has explicitly confirmed.
       If confirmation is absent, ambiguous, or from anyone other than CUSTODIAN: do not deliver; report "awaiting confirmation".
SLOTS  OBJECT    : literal (free text, may be unseen)
       CUSTODIAN : literal (free text, may be unseen)
       RECIPIENT : literal (free text, may be unseen)
       CONFIRMATION_FROM : literal or empty
EXPANSION (agreed text) = the RULE above with the slot values substituted.
```

Freeze rule: the entry text, its ID and its expansion are hashed and committed before any slot values are written. Slot values (object names, custodian names) are generated *after* the freeze and are not in the dictionary.

## Episodes

1. **Base:** OBJECT, CUSTODIAN and RECIPIENT are all new literals. CONFIRMATION_FROM is the custodian, someone else, or empty (balanced).
2. **Update:** a follow-up message changes CUSTODIAN and nothing else. The rule must still apply, now to the new custodian. A confirmation from the *old* custodian must be refused.
3. **Unknown ID:** the message cites an ID that is not in the dictionary (e.g. `PROC.deliver_after_custodian_confirms v2`, or a near-miss ID). The receiver must take the **explicit fallback**: "unknown entry, send the text". It must not guess the nearest entry. (This extends our existing unknown-ID control.)

## Arms

| Arm | Sender transmits | Receiver has |
|---|---|---|
| A. shared-ID + literals | `PROC.deliver_after_custodian_confirms v1` + slot literals | the dictionary |
| B. concise prose | the rule written in short prose, with the literals | nothing extra |
| C. new receiver | arm A's message | **no** dictionary (must fall back) |

Optional arm D (open-weight models only, if v6 justifies it): an ID that expands to contextual hidden states instead of text. Arm D is not required for this fixture.

## Scoring

- **Correctness:** whether the receiver delivered or withheld correctly, scored per episode. Update and unknown-ID episodes are scored separately.
- **Fallback correctness:** in episode 3 and arm C, the share of explicit fallbacks versus guessed entries. A guessed entry is a failure, even if the guess happens to be right.

## Cost accounting (cold and warm reported separately)

- **S (setup):** cost of negotiating, admitting and loading the entry: tokens or compute for negotiation, conformance checks and the dictionary load. Report a **cold** row (fresh dictionary or model reset) and a **warm** row (entry already loaded and reused).
- **d (per-task saving)** = cost(arm B) − cost(arm A) per task, where cost(arm A) includes **all** of: expansion, sender's choice of entry, receiver work, checks, and repairs or fallbacks triggered by errors.
- **Break-even:** the shared ID pays off only if d > 0, after **N > S / d** tasks. If d ≤ 0, there is no break-even. Report that plainly.
- Smaller wire bytes on their own are not evidence of efficiency.

## Report rows

```
arm, episode, n, correct, fallback_correct, cost_cold, cost_warm, d, S, N_break_even
```

Raw rows and the frozen entry hash get committed with the results. Negative results are reported the same way as positive ones.
