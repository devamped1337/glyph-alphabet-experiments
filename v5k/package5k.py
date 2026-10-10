"""zip results + MANIFEST.txt (sha256 of every file) -> $GLYPH_OUT/../glyph_v5k_results.zip.  usage: package5k.py [--no-states]"""
import os, sys, zipfile, hashlib, time, json
OUT = os.environ.get("GLYPH_OUT", os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")); skip = "--no-states" in sys.argv
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()
files = sorted(os.path.relpath(os.path.join(r, f), OUT) for r, _, fs in os.walk(OUT) for f in fs)
files = [f for f in files if not (skip and f.startswith("states_"))]
lines = [f"{sha(os.path.join(OUT, f))}  {os.path.getsize(os.path.join(OUT, f))}  {f}" for f in files]
man = os.path.join(OUT, "MANIFEST.txt"); open(man, "w").write(f"# glyph v5k results, {time.strftime('%Y-%m-%dT%H:%M:%S%z')}\n# sha256  bytes  path\n" + "\n".join(lines) + "\n")
z = os.path.join(os.path.dirname(OUT), "glyph_v5k_results.zip")
with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as Z:
    for f in files + ["MANIFEST.txt"]: Z.write(os.path.join(OUT, f), f)
open(z + ".sha256", "w").write(sha(z) + "  " + os.path.basename(z) + "\n"); print(z, os.path.getsize(z), "bytes,", len(files), "files; sha256", open(z + ".sha256").read())
