# Validating `ruled` against a real segmenter

Every number in the top-level README uses a simplified geometric baseline and
candidate shells built from released meshes. That is the standing gap: nobody
has shown this improves a **real** tracer. This directory is the recipe for
closing it, and it has to be run by a human — the Vesuvius Challenge
[contribution rules](https://github.com/ScrollPrize/villa/blob/main/CONTRIBUTING.md)
require that improvements come from a person actually using the tools on real
scroll data, and explicitly exclude synthetic examples.

## What you need

- Docker (image is ~2.8 GB compressed, ~6.1 GB extracted)
- ~15 GB free disk for image + chunk cache
- An X server if you want the GUI (`vc_grow_seg_from_seed` is CLI-only and does not need it)
- **No GPU required** — but you must set `"use_cuda": false`, because it defaults to `true`

## 1. Get VC3D

```bash
docker system prune -a          # optional; reclaims stale images
docker pull ghcr.io/scrollprize/villa/volume-cartographer:edge
```

## 2. Run the tracer on real data

```bash
mkdir -p ~/vc-work/out ~/vc-work/cache
cp validation/params.json ~/vc-work/

docker run --rm -it \
  -v ~/vc-work:/work \
  ghcr.io/scrollprize/villa/volume-cartographer:edge \
  vc_grow_seg_from_seed --help
```

Confirm the options match before going further:

```
--volume,-v      OME-Zarr volume path
--target-dir,-t  Target directory for output
--params,-p      JSON parameters file
--seed,-s        Seed coordinates (x y z)
--resume         Path to a tifxyz surface to resume from
```

Then trace from a seed. The tracer optimizes a surface against a **surface
prediction** volume, not the raw CT — for PHerc. 1667 the released prediction is
under `PHerc1667/representations/predictions/lasagna/`.

```bash
docker run --rm -it -v ~/vc-work:/work \
  ghcr.io/scrollprize/villa/volume-cartographer:edge \
  vc_grow_seg_from_seed \
    -v <path-or-url to the prediction .ome.zarr> \
    -t /work/out \
    -p /work/params.json \
    -s <x> <y> <z>
```

Output is a `tifxyz` surface in `/work/out`.

## 3. Score it

```bash
python -c "
from ruled import load_tifxyz, load_render, score, phase_track, slip_scan
# render the traced surface, then:
r = score(img); t = phase_track(img, r['period']); print(slip_scan(t))
"
```

A traced patch that jumped a wrap should show a phase step well above the
0.715 rad ceiling measured across 777 points on hand-verified wraps.

## 4. What makes this count

Capture, for the same seed and settings:

- the traced surface **before** any correction, and where `ruled` flags it
- whether the flag corresponds to a genuine wrap jump on inspection
- terminal output and the rendered images

That is the before/after evidence their PR template asks for, and it is the
difference between "interesting result" and a contribution they can act on.

## Where to get unstuck

The tracing docs are explicitly "a starting point" and point to the Vesuvius
Challenge Discord. Seed selection in particular is undocumented — ask there
rather than guessing.
