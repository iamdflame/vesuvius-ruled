#!/usr/bin/env bash
# Run a trace on the rented box and bring the result home.
#   ./validation/trace-remote.sh vc 17963 14015 27830
set -euo pipefail
HOST="${1:-vc}"; X="${2:-17963}"; Y="${3:-14015}"; Z="${4:-27830}"
VOL="https://vesuvius-challenge-open-data.s3.amazonaws.com/PHercParis4/representations/predictions/surfaces/20260411134726-surface-20260413141734-surface-recto-2um-ps256-L0-th0.45.zarr"

echo "== tracing from seed $X $Y $Z on $HOST =="
ssh "$HOST" "docker run --rm -v /root/vc-work:/work \
  ghcr.io/scrollprize/villa/volume-cartographer:edge \
  vc_grow_seg_from_seed -v '$VOL' -t /work/out -p /work/params.json -s $X $Y $Z" \
  2>&1 | tee "trace-$X-$Y-$Z.log"

echo "== fetching result =="
mkdir -p "results/$X-$Y-$Z"
rsync -az --info=progress2 "$HOST:/root/vc-work/out/" "results/$X-$Y-$Z/" || true
find "results/$X-$Y-$Z" -maxdepth 2 -type f | head -20
