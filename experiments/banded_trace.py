"""Re-derive the measured tracer result with BANDED phase.
Each patch is now (column, 3-period vertical band): its own 3D centroid, its
own surface normal, its own radius, its own line phase. Strictly more localized
than the column-centroid version used before."""
import numpy as np, tifffile, glob, os, re, sys
from PIL import Image
from scipy.spatial import cKDTree
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

def build(spec):
    scroll,inkpat,meshpat,vox,per,cmin=spec
    pts=[];wid=[];pha=[];nrm=[];cnf=[]
    wraps=sorted(set(re.search(r'(w\d+)',os.path.basename(f)).group(1)
                     for f in glob.glob(inkpat)))
    for wi,w in enumerate(wraps):
        ink=[f for f in glob.glob(inkpat) if re.search(r'(w\d+)',os.path.basename(f)).group(1)==w]
        mx=meshpat.format(w=w)
        try:
            a=np.asarray(Image.open(ink[0]),dtype=np.float32)
            X=tifffile.imread(mx+'x.tif');Y=tifffile.imread(mx+'y.tif');Z=tifffile.imread(mx+'z.tif')
        except Exception: continue
        m=(a>4.0).astype(np.float32); H,W=a.shape
        ratio=W/X.shape[1]; vrat=H/X.shape[0]
        P=np.stack([X,Y,Z],-1)
        nn=np.cross(np.gradient(P,axis=1),np.gradient(P,axis=0))
        ln=np.linalg.norm(nn,axis=-1,keepdims=True); nn=np.where(ln>1e-9,nn/np.maximum(ln,1e-9),0.)
        M=(X>0)&(Y>0)&(Z>0)
        bh=int(per*3); win=int(per*2.2); step=max(40,int(per//3))
        bands=list(range(0,max(1,H-bh+1),bh))
        cache={}
        for y0 in bands:
            for x0 in range(0,max(1,W-win),step):
                ph,c=band_phase(a,m,x0,x0+win,y0,min(H,y0+bh),per)
                if not np.isnan(ph) and c>=cmin: cache[(y0,x0+win//2)]=(ph,c)
        if not cache: continue
        keys=np.array(sorted(cache))
        for y0 in bands:
            vy0=int(y0/vrat); vy1=int(min(H,y0+bh)/vrat)
            if vy1-vy0<3: continue
            kk=keys[keys[:,0]==y0]
            if not len(kk): continue
            kx=kk[:,1]
            for u in range(X.shape[1]):
                mm=M[vy0:vy1,u]
                if mm.sum()<(vy1-vy0)*0.3: continue
                xi=u*ratio; j=int(np.argmin(np.abs(kx-xi)))
                if abs(kx[j]-xi)>win*0.75: continue
                ph,c=cache[(y0,int(kx[j]))]
                nv=nn[vy0:vy1,u][mm].mean(0); l=np.linalg.norm(nv)
                if l<1e-9: continue
                pts.append([X[vy0:vy1,u][mm].mean(),Y[vy0:vy1,u][mm].mean(),Z[vy0:vy1,u][mm].mean()])
                wid.append(wi); pha.append(ph); cnf.append(c); nrm.append(nv/l)
    return (np.array(pts,float),np.array(wid),np.array(pha),
            np.array(nrm),np.array(cnf),vox,scroll)

def evaluate(B,Lmm=0.71):
    pts,wid,pha,nrm,cnf,vox,name=B
    if len(pts)<500: print(f"{name}: only {len(pts)} patches"); return
    cx,cy=pts[:,0].mean(),pts[:,1].mean()
    rad=np.hypot(pts[:,0]-cx,pts[:,1]-cy)
    tree=cKDTree(pts)
    near=np.full(len(pts),np.inf)
    for i in np.unique(wid):
        a_=np.where(wid==i)[0]; b_=np.where(wid!=i)[0]
        if len(a_) and len(b_): near[a_]=cKDTree(pts[b_]).query(pts[a_])[0]
    near_mm=near*vox
    L=Lmm/vox; tol=L/4.5
    rec=[]
    for i in range(len(pts)):
        idx=np.array(tree.query_ball_point(pts[i],L+tol))
        if not len(idx): continue
        d=np.linalg.norm(pts[idx]-pts[i],axis=1)
        k=(np.abs(d-L)<tol)&(idx!=i); idx=idx[k]; d=d[k]
        if len(idx)<2 or len(np.unique(wid[idx]))<2: continue
        base=np.abs(d-L)*vox + 0.3*(1-np.abs(nrm[idx]@nrm[i])) + 1.0*np.abs(rad[idx]-rad[i])*vox
        ph=0.15*np.abs((pha[idx]-pha[i]+np.pi)%(2*np.pi)-np.pi)
        rec.append((near_mm[i], wid[idx[int(np.argmin(base))]]==wid[i],
                                wid[idx[int(np.argmin(base+ph))]]==wid[i]))
    R=np.array(rec,float)
    g=100*R[:,1].mean(); p=100*R[:,2].mean()
    cut=100*(1-(100-p)/max(100-g,1e-9))
    print(f"\n{name}: {len(pts)} banded patches, {len(R)} decisions spanning >1 sheet")
    print(f"  {'separation':>16} {'n':>6} {'geom':>8} {'+phase':>8} {'err cut':>8}")
    for a_,b_ in [(0,0.15),(0.15,0.30),(0.30,0.50),(0.50,0.80),(0.80,99)]:
        mm=(R[:,0]>=a_)&(R[:,0]<b_)
        if mm.sum()<40: continue
        gg=100*R[mm,1].mean(); pp=100*R[mm,2].mean()
        lab=f"{a_:.2f}-{b_:.2f}mm" if b_<99 else f">{a_:.2f}mm"
        print(f"  {lab:>16} {int(mm.sum()):6d} {gg:7.1f}% {pp:7.1f}% {100*(1-(100-pp)/max(100-gg,1e-9)):7.0f}%")
    print(f"  {'ALL':>16} {len(R):6d} {g:7.1f}% {p:7.1f}% {cut:7.0f}%")
    return g,p,cut,len(R)

r1=evaluate(build(('PHerc1667','data/ink/w*.jpg','data/mesh/{w}_',7.91e-3,355,0.30)))
r2=evaluate(build(('PHerc0139','data/gen/PHerc0139_w*_ink.jpg','data/gen/PHerc0139_{w}_',9.362e-3,266,0.30)))
print("\n\n========= BANDED vs FULL-HEIGHT (previously published) =========")
print(f"{'scroll':>12} {'old geom':>9} {'old +ph':>8} {'old cut':>8} | {'new geom':>9} {'new +ph':>8} {'new cut':>8}")
if r1: print(f"{'PHerc1667':>12} {83.3:8.1f}% {96.9:7.1f}% {82:7.0f}% | {r1[0]:8.1f}% {r1[1]:7.1f}% {r1[2]:7.0f}%")
if r2: print(f"{'PHerc0139':>12} {31.8:8.1f}% {62.0:7.1f}% {44:7.0f}% | {r2[0]:8.1f}% {r2[1]:7.1f}% {r2[2]:7.0f}%")
