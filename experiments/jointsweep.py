"""Joint sweep over phase window width x band height, with CROSS-SCROLL
held-out selection. Geometry (the problem definition) is fixed and precomputed
once per scroll, so only the phase channel varies.

Protocol: pick the best config on scroll A, report its score on scroll B.
That number is selection-bias free. Reporting the best cell would not be."""
import numpy as np, tifffile, glob, os, re, pickle
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

def prepare(scroll,inkpat,meshfmt,vox,per,Lmm=0.71):
    """geometry + candidate lists, computed ONCE; independent of phase params"""
    ck=f'data/prep_{scroll}.pkl'
    if os.path.exists(ck): return pickle.load(open(ck,'rb'))
    pts=[];wid=[];nrm=[];meta=[]
    wraps=sorted(set(re.search(r'(w\d+)',os.path.basename(f)).group(1) for f in glob.glob(inkpat)))
    for wi,w in enumerate(wraps):
        ink=[f for f in glob.glob(inkpat) if re.search(r'(w\d+)',os.path.basename(f)).group(1)==w]
        mx=meshfmt.format(w=w)
        try:
            a=np.asarray(Image.open(ink[0]),dtype=np.float32)
            X=tifffile.imread(mx+'x.tif');Y=tifffile.imread(mx+'y.tif');Z=tifffile.imread(mx+'z.tif')
        except Exception: continue
        H,W=a.shape; ratio=W/X.shape[1]
        P=np.stack([X,Y,Z],-1)
        nn=np.cross(np.gradient(P,axis=1),np.gradient(P,axis=0))
        ln=np.linalg.norm(nn,axis=-1,keepdims=True); nn=np.where(ln>1e-9,nn/np.maximum(ln,1e-9),0.)
        M=(X>0)&(Y>0)&(Z>0)
        for u in range(X.shape[1]):
            mm=M[:,u]
            if mm.sum()<X.shape[0]*0.25: continue
            nv=nn[:,u][mm].mean(0); l=np.linalg.norm(nv)
            if l<1e-9: continue
            pts.append([X[mm,u].mean(),Y[mm,u].mean(),Z[mm,u].mean()])
            wid.append(wi); nrm.append(nv/l); meta.append((wi,w,u*ratio,ink[0],H,W))
    pts=np.array(pts,float);wid=np.array(wid);nrm=np.array(nrm)
    cx,cy=pts[:,0].mean(),pts[:,1].mean(); rad=np.hypot(pts[:,0]-cx,pts[:,1]-cy)
    tree=cKDTree(pts); L=Lmm/vox; tol=L/4.5
    cases=[]
    for i in range(len(pts)):
        idx=np.array(tree.query_ball_point(pts[i],L+tol))
        if not len(idx): continue
        d=np.linalg.norm(pts[idx]-pts[i],axis=1)
        k=(np.abs(d-L)<tol)&(idx!=i); idx=idx[k]; d=d[k]
        if len(idx)<2 or len(np.unique(wid[idx]))<2: continue
        base=np.abs(d-L)*vox+0.3*(1-np.abs(nrm[idx]@nrm[i]))+1.0*np.abs(rad[idx]-rad[i])*vox
        cases.append((i,idx,base))
    out=(meta,wid,cases,len(pts))
    pickle.dump(out,open(ck,'wb')); return out

def phases_for(meta,per,wmult,nper,cmin=0.30):
    """phase per patch under one config"""
    byimg={}
    for wi,w,xi,f,H,W in meta: byimg.setdefault((f,H,W),[]).append(xi)
    cache={}
    for (f,H,W),xs in byimg.items():
        a=np.asarray(Image.open(f),dtype=np.float32); m=(a>4.0).astype(np.float32)
        win=int(per*wmult); step=max(30,int(per//3))
        bh=H if nper is None else min(H,int(per*nper))
        edges=[0] if nper is None else list(range(0,max(1,H-bh+1),max(1,bh//2)))
        tab={}
        for x0 in range(0,max(1,W-win),step):
            best=None
            for y0 in edges:
                ph,c=band_phase(a,m,x0,x0+win,y0,min(H,y0+bh),per)
                if not np.isnan(ph) and (best is None or c>best[1]): best=(ph,c)
            if best and best[1]>=cmin: tab[x0+win//2]=best[0]
        cache[f]=(np.array(sorted(tab)) if tab else np.array([]), tab, win)
    out=np.full(len(meta),np.nan)
    for j,(wi,w,xi,f,H,W) in enumerate(meta):
        kx,tab,win=cache[f]
        if not len(kx): continue
        i=int(np.argmin(np.abs(kx-xi)))
        if abs(kx[i]-xi)<=win*0.75: out[j]=tab[int(kx[i])]
    return out

def evaluate(prep,pha,wp=0.15):
    meta,wid,cases,npts=prep
    G=P=n=0
    for i,idx,base in cases:
        if np.isnan(pha[i]): continue
        pc=pha[idx]; ok=~np.isnan(pc)
        if ok.sum()<2: continue
        c=base.copy()
        c[ok]=c[ok]+wp*np.abs((pc[ok]-pha[i]+np.pi)%(2*np.pi)-np.pi)
        G+= wid[idx[int(np.argmin(base))]]==wid[i]
        P+= wid[idx[int(np.argmin(c))]]==wid[i]
        n+=1
    if n<200: return None
    g,p=100*G/n,100*P/n
    return g,p,100*(1-(100-p)/max(100-g,1e-9)),n

SCROLLS={'PHerc1667':('data/ink/w*.jpg','data/mesh/{w}_',7.91e-3,355),
         'PHerc0139':('data/gen/PHerc0139_w*_ink.jpg','data/gen/PHerc0139_{w}_',9.362e-3,266)}
PREP={k:prepare(k,*v) for k,v in SCROLLS.items()}
for k,v in PREP.items(): print(f"{k}: {v[3]} patches, {len(v[2])} scorable decisions")

GRID=[(wm,nb) for wm in (1.2,2.2,3.5) for nb in (3,5,8,None)]
res={}
print(f"\n{'window':>7} {'band':>6} | " + " | ".join(f"{s:>22}" for s in SCROLLS))
for wm,nb in GRID:
    row={}
    for s,(ip,mf,vox,per) in SCROLLS.items():
        pha=phases_for(PREP[s][0],per,wm,nb)
        r=evaluate(PREP[s],pha)
        row[s]=r
    res[(wm,nb)]=row
    cells=[]
    for s in SCROLLS:
        r=row[s]
        cells.append(f"{r[0]:5.1f}->{r[1]:5.1f} cut{r[2]:4.0f}%" if r else "        --       ")
    print(f"{wm:7.1f} {str(nb) if nb else 'full':>6} | " + " | ".join(f"{c:>22}" for c in cells))
pickle.dump(res,open('data/sweep_res.pkl','wb'))

print("\n===== HELD-OUT SELECTION (no selection bias) =====")
names=list(SCROLLS)
for sel,rep in [(names[0],names[1]),(names[1],names[0])]:
    best=max((k for k in res if res[k][sel]), key=lambda k: res[k][sel][2])
    rs,rr=res[best][sel],res[best][rep]
    print(f"  select on {sel}: best config window={best[0]}x period, band={best[1] or 'full'} "
          f"(cut {rs[2]:.0f}% on {sel})")
    print(f"     -> held-out score on {rep}: geom {rr[0]:.1f}% -> phase {rr[1]:.1f}%, "
          f"**cut {rr[2]:.0f}%**  (n={rr[3]})")
