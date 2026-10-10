import hashlib, json, os, subprocess, tarfile, glob, time
os.chdir("/workspace/glyph-exp")
files = sorted(glob.glob("lenses/*.pt") + glob.glob("results/v2/*.pt") + glob.glob("results/v3/*.pt") + glob.glob("results/v4/*.pt"))
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
commit = subprocess.check_output(["git", "-C", "/workspace/glyph-repo", "rev-parse", "HEAD"]).decode().strip()
rev = {m: open(os.path.expanduser(f"~/.cache/huggingface/hub/models--{m.replace('/', '--')}/refs/main")).read().strip()
       for m in ["Qwen/Qwen2.5-0.5B", "HuggingFaceTB/SmolLM2-360M", "EleutherAI/pythia-410m"]}
man = {"repo": "devamped1337/glyph-alphabet-experiments", "git_commit": commit, "created": time.strftime("%Y-%m-%d %H:%M %Z"),
       "hf_models": {m: {"revision": r, "dtype": "float32 (torch, CPU)"} for m, r in rev.items()},
       "seeds": {"v2": "numpy default_rng(0) negotiation/CV folds, (1) injection controls", "v3": "default_rng(0) split, (3) controls",
                 "v4": "default_rng(0) message generation/splits, (7) controls, (0) bootstrap; random.Random(mid) for bag order"},
       "lens_note": "J-lenses (lenses/*.pt) fitted in v1 for Qwen and SmolLM2 only; pythia used raw mid-layer states (no lens) in v4",
       "files": {p: {"sha256": sha(p), "bytes": os.path.getsize(p)} for p in files}}
json.dump(man, open("/tmp/MANIFEST.json", "w"), indent=1)
with tarfile.open("/workspace/glyph-artifacts-v4.tar.gz", "w:gz") as t:
    for p in files: t.add(p, arcname=f"glyph-artifacts-v4/{p}")
    t.add("/tmp/MANIFEST.json", arcname="glyph-artifacts-v4/MANIFEST.json")
print(os.path.getsize("/workspace/glyph-artifacts-v4.tar.gz") / 1e6, "MB", commit)
