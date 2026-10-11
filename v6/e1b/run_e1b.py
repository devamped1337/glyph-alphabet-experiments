#!/usr/bin/env python3
"""E1b entrypoint: python v6/e1b/run_e1b.py --stage {build,A,B0,B0b,B1,B2,B3}  (PREREG_E1b.md + Amendment A1)."""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from e1b import load_cfg
from e1b.stages import STAGES
ap = argparse.ArgumentParser(); ap.add_argument("--stage", required=True, choices=list(STAGES)); ap.add_argument("--config")
a = ap.parse_args(); STAGES[a.stage](load_cfg(a.config))
