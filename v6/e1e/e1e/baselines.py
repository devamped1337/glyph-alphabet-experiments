"""Byte-audit baselines (BYTE_AUDIT_PLAN_DRAFT.md sections 4, 6, 7, 8 and Amendment A1).

Requires zstandard==0.23.0 (requirements-e1e.txt); imported lazily so the mechanics package stays stdlib-only.
Baselines: 3 = per-message zstd, no dictionary; 4 = per-message zstd with a dictionary trained on dev messages;
4b = per-message zstd with the repository entry bodies as a raw-content dictionary (Amendment A1);
6 = three-way selection between zstd(ref envelope), zstd(raw envelope) and the raw envelope (section 8).
"""
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


def _compact():
    from . import compact
    return compact


def prefix_len(n):
    """Canonical LEB128 length-prefix bytes for a frame of n bytes (section 3.1; at most 5)."""
    return _compact().prefix_len(n)


def zstd_or_raw(msg, codec):
    """Per-message zstd frame vs raw envelope, strictly smaller wins, ties to the raw envelope (section 5.1 rule)."""
    from .codec import raw_wire
    raw, z = raw_wire(msg), codec.compress(msg)
    return (z, "zstd") if len(z) < len(raw) else (raw, "raw")


def oversized_fallback(msg, codec3):
    """Section 5.1: the common fallback for messages > 65,536 B in EVERY arm: smaller of the baseline-3 zstd frame and
    the raw envelope, ties to the raw envelope. The caller charges the canonical length prefix of the result."""
    return zstd_or_raw(msg, codec3)


def select_baseline4(dev_by_conv, participants=2, level=DEFAULT_LEVEL, frame=HEADLINE_FRAME):
    """Plan section 7 selection on dev only. dev_by_conv: [(conv_id, [bytes, ...])]. Eligible only with >= 50 messages
    and >= 8 conversations. Sizes {1024, 2048, 4096, 8192}; 4-fold CV grouped by conversation, fold = first 8 bytes
    big-endian of SHA-256("e1e-fold-1" NUL conv_id) mod 4; score = total per-message zstd frame bytes of the held-out fold
    plus dictionary bytes x (1 + participants); a fold where training raises fails that size. Returns
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
            sc.append(None if cdc is None else sum(len(cdc.compress(m)) for m in te)
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
    """Repository artifact distribution (arms 4b-delta, 5, 6, 7; section 2): the maintainer uploads every artifact once
    (the initial full snapshot, each delta, and a joiner's full snapshot once per distinct joined version other than
    the initial one); every participant downloads each artifact once (initial full sync, each delta); each joiner
    downloads the full snapshot of the version current when it joins. chain: records with 'full' and 'delta' bytes.
    joiner_versions: published indexes (1-based) at which joiners join, one entry per joiner."""
    if not chain:
        return {"upload": 0, "download": 0, "total": 0, "initial": 0, "per_update_download": 0, "per_join": 0,
                "artifacts": 0}
    arts = [len(chain[0]["full"])] + [len(r["delta"]) for r in chain[1:]]
    upload = sum(arts)
    download = sum(arts) * participants
    jv = [v for v in joiner_versions if v >= 1]  # a joiner before the first publication fetches nothing
    for v in sorted(set(jv)):
        if v != 1:
            upload += len(chain[v - 1]["full"])
    download += sum(len(chain[v - 1]["full"]) for v in jv)
    return {"upload": upload, "download": download, "total": upload + download, "artifacts": len(arts),
            "initial": arts[0] * (1 + participants),
            "per_update_download": (sum(arts[1:]) * participants / (len(arts) - 1)) if len(arts) > 1 else 0,
            "per_join": (sum(len(chain[v - 1]["full"]) for v in jv) / len(jv)) if jv else 0}


def dict_rebuild_sync(chain, participants, joiner_versions=()):
    """Arm 4b under A1: every published version's full raw-content dictionary is uploaded once and downloaded by every
    participant (initial and each new version, a full rebuild, never a delta); each joiner downloads its version's."""
    sizes = [len(repo_dict_bytes(r["state"])) for r in chain]
    return sync_cost(sizes, participants, [(v - 1, 1) for v in joiner_versions if v >= 1]) if sizes else \
        {"upload": 0, "download": 0, "total": 0, "storage_per_participant": 0}


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
        self.covered = self.refs = self.ref_bytes = 0
        self.nonzero_cov_msgs = 0

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

    def add_oversized(self, payload_len, input_len):
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
            "messages_with_refs": self.nonzero_cov_msgs,
            "oversized": {"count": self.over_n, "input_bytes": self.over_input,
                          "fallback_bytes": self.over_bytes, "fallback_prefix_bytes": self.over_prefix},
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
            assert codec3.decompress(data) == msg if kind == "zstd" else True
            for a in arms:
                tallies[a].add_oversized(len(data), n)
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
                data, kind = zstd_or_raw(msg, cdc)
                if kind == "zstd":
                    assert cdc.decompress(data) == msg  # offline byte-exact oracle
                mb = t.add_first(len(data), kind, n)
                if a in ("4b", "4b-delta") and idx:
                    st = chain[idx - 1]["state"]
                    d = {"version": idx, "digest": st.digest}
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
                    if info["kind"] == "compact" and info["refs"]:
                        t.nonzero_cov_msgs += 1
                    t.covered += info["covered_bytes"]
                    t.refs += info["refs"]
                    t.ref_bytes += info["ref_bytes"]
                elif a == "5" and info["kind"] == "ref":
                    t.covered += n
                    t.refs += 1
                    t.nonzero_cov_msgs += 1
            t.per_msg.append((mb, ctrl, n))
    return {a: tallies[a].finish() for a in arms}


def scenario_totals(message_results, chain, participants, joiner_versions, b4_codec=None):
    """Add sync/control accounting (sections 2, 6) to replay_arms results for one participants/joiners setting.
    Message bytes and sync bytes stay separate lines; total = messages + prefixes + declarations/rejects/retransmits
    + sync (+ the oversized fallback frames and their prefixes in 'all_message_total')."""
    d4 = static_dict_sync(b4_codec.dict_bytes, participants, len(joiner_versions)) if b4_codec is not None and b4_codec.dict_bytes else \
        {"upload": 0, "download": 0, "total": 0}
    art = repo_artifact_sync(chain, participants, joiner_versions)
    b4b = dict_rebuild_sync(chain, participants, joiner_versions)
    sync = {"1": {"upload": 0, "download": 0, "total": 0}, "3": {"upload": 0, "download": 0, "total": 0},
            "4": d4, "4b": b4b, "4b-delta": art, "5": art, "7": art,
            "6": {"upload": art["upload"] + d4["upload"], "download": art["download"] + d4["download"],
                  "total": art["total"] + d4["total"]}}
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
    return out


def joiner_indexes(M):
    """One joiner at each of the first three quartiles of the replay: message indexes floor(M*q/4), q = 1, 2, 3."""
    return [(M * q) // 4 for q in (1, 2, 3)]
