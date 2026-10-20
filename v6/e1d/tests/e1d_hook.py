"""Test-only hook (E1B_ALLOW_NO_GPU=1 + E1D_TEST_HOOK): reuses the E1c fake backend (sender picks the true
candidate, one F1 entry picks a neighbour, one F2 entry gets a wrong verifier spec)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "e1c" / "tests"))
import e1c_hook as H
def install(C1, B, a):
    import os; os.environ.setdefault("E1C_TEST_MODE", "ok"); H.install(C1, B, a)
