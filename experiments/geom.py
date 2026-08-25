"""Real geometry from the released meshes: where are wraps physically close
enough that a tracer could confuse them?  That is the true compressed region,
and the true ambiguity gate -- no simulation."""
import numpy as np, tifffile, glob, os, json
VOX=7.91e-3            # mm per volume unit
RATIO=8.76             # ink-ds8 px per tifxyz px

def load(w):
    try:
        x=tifffile.imread(f'data/mesh/{w}_x.tif'); y=tifffile.imread(f'data/mesh/{w}_y.tif')
        z=tifffile.imread(f'data/mesh/{w}_z.tif')
    except Exception: return None
    m=(x>0)&(y>0)&(z>0)
    return x,y,z,m

WRAPS=['w011','w012','w013','w018','w023','w028','w029','w030','w031','w032',
       'w033','w034','w035','w036','w037','w038','w039','w040','w041']
D={}
for w in WRAPS:
    r=load(w)
    if r: D[w]=r
print("loaded:", " ".join(sorted(D)))

# column centroid in 3D for each wrap (averaged over scroll-axis rows)
cols={}
for w,(x,y,z,m) in D.items():
    H,W=x.shape; c={}
    for u in range(W):
        mm=m[:,u]
        if mm.sum()<H*0.25: continue
        c[u]=(x[mm,u].mean(), y[mm,u].mean(), z[mm,u].mean(), mm.sum())
    cols[w]=c
    print(f"  {w}: {x.shape}  {len(c)} usable columns")

print("\nradial position of each wrap (cross-section distance from scroll centre):")
allx=np.concatenate([np.array([v[0] for v in c.values()]) for c in cols.values()])
ally=np.concatenate([np.array([v[1] for v in c.values()]) for c in cols.values()])
cx,cy=allx.mean(),ally.mean()
print(f"  estimated centre ({cx:.0f},{cy:.0f}) in volume units")
rad={}
for w,c in cols.items():
    r=np.array([np.hypot(v[0]-cx,v[1]-cy) for v in c.values()])
    rad[w]=r
    print(f"  {w}: radius mean={r.mean()*VOX:6.2f}mm  min={r.min()*VOX:6.2f}  max={r.max()*VOX:6.2f}")

print("\nminimum 3D distance between wrap pairs (mm) -- small = confusable:")
ks=sorted(cols)
print("        "+" ".join(f"{k[-3:]:>6s}" for k in ks))
for a in ks:
    Pa=np.array([[v[0],v[1],v[2]] for v in cols[a].values()])
    row=[]
    for b in ks:
        if a==b: row.append("   -  "); continue
        Pb=np.array([[v[0],v[1],v[2]] for v in cols[b].values()])
        idx=np.random.default_rng(0).choice(len(Pa),min(120,len(Pa)),replace=False)
        d=np.sqrt(((Pa[idx][:,None,:]-Pb[None,:,:])**2).sum(-1)).min()*VOX
        row.append(f"{d:6.2f}")
    print(f"  {a:5s} "+" ".join(row))
np.save('data/cols.npy', np.array([1]))
import pickle; pickle.dump((cols,cx,cy), open('data/geom.pkl','wb'))
