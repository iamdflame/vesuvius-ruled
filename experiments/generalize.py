"""Replicate the measured tracer experiment on a second and third scroll.
Everything is derived per-scroll: line period, ink/mesh scale ratio, voxel size."""
import numpy as np, glob, os, re, sys, tifffile
from PIL import Image
from scipy.spatial import cKDTree
from scipy.ndimage import gaussian_filter1d
sys.path.insert(0,'ruled')
from ruled import score
Image.MAX_IMAGE_PIXELS=None

def phase_track(a,m,per,win,step,min_cov=0.55):
    H,W=a.shape; out=[]
    for x0 in range(0,W-win,step):
        A=a[:,x0:x0+win]; M=m[:,x0:x0+win]
        cov=M.mean(axis=1); n=M.sum(axis=1)
        p=np.where(n>0,(A*M).sum(axis=1)/np.maximum(n,1),0.)
        good=cov>=min_cov
        if good.sum()<3.0*per: continue
        idx=np.where(good)[0]
        run=max(np.split(idx,np.where(np.diff(idx)>1)[0]+1),key=len)
        if len(run)<3.0*per: continue
        y=np.arange(run[0],run[-1]+1); s=p[y]
        d=s-gaussian_filter1d(s,per*1.2); d-=d.mean()
        w=np.hanning(len(d)); z=np.sum(d*w*np.exp(-2j*np.pi*y/per))
        c=np.abs(z)/(np.sum(np.abs(d)*w)+1e-9)
        out.append((x0+win/2., float(np.angle(z)), float(c)))
    return np.array(out) if out else np.zeros((0,3))

def run_scroll(scroll, vox_mm, cmin=0.25):
    wraps=sorted({re.search(r'_(w\d+)_',f).group(1)
                  for f in glob.glob(f'data/gen/{scroll}_*_ink.jpg')})
    pers=[]
    for w in wraps:
        r=score(np.asarray(Image.open(f'data/gen/{scroll}_{w}_ink.jpg'),dtype=np.float32))
        if r and r['z']>6: pers.append(r['period'])
    if not pers: print(f"{scroll}: no periodicity"); return None
    PER=float(np.median(pers))
    print(f"\n===== {scroll} =====")
    print(f"wraps={len(wraps)}  line period={PER:.0f}px (median of {len(pers)} scoring z>6)")
    pts=[];wid=[];pha=[];nrm=[]
    for wi,w in enumerate(wraps):
        try:
            a=np.asarray(Image.open(f'data/gen/{scroll}_{w}_ink.jpg'),dtype=np.float32)
            X=tifffile.imread(f'data/gen/{scroll}_{w}_x.tif');Y=tifffile.imread(f'data/gen/{scroll}_{w}_y.tif');Z=tifffile.imread(f'data/gen/{scroll}_{w}_z.tif')
        except Exception: continue
        m=a>4.0
        ratio=a.shape[1]/X.shape[1]
        t=phase_track(a,m.astype(np.float32),PER,int(PER*2.2),max(20,int(PER//6)))
        t=t[(~np.isnan(t[:,1]))&(t[:,2]>=cmin)]
        if len(t)<6: continue
        tx=t[:,0]
        P=np.stack([X,Y,Z],-1)
        n3=np.cross(np.gradient(P,axis=1),np.gradient(P,axis=0))
        ln=np.linalg.norm(n3,axis=-1,keepdims=True); n3=np.where(ln>1e-9,n3/np.maximum(ln,1e-9),0.)
        M=(X>0)&(Y>0)&(Z>0)
        for u in range(X.shape[1]):
            mm=M[:,u]
            if mm.sum()<X.shape[0]*0.25: continue
            xi=u*ratio; j=int(np.argmin(np.abs(tx-xi)))
            if abs(tx[j]-xi)>PER*1.2: continue
            nv=n3[:,u][mm].mean(0); l=np.linalg.norm(nv)
            if l<1e-9: continue
            pts.append([X[mm,u].mean(),Y[mm,u].mean(),Z[mm,u].mean()])
            wid.append(wi); pha.append(t[j,1]); nrm.append(nv/l)
    if len(pts)<300: print(f"  only {len(pts)} usable points"); return None
    pts=np.array(pts,float);wid=np.array(wid);pha=np.array(pha);nrm=np.array(nrm)
    cx,cy=pts[:,0].mean(),pts[:,1].mean()
    rad=np.hypot(pts[:,0]-cx,pts[:,1]-cy)
    tree=cKDTree(pts)
    near=np.full(len(pts),np.inf)
    for i in np.unique(wid):
        a_=np.where(wid==i)[0]; b_=np.where(wid!=i)[0]
        if len(a_) and len(b_): near[a_]=cKDTree(pts[b_]).query(pts[a_])[0]
    near_mm=near*vox_mm
    print(f"  {len(pts)} points, {len(np.unique(wid))} wraps; nearest-other-sheet median={np.median(near_mm):.3f}mm")
    L=90.0*(7.91/ (vox_mm*1000)); tol=L/4.5
    recs=[]
    for i in range(len(pts)):
        idx=np.array(tree.query_ball_point(pts[i],L+tol))
        if not len(idx): continue
        d=np.linalg.norm(pts[idx]-pts[i],axis=1)
        k=(np.abs(d-L)<tol)&(idx!=i); idx=idx[k]; d=d[k]
        if len(idx)<2 or len(np.unique(wid[idx]))<2: continue
        base=np.abs(d-L)*vox_mm + 0.3*(1-np.abs(nrm[idx]@nrm[i])) + 1.0*np.abs(rad[idx]-rad[i])*vox_mm
        ph=0.15*np.abs((pha[idx]-pha[i]+np.pi)%(2*np.pi)-np.pi)
        recs.append((near_mm[i], wid[idx[int(np.argmin(base))]]==wid[i],
                                 wid[idx[int(np.argmin(base+ph))]]==wid[i]))
    if len(recs)<100: print(f"  only {len(recs)} scorable decisions"); return None
    R=np.array(recs,float)
    print(f"  {len(R)} decisions where the shell spans >1 sheet")
    print(f"  {'separation':>18} {'n':>6} {'geom':>8} {'+phase':>8} {'err cut':>8}")
    for a_,b_ in [(0,0.30),(0.30,0.60),(0.60,99)]:
        m=(R[:,0]>=a_)&(R[:,0]<b_)
        if m.sum()<30: continue
        g=100*R[m,1].mean(); p=100*R[m,2].mean()
        lab=f"{a_:.2f}-{b_:.2f}mm" if b_<99 else f">{a_:.2f}mm"
        print(f"  {lab:>18} {int(m.sum()):6d} {g:7.1f}% {p:7.1f}% {100*(1-(100-p)/max(100-g,1e-9)):7.0f}%")
    g=100*R[:,1].mean(); p=100*R[:,2].mean()
    cut=100*(1-(100-p)/max(100-g,1e-9))
    print(f"  {'ALL':>18} {len(R):6d} {g:7.1f}% {p:7.1f}% {cut:7.0f}%")
    return g,p,cut,len(R)

res={}
res['PHerc0139']=run_scroll('PHerc0139', 9.362e-3)
res['PHerc0172']=run_scroll('PHerc0172', 7.91e-3)
print("\n\n================ GENERALIZATION ================")
print(f"{'scroll':>12} {'ink quality':>12} {'n':>6} {'geometry':>9} {'+phase':>8} {'err cut':>8}")
print(f"{'PHerc1667':>12} {'clean':>12} {3896:6d} {83.3:8.1f}% {96.9:7.1f}% {82:7.0f}%")
for k,v in res.items():
    if v: print(f"{k:>12} {'moderate' if '0139' in k else 'weakest':>12} {v[3]:6d} {v[0]:8.1f}% {v[1]:7.1f}% {v[2]:7.0f}%")
