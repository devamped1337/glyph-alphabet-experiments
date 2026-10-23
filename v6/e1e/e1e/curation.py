"""E1f deterministic curation (E1F_PROPOSAL_DRAFT.md section 4). DEV DATA ONLY, no randomness, no model.

Pipeline: conversation order and dev/held-out split -> version prefixes -> candidates (line blocks by level-wise
repeat mining, pair-wise maximal common substrings by suffix automaton, templates mined from literal line blocks)
-> greedy net-gain selection with fixed provisional ordinal cost 2, per-occurrence matched length, marginal overlap
removal and the section 4 tie rules -> entries -> forward-only five-block tuning over the declared grid.
Where the spec is silent the most literal reading is implemented and recorded in E1F_BUILD_NOTES.md.
"""
import hashlib
import collections
import heapq
import json
import math
import re

from .canon import E1EError, canonical
from .compact import END_TRIES, entry_matcher, template_end, template_starts, MATCH_CALL_CAP, MATCH_WORK_CAP
from .schema import INT_RE, MAX_BODY_CHARS, MAX_PARAMS, PROVS, WORD_RE, make_entry, match_template, parse_template

SEED = "e1e-fold-1"
MAX_MESSAGE_BYTES = 65536
PROVISIONAL_ORDINAL_BYTES = 2
GRID_L = (32, 64, 128, 256)
GRID_K = (2, 3)
GRID_C = (50, 200, 1000)
MAX_TEMPLATE_PARAMS = 4
MIN_L = min(GRID_L)
TOKEN_RE = re.compile(r"[A-Za-z0-9_.-]+")
MAX_ENTRIES = 4096


# ---------------------------------------------------------------- provenance-strict construction
def make_entry_strict(id, v, body, params=None, kind=None, *, prov):
    """Entry construction for E1f: `prov` is keyword-only, has no default and must be one of the SPEC values."""
    if prov is None or prov not in PROVS:
        raise E1EError("E_SCHEMA", f"explicit prov required, one of {PROVS}; got {prov!r}")
    return make_entry(id, v, body, params, kind, prov=prov)


# ---------------------------------------------------------------- order, split, schedule (section 4)
def fold_hash(conv_id):
    return hashlib.sha256((SEED + "\x00" + conv_id).encode("utf-8")).digest()


def order_conversations(messages):
    """messages: dicts with conv_id, seq and optional ts. Returns conv_ids ordered by first-message time (ties by
    SHA-256 of seed+NUL+conv_id). If any message lacks a timestamp none is used (every conversation ties and the
    hash order applies; this is the order for the synthetic and Glyph-own dev corpora, which have no timestamps)."""
    have = all(m.get("ts") is not None for m in messages)
    first = {}
    for m in messages:
        c = m["conv_id"]
        t = m["ts"] if have else 0
        if c not in first or t < first[c]:
            first[c] = t
    return sorted(first, key=lambda c: (first[c], fold_hash(c)))


def split_real(messages):
    """Real corpus split. Returns (dev_conv_ids, heldout_conv_ids), each in section 4 order.
    Timestamps present: the earliest 60% (rounded down) of conversations are dev. Missing: fold = first 8 bytes
    big-endian of the hash mod 5, folds 0-2 dev. (Implemented and unit-tested on made-up data; never run on real data here.)"""
    order = order_conversations(messages)
    have = all(m.get("ts") is not None for m in messages)
    if have:
        n_dev = (len(order) * 6) // 10
        return order[:n_dev], order[n_dev:]
    dev, held = [], []
    for c in order:
        (dev if int.from_bytes(fold_hash(c)[:8], "big") % 5 <= 2 else held).append(c)
    return dev, held


def heldout_order(messages):
    """Replay order of held-out messages: by timestamp, ties by SHA-256 of conv_id + message index (seq)."""
    return sorted(messages, key=lambda m: (m.get("ts") or 0,
                                           hashlib.sha256((m["conv_id"] + str(m["seq"])).encode("utf-8")).digest()))


def prefix_size(j, n, V):
    """Version j (1..V) is built from the first ceil(j*n/V) dev conversations."""
    return -(-j * n // V)


def version_for_rank(r, M, V):
    return 1 + (r * V) // M


def tuning_blocks(n):
    """Five disjoint consecutive blocks of sizes ceil/floor of n/5 (the first n mod 5 blocks get the ceil)."""
    base, extra = divmod(n, 5)
    out, i = [], 0
    for b in range(5):
        sz = base + (1 if b < extra else 0)
        out.append((i, i + sz))
        i += sz
    return out


# ---------------------------------------------------------------- suffix automaton (bytes)
def sam_build(s):
    nxt, link, length = [{}], [-1], [0]
    last = 0
    for c in s:
        cur = len(nxt)
        nxt.append({})
        length.append(length[last] + 1)
        link.append(0)
        p = last
        while p != -1 and c not in nxt[p]:
            nxt[p][c] = cur
            p = link[p]
        if p == -1:
            link[cur] = 0
        else:
            q = nxt[p][c]
            if length[p] + 1 == length[q]:
                link[cur] = q
            else:
                clone = len(nxt)
                nxt.append(dict(nxt[q]))
                length.append(length[p] + 1)
                link.append(link[q])
                while p != -1 and nxt[p].get(c) == q:
                    nxt[p][c] = clone
                    p = link[p]
                link[q] = link[cur] = clone
        last = cur
    return nxt, link, length


def maximal_common(sam, b, min_len):
    """Maximal common substrings of the automaton's string A and b with length >= min_len, as (start_in_b, length).
    Matching statistics: ms[i] is the longest suffix of b[:i+1] that occurs in A; (i, ms[i]) is right-maximal when
    b[i+1] does not extend it. The longest suffix is left-maximal by construction."""
    nxt, link, length = sam
    v = l = 0
    ms = []
    for c in b:
        while v and c not in nxt[v]:
            v = link[v]
            l = length[v]
        d = nxt[v].get(c)
        if d is None:
            v = l = 0
        else:
            v = d
            l += 1
        ms.append(l)
    out, n = [], len(ms)
    for i in range(n):
        if ms[i] >= min_len and (i == n - 1 or ms[i + 1] <= ms[i]):
            out.append((i - ms[i] + 1, ms[i]))
    return out


def trim_utf8(b):
    """Trim a byte string to code-point boundaries (drop leading continuation bytes, an incomplete trailing sequence)."""
    s = 0
    while s < len(b) and b[s] & 0xC0 == 0x80:
        s += 1
    e = len(b)
    k = e
    while k > s and b[k - 1] & 0xC0 == 0x80 and e - k < 3:
        k -= 1
    if k > s:  # b[k-1] is a lead byte (or ASCII)
        lead = b[k - 1]
        need = 1 if lead < 0x80 else 2 if lead >= 0xC0 and lead < 0xE0 else 3 if lead < 0xF0 else 4 if lead < 0xF8 else 1
        if e - (k - 1) < need:
            e = k - 1
    return b[s:e]


# ---------------------------------------------------------------- the dev corpus index (one source)
def _record_size(kind, body, params, prov):
    skel = {"id": "e00000", "v": 1, "kind": kind, "body": "", "params": params, "prov": prov,
            "digest": "sha256:" + "0" * 64}
    return len(canonical(skel)) - 2 + len(json.dumps(body, ensure_ascii=True))


class Miner:
    """Holds the dev corpus of ONE source (prov), caches pair results and occurrence lists across builds.
    convs: list of (conv_id, [message str, ...]) already in section 4 order. Oversized messages (> 65,536 B) are
    excluded from mining, occurrence counting and every denominator, and are counted."""

    def __init__(self, convs, prov, min_len=MIN_L):
        if prov is None or prov not in PROVS:
            raise E1EError("E_SCHEMA", "explicit prov required")
        self.prov = prov
        self.min_len = min_len
        self.conv_ids = [c for c, _ in convs]
        self.msgs, self.msg_conv, self.conv_msg_end = [], [], []
        self.oversized = []  # (conv index, bytes)
        for ci, (_, ms) in enumerate(convs):
            for t in ms:
                b = len(t.encode("utf-8"))
                if b > MAX_MESSAGE_BYTES:
                    self.oversized.append((ci, b))
                    continue
                self.msgs.append(t)
                self.msg_conv.append(ci)
            self.conv_msg_end.append(len(self.msgs))
        self.bmsgs = [t.encode("utf-8") for t in self.msgs]
        used = set("".join(self.msgs)) if self.msgs else set()
        sep = next(chr(c) for c in range(0xE000, 0xF8FF) if chr(c) not in used)
        self.T = sep.join(self.msgs)
        self.starts, p = [], 0
        for t in self.msgs:
            self.starts.append(p)
            p += len(t) + 1
        self._pairs = {}
        self._occ = {}
        self._tocc = {}
        self._W = None
        self.stats = {}

    def cutoff_msgs(self, n_convs):
        return self.conv_msg_end[n_convs - 1] if n_convs > 0 else 0

    # -- pair-wise maximal common substrings (cached, prefix independent) ------------------------------------
    def _windows(self):
        if self._W is None:
            w = self.min_len
            self._W = [{hash(b[i:i + w]) for i in range(len(b) - w + 1)} for b in self.bmsgs]
        return self._W

    def pair_results(self, a, b):
        key = (a, b)
        r = self._pairs.get(key)
        if r is None:
            A, B = self.bmsgs[a], self.bmsgs[b]
            if A == B:
                r = [(0, len(A))] if len(A) >= self.min_len else []
            elif self._windows()[a].isdisjoint(self._windows()[b]):
                r = []
            else:
                sam = self._sam(a)
                r = maximal_common(sam, B, self.min_len)
            self._pairs[key] = r
        return r

    def _sam(self, a):
        if getattr(self, "_sam_a", None) != a:
            self._sam_a, self._sam_v = a, sam_build(self.bmsgs[a])
        return self._sam_v

    def common_substrings(self, cutoff_m, L):
        """Strings (str) from maximal common substrings of pairs of messages from different conversations, both
        inside the cutoff; the >= L test is applied before trimming to code-point boundaries (build note)."""
        out, skipped = set(), 0
        for a in range(cutoff_m):
            for b in range(a + 1, cutoff_m):
                if self.msg_conv[a] == self.msg_conv[b]:
                    continue
                for st, ln in self.pair_results(a, b):
                    if ln < L:
                        continue
                    bs = trim_utf8(self.bmsgs[b][st:st + ln])
                    if not bs:
                        continue
                    s = bs.decode("utf-8")
                    if len(s) > MAX_BODY_CHARS:
                        skipped += 1
                        continue
                    out.add(s)
        return out, skipped

    # -- occurrences ------------------------------------------------------------------------------------------
    def occurrences(self, body):
        """All (message index, start char) of a literal body in the dev messages (overlapping starts included)."""
        r = self._occ.get(body)
        if r is None:
            r = []
            T, starts = self.T, self.starts
            i = T.find(body)
            import bisect
            while i >= 0:
                m = bisect.bisect_right(starts, i) - 1
                r.append((m, i - starts[m]))
                i = T.find(body, i + 1)
            self._occ[body] = r
        return r

    def template_occurrences(self, entry):
        """Encoder-consistent occurrences of a template candidate: (m, s, e, len_bytes, arg_bytes) for every start
        where the section 3.5 test (segmented or whole-message) yields exactly one parse."""
        key = (entry["body"], json.dumps(entry["params"], sort_keys=True))
        r = self._tocc.get(key)
        if r is None:
            from .compact import eligible_segmented, _encode_args
            toks = parse_template(entry["body"], entry["params"])
            mt = entry_matcher(entry)
            r = []
            lits = [t[1] for t in toks if t[0] == "lit"]
            anchor = max(lits, key=len)
            seen = set()
            import bisect
            i = self.T.find(anchor)
            while i >= 0:
                m = bisect.bisect_right(self.starts, i) - 1
                seen.add(m)
                i = self.T.find(anchor, self.starts[m] + len(self.msgs[m]) + 1)
            for m in sorted(seen):
                text = self.msgs[m]
                if eligible_segmented(entry, toks):
                    lastpos, budget = {}, [MATCH_CALL_CAP, MATCH_WORK_CAP, 0]
                    for s in template_starts(mt, text):
                        hit = template_end(mt, entry, text, s, lastpos, END_TRIES, budget)
                        if hit is not None:
                            e, parse = hit
                            r.append((m, s, e, len(text[s:e].encode("utf-8")), len(_encode_args(entry, parse))))
                else:
                    if text.startswith(mt.lead) and text.endswith(mt.tail):
                        parses = match_template(entry, text)
                        if parses is not None and len(parses) == 1:
                            r.append((m, 0, len(text), len(self.bmsgs[m]), len(_encode_args(entry, parses[0]))))
            self._tocc[key] = r
        return r

    # -- line blocks (level-wise repeat mining) --------------------------------------------------------------
    def line_blocks(self, cutoff_m, k):
        """Repeated runs of consecutive \\n-separated lines (maximal-or-sub), kept iff in >= k distinct conversations
        and <= 16,384 code points. Returns (nodes, skipped) where nodes is a list of dicts
        {text, bytes, convs(frozenset)}; the >= L byte test is applied by the caller."""
        lines = [self.msgs[m].split("\n") for m in range(cutoff_m)]
        intern, ids = {}, []
        for ls in lines:
            row = []
            for ln in ls:
                row.append(intern.setdefault(ln, len(intern)))
            ids.append(row)
        lb = [0] * len(intern)
        lc = [0] * len(intern)
        for ln, i in intern.items():
            lb[i] = len(ln.encode("utf-8"))
            lc[i] = len(ln)
        node_of, info = {}, []  # key -> node id ; info[node] = [bytes, chars, convs, sample]
        cur = {}
        for m in range(cutoff_m):
            for i, lid in enumerate(ids[m]):
                cur.setdefault(lid, []).append((m, i))
        occ, skipped = [], 0
        for lid, lst in cur.items():
            convs = {self.msg_conv[m] for m, _ in lst}
            if len(convs) < k:
                continue
            n = len(info)
            node_of[(-1, lid)] = n
            info.append([lb[lid], lc[lid], frozenset(convs), lst[0] + (lst[0][1],)])
            for m, i in lst:
                occ.append((m, i, i, n))
        level = occ
        while level:
            nxt = {}
            for m, i, j, node in level:
                if j + 1 < len(ids[m]):
                    lid = ids[m][j + 1]
                    nxt.setdefault((node, lid), []).append((m, i, j + 1))
            level = []
            for (node, lid), lst in nxt.items():
                convs = {self.msg_conv[m] for m, _, _ in lst}
                if len(convs) < k:
                    continue
                pb, pc = info[node][0], info[node][1]
                cb, cc = pb + 1 + lb[lid], pc + 1 + lc[lid]
                n = len(info)
                if cc > MAX_BODY_CHARS:
                    skipped += 1
                    node_of[(node, lid)] = n
                    info.append([cb, cc, frozenset(convs), None])
                    continue
                node_of[(node, lid)] = n
                info.append([cb, cc, frozenset(convs), lst[0]])
                for m, i, j in lst:
                    level.append((m, i, j, n))
        res = []
        for n, (bb, cc, convs, sample) in enumerate(info):
            if sample is None:
                continue
            m, i, j = sample
            res.append({"text": "\n".join(lines[m][i:j + 1]), "bytes": bb, "convs": convs})
        return res, skipped

    # -- templates ---------------------------------------------------------------------------------------------
    def mine_templates(self, blocks, k):
        """Section 4 template mining from literal-candidate line blocks (dicts with text, convs)."""
        groups = {}
        for blk in blocks:
            text = blk["text"]
            toks = [(mo.start(), mo.end()) for mo in TOKEN_RE.finditer(text)]
            if not toks:
                continue
            seps, pos = [], 0
            for s, e in toks:
                seps.append(text[pos:s])
                pos = e
            seps.append(text[pos:])
            # separator sequence = the non-token runs in order (empty runs at the ends are layout flags)
            key = (tuple(seps), len(toks))
            groups.setdefault(key, []).append((text, [text[s:e] for s, e in toks], blk["convs"]))
        out, discarded = [], 0
        for (seps, nt), mem in sorted(groups.items(), key=lambda kv: repr(kv[0])):
            if len({m[0] for m in mem}) < 2:
                continue
            convs = set()
            for _, _, c in mem:
                convs |= c
            if len(convs) < k:
                continue
            params, isparam = [], []
            for pos in range(nt):
                vals = {m[1][pos] for m in mem}
                if len(vals) >= 2:
                    typ = "int" if all(INT_RE.match(v) for v in vals) else "word"
                    if not all(WORD_RE.match(v) for v in vals):
                        isparam = None
                        break
                    params.append((f"p{len(params) + 1}", typ))
                    isparam.append(True)
                else:
                    isparam.append(False)
            if isparam is None or not params or len(params) > MAX_TEMPLATE_PARAMS:
                discarded += 1
                continue
            first = mem[0][1]
            body, pi = [], 0
            for pos in range(nt):
                body.append(_esc(seps[pos]))
                if isparam[pos]:
                    body.append("{" + params[pi][0] + "}")
                    pi += 1
                else:
                    body.append(first[pos])
            body.append(_esc(seps[nt]))
            body = "".join(body)
            if len(body) > MAX_BODY_CHARS:
                discarded += 1
                continue
            try:
                e = make_entry_strict("e00000", 1, body, params, prov=self.prov)
            except E1EError:
                discarded += 1
                continue
            ok = True
            for text, _, _ in mem:  # unambiguous on all source occurrences
                p = match_template(e, text)
                if p is None or len(p) != 1:
                    ok = False
                    break
            if not ok:
                discarded += 1
                continue
            out.append((body, params, frozenset(convs)))
        return out, discarded

    # -- the build ----------------------------------------------------------------------------------------------
    def curate(self, n_convs, L, k, C, joiners=0):
        """Section 4 curation over the first n_convs conversations. Returns (picks, stats). A pick is a dict with
        kind, body, params, G, total_len, occurrences, convs (source-conversation lineage as indexes)."""
        cutoff = self.cutoff_msgs(n_convs)
        stats = {"n_convs": n_convs, "messages": cutoff, "L": L, "k": k, "C": C, "joiners": joiners,
                 "oversized_messages_excluded": sum(1 for ci, _ in self.oversized if ci < n_convs),
                 "oversized_bytes_excluded": sum(b for ci, b in self.oversized if ci < n_convs)}
        if cutoff == 0:
            return [], stats
        blocks, sk_lines = self.line_blocks(cutoff, k)
        blocks = [b for b in blocks if b["bytes"] >= L]
        cs, sk_cs = self.common_substrings(cutoff, L)
        cands = {}  # key (kind, body, params-json) -> (kind, body, params)
        for b in blocks:
            cands.setdefault(("literal", b["text"], "[]"), ("literal", b["text"], []))
        for s in cs:
            cands.setdefault(("literal", s, "[]"), ("literal", s, []))
        # literal candidates are kept iff they occur in >= k distinct conversations (line blocks already do)
        lit = {}
        for key, (kind, body, params) in cands.items():
            occ = [o for o in self.occurrences(body) if o[0] < cutoff]
            if len({self.msg_conv[m] for m, _ in occ}) >= k:
                lit[key] = (kind, body, params)
        tpls, tdisc = self.mine_templates(blocks, k)
        for body, params, _ in tpls:
            lit.setdefault(("template", body, json.dumps(params)), ("template", body, params))
        stats.update({"line_block_candidates": len(blocks), "common_substring_candidates": len(cs),
                      "literal_candidates": sum(1 for v in lit.values() if v[0] == "literal"),
                      "template_candidates": sum(1 for v in lit.values() if v[0] == "template"),
                      "templates_discarded": tdisc, "bodies_over_16384_skipped": sk_lines + sk_cs})
        picks = self._greedy(lit, cutoff, C, joiners)
        stats["picks"] = len(picks)
        return picks, stats

    def _occ_list(self, kind, body, params, cutoff):
        """Occurrences (m, s, e, len_bytes, arg_bytes) within the cutoff."""
        if kind == "literal":
            lb = len(body.encode("utf-8"))
            return [(m, s, s + len(body), lb, 0) for m, s in self.occurrences(body) if m < cutoff]
        e = make_entry_strict("e00000", 1, body, params, prov=self.prov)
        return [o for o in self.template_occurrences(e) if o[0] < cutoff]

    def _greedy(self, cands, cutoff, C, joiners):
        """Section 4.4 greedy with an exact (not lazy) objective. After every selection each remaining candidate's gain
        is the gain recomputed against the current mask. The candidate's gain depends on the mask only through the
        messages of its own occurrences, so exactly the candidates with an occurrence in a message touched by the
        selection are recomputed (the others are provably unchanged); no monotonicity of G is assumed, because a masked
        occurrence with a negative contribution can raise a candidate's G. Selection: highest G, then larger total
        matched bytes, then lexicographically smaller body bytes, then the candidate's fixed enumeration index; stop
        when C picks exist or the best remaining G <= 0."""
        mult = 1 + joiners
        mask = {}
        store, by_msg = [], collections.defaultdict(list)
        for key in sorted(cands, key=lambda x: (x[1], x[2])):
            kind, body, params = cands[key]
            occ = self._occ_list(kind, body, params, cutoff)
            if not occ:
                continue
            rec = _record_size(kind, body, [dict(name=n, type=t) for n, t in params], self.prov) * mult
            cid = len(store)
            store.append((kind, body, params, occ, rec))
            for m in {o[0] for o in occ}:
                by_msg[m].append(cid)
        cur, ver, heap = {}, {}, []  # cid -> (G, total_len, spans) against the current mask; version stamps; max-heap

        def refresh(cid):
            kind, body, params, occ, rec = store[cid]
            cur[cid] = res = self._gain(occ, rec, mask)
            ver[cid] = ver.get(cid, 0) + 1
            if res[0] > 0:
                heapq.heappush(heap, (-res[0], -res[1], body.encode("utf-8"), cid, ver[cid]))

        for cid in range(len(store)):
            refresh(cid)
        picks = []
        while len(picks) < C:
            while heap and (heap[0][3] not in cur or heap[0][4] != ver[heap[0][3]]):
                heapq.heappop(heap)  # stale entry: its candidate was picked or recomputed since
            if not heap:
                break
            cid = heapq.heappop(heap)[3]
            kind, body, params, occ, rec = store[cid]
            g, tl, used = cur.pop(cid)
            touched = set()
            for m, s, e in used:
                mk = mask.get(m)
                if mk is None:
                    mk = mask[m] = bytearray(len(self.msgs[m]))
                mk[s:e] = b"\x01" * (e - s)
                touched.add(m)
            picks.append({"kind": kind, "body": body, "params": params, "G": g, "total_len": tl,
                          "occurrences": len(used), "convs": sorted({self.msg_conv[m] for m, _, _ in used}),
                          "entry_cost": rec})
            for c in sorted({c for m in touched for c in by_msg[m] if c in cur}):
                refresh(c)
        return picks

    @staticmethod
    def _gain(occ, rec, mask):
        """G(c) over the unblocked, left-to-right non-overlapping occurrences. Returns (G, total matched bytes, spans)."""
        g, tl, used, last_m, last_e = 0, 0, [], -1, -1
        for m, s, e, lb, ab in occ:
            if m != last_m:
                last_m, last_e = m, -1
            if s < last_e:
                continue
            mk = mask.get(m)
            if mk is not None and mk.find(b"\x01", s, e) >= 0:
                continue
            g += lb - (1 + PROVISIONAL_ORDINAL_BYTES + ab)
            tl += lb
            used.append((m, s, e))
            last_e = e
        return g - rec, tl, used


def _esc(s):
    return s.replace("{", "{{").replace("}", "}}")


# ---------------------------------------------------------------- ids and versions
def assign_ids(picks, prev_entries=None):
    """Ids are unspecified by the spec (build note). Reuse the id of an identical (kind, body, params) already in the
    previous snapshot (append-only repositories: E1E-REPO/1 defers deletion); new bodies get e{counter:05d} in pick order."""
    prev = {}
    mx = 0
    for e in (prev_entries or {}).values():
        prev[(e["kind"], e["body"], json.dumps([[p["name"], p["type"]] for p in e["params"]]))] = e["id"]
        if re.fullmatch(r"e\d{5}", e["id"]):
            mx = max(mx, int(e["id"][1:]))
    out, nxt = [], mx + 1
    for p in picks:
        k = (p["kind"], p["body"], json.dumps([list(x) for x in p["params"]]))
        if k in prev:
            out.append((prev[k], p, False))
        else:
            out.append((f"e{nxt:05d}", p, True))
            nxt += 1
    return out


def entries_from_picks(picks, prov, prev_entries=None):
    """Entries for the picks (all v=1 for new ids). Entries already present are not re-issued."""
    res = []
    for id_, p, new in assign_ids(picks, prev_entries):
        if new:
            res.append(make_entry_strict(id_, 1, p["body"], p["params"] or None, prov=prov))
    return res


# ---------------------------------------------------------------- forward-only tuning (section 4)
def tune(miner, evaluate, grid_L=GRID_L, grid_k=GRID_K, grid_C=GRID_C):
    """Forward-only five-block tuning. For each grid point and t = 2..5: curate from blocks B1..B(t-1) ONLY (the
    conversations before block t) and call evaluate(picks, (conv_start, conv_end)) -> arm-7 total in bytes
    (messages + sync, V = 1 static) on block Bt. The score is the mean over t; lowest wins, ties by smaller L, then
    k, then C. The greedy pick sequence does not depend on C (it stops at G <= 0 or C picks), so one curation with
    max(C) serves every C by taking a prefix. Returns (best (L, k, C), scores {(L, k, C): mean})."""
    n = len(miner.conv_ids)
    if n < 5:
        raise ValueError("tuning needs at least 5 dev conversations")
    blocks = tuning_blocks(n)
    sums = {}
    for L in grid_L:
        for k in grid_k:
            for t in range(1, 5):  # zero-based block index of Bt, t = 2..5
                start, end = blocks[t]
                picks, _ = miner.curate(start, L, k, max(grid_C))  # only conversations before block t
                for C in grid_C:
                    sums[(L, k, C)] = sums.get((L, k, C), 0) + evaluate(picks[:C], (start, end))
    scores = {g: s / 4 for g, s in sums.items()}
    best = min(sums, key=lambda g: (sums[g], g[0], g[1], g[2]))
    return best, scores


# ---------------------------------------------------------------- repository chain for a scenario
class Chain(list):
    """The published snapshots of one scenario, in publication order (list index i-1 = repository version i), plus the
    complete scheduled-version metadata: `schedule` has one dict per scheduled version 1..V
    {sched_version, n_convs, status ('published'|'empty'|'unused'), published_index|None, new_entries, overflow, picks};
    `trailing_skipped` = scheduled versions after the last publication (empty or unused); `max_version` = the highest
    scheduled version curated; `V`."""
    schedule = ()
    trailing_skipped = ()
    max_version = 0
    V = 0


def build_repository_chain(miner, n_dev, V, L, k, C, joiners, max_version=None):
    """AMENDMENT A1, section 4.7 (append-only publication). Scheduled version j (1..V) is curated from the first
    prefix_size(j, n_dev, V) dev conversations for EVERY j <= max_version (default V; a caller passes the highest
    scheduled version any replayed message uses; higher versions cannot influence a message and are not curated, status
    'unused'). The repository is the append-only union of everything published so far: the picks of version j (the
    top-C greedy sequence, in pick order) whose (kind, body, params) are not already in the repository become new
    entries; an existing entry keeps its id and v=1 forever (deletion and updates are deferred); a new entry gets id
    e{N:05d} with N = 1 + the largest numeric id so far, in pick order. The union (not C) is limited by MAX_ENTRIES =
    4096: if the new entries do not fit, the LAST new entries in pick order are dropped and counted as `overflow`. A
    scheduled version with no new entry (an unchanged or empty snapshot) publishes NOTHING: the previous snapshot stays
    current and the version is `empty`. Repository versions are numbered 1..P consecutively over the non-empty
    publications only, so V is a count of scheduled curation points, not of repository versions. A message scheduled at
    version s uses the latest published snapshot whose sched_version <= s (version 0 = the empty repository if none).
    Returns a Chain of per-publication records {sched_version, state, full, delta (None for the first), picks, stats,
    new_entries, overflow, skipped_versions (scheduled versions with no publication since the previous one),
    entry_lineage [{id, kind, G, occurrences, convs}] (source-conversation lineage of each new entry at first
    publication; PRIVATE: conversation ids)}."""
    from .repo import Publisher
    mv = V if max_version is None else min(V, max_version)
    pub = Publisher()
    chain, skipped = Chain(), []
    sched = []
    for j in range(1, V + 1):
        nj = prefix_size(j, n_dev, V)
        row = {"sched_version": j, "n_convs": nj, "status": "unused", "published_index": None, "new_entries": 0,
               "overflow": 0, "picks": 0}
        sched.append(row)
        if j > mv:
            skipped.append(j)
            continue
        picks, st = miner.curate(nj, L, k, C, joiners)
        row["picks"] = len(picks)
        prev = pub.state.entries if chain else None
        assigned = [(i, p) for i, p, new in assign_ids(picks, prev) if new]
        room = MAX_ENTRIES - len(pub.state.entries)
        overflow = max(0, len(assigned) - room)
        assigned = assigned[:room] if overflow else assigned
        row["overflow"] = overflow
        if not assigned:
            row["status"] = "empty"
            skipped.append(j)
            continue
        ents = [make_entry_strict(i, 1, p["body"], p["params"] or None, prov=miner.prov) for i, p in assigned]
        delta, full = pub.publish(ents)
        row.update(status="published", published_index=len(chain) + 1, new_entries=len(ents))
        chain.append({"sched_version": j, "state": pub.state, "full": full, "delta": delta if len(chain) else None,
                      "picks": picks, "stats": st, "new_entries": len(ents), "overflow": overflow,
                      "skipped_versions": skipped,
                      "entry_lineage": [{"id": i, "kind": p["kind"], "G": p["G"], "occurrences": p["occurrences"],
                                         "convs": p["convs"]} for i, p in assigned]})
        skipped = []
    chain.schedule, chain.trailing_skipped, chain.max_version, chain.V = sched, list(skipped), mv, V
    return chain
