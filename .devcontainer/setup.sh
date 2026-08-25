#!/usr/bin/env bash
# Runs once when the codespace is created.
set -euo pipefail

echo "== CPU (the reason we are not doing this locally) =="
for f in avx2 fma bmi2; do
  grep -qw "$f" /proc/cpuinfo && echo "  $f: YES" || echo "  $f: MISSING"
done
grep -m1 'model name' /proc/cpuinfo | sed 's/^/  /'

echo "== python deps for ruled =="
pip install --quiet --no-warn-script-location numpy scipy pillow tifffile imagecodecs zarr numcodecs
python -c "import sys; sys.path.insert(0,'.'); import ruled; print('  ruled imports:', len(ruled.__all__), 'exports')"

echo "== workspace =="
mkdir -p ~/vc-work/out ~/vc-work/cache
cp validation/params.json ~/vc-work/ 2>/dev/null || true
df -h / | awk 'NR==2{print "  disk free: "$4}'

echo
echo "Ready. Pull VC3D with:"
echo "  docker pull ghcr.io/scrollprize/villa/volume-cartographer:edge"
