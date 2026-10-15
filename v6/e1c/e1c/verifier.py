"""Stateless verifier (PREREG_E1c §4). A fresh call that sees ONLY the original prose message (never the
candidates, the pick or any ID) and writes the rule parameters in a strict one-line format. Deterministic code then
compares that spec with the picked entry. No model judges the match."""
import re

SYS_VERIFY = ("You read one message that states a pricing rule and write down its parameters. Compute any number "
              "that is stated relative to another. Reply with exactly one line in the format given, and nothing else.")
FMT = dict(
    F1="GROUP=<name of the membership scheme> MEMBER=<credits per unit for members> NONMEMBER=<credits per unit for non-members>",
    F2="GIVER=<role name of whoever hands over the items> GIVER_RATE=<credits per item billed to the giver> "
       "TAKER=<role name of whoever takes the items> TAKER_RATE=<credits per item billed to the taker>")
KEYS = dict(F1=("GROUP", "MEMBER", "NONMEMBER"), F2=("GIVER", "GIVER_RATE", "TAKER", "TAKER_RATE"))
INTS = {"MEMBER", "NONMEMBER", "GIVER_RATE", "TAKER_RATE"}

def verifier_parts(fam, message):
    """(system, prefix_user, suffix_user). Depends only on the family and the prose message."""
    return SYS_VERIFY, "", f"Message:\n{message}\n\nReply in exactly this format:\n{FMT[fam]}"

_TOK = re.compile(r"\b([A-Z_]+)\s*=\s*(.*?)(?=\s+[A-Z_]+\s*=|$)")

def parse_spec(fam, txt):
    """-> (spec dict | None, reason). Uses the first line that contains every required key exactly once."""
    for line in txt.strip().splitlines():
        kv = {}; dup = False
        for k, v in _TOK.findall(line.strip()):
            if k in kv: dup = True
            kv[k] = v.strip().strip(".,;").strip()
        if not all(k in kv for k in KEYS[fam]): continue
        if dup: return None, "duplicate_key"
        out = {}
        for k in KEYS[fam]:
            v = kv[k].strip("<>\"' ")
            if k in INTS:
                m = re.fullmatch(r"(-?\d+)(?:\s*credits?.*)?", v)
                if not m: return None, f"non_integer_{k}"
                out[k] = int(m.group(1))
            else:
                v = re.sub(r"^(the|a|an)\s+", "", v.lower()).strip()
                if not v: return None, f"empty_{k}"
                out[k] = v
        return out, "ok"
    return None, "format"

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
