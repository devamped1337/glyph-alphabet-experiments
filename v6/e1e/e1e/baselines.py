"""Byte-audit baselines (BYTE_AUDIT_PLAN_DRAFT.md sections 4, 6, 7, 8 and Amendment A1).

Requires zstandard==0.23.0 (requirements-e1e.txt); imported lazily so the mechanics package stays stdlib-only.
Baselines: 3 = per-message zstd, no dictionary; 4 = per-message zstd with a dictionary trained on dev messages;
4b = per-message zstd with the repository entry bodies as a raw-content dictionary (Amendment A1);
6 = three-way selection between zstd(ref envelope), zstd(raw envelope) and the raw envelope (section 8).
"""
import collections
from .canon import E1EError

ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"
DEFAULT_LEVEL = 19
HEADLINE_FRAME = {"write_content_size": False, "write_checksum": False, "write_dict_id": False}
INTEGRITY_FRAME = {"write_content_size": False, "write_checksum": True, "write_dict_id": True}
DICT_SEPARATOR = b"\n"


def _zstd():
    import zstandard
    return zstandard


def zstd_versions():
    z = _zstd()
    return {"zstandard": z.__version__, "libzstd": ".".join(map(str, z.ZSTD_VERSION))}


def repo_dict_bytes(state):
    """Amendment A1: entry bodies (UTF-8) of the snapshot, sorted by id, joined by LF; b'' if empty."""
    ents = state.entries
    return DICT_SEPARATOR.join(ents[k]["body"].encode("utf-8") for k in sorted(ents))


class ZstdCodec:
    """Per-message zstd. dict_data: None (baseline 3), trained ZstdCompressionDict bytes (baseline 4,
    dict_type='auto'), or raw-content bytes (baseline 4b, dict_type='raw'). Empty raw content -> no dictionary."""

    def __init__(self, level=DEFAULT_LEVEL, dict_data=None, dict_type="raw", frame=HEADLINE_FRAME, precompute=False):
        z = _zstd()
        self.level, self.frame = level, dict(frame)
        self.dict_bytes = bytes(dict_data) if dict_data else b""
        if self.dict_bytes:
            dt = z.DICT_TYPE_RAWCONTENT if dict_type == "raw" else z.DICT_TYPE_AUTO
            self._dict = z.ZstdCompressionDict(self.dict_bytes, dict_type=dt)
            if precompute:
                self._dict.precompute_compress(level=level)  # same bytes out, dictionary digested once
        else:
            self._dict = None

    def compress(self, data):
        z = _zstd()
        kw = dict(self.frame)
        if self._dict is not None:
            kw["dict_data"] = self._dict
        return z.ZstdCompressor(level=self.level, **kw).compress(data)  # fresh context per message

    def decompress(self, frame, max_output=1 << 20, chunk=256):
        """Exactly one complete frame: end of frame reached (checksum verified when the frame carries one),
        no trailing bytes, output bounded during decoding (input fed in small chunks, so at most
        max_output + one zstd block is ever buffered). Anything else raises E1EError."""
        z = _zstd()
        d = z.ZstdDecompressor(dict_data=self._dict) if self._dict is not None else z.ZstdDecompressor()
        obj, out, n, fed = d.decompressobj(), [], 0, 0
        try:
            while fed < len(frame) and not obj.eof:  # stop at end of frame; rest is trailing data
                part = obj.decompress(frame[fed:fed + chunk])
                fed += chunk
                n += len(part)
                if n > max_output:
                    raise E1EError("E_TOO_LARGE", "decompressed output too large")
                out.append(part)
        except z.ZstdError as e:
            raise E1EError("E_ZSTD", str(e))
        if not obj.eof:
            raise E1EError("E_ZSTD", "incomplete zstd frame")
        if obj.unused_data or fed < len(frame):
            raise E1EError("E_ZSTD", "trailing bytes after zstd frame")
        return b"".join(out)


def baseline3(level=DEFAULT_LEVEL, frame=HEADLINE_FRAME):
    return ZstdCodec(level, None, frame=frame)


def baseline4(dev_messages, size, level=DEFAULT_LEVEL, frame=HEADLINE_FRAME):
    """Trained dictionary (section 7). Returns None when training raises ('not trainable')."""
    z = _zstd()
    try:
        d = z.train_dictionary(size, list(dev_messages))
    except z.ZstdError:
        return None
    return ZstdCodec(level, d.as_bytes(), dict_type="auto", frame=frame)


def baseline4b(state, level=DEFAULT_LEVEL, frame=HEADLINE_FRAME):
    """Amendment A1: same level/frame as baseline 4, dictionary = repo_dict_bytes(state) (raw content)."""
    return ZstdCodec(level, repo_dict_bytes(state), dict_type="raw", frame=frame)


def sync_cost(dict_sizes, participants, joiners=()):
    """Section 6 charging for a dictionary that is rebuilt per version (no delta form; Amendment A1).
    dict_sizes: [bytes of version 1, version 2, ...] in publication order; participants: count holding the
    dictionary when each version is published (int, or a list per version); joiners: [(version_index, n)] joiners
    who fetch that version's full dictionary. Returns upload/download/storage totals."""
    sizes = list(dict_sizes)
    per = participants if isinstance(participants, (list, tuple)) else [participants] * len(sizes)
    if len(per) != len(sizes):
        raise ValueError("participants per version must match dict_sizes")
    upload = sum(s for s in sizes if s)
    download = sum(s * n for s, n in zip(sizes, per))
    download += sum(sizes[i] * n for i, n in joiners)
    return {"upload": upload, "download": download, "total": upload + download,
            "storage_per_participant": sizes[-1] if sizes else 0}


def select_b6(ref_wire, raw_env, codec):
    """Section 8 baseline 6: candidates (i) zstd(ref), (ii) zstd(raw envelope), (iii) raw envelope.
    Smallest wins; ties prefer (iii), then (ii), then (i). ref_wire None -> only (ii) and (iii)."""
    cands = [(len(raw_env), 0, "raw", raw_env)]
    zr = codec.compress(raw_env)
    cands.append((len(zr), 1, "zstd_raw", zr))
    if ref_wire is not None:
        zf = codec.compress(ref_wire)
        cands.append((len(zf), 2, "zstd_ref", zf))
    n, _, label, data = min(cands)
    return data, label


def unwrap(data, codec):
    """Receiver side of section 8 framing: zstd magic -> decompress, '{' -> envelope as is."""
    if data[:4] == ZSTD_MAGIC:
        if codec is None:
            raise E1EError("E_SCHEMA", "zstd frame without a codec")
        return codec.decompress(data)
    if data[:1] == b"{":
        return data
    raise E1EError("E_SCHEMA", "unknown frame start")


# ======================================================================================================
# E1f additions (E1F_PROPOSAL_DRAFT.md sections 2, 3.1, 5.1, 6): framing prefix lines, oversized fallback,
# arm 4b-delta, arm 7 accounting, and the lifecycle scenario runner. Nothing above this line changed.
# ======================================================================================================
ARMS = ("1", "3", "4", "4b", "4b-delta", "5", "6", "7")
PRIMARY_SCENARIO = {"V": 5, "participants": 2, "joiners": 0}
SCENARIO_GRID = [{"V": V, "participants": p, "joiners": j} for V in (1, 5, 20) for p in (2, 10) for j in (0, 3)]
FOLD_SEED = "e1e-fold-1"
EMPTY_DIGEST = None  # set lazily to the digest of the empty (version 0) repository


def _compact():
    from . import compact
    return compact


def prefix_len(n):
    """Canonical LEB128 length-prefix bytes for a frame of n bytes (section 3.1; at most 5)."""
    return _compact().prefix_len(n)


def zstd_or_raw(msg, codec):
    """Section 5.1 selection rule ONLY (the oversized-message fallback): the smaller of the zstd frame and the raw
    envelope, ties to the raw envelope. Named baselines 3/4/4b/4b-delta do NOT use this: they send their zstd frame
    (their native rule) for every eligible message (amendment A1, section 5.1)."""
    from .codec import raw_wire
    raw, z = raw_wire(msg), codec.compress(msg)
    return (z, "zstd") if len(z) < len(raw) else (raw, "raw")


def oversized_fallback(msg, codec3):
    """Section 5.1: the common fallback for messages > 65,536 B in EVERY arm: smaller of the baseline-3 zstd frame and the
    raw envelope, ties to the raw envelope. The caller charges the canonical length prefix of the result and must call
    verify_oversized."""
    return zstd_or_raw(msg, codec3)


def verify_oversized(data, kind, msg, codec3):
    """Byte-exact check of an oversized fallback frame against the original message (amendment A1). zstd: exactly one
    complete frame whose decompressed output is bounded by the ORIGINAL message length (no fixed ceiling) and equals the
    message. raw: the envelope must be the canonical E1E-MSG/1 raw encoding (parsed with the limit set to its own length,
    since the E1E-MSG/1 decoder's wire/size limits do not apply to this fallback) and decode to the message. Raises
    E1EError on any mismatch; returns True otherwise."""
    import base64
    from .canon import E1EError, parse_canonical
    from .codec import MSG_FORMAT
    if kind == "zstd":
        out = codec3.decompress(data, max_output=len(msg))
        if out != msg:
            raise E1EError("E_SCHEMA", "oversized zstd fallback does not reproduce the message")
        return True
    obj = parse_canonical(data, len(data))
    if not isinstance(obj, dict) or obj.get("format") != MSG_FORMAT or obj.get("type") != "raw":
        raise E1EError("E_SCHEMA", "oversized raw fallback is not a raw envelope")
    if set(obj) == {"format", "type", "text"} and isinstance(obj["text"], str):
        out = obj["text"].encode("utf-8")
    elif set(obj) == {"format", "type", "b64"} and isinstance(obj["b64"], str):
        out = base64.b64decode(obj["b64"], validate=True)
    else:
        raise E1EError("E_SCHEMA", "bad raw envelope")
    if out != msg or raw_wire_of(msg) != bytes(data):
        raise E1EError("E_SCHEMA", "oversized raw fallback does not reproduce the message")
    return True


def raw_wire_of(msg):
    from .codec import raw_wire
    return raw_wire(msg)


def select_baseline4(dev_by_conv, participants=2, level=DEFAULT_LEVEL, frame=HEADLINE_FRAME):
    """Plan section 7 selection on dev only. dev_by_conv: [(conv_id, [bytes, ...])]. Eligible only with >= 50 messages
    and >= 8 conversations. Sizes {1024, 2048, 4096, 8192}; 4-fold CV grouped by conversation, fold = first 8 bytes
    big-endian of SHA-256("e1e-fold-1" NUL conv_id) mod 4; score = total per-message zstd frame bytes of the held-out fold INCLUDING each
    frame's canonical length prefix (amendment A1), plus dictionary bytes x (1 + participants); a fold where training raises fails that size. Returns
    (codec or None, report dict). 'not trainable' -> codec None."""
    import hashlib
    msgs = [(c, m) for c, ms in dev_by_conv for m in ms]
    rep = {"eligible": len(msgs) >= 50 and len(dev_by_conv) >= 8, "sizes": {}, "chosen": None}
    if not rep["eligible"]:
        rep["status"] = "not trainable (insufficient dev corpus)"
        return None, rep
    fold = {c: int.from_bytes(hashlib.sha256((FOLD_SEED + "\x00" + c).encode()).digest()[:8], "big") % 4
            for c, _ in dev_by_conv}
    for size in (1024, 2048, 4096, 8192):
        sc = []
        for f in range(4):
            tr = [m for c, m in msgs if fold[c] != f]
            te = [m for c, m in msgs if fold[c] == f]
            cdc = baseline4(tr, size, level, frame)
            sc.append(None if cdc is None else sum(len(f) + prefix_len(len(f)) for f in (cdc.compress(m) for m in te))
                      + len(cdc.dict_bytes) * (1 + participants))
        rep["sizes"][size] = {"fold_scores": sc, "eligible": None not in sc,
                              "mean": (sum(sc) / 4 if None not in sc else None)}
    elig = [s for s in rep["sizes"] if rep["sizes"][s]["eligible"]]
    if not elig:
        rep["status"] = "not trainable (no size trains in all folds)"
        return None, rep
    chosen = min(elig, key=lambda s: (rep["sizes"][s]["mean"], s))
    final = baseline4([m for _, m in msgs], chosen, level, frame)
    rep["chosen"] = chosen
    rep["status"] = "trained" if final is not None else "not trainable (final training raised)"
    return final, rep


def repo_artifact_sync(chain, participants, joiner_versions=()):
    """Repository artifact distribution (arms 4b-delta, 5, 6, 7; section 2; amendment A1 joiner lifecycle): the maintainer
    uploads every artifact once (the initial full snapshot, each delta, and a joiner's full snapshot once per distinct
    joined version other than the initial one); every participant downloads each artifact once (initial full sync, each
    delta). A joiner is a participant from its join onward: it downloads the full snapshot of the version current when it
    joins (a joiner before the first publication, version 0, downloads the initial full snapshot) AND every later
    publication's delta, in the same lifecycle. chain: records with 'full' and 'delta' bytes. joiner_versions: published
    indexes (0 = before the first publication, else 1-based) at which joiners join, one entry per joiner."""
    if not chain:
        return {"upload": 0, "download": 0, "total": 0, "initial": 0, "per_update_download": 0, "per_join": 0,
                "artifacts": 0, "joiner_join_download": 0, "joiner_update_download": 0}
    arts = [len(chain[0]["full"])] + [len(r["delta"]) for r in chain[1:]]
    upload = sum(arts)
    download = sum(arts) * participants
    jv = [max(v, 1) for v in joiner_versions]
    for v in sorted(set(jv)):
        if v != 1:
            upload += len(chain[v - 1]["full"])
    join_dl = sum(len(chain[v - 1]["full"]) for v in jv)
    later_dl = sum(sum(arts[v:]) for v in jv)  # deltas of every publication after the joined version
    download += join_dl + later_dl
    return {"upload": upload, "download": download, "total": upload + download, "artifacts": len(arts),
            "initial": arts[0] * (1 + participants),
            "per_update_download": (sum(arts[1:]) * participants / (len(arts) - 1)) if len(arts) > 1 else 0,
            "per_join": (join_dl / len(jv)) if jv else 0,
            "joiner_join_download": join_dl, "joiner_update_download": later_dl}


def dict_rebuild_sync(chain, participants, joiner_versions=()):
    """Arm 4b under A1: every published version's full raw-content dictionary is uploaded once and downloaded by every
    participant (initial and each new version, a full rebuild, never a delta). A joiner downloads the dictionary of the
    version current when it joins (version 0: the first) and EVERY later published version's dictionary (lifecycle)."""
    sizes = [len(repo_dict_bytes(r["state"])) for r in chain]
    if not sizes:
        return {"upload": 0, "download": 0, "total": 0, "storage_per_participant": 0, "joiner_join_download": 0,
                "joiner_update_download": 0}
    out = sync_cost(sizes, participants)
    jv = [max(v, 1) for v in joiner_versions]
    join_dl = sum(sizes[v - 1] for v in jv)
    later_dl = sum(sum(sizes[v:]) for v in jv)
    out["download"] += join_dl + later_dl
    out["total"] = out["upload"] + out["download"]
    out["joiner_join_download"], out["joiner_update_download"] = join_dl, later_dl
    return out


def static_dict_sync(dict_bytes, participants, joiners=0):
    """Baseline 4's trained dictionary: uploaded once, downloaded by every participant and every joiner (section 6)."""
    n = len(dict_bytes)
    return {"upload": n, "download": n * (participants + joiners), "total": n * (1 + participants + joiners)}


class _Tally:
    """Per-arm byte accounting: message bytes (first-send frames), control bytes (declare, reject, retransmission) and
    the canonical length prefixes of each, kept as separate lines. Eligible (<= 65,536 B) and oversized are separate."""

    def __init__(self):
        self.n = self.input_bytes = 0
        self.msg = self.msg_prefix = self.ctrl = self.ctrl_prefix = 0
        self.declare = self.reject = self.retransmit = 0
        self.kinds = {}
        self.per_msg = []  # (message-frame bytes incl. prefix, control bytes incl. prefix, input bytes)
        self.rejected = 0
        self.over_n = self.over_input = self.over_bytes = self.over_prefix = 0
        self.over_kinds, self.over_verified = {}, 0
        self.enc = collections.Counter()
        self.enc_reasons = collections.Counter()
        self.enc_verify_errors = collections.Counter()
        self.covered = self.refs = self.ref_bytes = 0
        self.nonzero_cov_msgs = 0
        self.lit_segments = 0

    def add_first(self, payload_len, kind, input_len):
        self.n += 1
        self.input_bytes += input_len
        self.msg += payload_len
        p = prefix_len(payload_len)
        self.msg_prefix += p
        self.kinds[kind] = self.kinds.get(kind, 0) + 1
        return payload_len + p

    def add_ctrl(self, kind, payload_len):
        p = prefix_len(payload_len)
        self.ctrl += payload_len
        self.ctrl_prefix += p
        if kind == "declare":
            self.declare += payload_len + p
        elif kind == "reject":
            self.reject += payload_len + p
        else:
            self.retransmit += payload_len + p
        return payload_len + p

    def add_encoder_stats(self, info):
        """Arm 7 encoder statistics per eligible message (amendment A1): reasons, cap hits, verification failures."""
        e = self.enc
        e["messages"] += 1
        self.enc_reasons[info.get("reason")] += 1
        if "verify_error" in info:
            self.enc_verify_errors[info["verify_error"]] += 1
        if "candidates" in info:  # the encoder reached candidate generation
            e["enumerated_messages"] += 1
            e["candidates"] += info["candidates"]
            e["cap_hit_messages"] += bool(info["cap_hit"])
            e["entries_pending"] += info["entries_pending"]
            e["template_evaluations"] += info["template_evaluations"]
            e["eval_cap_hit_messages"] += bool(info["eval_cap_hit"])
            e["matcher_calls"] += info["matcher_calls"]
            e["matcher_span_chars"] += info["matcher_span_chars"]
            e["match_cap_hit_messages"] += bool(info["match_cap_hit"])
        e["verified_ok"] += info.get("reason") in ("compact", "compact_not_smaller")
        e["verify_failed"] += info.get("reason") == "verify_failed"
        e["receiver_rejects_after_send"] += bool(info.get("rejected"))
        e["raw_fallback_sends"] += info.get("kind") == "raw"

    def add_oversized(self, payload_len, input_len, kind=None, verified=False):
        self.over_kinds[kind] = self.over_kinds.get(kind, 0) + 1
        self.over_verified += bool(verified)
        self.over_n += 1
        self.over_input += input_len
        self.over_bytes += payload_len
        self.over_prefix += prefix_len(payload_len)

    def finish(self):
        msg_total = self.msg + self.msg_prefix
        ctrl_total = self.ctrl + self.ctrl_prefix
        per_msg_ratio = [(a / i) for a, _, i in self.per_msg if i]
        return {
            "eligible_messages": self.n, "input_bytes": self.input_bytes,
            "message_bytes": self.msg, "message_prefix_bytes": self.msg_prefix,
            "control_bytes": self.ctrl, "control_prefix_bytes": self.ctrl_prefix,
            "declare_bytes_incl_prefix": self.declare, "reject_bytes_incl_prefix": self.reject,
            "retransmit_bytes_incl_prefix": self.retransmit,
            "message_plus_control_total": msg_total + ctrl_total,
            "kinds": dict(self.kinds), "rejected": self.rejected,
            "byte_weighted_message_ratio": (msg_total / self.input_bytes) if self.input_bytes else None,
            "mean_per_message_ratio": (sum(per_msg_ratio) / len(per_msg_ratio)) if per_msg_ratio else None,
            "mean_message_frame_bytes": (msg_total / self.n) if self.n else None,
            "covered_bytes": self.covered, "refs": self.refs, "ref_bytes": self.ref_bytes,
            "messages_with_refs": self.nonzero_cov_msgs, "lit_segments": self.lit_segments,
            "oversized": {"count": self.over_n, "input_bytes": self.over_input,
                          "fallback_bytes": self.over_bytes, "fallback_prefix_bytes": self.over_prefix,
                          "kinds": dict(self.over_kinds), "verified_byte_exact": self.over_verified},
            **({"encoder": {**dict(self.enc), "reasons": {str(k): v for k, v in self.enc_reasons.items()},
                            "verify_errors": dict(self.enc_verify_errors)}} if self.enc else {}),
        }


def replay_arms(replay, chain, version_index, arms=ARMS, level=DEFAULT_LEVEL, b4_codec=None):
    """Replay `replay` (list of dicts: conv_id, sender, receiver, msg bytes) through the arms, byte-exact oracle on every
    message. chain: published snapshots (see curation.build_repository_chain). version_index(r) -> published index
    (1-based; 0 = empty repository) for the message with rank r. b4_codec: the baseline-4 codec (None = not trainable).
    Returns {arm: finished tally}; message-level only (sync is added by scenario_totals). A link is
    (conv_id, sender, receiver); a declaration is charged when the declaration used on a link changes (first use incl.).
    Repo arms: declarations are charged for 4b, 4b-delta, 5, 6, 7; not for 1, 3, 4."""
    from .canon import E1EError
    from .codec import Link, raw_wire, declare_wire
    from .compact import CompactLink, CompactReceiver
    from .repo import Receiver
    from .repo import RepoState
    global EMPTY_DIGEST
    EMPTY_DIGEST = RepoState().digest
    C = _compact()
    tallies = {a: _Tally() for a in arms}
    codec3 = baseline3(level)
    zc = {}  # published index -> codec 4b

    def codec_4b(i):
        if i not in zc:
            zc[i] = ZstdCodec(level, repo_dict_bytes(chain[i - 1]["state"]) if i else b"", dict_type="raw",
                              precompute=True)
        return zc[i]

    known = {r["state"].digest: r["state"] for r in chain}
    rx5, rx6, rx7 = Receiver(), Receiver(), CompactReceiver()
    applied = {"5": 0, "6": 0, "7": 0}
    links = {a: {} for a in ("5", "6", "7")}
    decl4 = {a: {} for a in ("4b", "4b-delta")}
    rxs = {"5": rx5, "6": rx6, "7": rx7}

    def advance(arm, idx):
        rx = rxs[arm]
        while applied[arm] < idx:
            i = applied[arm] + 1
            if i == 1:
                rx.load_full(chain[0]["full"])
            else:
                rx.apply_delta(chain[i - 1]["delta"])
            applied[arm] = i

    for r, item in enumerate(replay):
        msg, key = item["msg"], (item["conv_id"], item.get("sender"), item.get("receiver"))
        idx = version_index(r)
        n = len(msg)
        if n > C.MAX_MESSAGE_BYTES:  # section 5.1: one common fallback in every arm
            data, kind = oversized_fallback(msg, codec3)
            ok = verify_oversized(data, kind, msg, codec3)  # byte-exact, bounded by the original length
            for a in arms:
                tallies[a].add_oversized(len(data), n, kind, ok)
            continue
        raw = raw_wire(msg)
        zr = None
        for a in arms:
            t = tallies[a]
            ctrl = 0
            if a == "1":
                mb = t.add_first(len(raw), "raw", n)
            elif a in ("3", "4", "4b", "4b-delta"):
                if a == "3":
                    cdc = codec3
                elif a == "4":
                    cdc = b4_codec or codec3  # not trainable: baseline 3 is the strongest zstd baseline
                else:
                    cdc = codec_4b(idx)
                data, kind = cdc.compress(msg), "zstd"  # the named baseline's native rule: the zstd frame, always
                assert cdc.decompress(data) == msg  # offline byte-exact oracle
                mb = t.add_first(len(data), kind, n)
                if a in ("4b", "4b-delta"):  # same declaration rule as arms 5/6/7, the empty repository (v0) included
                    d = {"version": idx, "digest": chain[idx - 1]["state"].digest if idx else EMPTY_DIGEST}
                    if decl4[a].get(key) != d:
                        decl4[a][key] = d
                        ctrl += t.add_ctrl("declare", len(declare_wire(d)))
            else:
                advance(a, idx)
                rx = rxs[a]
                lk = links[a].get(key)
                if lk is None:
                    if a == "5":
                        lk = Link(known, rx, require_smaller=True)
                    elif a == "6":
                        lk = Link(known, rx, require_smaller=True, codec=b4_codec or codec3)
                    else:
                        lk = CompactLink(known, rx)
                    links[a][key] = lk
                before = len(lk.frames)
                out, info = lk.transmit(msg)
                assert out == msg
                new = lk.frames[before:]
                mb = 0
                for fr in new:
                    d_, kind, nbytes = fr[0], fr[1], fr[2]
                    if d_ == "fwd" and kind != "fallback":
                        mb = t.add_first(nbytes, kind, n)
                    else:
                        ctrl += t.add_ctrl(kind, nbytes)
                if info.get("rejected"):
                    t.rejected += 1
                if a == "7":
                    t.add_encoder_stats(info)
                    if info["kind"] == "compact" and info["refs"]:
                        t.nonzero_cov_msgs += 1
                    t.covered += info["covered_bytes"]
                    t.refs += info["refs"]
                    t.ref_bytes += info["ref_bytes"]
                    t.lit_segments += info.get("lit_segments", 0)
                elif a == "5" and info["kind"] == "ref":
                    t.covered += n
                    t.refs += 1
                    t.nonzero_cov_msgs += 1
            t.per_msg.append((mb, ctrl, n))
    return {a: tallies[a].finish() for a in arms}


BREAK_EVEN_PAIRS = tuple(("7", y) for y in ("3", "4", "4b", "4b-delta", "5", "6"))


def _sync_by_arm(chain, participants, joiner_versions, b4_codec):
    d4 = static_dict_sync(b4_codec.dict_bytes, participants, len(joiner_versions)) if b4_codec is not None and b4_codec.dict_bytes else \
        {"upload": 0, "download": 0, "total": 0}
    art = repo_artifact_sync(chain, participants, joiner_versions)
    b4b = dict_rebuild_sync(chain, participants, joiner_versions)
    zero = {"upload": 0, "download": 0, "total": 0}
    return {"1": zero, "3": zero, "4": d4, "4b": b4b, "4b-delta": art, "5": art, "7": art,
            "6": {"upload": art["upload"] + d4["upload"], "download": art["download"] + d4["download"],
                  "total": art["total"] + d4["total"]}}


def break_even(message_results, chain, participants, joiner_versions, b4_codec=None, pairs=BREAK_EVEN_PAIRS):
    """Amendment A1 (section 6, break-even). For X vs Y (X = arm 7), on the OBSERVED message bytes: sync_total(arm) =
    initial + U*per_update + J*per_join, where initial = sync with no updates observed beyond version 1 and no joiners (the
    first artifact uploaded once and downloaded by every participant), per_update = (sync(no joiners) - initial)/U over the
    U = P-1 observed publications after the first, per_join = (sync(with joiners) - sync(no joiners))/J. X's advantage over Y
    at u updates and j joins is  A(u, j) = (msgY - msgX) + (initial_Y - initial_X) - u*(pu_X - pu_Y) - j*(pj_X - pj_Y),
    (msg = message + control bytes of the eligible messages, positive A = X smaller). Break-even counts are where A = 0
    solved separately for u (j at its observed J) and for j (u at its observed U); a count is reported only when it is
    defined, positive and finite; otherwise an explicit status string is given ('undefined: ...', 'X ahead at every
    count', 'X behind at every count'). Everything is computed from emitted numbers (ingredients included)."""
    J, U = len(joiner_versions), max(len(chain) - 1, 0)
    s0 = _sync_by_arm(chain, participants, [], b4_codec)
    s1 = _sync_by_arm(chain, participants, joiner_versions, b4_codec)
    first = len(chain[0]["full"]) * (1 + participants) if chain else 0
    d4 = static_dict_sync(b4_codec.dict_bytes, participants, 0)["total"] if b4_codec is not None and b4_codec.dict_bytes else 0
    sizes = [len(repo_dict_bytes(r["state"])) for r in chain]
    initial = {"1": 0, "3": 0, "4": d4, "4b": (sizes[0] * (1 + participants) if sizes else 0), "4b-delta": first, "5": first,
               "6": first + d4, "7": first}
    ing = {}
    for a in message_results:
        pu = (s0[a]["total"] - initial[a]) / U if U else None
        pj = (s1[a]["total"] - s0[a]["total"]) / J if J else None
        ing[a] = {"initial_sync": initial[a], "per_update_sync": pu, "per_join_sync": pj,
                  "message_plus_control": message_results[a]["message_plus_control_total"], "sync_total": s1[a]["total"]}

    def solve(adv0, step, what, count_observed):
        if step is None:
            return f"undefined: no {what} observed"
        if step == 0:
            return "undefined: identical per-" + what + " cost (X ahead at every count)" if adv0 > 0 else \
                   ("undefined: identical per-" + what + " cost (X behind at every count)" if adv0 < 0 else "undefined: identical per-" + what + " cost (tie at every count)")
        if step < 0:
            return "X ahead at every count" if adv0 > 0 else f"{what} count where X catches up: {adv0 / -step:.3f}"
        if adv0 <= 0:
            return "X behind at every count"
        return adv0 / step

    out = {}
    for x, y in pairs:
        if x not in message_results or y not in message_results:
            continue
        ix, iy = ing[x], ing[y]
        base = (iy["message_plus_control"] - ix["message_plus_control"]) + (iy["initial_sync"] - ix["initial_sync"])
        pu_x, pu_y, pj_x, pj_y = ix["per_update_sync"], iy["per_update_sync"], ix["per_join_sync"], iy["per_join_sync"]
        du = None if pu_x is None else pu_x - pu_y
        dj = None if pj_x is None else pj_x - pj_y
        a_obs = base - U * (du or 0) - J * (dj or 0)
        out[f"{x}_vs_{y}"] = {
            "advantage_observed": a_obs,  # equals total_Y - total_X on the observed scenario
            "advantage_at_zero_updates_and_joins": base,
            "break_even_updates": solve(base - J * (dj or 0), du, "update", U),
            "break_even_joins": solve(base - U * (du or 0), dj, "join", J),
            "per_update_delta_X_minus_Y": du, "per_join_delta_X_minus_Y": dj}
    return {"ingredients": ing, "pairs": out, "updates_observed": U, "joins_observed": J}


def scenario_totals(message_results, chain, participants, joiner_versions, b4_codec=None):
    """Add sync/control accounting (sections 2, 6) to replay_arms results for one participants/joiners setting.
    Message bytes and sync bytes stay separate lines; total = messages + prefixes + declarations/rejects/retransmits
    + sync (+ the oversized fallback frames and their prefixes in 'all_message_total'). The result also carries
    '_break_even' (see break_even) and, per arm, the sync ingredients (initial, per_update, per_join)."""
    art = repo_artifact_sync(chain, participants, joiner_versions)
    sync = _sync_by_arm(chain, participants, joiner_versions, b4_codec)
    out = {}
    for a, res in message_results.items():
        r = dict(res)
        r["sync_upload"], r["sync_download"], r["sync_total"] = sync[a]["upload"], sync[a]["download"], sync[a]["total"]
        r["total"] = res["message_plus_control_total"] + sync[a]["total"]  # eligible messages only
        o = res["oversized"]
        r["all_message_total"] = r["total"] + o["fallback_bytes"] + o["fallback_prefix_bytes"]
        r["total_per_eligible_message"] = r["total"] / res["eligible_messages"] if res["eligible_messages"] else None
        r["total_over_input_bytes"] = r["total"] / res["input_bytes"] if res["input_bytes"] else None
        out[a] = r
    out["_break_even"] = break_even(message_results, chain, participants, joiner_versions, b4_codec)
    out["_sync_ingredients"] = {"repo_artifact": {k: art[k] for k in art}}
    return out


def joiner_indexes(M):
    """One joiner at each of the first three quartiles of the replay: message indexes floor(M*q/4), q = 1, 2, 3."""
    return [(M * q) // 4 for q in (1, 2, 3)]
