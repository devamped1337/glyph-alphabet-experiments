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


def declare_wire(decl):
    """Canonical receiver snapshot declaration frame (E1E-MSG/1 type 'declare')."""
    d = decl if isinstance(decl, dict) else {}
    return canonical({"format": MSG_FORMAT, "type": "declare", "version": d.get("version"), "digest": d.get("digest")})


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

    def __init__(self, known, receiver, require_smaller=True, codec=None):
        """require_smaller=True is the audit policy (plan section 8, Stefan 2026-10-23). codec: a
        baselines.ZstdCodec enables the baseline-6 three-way selection; None sends uncompressed (baseline 5)."""
        self._known, self._receiver = known, receiver
        self._require_smaller, self._codec = require_smaller, codec
        self._frames = []  # (direction, kind, nbytes)
        self._last_decl = None

    known = property(lambda self: self._known)
    receiver = property(lambda self: self._receiver)

    @property
    def frames(self):
        """Read-only copy of the accounting log."""
        return tuple(self._frames)

    def transmit(self, msg, declaration=None):
        if len(msg) > MAX_MESSAGE_BYTES:
            raise E1EError("E_TOO_LARGE", "message exceeds MAX_MESSAGE_BYTES; nothing is sent")
        decl = self._receiver.declare() if declaration is None else declaration
        if decl != self._last_decl:  # receiver -> sender declaration frame, charged when it changes
            self._frames.append(("back", "declare", len(declare_wire(decl))))
            self._last_decl = dict(decl) if isinstance(decl, dict) else decl
        if self._codec is None:
            wire, info = encode(self._known, decl, msg, require_smaller=self._require_smaller)
            kind = "ref" if info["reason"] == "ref" else "raw"
        else:  # baseline 6: the ref competes after compression, so do not pre-filter by uncompressed size
            from .baselines import select_b6
            ref, info = encode(self._known, decl, msg, require_smaller=False)
            wire, kind = select_b6(ref if info["reason"] == "ref" else None, raw_wire(msg), self._codec)
            if kind != "zstd_ref" and info["reason"] == "ref":
                info["reason"] = "ref_not_smaller"
        self._frames.append(("fwd", kind, len(wire)))  # only the selected send is billed
        before = self._receiver.state.fingerprint()
        try:
            if self._codec is None:
                out = decode_message(self._receiver.state, wire)
            else:
                from .baselines import unwrap
                out = decode_message(self._receiver.state, unwrap(wire, self._codec))
            rejected = None
        except E1EError as err:
            rejected = err.code
            rej = reject_wire(err.code, wire)
            self._frames.append(("back", "reject", len(rej)))
            fb = raw_wire(msg)
            self._frames.append(("fwd", "fallback", len(fb)))
            out = decode_message(self._receiver.state, fb)
        assert self._receiver.state.fingerprint() == before  # decoding never mutates state
        return out, {"kind": kind, "rejected": rejected, "reason": info["reason"]}

    def totals(self):
        t = {}
        for d, k, n in self._frames:
            t[k] = t.get(k, 0) + n
        t["all"] = sum(n for _, _, n in self._frames)
        return t


def transmit(known, receiver, msg, declaration=None):
    return Link(known, receiver).transmit(msg, declaration)
