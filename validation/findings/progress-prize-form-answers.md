# Progress Prize — form answers (paste-ready)

Form: https://docs.google.com/forms/d/e/1FAIpQLSev2vJobu521iB6OuyehDktzYTEo131F4iUGwt3Qxa9a1fk6A/viewform
Deadline: 31 Aug 2026, 11:59pm Pacific

---

## Email *

```
uniquedsdave@gmail.com
```

---

## Your full name *

```
<<< FILL IN — I don't know your legal name. GitHub is `iamdflame`,
    git config says `Highneighbour`. Use the name you want on the payment. >>>
```

---

## Team description *

```
Individual submission. No team.

Work was done with an AI coding agent (Claude); all results were run
against the public open-data bucket and are reproducible from the repo.
```

> *Note: disclosing the AI assistance is optional but I'd recommend it — the
> maintainer who replied on villa#1603 signed their own comment "Claude (AI
> agent) on behalf of @Bullo27", so it is normal in this project, and it costs
> nothing to be straightforward about it.*

---

## URL to your open source / publicly available contribution *

```
https://github.com/iamdflame/vesuvius-ruled
https://github.com/ScrollPrize/villa/issues/1603
```

---

## Short description of how your contributions substantially increase the probability of reading complete scrolls *

```
Two contributions, both aimed at the step that currently gates complete
scrolls: segmentation you can trust without a human checking every patch.

1. A silent data-loss bug in vc_grow_seg_from_seed (villa#1603).

Tracing against a released surface prediction — what the tool is built for —
runs to completion and then throws the result away. Voxel size cannot be
resolved from prediction metadata.json, so area_cm2 computes as 0 and the
default min_area_cm discards every surface after the full trace, with no error.
The user sees a successful-looking run and an empty directory.

Found by running the tool on real data (PHerc. Paris 4, seed 17963 14015 27830,
99 generations, 15.6M vx^2, meta.json recording area_vx2 15627277 / area_cm2
0.0). A maintainer reproduced it from source on main, confirmed it as "a real
silent data-loss bug", measured 48 of 108 volume and surface artifacts affected
across three metadata schemas, and built and tested a fix (voxelsize 0 -> 2.4,
area 0.0 -> 0.900161 cm^2, discard -> save, ctest 154/154). I then swept the
prediction kinds not covered and found a third failure class: 97 non-surface
prediction stores (84 lasagna, 12 fibers, 1 ink-3d) return 404 for
metadata.json entirely, so no voxel size is recoverable from them at all.

Anyone tracing against released predictions was losing every trace silently.
That is a direct, measured blocker on scaling segmentation.

2. ruled — an independent, training-free signal for sheet identity.

The challenge's stated hardest problem is false-positive stitches that connect
separate sheets. Every current method judges this geometrically, and geometry
goes blind exactly where the scrolls are hardest: where wraps are compressed
into contact, X-ray contrast between adjacent sheets disappears. But the ink
was applied before the scroll was rolled and crushed, so two touching wraps are
geometrically identical and textually unrelated. The scribe's line ruling is
periodic, and its local phase is a per-sheet signature — smooth along a sheet,
independent between wraps. Nothing in the pipeline uses it.

Measured on released data: adding line phase to a strong geometric tracer cuts
sheet-identity errors 72% on PHerc. 1667 (77.2% -> 93.6%, n=5,957) and 44% on
PHerc. 0139 (30.3% -> 60.8%, n=4,433). Each figure was selected on the other
scroll, so neither is a selection artifact, and across 12 parameter
configurations the spread is ~7 points. Geometry in that comparison gets every
cue a real tracer uses, including radial consistency, which alone lifts it from
42.3% to 83.2%.

The gain concentrates precisely where the pipeline is stuck. Binned by measured
distance to the nearest other sheet on PHerc. 1667: where sheets are in physical
contact (0.00-0.15 mm; minimum separations measured down to 0.04 mm, against
papyrus 0.1-0.3 mm thick) geometry falls to 38.7%, near chance, and phase holds
85.5%. Where sheets are well separated, geometry is already at 99.7% and phase
changes nothing and does no harm.

Why this matters for complete scrolls: segmentation currently costs $1-5M per
scroll because humans verify everything, against a stated target under $5k.
Verification is the cost gate, not generation. This channel is independent of
geometry, so where the two agree confidence compounds and where they disagree
you get a short review queue instead of checking every patch by hand. That is
what turns full-scroll coverage from a budget problem into a throughput one.

The library also ships a training-free text-presence score that recovers all
three already-read scrolls unsupervised from 48 released segments with no
labels, and a pre-flight check (median localized phase confidence) that predicts
in seconds whether the method will work on a given scroll. It reads tifxyz and
OME-Zarr directly and was verified against production vc_grow_seg_from_seed
output.

Limits, stated plainly and documented in the repo with measurements: this sits
downstream of ink detection and cannot replace it — raw surface texture carries
no line grid (ink ACF +0.513 vs raw -0.049 at the known text period). The line
grid amplifies existing ink signal and cannot create it (prior benefit
correlates +0.849 with existing grid strength; below ACF 0.128 it is actively
harmful). It must be gated onto geometry — applied everywhere it makes a good
tracer worse. And it cannot run on PHerc. 0172 at all. The repo documents each
of these, along with the four routes I tested that did not work.
```

---

## Terms and Conditions *

```
Yes, I agree
```

*(The repo is already MIT-licensed and public, so the open-source condition is
already satisfied.)*
