"""Protocol: dictionary with version/hash check, delegate expansion, sender selection, receiver prompts
(PREREG_E1b §1, §9 B2/B3, A1.6). The case text reaches the receiver identically in every arm."""
import random, re
from .cases import render_message, render_label

SYS_ARITH = ("You apply shared dictionary rules to cases. Show brief working, then finish with a final line of the "
             "form 'Answer: <integer>'. If the information given does not determine the answer, finish with 'Answer: UNKNOWN'.")
SYS_PROBE = "You answer multiple-choice questions about a rule. Reply with a single letter: A, B, C or D."
SYS_SENDER = ("You route a message to the dictionary entry that states exactly the same rule. "
              "Reply with a single letter: A, B, C or D.")
MSG_RE = re.compile(r"^\s*([A-Z0-9]+-[0-9A-Z]+)@v(\d+)#([0-9a-f]{8})\s*$")

def framed_id(e):
    """Payload on the wire for the ID arm: ID@version#hash8."""
    return f"{e['id']}@v{e['ver']}#{e['hash'][:8]}"

class Dictionary:
    """Receiver-side delegate's local verified copy."""
    def __init__(self, book):
        self.E = book["entries"]
    def resolve(self, msg):
        """Deterministic check before any model call: exists, version, hash. -> (entry|None, reason)."""
        m = MSG_RE.match(msg)
        if not m: return None, "malformed"
        eid, ver, h = m.group(1), int(m.group(2)), m.group(3)
        e = self.E.get(eid)
        if e is None or e.get("kind") == "planted": return None, "unknown_id"
        if e["ver"] != ver: return None, "stale_version"
        if e["hash"][:8] != h: return None, "hash_mismatch"
        return e, "ok"

# ---------------------------------------------------------------- receiver prompts: (prefix_user, suffix_user)
def rule_block(text): return f"Rule:\n{text}\n\n"
def case_block(case): return f"Case: {case['text']}"

def receiver_parts(cond, entry, case, book=None, msg=None, ablate_answer=False):
    """Return (system, prefix_user, suffix_user, payload_str). prefix holds the rule (cacheable), suffix the case."""
    suffix = case_block(case) + ("\nAnswer:" if ablate_answer else "")
    if cond in ("id_oracle", "id_selected", "direct_text"):
        # id arms: delegate expanded the ID to entry['text']; direct_text sends that exact text -> byte-identical
        prefix = rule_block(entry["text"])
        payload = framed_id(entry) if cond != "direct_text" else entry["text"]
    elif cond == "prose":
        m = msg if msg is not None else render_message(entry); prefix = rule_block(m); payload = m
    elif cond == "id_raw":
        payload = framed_id(entry); prefix = rule_block(payload)
    elif cond == "placebo":
        txt = entry["text"]
        for k, v in entry["sem"].items():
            if isinstance(v, int) and not isinstance(v, bool): txt = re.sub(rf"\b{v}\b", "___", txt)
        prefix = rule_block(txt); payload = txt
    elif cond == "unknown":
        prefix, payload = "", msg
    else: raise ValueError(cond)
    return SYS_ARITH, prefix, suffix, payload

def probe_parts(entry_text, probe, with_text=True):
    opts = "\n".join(f"{L}) {o}" for L, o in zip("ABCD", probe["options"]))
    prefix = rule_block(entry_text) if with_text else ""
    return SYS_PROBE, prefix, f"Question: {probe['question']}\n{opts}\nAnswer with a single letter."

# ---------------------------------------------------------------- sender (4-way selection, not search)
def sender_view(book, eid, rng):
    """What the sender sees: the original message + 4 candidates (true + 3 confusable neighbours), shuffled."""
    E = book["entries"]; cands = [eid] + book["neighbours"][eid]; rng.shuffle(cands)
    msg = render_message(E[eid])
    lines = [f"{L}) {framed_id(E[c])}  {render_label(E[c])}" for L, c in zip("ABCD", cands)]
    user = f"Message:\n{msg}\n\nCandidates:\n" + "\n".join(lines) + "\n\nWhich candidate states exactly the same rule?"
    return dict(message=msg, candidates=cands, labels=[render_label(E[c]) for c in cands], user=user,
                prep_bytes=len("\n".join(lines).encode()))

def sender_parts(view): return SYS_SENDER, "", view["user"]

# ---------------------------------------------------------------- bytes (A1.6)
def bytes_record(cond, payload, case, sender_wire_bytes=0):
    """payload = rule part only; whole-exchange = payload + identical case text + sender-side wire bytes."""
    p = len(payload.encode("utf-8")); c = len(case["text"].encode("utf-8"))
    return dict(payload_bytes=p, case_bytes=c, sender_wire_bytes=sender_wire_bytes,
                whole_exchange_bytes=p + c + sender_wire_bytes)
