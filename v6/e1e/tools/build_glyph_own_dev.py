"""Build the sanitised Glyph-own DEVELOPMENT corpus (data/glyph_own_dev_r1.jsonl).

Approved by the operator on 2026-10-21 21:08 AEDT as development-only data. Never evaluation data.
Sources (box-local, not committed): Codex CLI session transcripts saved under /tmp, Glyph's own public
forum request bodies under /workspace/e1dpost/body*.md, and committed review files under v6/*/reviews/.
Excluded: raw chat with the operator, other agents' forum replies (third-party content), command
OUTPUT inside Codex transcripts (file dumps, not messages), duplicated transcript copies, and the
generated output of the synthetic-data sessions (already in synthetic_gpt_r1.jsonl).
Sanitisation policy: see SANITISE below and data/README.md. Run: python3 tools/build_glyph_own_dev.py
"""
import glob
import json
import os
import re
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
E1E = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(E1E))
OUT = os.path.join(E1E, "data", "glyph_own_dev_r1.jsonl")

TRANSCRIPTS = [  # (path, label); one Codex session each, deduplicated by session id
    ("/tmp/gpt_e1e_r1.txt", "codex_pilot_review_r1"),
    ("/tmp/gpt_e1e_code_r1.err", "codex_code_review_r1"),
    ("/tmp/gpt_e1e_code_r2.err", "codex_code_review_r2"),
    ("/tmp/syn_part1.err", "codex_synthetic_request_1"),
    ("/tmp/syn_part2.err", "codex_synthetic_request_2"),
    ("/tmp/syn_part3.err", "codex_synthetic_request_3"),
    ("/tmp/gpt_e1e_code_r3.txt", "codex_code_review_r3"),
    ("/tmp/gpt_e1e_code_r4.err", "codex_code_review_r4"),
    ("/tmp/gpt_e1e_code_r5.err", "codex_code_review_r5"),
]
FORUM = sorted(glob.glob("/workspace/e1dpost/body*.md"))

# Ordered substitutions. Applied to every text; order matters (URLs before paths, etc.).
SANITISE = [
    (r"-----BEGIN [A-Z ]+-----.*?-----END [A-Z ]+-----", "<SECRET>"),
    (r"\b(sk-|ghp_|gho_|github_pat_|xox[abp]-|AKIA|AIza|hf_)[A-Za-z0-9_\-]{8,}", "<SECRET>"),
    (r"(?i)\b(authorization\s*:\s*)(bearer|basic|token)\s+\S+", r"\1<SECRET>"),
    (r"(?i)(?<![/\w])(bearer|basic)\s+(?!<SECRET>)[A-Za-z0-9._~+/=\-]+", r"\1 <SECRET>"),
    (r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-.]+", "<SECRET>"),
    (r"(?i)\b(?:https?|ssh|git|ftp|sftp|file|wss?)://[^\s)\]>\"'`]*", "<URL>"),
    (r"(?:\"[^\"\n]*\"|[\w.+-]+)@[\w-]+(\.[\w-]+)+", "<EMAIL>"),
    (r"(?<![\w])[A-Za-z]:\\[^\s\"'`]*", "<PATH>"),
    (r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", "<UUID>"),
    (r"\b[a-z]{1,3}_[0-9A-HJKMNP-TV-Z]{26}\b", "<ID>"),
    (r"\bsha256:[0-9a-f]{8,64}\b", "<HASH>"),
    (r"\b(?=[0-9a-fA-F]*[a-fA-F])(?=[0-9a-fA-F]*[0-9])[0-9a-fA-F]{7,64}\b", "<HASH>"),
    (r"(?<![\w.])(/(home|workspace|tmp|cursor|root|usr|etc|var|opt|mnt|Users|private|Volumes)(/[^\s:\"'`)\],]*)?)", "<PATH>"),
    (r"\b\d{6,}\b", "<NUM>"),
    (r"\bdevamped1337\b", "<ORG>"),
    (r"\bglyph-alphabet-experiments\b", "<REPO>"),
    (r"(?i)\bstefan( markovich)?\b", "<OPERATOR>"),
    (r"(?i)\bmarkovich\b", "<OPERATOR>"),
    (r"(?i)\bdevamped\w*", "<HANDLE>"),
    (r"(?i)\bglyph\b", "<AGENT_SELF>"),
    # generic handle detectors
    (r"(?<![\w@])@(?!(?:property|staticmethod|classmethod|dataclass|abstractmethod)(?![\w.]))[A-Za-z0-9_][A-Za-z0-9_.-]*", "<HANDLE>"),
    (r"(?<![\w/])u/[A-Za-z0-9_-]{2,}", "<HANDLE>"),
    (r"\b(?=[A-Za-z0-9_.-]*[-_0-9])[A-Za-z][A-Za-z0-9_.-]*(?= (?:on|from|at) (?:1f916|[Mm]oltbook|[Oo]rbiobook)\b)", "<HANDLE>"),
]

# Credential-context keys: any identifier ending in one of these (case-insensitive), optionally quoted
# (also backslash-escaped quotes), followed by '=' or ':'.
CRED_KEY = (r"(?i)(?<![A-Za-z0-9])(\\?[\"']?)([A-Za-z0-9_.-]*?(?:token|secret|password|passwd|passphrase|pwd|api[_-]?key"
            r"|apikey|private[_-]?key|credentials?|cookie|session[_-]?key))(\\?[\"']?)(\s*[=:]\s*)")
def redact_credentials(t):
    """Conservative: after a credential-context key and separator, redact the REST OF THE LINE.
    This covers quoted, escaped, multiply-encoded, array and backslash-escaped values without parsing them."""
    return re.sub(CRED_KEY + r"(?!<SECRET>$)[^\n]*", lambda m: m.group(0)[:m.end(4) - m.start()] + "<SECRET>", t, flags=re.M)


def known_handles():
    """Forum handles/agent names from the box's forum JSON (author fields and 'X on <forum>' mentions)."""
    names = set()
    srcs = json.load(open(os.path.join(HERE, "glyph_own_dev_inputs.json")))["handle_sources"]
    for f in [x["path"] for x in srcs if os.path.exists(x["path"])]:  # box-local; absent elsewhere
        try:
            raw = open(f, encoding="utf-8").read(); obj = json.loads(raw)
        except Exception:
            continue
        stack = [obj]
        while stack:
            o = stack.pop()
            if isinstance(o, dict):
                for k, v in o.items():
                    if k in ("author", "author_name", "username", "handle", "user", "agent_name") and isinstance(v, str):
                        names.add(v)
                    if k in ("author", "user", "agent") and isinstance(v, dict):
                        for kk in ("name", "handle", "username", "display_name"):
                            if isinstance(v.get(kk), str):
                                names.add(v[kk])
                    stack.append(v)
            elif isinstance(o, list):
                stack.extend(o)
        names.update(re.findall(r"([A-Za-z0-9_.-]+) on (?:1f916|[Mm]oltbook|[Oo]rbiobook)", raw))
    stop = {"posted", "reply", "comment", "thread", "post", "me", "us", "here", "this", "it"}
    return sorted({n for n in names if len(n) >= 3 and n.lower() not in stop}, key=lambda n: (-len(n), n))


HANDLES = known_handles()


# Enforced post-sanitisation scan: any hit aborts the build before anything is written.
FORBIDDEN = [
    r"@[\w-]+\.[\w.-]+", r"(?i)\b[a-z][a-z0-9+.-]*://", r"(?i)<URL>[^\s<]", r"(?i)\bwww\.", r"(?i)stefan|markovich|devamped",
    r"(?<![\w.])/(home|workspace|tmp|Users|root|cursor|private|Volumes)/", r"(?<![\w])[A-Za-z]:\\",
    r"\b(sk-|ghp_|gho_|github_pat_|xox[abp]-|AKIA|AIza|hf_|glpat-)\w{6,}",
    r"\beyJ[\w-]{10,}", r"-----BEGIN", r"(?i)(?<![/\w])(bearer|basic)\s+(?!<SECRET>)[A-Za-z0-9._~+/=-]+",
    r"\b[0-9a-fA-F]{32,}\b", r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-", r"[A-Za-z0-9+/]{40,}={0,2}", r"(?i)session id",
    r"(?i)\bglyph\b", r"(?<![\w@])@(?!(?:property|staticmethod|classmethod|dataclass|abstractmethod)(?![\w.]))[A-Za-z0-9_]",
    r"(?<![\w/])u/[A-Za-z0-9_-]{2,}",
]


def scan(t):
    """Independent rejection scan; raises SystemExit on any hit."""
    for m in re.finditer(CRED_KEY, t):
        rest = t[m.end():].split("\n", 1)[0]
        if rest != "<SECRET>":
            raise SystemExit(f"post-sanitisation scan failed: credential value after {m.group(2)!r}")
    low = t.lower()
    for h in HANDLES:
        if re.search(r"(?<![a-z0-9_])" + re.escape(h.lower()) + r"(?![a-z0-9_])", low):
            raise SystemExit("post-sanitisation scan failed: known handle survived")
    for p in FORBIDDEN:
        m = re.search(p, t)
        if m:
            raise SystemExit(f"post-sanitisation scan failed: {p!r} matched {m.group(0)[:20]!r}...")


def sanitise(t):
    t = redact_credentials(t)
    for h in HANDLES:
        t = re.sub(r"(?i)(?<![A-Za-z0-9_])" + re.escape(h) + r"(?![A-Za-z0-9_])", "<HANDLE>", t)
    for pat, rep in SANITISE:
        t = re.sub(pat, rep, t, flags=re.S)
    return t


def parse_transcript(path):
    lines = open(path, encoding="utf-8", errors="replace").read().split("\n")
    sid = next((l.split(":", 1)[1].strip() for l in lines if l.startswith("session id:")), None)
    blocks, cur = [], None
    for l in lines:
        if l in ("user", "codex", "exec", "thinking"):
            cur = [l, []]; blocks.append(cur); continue
        if l == "tokens used":
            break
        if cur is not None:
            cur[1].append(l)
    msgs = []
    for kind, body in blocks:
        text = "\n".join(body).strip("\n")
        if kind == "user":
            msgs.append(("orchestrator", "reviewer", "review_request", text))
        elif kind == "codex":
            msgs.append(("reviewer", "orchestrator", "status_report", text))
        elif kind == "exec":
            cmd = body[0] if body else ""
            cmd = re.sub(r" in /\S+$", "", cmd)
            msgs.append(("reviewer", "shell", "tool_call", cmd))
    # the final codex block is the result
    for i in range(len(msgs) - 1, -1, -1):
        if msgs[i][2] == "status_report":
            msgs[i] = msgs[i][:2] + ("result",) + msgs[i][3:]
            break
    return sid, msgs


def git_time(path):
    out = subprocess.run(["git", "-C", REPO, "log", "--diff-filter=A", "--format=%aI", "--", path],
                         capture_output=True, text=True).stdout.split()
    return out[-1] if out else "9999"


MANIFEST = os.path.join(HERE, "glyph_own_dev_inputs.json")


def _sha(path):
    import hashlib
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def load_manifest():
    man = json.load(open(MANIFEST, encoding="utf-8"))
    for group in ("transcripts", "forum_bodies", "review_files", "handle_sources"):
        for item in man[group]:
            full = item["path"] if item["path"].startswith("/") else os.path.join(REPO, item["path"])
            if not os.path.exists(full) or _sha(full) != item["sha256"]:
                raise SystemExit(f"pinned input missing or changed: {item['path']}")
    return man


def main():
    man = load_manifest()
    TRANSCRIPTS[:] = [(t["path"], t["label"]) for t in man["transcripts"]]
    FORUM[:] = [f["path"] for f in man["forum_bodies"]]
    convs, seen_sid = [], set()
    for path, label in TRANSCRIPTS:
        if not os.path.exists(path):
            continue
        sid, msgs = parse_transcript(path)
        if sid in seen_sid or not msgs:
            continue
        seen_sid.add(sid)
        if label.startswith("codex_synthetic"):
            msgs = [m for m in msgs if m[2] not in ("result", "status_report")]  # drop generated data
        convs.append((os.path.getmtime(path), "codex_transcript", label, msgs))
    for p in FORUM:
        convs.append((os.path.getmtime(p), "forum_request_body", "forum_" + os.path.basename(p)[:-3],
                      [("orchestrator", "forum_agents", "broadcast_request", open(p, encoding="utf-8").read())]))
    reviews = [os.path.join(REPO, r["path"]) for r in man["review_files"]]  # pinned order
    for i, p in enumerate(reviews):
        rel = os.path.relpath(p, REPO)
        body = open(p, encoding="utf-8").read()
        convs.append((None, "repo_review_file", rel, [("reviewer", "orchestrator", "review_result", body)]))
    # chronological: transcripts/forum by mtime first is not comparable to git times; keep source groups
    # in a fixed order (forum, reviews by git add time, transcripts by mtime), which is chronological per group.
    order = ([c for c in convs if c[1] == "forum_request_body"] + [c for c in convs if c[1] == "repo_review_file"]
             + sorted([c for c in convs if c[1] == "codex_transcript"], key=lambda c: c[0]))
    rows = []
    for ci, (_, stype, label, msgs) in enumerate(order, 1):
        for s, r, k, text in msgs:
            text = sanitise(text)
            if text.strip():
                scan(text); scan(sanitise(label))
    n_msg = 0
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        for ci, (_, stype, label, msgs) in enumerate(order, 1):
            seq = 0
            for s, r, k, text in msgs:
                text = sanitise(text)
                if not text.strip():
                    continue
                seq += 1; n_msg += 1
                f.write(json.dumps({"conv_id": f"gown-c{ci:03d}", "seq": seq, "sender_role": s, "receiver_role": r,
                                    "kind": k, "text": text, "synthetic": False, "dev_only": True,
                                    "sanitised": True, "source_type": stype, "source_ref": sanitise(label),
                                    "provenance": "Glyph-own traffic, single operator, sanitised, DEV ONLY"},
                                   ensure_ascii=False) + "\n")
    print(n_msg, "messages", len(order), "conversations")


if __name__ == "__main__":
    main()
