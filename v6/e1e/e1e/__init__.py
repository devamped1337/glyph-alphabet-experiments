"""E1E-REPO/1 fixture-tested mechanics draft (no corpus measurement or savings claim)."""
from .canon import E1EError, canonical, parse_canonical, sha256_hex
from .schema import make_entry, validate_entry, parse_template, render, match_template
from .repo import RepoState, Publisher, Receiver, load_full, apply_delta, make_delta, FORMAT
from .codec import encode, decode_message, transmit, Link
