"""Local span redaction. Patterns are defence in depth, not an anonymity proof."""
import ast
import re
import unicodedata
import urllib.parse

from errors import KitError

PLACEHOLDER = "<REDACTED>"
EMAIL = re.compile(r'''(?<![\w.!#$%&'*+/=?^`{|}~-])(?:"[^"\r\n]+"|[\w.!#$%&'*+/=?^`{|}~-]+)@[\w-]+(?:\.[\w-]+)+''')
OBFUSCATED_EMAIL = re.compile(r"(?i)\b[\w.+-]+\s+(?:at|\[at\]|\(at\))\s+[\w-]+(?:\s+(?:dot|\[dot\]|\(dot\))\s+[\w-]+)+\b")
# Same decorator exemptions as the repository sanitiser, plus broadcast mentions.
HANDLE = re.compile(r"(?<![\w@])@(?!(?:property|staticmethod|classmethod|dataclass|abstractmethod|here|channel)(?![\w.]))[\w][\w.-]*|(?<![\w/])u/[\w-]+", re.UNICODE)
PHONE = re.compile(r"(?<![\w.])(?:\(\d{1,4}\)[ \t]*\d|\+?\d)[\d ()\t.-]{5,}\d(?!\w|\.\d)")
NUMERIC_CONTEXT = re.compile(r"(?<![\w.])(?:\d{4}-\d{2}-\d{2}|(?!\d{3}\.\d{3}\.\d{4}(?!\w|\.\d))\d+(?:\.\d+)+)(?!\w|\.\d)")
URL = re.compile(r'''(?i)\b(?:[a-z][a-z0-9+.-]*://|www\.)[^\s<>"'`]+|(?<![\w@.-])(?:[a-z0-9-]+\.)+(?:com|org|net|io|dev|ai|app|co|edu|gov|au|uk|me|info|xyz|invalid|example)\b(?:/[^\s<>"'`]*)?''')
KEY = re.compile(r"(?i)\b(?:sk_(?:live|test)_|sk-|gh[pousr]_|github_pat_|glpat-|xox[baprs]-|hf_|AKIA|ASIA|AIza)[A-Za-z0-9_/-]{8,}|\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")
PEM = re.compile(r"-----BEGIN [^-\r\n]+-----.*?(?:-----END [^-\r\n]+-----|\Z)", re.S)
SSH = re.compile(r"\b(?:ssh-rsa|ssh-ed25519|ecdsa-sha2-[\w-]+)[ \t]+[A-Za-z0-9+/=]+(?:[ \t]+[^\r\n]+)?")
UUID = re.compile(r"(?i)\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b")
# Do not treat ordinary long snake_case identifiers as secrets.
OPAQUE = re.compile(r"(?<![\w])(?:[A-Fa-f0-9]{32,}|[A-Za-z0-9+/=]{40,})(?![\w])")
CREDENTIAL = re.compile(r'''(?ix)(?<![\w])(?:\\?["']?)(?P<key>[\w.-]*?(?:token|secret[_-]?key|secret|password|passwd|passphrase|pass|pwd|api[_-]?key|private[_-]?key|session[_-]?(?:id|key)|credentials?|cookie|authorization|authentication))(?:\\?["']?)[ \t]*(?P<separator>==|!=|=|:)[ \t]*''')
USER_HOST = re.compile(r"(?<![\w@])[-\w.+]+@[-\w]+(?:\.[-\w]+)*(?![\w@])")
AUTH = re.compile(r"(?i)(?<![/\w])(?:Bearer|Basic)[ \t]+[^\s<>]+")
CLI_SECRET = re.compile(r'''(?i)(?:--(?:password|token|secret|api-key)(?:=|[ \t]+)|(?<!\w)-u[ \t]+)(?P<value>"[^"\r\n]*"|'[^'\r\n]*'|[^\s]+)''')
HOME = re.compile(r'''(?i)(?<![\w])(?:[A-Z]:[\\/](?:Users|Documents and Settings)[\\/][^\s/\\"'<>]+|/(?:home|Users)/[^\s/"'<>]+|/root(?=/|\b)|~/[^\s/"'<>]+)(?:[/\\][^\s"'<>]*)?''')
PATTERNS = (("URL", URL), ("email", EMAIL), ("user-host", USER_HOST), ("obfuscated-email", OBFUSCATED_EMAIL),
            ("key", KEY), ("private-key", PEM), ("ssh-key", SSH), ("uuid", UUID),
            ("authorization", AUTH), ("command-credential", CLI_SECRET), ("home-path", HOME))


def _canonical_with_spans(text):
    """Map decoded/compatibility characters back to exact source intervals."""
    chars = [(c, i, i + 1) for i, c in enumerate(text)]
    for _ in range(4):
        normal = []
        for c, start, end in chars:
            for d in unicodedata.normalize("NFKC", c):
                if unicodedata.category(d) != "Cf":
                    normal.append((d, start, end))
        value = "".join(c for c, _, _ in normal)
        out, pos = [], 0
        for m in re.finditer(r"(?:%[0-9a-fA-F]{2})+|\\u[0-9a-fA-F]{4}|\\x[0-9a-fA-F]{2}", value):
            out.extend(normal[pos:m.start()])
            token = m[0]
            if token.startswith("%"):
                data = urllib.parse.unquote_to_bytes(token)
                try:
                    decoded = data.decode("utf-8")
                except UnicodeDecodeError:
                    decoded = None
                if decoded is not None:
                    byte = 0
                    for c in decoded:
                        count = len(c.encode("utf-8"))
                        out.append((c, normal[m.start() + 3 * byte][1], normal[m.start() + 3 * (byte + count) - 1][2]))
                        byte += count
                else:
                    out.extend((c, normal[m.start()][1], normal[m.end() - 1][2]) for c in urllib.parse.unquote(token))
            else:
                out.append((chr(int(token[2:], 16)), normal[m.start()][1], normal[m.end() - 1][2]))
            pos = m.end()
        out.extend(normal[pos:])
        if out == chars:
            break
        chars = out
    return "".join(c for c, _, _ in chars), [(a, b) for _, a, b in chars]


def canonical_scan_text(text):
    return _canonical_with_spans(text)[0]



def _dotted_decorator(text, match):
    """Require a valid decorator line followed by a declaration, allowing decorator chains."""
    token = match[0]
    if not token.startswith("@") or "." not in token:
        return False
    line_start = text.rfind("\n", 0, match.start()) + 1
    if text[line_start:match.start()].strip():
        return False
    lines = text[line_start:].splitlines()
    for index, line in enumerate(lines):
        value = line.strip()
        if not value:
            continue
        if value.startswith("@"):
            try:
                # Parse syntax only: never evaluate a decorator or its arguments.
                ast.parse(value + "\ndef _glyph_placeholder():\n    pass\n")
            except (SyntaxError, ValueError, RecursionError):
                return False
            continue
        return index > 0 and bool(re.match(r"(?:async\s+def|def|class)\s+", value))
    return False


def _nonliteral_credential(tail):
    # Environment lookups contain a variable name, not the secret value itself.
    lookup = re.match(r"""(?:os\.environ\s*\[\s*(['"])[\w.-]+\1\s*\]|os\.getenv\s*\(\s*(['"])[\w.-]+\2\s*\))""", tail)
    return bool(lookup and re.fullmatch(r"[\s,}\]]*", tail[lookup.end():]))


def _type_hint(tail):
    return bool(re.fullmatch(r"(?:str|bytes|int|float|bool|list|dict|set|tuple|object|Optional|Union|Literal)(?:\[[\w\[\], .|]+\])?(?:[ \t]*\|[ \t]*(?:None|str|bytes))*[ \t]*(?:#.*)?", tail))


def _credential_spans(text):
    lines = text.splitlines(keepends=True)
    offset, block_indent = 0, None
    for line in lines:
        body = line.rstrip("\r\n")
        indent = len(body) - len(body.lstrip(" \t"))
        if block_indent is not None:
            if not body.strip():
                offset += len(line)
                continue
            if indent > block_indent:
                if body[indent:] != PLACEHOLDER:
                    yield offset + indent, offset + len(body)
                offset += len(line)
                continue
            block_indent = None
        for m in CREDENTIAL.finditer(body):
            start = m.end()
            tail = body[start:]
            # Empty YAML containers and Python control-flow headers have no scalar secret.
            if not tail or re.match(r"(?:#|//)", tail):
                continue
            if re.fullmatch(r"[|>][+-]?[ \t]*(?:#.*)?", tail):
                block_indent = indent
                continue
            if m[0].rstrip().endswith(":") and re.match(r"^\s*(?:if|elif|while)\s+", body) and ":" not in body[:m.start()]:
                continue
            if m["separator"] == ":" and not body[:m.start()].strip() and m[0].lstrip()[0] not in "\\\"'" and _type_hint(tail):
                continue
            if _nonliteral_credential(tail):
                continue
            if tail.startswith(('\\"', "\\'")):
                close = body.find(tail[:2], start + 2)
                start += 2
                end = close if close >= 0 else len(body)
            elif tail[0] in "\"'":
                quoted = re.match(r'''"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*' '''.rstrip(), tail)
                end = start + quoted.end() - 1 if quoted else len(body)
                start += 1
            elif m["key"].casefold() in ("authorization", "authentication"):
                end = len(body)
            elif tail.startswith(PLACEHOLDER):
                continue
            else:
                scalar = re.match(r"[^\s,;\]}]+", tail)
                if scalar is None:
                    continue
                end = start + scalar.end()
            if body[start:end] != PLACEHOLDER:
                yield offset + start, offset + end
        offset += len(line)


def _findings(text, allow_handles=(), extra_terms=()):
    allowed = {h.casefold() for h in allow_handles}
    for rule, pattern in PATTERNS:
        for m in pattern.finditer(text):
            if rule == "command-credential":
                if m["value"] != PLACEHOLDER:
                    yield m.start("value"), m.end("value"), rule
            else:
                yield m.start(), m.end(), rule
    for m in OPAQUE.finditer(text):
        token = m[0]
        # Hex identifiers and mixed-class base64-like tokens; not long plain words.
        if (re.fullmatch(r"[a-fA-F0-9]+", token) and any(c.isdigit() for c in token) and any(c.isalpha() for c in token)) or sum((any(c.islower() for c in token), any(c.isupper() for c in token), any(c.isdigit() for c in token), any(c in "+/=" for c in token))) >= 3:
            yield m.start(), m.end(), "opaque-token"
    # Split around dates, versions and IP addresses so they cannot be swallowed by a phone match.
    pos = 0
    for protected in list(NUMERIC_CONTEXT.finditer(text)) + [None]:
        end = protected.start() if protected else len(text)
        for m in PHONE.finditer(text[pos:end]):
            if 7 <= sum(c.isdigit() for c in m[0]) <= 18:
                yield pos + m.start(), pos + m.end(), "phone"
        pos = protected.end() if protected else len(text)
    for m in HANDLE.finditer(text):
        if m[0].casefold() not in allowed and not _dotted_decorator(text, m):
            yield m.start(), m.end(), "handle"
    for a, b in _credential_spans(text):
        yield a, b, "credential-value"
    for term in sorted(set(extra_terms), key=len, reverse=True):
        if term:
            for m in re.finditer(re.escape(term), text, flags=re.I):
                yield m.start(), m.end(), "extra-term"


def scrub(text, allow_handles=(), extra_terms=()):
    """Redact matched source spans; preserve every untouched source character and line ending."""
    canonical, mapping = _canonical_with_spans(text)
    spans = [(a, b) for a, b, _ in _findings(text, allow_handles, extra_terms)]
    spans += [(mapping[a][0], mapping[b - 1][1]) for a, b, _ in _findings(canonical, allow_handles, extra_terms)]
    merged = []
    for a, b in sorted(spans):
        if merged and a < merged[-1][1]:
            merged[-1] = (merged[-1][0], max(b, merged[-1][1]))
        else:
            merged.append((a, b))
    out, pos = [], 0
    for a, b in merged:
        out.extend((text[pos:a], PLACEHOLDER))
        pos = b
    out.append(text[pos:])
    return "".join(out)


def scan(text, allow_handles=(), extra_terms=()):
    """Independently refuse detected leftovers without showing matched content."""
    for candidate in (text, canonical_scan_text(text)):
        first = next(_findings(candidate, allow_handles, extra_terms), None)
        if first:
            raise KitError(first[2], "Sensitive content remains; edit a private copy and run again.")


def safe_display(text):
    """Escape terminal controls/bidi controls while leaving printable Unicode readable."""
    return "".join(c if c in "\n\t" or not unicodedata.category(c).startswith("C")
                   else "\\u%04x" % ord(c) for c in text)
