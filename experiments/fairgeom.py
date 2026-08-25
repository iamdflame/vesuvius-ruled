"""Fair fight: give geometry every cue a real tracer actually uses.
  - step length      |d - L|
  - surface normal agreement (from the mesh)
  - radial consistency: along a sheet radius barely changes; a wrap jump
    changes it by the sheet spacing.  This is the strongest geometric cue.
Then ask whether line phase still adds anything."""
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

# per-wrap normals from the mesh grid
NRM={}
for w in WR:
    X=tifffile.imread(f'data/mesh/{w}_x.tif'); Y=tifffile.imread(f'data/mesh/{w}_y.tif'); Z=tifffile.imread(f'data/mesh/{w}_z.tif')
    P=np.stack([X,Y,Z],-1)
    du=np.gradient(P,axis=1); dv=np.gradient(P,axis=0)
    n=np.cross(du,dv); ln=np.linalg.norm(n,axis=-1,keepdims=True)
    NRM[w]=np.where(ln>1e-9,n/np.maximum(ln,1e-9),0.0)

pts=[];wid=[];uid=[];pha=[];nrm=[]
for w in WR:
    keys=sorted(PH[w]); ka=np.array(keys)
    M=(tifffile.imread(f'data/mesh/{w}_x.tif')>0)
    for u,v in cols[w].items():
        x=u*RATIO; j=int(np.argmin(np.abs(ka-x)))
        if abs(ka[j]-x)>90: continue
        col=NRM[w][:,u][M[:,u]]
        if not len(col): continue
        nv=col.mean(0); ln=np.linalg.norm(nv)
        if ln<1e-9: continue
        pts.append(v[:3]); wid.append(widx[w]); uid.append(u); pha.append(PH[w][keys[j]]); nrm.append(nv/ln)
pts=np.array(pts,float); wid=np.array(wid); pha=np.array(pha); nrm=np.array(nrm)
rad=np.hypot(pts[:,0]-cx,pts[:,1]-cy)
tree=cKDTree(pts)
near=np.full(len(pts),np.inf)
for i in range(len(WR)):
    a=np.where(wid==i)[0]; b=np.where(wid!=i)[0]
    if len(a) and len(b): near[a]=cKDTree(pts[b]).query(pts[a])[0]
near_mm=near*VOX
print(f"{len(pts)} points with 3D position, surface normal, radius and line phase")

def run(L,tol,mode,wg_n,wg_r,wp,gate_mm=0.40):
    hit=n=0
    for i in range(len(pts)):
        idx=np.array(tree.query_ball_point(pts[i],L+tol))
        if not len(idx): continue
        d=np.linalg.norm(pts[idx]-pts[i],axis=1)
        k=(np.abs(d-L)<tol)&(idx!=i); idx=idx[k]; d=d[k]
        if len(idx)<2 or len(np.unique(wid[idx]))<2: continue
        c=np.abs(d-L)*VOX
        c=c+wg_n*(1-np.abs(nrm[idx]@nrm[i]))          # normal agreement
        c=c+wg_r*np.abs(rad[idx]-rad[i])*VOX          # radial consistency
        if mode=='always' or (mode=='gated' and near_mm[i]<gate_mm):
            c=c+wp*np.abs((pha[idx]-pha[i]+np.pi)%(2*np.pi)-np.pi)
        hit += wid[idx[int(np.argmin(c))]]==wid[i]; n+=1
    return hit,n

print("\ngeometry cues weighted: normals wn, radial wr.  phase weight wp=0.15")
for L,tol in [(60,15),(90,20)]:
    print(f"\nstep {L*VOX:.2f}mm  shell +/-{tol*VOX:.2f}mm")
    print(f"{'wn':>5} {'wr':>5} {'n':>5} {'geom':>8} {'+phase':>8} {'gain':>8}")
    for wn,wr in [(0.0,0.0),(0.3,0.0),(0.0,1.0),(0.3,1.0),(0.3,3.0),(0.3,10.0)]:
        h0,n0=run(L,tol,'none',wn,wr,0)
        h1,n1=run(L,tol,'always',wn,wr,0.15)
        if n0<30: continue
        r0,r1=100*h0/n0,100*h1/n1
        print(f"{wn:5.1f} {wr:5.1f} {n0:5d} {r0:7.1f}% {r1:7.1f}% {r1-r0:+7.1f}pp")
