"""Conservative local scrubber. Patterns are defence in depth, not an anonymity proof."""
import re
import unicodedata
import urllib.parse

PLACEHOLDER = "<REDACTED>"
EMAIL = re.compile(r'''(?:"[^"\r\n]+"|[\w.!#$%&'*+/=?^`{|}~-]+)@[\w-]+(?:\.[\w-]+)+''')
HANDLE = re.compile(r"(?<![\w@])@[\w][\w.-]*|(?<![\w/])u/[\w-]+", re.UNICODE)
PHONE = re.compile(r"(?<![\w])\+?\d[\d ()\t.-]{6,}\d(?![\w])")
URL = re.compile(r'''(?i)\b(?:[a-z][a-z0-9+.-]*://|www\.)[^\s<>"'`]+''')
KEY = re.compile(r"(?i)\b(?:sk-|gh[pousr]_|github_pat_|glpat-|xox[baprs]-|hf_|AKIA|ASIA|AIza)[A-Za-z0-9_/-]{8,}|\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")
PEM = re.compile(r"-----BEGIN [^-\r\n]+-----.*?(?:-----END [^-\r\n]+-----|\Z)", re.S)
OPAQUE = re.compile(r"(?<![\w])(?:[A-Fa-f0-9]{32,}|[A-Za-z0-9_+/=-]{40,})(?![\w])")
CREDENTIAL = re.compile(r'''(?ix)(?<![\w])(?:\\?["']?)[\w.-]*?(?:token|secret|password|passwd|passphrase|pwd|api[_-]?key|private[_-]?key|credentials?|cookie|authorization|authentication)(?:\\?["']?)\s*[=:]\s*''')
AUTH = re.compile(r"(?i)(?<![/\w])(?:Bearer|Basic)\s+[^\s<>]+")


def canonical_scan_text(text):
    """Inspect compatibility forms, escaped strings and percent encoding as well as literal text."""
    out = unicodedata.normalize("NFKC", text)
    out = "".join(c for c in out if unicodedata.category(c) != "Cf")
    for _ in range(3):
        decoded = urllib.parse.unquote(out)
        decoded = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m[1], 16)), decoded)
        decoded = re.sub(r"\\x([0-9a-fA-F]{2})", lambda m: chr(int(m[1], 16)), decoded)
        if decoded == out:
            break
        out = decoded
    return out


def _credentials(text):
    lines, out, deeper = text.splitlines(keepends=True), [], None
    for line in lines:
        ending = "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else "\r" if line.endswith("\r") else ""
        body = line[:-len(ending)] if ending else line
        indent = len(body) - len(body.lstrip(" \t"))
        if deeper is not None and body.strip() and indent > deeper:
            out.append(PLACEHOLDER + ending)
            continue
        deeper = None
        match = CREDENTIAL.search(body)
        if match:
            body = body[:match.end()] + PLACEHOLDER
            deeper = indent
        out.append(body + ending)
    return "".join(out)


def _phone(match):
    return PLACEHOLDER if 7 <= sum(c.isdigit() for c in match[0]) <= 18 else match[0]


def scrub(text, allow_handles=(), extra_terms=()):
    """Keep untouched bytes/code points unchanged. All URLs removed (including signed/token paths)."""
    allowed = {h.casefold() for h in allow_handles}
    text = PEM.sub(PLACEHOLDER, text)
    guarded = []
    for line in text.splitlines(keepends=True):
        normalized = canonical_scan_text(line)
        if normalized != line:
            try:
                scan(normalized, allow_handles)
            except ValueError:
                ending = "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else "\r" if line.endswith("\r") else ""
                line = PLACEHOLDER + ending
        guarded.append(line)
    text = "".join(guarded)
    text = _credentials(text)
    for pat in (URL, EMAIL, KEY, AUTH, OPAQUE):
        text = pat.sub(PLACEHOLDER, text)
    text = PHONE.sub(_phone, text)
    text = HANDLE.sub(lambda m: m[0] if m[0].casefold() in allowed else PLACEHOLDER, text)
    for term in sorted(set(extra_terms), key=len, reverse=True):
        if term:
            text = re.sub(re.escape(term), PLACEHOLDER, text, flags=re.I)
    return text


def scan(text, allow_handles=()):
    """Fail closed on detected leftovers, including encoded variants. Never print matched secrets."""
    allowed = {h.casefold() for h in allow_handles}
    for candidate in (text, canonical_scan_text(text)):
        for label, pattern in (("email", EMAIL), ("URL", URL), ("key-like string", KEY),
                               ("private key", PEM), ("opaque string", OPAQUE), ("authorization", AUTH)):
            if pattern.search(candidate):
                raise ValueError("Sensitive content remains: " + label + "; edit the input and run again.")
        if any(_phone(m) == PLACEHOLDER for m in PHONE.finditer(candidate)):
            raise ValueError("Sensitive content remains: phone-like number; edit the input.")
        if any(m[0].casefold() not in allowed for m in HANDLE.finditer(candidate)):
            raise ValueError("Sensitive content remains: handle; edit the input or explicitly allowlist it.")
        for line in candidate.splitlines():
            for m in CREDENTIAL.finditer(line):
                if line[m.end():] != PLACEHOLDER:
                    raise ValueError("Sensitive content remains: credential value; edit the input.")


def safe_display(text):
    """Escape terminal controls/bidi controls while leaving printable Unicode readable."""
    return "".join(c if c in "\n\t" or not unicodedata.category(c).startswith("C")
                   else "\\u%04x" % ord(c) for c in text)
