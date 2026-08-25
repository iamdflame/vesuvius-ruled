import numpy as np
from scipy.ndimage import gaussian_filter1d

def _profile(a, m):
    n = m.sum(axis=1)
    return np.where(n > 0, (a * m).sum(axis=1) / np.maximum(n, 1), 0.0)

def _best_run(m, cov_min):
    cov = m.mean(axis=1); good = cov >= cov_min
    if not good.any(): return None
    idx = np.where(good)[0]
    return max(np.split(idx, np.where(np.diff(idx) > 1)[0] + 1), key=len)

def _acf_peak(s, pmin, pmax):
    d = s - gaussian_filter1d(s, pmax * 0.8); d -= d.mean()
    if d.std() < 1e-9: return 0, 0.0
    n = len(d)
    F = np.fft.rfft(d, n=2 * n)
    c = np.fft.irfft(F * np.conj(F))[:pmax + 40]; c /= c[0]
    lag = pmin + int(np.argmax(c[pmin:pmax]))
    return lag, float(c[lag])

def line_period(img, mask=None, pmin=120, nper_min=4.0, cov_min=0.30):
    """Dominant line period (px) and ACF strength, or (0, 0.0) if none."""
    a = np.asarray(img, np.float32)
    m = (a > 4.0) if mask is None else np.asarray(mask, bool)
    run = _best_run(m, cov_min)
    if run is None or len(run) < pmin * nper_min: return 0, 0.0
    s = _profile(a, m)[run[0]:run[-1] + 1]
    pmax = int(len(s) / nper_min)
    if pmax <= pmin + 20: return 0, 0.0
    return _acf_peak(s, pmin, pmax)

def score(img, mask=None, pmin=120, nper_min=4.0, cov_min=0.30, n_null=80, seed=0):
    """Text-presence score. z is measured against a row-shuffle null, which
    preserves the profile's value distribution and destroys only periodicity."""
    a = np.asarray(img, np.float32)
    m = (a > 4.0) if mask is None else np.asarray(mask, bool)
    run = _best_run(m, cov_min)
    if run is None or len(run) < pmin * nper_min: return None
    s = _profile(a, m)[run[0]:run[-1] + 1]
    pmax = int(len(s) / nper_min)
    if pmax <= pmin + 20: return None
    lag, peak = _acf_peak(s, pmin, pmax)
    rng = np.random.default_rng(seed)
    null = np.array([_acf_peak(rng.permutation(s), pmin, pmax)[1] for _ in range(n_null)])
    return dict(period=lag, acf=peak, null_mean=float(null.mean()),
                null_std=float(null.std()), z=float((peak - null.mean()) / (null.std() + 1e-9)),
                run_len=len(s))

def _phase(a, m, x0, x1, per, min_cov):
    A = a[:, x0:x1]; M = m[:, x0:x1]
    cov = M.mean(axis=1); good = cov >= min_cov
    if good.sum() < 3.0 * per: return np.nan, 0.0
    idx = np.where(good)[0]
    run = max(np.split(idx, np.where(np.diff(idx) > 1)[0] + 1), key=len)
    if len(run) < 3.0 * per: return np.nan, 0.0
    y = np.arange(run[0], run[-1] + 1)
    s = _profile(A, M)[y]
    d = s - gaussian_filter1d(s, per * 1.2); d -= d.mean()
    w = np.hanning(len(d))
    zc = np.sum(d * w * np.exp(-2j * np.pi * y / per))
    return float(np.angle(zc)), float(np.abs(zc) / (np.sum(np.abs(d) * w) + 1e-9))

def phase_track(img, period, mask=None, win=350, step=50, min_cov=0.60):
    """Line phase vs position along the winding direction, with confidence."""
    a = np.asarray(img, np.float32)
    m = (a > 4.0) if mask is None else np.asarray(mask, bool)
    m = m.astype(np.float32)
    out = []
    for x0 in range(0, a.shape[1] - win, step):
        p, c = _phase(a, m, x0, x0 + win, period, min_cov)
        out.append((x0 + win / 2.0, p, c))
    return np.array(out)

def _wrap(x): return (x + np.pi) % (2 * np.pi) - np.pi

def slip_scan(track, win=350, span=1100, cmin=0.42, nmin=5, step_c=100):
    """Phase discontinuity vs position. Windows overlapping the candidate
    point are excluded, so a seam cannot contaminate both trend fits."""
    ok = (~np.isnan(track[:, 1])) & (track[:, 2] >= cmin)
    xs, ph, cf = track[ok, 0], track[ok, 1], track[ok, 2]
    if len(xs) < 2 * nmin: return np.zeros((0, 3))
    g = win / 2.0; out = []
    for xc in np.arange(xs.min() + win, xs.max() - win, step_c):
        L = (xs <= xc - g) & (xs >= xc - g - span); R = (xs >= xc + g) & (xs <= xc + g + span)
        if L.sum() < nmin or R.sum() < nmin: continue
        xl, pl = xs[L], np.unwrap(ph[L]); xr, pr = xs[R], np.unwrap(ph[R])
        if np.diff(xl).max() > 2 * win or np.diff(xr).max() > 2 * win: continue
        cl = np.polyfit(xl, pl, 1); cr = np.polyfit(xr, pr, 1)
        s = abs(_wrap(np.polyval(cr, xc) - np.polyval(cl, xc)))
        res = np.r_[pl - np.polyval(cl, xl), pr - np.polyval(cr, xr)]
        noise = 1.4826 * np.median(np.abs(res - np.median(res))) + 1e-6
        out.append((xc, s, s / noise))
    return np.array(out) if out else np.zeros((0, 3))


# ---------------------------------------------------------------- stitching

def stitch_score(phase_a, phase_b):
    """Phase discontinuity between two patches. Lower = more likely the same
    sheet, continuing. Scale (measured on PHerc. 1667, 10 wraps):

        ~0.29 rad  correct continuation
        ~0.69 rad  same sheet, wrong place
        ~1.86 rad  different wrap (a sheet switch)
    """
    return float(abs(_wrap(phase_b - phase_a)))


def choose_continuation(phase_src, candidates):
    """Rank candidate continuations for a patch. `candidates` maps any key to
    a phase. Returns (best_key, scores) with scores sorted ascending.

    Posed as SELECTION, not detection: no threshold and no null, which is why
    it reaches 94% where thresholded detection of the same signal reaches ~20%.
    Real stitching already supplies a short candidate list from geometry, and
    this channel is independent of geometry -- so agreement is strong evidence
    and disagreement is a short review queue.
    """
    scores = sorted(((stitch_score(phase_src, p), k) for k, p in candidates.items()))
    return (scores[0][1] if scores else None), scores


def combine_with_geometry(geo_costs, phase_src, phase_cands,
                          ambiguous, weight=1.0):
    """Add the text channel to a geometric tracer's decision -- but ONLY where
    geometry is ambiguous.

    geo_costs   : {candidate_key: geometric cost}  (lower = geometry prefers it)
    phase_src   : line phase of the patch we are continuing FROM
    phase_cands : {candidate_key: line phase}
    ambiguous   : bool. Consult text only when geometry is uncertain here.
    weight      : scale of the phase term relative to geometric cost.

    Returns (best_key, combined_costs).

    Gating is not optional. Measured on 10 wraps of PHerc. 1667, applying the
    text channel at EVERY step makes a good geometric tracer worse (it adds a
    noisy vote where geometry was already right). Applied only in ambiguous
    steps it helps in every condition tested:

        gate recall/fpr     drift-error reduction
        1.0 / 0.0 (oracle)        73 - 77%
        0.8 / 0.1 (realistic)     56 - 59%
        0.6 / 0.2                 28 - 35%
        0.3 / 0.3                  ~0

    So gate quality is the leverage: a better compressed-region detector
    multiplies the benefit directly.
    """
    out = dict(geo_costs)
    if ambiguous:
        for k, p in phase_cands.items():
            if k in out:
                out[k] = out[k] + weight * stitch_score(phase_src, p)
    best = min(out, key=out.get) if out else None
    return best, out
