# ruled

**An independent, text-derived signal for tracking papyrus sheets in Herculaneum scrolls.**

Current sheet-tracing methods use geometry. Geometry goes blind exactly where the
scrolls are hardest — in compressed regions where wraps touch, X-ray contrast between
adjacent sheets is gone. But the ink was applied *before* the scroll was rolled and
crushed, so two touching wraps are geometrically identical and **textually unrelated**.
This measures that.

The scribe's line ruling is a periodic signal. Its local *phase* is a per-sheet
signature: smooth along a sheet, independent between wraps. Nothing else in the
pipeline uses it.

### Headline result

Adding line phase to a geometric tracer cuts sheet-identity errors:

| scroll | n decisions | geometry | + line phase | error cut |
|---|---|---|---|---|
| PHerc. 1667 | 5,957 | 77.2% | **93.6%** | **72%** |
| PHerc. 0139 | 4,433 | 30.3% | **60.8%** | **44%** |

Each figure is **held out** — the configuration was selected on the *other* scroll.
Across 12 parameter configurations the spread is ~7 points, so there is nothing to
cherry-pick. All numbers come from released data on the public bucket; nothing is
simulated except where explicitly labelled.

The gain concentrates where the challenge is stuck. Binned by measured distance to
the nearest other sheet (PHerc. 1667):

| separation | geometry | + phase |
|---|---|---|
| **0.00–0.15 mm (in contact)** | 38.7% | **85.5%** |
| 0.15–0.30 mm | 77.9% | 98.2% |
| > 0.80 mm (well separated) | 99.7% | 100.0% |

Where sheets are well separated it changes nothing and does no harm. Where they touch —
measured separations down to **0.04 mm**, against papyrus 0.1–0.3 mm thick — geometry
falls toward chance and phase more than doubles it.

### Install & run

```bash
pip install numpy scipy pillow tifffile
python fetch_data.py          # ~160 MB from the public bucket, no credentials
python cli.py data/PHerc1667/*_ink.jpg
```

```python
from ruled import score, phase_track, choose_continuation, combine_with_geometry

score(img)                       # is there ruled text here?  -> period, ACF, z
t = phase_track(img, period)     # where the line grid sits, along the winding
choose_continuation(p, cands)    # which candidate patch continues this one
combine_with_geometry(...)       # gated: consult text only where geometry is unsure
```

### Reproduce

`experiments/` holds the scripts behind every number above. They expect data laid out
by `fetch_data.py`; paths at the top of each script may need adjusting for your layout.
`jointsweep.py` produces the headline held-out result.

---

## Why

The challenge's 2026 open problems state: *"When ink fails to appear, we do
not always know which part of the pipeline is limiting us."* There is also no
automated way to score a segmentation — every tool needs a human to look at
the output and judge. `score()` is a cheap, calibrated answer to the first
question and a starting point for the second.

Significance comes from a **within-image row-shuffle null**: permuting the
profile's rows preserves its value distribution exactly and destroys only
periodicity, so `z` is not calibrated against any external assumption.

## Validation (PHerc. 1667, Paris 4, 0139, 0172, 0500P2, 0343P, 0814)

Scored 48 released segments across 6 scrolls. It recovers the three
already-read scrolls **unsupervised** — no labels, no transcriptions:

| scroll | status | z range | period |
|---|---|---|---|
| PHerc. Paris 4 | read (Title prize) | 108 – 221 | 335 px |
| PHerc. 0139 | read (*On Gods* VIII) | 30 – 55 | 269 px |
| PHerc. 0172 | read (*On Vices*) | 7 – 41 | 168 px |
| PHerc. 0500P2 | — | −0.6 – 30 | scattered |
| PHerc. 0343P | — | −0.8 – 29 | scattered |
| PHerc. 0814 | — | −16 – 10 | none |

It also discriminates *within* a scroll (0500P2 runs z=30 down to −0.6
segment by segment), which is what makes it useful for triage.

**Not a tiling artifact.** Ink maps come from tiled inference
(`tile256-stride128`). The renders exist at two source resolutions on grids
differing by exactly 1.062×, so real text predicts a period ratio of 1.062
and a fixed tiling artifact predicts 1.000. Measured median: **1.079** —
1.6% from the text hypothesis, ~4σ from the artifact one.

## Line phase

Phase is smooth inside a correct segmentation and independent between wraps:

- 777 scan points across 11 correct wraps of PHerc. 1667: phase step never
  exceeded **0.715 rad** (median 0.072). Phase wanders up to 250° per segment
  but *smoothly* — that is papyrus warp.
- Cross-wrap phase at matched scroll heights: **R = 0.31** across 8 wraps,
  where 8 random phases give R ≈ 0.35. So a wrap jump does displace phase.

`slip_scan` uses this to flag candidate sheet switches. On injected switches
it caught 10 of 12 where line signal is strong (8/8 above 89°), but
whole-scroll yield is only ~20% at a zero-false-positive threshold. **It is
signal-limited. Treat it as a hint, not a verdict.**

## Stitch validation — the main result

Their hardest stated open problem is stitching: *"false positive stitches that
incorrectly connect separate sheets remain a significant challenge."*

Posed as **detection** ("is there a switch here?") this signal yields only ~20%
at a zero-false-positive threshold. Posed as **selection** ("which candidate
continues this patch?") the same signal reaches **94%** — because selection
needs no threshold and no null.

Measured on 10 wraps of PHerc. 1667:

| comparison | accuracy | n |
|---|---|---|
| correct continuation vs **a sheet switch** | **94.0%** | 745 |
| correct vs same sheet, distant window | 77–82% | 753 |
| 3-way forced choice (chance 33%) | 72–76% | 727 |

Median phase discontinuity: **0.285 rad** correct, **0.686** same-sheet-wrong-place,
**1.856** cross-sheet. It beats the same-sheet control, so it encodes position on
the sheet rather than mere image identity. Multi-band matching raises 2-way
accuracy to ~95% at reduced coverage (n falls from 577 to 41 — that is a
coverage tradeoff, not a free gain).

```python
from ruled import phase_track, choose_continuation
best, ranked = choose_continuation(phase_of_patch, {"cand_a": pa, "cand_b": pb})
```

**Why this matters for cost.** Segmentation runs $1–5M per scroll because humans
verify everything; the target is <$5k. This channel is *independent of geometry*,
so where the two agree confidence is high and where they disagree you get a short
review queue. That is the difference between checking everything and checking a
fraction.

## Measured end to end on released data

The released `tifxyz` meshes give real 3D coordinates per surface point, so the
geometric cost, candidate set, and ambiguity gate are all **measured**, not
modelled. Geometry gets every cue a real tracer uses: step length, surface
normals, and radial consistency (which is powerful on its own — it lifts
geometry from 42.3% to 83.2%; normals add nothing, since adjacent wraps are
parallel).

3,896 real tracing decisions, 10 released wraps of PHerc. 1667:

| distance to nearest other sheet | n | geometry | + phase | error cut |
|---|---|---|---|---|
| **0.00–0.15 mm (in contact)** | 62 | 38.7% | **85.5%** | 76% |
| 0.15–0.30 mm | 711 | 77.9% | 98.2% | 92% |
| 0.30–0.50 mm | 1224 | 75.7% | 95.1% | 80% |
| 0.50–0.80 mm | 1610 | 90.2% | 97.6% | 76% |
| > 0.80 mm | 289 | 99.7% | 100.0% | — |
| **all** | **3896** | **83.3%** | **96.9%** | **82%** |

**The single number is not robust — report the range.** Re-deriving this after
fixing the band-height bug showed the result moves with configuration:

| configuration (PHerc. 1667) | geometry | + phase | error cut |
|---|---|---|---|
| column patches, 350 px phase window | 83.3% | 96.9% | 82% |
| column patches, 781 px window, 5-period band | 76.1% | 94.5% | 77% |
| column patches, 781 px window, full height | 76.6% | 94.1% | 75% |
| column×band patches (finer granularity) | 68.8% | 85.9% | 55% |

Patch granularity moves *both* channels (geometry falls 83.3%→68.8% too), so the
finer version is a harder problem, not a corrected measurement. Band height,
with geometry held fixed, is mild: 67/77/75/75% for 3/5/8/full periods — a
shallow optimum near **5 line periods**.

**Settled by a held-out sweep.** Fixing the problem definition (geometry and
candidate lists precomputed once, so only the phase channel varies) and sweeping
12 configurations:

- PHerc. 1667: error cut **66–73%** across all 12
- PHerc. 0139: error cut **42–48%** across all 12

The grid is flat — ~7 points of spread — so there is no configuration to
cherry-pick. Selecting on one scroll and reporting on the other:

| selected on | config | reported on (held out) | geometry | + phase | error cut |
|---|---|---|---|---|---|
| PHerc. 1667 | 1.2× period, band 8 | PHerc. 0139 | 30.3% | 60.8% | **44%** |
| PHerc. 0139 | 2.2× period, band 5 | PHerc. 1667 | 77.2% | 93.6% | **72%** |

**Headline: 72% (PHerc. 1667, n=5957) and 44% (PHerc. 0139, n=4433), held-out.**

The earlier "55–82%" was not parameter sensitivity — parameters move it by 7
points, not 27. That spread came from mixing *different problem definitions*
(column×band granularity is a harder task for both channels; the 82% used a
separate pipeline with different matching tolerances). Reproduce: `jointsweep.py`.

The outer wraps of this scroll are physically touching — minimum separations of
**0.04 mm** between w037/w040 and w038/w040, against papyrus 0.1–0.3 mm thick.
Geometry collapses to near chance there. Phase is a property of the writing, so
compression does not touch it; where sheets are well separated it changes
nothing and does no harm.

Caveats: candidate sets come from a distance shell, not a production segmenter's
proposals; n=62 in the tightest bin carries wide error bars; ten wraps of one
scroll, and PHerc. 1667 has unusually clean ink maps; radius is measured from an
estimated scroll centre, which is well behaved here and may not be on a badly
deformed roll.

Reproduce: `geom.py` (mesh geometry) then `final_real.py`.

### Generalization — three scrolls

Identical pipeline, everything derived per scroll (period, ink/mesh scale ratio,
voxel size), nothing tuned. Run with `generalize.py`.

| scroll | segments | phase confidence | n | geometry | + phase | error cut |
|---|---|---|---|---|---|---|
| PHerc. 1667 | large, clean ink | ~0.44 | 3896 | 83.3% | 96.9% | **82%** |
| PHerc. 0139 | large, tightly packed | 0.33–0.64 | 4504 | 31.8% | 62.0% | **44%** |
| PHerc. 0172 | small | 0.07–0.19 | — | — | — | **cannot run** |

**PHerc. 0139** replicates the pattern at lower absolute levels — it is a much
more compressed scroll (median nearest-other-sheet 0.277 mm vs 1667's 0.666 mm),
so geometry sits at 24.7% in the close bin, essentially chance, and phase more
than doubles it to 52.4%.

**PHerc. 0172 cannot run**, and not for lack of text — scroll-level periodicity
scores z=8.6–42.6. It fails on *area*: wrap segments 1213–2048 px wide against
1667's ~4200 leave too little to average over, so localized phase confidence is
0.07–0.19 against a 0.25 gate and only 1 of 14 wraps is usable.

**Why PHerc. 0172 fails — three hypotheses tested, all rejected:**

1. *Too little area.* If so, confidence would rise with window width. On 0139 it
   does (0.526 → 0.664, monotone, 2.2×–12× period). On 0172 it **falls**
   (0.125 → 0.085). Rejected.
2. *Inconsistent line period.* Per-segment periods spanned 145–410 (42% spread).
   Re-scoring in a band that cannot hold a 2× harmonic collapsed it to **5.5%**,
   comparable to 1667 (2.1%) and 0139 (5.9%). **That 42% was my detector picking
   harmonics, not their flattening.** Rejected.
3. *Wrong period fed to the tracker.* Per-segment periods moved median confidence
   0.144 → 0.148. Rejected.

What survives: 0172's line signal is real per-segment but **does not survive
localization**. Per-segment ACF 0.330 vs 0.415 / 0.456 — weaker, but not enough
to explain localized confidence of 0.148 vs 0.488. No parameter choice recovers it.

**Use a 3-period vertical band, not the full segment height.** Computing one
phase estimate over the whole height smears it: small tilt in the ruling
accumulates across many periods. Restricting to ~3 periods vertically:

| scroll | full height | 3-period band | change |
|---|---|---|---|
| PHerc. 1667 | 0.508 | 0.544 | +7% |
| PHerc. 0139 | 0.528 | 0.555 | +5% |
| PHerc. 0172 | 0.131 | 0.242 | +85% |
| PHerc. Paris 4 | 0.263 | **0.495** | unlocked |

The gain scales with segment height (Paris 4's merges are 29 periods tall), so
it matters most on the large merged segments the field is moving toward.

**Audit of PHerc. Paris 4 (negative result).** Eight released merged segments,
each spanning 4–7 wraps across 22–25k px: 9,368 measurements, median phase step
**0.109 rad**, no detectable defects. Confidence falls as step size rises
(0.562 → 0.32), high-confidence large steps are 2 of 9,368, and no flag repeats
across bands at the same x. Their merges are clean by this measure — which also
demonstrates **specificity**: the same detector fires on injected wrap jumps and
stays quiet on good segmentation.

**Pre-flight check.** Median localized phase confidence predicts usability and
costs seconds:

| scroll | median phase confidence | outcome |
|---|---|---|
| PHerc. 1667 | ~0.44 | works — 82% error cut |
| PHerc. 0139 | 0.488 | works — 44% error cut |
| PHerc. 0172 | 0.148 | cannot run |

Roughly **0.3** separates them. Check before pointing the machinery at a scroll.

Untested: 0172's large merged segments (6150–7663 px) do produce usable phase
tracks, but carry no wrap labels, so there is no ground truth to score against.

**Envelope:**
- Needs **localized** line coherence, which is stricter than "the scroll has
  detectable text". Whole-segment periodicity can be unmistakable while the
  localized estimate is unusable.
- Helps most where there is headroom. On a very tightly packed scroll it roughly
  doubles accuracy from near chance but does not alone reach production quality.
- **The relative gain transfers; the absolute levels do not.** The geometric
  baseline here is deliberately simple, so a real segmenter starts higher.

## Combining with geometry — gating is mandatory

`combine_with_geometry()` adds the text channel to a geometric tracer. It must
be **gated**: consulted only where geometry is ambiguous.

Applied at every step, it makes a good geometric tracer *worse* — it adds a
noisy vote where geometry was already right. Applied only in ambiguous steps
it helped in every condition tested. Simulating geometry that fails in a
fraction `p` of steps (compressed regions), over 10 wraps of PHerc. 1667:

| ambiguity gate (recall / fpr) | drift-error reduction |
|---|---|
| 1.0 / 0.0 (oracle) | 73 – 77% |
| **0.8 / 0.1 (realistic)** | **56 – 59%** |
| 0.6 / 0.2 | 28 – 35% |
| 0.3 / 0.3 | ~0 (can go slightly negative) |

Retention at p=0.30, 3 candidates: geometry alone 71.1%, gated 87.7% with a
realistic gate. **Gate quality is the leverage** — a better compressed-region
detector multiplies the benefit directly, and compressed regions are already
what the challenge identifies as the hard case.

Caveat stated plainly: geometry here is *simulated* as "prefers one candidate
with strength G, wrong a fraction p of the time." That is a model, not a
measurement of any real segmenter. The 94% forced-choice number is measured;
these combination figures inherit the model's assumptions.

## Scope limit (measured, not assumed)

**This needs ink predictions. It cannot run on raw surface volumes.**

Tested on PHerc. 1667 w030, same pixel region, level-3 surface volume vs the
ink map. At the known text period (362 px):

| | ACF at 362 | ACF at 724 (2×) |
|---|---|---|
| ink map | **+0.513** | +0.391 |
| raw surface | −0.049 | −0.074 |
| raw surface, high-passed | −0.141 | −0.052 |

Cross-correlation of the two profiles: −0.035 at lag 0, and scanning ±1 period
gives a symmetric ±0.25 envelope — what uncorrelated signals look like. The
raw surface *does* have significant periodicity (z up to 25) but at 240–260
and ~410 px, which is fiber/strip structure, not writing.

So the ink signal is present in the CT but requires a nonlinear learned
detector to surface it; a row-mean statistic will not do it. This method sits
**downstream** of ink detection.

## Install

```
pip install numpy scipy pillow
python cli.py path/to/*.jpg
```

Data: `s3://vesuvius-challenge-open-data/` (public, CC BY-NC 4.0),
`{scroll}/segments/{seg}/ink-detection/downsampled/*-ds8.jpg`
