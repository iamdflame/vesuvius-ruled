"""Range-sliced reader for Vesuvius surface-volume zarrs.
Chunks are raw uint8 (compressor: null), shape (nz,128,128) C-order, so depth
slice z of a chunk is a contiguous nz-independent block at offset z*128*128.
We fetch only those bytes -> ~120x less traffic than whole chunks."""
import numpy as np, urllib.request, json, re
from concurrent.futures import ThreadPoolExecutor
B="https://vesuvius-challenge-open-data.s3.amazonaws.com"
CS=128

def meta(prefix, level=3):
    z=json.loads(urllib.request.urlopen(f"{B}/{prefix}/{level}/.zarray").read())
    return z

def _get(args):
    url, off, ln = args
    rq=urllib.request.Request(url, headers={"Range": f"bytes={off}-{off+ln-1}"})
    try:
        with urllib.request.urlopen(rq, timeout=60) as r: return r.read()
    except Exception: return None

def read_slice(prefix, level, z, y0,y1, x0,x1, workers=24):
    za=meta(prefix,level); nz=za["shape"][0]
    assert za["compressor"] is None and za["dtype"]=="|u1"
    cy0,cy1=y0//CS,(y1-1)//CS; cx0,cx1=x0//CS,(x1-1)//CS
    out=np.zeros((( cy1-cy0+1)*CS, (cx1-cx0+1)*CS), np.uint8)
    jobs=[]; pos=[]
    for cy in range(cy0,cy1+1):
        for cx in range(cx0,cx1+1):
            jobs.append((f"{B}/{prefix}/{level}/0/{cy}/{cx}", z*CS*CS, CS*CS))
            pos.append((cy-cy0,cx-cx0))
    with ThreadPoolExecutor(workers) as ex: bufs=list(ex.map(_get,jobs))
    ok=0
    for (ry,rx),b in zip(pos,bufs):
        if b is None or len(b)!=CS*CS: continue
        out[ry*CS:(ry+1)*CS, rx*CS:(rx+1)*CS]=np.frombuffer(b,np.uint8).reshape(CS,CS); ok+=1
    sub=out[y0-cy0*CS:y0-cy0*CS+(y1-y0), x0-cx0*CS:x0-cx0*CS+(x1-x0)]
    return sub, ok, len(jobs), nz
