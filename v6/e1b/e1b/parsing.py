"""Frozen parsing rules (PREREG_E1b §6 + Amendment A1.5). Do not edit after the freeze without an amendment."""
import re

def parse_letter(txt):
    """Probe / sender replies. First standalone letter A-D is taken. No letter, a letter outside A-D, or two
    or more DIFFERENT standalone letters -> invalid (counted wrong). Returns (letter|None, path)."""
    t = txt.strip()
    letters = re.findall(r"(?<![A-Za-z])([A-Za-z])(?![A-Za-z])", t)
    caps = [l for l in letters if l.isupper()]
    if not caps: return None, "invalid_none"
    if caps[0] not in "ABCD": return None, "invalid_letter"
    if len({c for c in caps if c in "ABCD"}) > 1 or any(c not in "ABCD" for c in caps):
        return None, "invalid_multiple"
    return caps[0], "letter"

_ANS = re.compile(r"answer\s*[:=]\s*\**\s*(-?\d[\d,]*|unknown)", re.I)

def parse_answer(txt):
    """Arithmetic replies. Last 'Answer:' line taken; if none, last integer; 'Answer: UNKNOWN' -> abstention
    (not correct, reported separately); >=2 conflicting Answer lines -> last used and flagged; nothing
    parseable -> invalid (counted wrong). Returns dict(pred, abstained, path, conflict)."""
    am = [a.replace(",", "") for a in _ANS.findall(txt)]
    if am:
        a = am[-1]; conflict = len({x.lower() for x in am}) > 1
        if a.lower() == "unknown": return dict(pred="UNKNOWN", abstained=True, path="answer_line", conflict=conflict)
        return dict(pred=str(int(a)), abstained=False, path="answer_line", conflict=conflict)
    ints = re.findall(r"-?\d+", txt.replace(",", ""))
    if ints: return dict(pred=str(int(ints[-1])), abstained=False, path="last_integer", conflict=False)
    return dict(pred=None, abstained=False, path="invalid", conflict=False)

def score_answer(parsed, gold):
    """Correct iff pred == gold. Abstention and invalid are not correct."""
    return parsed["pred"] is not None and not parsed["abstained"] and parsed["pred"] == str(gold)


# ---------------------------------------------------------------- A10 (DRAFT): sender reply handling
# Candidate IDs are rendered "F1-1434@v1#ed92089f" (families F1, F2, F3L). A reply such as "B) F1" (letter, then the
# start of the candidate ID, cut at the frozen 4-token limit) was rejected by parse_letter because the "F" of "F1"
# reads as a second standalone letter. A10 removes candidate-ID fragments first, then applies parse_letter UNCHANGED:
# a bare "F1" -> invalid_none; two different option letters -> invalid_multiple; no broad first-letter rule.
_ID_FRAG = re.compile(r"(?<![A-Za-z0-9])F(?:1|2|3L)(?:-\d*)?(?:@v?\d*)?(?:#[0-9a-f]*)?(?![A-Za-z0-9])")

def parse_letter_a10(txt):
    """A10 sender parser: parse_letter after deleting candidate-ID fragments (F1 / F2 / F3L, optionally
    -NNNN@vN#hash, possibly truncated). Returns (letter|None, path)."""
    return parse_letter(_ID_FRAG.sub(" ", txt))
