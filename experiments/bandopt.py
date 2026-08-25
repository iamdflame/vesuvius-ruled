"""Band height trades tilt-smearing against sample size. Sweep it inside the
tracer test, holding patch geometry FIXED so only phase quality varies."""
import numpy as np, tifffile, glob, os, re
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

def run(scroll,inkpat,meshfmt,vox,per,nper,Lmm=0.71):
    """patches are always COLUMN-centroids (geometry fixed); only the phase
    attached to them changes with band height nper."""
    pts=[];wid=[];pha=[];nrm=[]
    wraps=sorted(set(re.search(r'(w\d+)',os.path.basename(f)).group(1) for f in glob.glob(inkpat)))
    for wi,w in enumerate(wraps):
        ink=[f for f in glob.glob(inkpat) if re.search(r'(w\d+)',os.path.basename(f)).group(1)==w]
        mx=meshfmt.format(w=w)
        try:
            a=np.asarray(Image.open(ink[0]),dtype=np.float32)
            X=tifffile.imread(mx+'x.tif');Y=tifffile.imread(mx+'y.tif');Z=tifffile.imread(mx+'z.tif')
        except Exception: continue
        m=(a>4.0).astype(np.float32); H,W=a.shape
        ratio=W/X.shape[1]
        P=np.stack([X,Y,Z],-1)
        nn=np.cross(np.gradient(P,axis=1),np.gradient(P,axis=0))
        ln=np.linalg.norm(nn,axis=-1,keepdims=True); nn=np.where(ln>1e-9,nn/np.maximum(ln,1e-9),0.)
        M=(X>0)&(Y>0)&(Z>0)
        bh=H if nper is None else min(H,int(per*nper))
        win=int(per*2.2); step=max(40,int(per//3))
        edges=[0] if nper is None else list(range(0,max(1,H-bh+1),max(1,bh//2)))
        cache={}
        for x0 in range(0,max(1,W-win),step):
            best=None
            for y0 in edges:
                ph,c=band_phase(a,m,x0,x0+win,y0,min(H,y0+bh),per)
                if not np.isnan(ph) and (best is None or c>best[1]): best=(ph,c)
            if best and best[1]>=0.30: cache[x0+win//2]=best[0]
        if not cache: continue
        kx=np.array(sorted(cache))
        for u in range(X.shape[1]):
            mm=M[:,u]
            if mm.sum()<X.shape[0]*0.25: continue
            xi=u*ratio; j=int(np.argmin(np.abs(kx-xi)))
            if abs(kx[j]-xi)>win*0.75: continue
            nv=nn[:,u][mm].mean(0); l=np.linalg.norm(nv)
            if l<1e-9: continue
            pts.append([X[mm,u].mean(),Y[mm,u].mean(),Z[mm,u].mean()])
            wid.append(wi); pha.append(cache[kx[j]]); nrm.append(nv/l)
    pts=np.array(pts,float);wid=np.array(wid);pha=np.array(pha);nrm=np.array(nrm)
    if len(pts)<300: return None
    cx,cy=pts[:,0].mean(),pts[:,1].mean(); rad=np.hypot(pts[:,0]-cx,pts[:,1]-cy)
    tree=cKDTree(pts); L=Lmm/vox; tol=L/4.5
    G=P_=0; n=0
    for i in range(len(pts)):
        idx=np.array(tree.query_ball_point(pts[i],L+tol))
        if not len(idx): continue
        d=np.linalg.norm(pts[idx]-pts[i],axis=1)
        k=(np.abs(d-L)<tol)&(idx!=i); idx=idx[k]; d=d[k]
        if len(idx)<2 or len(np.unique(wid[idx]))<2: continue
        base=np.abs(d-L)*vox+0.3*(1-np.abs(nrm[idx]@nrm[i]))+1.0*np.abs(rad[idx]-rad[i])*vox
        ph=0.15*np.abs((pha[idx]-pha[i]+np.pi)%(2*np.pi)-np.pi)
        G+= wid[idx[int(np.argmin(base))]]==wid[i]
        P_+=wid[idx[int(np.argmin(base+ph))]]==wid[i]
        n+=1
    return 100*G/n,100*P_/n,n,len(pts)

for scroll,inkpat,fmt,vox,per,tall in [
    ('PHerc1667','data/ink/w*.jpg','data/mesh/{w}_',7.91e-3,355,'~14 periods tall'),
    ('PHerc0139','data/gen/PHerc0139_w*_ink.jpg','data/gen/PHerc0139_{w}_',9.362e-3,266,'~13 periods tall')]:
    print(f"\n=== {scroll} ({tall}) — geometry identical across rows, only phase changes ===")
    print(f"{'band':>12} {'patches':>8} {'n':>6} {'geom':>8} {'+phase':>8} {'err cut':>8}")
    for nper,lab in [(3,'3 periods'),(5,'5 periods'),(8,'8 periods'),(None,'full height')]:
        r=run(scroll,inkpat,fmt,vox,per,nper)
        if not r: print(f"{lab:>12}  insufficient"); continue
        g,p,n,np_=r
        print(f"{lab:>12} {np_:8d} {n:6d} {g:7.1f}% {p:7.1f}% {100*(1-(100-p)/max(100-g,1e-9)):7.0f}%")
