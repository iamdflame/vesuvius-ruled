"""ruled — training-free text-structure scoring for Herculaneum scroll segments.

Two measurements, both computed from a flattened ink-prediction image alone:

  score(img)      Is there a ruled line grid here?  Returns period, ACF strength
                  and a z-score against a within-image row-shuffle null.

  phase_track(img)  Where does the line grid sit, along the winding direction?
                  Smooth inside a correct segmentation; steps at a sheet switch.

No training, no geometry, no GPU.  Scope: needs ink predictions as input —
raw surface texture does not carry the line grid (measured; see README).
"""
from .surface import read_slice
from .core import (score, phase_track, slip_scan, line_period,
                   stitch_score, choose_continuation, combine_with_geometry)
__all__=["score","phase_track","slip_scan","line_period",
         "stitch_score","choose_continuation","combine_with_geometry","read_slice"]
__version__="0.1.0"
