"""Score flattened scroll renders for ruled text structure.

    python cli.py data/PHerc1667/*_ink.jpg
    python cli.py --json data/PHerc1667/*_ink.jpg > scores.json

JSON output is one record per input, for piping into other tools.
"""
import sys, os, json
from ruled import load_render, score

def main(argv):
    as_json = "--json" in argv
    files = [a for a in argv if not a.startswith("--")]
    if not files:
        print(__doc__); return 1
    out = []
    if not as_json:
        print(f"{'file':44s} {'period':>7s} {'ACF':>7s} {'z':>8s}  verdict")
    for f in files:
        try:
            img, _ = load_render(f)
            r = score(img)
        except Exception as e:
            r = None
            if not as_json: print(f"{os.path.basename(f)[:44]:44s} error: {e}")
            continue
        if r is None:
            rec = dict(file=f, status="insufficient_coverage")
        else:
            v = "ruled_text" if r["z"] > 8 else ("weak" if r["z"] > 3 else "no_line_structure")
            rec = dict(file=f, status="ok", verdict=v, **r)
        out.append(rec)
        if not as_json:
            if rec["status"] != "ok":
                print(f"{os.path.basename(f)[:44]:44s} {'--':>7s} {'--':>7s} {'--':>8s}  too little coverage")
            else:
                print(f"{os.path.basename(f)[:44]:44s} {r['period']:7d} {r['acf']:7.3f} {r['z']:8.1f}  {rec['verdict']}")
    if as_json:
        json.dump(out, sys.stdout, indent=2); print()
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
