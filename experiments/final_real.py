"""Does the gain concentrate where sheets are physically close?
Strong geometric baseline (step length + normals + radial consistency)."""
import numpy as np, pickle, tifffile
from scipy.spatial import cKDTree
VOX=7.91e-3; RATIO=8.76
cols,cx,cy=pickle.load(open('data/geom.pkl','rb'))
db=pickle.load(open('data/tracks.pkl','rb'))
PHW=['w013','w018','w023','w028','w029','w030','w031','w032','w034','w035']
PH={}
for w in PHW:
    A=db[(w,0)]; ok=(~np.isnan(A[:,1]))&(A[:,2]>=0.25)
    PH[w]={int(round(x)):float(p) for x,p,c in A[ok]}
WR=[w for w in PHW if w in cols]; widx={w:i for i,w in enumerate(WR)}
NRM={}
for w in WR:
    X=tifffile.imread(f'data/mesh/{w}_x.tif');Y=tifffile.imread(f'data/mesh/{w}_y.tif');Z=tifffile.imread(f'data/mesh/{w}_z.tif')
    P=np.stack([X,Y,Z],-1); n=np.cross(np.gradient(P,axis=1),np.gradient(P,axis=0))
    ln=np.linalg.norm(n,axis=-1,keepdims=True); NRM[w]=np.where(ln>1e-9,n/np.maximum(ln,1e-9),0.)
pts=[];wid=[];pha=[];nrm=[]
for w in WR:
    keys=sorted(PH[w]); ka=np.array(keys); M=(tifffile.imread(f'data/mesh/{w}_x.tif')>0)
    for u,v in cols[w].items():
        x=u*RATIO; j=int(np.argmin(np.abs(ka-x)))
        if abs(ka[j]-x)>90: continue
        col=NRM[w][:,u][M[:,u]]
        if not len(col): continue
        nv=col.mean(0); ln=np.linalg.norm(nv)
        if ln<1e-9: continue
        pts.append(v[:3]); wid.append(widx[w]); pha.append(PH[w][keys[j]]); nrm.append(nv/ln)
pts=np.array(pts,float); wid=np.array(wid); pha=np.array(pha); nrm=np.array(nrm)
rad=np.hypot(pts[:,0]-cx,pts[:,1]-cy); tree=cKDTree(pts)
near=np.full(len(pts),np.inf)
for i in range(len(WR)):
    a=np.where(wid==i)[0]; b=np.where(wid!=i)[0]
    if len(a) and len(b): near[a]=cKDTree(pts[b]).query(pts[a])[0]
near_mm=near*VOX

L,tol,WN,WR_,WP=90,20,0.3,1.0,0.15
recs=[]
for i in range(len(pts)):
    idx=np.array(tree.query_ball_point(pts[i],L+tol))
    if not len(idx): continue
    d=np.linalg.norm(pts[idx]-pts[i],axis=1)
    k=(np.abs(d-L)<tol)&(idx!=i); idx=idx[k]; d=d[k]
    if len(idx)<2 or len(np.unique(wid[idx]))<2: continue
    base=np.abs(d-L)*VOX + WN*(1-np.abs(nrm[idx]@nrm[i])) + WR_*np.abs(rad[idx]-rad[i])*VOX
    ph=WP*np.abs((pha[idx]-pha[i]+np.pi)%(2*np.pi)-np.pi)
    g=wid[idx[int(np.argmin(base))]]==wid[i]
    p=wid[idx[int(np.argmin(base+ph))]]==wid[i]
    recs.append((near_mm[i],g,p))
R=np.array(recs)
print(f"n = {len(R)} decisions where the candidate shell spans >1 sheet")
print(f"step {L*VOX:.2f}mm, strong geometry (length + normals + radial)\n")
print(f"{'nearest other sheet':>22} {'n':>6} {'geometry':>9} {'+phase':>8} {'err cut':>8}")
edges=[0,0.15,0.30,0.50,0.80,99]
for a,b in zip(edges[:-1],edges[1:]):
    m=(R[:,0]>=a)&(R[:,0]<b)
    if m.sum()<40: continue
    g=100*R[m,1].mean(); p=100*R[m,2].mean()
    cut=100*(1-(100-p)/max(100-g,1e-9))
    lab=f"{a:.2f} - {b:.2f} mm" if b<99 else f"> {a:.2f} mm"
    print(f"{lab:>22} {int(m.sum()):6d} {g:8.1f}% {p:7.1f}% {cut:7.0f}%")
g=100*R[:,1].mean(); p=100*R[:,2].mean()
print(f"{'ALL':>22} {len(R):6d} {g:8.1f}% {p:7.1f}% {100*(1-(100-p)/(100-g)):7.0f}%")
