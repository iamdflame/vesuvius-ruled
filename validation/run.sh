#!/usr/bin/env bash
# One traced patch on PHerc. Paris 4, from a verified seed.
set -euo pipefail

VOL="https://vesuvius-challenge-open-data.s3.amazonaws.com/PHercParis4/representations/predictions/surfaces/20260411134726-surface-20260413141734-surface-recto-2um-ps256-L0-th0.45.zarr"
SEED="${1:-17963} ${2:-14015} ${3:-27830}"

mkdir -p ~/vc-work/out ~/vc-work/cache
cp -n "$(dirname "$0")/params.json" ~/vc-work/ 2>/dev/null || true

docker run --rm -it -v ~/vc-work:/work \
  ghcr.io/scrollprize/villa/volume-cartographer:edge \
  vc_grow_seg_from_seed \
    -v "$VOL" \
    -t /work/out \
    -p /work/params.json \
    -s $SEED
