"""Readers for the formats the Vesuvius community actually uses, so `ruled`
can be pointed at released data directly instead of requiring a preprocessing
step: tifxyz quadmeshes, OME-Zarr / Zarr arrays, and flat image renders.

    from ruled import load_render, load_tifxyz, load_zarr_slice
"""
import json, os, glob
import numpy as np


def load_render(path):
    """A flattened surface render (ink prediction or texture) as float32 + mask.

    Returns (image, mask). Mask is True where the segment has data; background
    in these renders is exactly 0, so a small threshold separates it cleanly.
    """
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    a = np.asarray(Image.open(path).convert("L"), dtype=np.float32)
    return a, a > 4.0


def load_tifxyz(path):
    """A tifxyz quadmesh directory (x.tif, y.tif, z.tif [, meta.json]).

    Returns dict with:
      xyz    (H, W, 3) float32 volume coordinates, NaN where the mesh has no data
      mask   (H, W) bool
      normal (H, W, 3) float32 unit surface normals from the mesh grid
      meta   parsed meta.json if present, else {}

    Coordinates are in voxel units of the volume the mesh was cut against; the
    voxel size is usually in the directory name (e.g. '...-7.91um.tifxyz').
    """
    import tifffile
    path = path.rstrip("/")
    x = tifffile.imread(os.path.join(path, "x.tif")).astype(np.float32)
    y = tifffile.imread(os.path.join(path, "y.tif")).astype(np.float32)
    z = tifffile.imread(os.path.join(path, "z.tif")).astype(np.float32)
    mask = (x > 0) & (y > 0) & (z > 0)
    xyz = np.stack([x, y, z], -1)
    xyz[~mask] = np.nan
    du = np.gradient(np.nan_to_num(xyz), axis=1)
    dv = np.gradient(np.nan_to_num(xyz), axis=0)
    n = np.cross(du, dv)
    ln = np.linalg.norm(n, axis=-1, keepdims=True)
    normal = np.where(ln > 1e-9, n / np.maximum(ln, 1e-9), 0.0).astype(np.float32)
    meta = {}
    mp = os.path.join(path, "meta.json")
    if os.path.exists(mp):
        try: meta = json.load(open(mp))
        except Exception: pass
    return dict(xyz=xyz, mask=mask, normal=normal, meta=meta)


def voxel_size_mm(name):
    """Pull the voxel size out of a tifxyz/volume name, e.g. '-7.91um.tifxyz'."""
    import re
    m = re.search(r"([\d.]+)um", str(name))
    return float(m.group(1)) * 1e-3 if m else None


def load_zarr_slice(store, level, z, y0, y1, x0, x1):
    """One depth slice of a surface-volume Zarr, as float32 + mask.

    `store` is a local path or an https URL to the .zarr root. Remote stores are
    read with HTTP range requests over raw chunks (see ruled.surface.read_slice),
    which avoids pulling whole chunks for a single slice.
    """
    if str(store).startswith("http"):
        from .surface import read_slice
        a, ok, tot, nz = read_slice(str(store).rstrip("/"), level, z, y0, y1, x0, x1)
        a = a.astype(np.float32)
        return a, a > 0
    import zarr
    arr = zarr.open(os.path.join(str(store), str(level)), mode="r")
    a = np.asarray(arr[z, y0:y1, x0:x1], dtype=np.float32)
    return a, a > 0


def find_segments(root, pattern="*"):
    """Locate segment directories under a scroll tree, returning for each the
    render and tifxyz paths that `ruled` can consume."""
    out = []
    for seg in sorted(glob.glob(os.path.join(root, pattern))):
        if not os.path.isdir(seg): continue
        inks = sorted(glob.glob(os.path.join(seg, "ink-detection", "downsampled", "*.jpg")))
        meshes = sorted(glob.glob(os.path.join(seg, "mesh", "*.tifxyz")))
        if inks or meshes:
            out.append(dict(segment=os.path.basename(seg),
                            render=inks[0] if inks else None,
                            tifxyz=meshes[0] if meshes else None))
    return out
