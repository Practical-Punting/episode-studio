"""THE PUBLISH LOUDNESS — one home for the numbers both assemblers mix to.

Jodie's ruling, 27 Sep 2026, from EP50 on: -14 LUFS integrated, true peak no higher than
-1.0 dBTP. YouTube plays at about -14 and never turns a quiet video up, so the old -16
master played ~2 dB soft.

📌 WHY A MODULE. `assemble_episode.py` (single presenter) carried these as its own
constants and `twoway_render.py` carried a second, older recipe (-16, auto-level ON) that
nobody moved when the first one did. Two homes for one decision is how the two-way kept
the old level for nine days. Both mixers now import from here, and `qc_episode.py`'s
verdict reads the same target, so the maker and the checker cannot disagree.

⚠️ THE WHOLE MIX MOVES, NOT JUST THE VOICE. loudnorm acts on the SPEECH alone; the music
bed and the duck threshold are absolute numbers tuned against speech at MIX_REF_LUFS.
Lifting only the speech would put Gordon 2 dB further over the music AND duck the music
harder, because the key got hotter. So both are scaled by the same LIFT.

🔴 AND THE LIMITER RUNS WITH level=0. alimiter's auto-level is ON by default: it turns the
output up until the peaks hit FULL SCALE, so `limit=0.95` was never a ceiling. With
level=0 the limit IS the ceiling, and it sits LIMIT_MARGIN_DB under the true-peak target
because it is a SAMPLE-peak limiter and the AAC encode after it adds inter-sample overs.
Measured on EP48's own inputs (27 Sep 2026): -14.5 LUFS, true peak -1.6 dBTP at a 1.0 dB
margin; at 0.5 dB the peak was -1.1, too close to the line after the encode.
"""
TARGET_LUFS = -14.0          # integrated, whole file
TARGET_TP = -1.0             # dBTP ceiling, whole file
TOLERANCE_LU = 1.0           # the ceiling costs about half a LU on a hot raw mix
MIX_REF_LUFS = -16.0         # the speech level the bed/duck balance was tuned at — do not move
LIFT = 10 ** ((TARGET_LUFS - MIX_REF_LUFS) / 20)
LIMIT_MARGIN_DB = 1.0
LIMIT = round(10 ** ((TARGET_TP - LIMIT_MARGIN_DB) / 20), 4)
DUCK_THRESHOLD_REF = 0.015   # the sidechain threshold at MIX_REF_LUFS
