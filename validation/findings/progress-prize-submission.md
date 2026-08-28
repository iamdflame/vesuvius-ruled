# Progress Prize submission — August 2026

Form: https://docs.google.com/forms/d/e/1FAIpQLSev2vJobu521iB6OuyehDktzYTEo131F4iUGwt3Qxa9a1fk6A/viewform
Deadline: 31 Aug 2026, 11:59pm Pacific

---

## What this contributes, in one sentence

A confirmed fix for a silent data-loss bug in `vc_grow_seg_from_seed`, plus
`ruled` — a training-free tool that scores whether a segmentation contains
readable ruled text and flags where a trace has left its sheet.

## 1. A silent data-loss bug in an actively used tool

**[ScrollPrize/villa#1603](https://github.com/ScrollPrize/villa/issues/1603)**

Tracing against a released *surface prediction* — what `vc_grow_seg_from_seed`
is designed for — runs to completion and then discards the result. Voxel size
cannot be resolved from prediction `metadata.json`, so `area_cm2` computes as 0
and the default `min_area_cm` bins every surface after the full trace. The user
sees a successful-looking run and an empty output directory.

Found by running the tool on real data: PHerc. Paris 4, seed `17963 14015 27830`
(verified to sit on a predicted surface, tracer independently read 255/255),
99 generations, 15.6M vx², output `meta.json` recording `area_vx2: 15627277,
area_cm2: 0.0`.

A maintainer reproduced it from source on `main`, confirmed it as "a real silent
data-loss bug", measured the blast radius at **48 of 108** volume/surface
artifacts across three metadata schemas, and built and tested a fix
(`voxelsize` 0 → 2.4, area 0.0 → 0.900161 cm², discard → save, `ctest` 154/154).

I then extended the sweep to the prediction kinds not covered and found a third
failure class: **97 non-surface prediction stores (84 lasagna, 12 fibers, 1
ink-3d) return HTTP 404 for `metadata.json` entirely**, so the fix cannot help
them and no physical voxel size is recoverable from the store (`.zattrs` gives
`unit: "pixel"` with relative scale only).

The diagnosis in my original report named the wrong code path — I cited the
local-load branch while my repro went through the remote one. The maintainer
corrected it; the symptom and impact stood. That exchange is in the thread.

## 2. `ruled` — training-free text-structure scoring

**https://github.com/iamdflame/vesuvius-ruled** (MIT, public)

The challenge's open problems state: *"When ink fails to appear, we do not always
know which part of the pipeline is limiting us."* There is also no automated way
to score a segmentation. `ruled` addresses both, from a channel nothing in the
pipeline currently uses: the scribe's line ruling. Its local **phase** is a
per-sheet signature — smooth along a sheet, independent between wraps — and it
is independent of the geometry every existing method relies on.

```python
score(img)                    # is there ruled text here?  -> period, ACF, z
phase_track(img, period)      # where the line grid sits along the winding
choose_continuation(p, cands) # which candidate patch continues this one
combine_with_geometry(...)    # gated: consult text only where geometry is unsure
```

**Measured on released data, held out.** Adding line phase to a geometric tracer
cuts sheet-identity errors:

| scroll | n decisions | geometry | + line phase | error cut |
|---|---|---|---|---|
| PHerc. 1667 | 5,957 | 77.2% | 93.6% | **72%** |
| PHerc. 0139 | 4,433 | 30.3% | 60.8% | **44%** |

Each figure was selected on the *other* scroll. Across 12 parameter
configurations the spread is ~7 points, so there is no configuration to
cherry-pick. Geometry is given every cue a real tracer uses (step length,
surface normals, radial consistency — radial alignment alone lifts it from
42.3% to 83.2%).

The gain lands where the challenge is stuck. Binned by measured distance to the
nearest other sheet (PHerc. 1667):

| separation | geometry | + phase |
|---|---|---|
| **0.00–0.15 mm (in contact)** | 38.7% | **85.5%** |
| 0.15–0.30 mm | 77.9% | 98.2% |
| > 0.80 mm (well separated) | 99.7% | 100.0% |

Minimum measured sheet separations reach **0.04 mm** against papyrus 0.1–0.3 mm
thick. Where sheets are well separated it changes nothing and does no harm.

**Unsupervised validation.** Scoring 48 released segments across 6 scrolls
recovers all three already-read scrolls with no labels: Paris 4 (z=108–221),
PHerc. 0139 (30–55), PHerc. 0172 (7–41). Significance comes from a within-image
row-shuffle null. Not a tiling artifact: the two render resolutions sit on grids
differing by 1.062×, and the measured period ratio is 1.079 — 1.6% from the text
hypothesis, ~4σ from the artifact one.

**A pre-flight check.** Median localized phase confidence predicts whether the
method will work on a scroll, in seconds: 1667 ~0.44 (works), 0139 0.488 (works),
0172 0.148 (cannot run). Roughly 0.3 separates them.

**Specificity.** Audited PHerc. Paris 4's eight released merged segments (4–7
wraps each, 22–25k px): 9,368 measurements, median phase step 0.109 rad, no
detectable defects. Their merges are clean — the same detector fires on injected
wrap jumps and stays quiet on good segmentation.

## 3. Format compatibility

Reads released data directly, no preprocessing step: `load_tifxyz` (quadmesh →
xyz, mask, per-vertex normals, meta), `load_zarr_slice` (OME-Zarr/Zarr, local
path or https), `load_render`, `find_segments`. Remote zarr reads use HTTP range
requests over raw chunks, so one depth slice costs ~16 KB rather than a 1.9 MB
whole chunk. CLI emits JSON for piping. Verified against production
`vc_grow_seg_from_seed` output.

## 4. Documented negatives

The repo records what did not work, with measurements:

- **Raw surface texture carries no line grid.** At the known text period, ink
  ACF +0.513 vs raw surface −0.049; no harmonic. The method sits downstream of
  ink detection and cannot replace it.
- **The line grid cannot rescue weak ink.** Prior benefit is proportional to
  existing grid strength (corr +0.849); below ACF 0.128 it is actively harmful.
  It amplifies signal, it cannot create it.
- **Ungated, it makes a good geometric tracer worse.** Gating is mandatory.
- **PHerc. 0172 cannot run**, and three of my explanations for that were wrong
  before the fourth held.

## Reproduce

```bash
git clone https://github.com/iamdflame/vesuvius-ruled && cd vesuvius-ruled
pip install numpy scipy pillow tifffile zarr
python fetch_data.py          # public bucket, no credentials
python experiments/jointsweep.py     # the headline held-out result
```

`validation/` contains the VC3D run kit: verified seeds for PHerc. Paris 4, a
params file, and a devcontainer that runs the trace in a free Codespace.
