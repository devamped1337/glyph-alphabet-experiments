"""Repository state, full/delta artifacts and transactional operations (SPEC sections 3, 7)."""
import copy
import types

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
        if type(version) is not int or not 0 <= version <= 2**31:
            raise E1EError("E_SCHEMA", "RepoState version must be an int in 0..2^31")
        entries = dict(entries or {})
        for k, e in entries.items():
            validate_entry(e)
            if k != e["id"]:
                raise E1EError("E_SCHEMA", "entries must be keyed by their id")
        seen = dict(seen or {})
        for key, d in seen.items():
            if (not isinstance(key, tuple) or len(key) != 2 or not isinstance(key[0], str)
                    or type(key[1]) is not int or not isinstance(d, str)):
                raise E1EError("E_SCHEMA", "seen must map (str id, int v) -> str digest")
        set_ = object.__setattr__
        set_(self, "_version", version)
        set_(self, "_e", copy.deepcopy(dict(entries or {})))  # private; never shared with callers
        set_(self, "_seen", dict(seen or {}))
        for e in self._e.values():
            self._seen.setdefault((e["id"], e["v"]), e["digest"])
        set_(self, "_digest", state_digest(version, self._e))

    def __setattr__(self, name, value):
        raise AttributeError("RepoState is immutable")

    def __delattr__(self, name):
        raise AttributeError("RepoState is immutable")

    @property
    def version(self):
        return self._version

    @property
    def digest(self):
        return self._digest

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
        if state is not None and not isinstance(state, RepoState):
            raise E1EError("E_SCHEMA", "holder state must be a RepoState")
        self._state = state or RepoState()

    @property
    def state(self):
        """Read-only: state changes only through validated load_full/apply_delta/publish."""
        return self._state

    def load_full(self, data):
        new = load_full(data, self.state)
        self._state = new
        return new

    def apply_delta(self, data):
        new = apply_delta(self.state, data)
        self._state = new
        return new


class Publisher(Holder):
    """Maintainer: publishes deltas and keeps every snapshot it produced, keyed by digest."""

    def __init__(self):
        super().__init__()
        self._history = {self.state.digest: self.state}

    @property
    def history(self):
        """Read-only view of digest -> immutable RepoState."""
        return types.MappingProxyType(self._history)

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
        self._state = new
        self._history[new.digest] = new
        return delta, new.full_bytes()


class Receiver(Holder):
    def declare(self):
        """Snapshot declaration a receiver sends so senders never assume its state."""
        return {"version": self.state.version, "digest": self.state.digest}
