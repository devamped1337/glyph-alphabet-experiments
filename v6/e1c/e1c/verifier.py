"""Stateless verifier (PREREG_E1c §4). A fresh call that sees ONLY the original prose message (never the
candidates, the pick or any ID) and writes the rule parameters in a strict one-line format. Deterministic code then
compares that spec with the picked entry. No model judges the match."""
import re

SYS_VERIFY = ("You read one message that states a pricing rule and write down its parameters. Compute any number "
              "that is stated relative to another. Reply with exactly one line in the format given, with single-word names and plain integers, and nothing else.")
FMT = dict(
    F1="GROUP=<name of the membership scheme> MEMBER=<credits per unit for members> NONMEMBER=<credits per unit for non-members>",
    F2="GIVER=<role name of whoever hands over the items> GIVER_RATE=<credits per item billed to the giver> "
       "TAKER=<role name of whoever takes the items> TAKER_RATE=<credits per item billed to the taker>")
KEYS = dict(F1=("GROUP", "MEMBER", "NONMEMBER"), F2=("GIVER", "GIVER_RATE", "TAKER", "TAKER_RATE"))
INTS = {"MEMBER", "NONMEMBER", "GIVER_RATE", "TAKER_RATE"}

def verifier_parts(fam, message):
    """(system, prefix_user, suffix_user). Depends only on the family and the prose message."""
    return SYS_VERIFY, "", f"Message:\n{message}\n\nReply in exactly this format:\n{FMT[fam]}"

# Registered grammar (r2, GPT r1 #5): the WHOLE reply, after stripping leading/trailing whitespace, must be exactly
# one line: the family's keys in the registered order, single-word names ([A-Za-z]+), plain integers, separated by
# spaces/tabs. Anything else (extra lines, extra keys, duplicate keys, units, explanations, punctuation) is a format
# error -> fallback to prose.
_W, _I, _SP = r"([A-Za-z]+)", r"(-?[0-9]+)", r"[ \t]+"   # r3: ASCII digits only ([0-9], not \d)
GRAMMAR = dict(F1=re.compile(rf"GROUP={_W}{_SP}MEMBER={_I}{_SP}NONMEMBER={_I}"),
               F2=re.compile(rf"GIVER={_W}{_SP}GIVER_RATE={_I}{_SP}TAKER={_W}{_SP}TAKER_RATE={_I}"))

def parse_spec(fam, txt):
    """-> (spec | None, reason). reason in {ok, format}. Strict full-response grammar (see GRAMMAR)."""
    m = GRAMMAR[fam].fullmatch(txt.strip())
    if not m: return None, "format"
    out = {}
    for k, v in zip(KEYS[fam], m.groups()): out[k] = int(v) if k in INTS else v.lower()
    return out, "ok"

def expected_spec(e):
    s = e["sem"]
    if e["fam"] == "F1": return dict(GROUP=e["g"].lower(), MEMBER=s["mem"], NONMEMBER=s["non"])
    if e["fam"] == "F2": return dict(GIVER=e["x"].lower(), GIVER_RATE=s["xr"], TAKER=e["y"].lower(), TAKER_RATE=s["yr"])
    raise ValueError(e["fam"])

def matches(spec, e):
    """Deterministic comparison of the verifier's spec with the PICKED entry (every field must be equal)."""
    if spec is None: return False, "no_spec"
    exp = expected_spec(e); bad = [k for k in exp if spec.get(k) != exp[k]]
    return (not bad), ("ok" if not bad else "mismatch:" + ",".join(bad))
