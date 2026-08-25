"""Corrected metric: success = the tracer STAYS ON ITS SHEET.
Picking a different column of the same wrap is not an error -- only leaving
the sheet is. Everything else is as measured: real 3D coords, real candidate
shells, real distance-to-nearest-other-sheet as the gate."""
import numpy as np, pickle
from scipy.spatial import cKDTree
from slip import wrap
VOX=7.91e-3; RATIO=8.76
cols,cx,cy=pickle.load(open('data/geom.pkl','rb'))
db=pickle.load(open('data/tracks.pkl','rb'))
PHW=['w013','w018','w023','w028','w029','w030','w031','w032','w034','w035']
PH={}
for w in PHW:
    A=db[(w,0)]; ok=(~np.isnan(A[:,1]))&(A[:,2]>=0.25)
    PH[w]={int(round(x)):float(p) for x,p,c in A[ok]}
WR=[w for w in PHW if w in cols]
widx={w:i for i,w in enumerate(WR)}
pts=[];wid=[];uid=[];pha=[]
for w in WR:
    keys=sorted(PH[w]); ka=np.array(keys)
    for u,v in cols[w].items():
        x=u*RATIO; j=int(np.argmin(np.abs(ka-x)))
        if abs(ka[j]-x)>90: continue
        pts.append(v[:3]); wid.append(widx[w]); uid.append(u); pha.append(PH[w][keys[j]])
pts=np.array(pts,float); wid=np.array(wid); uid=np.array(uid); pha=np.array(pha)
tree=cKDTree(pts)
near=np.full(len(pts),np.inf)
for i in range(len(WR)):
    a=np.where(wid==i)[0]; b=np.where(wid!=i)[0]
    if len(a) and len(b): near[a]=cKDTree(pts[b]).query(pts[a])[0]
near_mm=near*VOX

def run(L,tol,gate_mm,mode,wp):
    hit=n=amb=0; ncand=[]
    for i in range(len(pts)):
        src=pts[i]
        idx=np.array(tree.query_ball_point(src,L+tol))
        if not len(idx): continue
        d=np.linalg.norm(pts[idx]-src,axis=1)
        keep=(np.abs(d-L)<tol)&(idx!=i)
        idx=idx[keep]; d=d[keep]
        if len(idx)<2: continue
        if len(np.unique(wid[idx]))<2: continue     # no cross-sheet risk here
        ambiguous = near_mm[i]<gate_mm; amb+=ambiguous
        use=(mode=='always') or (mode=='gated' and ambiguous)
        c=np.abs(d-L)*VOX
        if use: c=c+wp*np.abs((pha[idx]-pha[i]+np.pi)%(2*np.pi)-np.pi)
        hit += wid[idx[int(np.argmin(c))]]==wid[i]; n+=1; ncand.append(len(idx))
    return hit,n,amb,(np.median(ncand) if ncand else 0)

print("metric: did the tracer STAY ON ITS SHEET (any column)?")
print("only decisions where the candidate shell contains >1 sheet are scored\n")
for L,tol in [(40,12),(60,15),(90,20)]:
    print(f"step {L*VOX:.2f}mm  shell +/-{tol*VOX:.2f}mm")
    print(f"{'gate mm':>8} {'n':>5} {'cands':>6} {'amb%':>6} {'geom':>8} {'always':>8} {'gated':>8} {'gain':>8}")
    for gate in [0.20,0.40,0.80]:
        h0,n0,_,mc=run(L,tol,gate,'none',0)
        h1,n1,_,_=run(L,tol,gate,'always',0.15)
        h2,n2,a,_=run(L,tol,gate,'gated',0.15)
        if n0<30: print(f"{gate:8.2f}  too few"); continue
        r0,r1,r2=100*h0/n0,100*h1/n1,100*h2/n2
        print(f"{gate:8.2f} {n0:5d} {mc:6.0f} {100*a/max(n2,1):5.1f}% {r0:7.1f}% {r1:7.1f}% {r2:7.1f}% {r2-r0:+7.1f}pp")
    print()
