"""Development diagnostic: reference-size inflation on the GPT-generated synthetic set.
NOT a savings claim. In-sample (dictionary built from the same messages it encodes), synthetic only.

Dictionary rule (deterministic):
 1. Literal entry for every exact message text that occurs >= 2 times (id lit-NNNN, ordered by text).
 2. Template induction: split each remaining text into alternating non-whitespace / whitespace tokens
    (re '\\S+|\\s+'). Group texts by key = (first token, tuple of all whitespace tokens, token count).
    Groups of >= 2 distinct texts: positions where every member agrees are literal, others become
    params p0,p1,.. typed int (all canonical ints) > word (all [A-Za-z0-9_.-]+) > text.
    Keep only if >= half of non-whitespace positions are literal and the template validates.
    Ids tpl-NNNN ordered by key repr. Braces in literals are escaped.
Run: python3 tools/dev_inflation.py   (stdlib + e1e only)
"""
import collections
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from e1e import Publisher, make_entry, E1EError, encode, decode_message  # noqa: E402
from e1e.codec import raw_wire  # noqa: E402
from e1e.schema import INT_RE, WORD_RE  # noqa: E402

DATA = os.path.join(os.path.dirname(HERE), "data", "synthetic_gpt_r1.jsonl")
OUT = os.path.join(os.path.dirname(HERE), "measurements", "dev_inflation_synthetic.json")
HEX_FULL = 64
DIGESTS_PER_REF = 2  # "snap" and "entry"


def esc(s):
    return s.replace("{", "{{").replace("}", "}}")


def build_entries(texts):
    counts = collections.Counter(texts)
    ents = [make_entry(f"lit-{i:04d}", 1, t) for i, t in enumerate(sorted(t for t, c in counts.items() if c >= 2))]
    rest = sorted(t for t, c in counts.items() if c == 1)
    groups = collections.defaultdict(list)
    for t in rest:
        toks = re.findall(r"\S+|\s+", t)
        if not toks:
            continue
        key = (toks[0], tuple(x for x in toks if x.isspace()), len(toks))
        groups[key].append(toks)
    n = 0
    for key in sorted(groups, key=repr):
        g = groups[key]
        if len(g) < 2:
            continue
        body, params, lit_ws, nonws = [], [], 0, 0
        for pos in range(key[2]):
            col = [m[pos] for m in g]
            if col[0].isspace() or len(set(col)) == 1:
                body.append(esc(col[0]))
                if not col[0].isspace():
                    lit_ws += 1; nonws += 1
                continue
            nonws += 1
            typ = ("int" if all(INT_RE.match(c) for c in col) else
                   "word" if all(WORD_RE.match(c) for c in col) else "text")
            name = f"p{len(params)}"
            params.append((name, typ)); body.append("{" + name + "}")
        if not params or lit_ws * 2 < nonws:
            continue
        try:
            ents.append(make_entry(f"tpl-{n:04d}", 1, "".join(body), params))
            n += 1
        except E1EError:
            pass
    return ents


def main():
    recs = [json.loads(l) for l in open(DATA, encoding="utf-8") if l.strip()]
    texts = [r["text"] for r in recs]
    ents = build_entries(texts)
    pub = Publisher(); pub.publish(ents)
    st = pub.state; decl = {"version": st.version, "digest": st.digest}
    rows = []
    for r in recs:
        m = r["text"].encode("utf-8")
        wire, info = encode(pub.history, decl, m)
        assert decode_message(st, wire) == m
        rows.append({"is_ref": info["reason"] == "ref", "wire": len(wire), "msg": len(m), "env": len(raw_wire(m))})
    refs = [x for x in rows if x["is_ref"]]

    def larger(hexlen):
        return larger_cut(DIGESTS_PER_REF * (HEX_FULL - hexlen))

    def larger_cut(cut):
        return {"ref_wire_gt_raw_message_bytes": sum(x["wire"] - cut > x["msg"] for x in refs),
                "ref_wire_gt_raw_envelope_bytes": sum(x["wire"] - cut > x["env"] for x in refs)}

    out = {
        "label": "DEVELOPMENT DIAGNOSTIC ONLY - synthetic GPT-generated data, in-sample dictionary, NOT a savings claim",
        "data": "data/synthetic_gpt_r1.jsonl",
        "messages": len(rows), "conversations": len({r["conv_id"] for r in recs}),
        "dictionary": {"entries": len(ents), "literal": sum(e["kind"] == "literal" for e in ents),
                       "template": sum(e["kind"] == "template" for e in ents),
                       "full_snapshot_bytes": len(st.full_bytes())},
        "encoded_as_ref": len(refs), "sent_raw": len(rows) - len(refs),
        "all_round_trips_exact": True,
        "full_64hex": larger(64),
        "hypothetical_12hex": dict(larger(12), note="HYPOTHETICAL: arithmetic only, 2 digests x 52 hex chars removed, sha256: prefix kept; no such format exists"),
        "hypothetical_no_digest_fields_values": dict(larger_cut(DIGESTS_PER_REF * len('"sha256:' + "0" * 64 + '"')), note="HYPOTHETICAL: both digest values removed entirely (quotes, sha256: prefix and 64 hex); keys, ids, versions, args and framing remain; does not isolate escaping"),
        "excess_breakdown_full_64hex": {"ref_excess_over_raw_message_bytes_total": sum(x["wire"] - x["msg"] for x in refs),
                                        "hex_digit_bytes_in_refs_total": DIGESTS_PER_REF * HEX_FULL * len(refs),
                                        "note": "hex digits are part of the excess; the remainder is keys, prefixes, ids, versions, args, quoting/escaping, not separated here"},
        "hypothetical_8hex": dict(larger(8), note="HYPOTHETICAL: arithmetic only, 2 digests x 56 hex chars removed, sha256: prefix kept; no such format exists"),
        "bytes_full_64hex": {"raw_message_total": sum(x["msg"] for x in rows),
                             "wire_total": sum(x["wire"] for x in rows),
                             "raw_envelope_total_if_all_raw": sum(x["env"] for x in rows),
                             "ref_messages_raw_total": sum(x["msg"] for x in refs),
                             "ref_messages_wire_total": sum(x["wire"] for x in refs)},
    }
    with open(OUT, "w", encoding="ascii") as f:
        json.dump(out, f, indent=1, sort_keys=True); f.write("\n")
    print(json.dumps(out, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
