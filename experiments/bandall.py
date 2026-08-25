"""Apply vertical banding to every scroll. Does it rescue PHerc0172?"""
import numpy as np, glob, os, re
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

def prof_period(a,m,lo,hi):
    cov=m.mean(axis=1); n=m.sum(axis=1)
    p=np.where(n>0,(a*m).sum(axis=1)/np.maximum(n,1),0.)
    idx=np.where(cov>=0.30)[0]
    if len(idx)<400: return 0
    run=max(np.split(idx,np.where(np.diff(idx)>1)[0]+1),key=len)
    if len(run)<400: return 0
    s=p[run[0]:run[-1]+1]
    hi=min(hi,int(len(s)/4))
    if hi<=lo: return 0
    d=s-gaussian_filter1d(s,hi*0.8); d-=d.mean()
    if d.std()<1e-9: return 0
    nn=len(d); F=np.fft.rfft(d,n=2*nn); c=np.fft.irfft(F*np.conj(F))[:hi+40]; c/=c[0]
    return lo+int(np.argmax(c[lo:hi]))

SETS=[('PHerc1667','data/ink/w*.jpg',(250,520)),
      ('PHerc0139','data/gen/PHerc0139_*_ink.jpg',(190,400)),
      ('PHerc0172','data/gen/PHerc0172_*_ink.jpg',(120,260)),
      ('PHercParis4','data/multi/PHercParis4__*.jpg',(250,520))]
print(f"{'scroll':>12} {'segs':>5} {'per':>5} | {'FULL-HEIGHT conf':>17} | {'3-PERIOD BAND conf':>19} | {'verdict change'}")
for name,pat,band in SETS:
    full=[]; ban=[]; per_used=[]
    for f in sorted(glob.glob(pat)):
        a=np.asarray(Image.open(f),dtype=np.float32); m=(a>4.0).astype(np.float32)
        H,W=a.shape
        per=prof_period(a,m,*band)
        if not per: continue
        per_used.append(per)
        win=int(per*2.2); step=max(40,per//3)
        if W<=win+40: continue
        for x0 in range(0,W-win,step):
            ph,c=band_phase(a,m,x0,x0+win,0,H,per)
            if not np.isnan(ph): full.append(c)
        bh=int(per*3)
        edges=list(range(0,max(1,H-bh+1),max(1,bh//2))) or [0]
        for x0 in range(0,W-win,step*2):
            for y0 in edges:
                ph,c=band_phase(a,m,x0,x0+win,y0,min(H,y0+bh),per)
                if not np.isnan(ph): ban.append(c)
    if not full or not ban: print(f"{name:>12}  insufficient"); continue
    mf,mb=np.median(full),np.median(ban)
    vf="PASS" if mf>=0.30 else ("marg" if mf>=0.22 else "FAIL")
    vb="PASS" if mb>=0.30 else ("marg" if mb>=0.22 else "FAIL")
    print(f"{name:>12} {len(per_used):5d} {int(np.median(per_used)):5d} | {mf:9.3f} ({vf:>4})   | {mb:11.3f} ({vb:>4})    | {vf} -> {vb}")
