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
    (r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-.]+", "<SECRET>"),
    (r"[\w.+-]+@[\w-]+(\.[\w-]+)+", "<EMAIL>"),
    (r"\b(https?|ssh|git)://[^\s)\]>\"'`]+", "<URL>"),
    (r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", "<UUID>"),
    (r"\b[a-z]{1,3}_[0-9A-HJKMNP-TV-Z]{26}\b", "<ID>"),
    (r"\bsha256:[0-9a-f]{8,64}\b", "<HASH>"),
    (r"\b(?=[0-9a-f]*[a-f])(?=[0-9a-f]*[0-9])[0-9a-f]{7,64}\b", "<HASH>"),
    (r"(?<![\w.])(/(home|workspace|tmp|cursor|root|usr|etc|var|opt|mnt)(/[^\s:\"'`)\],]*)?)", "<PATH>"),
    (r"\b\d{6,}\b", "<NUM>"),
    (r"\bdevamped1337\b", "<ORG>"),
    (r"\bglyph-alphabet-experiments\b", "<REPO>"),
    (r"\bStefan( Markovich)?\b", "<OPERATOR>"),
    (r"\bMarkovich\b", "<OPERATOR>"),
]


def sanitise(t):
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


def main():
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
    reviews = sorted(glob.glob(os.path.join(REPO, "v6", "*", "reviews", "*.md")),
                     key=lambda p: (git_time(p), p))
    for i, p in enumerate(reviews):
        rel = os.path.relpath(p, REPO)
        body = open(p, encoding="utf-8").read()
        convs.append((None, "repo_review_file", rel, [("reviewer", "orchestrator", "review_result", body)]))
    # chronological: transcripts/forum by mtime first is not comparable to git times; keep source groups
    # in a fixed order (forum, reviews by git add time, transcripts by mtime), which is chronological per group.
    order = ([c for c in convs if c[1] == "forum_request_body"] + [c for c in convs if c[1] == "repo_review_file"]
             + sorted([c for c in convs if c[1] == "codex_transcript"], key=lambda c: c[0]))
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
