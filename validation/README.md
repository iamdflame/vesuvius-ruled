# Validating `ruled` against a real segmenter

Every number in the top-level README uses a simplified geometric baseline and
candidate shells built from released meshes. That is the standing gap: nobody
has shown this improves a **real** tracer. This directory is the recipe for
closing it, and it has to be run by a human — the Vesuvius Challenge
[contribution rules](https://github.com/ScrollPrize/villa/blob/main/CONTRIBUTING.md)
require that improvements come from a person actually using the tools on real
scroll data, and explicitly exclude synthetic examples.

## Running it in a Codespace (free, no card)

The prebuilt VC3D binary needs AVX2+FMA, so any CPU older than 2013 dies with
SIGILL (exit 132). GitHub Codespaces runs on modern Azure hardware and the free
tier covers this comfortably.

```bash
gh auth refresh -h github.com -s codespace          # one-time, opens a browser
gh codespace create -R iamdflame/vesuvius-ruled -m standardLinux32gb
gh codespace ssh -- 'docker pull ghcr.io/scrollprize/villa/volume-cartographer:edge'
gh codespace ssh -- 'bash -s' < validation/provision-remote.sh
```

The devcontainer brings up Docker-in-Docker, Python 3.12 and the `ruled`
dependencies, and prints the CPU flags on first boot so you can confirm AVX2
before doing anything else.

Stop it when idle — `gh codespace stop` — since billing is by the core-hour.

## What you need (if renting instead)

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

### Which volume, and which seed

The tracer optimizes against a **surface prediction**, not raw CT. Use
**PHerc. Paris 4** — it is the only scroll whose released prediction has full
levels 0–5, and its meshes are cut against the same volume id, which is what
makes the seed coordinates verifiable:

```
PHercParis4/representations/predictions/surfaces/
  20260411134726-surface-20260413141734-surface-recto-2um-ps256-L0-th0.45.zarr
```

Level 0 is `[75784, 32693, 32693]` (z, y, x), uint8, blosc/zstd, 256³ chunks.

**Seed coordinates map 1:1 onto this volume from any Paris 4 `tifxyz` cut on
`20260411134726` — no scaling.** Verified empirically: sampling the prediction
at mesh points returns 255/255. The seeds in `seeds-PHercParis4.txt` were each
confirmed to land on a predicted surface, spread across the scroll's z extent:

```
  14396  17831  13988        19711  15487  46397
  15790  13590  23578        16443  17924  56609
  19629  13363  34803        17984  18699  66346
```

```bash
docker run --rm -it -v ~/vc-work:/work \
  ghcr.io/scrollprize/villa/volume-cartographer:edge \
  vc_grow_seg_from_seed \
    -v https://vesuvius-challenge-open-data.s3.amazonaws.com/PHercParis4/representations/predictions/surfaces/20260411134726-surface-20260413141734-surface-recto-2um-ps256-L0-th0.45.zarr \
    -t /work/out \
    -p /work/params.json \
    -s 17963 14015 27830
```

Or just `./validation/run.sh` (optionally `run.sh X Y Z` for a different seed).

`vc_grow_seg_from_seed.cpp:36` accepts `http://`, `https://` and `s3://`; the
`s3://bucket/key` form is rewritten to an https endpoint by `RemoteUrl.cpp`.
The volume is ~81 TB at level 0 so it cannot be downloaded — pass the remote
location and let VC3D's Zarr object cache stream it.

Output is a `tifxyz` surface in `/work/out`, which `ruled.load_tifxyz()` reads
directly.

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
