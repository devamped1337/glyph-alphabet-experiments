"""Small synthetic fixtures only. No real or private messages are used."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from e1e import make_entry  # noqa: E402

V1 = [
    make_entry("ack", 1, "ACK: task received, starting now."),
    make_entry("status", 1, "status: job {job} is {state} after {n} steps",
               [("job", "word"), ("state", "word"), ("n", "int")]),
    make_entry("handoff", 1, "Handoff to {agent}:\r\n{note}\r\n-- end",
               [("agent", "word"), ("note", "text")]),
    make_entry("json-tool", 1, '{{"tool":"{name}","args":{{"q":"{q}"}}}}',
               [("name", "word"), ("q", "text")]),
    make_entry("uni-nfc", 1, "caf\u00e9 note: {t}", [("t", "text")]),
    make_entry("uni-nfd", 1, "cafe\u0301 note: {t}", [("t", "text")]),
]
# v2 delta: revise one entry, add one.
V2_DELTA = [
    make_entry("ack", 2, "ACK: task received.\nStarting now."),
    make_entry("pair", 1, "pair {a} and {b}", [("a", "text"), ("b", "text")]),
]
V3_DELTA = [make_entry("lf", 1, "line one\nline {k}\n", [("k", "int")])]

ROUND_TRIPS = [
    b"ACK: task received.\nStarting now.",
    b"status: job build-7 is done after 42 steps",
    b"status: job x is failed after -3 steps",
    b"Handoff to reviewer:\r\nplease check\nthe \"diff\" \\ carefully\r\n-- end",
    '{"tool":"search","args":{"q":"na\u00efve \u65e5\u672c \U0001F600 \\"quoted\\""}}'.encode("utf-8"),
    "caf\u00e9 note: NFC body".encode("utf-8"),
    "cafe\u0301 note: NFD body".encode("utf-8"),
    "line one\nline 9\n".encode("utf-8"),
    b"\xef\xbb\xbfBOM-prefixed plain text\r\n",
    b"\x00\x01 control bytes \x7f",
    b"\xff\xfe not utf-8",
    b"",
]
