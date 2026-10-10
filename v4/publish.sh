#!/bin/bash
set -x
cd /workspace/glyph-exp
R=/workspace/glyph-repo
mkdir -p $R/v4 $R/results/v4 $R/logs/v4
cp v4/*.py v4/*.sh v4/book_v4.json $R/v4/
cp RESULTS_v4.md $R/ ; cp RESULTS_v4.md $R/v4/
cp results/v4/*.json $R/results/v4/
cp logs/v4/*.log $R/logs/v4/ 2>/dev/null || true
rm -f $R/results/v4/smoke_*.json
cd $R && find . -name "*.pt" -not -path "./.git/*" -delete
git add -A
if git diff --cached --quiet; then
  echo "nothing new to commit"
else
  git commit -q -m "v4: three-party repository (qwen, smol, pythia), frozen blocks, composition tests, deliveries, ablations, costs"
  git push origin main
fi
cd /workspace/glyph-exp && .venv/bin/python v4/make_artifacts.py
SZ=$(stat -c %s /workspace/glyph-artifacts-v4.tar.gz)
if [ $SZ -lt 2000000000 ]; then
  if gh release view v4-artifacts --repo devamped1337/glyph-alphabet-experiments >/dev/null 2>&1; then
    echo "release v4-artifacts already exists"
    gh release view v4-artifacts --repo devamped1337/glyph-alphabet-experiments --json url
  else
    gh release create v4-artifacts /workspace/glyph-artifacts-v4.tar.gz --repo devamped1337/glyph-alphabet-experiments --title "v4 artifacts" --notes "Fitted J-lenses (v1, used v2-v3), v2 dictionary + states, v3 book + states, v4 three-model book + states (*.pt). MANIFEST.json inside lists git commit, HF model revisions, dtype, seeds and sha256 of every file."
    gh release view v4-artifacts --repo devamped1337/glyph-alphabet-experiments --json url
  fi
else echo "tarball over 2GB, release skipped"; fi
git -C $R rev-parse HEAD
echo PUBLISHDONE
