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

    def __init__(self, level=DEFAULT_LEVEL, dict_data=None, dict_type="raw", frame=HEADLINE_FRAME):
        z = _zstd()
        self.level, self.frame = level, dict(frame)
        self.dict_bytes = bytes(dict_data) if dict_data else b""
        if self.dict_bytes:
            dt = z.DICT_TYPE_RAWCONTENT if dict_type == "raw" else z.DICT_TYPE_AUTO
            self._dict = z.ZstdCompressionDict(self.dict_bytes, dict_type=dt)
        else:
            self._dict = None

    def compress(self, data):
        z = _zstd()
        kw = dict(self.frame)
        if self._dict is not None:
            kw["dict_data"] = self._dict
        return z.ZstdCompressor(level=self.level, **kw).compress(data)  # fresh context per message

    def decompress(self, frame, max_output=1 << 20):
        z = _zstd()
        d = z.ZstdDecompressor(dict_data=self._dict) if self._dict is not None else z.ZstdDecompressor()
        try:
            out = d.decompressobj().decompress(frame)  # content size not in frame: use streaming API
        except z.ZstdError as e:
            raise E1EError("E_ZSTD", str(e))
        if len(out) > max_output:
            raise E1EError("E_TOO_LARGE", "decompressed output too large")
        return out


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
