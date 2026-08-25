"""Fetch the public data the experiments need (~350 MB).

Everything comes from the open Vesuvius Challenge bucket
(s3://vesuvius-challenge-open-data, CC BY-NC 4.0). No credentials required.

    python fetch_data.py            # ink maps + meshes for PHerc1667 / 0139 / 0172
    python fetch_data.py --paris4   # adds PHercParis4 merged segments (~190 MB)
"""
import os, re, sys, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor

B = "https://vesuvius-challenge-open-data.s3.amazonaws.com"

def ls(prefix, delim=True, mk=1000):
    q = {"list-type": "2", "max-keys": str(mk), "prefix": prefix}
    if delim: q["delimiter"] = "/"
    return urllib.request.urlopen(B + "/?" + urllib.parse.urlencode(q)).read().decode()

def segments(scroll):
    return re.findall(r"<Prefix>([^<]+/)</Prefix>", ls(f"{scroll}/segments/"))

def get(job):
    out, key = job
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if os.path.exists(out) and os.path.getsize(out) > 500: return
    try:
        urllib.request.urlretrieve(B + "/" + urllib.parse.quote(key), out)
    except Exception as e:
        print(f"  failed {os.path.basename(out)}: {e}")

def collect(scroll, meshres, outdir, limit=14):
    jobs = []
    for s in sorted(x for x in segments(scroll) if re.search(r"-w0?\d\d", x))[:limit]:
        w = re.search(r"-(w0?\d+)", s).group(1)
        try:
            mesh = re.findall(r"<Key>([^<]*" + re.escape(meshres) + r"\.tifxyz/[xyz]\.tif)</Key>",
                              ls(s + "mesh/", delim=False, mk=300))
            ink = re.findall(r"<Key>([^<]*ds8\.jpg)</Key>",
                             ls(s + "ink-detection/downsampled/", delim=False, mk=30))
        except Exception:
            continue
        if len(mesh) < 3 or not ink: continue
        for k in mesh: jobs.append((f"{outdir}/{w}_{k[-5]}.tif", k))
        jobs.append((f"{outdir}/{w}_ink.jpg", sorted(ink, key=len)[0]))
    return jobs

if __name__ == "__main__":
    jobs = []
    jobs += collect("PHerc1667", "7.91um", "data/PHerc1667")
    jobs += collect("PHerc0139", "9.362um", "data/PHerc0139")
    jobs += collect("PHerc0172", "7.91um", "data/PHerc0172")
    if "--paris4" in sys.argv:
        segs = [s for s in segments("PHercParis4") if re.search(r"w\d+-\d+", s)]
        for s in sorted(segs)[:8]:
            tag = s.rstrip("/").split("/")[-1]
            ink = re.findall(r"<Key>([^<]*ds8\.jpg)</Key>",
                             ls(s + "ink-detection/downsampled/", delim=False, mk=30))
            if ink: jobs.append((f"data/PHercParis4/{tag}_ink.jpg", sorted(ink, key=len)[0]))
    print(f"fetching {len(jobs)} files into ./data")
    with ThreadPoolExecutor(8) as ex:
        for i, _ in enumerate(ex.map(get, jobs)):
            if i % 20 == 0: print(f"  {i}/{len(jobs)}", flush=True)
    print("done")
