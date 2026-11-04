# GPT (Codex CLI, read-only) code re-check r3 of E1e mechanics draft

Reviewed checkout: commit eb50a87. Date: 2026-10-21 (AEDT). Verbatim final response below (session log omitted). The finding (writable RepoState.version/digest) was fixed in the following commit: RepoState is now frozen (read-only version/digest properties, all attribute assignment/deletion raises), Holder.state is read-only, Publisher.history is a read-only mapping view and Link.frames a tuple copy, with regression test test_metadata_reassignment_blocked.

I’ll read the four files and prior findings, trace how callers can access snapshot state, and run the relevant tests.
exec
/bin/bash -lc "pwd; rg --files -g AGENTS.md -g '*gpt_E1e_code_r*.md' -g 'repo.py' -g 'codec.py' -g 'schema.py' -g 'test_rejections.py'" in /workspace/e1e-gpt
 succeeded in 0ms:
/workspace/e1e-gpt
v6/e1e/e1e/codec.py
v6/e1e/tests/test_rejections.py
v6/e1e/e1e/schema.py
v6/e1e/e1e/repo.py
v6/e1e/reviews/gpt_E1e_code_r2.md
v6/e1e/reviews/gpt_E1e_code_r1.md

exec
/bin/bash -lc 'cat v6/e1e/e1e/repo.py v6/e1e/e1e/codec.py v6/e1e/e1e/schema.py v6/e1e/tests/test_rejections.py' in /workspace/e1e-gpt
 succeeded in 0ms:
"""Repository state, full/delta artifacts and transactional operations (SPEC sections 3, 7)."""
import copy

from .canon import E1EError, canonical, parse_canonical, sha256_hex
from .schema import validate_entry

FORMAT = "E1E-REPO/1"
MAX_ENTRIES = 4096
FULL_KEYS = {"format", "type", "version", "entries", "digest"}
DELTA_KEYS = {"format", "type", "base_version", "base_digest", "target_version",
              "target_digest", "entries", "digest"}


def state_digest(version, entries):
    """Digest of a snapshot: format, version and every full entry, sorted by id."""
    body = {"format": FORMAT, "version": version,
            "entries": [entries[k] for k in sorted(entries)]}
    return sha256_hex(canonical(body))


class RepoState:
    """Immutable snapshot plus the (id, v) -> entry-digest history this holder has seen."""

    def __init__(self, version=0, entries=None, seen=None):
        self.version = version
        self._e = copy.deepcopy(dict(entries or {}))  # private; never shared with callers
        self._seen = dict(seen or {})
        for e in self._e.values():
            self._seen.setdefault((e["id"], e["v"]), e["digest"])
        self.digest = state_digest(version, self._e)

    @property
    def entries(self):
        """A defensive deep copy: mutating it cannot alter this snapshot or its digest."""
        return copy.deepcopy(self._e)

    @property
    def seen(self):
        return dict(self._seen)

    def entry(self, id):
        e = self._e.get(id)
        return None if e is None else copy.deepcopy(e)

    def full_bytes(self):
        obj = {"format": FORMAT, "type": "full", "version": self.version,
               "entries": [self._e[k] for k in sorted(self._e)], "digest": self.digest}
        return canonical(obj)

    def fingerprint(self):
        """Everything observable about the state, for 'unchanged after rejection' assertions."""
        return (self.version, self.digest, canonical([self._e[k] for k in sorted(self._e)]),
                tuple(sorted(self._seen.items())))


def _entries_list(obj):
    ents = obj["entries"]
    if not isinstance(ents, list) or len(ents) > MAX_ENTRIES:
        raise E1EError("E_SCHEMA", "entries must be a list within MAX_ENTRIES")
    ids = []
    for e in ents:
        validate_entry(e)
        ids.append(e["id"])
    if len(set(ids)) != len(ids):
        raise E1EError("E_DUP_ENTRY", "duplicate entry id in artifact")
    if ids != sorted(ids):
        raise E1EError("E_NONCANONICAL", "entries must be sorted by id")
    return ents


def _version(x, what):
    if type(x) is not int or not 0 <= x <= 2**31:
        raise E1EError("E_SCHEMA", f"bad {what}")
    return x


def parse_full(data):
    obj = parse_canonical(data)
    if not isinstance(obj, dict) or set(obj) != FULL_KEYS or obj["format"] != FORMAT or obj["type"] != "full":
        raise E1EError("E_SCHEMA", "not an E1E-REPO/1 full artifact")
    _version(obj["version"], "version")
    ents = _entries_list(obj)
    st = RepoState(obj["version"], {e["id"]: e for e in ents})
    if st.digest != obj["digest"]:
        raise E1EError("E_DIGEST", "full snapshot digest mismatch")
    return st


def load_full(data, current=None):
    """Validate a full artifact; return the new state for `current` (never mutates)."""
    st = parse_full(data)
    if current is not None:
        if st.version < current.version:
            raise E1EError("E_STALE", f"full v{st.version} older than held v{current.version}")
        if st.version == current.version and st.digest != current.digest:
            raise E1EError("E_FORK", "same version, different snapshot digest")
        missing = set(current._e) - set(st._e)
        if missing:
            raise E1EError("E_DELETION_DEFERRED", f"full artifact omits held entries {sorted(missing)}")
        for (i, v), d in current.seen.items():
            e = st._e.get(i)
            if e is not None and e["v"] == v and e["digest"] != d:
                raise E1EError("E_VERSION_REUSE", f"{i} v{v} has different content")
            if e is not None and e["v"] < v:
                raise E1EError("E_VERSION", f"{i} would regress from v{v} to v{e['v']}")
        seen = dict(current.seen)
        seen.update(st.seen)
        st = RepoState(st.version, st._e, seen)
    return st


def parse_delta(data):
    obj = parse_canonical(data)
    if not isinstance(obj, dict) or set(obj) != DELTA_KEYS or obj["format"] != FORMAT or obj["type"] != "delta":
        raise E1EError("E_SCHEMA", "not an E1E-REPO/1 delta artifact")
    for k in ("base_version", "target_version"):
        _version(obj[k], k)
    for k in ("base_digest", "target_digest", "digest"):
        if not isinstance(obj[k], str):
            raise E1EError("E_SCHEMA", f"bad {k}")
    body = {k: obj[k] for k in DELTA_KEYS - {"digest"}}
    if sha256_hex(canonical(body)) != obj["digest"]:
        raise E1EError("E_DIGEST", "delta artifact digest mismatch")
    ents = _entries_list(obj)
    if not ents:
        raise E1EError("E_SCHEMA", "empty delta")
    if obj["target_version"] != obj["base_version"] + 1:
        raise E1EError("E_VERSION", "target_version must be base_version + 1")
    return obj, ents


def check_entry_progression(state, e):
    prior = state.seen.get((e["id"], e["v"]))
    if prior is not None and prior != e["digest"]:
        raise E1EError("E_VERSION_REUSE", f"{e['id']} v{e['v']} already has different content")
    cur = state._e.get(e["id"])
    want = 1 if cur is None else cur["v"] + 1
    if e["v"] != want:
        raise E1EError("E_VERSION", f"{e['id']} must be v{want}, got v{e['v']}")


def apply_delta(state, data):
    """Validate everything, then return the new state. `state` is never mutated."""
    obj, ents = parse_delta(data)
    if obj["base_version"] != state.version:
        raise E1EError("E_STALE" if obj["base_version"] > state.version else "E_BASE_MISMATCH",
                       f"delta base v{obj['base_version']} vs held v{state.version}")
    if obj["base_digest"] != state.digest:
        raise E1EError("E_BASE_MISMATCH", "base digest differs from held snapshot (same version)")
    for e in ents:
        check_entry_progression(state, e)
    new_entries = dict(state._e)
    seen = dict(state._seen)
    for e in ents:
        new_entries[e["id"]] = e
        seen[(e["id"], e["v"])] = e["digest"]
    new = RepoState(obj["target_version"], new_entries, seen)
    if new.digest != obj["target_digest"]:
        raise E1EError("E_TARGET_MISMATCH", "result does not match declared target digest")
    return new


def make_delta(state, entries):
    ents = sorted(entries, key=lambda e: e["id"])
    new_entries = dict(state._e)
    for e in ents:
        new_entries[e["id"]] = e
    body = {"format": FORMAT, "type": "delta", "base_version": state.version,
            "base_digest": state.digest, "target_version": state.version + 1,
            "target_digest": state_digest(state.version + 1, new_entries), "entries": ents}
    body["digest"] = sha256_hex(canonical(body))
    return canonical(body)


class Holder:
    """Something that holds one current RepoState and swaps it only after full validation."""

    def __init__(self, state=None):
        self.state = state or RepoState()

    def load_full(self, data):
        new = load_full(data, self.state)
        self.state = new
        return new

    def apply_delta(self, data):
        new = apply_delta(self.state, data)
        self.state = new
        return new


class Publisher(Holder):
    """Maintainer: publishes deltas and keeps every snapshot it produced, keyed by digest."""

    def __init__(self):
        super().__init__()
        self.history = {self.state.digest: self.state}

    def publish(self, entries):
        """Transactional: validate all entries and the generated delta, then commit."""
        seen_ids = set()
        for e in entries:
            validate_entry(e)
            if e["id"] in seen_ids:
                raise E1EError("E_DUP_ENTRY", f"duplicate id {e['id']} in publish")
            seen_ids.add(e["id"])
        if not entries:
            raise E1EError("E_SCHEMA", "nothing to publish")
        delta = make_delta(self.state, entries)
        new = apply_delta(self.state, delta)  # same validator receivers run
        self.state = new
        self.history[new.digest] = new
        return delta, new.full_bytes()


class Receiver(Holder):
    def declare(self):
        """Snapshot declaration a receiver sends so senders never assume its state."""
        return {"version": self.state.version, "digest": self.state.digest}
"""Message codec: references, raw fallback, verification and receiver rejection (SPEC sections 6-8)."""
import base64
import copy

from .canon import E1EError, canonical, parse_canonical, sha256_hex
from .schema import match_template, render, validate_args

MSG_FORMAT = "E1E-MSG/1"
MAX_MESSAGE_BYTES = 65536
MAX_CANDIDATES = 8
MAX_WIRE_BYTES = 6 * MAX_MESSAGE_BYTES + 1024
REF_KEYS = {"format", "type", "snap", "id", "v", "entry", "args"}


def raw_wire(msg):
    try:
        obj = {"format": MSG_FORMAT, "type": "raw", "text": msg.decode("utf-8", "strict")}
    except UnicodeDecodeError:
        obj = {"format": MSG_FORMAT, "type": "raw", "b64": base64.b64encode(msg).decode("ascii")}
    return canonical(obj)


def reject_wire(code, wire):
    return canonical({"format": MSG_FORMAT, "type": "reject", "code": code, "msg": sha256_hex(wire)})


def decode_message(state, wire):
    """Receiver-side decoder. Returns the original message bytes or raises E1EError."""
    obj = parse_canonical(wire, MAX_WIRE_BYTES)
    if not isinstance(obj, dict) or obj.get("format") != MSG_FORMAT:
        raise E1EError("E_SCHEMA", "not an E1E-MSG/1 message")
    t = obj.get("type")
    if t == "raw":
        if set(obj) == {"format", "type", "text"} and isinstance(obj["text"], str):
            out = obj["text"].encode("utf-8")
        elif set(obj) == {"format", "type", "b64"} and isinstance(obj["b64"], str):
            try:
                out = base64.b64decode(obj["b64"], validate=True)
            except ValueError:
                raise E1EError("E_SCHEMA", "bad base64")
            if base64.b64encode(out).decode("ascii") != obj["b64"]:
                raise E1EError("E_NONCANONICAL", "non-canonical base64")
        else:
            raise E1EError("E_SCHEMA", "bad raw message")
    elif t == "ref":
        if set(obj) != REF_KEYS:
            raise E1EError("E_SCHEMA", "bad ref message keys")
        if obj["snap"] != state.digest:
            raise E1EError("E_STALE", "reference names a snapshot the receiver does not hold")
        if type(obj["v"]) is not int or not isinstance(obj["id"], str):
            raise E1EError("E_SCHEMA", "ref id must be a string and v an integer")
        e = state._e.get(obj["id"])
        if e is None or e["v"] != obj["v"] or e["digest"] != obj["entry"]:
            raise E1EError("E_UNKNOWN_REF", f"no entry {obj['id']!r} v{obj['v']!r} with that digest")
        if e["kind"] == "template":
            validate_args(e, obj["args"])
        elif obj["args"] != {}:
            raise E1EError("E_PARAM", "literal reference with args")
        out = render(e, obj["args"]).encode("utf-8")
    else:
        raise E1EError("E_SCHEMA", f"unknown message type {t!r}")
    if len(out) > MAX_MESSAGE_BYTES:
        raise E1EError("E_TOO_LARGE", "decoded message too large")
    return out


def _first_literal(e):
    if e["kind"] == "literal":
        return e["body"]
    from .schema import parse_template
    t = parse_template(e["body"], e["params"])[0]
    return t[1] if t[0] == "lit" else ""


def candidates(state, text, k=MAX_CANDIDATES):
    """Bounded, deterministic candidate set: entries whose leading literal prefixes the text,
    ordered by (longest leading literal first, id), truncated to k."""
    cs = [(len(_first_literal(e)), e["id"]) for e in state._e.values()
          if text.startswith(_first_literal(e))]
    cs.sort(key=lambda x: (-x[0], x[1]))
    return [copy.deepcopy(state._e[i]) for _, i in cs[:k]]  # never expose snapshot internals


def encode(known, declaration, msg, k=MAX_CANDIDATES, require_smaller=False):
    """Encode `msg` (bytes) for a receiver that declared `declaration`.
    `known` maps snapshot digest -> RepoState the sender can see. Returns (wire, info).
    require_smaller=False: this mechanics draft sends any verified reference, even when it is
    larger than the raw envelope (no savings policy is claimed)."""
    info = {"reason": None, "skipped": []}
    if len(msg) > MAX_MESSAGE_BYTES:
        raise E1EError("E_TOO_LARGE", "message exceeds MAX_MESSAGE_BYTES; nothing is sent")
    raw = raw_wire(msg)
    snap = known.get(declaration.get("digest")) if isinstance(declaration, dict) else None
    if snap is None or snap.version != declaration.get("version"):
        info["reason"] = "unknown_declared_snapshot"; return raw, info
    try:
        text = msg.decode("utf-8", "strict")
    except UnicodeDecodeError:
        info["reason"] = "not_utf8"; return raw, info
    best = None
    for e in candidates(snap, text, k):
        parses = match_template(e, text)
        if parses is None:
            info["skipped"].append((e["id"], "budget")); continue
        if len(parses) != 1:
            if parses:
                info["skipped"].append((e["id"], "ambiguous"))
            continue
        wire = canonical({"format": MSG_FORMAT, "type": "ref", "snap": snap.digest, "id": e["id"],
                          "v": e["v"], "entry": e["digest"], "args": parses[0]})
        try:  # exact verification through the real decoder on the declared snapshot
            ok = decode_message(snap, wire) == msg
        except E1EError:
            ok = False
        if not ok:
            info["skipped"].append((e["id"], "verify_failed")); continue
        if best is None or (len(wire), e["id"]) < (len(best[0]), best[1]):
            best = (wire, e["id"])
    if best is None or (require_smaller and len(best[0]) >= len(raw)):
        info["reason"] = "no_match" if best is None else "ref_not_smaller"
        return raw, info
    info["reason"] = "ref"; info["id"] = best[1]
    return best[0], info


class Link:
    """One sender->receiver channel with byte accounting of every frame."""

    def __init__(self, known, receiver):
        self.known, self.receiver = known, receiver
        self.frames = []  # (direction, kind, nbytes)

    def transmit(self, msg, declaration=None):
        decl = self.receiver.declare() if declaration is None else declaration
        wire, info = encode(self.known, decl, msg)
        kind = "ref" if info["reason"] == "ref" else "raw"
        self.frames.append(("fwd", kind, len(wire)))
        before = self.receiver.state.fingerprint()
        try:
            out = decode_message(self.receiver.state, wire)
            rejected = None
        except E1EError as err:
            rejected = err.code
            rej = reject_wire(err.code, wire)
            self.frames.append(("back", "reject", len(rej)))
            fb = raw_wire(msg)
            self.frames.append(("fwd", "fallback", len(fb)))
            out = decode_message(self.receiver.state, fb)
        assert self.receiver.state.fingerprint() == before  # decoding never mutates state
        return out, {"kind": kind, "rejected": rejected, "reason": info["reason"]}

    def totals(self):
        t = {}
        for d, k, n in self.frames:
            t[k] = t.get(k, 0) + n
        t["all"] = sum(n for _, _, n in self.frames)
        return t


def transmit(known, receiver, msg, declaration=None):
    return Link(known, receiver).transmit(msg, declaration)
"""Entries, typed-template grammar and deterministic matching (SPEC sections 4-6)."""
import re

from .canon import E1EError, canonical, sha256_hex

ID_RE = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}\Z")
NAME_RE = re.compile(r"[a-z][a-z0-9_]{0,31}\Z")
WORD_RE = re.compile(r"[A-Za-z0-9_.-]+\Z")
INT_RE = re.compile(r"-?(0|[1-9][0-9]{0,17})\Z")
TYPES = ("int", "word", "text")
KINDS = ("literal", "template")
PROVS = ("synthetic",)  # only synthetic fixtures are approved for this draft
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
"""Rejection boundaries. Every rejected operation must leave holder state unchanged.
These are NOT round trips; corrupted inputs are asserted to fail."""
import json
import unittest

from tests.helpers import build, recv_at, redigest_delta, RejectMixin
from e1e import (Publisher, Receiver, E1EError, Link, make_entry, make_delta, canonical,
                 parse_canonical, decode_message, encode, sha256_hex)
from e1e.repo import RepoState, parse_full
from e1e.schema import match_template, entry_digest


def ref(state, eid, args, v=None, digest=None, snap=None):
    e = state.entries[eid]
    return canonical({"format": "E1E-MSG/1", "type": "ref", "snap": snap or state.digest, "id": eid,
                      "v": v or e["v"], "entry": digest or e["digest"], "args": args})


class Artifacts(RejectMixin, unittest.TestCase):
    def setUp(self):
        self.pub, self.deltas, self.fulls = build()

    def test_wrong_base_digest_same_version(self):
        # A forked v1 (different content, same version) receives the real v1->v2 delta.
        fork = Publisher()
        fork.publish([make_entry("other", 1, "forked content")])
        r = Receiver(); r.load_full(fork.state.full_bytes())
        self.assertEqual(r.state.version, 1)
        self.assertRejected(r, lambda: r.apply_delta(self.deltas[1]), "E_BASE_MISMATCH")

    def test_target_digest_mismatch(self):
        r = recv_at(self.fulls, 0)
        obj = json.loads(self.deltas[1]); obj["target_digest"] = "sha256:" + "0" * 64
        self.assertRejected(r, lambda: r.apply_delta(redigest_delta(obj)), "E_TARGET_MISMATCH")

    def test_truncated_and_corrupt(self):
        r = recv_at(self.fulls, 0)
        for b in (self.deltas[1][:-1], self.deltas[1][: len(self.deltas[1]) // 2], b""):
            self.assertRejected(r, lambda: r.apply_delta(b), "E_MALFORMED")
        flipped = self.deltas[1].replace(b"Starting", b"Startinh")
        self.assertRejected(r, lambda: r.apply_delta(flipped), "E_DIGEST")
        self.assertRejected(r, lambda: r.load_full(self.fulls[1].replace(b"Starting", b"Startinh")),
                            "E_DIGEST")
        self.assertRejected(r, lambda: r.load_full(self.fulls[1][:-3]), "E_MALFORMED")
        self.assertRejected(r, lambda: r.load_full(self.fulls[1] + b" "), "E_NONCANONICAL")
        pretty = json.dumps(json.loads(self.fulls[1]), indent=1).encode()
        self.assertRejected(r, lambda: r.load_full(pretty), "E_NONCANONICAL")
        self.assertRejected(r, lambda: r.load_full("é".encode() + self.fulls[1]), "E_MALFORMED")

    def test_entry_digest_tamper_resealed(self):
        r = recv_at(self.fulls, 0)
        obj = json.loads(self.deltas[1]); obj["entries"][0]["body"] = "ACK changed"
        self.assertRejected(r, lambda: r.apply_delta(redigest_delta(obj)), "E_DIGEST")

    def test_duplicate_json_keys(self):
        r = recv_at(self.fulls, 0)
        dup = self.deltas[1].replace(b'{"base_digest"', b'{"base_digest":"x","base_digest"', 1)
        self.assertRejected(r, lambda: r.apply_delta(dup), "E_DUP_KEY")

    def test_duplicate_delta_entries(self):
        r = recv_at(self.fulls, 0)
        obj = json.loads(self.deltas[1])
        obj["entries"] = [obj["entries"][0], obj["entries"][0], obj["entries"][1]]
        self.assertRejected(r, lambda: r.apply_delta(redigest_delta(obj)), "E_DUP_ENTRY")
        self.assertRaises(E1EError, self.pub.publish, [make_entry("zz", 1, "a"), make_entry("zz", 1, "a")])

    def test_illegal_version_reuse(self):
        r = recv_at(self.fulls, 1)  # holds ack v2
        alt = make_entry("ack", 2, "ACK: different content, same version")
        d = make_delta(r.state, [alt])
        self.assertRejected(r, lambda: r.apply_delta(d), "E_VERSION_REUSE")
        before = self.pub.state.fingerprint()
        alt3 = make_entry("lf", 1, "different lf v1 {k}", [("k", "int")])
        with self.assertRaises(E1EError) as cm:
            self.pub.publish([alt3])
        self.assertEqual(cm.exception.code, "E_VERSION_REUSE")
        self.assertEqual(self.pub.state.fingerprint(), before)
        # same body, changed parameter schema at same version is also reuse
        st = make_entry("status", 1, "status: job {job} is {state} after {n} steps",
                        [("job", "word"), ("state", "text"), ("n", "int")])
        self.assertNotEqual(st["digest"], self.pub.state.entries["status"]["digest"])
        self.assertRejected(r, lambda: r.apply_delta(make_delta(r.state, [st])), "E_VERSION_REUSE")

    def test_version_skip_and_regress(self):
        r = recv_at(self.fulls, 1)
        self.assertRejected(r, lambda: r.apply_delta(make_delta(r.state, [make_entry("ack", 4, "x")])), "E_VERSION")
        self.assertRejected(r, lambda: r.apply_delta(make_delta(r.state, [make_entry("new", 2, "x")])), "E_VERSION")
        self.assertRejected(r, lambda: r.load_full(self.fulls[0]), "E_STALE")
        self.assertRejected(r, lambda: r.apply_delta(self.deltas[1]), "E_BASE_MISMATCH")  # replay
        r0 = recv_at(self.fulls, 0)  # v1 holder receiving the v2->v3 delta (gap)
        self.assertRejected(r0, lambda: r0.apply_delta(self.deltas[2]), "E_STALE")

    def test_publish_transactional(self):
        before = self.pub.state.fingerprint(); hist = dict(self.pub.history)
        good = make_entry("fresh", 1, "fresh")
        bad = dict(make_entry("bad", 1, "x")); bad["digest"] = "sha256:00"
        for batch in ([good, bad], [good, make_entry("ack", 9, "x")], []):
            self.assertRaises(E1EError, self.pub.publish, batch)
            self.assertEqual(self.pub.state.fingerprint(), before)
            self.assertEqual(self.pub.history, hist)

    def test_bad_template_schemas(self):
        for body, params in [("a {x", [("x", "text")]), ("a {x}{y}", [("x", "text"), ("y", "text")]),
                             ("a {x}", []), ("a } b", []), ("a {x} {x}", [("x", "text")]),
                             ("{x}", [("x", "text")]), ("a {X}", [("X", "text")]),
                             ("a {x}", [("x", "float")])]:
            with self.assertRaises(E1EError, msg=body):
                make_entry("t", 1, body, params, kind="template")


class Messages(RejectMixin, unittest.TestCase):
    def setUp(self):
        self.pub, self.deltas, self.fulls = build()
        self.r = recv_at(self.fulls, 2)
        self.st = self.r.state

    def test_malformed_parameters(self):
        for args in ({"job": "a b", "state": "ok", "n": 1}, {"job": "a", "state": "ok", "n": "1"},
                     {"job": "a", "state": "ok"}, {"job": "a", "state": "ok", "n": 1, "x": 1},
                     {"job": "a", "state": "ok", "n": True}, {"job": "", "state": "ok", "n": 1},
                     {"job": "a", "state": "ok", "n": 10**19}):
            self.assertRejected(self.r, lambda: decode_message(self.st, ref(self.st, "status", args)), "E_PARAM")
        self.assertRejected(self.r, lambda: decode_message(self.st, ref(self.st, "ack", {"x": "y"})), "E_PARAM")
        bad = b'{"args":{"job":"a","n":1.5,"state":"b"}}'
        self.assertRejected(self.r, lambda: decode_message(self.st, bad), "E_SCHEMA")

    def test_unknown_references(self):
        for w in (canonical({"format": "E1E-MSG/1", "type": "ref", "snap": self.st.digest, "id": "nope",
                             "v": 1, "entry": "sha256:00", "args": {}}),
                  ref(self.st, "ack", {}, v=1), ref(self.st, "ack", {}, digest="sha256:" + "1" * 64)):
            self.assertRejected(self.r, lambda: decode_message(self.st, w), "E_UNKNOWN_REF")
        self.assertRejected(self.r, lambda: decode_message(self.st, ref(self.st, "ack", {}, snap="sha256:ab")),
                            "E_STALE")

    def test_ambiguous_match_not_encoded(self):
        e = self.st.entries["pair"]
        m = "pair x and y and z"
        self.assertEqual(len(match_template(e, m)), 2)
        decl = self.r.declare()
        wire, info = encode(self.pub.history, decl, m.encode())
        self.assertNotEqual(info["reason"], "ref")
        self.assertIn(("pair", "ambiguous"), info["skipped"])
        self.assertEqual(decode_message(self.st, wire), m.encode())
        self.assertEqual(len(match_template(e, "pair x and y")), 1)

    def test_nfc_nfd_not_interchangeable(self):
        nfc, nfd = self.st.entries["uni-nfc"], self.st.entries["uni-nfd"]
        self.assertEqual(match_template(nfc, "cafe\u0301 note: t"), [])
        self.assertEqual(match_template(nfd, "caf\u00e9 note: t"), [])

    def test_wire_escaping_and_invalid_unicode(self):
        w = canonical({"format": "E1E-MSG/1", "type": "raw", "text": "a"})
        self.assertRejected(self.r, lambda: decode_message(self.st, w.replace(b'"a"', b'"\\ud800"')), "E_SCHEMA")
        self.assertRejected(self.r, lambda: decode_message(self.st, w.replace(b'"a"', b'"\\u0061"')), "E_NONCANONICAL")
        self.assertRejected(self.r, lambda: decode_message(self.st, b'{"b64":"AA=","format":"E1E-MSG/1","type":"raw"}'), "E_SCHEMA")


class ReceiverState(RejectMixin, unittest.TestCase):
    def setUp(self):
        self.pub, self.deltas, self.fulls = build()

    def test_stale_copy_receiver_falls_back(self):
        stale = recv_at(self.fulls, 0)  # honest v1 declaration, ack v1 only
        link = Link(self.pub.history, stale)
        m = b"ACK: task received.\nStarting now."  # only encodable with ack v2
        out, info = link.transmit(m)
        self.assertEqual(out, m)
        self.assertEqual(info["kind"], "raw")  # sender used the declared v1 snapshot, not its own v3
        self.assertIsNone(info["rejected"])

    def test_stale_declaration_rejected_then_fallback(self):
        r = recv_at(self.fulls, 1)
        old_decl = r.declare()
        r.apply_delta(self.deltas[2])  # receiver advanced after declaring
        link = Link(self.pub.history, r)
        m = b"status: job a is ok after 1 steps"
        before = r.state.fingerprint()
        out, info = link.transmit(m, declaration=old_decl)
        self.assertEqual(out, m)
        self.assertEqual(info["rejected"], "E_STALE")
        self.assertEqual(r.state.fingerprint(), before)
        t = link.totals()
        self.assertGreater(t["reject"], 0); self.assertGreater(t["fallback"], 0)
        self.assertEqual(t["all"], t["ref"] + t["reject"] + t["fallback"])

    def test_receiver_copy_diverged_from_declaration(self):
        # Receiver lies/mis-declares v2 while holding a fork: decoder must reject, fallback delivers.
        fork = Publisher(); fork.publish([make_entry("status", 1, "forked {x}!", [("x", "word")])])
        r = Receiver(); r.load_full(fork.state.full_bytes())
        v1 = parse_full(self.fulls[0])
        decl = {"version": 1, "digest": v1.digest}  # declares the real v1, holds a fork
        out, info = Link(self.pub.history, r).transmit(b"status: job a is ok after 1 steps", decl)
        self.assertEqual(out, b"status: job a is ok after 1 steps")
        self.assertEqual(info["rejected"], "E_STALE")

    def test_unknown_declaration_sends_raw(self):
        r = Receiver()
        out, info = Link(self.pub.history, r).transmit(b"ACK", {"version": 7, "digest": "sha256:zz"})
        self.assertEqual((out, info["reason"]), (b"ACK", "unknown_declared_snapshot"))


if __name__ == "__main__":
    unittest.main()


class ReviewR1Regressions(RejectMixin, unittest.TestCase):
    """Regressions for gpt_E1e_code_r1 findings and its requested extra coverage."""

    def setUp(self):
        self.pub, self.deltas, self.fulls = build()

    def _full(self, version, entries):
        return RepoState(version, {e["id"]: e for e in entries}).full_bytes()

    def test_full_load_cannot_delete(self):
        r = recv_at(self.fulls, 0)
        self.assertRejected(r, lambda: r.load_full(self._full(2, [])), "E_DELETION_DEFERRED")

    def test_full_load_fork_and_history_conflict(self):
        r = recv_at(self.fulls, 0)
        fork = list(parse_full(self.fulls[0]).entries.values()) + [make_entry("zzz", 1, "extra")]
        self.assertRejected(r, lambda: r.load_full(self._full(1, fork)), "E_FORK")
        conflict = [make_entry("ack", 1, "ACK other")] + [e for e in parse_full(self.fulls[0]).entries.values() if e["id"] != "ack"]
        self.assertRejected(r, lambda: r.load_full(self._full(2, conflict)), "E_VERSION_REUSE")

    def test_snapshots_do_not_alias(self):
        old = self.pub.history[parse_full(self.fulls[0]).digest]
        b0, d0 = old.full_bytes(), self.pub.state.full_bytes()
        old.entries["status"]["body"] = "changed"
        self.pub.state.entries["status"]["body"] = "changed"
        self.assertEqual((old.full_bytes(), self.pub.state.full_bytes()), (b0, d0))

    def test_bool_version_rejected(self):
        r = recv_at(self.fulls, 0); st = r.state
        e = st.entry("ack")
        w = canonical({"format": "E1E-MSG/1", "type": "ref", "snap": st.digest, "id": "ack", "v": True,
                       "entry": e["digest"], "args": {}})
        self.assertRejected(r, lambda: decode_message(st, w), "E_SCHEMA")

    def test_oversized_send_records_nothing(self):
        r = recv_at(self.fulls, 2); link = Link(self.pub.history, r)
        with self.assertRaises(E1EError) as cm:
            link.transmit(b"a" * 65537)
        self.assertEqual((cm.exception.code, link.frames), ("E_TOO_LARGE", []))

    def test_match_budget_and_candidate_limit(self):
        e = make_entry("p", 1, "x{a}y{b}y{c}z", [("a", "text"), ("b", "text"), ("c", "text")])
        self.assertIsNone(match_template(e, "x" + "y" * 400 + "q"))  # budget exhausted -> no match
        pub = Publisher()
        pub.publish([make_entry(f"c{i:02d}", 1, "hdr " + "h" * i + " {t}", [("t", "text")]) for i in range(12)])
        st = pub.state
        from e1e.codec import candidates
        cs = candidates(st, "hdr " + "h" * 11 + " body")
        self.assertEqual([c["id"] for c in cs], ["c11"])
        cs = candidates(st, "hdr ")
        self.assertEqual(cs, [])
        many = Publisher(); many.publish([make_entry(f"d{i:02d}", 1, "same {t}", [("t", "text")]) for i in range(12)])
        self.assertEqual([c["id"] for c in candidates(many.state, "same q")], [f"d{i:02d}" for i in range(8)])

    def test_candidates_do_not_alias(self):
        from e1e.codec import candidates
        st = self.pub.state; b0 = st.full_bytes()
        candidates(st, "status: job a is ok after 1 steps")[0]["body"] = "changed"
        self.assertEqual(st.full_bytes(), b0)
        self.assertEqual(parse_full(st.full_bytes()).digest, st.digest)

exec
/bin/bash -lc 'cat v6/e1e/reviews/gpt_E1e_code_r1.md v6/e1e/reviews/gpt_E1e_code_r2.md; git show --stat 2c17eba; rg --files v6/e1e' in /workspace/e1e-gpt
 succeeded in 0ms:
# GPT (Codex CLI, read-only) code review r1 of E1e mechanics draft

Reviewed checkout: commit ad77d0c. Date: 2026-10-21 (AEDT). Verbatim response below. All four findings were fixed in the following commit, with regression tests (class ReviewR1Regressions).

Reviewed HEAD `ad77d0c` and all requested files in full. All **25 tests pass**, run with bytecode writing disabled.

**Verdict: needs fixes first**, primarily the full-load deletion path.

1. **High — full sync permits deletion.** [repo.py:82](/workspace/e1e-gpt/v6/e1e/e1e/repo.py:82) checks history only when an ID remains present. Reproduction: load a valid v1 containing `a`, then load a correctly digested v2 with `entries: []`. It succeeds and removes `a`, contradicting §3’s additions/revisions-only rule. Reject full artifacts that omit held entries.

2. **Medium — snapshots are mutable and share entry objects.** [repo.py:24](/workspace/e1e-gpt/v6/e1e/e1e/repo.py:24), [repo.py:134](/workspace/e1e-gpt/v6/e1e/e1e/repo.py:134). Reproduction: publish `a`, retain `old = pub.state`, publish `b`, then assign `old.entries["a"]["body"] = "changed"`. The current snapshot also changes while its stored digest remains unchanged. This breaks the advertised immutable, digest-keyed snapshot boundary. Use immutable nested structures or defensive copies at exposure boundaries.

3. **Medium — malformed reference version accepted.** [codec.py:50](/workspace/e1e-gpt/v6/e1e/e1e/codec.py:50) compares versions without validating their type. A canonical reference to a v1 entry with `"v": true` and otherwise correct fields decodes successfully because `True == 1`. Require an integer version explicitly, excluding booleans.

4. **Low — oversized sends produce an undeliverable fallback.** [codec.py:87](/workspace/e1e-gpt/v6/e1e/e1e/codec.py:87). `encode(..., b"a"*65537)` returns a raw frame marked `too_large`; `Link.transmit` sends it, records rejection, then sends the same invalid payload as fallback and raises `E_TOO_LARGE`. Reject oversized input before serialization or recording traffic.

Against §4, the main package is present: protocol, transactional validation, typed codec, actual-decoder byte verification, receiver declarations, fallback accounting, and deterministic synthetic evidence. Missing regression coverage includes the findings above, full-load fork/history conflicts, and explicit matching-budget/candidate-limit boundaries.

I found **no rejected repository operation that mutates state through the normal validated API**, and **no accepted non-identical byte round trip**. The snapshot-aliasing finding requires direct mutation of an exposed object; it is distinct from rejection atomicity. The synthetic-only labeling and absence of savings claims are appropriate.
# GPT (Codex CLI, read-only) code re-check r2 of E1e mechanics draft

Reviewed checkout: commit e9acb32. Date: 2026-10-21 (AEDT). Verbatim response below. The remaining finding (candidates() returned private entry dicts) was fixed in the following commit by returning deep copies, with regression test test_candidates_do_not_alias; that fix has not been re-reviewed by GPT (one re-check only, per instructions).

Read all nine files in full at `e9acb32`. **All 31 tests pass.**

1. **Deletion: fixed.** Full loads cannot omit held entries.
2. **Snapshot exposure: partially fixed.** Constructor inputs and `entries`/`seen`/`entry()` are defensively copied, but the fix leaves another exposure below.
3. **Reference version: fixed.** Non-integers, including booleans, are rejected.
4. **Oversized sends: fixed.** `E_TOO_LARGE` occurs before serialization or frame accounting.

**Medium — mutable candidates escape the snapshot boundary:** [codec.py:81](/workspace/e1e-gpt/v6/e1e/e1e/codec.py:81) now returns private entry dictionaries. Reproduced with `candidates(state, "hello")[0]["body"] = "changed"`: snapshot bytes change while the stored digest stays unchanged. Return defensive copies and add regression coverage for this path.

**Verdict: needs this fix before acceptance as a fixture-tested mechanics draft.** No other new bug found in this re-check.
commit 2c17eba5fe30d1d4a39bc9bbcc32887be820ec43
Author: devamped1337 <devamped1337@users.noreply.github.com>
Date:   Wed Oct 21 19:50:52 2026 +1100

    E1e: fix GPT re-check r2 finding (candidates return copies) + regression; save review r2

 v6/e1e/e1e/codec.py               |  3 ++-
 v6/e1e/reviews/gpt_E1e_code_r2.md | 14 ++++++++++++++
 v6/e1e/tests/test_rejections.py   |  7 +++++++
 3 files changed, 23 insertions(+), 1 deletion(-)
v6/e1e/REPOSITORY_PILOT_DRAFT.md
v6/e1e/e1e/codec.py
v6/e1e/e1e/schema.py
v6/e1e/e1e/canon.py
v6/e1e/e1e/repo.py
v6/e1e/e1e/__init__.py
v6/e1e/SPEC_E1E_REPO_1.md
v6/e1e/README_MECHANICS.md
v6/e1e/GLYPH_REPLY_r1.md
v6/e1e/data/README.md
v6/e1e/data/synthetic_gpt_r1.jsonl
v6/e1e/COLLECTION_LOG.md
v6/e1e/tests/helpers.py
v6/e1e/tests/test_rejections.py
v6/e1e/tests/fixtures.py
v6/e1e/tests/test_roundtrip.py
v6/e1e/tests/__init__.py
v6/e1e/reviews/gpt_E1e_code_r2.md
v6/e1e/reviews/gpt_E1e_code_r1.md
v6/e1e/reviews/gpt_E1e_pilot_r1.md

exec
/bin/bash -lc 'cat v6/e1e/e1e/schema.py' in /workspace/e1e-gpt
 succeeded in 0ms:
"""Entries, typed-template grammar and deterministic matching (SPEC sections 4-6)."""
import re

from .canon import E1EError, canonical, sha256_hex

ID_RE = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}\Z")
NAME_RE = re.compile(r"[a-z][a-z0-9_]{0,31}\Z")
WORD_RE = re.compile(r"[A-Za-z0-9_.-]+\Z")
INT_RE = re.compile(r"-?(0|[1-9][0-9]{0,17})\Z")
TYPES = ("int", "word", "text")
KINDS = ("literal", "template")
PROVS = ("synthetic",)  # only synthetic fixtures are approved for this draft
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

exec
/bin/bash -lc 'cat v6/e1e/tests/test_rejections.py' in /workspace/e1e-gpt
 succeeded in 0ms:
"""Rejection boundaries. Every rejected operation must leave holder state unchanged.
These are NOT round trips; corrupted inputs are asserted to fail."""
import json
import unittest

from tests.helpers import build, recv_at, redigest_delta, RejectMixin
from e1e import (Publisher, Receiver, E1EError, Link, make_entry, make_delta, canonical,
                 parse_canonical, decode_message, encode, sha256_hex)
from e1e.repo import RepoState, parse_full
from e1e.schema import match_template, entry_digest


def ref(state, eid, args, v=None, digest=None, snap=None):
    e = state.entries[eid]
    return canonical({"format": "E1E-MSG/1", "type": "ref", "snap": snap or state.digest, "id": eid,
                      "v": v or e["v"], "entry": digest or e["digest"], "args": args})


class Artifacts(RejectMixin, unittest.TestCase):
    def setUp(self):
        self.pub, self.deltas, self.fulls = build()

    def test_wrong_base_digest_same_version(self):
        # A forked v1 (different content, same version) receives the real v1->v2 delta.
        fork = Publisher()
        fork.publish([make_entry("other", 1, "forked content")])
        r = Receiver(); r.load_full(fork.state.full_bytes())
        self.assertEqual(r.state.version, 1)
        self.assertRejected(r, lambda: r.apply_delta(self.deltas[1]), "E_BASE_MISMATCH")

    def test_target_digest_mismatch(self):
        r = recv_at(self.fulls, 0)
        obj = json.loads(self.deltas[1]); obj["target_digest"] = "sha256:" + "0" * 64
        self.assertRejected(r, lambda: r.apply_delta(redigest_delta(obj)), "E_TARGET_MISMATCH")

    def test_truncated_and_corrupt(self):
        r = recv_at(self.fulls, 0)
        for b in (self.deltas[1][:-1], self.deltas[1][: len(self.deltas[1]) // 2], b""):
            self.assertRejected(r, lambda: r.apply_delta(b), "E_MALFORMED")
        flipped = self.deltas[1].replace(b"Starting", b"Startinh")
        self.assertRejected(r, lambda: r.apply_delta(flipped), "E_DIGEST")
        self.assertRejected(r, lambda: r.load_full(self.fulls[1].replace(b"Starting", b"Startinh")),
                            "E_DIGEST")
        self.assertRejected(r, lambda: r.load_full(self.fulls[1][:-3]), "E_MALFORMED")
        self.assertRejected(r, lambda: r.load_full(self.fulls[1] + b" "), "E_NONCANONICAL")
        pretty = json.dumps(json.loads(self.fulls[1]), indent=1).encode()
        self.assertRejected(r, lambda: r.load_full(pretty), "E_NONCANONICAL")
        self.assertRejected(r, lambda: r.load_full("é".encode() + self.fulls[1]), "E_MALFORMED")

    def test_entry_digest_tamper_resealed(self):
        r = recv_at(self.fulls, 0)
        obj = json.loads(self.deltas[1]); obj["entries"][0]["body"] = "ACK changed"
        self.assertRejected(r, lambda: r.apply_delta(redigest_delta(obj)), "E_DIGEST")

    def test_duplicate_json_keys(self):
        r = recv_at(self.fulls, 0)
        dup = self.deltas[1].replace(b'{"base_digest"', b'{"base_digest":"x","base_digest"', 1)
        self.assertRejected(r, lambda: r.apply_delta(dup), "E_DUP_KEY")

    def test_duplicate_delta_entries(self):
        r = recv_at(self.fulls, 0)
        obj = json.loads(self.deltas[1])
        obj["entries"] = [obj["entries"][0], obj["entries"][0], obj["entries"][1]]
        self.assertRejected(r, lambda: r.apply_delta(redigest_delta(obj)), "E_DUP_ENTRY")
        self.assertRaises(E1EError, self.pub.publish, [make_entry("zz", 1, "a"), make_entry("zz", 1, "a")])

    def test_illegal_version_reuse(self):
        r = recv_at(self.fulls, 1)  # holds ack v2
        alt = make_entry("ack", 2, "ACK: different content, same version")
        d = make_delta(r.state, [alt])
        self.assertRejected(r, lambda: r.apply_delta(d), "E_VERSION_REUSE")
        before = self.pub.state.fingerprint()
        alt3 = make_entry("lf", 1, "different lf v1 {k}", [("k", "int")])
        with self.assertRaises(E1EError) as cm:
            self.pub.publish([alt3])
        self.assertEqual(cm.exception.code, "E_VERSION_REUSE")
        self.assertEqual(self.pub.state.fingerprint(), before)
        # same body, changed parameter schema at same version is also reuse
        st = make_entry("status", 1, "status: job {job} is {state} after {n} steps",
                        [("job", "word"), ("state", "text"), ("n", "int")])
        self.assertNotEqual(st["digest"], self.pub.state.entries["status"]["digest"])
        self.assertRejected(r, lambda: r.apply_delta(make_delta(r.state, [st])), "E_VERSION_REUSE")

    def test_version_skip_and_regress(self):
        r = recv_at(self.fulls, 1)
        self.assertRejected(r, lambda: r.apply_delta(make_delta(r.state, [make_entry("ack", 4, "x")])), "E_VERSION")
        self.assertRejected(r, lambda: r.apply_delta(make_delta(r.state, [make_entry("new", 2, "x")])), "E_VERSION")
        self.assertRejected(r, lambda: r.load_full(self.fulls[0]), "E_STALE")
        self.assertRejected(r, lambda: r.apply_delta(self.deltas[1]), "E_BASE_MISMATCH")  # replay
        r0 = recv_at(self.fulls, 0)  # v1 holder receiving the v2->v3 delta (gap)
        self.assertRejected(r0, lambda: r0.apply_delta(self.deltas[2]), "E_STALE")

    def test_publish_transactional(self):
        before = self.pub.state.fingerprint(); hist = dict(self.pub.history)
        good = make_entry("fresh", 1, "fresh")
        bad = dict(make_entry("bad", 1, "x")); bad["digest"] = "sha256:00"
        for batch in ([good, bad], [good, make_entry("ack", 9, "x")], []):
            self.assertRaises(E1EError, self.pub.publish, batch)
            self.assertEqual(self.pub.state.fingerprint(), before)
            self.assertEqual(self.pub.history, hist)

    def test_bad_template_schemas(self):
        for body, params in [("a {x", [("x", "text")]), ("a {x}{y}", [("x", "text"), ("y", "text")]),
                             ("a {x}", []), ("a } b", []), ("a {x} {x}", [("x", "text")]),
                             ("{x}", [("x", "text")]), ("a {X}", [("X", "text")]),
                             ("a {x}", [("x", "float")])]:
            with self.assertRaises(E1EError, msg=body):
                make_entry("t", 1, body, params, kind="template")


class Messages(RejectMixin, unittest.TestCase):
    def setUp(self):
        self.pub, self.deltas, self.fulls = build()
        self.r = recv_at(self.fulls, 2)
        self.st = self.r.state

    def test_malformed_parameters(self):
        for args in ({"job": "a b", "state": "ok", "n": 1}, {"job": "a", "state": "ok", "n": "1"},
                     {"job": "a", "state": "ok"}, {"job": "a", "state": "ok", "n": 1, "x": 1},
                     {"job": "a", "state": "ok", "n": True}, {"job": "", "state": "ok", "n": 1},
                     {"job": "a", "state": "ok", "n": 10**19}):
            self.assertRejected(self.r, lambda: decode_message(self.st, ref(self.st, "status", args)), "E_PARAM")
        self.assertRejected(self.r, lambda: decode_message(self.st, ref(self.st, "ack", {"x": "y"})), "E_PARAM")
        bad = b'{"args":{"job":"a","n":1.5,"state":"b"}}'
        self.assertRejected(self.r, lambda: decode_message(self.st, bad), "E_SCHEMA")

    def test_unknown_references(self):
        for w in (canonical({"format": "E1E-MSG/1", "type": "ref", "snap": self.st.digest, "id": "nope",
                             "v": 1, "entry": "sha256:00", "args": {}}),
                  ref(self.st, "ack", {}, v=1), ref(self.st, "ack", {}, digest="sha256:" + "1" * 64)):
            self.assertRejected(self.r, lambda: decode_message(self.st, w), "E_UNKNOWN_REF")
        self.assertRejected(self.r, lambda: decode_message(self.st, ref(self.st, "ack", {}, snap="sha256:ab")),
                            "E_STALE")

    def test_ambiguous_match_not_encoded(self):
        e = self.st.entries["pair"]
        m = "pair x and y and z"
        self.assertEqual(len(match_template(e, m)), 2)
        decl = self.r.declare()
        wire, info = encode(self.pub.history, decl, m.encode())
        self.assertNotEqual(info["reason"], "ref")
        self.assertIn(("pair", "ambiguous"), info["skipped"])
        self.assertEqual(decode_message(self.st, wire), m.encode())
        self.assertEqual(len(match_template(e, "pair x and y")), 1)

    def test_nfc_nfd_not_interchangeable(self):
        nfc, nfd = self.st.entries["uni-nfc"], self.st.entries["uni-nfd"]
        self.assertEqual(match_template(nfc, "cafe\u0301 note: t"), [])
        self.assertEqual(match_template(nfd, "caf\u00e9 note: t"), [])

    def test_wire_escaping_and_invalid_unicode(self):
        w = canonical({"format": "E1E-MSG/1", "type": "raw", "text": "a"})
        self.assertRejected(self.r, lambda: decode_message(self.st, w.replace(b'"a"', b'"\\ud800"')), "E_SCHEMA")
        self.assertRejected(self.r, lambda: decode_message(self.st, w.replace(b'"a"', b'"\\u0061"')), "E_NONCANONICAL")
        self.assertRejected(self.r, lambda: decode_message(self.st, b'{"b64":"AA=","format":"E1E-MSG/1","type":"raw"}'), "E_SCHEMA")


class ReceiverState(RejectMixin, unittest.TestCase):
    def setUp(self):
        self.pub, self.deltas, self.fulls = build()

    def test_stale_copy_receiver_falls_back(self):
        stale = recv_at(self.fulls, 0)  # honest v1 declaration, ack v1 only
        link = Link(self.pub.history, stale)
        m = b"ACK: task received.\nStarting now."  # only encodable with ack v2
        out, info = link.transmit(m)
        self.assertEqual(out, m)
        self.assertEqual(info["kind"], "raw")  # sender used the declared v1 snapshot, not its own v3
        self.assertIsNone(info["rejected"])

    def test_stale_declaration_rejected_then_fallback(self):
        r = recv_at(self.fulls, 1)
        old_decl = r.declare()
        r.apply_delta(self.deltas[2])  # receiver advanced after declaring
        link = Link(self.pub.history, r)
        m = b"status: job a is ok after 1 steps"
        before = r.state.fingerprint()
        out, info = link.transmit(m, declaration=old_decl)
        self.assertEqual(out, m)
        self.assertEqual(info["rejected"], "E_STALE")
        self.assertEqual(r.state.fingerprint(), before)
        t = link.totals()
        self.assertGreater(t["reject"], 0); self.assertGreater(t["fallback"], 0)
        self.assertEqual(t["all"], t["ref"] + t["reject"] + t["fallback"])

    def test_receiver_copy_diverged_from_declaration(self):
        # Receiver lies/mis-declares v2 while holding a fork: decoder must reject, fallback delivers.
        fork = Publisher(); fork.publish([make_entry("status", 1, "forked {x}!", [("x", "word")])])
        r = Receiver(); r.load_full(fork.state.full_bytes())
        v1 = parse_full(self.fulls[0])
        decl = {"version": 1, "digest": v1.digest}  # declares the real v1, holds a fork
        out, info = Link(self.pub.history, r).transmit(b"status: job a is ok after 1 steps", decl)
        self.assertEqual(out, b"status: job a is ok after 1 steps")
        self.assertEqual(info["rejected"], "E_STALE")

    def test_unknown_declaration_sends_raw(self):
        r = Receiver()
        out, info = Link(self.pub.history, r).transmit(b"ACK", {"version": 7, "digest": "sha256:zz"})
        self.assertEqual((out, info["reason"]), (b"ACK", "unknown_declared_snapshot"))


if __name__ == "__main__":
    unittest.main()


class ReviewR1Regressions(RejectMixin, unittest.TestCase):
    """Regressions for gpt_E1e_code_r1 findings and its requested extra coverage."""

    def setUp(self):
        self.pub, self.deltas, self.fulls = build()

    def _full(self, version, entries):
        return RepoState(version, {e["id"]: e for e in entries}).full_bytes()

    def test_full_load_cannot_delete(self):
        r = recv_at(self.fulls, 0)
        self.assertRejected(r, lambda: r.load_full(self._full(2, [])), "E_DELETION_DEFERRED")

    def test_full_load_fork_and_history_conflict(self):
        r = recv_at(self.fulls, 0)
        fork = list(parse_full(self.fulls[0]).entries.values()) + [make_entry("zzz", 1, "extra")]
        self.assertRejected(r, lambda: r.load_full(self._full(1, fork)), "E_FORK")
        conflict = [make_entry("ack", 1, "ACK other")] + [e for e in parse_full(self.fulls[0]).entries.values() if e["id"] != "ack"]
        self.assertRejected(r, lambda: r.load_full(self._full(2, conflict)), "E_VERSION_REUSE")

    def test_snapshots_do_not_alias(self):
        old = self.pub.history[parse_full(self.fulls[0]).digest]
        b0, d0 = old.full_bytes(), self.pub.state.full_bytes()
        old.entries["status"]["body"] = "changed"
        self.pub.state.entries["status"]["body"] = "changed"
        self.assertEqual((old.full_bytes(), self.pub.state.full_bytes()), (b0, d0))

    def test_bool_version_rejected(self):
        r = recv_at(self.fulls, 0); st = r.state
        e = st.entry("ack")
        w = canonical({"format": "E1E-MSG/1", "type": "ref", "snap": st.digest, "id": "ack", "v": True,
                       "entry": e["digest"], "args": {}})
        self.assertRejected(r, lambda: decode_message(st, w), "E_SCHEMA")

    def test_oversized_send_records_nothing(self):
        r = recv_at(self.fulls, 2); link = Link(self.pub.history, r)
        with self.assertRaises(E1EError) as cm:
            link.transmit(b"a" * 65537)
        self.assertEqual((cm.exception.code, link.frames), ("E_TOO_LARGE", []))

    def test_match_budget_and_candidate_limit(self):
        e = make_entry("p", 1, "x{a}y{b}y{c}z", [("a", "text"), ("b", "text"), ("c", "text")])
        self.assertIsNone(match_template(e, "x" + "y" * 400 + "q"))  # budget exhausted -> no match
        pub = Publisher()
        pub.publish([make_entry(f"c{i:02d}", 1, "hdr " + "h" * i + " {t}", [("t", "text")]) for i in range(12)])
        st = pub.state
        from e1e.codec import candidates
        cs = candidates(st, "hdr " + "h" * 11 + " body")
        self.assertEqual([c["id"] for c in cs], ["c11"])
        cs = candidates(st, "hdr ")
        self.assertEqual(cs, [])
        many = Publisher(); many.publish([make_entry(f"d{i:02d}", 1, "same {t}", [("t", "text")]) for i in range(12)])
        self.assertEqual([c["id"] for c in candidates(many.state, "same q")], [f"d{i:02d}" for i in range(8)])

    def test_candidates_do_not_alias(self):
        from e1e.codec import candidates
        st = self.pub.state; b0 = st.full_bytes()
        candidates(st, "status: job a is ok after 1 steps")[0]["body"] = "changed"
        self.assertEqual(st.full_bytes(), b0)
        self.assertEqual(parse_full(st.full_bytes()).digest, st.digest)

exec
/bin/bash -lc 'cat v6/e1e/e1e/canon.py v6/e1e/README_MECHANICS.md; git status --short; git rev-parse --short HEAD' in /workspace/e1e-gpt
 succeeded in 0ms:
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
# E1e CPU mechanics — fixture-tested mechanics draft — no corpus measurement or savings claim

What this is: a stdlib-only Python implementation of `SPEC_E1E_REPO_1.md` (package `e1e/`) plus unittest suites in
`tests/`. It follows `reviews/gpt_E1e_pilot_r1.md` §4 and the §3 corrections (delta duplicate IDs rejected, delta bound
to base full digest and checked against target digest, version progression and ID/version immutability, template
schema inside the entry digest).

What this is not: no real or private messages (none are approved; fixtures in `tests/fixtures.py` are synthetic),
no corpus, no compression baselines (zstd deliberately not used yet), no byte-saving numbers. With 64-hex digests
in every reference, refs are often *larger* than the raw envelope for these short fixtures; that is expected and is
not a measurement.

Run (CPU only, no dependencies): `cd v6/e1e && python3 -m unittest discover -s tests -t . -v`

Layout: `e1e/canon.py` (escaped canonical JSON, strict parse), `e1e/schema.py` (entries, templates, matching),
`e1e/repo.py` (state, full/delta, transactional ops, publisher/receiver), `e1e/codec.py` (encode/verify/decode,
fallback, link accounting). Tests: `tests/test_roundtrip.py` (successful-path evidence) and
`tests/test_rejections.py` (rejection boundaries, each asserting unchanged state). Results are reported separately.
eb50a87

exec
/bin/bash -lc 'PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -t . -v' in /workspace/e1e-gpt/v6/e1e
 succeeded in 0ms:
test_bad_template_schemas (tests.test_rejections.Artifacts.test_bad_template_schemas) ... ok
test_duplicate_delta_entries (tests.test_rejections.Artifacts.test_duplicate_delta_entries) ... ok
test_duplicate_json_keys (tests.test_rejections.Artifacts.test_duplicate_json_keys) ... ok
test_entry_digest_tamper_resealed (tests.test_rejections.Artifacts.test_entry_digest_tamper_resealed) ... ok
test_illegal_version_reuse (tests.test_rejections.Artifacts.test_illegal_version_reuse) ... ok
test_publish_transactional (tests.test_rejections.Artifacts.test_publish_transactional) ... ok
test_target_digest_mismatch (tests.test_rejections.Artifacts.test_target_digest_mismatch) ... ok
test_truncated_and_corrupt (tests.test_rejections.Artifacts.test_truncated_and_corrupt) ... ok
test_version_skip_and_regress (tests.test_rejections.Artifacts.test_version_skip_and_regress) ... ok
test_wrong_base_digest_same_version (tests.test_rejections.Artifacts.test_wrong_base_digest_same_version) ... ok
test_ambiguous_match_not_encoded (tests.test_rejections.Messages.test_ambiguous_match_not_encoded) ... ok
test_malformed_parameters (tests.test_rejections.Messages.test_malformed_parameters) ... ok
test_nfc_nfd_not_interchangeable (tests.test_rejections.Messages.test_nfc_nfd_not_interchangeable) ... ok
test_unknown_references (tests.test_rejections.Messages.test_unknown_references) ... ok
test_wire_escaping_and_invalid_unicode (tests.test_rejections.Messages.test_wire_escaping_and_invalid_unicode) ... ok
test_receiver_copy_diverged_from_declaration (tests.test_rejections.ReceiverState.test_receiver_copy_diverged_from_declaration) ... ok
test_stale_copy_receiver_falls_back (tests.test_rejections.ReceiverState.test_stale_copy_receiver_falls_back) ... ok
test_stale_declaration_rejected_then_fallback (tests.test_rejections.ReceiverState.test_stale_declaration_rejected_then_fallback) ... ok
test_unknown_declaration_sends_raw (tests.test_rejections.ReceiverState.test_unknown_declaration_sends_raw) ... ok
test_bool_version_rejected (tests.test_rejections.ReviewR1Regressions.test_bool_version_rejected) ... ok
test_candidates_do_not_alias (tests.test_rejections.ReviewR1Regressions.test_candidates_do_not_alias) ... ok
test_full_load_cannot_delete (tests.test_rejections.ReviewR1Regressions.test_full_load_cannot_delete) ... ok
test_full_load_fork_and_history_conflict (tests.test_rejections.ReviewR1Regressions.test_full_load_fork_and_history_conflict) ... ok
test_match_budget_and_candidate_limit (tests.test_rejections.ReviewR1Regressions.test_match_budget_and_candidate_limit) ... ok
test_oversized_send_records_nothing (tests.test_rejections.ReviewR1Regressions.test_oversized_send_records_nothing) ... ok
test_snapshots_do_not_alias (tests.test_rejections.ReviewR1Regressions.test_snapshots_do_not_alias) ... ok
test_crlf_lf_distinct (tests.test_roundtrip.RoundTrip.test_crlf_lf_distinct) ... ok
test_deltas_from_empty_equal_full (tests.test_roundtrip.RoundTrip.test_deltas_from_empty_equal_full) ... ok
test_full_plus_deltas_equals_target_full (tests.test_roundtrip.RoundTrip.test_full_plus_deltas_equals_target_full) ... ok
test_joiner_full_sync_then_roundtrips (tests.test_roundtrip.RoundTrip.test_joiner_full_sync_then_roundtrips) ... ok
test_serialization_stable (tests.test_roundtrip.RoundTrip.test_serialization_stable) ... ok
test_specific_refs_are_exact (tests.test_roundtrip.RoundTrip.test_specific_refs_are_exact) ... ok

----------------------------------------------------------------------
Ran 32 tests in 0.072s

OK

exec
/bin/bash -lc "PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
from e1e.repo import Publisher, parse_full, RepoState
from e1e.schema import make_entry
from e1e.codec import candidates
p = Publisher()
e = make_entry('a', 1, 'hello {x}', [('x', 'text')])
p.publish([e])
st = p.state
before = st.fingerprint()
for value in (st.entries['a'], st.entry('a'), candidates(st, 'hello world')[0]):
    value['params'][0]['type'] = 'word'
    value['body'] = 'changed'
e['params'][0]['type'] = 'word'
st.seen.clear()
assert st.fingerprint() == before
print('Nested copies, publish input and seen isolation: PASS')
st.version = 99
print('Public version reassignment changes fingerprint:', st.fingerprint() "'!= before)
try:
    parse_full(st.full_bytes())
except Exception as exc:
    print('"'Reparsing snapshot after reassignment:', exc)
st.version = before[0]
st.digest = 'sha256:' + '0' * 64
print('Publisher history key now differs from held snapshot digest:', next(k for k, v in p.history.items() if v is st) "'!= st.digest)
PY' in /workspace/e1e-gpt/v6/e1e
 succeeded in 0ms:
Nested copies, publish input and seen isolation: PASS
Public version reassignment changes fingerprint: True
Reparsing snapshot after reassignment: E_DIGEST: full snapshot digest mismatch
Publisher history key now differs from held snapshot digest: True

codex
**Verdict: needs fixes** for the requested immutable snapshot guarantee.

Read all four requested files in full. The candidate fix is correct: deep copies protect nested parameter dictionaries too. Constructor inputs, `entries`, `entry()`, and `seen` expose no remaining entry aliases. **All 32 tests pass.**

One **medium** finding remains: [RepoState.version and digest](/workspace/e1e-gpt/v6/e1e/e1e/repo.py:25) are publicly writable. Reproduced `st.version = 99`: `st.full_bytes()` then fails parsing with `E_DIGEST`. Assigning `st.digest` also invalidates the publisher history’s digest-to-snapshot association. Make both read-only properties and add reassignment regression coverage.

I missed this metadata mutation path in r2. No other blockers found for a fixture-tested mechanics draft.
