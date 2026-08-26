**In one sentence:** `vc_grow_seg_from_seed` traces a surface successfully against a released *surface prediction* volume and then silently discards it, because prediction `metadata.json` nests the scan metadata one level deeper than volume `metadata.json`, so voxel size resolves to 0 and the `min_area_cm` check drops every result.

**I was trying to:** Trace a patch on PHerc. Paris 4 from a seed, to check whether text-line phase can flag a tracer wandering onto a neighbouring sheet in a compressed region.

**Using:** `ghcr.io/scrollprize/villa/volume-cartographer:edge` (meta reports `vc_gsfs_version: "dev"`), 4-core x86_64, real data from the public bucket.

```bash
docker run --rm -v ~/vc-work:/work \
  ghcr.io/scrollprize/villa/volume-cartographer:edge \
  vc_grow_seg_from_seed \
    -v https://vesuvius-challenge-open-data.s3.amazonaws.com/PHercParis4/representations/predictions/surfaces/20260411134726-surface-20260413141734-surface-recto-2um-ps256-L0-th0.45.zarr \
    -t /work/out -p /work/params.json -s 17963 14015 27830
```

**What happened:** The trace ran to completion — 99 generations, seed correctly read as 255 — then produced no output and no error explaining why. The output directory stayed empty.

```
[WARN ] Failed to load remote volume metadata for '...th0.45.zarr':
        metadata.json missing 'scan' key
...
seed location [17963, 14015, 27830] value is 255
gen 99 processing 788 fringe cands (total done 38412 fringe: 780)
generated surface 15627277.310839 vx^2 (0.000000 cm^2)
```

Every `area` readout is `0.00 mm^2` and the final area is `0.000000 cm^2`, despite 15.6M vx². With the default `min_area_cm: 0.3` the surface is dropped at the area check after all the tracing work is done.

**What I expected or needed:** Either the surface is written, or the tool says why it was not. Losing a completed trace to a silent area check is expensive — the user sees a successful-looking run and an empty directory.

**Evidence / reproduction:** Setting `min_area_cm: -1` in the params makes the identical run save correctly:

```
generated surface 15627277.310839 vx^2 (0.000000 cm^2)
saving "/work/out/auto_grown_20260825232050529"
```

The saved `meta.json` records the inconsistency directly:

```json
"area_vx2": 15627277.310839027,
"area_cm2": 0.0
```

The result is a valid 202×202 tifxyz, 39,204 valid points (96.1%), spanning x 16041–19985, y 12107–16020, z 26218–29506.

- [x] I personally encountered and reproduced this using the version and data stated above.

## Details

The two metadata schemas differ. `Volume.cpp:1083` requires a top-level `scan`:

```cpp
auto full = vc::json::load_json_file(altPath);
if (!full.contains("scan")) {
    throw std::runtime_error("metadata.json missing 'scan' key: " + altPath.string());
}
metadata_ = full;
metadata_.update(full["scan"]);
```

But for released prediction volumes the same information is present one level down:

| | path to `samplePixelSize` | value |
|---|---|---|
| `volumes/…-2.400um-….zarr/metadata.json` | `scan.tomo.acquisition.detector.samplePixelSize` | 0.0024 |
| `representations/predictions/surfaces/….zarr/metadata.json` | `source.metadata.scan.tomo.acquisition.detector.samplePixelSize` | **0.0024** |

Prediction metadata top-level keys are `generated_at, kind, model, output, post_processing, schema_version, source, workflow` — no `scan`, but `source.metadata.scan` is the complete scan block.

A fallback to `source.metadata.scan` when top-level `scan` is absent would fix this, and `Volume.cpp:99` already uses a similar multi-key search pattern (`{"scan", "volume", "properties", "metadata"}`) elsewhere.

Two smaller things noticed alongside:

1. The `voxelsize` params override documented in `main` (`vc_grow_seg_from_seed.cpp:330-333, 367-371`) has no effect in the `:edge` image — that binary's startup header prints `mode / step size / min_area_cm / tgt_overlap_count` with no `voxelsize:` line, so it predates that code. Not a bug in `main`, but it means the natural workaround does not work with the published image.
2. It may be worth logging the area check when it discards, e.g. `discarding generated surface because area_cm2 0 < min_area_cm 0.3`, since the current run looks like a success.

I have not built VC3D from source, so I have not compile-tested a patch — this is a diagnosis with a proposed fix rather than a verified one.
