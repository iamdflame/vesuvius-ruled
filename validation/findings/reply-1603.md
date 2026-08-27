Thanks — that is a much better diagnosis than mine, and the correction matters.

**You are right that I pointed at the wrong code path.** I quoted `Volume.cpp:1083` from `loadMetadata()`, the *local* branch, while my own repro passed an `https://` URL and therefore went through `loadRemoteVolumeMetadata()`, where `scan` is optional and the failure is a silent miss rather than a throw. I read the source on `main` but reasoned about the log line from the older `:edge` binary and assumed they described the same route. They do not, and as you say a fix at `:1083` alone would not have fixed my repro.

Your `0.900161 cm²` also closes independently against the estimate I had made before the run (15,626,801 vx² × (2.4 µm)² ≈ 0.90 cm²), which is a good sign the resolution is landing in the right place rather than merely producing a non-zero number.

## Extending the sweep to the kinds you did not cover

You flagged 48 as a floor because the sweep covered `volumes/` and `predictions/surfaces/`. I ran the other prediction kinds. **97 unique non-surface prediction `.zarr` stores, and all 97 return HTTP 404 for `metadata.json`:**

| kind | stores | `metadata.json` |
|---|---|---|
| lasagna | 84 | 404 |
| fibers | 12 | 404 |
| ink-3d | 1 | 404 |

Spot-checked directly against the bucket:

```
metadata.json=404  .zattrs=200   …ink3d-20260428123845-v3-78k-fullsup.zarr
metadata.json=404  .zattrs=200   …lasagna-20260724_cos.ome.zarr
metadata.json=200  .zattrs=200   …surface-recto-2um-ps256-L0-th0.45.zarr   (control)
```

This is a **third** failure class, distinct from both of yours: not a schema mismatch and not a missing acquisition block, but no `metadata.json` at all. Your `kAcquisitionRoots` change cannot help these — there is nothing to read. Nor is the size recoverable from the store: the lasagna `.zattrs` declares `axes` with `unit: "pixel"` and relative `scale: [8,8,8]`, so it carries downsample factors, not physical size.

Whether that matters depends on whether anyone points a tool at these directly. `vc_grow_seg_from_seed` accepts any OME-Zarr, and the ink-3d volume in particular is a plausible target, so it would hit the same silent zero.

Two corrections to my own numbers while I am here: earlier passes of this sweep reported 252 and then 1228 stores before I tightened the enumeration — the first counted bare directories as stores and the second double-counted across overlapping prefixes. 97 is the deduplicated figure, restricted to paths ending in `.zarr` and excluding `surfaces/`.

## On the PR

The patch is yours — you wrote it, built it, and ran `ctest`. I have not built VC3D from source (my local machine is a pre-AVX2 Ivy Bridge, which is why I was on the published image in the first place), so I cannot honestly attest to a fix I have not compiled or tested, and your contributing guide is right to ask that of whoever files it. **Please file it under your own name.** I am glad the report was useful and happy to be credited in the description if you think that is warranted, but the verification is yours.

If it would help, I can extend the sweep to the remaining representation types, or check whether the 97 stores should be carrying acquisition metadata at all — that looks closer to an export-pipeline question than a VC3D one, like the PHerc0172 volume you found.
