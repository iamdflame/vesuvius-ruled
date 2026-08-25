"""Separate real discontinuities from the noise tail.
A real defect: large phase step with HIGH confidence on BOTH sides, and
neighbouring bands at the same x agreeing that something is wrong."""
import numpy as np, glob, os
from PIL import Image
from scipy.ndimage import gaussian_filter1d
Image.MAX_IMAGE_PIXELS=None
def band_phase(a,m,x0,x1,y0,y1,per,min_cov=0.55):
    A=a[y0:y1,x0:x1]; M=m[y0:y1,x0:x1]
    cov=M.mean(axis=1); n=M.sum(axis=1)
    p=np.where(n>0,(A*M).sum(axis=1)/np.maximum(n,1),0.)
    good=cov>=min_cov
    if good.sum()<2.5*per: return np.nan,0.
    idx=np.where(good)[0]
    run=max(np.split(idx,np.where(np.diff(idx)>1)[0]+1),key=len)
    if len(run)<2.5*per: return np.nan,0.
    y=np.arange(run[0],run[-1]+1)+y0
    s=p[y-y0]; d=s-gaussian_filter1d(s,per*1.2); d-=d.mean()
    w=np.hanning(len(d)); z=np.sum(d*w*np.exp(-2j*np.pi*y/per))
    return float(np.angle(z)), float(np.abs(z)/(np.sum(np.abs(d)*w)+1e-9))
def wrapf(x): return (x+np.pi)%(2*np.pi)-np.pi
PER={'20260701183127':348,'20260701183128':337,'20260701183129':336,'20260701183130':338,
     '20260701183132':336,'20260701183133':336,'20260701183134':331,'20260701183135':340}
recs=[]
for f in sorted(glob.glob('data/multi/PHercParis4__*.jpg')):
    key=os.path.basename(f).split('__')[1][:14]; per=PER.get(key)
    if not per: continue
    tag=os.path.basename(f).split('__')[1][15:24]
    a=np.asarray(Image.open(f),dtype=np.float32); m=(a>4.0).astype(np.float32)
    H,W=a.shape; bh=int(per*3); win=int(per*2.2); step=max(50,per//3)
    for y0 in range(0,max(1,H-bh+1),bh):
        xs=[];ph=[];cf=[]
        for x0 in range(0,W-win,step):
            p_,c=band_phase(a,m,x0,x0+win,y0,min(H,y0+bh),per)
            if np.isnan(p_) or c<0.30: continue
            xs.append(x0+win/2.); ph.append(p_); cf.append(c)
        if len(xs)<12: continue
        xs=np.array(xs);ph=np.array(ph);cf=np.array(cf)
        for i in range(1,len(xs)):
            if xs[i]-xs[i-1]>step*2.5: continue
            recs.append((tag,y0,xs[i],abs(wrapf(ph[i]-ph[i-1])),min(cf[i],cf[i-1])))
R=recs
st=np.array([r[3] for r in R]); cf=np.array([r[4] for r in R])
print(f"n={len(R)}  median step={np.median(st):.3f}\n")
print("does a big step mean low confidence (noise) or not?")
for lo,hi in [(0,0.2),(0.2,0.5),(0.5,1.0),(1.0,2.0),(2.0,3.2)]:
    k=(st>=lo)&(st<hi)
    if k.sum()<10: continue
    print(f"  step {lo:.1f}-{hi:.1f} rad : n={int(k.sum()):5d}  median confidence={np.median(cf[k]):.3f}")
print("\nHIGH-CONFIDENCE large steps (conf>=0.45 on both sides, step>1.5 rad):")
hot=[r for r in R if r[3]>1.5 and r[4]>=0.45]
hot.sort(key=lambda r:-r[3])
print(f"  {len(hot)} of {len(R)} ({100*len(hot)/len(R):.2f}%)")
print(f"  {'step':>6} {'conf':>6} {'segment':>10} {'x':>7} {'band y':>7}")
for r in hot[:20]: print(f"  {r[3]:6.3f} {r[4]:6.3f} {r[0]:>10} {int(r[2]):7d} {r[1]:7d}")
# clustering: do flags at the same x appear in multiple bands?
from collections import defaultdict
byseg=defaultdict(list)
for r in hot: byseg[r[0]].append((int(r[2]),r[1]))
print("\nclustering — same segment, same x (+/-700px), different bands:")
found=0
for tag,v in byseg.items():
    v.sort()
    for i,(x,y) in enumerate(v):
        near=[(x2,y2) for x2,y2 in v if abs(x2-x)<=700 and y2!=y]
        if near:
            found+=1
            print(f"  {tag} x~{x} : bands {sorted(set([y]+[b for _,b in near]))}")
            break
print(f"  {found} segments show a flag repeating across bands at the same x" if found else "  none — flags are isolated, consistent with a noise tail")
