"""E1d (DRAFT): build the minimal dictionary distribution artifact from a book, round-trip it through the receiver
loader, and count its exact bytes. CPU only, read-only on the book; no model, no network.

  python v6/e1d/tools/measure_dict_artifact.py [book.json] [out.json]
  default book = v6/e1c/data/book_test.json (E1c T1 TEST book), default out = stdout

Artifact format "E1D-DICT/1" (UTF-8, LF line ends), frozen by DRAFT_PLAN.md §4.2:
  line 1 (manifest): E1D-DICT/1 kind=<full|delta> dict_ver=<int> base=<int|-> n=<entries> sha256=<hex of body>
  body: one line per member entry, sorted by id:  <id>@v<ver>#<hash8> <entry text>
The receiver needs nothing else: e1b Dictionary.resolve checks id, membership, version and hash8, and the delegate
expands an accepted ID to the entry text. The loader re-derives sha256(text)[:8] and checks it against hash8, and
checks the manifest count and body digest. The loader output is a book-like dict fed to the UNCHANGED
e1b.protocol.Dictionary, so the round trip is checked against the E1c resolve code itself."""
import sys, json, hashlib, gzip, re
from pathlib import Path
V6 = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(V6 / "e1b")); sys.path.insert(0, str(V6 / "e1c"))
from e1b import sha256_text
from e1b.protocol import framed_id, Dictionary, MSG_RE, rule_block

MAGIC = "E1D-DICT/1"
HDR = re.compile(r"^E1D-DICT/1 kind=(full|delta) dict_ver=(\d+) base=(\d+|-) n=(\d+) sha256=([0-9a-f]{64})$")

def line(e): return f"{framed_id(e)} {e['text']}\n"

def build(E, members, kind="full", dict_ver=1, base=None):
    body = "".join(line(E[k]) for k in sorted(set(members))).encode("utf-8")
    hdr = f"{MAGIC} kind={kind} dict_ver={dict_ver} base={'-' if base is None else base} n={len(set(members))} sha256={hashlib.sha256(body).hexdigest()}\n"
    return hdr.encode("utf-8") + body, len(hdr.encode("utf-8")), len(body)

def load(raw, base=None):
    """-> book-like {'entries': {id: {id, ver, hash(=hash8), text}}, 'dictionary': [ids], 'dict_ver': v}.
    A delta needs `base` (a previous load() result) at dict_ver == the delta's base."""
    txt = raw.decode("utf-8"); hdr, _, body = txt.partition("\n"); m = HDR.match(hdr)
    if not m: raise ValueError("bad manifest")
    kind, ver, bver, n, h = m.group(1), int(m.group(2)), m.group(3), int(m.group(4)), m.group(5)
    if hashlib.sha256(body.encode("utf-8")).hexdigest() != h: raise ValueError("body digest mismatch")
    lines = body.split("\n"); assert lines[-1] == ""; lines = lines[:-1]
    if len(lines) != n: raise ValueError("entry count mismatch")
    E = {}
    if kind == "delta":
        if base is None or str(base["dict_ver"]) != bver: raise ValueError("delta base version mismatch")
        E = {k: dict(v) for k, v in base["entries"].items()}
    for ln in lines:
        fid, _, text = ln.partition(" "); mm = MSG_RE.match(fid)
        if not mm: raise ValueError(f"bad framed id {fid}")
        eid, ev, h8 = mm.group(1), int(mm.group(2)), mm.group(3)
        if sha256_text(text)[:8] != h8: raise ValueError(f"hash8 mismatch {eid}")
        if eid in E and kind == "full": raise ValueError(f"duplicate {eid}")
        E[eid] = dict(id=eid, ver=ev, hash=h8, text=text)
    return dict(entries=E, dictionary=sorted(E), dict_ver=ver)

def roundtrip(B, members, L):
    """Every member resolves 'ok' through the unchanged e1b Dictionary with identical text and receiver rule block;
    non-members are 'unknown_id'; stale version / wrong hash rejected."""
    D = Dictionary(L); E = B["entries"]; bad = []
    for k in members:
        ent, why = D.resolve(framed_id(E[k]))
        if why != "ok" or ent["text"] != E[k]["text"] or rule_block(ent["text"]) != rule_block(E[k]["text"]): bad.append(k)
    non = [k for k in sorted(E) if k not in set(members) and E[k].get("hash")][:200]
    non_ok = all(D.resolve(framed_id(E[k]))[1] == "unknown_id" for k in non)
    k0 = sorted(members)[0]; e0 = E[k0]
    stale = D.resolve(f"{e0['id']}@v{e0['ver'] + 1}#{e0['hash'][:8]}")[1]
    wrong = D.resolve(f"{e0['id']}@v{e0['ver']}#{'0' * 8 if e0['hash'][:8] != '0' * 8 else '1' * 8}")[1]
    return dict(members_ok=len(members) - len(bad), members=len(members), failures=bad[:5], non_members_checked=len(non),
                non_members_unknown=non_ok, stale_version=stale, wrong_hash=wrong)

def gz(b): return len(gzip.compress(b, compresslevel=9, mtime=0))

def measure(B, members, label):
    raw, hb, bb = build(B["entries"], members); L = load(raw)
    try: load(raw[:-2] + b"X\n"); tamper = "NOT DETECTED"
    except ValueError as ex: tamper = f"rejected ({ex})"
    return dict(label=label, n_entries=len(set(members)), manifest_bytes=hb, body_bytes=bb, artifact_bytes=len(raw),
                artifact_gzip9_bytes=gz(raw), mean_line_bytes=bb / len(set(members)), sha256=hashlib.sha256(raw).hexdigest(),
                roundtrip=roundtrip(B, sorted(set(members)), L), tamper_check=tamper)

def serialize(case_text, kind, payload):
    """Frozen E1d message serializer (DRAFT_PLAN §4.1): canonical JSON, UTF-8, no whitespace, sorted keys.
    kind 'i' = framed ID, 'p' = prose."""
    return json.dumps({"c": case_text, kind: payload}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

def main():
    bp = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else V6 / "e1c" / "data" / "book_test.json"
    raw = bp.read_bytes(); B = json.loads(raw); E = B["entries"]; N = B["neighbours"]
    core = [k for f in ("F1", "F2") for k in B["e1c_core"][f]]
    t1 = sorted({x for k in core for x in [k] + N[k]})           # what a T1 sender could pick: core + neighbours
    pub = sorted(set(B["dictionary"]))                            # the published membership e1b Dictionary(B) uses
    out = dict(book=str(bp.relative_to(V6.parent)), book_sha256=hashlib.sha256(raw).hexdigest(), format=MAGIC,
               t1_minimal=measure(B, t1, "E1c T1 assigned core (240) + neighbours"),
               published=measure(B, pub, "book['dictionary'] (published membership used by Dictionary(B))"))
    # cross-checks against the E1c registered cost and GPT r2's figure (independent line sums)
    from e1c.analysis import dict_bytes
    out["crosscheck"] = dict(e1c_dict_bytes_registered=dict_bytes(B, core),
                             published_line_sum_independent=sum(len((framed_id(E[k]) + " " + E[k]["text"] + "\n").encode()) for k in pub))
    sp = set(pub); used = set(core); allcore = {k for f in ("F1", "F2") for k in B["groups"][f"core_{f}"]}
    honest = {k for k in sp if E[k]["kind"] == "honest"}
    out["published_breakdown"] = dict(core_used=len(used & sp), core_spare_2n_build=len((allcore - used) & sp),
                                      F3L=len(set(B["groups"]["F3L"]) & sp), neighbours=len(sp - honest),
                                      honest_total=len(honest))
    # delta example: last 10% of core (by sorted id) + their neighbours as dict_ver 2 over the remaining 90% (v1)
    cs = sorted(core); cut = len(cs) - len(cs) // 10; c1, c2 = cs[:cut], cs[cut:]
    m1 = sorted({x for k in c1 for x in [k] + N[k]}); m2 = sorted({x for k in c2 for x in [k] + N[k]} - set(m1))
    r1, _, _ = build(E, m1); r2, h2, b2 = build(E, m2, kind="delta", dict_ver=2, base=1)
    L2 = load(r2, base=load(r1)); rt = roundtrip(B, t1, L2)
    out["delta_example"] = dict(core_added=len(c2), entries_added=len(m2), manifest_bytes=h2, body_bytes=b2,
                                delta_bytes=len(r2), applied_equals_full=(L2["entries"] == load(build(E, t1)[0])["entries"]),
                                roundtrip_after_delta=rt)
    # serializer framing overhead on the T1 cases/payloads (constant if no JSON escaping is needed)
    cases = [c for c in B["cases"]["test"] if c["entry"] in used]
    from e1b.protocol import render_message
    ov_p = {len(serialize(c["text"], "p", render_message(E[c["entry"]]))) - len(c["text"].encode()) - len(render_message(E[c["entry"]]).encode()) for c in cases}
    ov_i = {len(serialize(c["text"], "i", framed_id(E[c["entry"]]))) - len(c["text"].encode()) - len(framed_id(E[c["entry"]]).encode()) for c in cases}
    out["serializer_framing_bytes"] = dict(prose=sorted(ov_p), id=sorted(ov_i), n_cases=len(cases))
    s = json.dumps(out, indent=1, sort_keys=True)
    if len(sys.argv) > 2: Path(sys.argv[2]).write_text(s + "\n")
    print(s)

if __name__ == "__main__": main()
