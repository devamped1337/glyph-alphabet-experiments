"""Entries, typed-template grammar and deterministic matching (SPEC sections 4-6)."""
import re

from .canon import E1EError, canonical, sha256_hex

ID_RE = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}\Z")
NAME_RE = re.compile(r"[a-z][a-z0-9_]{0,31}\Z")
WORD_RE = re.compile(r"[A-Za-z0-9_.-]+\Z")
INT_RE = re.compile(r"-?(0|[1-9][0-9]{0,17})\Z")
TYPES = ("int", "word", "text")
KINDS = ("literal", "template")
PROVS = ("synthetic", "glyph_own_dev", "real_dev")  # source class of the material an entry was built from
MAX_BODY_CHARS = 16384
MAX_PARAMS = 8
MATCH_BUDGET = 20000
ENTRY_KEYS = {"id", "v", "kind", "body", "params", "prov", "digest"}


def entry_digest(e):
    """Digest over every semantic field, including the template parameter schema."""
    core = {k: e[k] for k in ("id", "v", "kind", "body", "params", "prov")}
    return sha256_hex(canonical(core))


def make_entry(id, v, body, params=None, kind=None, prov="synthetic"):
    params = [] if params is None else [dict(name=n, type=t) for n, t in params]
    kind = kind or ("template" if params else "literal")
    e = {"id": id, "v": v, "kind": kind, "body": body, "params": params, "prov": prov}
    e["digest"] = entry_digest(e)
    validate_entry(e)
    return e


def validate_entry(e):
    if not isinstance(e, dict) or set(e) != ENTRY_KEYS:
        raise E1EError("E_SCHEMA", "entry must have exactly keys " + ",".join(sorted(ENTRY_KEYS)))
    if not isinstance(e["id"], str) or not ID_RE.match(e["id"]):
        raise E1EError("E_SCHEMA", f"bad id {e['id']!r}")
    if type(e["v"]) is not int or not 1 <= e["v"] <= 2**31:
        raise E1EError("E_SCHEMA", "bad entry version")
    if e["kind"] not in KINDS or e["prov"] not in PROVS:
        raise E1EError("E_SCHEMA", "bad kind/prov")
    if not isinstance(e["body"], str) or not 0 < len(e["body"]) <= MAX_BODY_CHARS:
        raise E1EError("E_SCHEMA", "bad body")
    if not isinstance(e["params"], list) or len(e["params"]) > MAX_PARAMS:
        raise E1EError("E_SCHEMA", "bad params")
    for p in e["params"]:
        if (not isinstance(p, dict) or set(p) != {"name", "type"} or not isinstance(p["name"], str)
                or not NAME_RE.match(p["name"]) or p["type"] not in TYPES):
            raise E1EError("E_SCHEMA", f"bad param {p!r}")
    if e["kind"] == "literal" and e["params"]:
        raise E1EError("E_SCHEMA", "literal entry with params")
    if e["kind"] == "template":
        parse_template(e["body"], e["params"])
    if not isinstance(e["digest"], str) or e["digest"] != entry_digest(e):
        raise E1EError("E_DIGEST", f"entry digest mismatch for {e['id']}")
    return e


def parse_template(body, params):
    """Tokenize: '{name}' placeholder, '{{' and '}}' literal braces. Returns token list."""
    types = {}
    for p in params:
        if p["name"] in types:
            raise E1EError("E_SCHEMA", f"duplicate param {p['name']}")
        types[p["name"]] = p["type"]
    toks, lit, i, used = [], [], 0, []
    while i < len(body):
        c = body[i]
        if c == "{" and body.startswith("{{", i):
            lit.append("{"); i += 2
        elif c == "}" and body.startswith("}}", i):
            lit.append("}"); i += 2
        elif c == "{":
            j = body.find("}", i)
            name = body[i + 1:j] if j > 0 else ""
            if j < 0 or name not in types:
                raise E1EError("E_SCHEMA", f"undeclared/unterminated placeholder at {i}")
            if lit:
                toks.append(("lit", "".join(lit))); lit = []
            if toks and toks[-1][0] == "param":
                raise E1EError("E_SCHEMA", "adjacent placeholders are not allowed")
            toks.append(("param", name, types[name])); used.append(name); i = j + 1
        elif c == "}":
            raise E1EError("E_SCHEMA", f"stray '}}' at {i}")
        else:
            lit.append(c); i += 1
    if lit:
        toks.append(("lit", "".join(lit)))
    if sorted(used) != sorted(types) or len(used) != len(set(used)):
        raise E1EError("E_SCHEMA", "each declared param must appear exactly once")
    if not any(t[0] == "lit" for t in toks):
        raise E1EError("E_SCHEMA", "template needs at least one literal character")
    return toks


def check_arg(typ, val):
    if typ == "int":
        return type(val) is int and INT_RE.match(str(val)) is not None
    if not isinstance(val, str) or not val:
        return False
    if typ == "word":
        return WORD_RE.match(val) is not None
    try:
        val.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True  # text: any non-empty string


def validate_args(entry, args):
    want = {p["name"]: p["type"] for p in entry["params"]}
    if not isinstance(args, dict) or set(args) != set(want):
        raise E1EError("E_PARAM", "argument names do not match the entry schema")
    for k, t in want.items():
        if not check_arg(t, args[k]):
            raise E1EError("E_PARAM", f"argument {k!r} is not a valid {t}")


def render(entry, args):
    if entry["kind"] == "literal":
        if args:
            raise E1EError("E_PARAM", "literal entry takes no args")
        return entry["body"]
    validate_args(entry, args)
    return "".join(t[1] if t[0] == "lit" else str(args[t[1]])
                   for t in parse_template(entry["body"], entry["params"]))


def match_template(entry, text, cap=2):
    """Return up to `cap` distinct parses (dicts) of text, or None if the step budget runs out."""
    if entry["kind"] == "literal":
        return [{}] if text == entry["body"] else []
    toks = parse_template(entry["body"], entry["params"])
    out, steps = [], [0]

    def ends(t, pos):
        typ, n = t[2], len(text)
        for end in range(pos + 1, n + 1):
            steps[0] += 1
            if steps[0] > MATCH_BUDGET:
                raise _Budget()
            s = text[pos:end]
            if typ == "text":
                yield end, s
            elif typ == "word":
                if not WORD_RE.match(s):
                    return
                yield end, s
            else:
                if INT_RE.match(s):
                    yield end, int(s)
                elif not re.fullmatch(r"-?[0-9]*", s):
                    return

    def rec(ti, pos, acc):
        if len(out) >= cap:
            return
        if ti == len(toks):
            if pos == len(text):
                out.append(dict(acc))
            return
        t = toks[ti]
        if t[0] == "lit":
            if text.startswith(t[1], pos):
                rec(ti + 1, pos + len(t[1]), acc)
            return
        for end, val in ends(t, pos):
            if ti + 1 < len(toks) and not text.startswith(toks[ti + 1][1], end):
                continue
            if ti + 1 == len(toks) and end != len(text):
                continue
            acc[t[1]] = val
            rec(ti + 1, end, acc)
            del acc[t[1]]
            if len(out) >= cap:
                return

    try:
        rec(0, 0, {})
    except _Budget:
        return None
    return out


class _Budget(Exception):
    pass
