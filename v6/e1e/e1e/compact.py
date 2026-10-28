"""E1F-MSG/1 compact frames (E1F_PROPOSAL_DRAFT.md section 3; additive, E1E-MSG/1 is unchanged).

Frame discrimination (section 3.1): 0x7B '{' = E1E-MSG/1 JSON envelope, 0x28B52FFD = zstd frame, 0x01 = E1F compact.
Compact body (section 3.2): 0x01, varint epoch, then 1..256 segments (LIT 0x02 / REF 0x01), no end marker.
Every frame on a link is preceded by a canonical LEB128 length prefix (section 3.1), charged by the link accounting.

New error codes introduced here (the E1E-MSG/1 decoder never raises them): E_TRUNCATED, E_RANGE.
E_NONCANONICAL, E_SCHEMA, E_STALE, E_UNKNOWN_REF, E_PARAM, E_TOO_LARGE, E_FORK are existing codes reused.
Where the frozen spec text is silent the most literal reading is implemented and recorded in E1F_BUILD_NOTES.md.
"""
import bisect
import collections
import heapq

from .canon import E1EError
from .codec import MAX_MESSAGE_BYTES, decode_message, declare_wire, raw_wire, reject_wire
from .repo import Receiver, RepoState
from .schema import INT_RE, WORD_RE, match_template, parse_template

NEW_ERROR_CODES = ("E_TRUNCATED", "E_RANGE")
DISC_COMPACT = 0x01
DISC_JSON = 0x7B
ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"
OP_REF = 0x01
OP_LIT = 0x02
MAX_COMPACT_FRAME = 65536
MAX_SEGMENTS = 256
MAX_PREFIX_BYTES = 5
MAX_U32 = 2**32 - 1
MAX_U64 = 2**64 - 1
CANDIDATE_CAP = 4096
END_TRIES = 64
INT_DOMAIN = 10**18  # |n| < 10^18


# ---------------------------------------------------------------- varint / zigzag
def encode_varint(n, max_bytes=MAX_PREFIX_BYTES, max_value=MAX_U32):
    if type(n) is not int or n < 0 or n > max_value:
        raise E1EError("E_RANGE", "varint value out of range")
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            break
    if len(out) > max_bytes:
        raise E1EError("E_RANGE", "varint too wide")
    return bytes(out)


def read_varint(buf, pos, max_bytes=MAX_PREFIX_BYTES, max_value=MAX_U32):
    """Unsigned LEB128, shortest form only. Returns (value, new_pos).
    Run out of bytes -> E_TRUNCATED; more than max_bytes or value > max_value -> E_RANGE;
    a final 0x00 group after a continuation -> E_NONCANONICAL. Checks happen in byte order."""
    n = 0
    for i in range(max_bytes):
        if pos + i >= len(buf):
            raise E1EError("E_TRUNCATED", "varint cut off")
        b = buf[pos + i]
        n |= (b & 0x7F) << (7 * i)
        if not b & 0x80:
            if b == 0 and i > 0:
                raise E1EError("E_NONCANONICAL", "varint is not the shortest encoding")
            if n > max_value:
                raise E1EError("E_RANGE", "varint exceeds maximum value")
            return n, pos + i + 1
    raise E1EError("E_RANGE", "varint wider than the maximum width")


def zigzag(n):
    if type(n) is not int or not -INT_DOMAIN < n < INT_DOMAIN:
        raise E1EError("E_PARAM", "int argument outside the E1E-REPO/1 int domain")
    return n * 2 if n >= 0 else -n * 2 - 1


def unzigzag(z):
    return (z >> 1) ^ -(z & 1)


def encode_zigzag(n):
    return encode_varint(zigzag(n), 10, MAX_U64)


# ---------------------------------------------------------------- length-prefix framing (section 3.1)
def frame(payload):
    """Length prefix (canonical LEB128 of len(payload), at most 5 bytes) + payload."""
    return encode_varint(len(payload)) + bytes(payload)


def prefix_len(n):
    return len(encode_varint(n))


def read_frame(buf, pos=0):
    """Read one frame from buf at pos. Returns (payload, new_pos). The declared length is checked
    against the bytes actually remaining before anything is sliced or allocated."""
    n, p = read_varint(buf, pos)
    if n > len(buf) - p:
        raise E1EError("E_TRUNCATED", f"frame declares {n} bytes but only {len(buf) - p} remain")
    return bytes(buf[p:p + n]), p + n


# ---------------------------------------------------------------- snapshot view (ordinals, templates)
class _Snap:
    """Cached per-snapshot view: ordinal-ordered entries, parsed templates, compiled regexes."""

    def __init__(self, state):
        self.state = state
        self.entries = [state._e[k] for k in sorted(state._e)]  # ordinal = index (id ascending by code point)
        self.toks = []
        self._enc = None
        for e in self.entries:
            self.toks.append(parse_template(e["body"], e["params"]) if e["kind"] == "template" else None)
        self._match = None

    def matcher(self):
        if self._match is None:
            self._match = _build_matchers(self)
        return self._match


_SNAP_CACHE = collections.OrderedDict()


def snap_view(state):
    key = state.digest
    v = _SNAP_CACHE.get(key)
    if v is None:
        v = _Snap(state)
        _SNAP_CACHE[key] = v
        while len(_SNAP_CACHE) > 48:
            _SNAP_CACHE.popitem(last=False)
    else:
        _SNAP_CACHE.move_to_end(key)
    return v


def _render(entry, toks, args):
    if toks is None:
        return entry["body"]
    return "".join(t[1] if t[0] == "lit" else str(args[t[1]]) for t in toks)


# ---------------------------------------------------------------- decoder (sections 3.2, 3.3)
def _read_args(entry, buf, pos):
    args = {}
    for p in entry["params"]:
        typ, name = p["type"], p["name"]
        if typ == "int":
            z, pos = read_varint(buf, pos, 10, MAX_U64)
            n = unzigzag(z)
            if not -INT_DOMAIN < n < INT_DOMAIN:
                raise E1EError("E_PARAM", "int argument outside the int domain")
            args[name] = n
            continue
        ln, pos = read_varint(buf, pos)
        if ln < 1:
            raise E1EError("E_PARAM", f"empty {typ} argument")
        if ln > len(buf) - pos:
            raise E1EError("E_TRUNCATED", "argument length exceeds the remaining frame")
        raw = bytes(buf[pos:pos + ln])
        pos += ln
        if typ == "word":
            try:
                s = raw.decode("ascii")
            except UnicodeDecodeError:
                raise E1EError("E_PARAM", "word argument is not ASCII")
            if not WORD_RE.match(s):
                raise E1EError("E_PARAM", "word argument has characters outside [A-Za-z0-9_.-]")
        else:
            try:
                s = raw.decode("utf-8", "strict")
            except UnicodeDecodeError:
                raise E1EError("E_PARAM", "text argument is not valid UTF-8")
        args[name] = s
    return args, pos


def decode_compact(payload, resolve):
    """Decode a compact frame body (without the length prefix). `resolve(epoch)` returns the RepoState
    the receiver retains for that epoch, or None. Returns the message bytes or raises E1EError.
    Parsing is sequential in byte order: first byte, epoch varint checks, E_STALE, then each segment
    (opcode E_SCHEMA, varint checks, ordinal E_UNKNOWN_REF, args E_PARAM), then the reconstructed size."""
    if len(payload) < 1:
        raise E1EError("E_SCHEMA", "empty frame: no discriminator byte")
    if payload[0] != DISC_COMPACT:
        raise E1EError("E_SCHEMA", "not a compact frame")
    if len(payload) > MAX_COMPACT_FRAME:
        raise E1EError("E_TOO_LARGE", "compact frame exceeds 65536 bytes")
    epoch, pos = read_varint(payload, 1)
    state = resolve(epoch) if epoch >= 1 else None
    if state is None:
        raise E1EError("E_STALE", f"epoch {epoch} is not a retained snapshot")
    view = snap_view(state)
    if pos >= len(payload):
        raise E1EError("E_SCHEMA", "compact frame has no segments")
    pieces, total, nseg, oversize = [], 0, 0, False
    end = len(payload)
    while pos < end:
        if nseg >= MAX_SEGMENTS:
            raise E1EError("E_TOO_LARGE", "more than 256 segments")
        nseg += 1
        op = payload[pos]
        pos += 1
        if op == OP_LIT:
            n, pos = read_varint(payload, pos)
            if n < 1:
                raise E1EError("E_SCHEMA", "LIT with length 0")
            if n > end - pos:
                raise E1EError("E_TRUNCATED", "LIT length exceeds the remaining frame")
            chunk = bytes(payload[pos:pos + n])
            pos += n
            try:
                chunk.decode("utf-8", "strict")
            except UnicodeDecodeError:
                raise E1EError("E_SCHEMA", "LIT bytes are not valid UTF-8 on their own")
        elif op == OP_REF:
            ordn, pos = read_varint(payload, pos)
            if ordn >= len(view.entries):
                raise E1EError("E_UNKNOWN_REF", f"ordinal {ordn} not in snapshot of {len(view.entries)} entries")
            entry = view.entries[ordn]
            args, pos = _read_args(entry, payload, pos)
            # rendering is bounded (<= 16384 code points + args taken from the frame); once the total is over
            # the limit nothing more is retained, but the rest of the frame is still validated (error precedence)
            chunk = b"" if oversize else _render(entry, view.toks[ordn], args).encode("utf-8")
        else:
            raise E1EError("E_SCHEMA", f"unknown opcode 0x{op:02x}")
        total += len(chunk)
        if total > MAX_MESSAGE_BYTES:
            oversize = True
            pieces = []  # stop retaining output; the error is raised after the rest of the frame is validated
        elif not oversize:
            pieces.append(chunk)
    if oversize:
        raise E1EError("E_TOO_LARGE", "reconstructed message exceeds 65536 bytes")
    return b"".join(pieces)


def decode_frame(payload, resolve, current_state=None, zstd_codec=None):
    """Dispatch on the first byte (section 3.1). `current_state` serves E1E-MSG/1 envelopes."""
    if len(payload) < 1:
        raise E1EError("E_SCHEMA", "empty frame: no discriminator byte")
    b = payload[0]
    if b == DISC_COMPACT:
        return decode_compact(payload, resolve)
    if b == DISC_JSON:
        return decode_message(current_state if current_state is not None else RepoState(), payload)
    if payload[:4] == ZSTD_MAGIC:
        if zstd_codec is None:
            raise E1EError("E_SCHEMA", "zstd frame without a codec")
        out = zstd_codec.decompress(payload)
        if len(out) > MAX_MESSAGE_BYTES:
            raise E1EError("E_TOO_LARGE", "decompressed message too large")
        return out
    raise E1EError("E_SCHEMA", f"unknown first byte 0x{b:02x}")


class CompactReceiver(Receiver):
    """An E1E receiver that retains its current snapshot and the immediately previous one (section 3.3).
    State changes go only through the validated load_full / apply_delta of E1E-REPO/1."""

    def __init__(self, state=None):
        super().__init__(state)
        self._previous = None

    @property
    def previous(self):
        return self._previous

    def _rotate(self, old):
        if (self._state.version != old.version or self._state.digest != old.digest) and old.version >= 1:
            self._previous = old  # the empty version-0 repository is not a snapshot an epoch can name

    def load_full(self, data):
        old = self._state
        new = super().load_full(data)
        self._rotate(old)
        return new

    def apply_delta(self, data):
        old = self._state
        new = super().apply_delta(data)
        self._rotate(old)
        return new

    def resolve(self, epoch):
        for s in (self._state, self._previous):
            if s is not None and s.version == epoch:
                return s
        return None

    def decode(self, payload, zstd_codec=None):
        return decode_frame(payload, self.resolve, self._state, zstd_codec)


# ---------------------------------------------------------------- matching machinery for the encoder
def eligible_segmented(entry, toks):
    """Section 3.5: body ends in a literal character and all params are int or word."""
    if entry["kind"] != "template":
        return False
    return toks[-1][0] == "lit" and all(p["type"] in ("int", "word") for p in entry["params"])


_FIRST_CLASS = {"int": frozenset("-0123456789"), "word": frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-")}
MATCH_CALL_CAP = 4096  # amendment A1: at most this many E1E matcher (match_template) invocations per message; each is bounded by the E1E step budget
MATCH_WORK_CAP = 1 << 20  # amendment A1: and at most this many characters summed over the spans handed to the matcher per message
EVAL_CAP = 65536  # section 3.5 amendment A1: at most this many template (offset, entry) evaluations per message


class _M:
    __slots__ = ("kind", "body", "entry", "toks", "last", "lead", "tail", "whole_only", "first_cls", "lit1")


def _build_matchers(view):
    out = []
    for i, e in enumerate(view.entries):
        m = _M()
        m.entry, m.toks = e, view.toks[i]
        if e["kind"] == "literal":
            m.kind, m.body = "lit", e["body"]
        else:
            m.kind = "tpl"
            toks = view.toks[i]
            m.lead = toks[0][1] if toks[0][0] == "lit" else ""
            m.tail = toks[-1][1] if toks[-1][0] == "lit" else ""
            m.whole_only = not eligible_segmented(e, toks)
            if not m.whole_only:
                types = {p["name"]: p["type"] for p in e["params"]}
                m.last = toks[-1][1][-1]
                m.first_cls = _FIRST_CLASS[types[toks[0][1]]] if toks[0][0] == "param" else None
                m.lit1 = toks[1][1] if toks[0][0] == "param" else None
        out.append(m)
    return out


def _char_to_byte_offsets(text):
    if text.isascii():
        return None
    offs, b = [], 0
    for c in text:
        offs.append(b)
        b += len(c.encode("utf-8"))
    offs.append(b)
    return offs


def _encode_args(entry, args):
    out = bytearray()
    for p in entry["params"]:
        v = args[p["name"]]
        if p["type"] == "int":
            out += encode_zigzag(v)
        else:
            b = v.encode("utf-8")
            out += encode_varint(len(b)) + b
    return bytes(out)


def template_end(m, e, text, s, lastpos, tries=END_TRIES, budget=None):
    """Section 3.5 template end search at start s: ends after occurrences of the last literal character, tried in
    descending order, at most `tries` of them; the first with exactly one parse wins. Returns (end, parse) or None.
    `lastpos` is a per-message cache {char: [positions]}. `budget` (optional [calls, chars, calls_made] list) counts down the per-message
    matcher invocations and the summed span lengths handed to the matcher; when either is exhausted no further matcher
    call is made (the search returns None and calls is set to 0)."""
    lp = lastpos.get(m.last)
    if lp is None:
        lp = [i for i, c in enumerate(text) if c == m.last]
        lastpos[m.last] = lp
    lo = bisect.bisect_left(lp, s)
    hi = len(lp) - 1
    t = 0
    tail = m.tail
    while hi >= lo and t < tries:
        end = lp[hi] + 1
        hi -= 1
        t += 1
        # necessary conditions only (linear time, no backtracking); the E1E matcher, under its own step budget, decides
        if end - s < len(tail) or not text.endswith(tail, s, end):
            continue
        if budget is not None:
            if budget[0] <= 0 or budget[1] < end - s:
                budget[0] = 0
                return None
            budget[0] -= 1
            budget[1] -= end - s
            budget[2] += 1
        parses = match_template(e, text[s:end])
        if parses is not None and len(parses) == 1:
            return end, parses[0]
    return None


def template_starts(m, text):
    """Ascending start offsets (chars) where an eligible template can possibly match: a linear-time necessary
    condition (leading literal occurs at s; or, for a leading param, the first character is in its class and the
    following literal still occurs later). The matcher decides; this never produces a non-superset."""
    if m.lead:
        i = text.find(m.lead)
        while i >= 0:
            yield i
            i = text.find(m.lead, i + 1)
    else:
        lim = text.rfind(m.lit1)
        cls = m.first_cls
        for s in range(min(len(text), lim)):  # the literal must start at >= s + 1, so s <= lim - 1
            if text[s] in cls:
                yield s


def entry_matcher(entry):
    """Matcher record for one entry (same construction the snapshot view uses)."""
    class _V:
        pass
    v = _V()
    v.entries = [entry]
    v.toks = [parse_template(entry["body"], entry["params"]) if entry["kind"] == "template" else None]
    return _build_matchers(v)[0]


def _literal_starts(body, text):
    i = text.find(body)
    while i >= 0:
        yield i
        i = text.find(body, i + 1)


def find_candidates(state, text, cap=CANDIDATE_CAP, tries=END_TRIES, eval_cap=EVAL_CAP, match_cap=MATCH_CALL_CAP, work_cap=MATCH_WORK_CAP):
    """Section 3.5 enumeration for a snapshot and a str message. Returns (candidates, stats); a candidate is
    (start_char, end_char, ordinal, ref_bytes) in enumeration order: ascending offset, then ascending ordinal.
    (offset, entry) pairs are produced incrementally from per-entry start iterators merged in that order (never all
    materialised); enumeration stops as soon as `cap` candidates exist. stats: candidates, cap_hit (stopped with at
    least one unexamined prefiltered pair left), entries_pending (entries that still had an unexamined start),
    template_evaluations, eval_cap_hit (template evaluations reached `eval_cap`; enumeration stopped there),
    matcher_calls, matcher_span_chars (summed span characters actually handed to the matcher), match_cap_hit (matcher invocations or summed span characters reached `match_cap`/`work_cap`; template
    candidates after that point are not generated)."""
    view = snap_view(state)
    ms = view.matcher()
    n = len(text)
    lastpos = {}
    heap, iters = [], {}
    for o, m in enumerate(ms):
        if m.kind == "lit":
            if len(m.body) > n:
                continue
            it = _literal_starts(m.body, text)
        elif m.whole_only:
            if n >= 1 and text.startswith(m.lead) and text.endswith(m.tail):
                it = iter((0,))
            else:
                continue
        else:
            it = template_starts(m, text)
        first = next(it, None)
        if first is not None:
            iters[o] = it
            heap.append((first, o))
    heapq.heapify(heap)
    cands, evals, cap_hit, eval_hit, match_hit = [], 0, False, False, False
    budget = [match_cap, work_cap, 0]  # calls left, chars left, calls made
    while heap:
        if len(cands) >= cap:
            cap_hit = True
            break
        s, o = heap[0]
        m = ms[o]
        if m.kind == "tpl":
            if evals >= eval_cap or budget[0] <= 0:
                # template work is exhausted: drop every remaining template iterator, literals continue unaffected
                eval_hit = eval_hit or evals >= eval_cap
                match_hit = match_hit or budget[0] <= 0
                heap = [(x, q) for x, q in heap if ms[q].kind == "lit"]
                heapq.heapify(heap)
                continue
            evals += 1
        nxt = next(iters[o], None)
        if nxt is None:
            heapq.heappop(heap)
            del iters[o]
        else:
            heapq.heapreplace(heap, (nxt, o))
        e = view.entries[o]
        if m.kind == "lit":
            cands.append((s, s + len(m.body), o, bytes([OP_REF]) + encode_varint(o)))
        elif m.whole_only:
            if budget[0] <= 0 or budget[1] < n:
                budget[0] = 0
                match_hit = True  # the budget suppressed this whole-message match: report it
                continue
            budget[0] -= 1
            budget[1] -= n
            budget[2] += 1
            parses = match_template(e, text)
            if parses is not None and len(parses) == 1:
                cands.append((0, n, o, bytes([OP_REF]) + encode_varint(o) + _encode_args(e, parses[0])))
        else:
            hit = template_end(m, e, text, s, lastpos, tries, budget)
            if hit is None and budget[0] <= 0:
                match_hit = True
            if hit is not None:
                end, parse = hit
                cands.append((s, end, o, bytes([OP_REF]) + encode_varint(o) + _encode_args(e, parse)))
    return cands, {"candidates": len(cands), "cap_hit": cap_hit, "entries_pending": len(heap),
                   "template_evaluations": evals, "eval_cap_hit": eval_hit,
                   "matcher_calls": budget[2], "matcher_span_chars": work_cap - budget[1],
                   "match_cap_hit": match_hit}


def plan_segments(text, cands):
    """Greedy selection (section 3.5). Returns the list of ('lit', bytes) / ('ref', ref_bytes, covered_bytes)."""
    boff = _char_to_byte_offsets(text)
    bo = (lambda i: i) if boff is None else (lambda i: boff[i])
    good = []
    for s, e, o, ref in cands:
        saved = (bo(e) - bo(s)) - len(ref)
        if saved > 0:
            good.append((s, e, o, ref, saved))
    segs, pos, i, n = [], 0, 0, len(good)
    data = text.encode("utf-8")
    while True:
        while i < n and good[i][0] < pos:
            i += 1
        if i >= n:
            break
        s0, j = good[i][0], i
        best = None
        while j < n and good[j][0] == s0:
            c = good[j]
            key = (-c[4], -(c[1] - c[0]), c[2])  # saved desc, longer span, lower ordinal
            if best is None or key < best[0]:
                best = (key, c)
            j += 1
        s, e, o, ref, saved = best[1]
        if s > pos:
            segs.append(("lit", data[bo(pos):bo(s)]))
        segs.append(("ref", ref, bo(e) - bo(s)))
        pos, i = e, j
    if pos < len(text):
        segs.append(("lit", data[bo(pos):]))
    return segs


def build_frame(epoch, segs):
    out = bytearray([DISC_COMPACT]) + encode_varint(epoch)
    for sg in segs:
        if sg[0] == "lit":
            out += bytes([OP_LIT]) + encode_varint(len(sg[1])) + sg[1]
        else:
            out += sg[1]
    return bytes(out)


def send_rule(compact_payload, raw_payload):
    """Section 3.5: among {compact, raw envelope} send the strictly smaller; ties go to the raw envelope."""
    if len(compact_payload) < len(raw_payload):
        return compact_payload, "compact"
    return raw_payload, "raw"


def encode(known, declaration, msg):
    """Arm 7 sender. `known` maps snapshot digest -> RepoState the sender holds; `declaration` is the receiver's
    {"version","digest"}. Returns (payload, info). payload is a compact frame body or the raw E1E-MSG/1 envelope
    (always the JSON envelope); the strictly smaller wins, ties go to the raw envelope (section 3.5).
    info: reason, kind ('compact'|'raw'), covered_bytes, refs, plus matcher stats."""
    info = {"reason": None, "kind": "raw", "covered_bytes": 0, "refs": 0, "ref_bytes": 0, "lit_segments": 0}
    if len(msg) > MAX_MESSAGE_BYTES:
        raise E1EError("E_TOO_LARGE", "message exceeds MAX_MESSAGE_BYTES; nothing is sent")
    raw = raw_wire(msg)
    if not msg:
        info["reason"] = "empty_message"
        return raw, info
    snap = known.get(declaration.get("digest")) if isinstance(declaration, dict) else None
    if snap is None or snap.version != declaration.get("version") or snap.version < 1:
        info["reason"] = "unknown_declared_snapshot"
        return raw, info
    try:
        text = msg.decode("utf-8", "strict")
    except UnicodeDecodeError:
        info["reason"] = "not_utf8"
        return raw, info
    cands, st = find_candidates(snap, text)
    info.update(st)
    segs = plan_segments(text, cands)
    payload = build_frame(snap.version, segs)
    try:  # verification by the real decoder, including the epoch rule
        ok = decode_compact(payload, lambda ep: snap if ep == snap.version else None) == msg
    except E1EError as err:
        ok = False
        info["verify_error"] = err.code
    if not ok:
        info["reason"] = "verify_failed"
        return raw, info
    chosen, kind = send_rule(payload, raw)
    if kind == "raw":
        info["reason"] = "compact_not_smaller"
        return raw, info
    info["reason"] = "compact"
    info["kind"] = "compact"
    refs = [s for s in segs if s[0] == "ref"]
    info["refs"] = len(refs)
    info["covered_bytes"] = sum(s[2] for s in refs)
    info["ref_bytes"] = sum(len(s[1]) for s in refs)
    info["lit_segments"] = len(segs) - len(refs)
    info["segments"] = len(segs)
    return payload, info


# ---------------------------------------------------------------- link accounting (arm 7)
class CompactLink:
    """One sender->receiver channel for arm 7 with byte accounting of every frame. Every frame is charged its
    payload bytes under its kind plus its canonical length prefix under 'prefix' (reported as its own line).
    Kinds: compact, raw (first sends); declare, reject (receiver->sender); fallback (re-send after a reject)."""

    def __init__(self, known, receiver):
        self._known, self._receiver = known, receiver
        self._frames = []  # (direction, kind, payload_bytes, prefix_bytes)
        self._last_decl = None

    receiver = property(lambda self: self._receiver)

    @property
    def frames(self):
        return tuple(self._frames)

    def _charge(self, direction, kind, payload):
        self._frames.append((direction, kind, len(payload), prefix_len(len(payload))))

    def _declare(self, decl):
        if decl != self._last_decl:
            self._charge("back", "declare", declare_wire(decl))
            self._last_decl = dict(decl) if isinstance(decl, dict) else decl

    def deliver(self, payload, original, kind=None):
        """Send `payload` as the first frame for `original`; on a reject the sender re-sends the original as the
        raw envelope (charged). Returns (decoded bytes, rejection code or None)."""
        k = kind or ("compact" if payload[:1] == bytes([DISC_COMPACT]) else "raw")
        self._charge("fwd", k, payload)
        before = self._receiver.state.fingerprint()
        try:
            out, rejected = self._receiver.decode(payload), None
            if out != original:
                raise E1EError("E_SCHEMA", "decoded bytes differ from the original")
        except E1EError as err:
            rejected = err.code
            self._charge("back", "reject", reject_wire(err.code, payload))
            fb = raw_wire(original)
            self._charge("fwd", "fallback", fb)
            out = decode_message(self._receiver.state, fb)
        assert self._receiver.state.fingerprint() == before
        return out, rejected

    def transmit(self, msg, declaration=None):
        decl = self._receiver.declare() if declaration is None else declaration
        self._declare(decl)
        payload, info = encode(self._known, decl, msg)
        out, rejected = self.deliver(payload, msg, info["kind"])
        info = dict(info)
        info["rejected"] = rejected
        return out, info

    def totals(self):
        t = collections.Counter()
        for _, k, n, p in self._frames:
            t[k] += n
            t["prefix"] += p
        t = dict(t)
        t["all"] = sum(n + p for _, _, n, p in self._frames)
        return t
