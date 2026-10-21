"""Canonical escaped-JSON serialization and strict parsing (SPEC section 2)."""
import hashlib
import json

MAX_ARTIFACT_BYTES = 1 << 20
MAX_DEPTH = 8


class E1EError(Exception):
    """Validation failure; .code is one of the SPEC section 8 error codes."""

    def __init__(self, code, detail=""):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def _check_value(v, depth=0):
    if depth > MAX_DEPTH:
        raise E1EError("E_SCHEMA", "nesting too deep")
    if v is None or isinstance(v, bool):
        return
    if isinstance(v, int):
        return
    if isinstance(v, float):
        raise E1EError("E_SCHEMA", "floats are not permitted")
    if isinstance(v, str):
        try:
            v.encode("utf-8", "strict")
        except UnicodeEncodeError:
            raise E1EError("E_SCHEMA", "lone surrogate in string")
        return
    if isinstance(v, list):
        for x in v:
            _check_value(x, depth + 1)
        return
    if isinstance(v, dict):
        for k, x in v.items():
            if not isinstance(k, str):
                raise E1EError("E_SCHEMA", "non-string key")
            _check_value(k, depth + 1)
            _check_value(x, depth + 1)
        return
    raise E1EError("E_SCHEMA", f"unsupported type {type(v).__name__}")


def canonical(obj):
    """Deterministic bytes: sorted keys, no whitespace, ASCII-only (all non-ASCII \\u-escaped)."""
    _check_value(obj)
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")


def _no_dups(pairs):
    d = {}
    for k, v in pairs:
        if k in d:
            raise E1EError("E_DUP_KEY", f"duplicate JSON key {k!r}")
        d[k] = v
    return d


def _bad_const(c):
    raise E1EError("E_SCHEMA", f"non-finite number {c}")


def parse_canonical(data, limit=MAX_ARTIFACT_BYTES):
    """Parse bytes that must be exactly the canonical serialization of their value."""
    if not isinstance(data, (bytes, bytearray)):
        raise E1EError("E_MALFORMED", "input must be bytes")
    data = bytes(data)
    if len(data) > limit:
        raise E1EError("E_TOO_LARGE", f"{len(data)} > {limit}")
    try:
        text = data.decode("ascii")
    except UnicodeDecodeError:
        raise E1EError("E_MALFORMED", "artifact bytes must be ASCII escaped JSON")
    try:
        obj = json.loads(text, object_pairs_hook=_no_dups, parse_constant=_bad_const,
                         parse_float=lambda s: _bad_const(s))
    except E1EError:
        raise
    except (ValueError, RecursionError) as e:
        raise E1EError("E_MALFORMED", f"invalid JSON: {e}")
    if canonical(obj) != data:
        raise E1EError("E_NONCANONICAL", "bytes are not the canonical serialization")
    return obj


def sha256_hex(b):
    return "sha256:" + hashlib.sha256(b).hexdigest()
