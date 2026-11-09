#!/usr/bin/env python3
"""Gated exploratory byte replay for the internal-75 synthetic cohort.

Importing this module does not compress, mine, or train. main() refuses
unless an external review ack authorises the run. The ack is not part of
this repository. This file does not change the frozen grid, coverage floor,
retirement rule, or e1e-fold-1 split.
"""
import gzip
import hashlib
import json
import os
import signal
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

DATA = os.path.join(ROOT, "data", "internal75")
MANIFEST_PATH = os.path.join(ROOT, "internal75", "MANIFEST.json")
COMBINED = "combined75_messages.jsonl"
AUTHORS = ("gpt_messages.jsonl", "grok_messages.jsonl", "claude_messages.jsonl", "glyph_messages.jsonl")
EXPECTED_COUNTS = {"gpt": 25, "grok": 25, "claude": 15, "glyph": 10}
# Transferred from the already published synthetic dev screen. Not re-selected here.
FIXED = {"L": 32, "k": 2, "C": 50, "V": 5, "participants": 2, "joiners": 0, "zstd_level": 19}
ARMS = ("1", "3", "4b", "4b-delta", "5", "6", "7")  # arm 4 omitted: selecting it would train on these messages
FLOOR = 0.20  # unchanged; a number on this cohort does not clear the earlier failures
DEADLINE_S = 60
AUDIT_DIR_REL = "measurements/internal75-audit"
SUPPORT = ("e1e/canon.py", "e1e/schema.py", "e1e/repo.py", "e1e/codec.py", "e1e/compact.py",
           "e1e/curation.py", "e1e/baselines.py")
PROTECTED = ("measurements/e1f_dev_screen_synthetic.json",
             "measurements/e1f_dev_screen_glyph_own_aggregates.json",
             "measurements/dev_inflation_synthetic.json",
             "data/synthetic_gpt_r1.jsonl")


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def manifest():
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        return json.load(f)


def author_of(conv_id):
    if conv_id.startswith("ix50-c") and conv_id[len("ix50-c"):].isdigit():
        n = int(conv_id[len("ix50-c"):])
        if 1 <= n <= 10:
            return "gpt"
        if 11 <= n <= 20:
            return "grok"
    if conv_id.startswith("claude-c") and conv_id[len("claude-c"):].isdigit() and 1 <= int(conv_id[len("claude-c"):]) <= 5:
        return "claude"
    if conv_id.startswith("glyph-c") and conv_id[len("glyph-c"):].isdigit() and 1 <= int(conv_id[len("glyph-c"):]) <= 5:
        return "glyph"
    return None


def _load_jsonl(path):
    with open(path, "rb") as handle:
        raw = handle.read()
    rows = []
    for line in raw.splitlines():
        if not line.strip():
            raise SystemExit("blank line in " + os.path.basename(path))
        rows.append(json.loads(line.decode("utf-8")))
    return raw, rows


def validate():
    """Check the frozen bytes and counts. Does not rewrite or normalise text."""
    man = manifest()
    if man.get("data_freeze") is not True or man.get("code_freeze") is not False:
        raise SystemExit("manifest must mark data frozen and code not frozen")
    raw, rows = _load_jsonl(os.path.join(DATA, COMBINED))
    got = hashlib.sha256(raw).hexdigest()
    if got != man["combined_sha256"] or len(raw) != man["combined_bytes"]:
        raise SystemExit("combined JSONL hash or size mismatch")
    if len(rows) != 75:
        raise SystemExit("combined record count is not 75")
    convs = {}
    authors = {k: 0 for k in EXPECTED_COUNTS}
    allowed = {"conv_id", "seq", "sender_role", "receiver_role", "kind", "text", "synthetic"}
    for row in rows:
        if set(row) != allowed or row["synthetic"] is not True or "ts" in row:
            raise SystemExit("unexpected field, synthetic flag, or timestamp")
        if not isinstance(row["text"], str) or row["text"] == "":
            raise SystemExit("empty or non-text body")
        if len(row["text"].encode("utf-8")) > 65536:
            raise SystemExit("message exceeds 65536 bytes; refusing rather than dropping it")
        who = author_of(row["conv_id"])
        if who is None:
            raise SystemExit("conversation id is outside the frozen 30")
        authors[who] += 1
        convs.setdefault(row["conv_id"], []).append(row["seq"])
    if authors != EXPECTED_COUNTS or len(convs) != 30:
        raise SystemExit("author or conversation count mismatch")
    for seqs in convs.values():
        if seqs != list(range(1, len(seqs) + 1)):
            raise SystemExit("sequence gap or reorder inside a conversation")
    parsed = []
    for name in AUTHORS:
        path = os.path.join(DATA, name)
        araw, arows = _load_jsonl(path)
        pin = man["author_files"][name]
        if hashlib.sha256(araw).hexdigest() != pin["sha256"] or len(araw) != pin["bytes"]:
            raise SystemExit("author file hash mismatch: " + name)
        parsed.extend(arows)
    if [(r["conv_id"], r["seq"], r["text"]) for r in rows] != [(r["conv_id"], r["seq"], r["text"]) for r in parsed]:
        raise SystemExit("combined bodies differ from the author files")
    return {"messages": 75, "conversations": 30, "authors": authors, "combined_sha256": got}


def plan():
    return {
        "question": "On this synthetic internal cohort, after repository and setup bytes, is arm 7's primary-scenario total strictly smaller than both arm 4b-delta and arm 6?",
        "generalisable_to_outside_traffic": False,
        "partition": "all_dev",
        "heldout_count": 0,
        "seed": "e1e-fold-1",
        "seed_applied_to_heldout_split": False,
        "calls_tune": False,
        "calls_select_baseline4": False,
        "calls_dev_screen": False,
        "fixed_point_transferred_from_prior_synthetic_screen": dict(FIXED),
        "arms": list(ARMS),
        "arm4": "not run; dictionary-size search would fit the same 75 messages being scored",
        "baseline2_gzip9": "included as byte-audit plan baseline 2, stdlib, mtime=0, no sync, no training",
        "coverage_floor_unchanged": FLOOR,
        "prior_negative_screens_remain_failed": True,
        "floor_on_this_cohort_cannot_clear_prior_screens": True,
        "retirement_rule_unchanged": True,
        "external_gate": "unmet",
        "zstd_pin": "zstandard==0.23.0, libzstd 1.5.6, level 19, headline frame",
        "byte_exact": "audit_strict=True raises AuditAbort, which is not an assert, before raw fallback or retransmission. Python -O cannot strip it. Arm 1 is checked through decode_message.",
        "watchdog_seconds": DEADLINE_S,
        "repeats": "no timings and no speedup claim; if a run is later authorised, a second invocation must reproduce the aggregate sha256 or the run is invalid",
        "search_space": 1,
        "gzip9": "message frames only; not an arm total and not part of the arm 7 comparison",
    }


class AuditDeadline(BaseException):
    """Interval-timer stop. A BaseException so protocol `except Exception` handlers cannot continue."""


def install_watchdog(seconds):
    if not hasattr(signal, "setitimer"):
        raise SystemExit("no interval timer; not measuring")

    def handler(signum, frame):
        raise AuditDeadline("audit exceeded %ss; no report kept" % seconds)

    signal.signal(signal.SIGALRM, handler)
    signal.setitimer(signal.ITIMER_REAL, seconds)


def clear_watchdog():
    if hasattr(signal, "setitimer"):
        signal.setitimer(signal.ITIMER_REAL, 0)


def _git_head():
    repo = os.path.abspath(os.path.join(ROOT, "..", ".."))
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def support_hashes():
    return {rel: _sha256(os.path.join(ROOT, rel)) for rel in SUPPORT}


def parse_review(text):
    found = {}
    for line in text.splitlines():
        if ": " not in line:
            continue
        key, value = line.split(": ", 1)
        if key in ("VERDICT", "SOURCE_COVERAGE", "CANDIDATE", "HARNESS") and key not in found:
            found[key] = value.strip()
    return found


def review_problems(text, head, harness):
    found = parse_review(text)
    problems = []
    if found.get("VERDICT") != "APPROVE":
        problems.append("verdict is not APPROVE")
    if found.get("SOURCE_COVERAGE") != "full":
        problems.append("source coverage is not full")
    if found.get("CANDIDATE") != head:
        problems.append("candidate commit is not bound")
    if found.get("HARNESS") != harness:
        problems.append("harness hash is not bound")
    return problems


def _load_review(path, expect):
    if not isinstance(path, str) or not os.path.isfile(path):
        return "review artifact missing", None
    with open(path, "rb") as handle:
        raw = handle.read()
    if hashlib.sha256(raw).hexdigest() != expect:
        return "review artifact hash mismatch", None
    try:
        return None, raw.decode("utf-8")
    except UnicodeError:
        return "review artifact is not utf-8", None


def ack_refusal(path, head_sha=None):
    if not path or not os.path.isfile(path):
        return "review ack missing; measurement not started"
    try:
        with open(path, encoding="utf-8") as handle:
            ack = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return "review ack is not JSON"
    man = manifest()
    if ack.get("authorize_run") is not True:
        return "review ack does not authorise the run"
    head = _git_head() if head_sha is None else head_sha
    if not head or ack.get("candidate_commit") != head:
        return "review ack is not bound to this candidate commit"
    harness = _sha256(__file__)
    if ack.get("harness_sha256") != harness or man.get("harness_sha256") != harness:
        return "review ack harness hash is not this file"
    if ack.get("combined_sha256") != man["combined_sha256"]:
        return "review ack combined hash mismatch"
    claimed = ack.get("support_sha256")
    live = support_hashes()
    if claimed != live or claimed != man.get("support_sha256"):
        return "review ack support hashes are not this tree"
    for who in ("gpt", "grok"):
        reason, text = _load_review(ack.get(who + "_review_path"), ack.get(who + "_review_sha256"))
        if reason:
            return who + " " + reason
        problems = review_problems(text, head, harness)
        if problems:
            return who + " review rejected: " + "; ".join(problems)
    return None


def prepare_output(path):
    """Refuse every destination except a new file directly inside the audit directory."""
    if not isinstance(path, str) or not path:
        raise SystemExit("output path is missing")
    allowed = os.path.realpath(os.path.join(ROOT, AUDIT_DIR_REL))
    parent = os.path.realpath(os.path.dirname(os.path.abspath(path)))
    name = os.path.basename(os.path.abspath(path))
    if parent != allowed or name in ("", ".", ".."):
        raise SystemExit("output must be a new file inside measurements/internal75-audit")
    os.makedirs(allowed, exist_ok=True)
    real = os.path.join(allowed, name)
    frozen = list(PROTECTED) + [os.path.join("data", "internal75", item) for item in (COMBINED,) + AUTHORS]
    frozen += ["tools/internal75_run.py", "internal75/MANIFEST.json", "e1e/codec.py", "e1e/compact.py", "e1e/baselines.py"]
    for rel in frozen:
        if os.path.realpath(os.path.join(ROOT, rel)) == real:
            raise SystemExit("refusing to overwrite a frozen input or result")
    if os.path.lexists(real):
        raise SystemExit("output already exists; refusing to overwrite")
    return real


_refuse_output = prepare_output


def coverage_record(arm7):
    if "covered_bytes" not in arm7 or "input_bytes" not in arm7:
        raise SystemExit("arm 7 coverage fields are missing; not defaulting them to zero")
    eligible = arm7["input_bytes"]
    if not eligible:
        return {"covered_bytes": arm7["covered_bytes"], "eligible_bytes": 0, "coverage": None,
                "coverage_defined": False, "floor": FLOOR, "prior_screens_remain_failed": True}
    return {"covered_bytes": arm7["covered_bytes"], "eligible_bytes": eligible,
            "coverage": arm7["covered_bytes"] / eligible, "coverage_defined": True,
            "floor": FLOOR, "prior_screens_remain_failed": True}


def gzip_record(message_bytes):
    return {"scope": "message_frames_only", "message_bytes": message_bytes, "sync_bytes": 0,
            "included_in_arm_totals": False, "comparable_as_arm_total": False}


def publication_evidence(chain, version_index):
    publications = []
    for rec in chain:
        publications.append({
            "sched_version": rec["sched_version"],
            "new_entries": rec["new_entries"],
            "overflow": rec["overflow"],
            "overflow_count": rec["overflow_count"],
            "overflow_bytes": rec["overflow_bytes"],
            "full_bytes": len(rec["full"]),
            "delta_bytes": 0 if rec["delta"] is None else len(rec["delta"]),
            "skipped_versions": list(rec["skipped_versions"]),
        })
    schedule = []
    for row in getattr(chain, "schedule", ()):
        schedule.append({key: row[key] for key in (
            "sched_version", "n_convs", "status", "published_index", "new_entries",
            "overflow", "overflow_count", "overflow_bytes", "picks")})
    return {"publications": publications, "schedule": schedule, "version_index_by_rank": list(version_index)}


def _require_zstd():
    import zstandard
    if getattr(zstandard, "__version__", None) != "0.23.0" or getattr(zstandard, "ZSTD_VERSION", None) != (1, 5, 6):
        raise SystemExit("zstd pin mismatch; not measuring")
    return zstandard.__version__, zstandard.ZSTD_VERSION


def run_measurement(out_path, deadline_s=DEADLINE_S):
    """One fixed replay. Reached only after ack_refusal returns None."""
    from e1e.canon import AuditAbort, E1EError
    install_watchdog(deadline_s)
    written = None
    try:
        real = prepare_output(out_path)
        zstd_version = _require_zstd()
        summary = validate()
        from e1e import baselines as B
        from e1e import curation as K

        raw, rows = _load_jsonl(os.path.join(DATA, COMBINED))
        by = {}
        for row in rows:
            by.setdefault(row["conv_id"], []).append(row)
        messages = [{"conv_id": c, "seq": r["seq"], "text": r["text"]} for c, rs in by.items() for r in rs]
        order = K.order_conversations(messages)  # synthetic all-dev order; not a held-out split
        convs = [(c, [r["text"] for r in by[c]]) for c in order]
        replay = [{"conv_id": c, "sender": r["sender_role"], "receiver": r["receiver_role"],
                   "msg": r["text"].encode("utf-8")} for c in order for r in by[c]]
        if len(replay) != 75:
            raise SystemExit("replay length changed")
        miner = K.Miner(convs, "synthetic")
        chain = K.build_repository_chain(
            miner, len(convs), FIXED["V"], FIXED["L"], FIXED["k"], FIXED["C"], FIXED["joiners"])
        sched = [K.version_for_rank(r, len(replay), FIXED["V"]) for r in range(len(replay))]

        def version_map(sched_version):
            idx = 0
            for i, rec in enumerate(chain, 1):
                if rec["sched_version"] <= sched_version:
                    idx = i
            return idx

        indexes = [version_map(item) for item in sched]
        res = B.replay_arms(
            replay, chain, lambda r: indexes[r], ARMS, level=FIXED["zstd_level"],
            b4_codec=None, audit_strict=True)
        totals = B.scenario_totals(res, chain, FIXED["participants"], [], b4_codec=None)
        gzip_bytes = 0
        for item in replay:
            frame = gzip.compress(item["msg"], 9, mtime=0)
            if gzip.decompress(frame) != item["msg"]:
                raise AuditAbort("gzip frame does not decode to the message")
            gzip_bytes += len(frame)
        coverage = coverage_record(totals["7"])
        arm7, arm6, arm4bd = totals["7"]["total"], totals["6"]["total"], totals["4b-delta"]["total"]
        report = {
            "label": "EXPLORATORY INTERNAL ALL-DEV. Not held-out evidence. Not an outside-traffic result. Does not clear the prior Stage-1 failures and does not change the retirement rule.",
            "combined_sha256": hashlib.sha256(raw).hexdigest(),
            "counts": summary,
            "plan": plan(),
            "bindings": {"candidate_commit": _git_head(), "harness_sha256": _sha256(__file__),
                         "support_sha256": support_hashes()},
            "zstd": {"version": zstd_version[0], "lib": list(zstd_version[1])},
            "conversation_order": "order_conversations without timestamps; held-out split not applied",
            "gzip9_message_frames_only": gzip_record(gzip_bytes),
            "coverage_descriptive": coverage,
            "arms": {arm: totals[arm] for arm in ARMS},
            "break_even": totals["_break_even"],
            "publication": publication_evidence(chain, indexes),
            "primary_totals": {arm: totals[arm]["total"] for arm in ARMS},
            "arm7_strictly_smaller_than_both_4b_delta_and_6": arm7 < arm4bd and arm7 < arm6,
            "claim_scope": "synthetic internal cohort only",
        }
        blob = json.dumps(report, indent=1, sort_keys=True).encode("utf-8") + b"\n"
        fd = os.open(real, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        written = real
        with os.fdopen(fd, "wb") as handle:
            handle.write(blob)
        return report
    except AuditDeadline:
        if written and os.path.lexists(written):
            os.remove(written)
        raise SystemExit("audit deadline exceeded; no report kept")
    except (AuditAbort, E1EError):
        if written and os.path.lexists(written):
            os.remove(written)
        raise SystemExit("audit aborted on a verification failure; no report kept")
    finally:
        clear_watchdog()


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] != ["--ack"] or len(argv) != 4 or argv[2] != "--out":
        raise SystemExit("usage: python3 tools/internal75_run.py --ack ACK.json --out measurements/internal75-audit/report.json")
    reason = ack_refusal(argv[1])
    if reason:
        raise SystemExit(reason)
    prepare_output(argv[3])
    run_measurement(argv[3])


if __name__ == "__main__":
    main()
