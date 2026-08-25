"""Score every image given on the command line. Usage: python cli.py *.jpg"""
import sys, os, numpy as np
from PIL import Image
from ruled import score
Image.MAX_IMAGE_PIXELS = None
print(f"{'file':44s} {'period':>7s} {'ACF':>7s} {'z':>8s}  verdict")
for f in sys.argv[1:]:
    r = score(np.asarray(Image.open(f).convert('L'), np.float32))
    if r is None:
        print(f"{os.path.basename(f)[:44]:44s} {'--':>7s} {'--':>7s} {'--':>8s}  too little coverage"); continue
    v = "RULED TEXT" if r['z'] > 8 else ("weak" if r['z'] > 3 else "no line structure")
    print(f"{os.path.basename(f)[:44]:44s} {r['period']:7d} {r['acf']:7.3f} {r['z']:8.1f}  {v}")
