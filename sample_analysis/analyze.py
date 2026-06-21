#!/usr/bin/env python3
"""
Piano sample analyzer — outputs a Sompyler instrument definition (.spli).

Uses mezzo-forte (mf) samples as the primary reference since that set
covers the full keyboard range. The analysis pipeline:

  1. Load each AIFF sample
  2. Detect the onset (hammer strike)
  3. Extract partial amplitudes via FFT (PROFILE)
  4. Extract attack shape from RMS envelope
  5. Extract decay/sustain shape from RMS envelope
  6. Group notes into register bins (one per octave)
  7. Average PROFILE across each bin, pick a representative envelope
  8. Write a .spli file with frequency-keyed variations

Shape coordinate format (Sompyler):
  'length_s:start_vol;x1,y1;x2,y2;...'
  - length_s: duration in seconds
  - start_vol: amplitude at x=0 in %dB (100=0dBFS, 0=-100dBFS)
  - xN: relative position (only ratios matter; normalized to length)
  - yN: amplitude in %dB
  - If start_vol omitted, values normalized to peak.
"""

import os
import sys
import glob
import numpy as np
import soundfile as sf
from scipy.signal import find_peaks

DATA_DIR  = os.path.join(os.path.dirname(__file__), 'data', 'piano', 'mf')
OUT_DIR   = os.path.join(os.path.dirname(__file__), 'output')
OUT_FILE  = os.path.join(OUT_DIR, 'piano_analyzed.spli')

# ── Note name → frequency ────────────────────────────────────────────────────

NOTE_SEMITONES = {
    'C': 0, 'Db': 1, 'D': 2, 'Eb': 3, 'E': 4, 'F': 5,
    'Gb': 6, 'G': 7, 'Ab': 8, 'A': 9, 'Bb': 10, 'B': 11,
}

def note_to_hz(name):
    """'A4' → 440.0, 'Bb3' → 233.08, etc. (equal temperament, A4=440)"""
    for prefix_len in (2, 1):
        pitch = name[:prefix_len]
        if pitch in NOTE_SEMITONES:
            octave = int(name[prefix_len:])
            semitone = NOTE_SEMITONES[pitch] + (octave + 1) * 12
            return 440.0 * 2 ** ((semitone - 69) / 12)
    raise ValueError(f'Unknown note: {name}')

def parse_filename(path):
    """'Piano.mf.A4.aiff' → ('mf', 'A4', 440.0)"""
    base = os.path.basename(path)
    parts = base.split('.')
    dynamic, note = parts[1], parts[2]
    return dynamic, note, note_to_hz(note)

# ── Audio loading ────────────────────────────────────────────────────────────

def load_mono(path):
    y, sr = sf.read(path)
    if y.ndim == 2:
        y = y.mean(axis=1)
    return y.astype(np.float64), sr

# ── Onset detection ──────────────────────────────────────────────────────────

def find_onset(y, sr, frame_ms=5):
    """Returns onset sample index using RMS threshold."""
    frame = int(sr * frame_ms / 1000)
    n_frames = len(y) // frame
    rms = np.array([
        np.sqrt(np.mean(y[i*frame:(i+1)*frame] ** 2))
        for i in range(n_frames)
    ])
    threshold = rms.max() * 0.04
    candidates = np.where(rms > threshold)[0]
    if len(candidates) == 0:
        return 0
    return candidates[0] * frame

# ── Partial extraction ───────────────────────────────────────────────────────

MAX_PARTIALS = 20
FFT_WINDOW_S = 0.5    # analysis window after onset
FFT_OFFSET_S = 0.05   # skip first 50ms (transient noise)

def extract_partials(y, sr, fundamental_hz, onset):
    """
    Returns list of partial amplitudes (len <= MAX_PARTIALS), normalized
    so the loudest partial = 100. Values < 1 are clamped to 0.
    """
    start = onset + int(FFT_OFFSET_S * sr)
    end   = start + int(FFT_WINDOW_S * sr)
    segment = y[start:end]
    if len(segment) < 512:
        return [100]

    window = np.hanning(len(segment))
    fft = np.abs(np.fft.rfft(segment * window))
    freqs = np.fft.rfftfreq(len(segment), 1.0 / sr)

    # Tolerance window: ±3% of each partial's expected frequency
    tol_ratio = 0.03

    amps = []
    for k in range(1, MAX_PARTIALS + 1):
        target = fundamental_hz * k
        if target > sr / 2:
            break
        lo_hz = target * (1 - tol_ratio)
        hi_hz = target * (1 + tol_ratio)
        lo_bin = int(lo_hz * len(segment) / sr)
        hi_bin = int(hi_hz * len(segment) / sr) + 1
        hi_bin = min(hi_bin, len(fft))
        if lo_bin >= hi_bin:
            amps.append(0.0)
        else:
            amps.append(float(fft[lo_bin:hi_bin].max()))

    peak = max(amps) if amps else 1.0
    if peak == 0:
        return [100]
    return [max(0, int(round(a / peak * 100))) for a in amps]

# ── Envelope analysis ────────────────────────────────────────────────────────

ENV_FRAME_MS = 10   # RMS frame size for envelope

def rms_envelope(y, sr):
    frame = int(sr * ENV_FRAME_MS / 1000)
    n = len(y) // frame
    return np.array([
        np.sqrt(np.mean(y[i*frame:(i+1)*frame] ** 2))
        for i in range(n)
    ])

def fit_attack(env, onset_frame, peak_frame):
    """
    Returns (length_s, shape_str) for the attack phase.
    Shape has 4 sample points from onset to peak.
    """
    segment = env[onset_frame:peak_frame + 1]
    if len(segment) < 2:
        length_s = 0.05
        return length_s, f'{length_s:.3f}:1,100'

    length_s = len(segment) * ENV_FRAME_MS / 1000
    # Normalize to peak = 100
    peak = segment.max()
    if peak == 0:
        return length_s, f'{length_s:.3f}:1,100'
    norm = segment / peak * 100

    # Sample 4 points across the attack
    n_pts = min(4, len(norm))
    indices = np.linspace(0, len(norm) - 1, n_pts + 1, dtype=int)[1:]
    coords = ';'.join(f'{i+1},{int(round(norm[idx]))}' for i, idx in enumerate(indices))
    return length_s, f'{length_s:.3f}:{coords}'

def fit_decay(env, peak_frame, sr_frames, max_s=15.0):
    """
    Returns (length_s, shape_str) for the decay/sustain phase.
    Samples 6 points on the decay curve from peak to -30dB (or max_s).
    """
    # Limit to max_s seconds of decay
    end_frame = min(len(env), peak_frame + int(max_s * 1000 / ENV_FRAME_MS))
    segment = env[peak_frame:end_frame]

    if len(segment) < 2 or segment[0] == 0:
        return max_s, f'{max_s:.1f}:100;1,0'

    norm = segment / segment[0] * 100  # 100 at start

    # Find where signal drops to -30dB (≈3% of peak)
    below_30db = np.where(norm < 3)[0]
    if len(below_30db) > 0:
        end_idx = below_30db[0]
    else:
        end_idx = len(norm) - 1

    length_s = (end_idx + 1) * ENV_FRAME_MS / 1000
    segment_trimmed = norm[:end_idx + 1]

    # Sample 6 points on the decay
    n_pts = 6
    indices = np.linspace(0, len(segment_trimmed) - 1, n_pts, dtype=int)
    coords_parts = ['100']  # start value before first ';'
    coords_parts += [f'{i+1},{int(round(segment_trimmed[idx]))}' for i, idx in enumerate(indices)]
    shape_str = f'{length_s:.1f}:{";".join(coords_parts)}'
    return length_s, shape_str

# ── Per-sample analysis ──────────────────────────────────────────────────────

def analyze_sample(path):
    """
    Returns dict with: note, hz, partials, attack_str, decay_str
    or None if analysis fails.
    """
    try:
        dynamic, note, hz = parse_filename(path)
        y, sr = load_mono(path)

        onset = find_onset(y, sr)
        env = rms_envelope(y, sr)

        onset_frame = onset // int(sr * ENV_FRAME_MS / 1000)
        peak_frame  = onset_frame + int(env[onset_frame:].argmax())

        partials = extract_partials(y, sr, hz, onset)
        attack_len, attack_str = fit_attack(env, onset_frame, peak_frame)
        decay_len, decay_str   = fit_decay(env, peak_frame, sr)

        return {
            'note': note,
            'hz': hz,
            'partials': partials,
            'attack': attack_str,
            'attack_len': attack_len,
            'decay': decay_str,
        }
    except Exception as e:
        print(f'  WARN {os.path.basename(path)}: {e}', file=sys.stderr)
        return None

# ── Register grouping ────────────────────────────────────────────────────────

# Bin boundaries in Hz — roughly one octave each.
# Key = representative frequency label used in the .spli (Hz of bin centre note).
REGISTER_BINS = [
    (0,    41,   31),    # A0–B0  (~27–31 Hz)  → label 27
    (41,   82,   55),    # C1–B1  (~33–62 Hz)  → label 55
    (82,   165,  110),   # C2–B2  (~65–123 Hz) → label 110
    (165,  330,  220),   # C3–B3  (~131–247Hz) → label 220
    (330,  660,  440),   # C4–B4  (~262–494Hz) → label 440
    (660,  1320, 880),   # C5–B5  (~523–988Hz) → label 880
    (1320, 2637, 1760),  # C6–B6  (~1047–1976) → label 1760
    (2637, 9999, 3520),  # C7–C8  (~2093–4186) → label 3520
]

def assign_bin(hz):
    for lo, hi, label in REGISTER_BINS:
        if lo < hz <= hi:
            return label
    return REGISTER_BINS[-1][2]

def average_profile(samples_in_bin):
    """Average partial volumes across notes in a register bin."""
    max_len = max(len(s['partials']) for s in samples_in_bin)
    matrix = np.zeros((len(samples_in_bin), max_len))
    for i, s in enumerate(samples_in_bin):
        p = s['partials']
        matrix[i, :len(p)] = p
    avg = matrix.mean(axis=0)
    # Normalize to loudest partial = 100
    peak = avg.max()
    if peak == 0:
        return [100]
    return [int(round(v / peak * 100)) for v in avg]

def pick_representative(samples_in_bin):
    """Pick the sample closest to the bin centre for envelope shapes."""
    label = assign_bin(samples_in_bin[0]['hz'])
    return min(samples_in_bin, key=lambda s: abs(s['hz'] - label))

# ── SPLI output ──────────────────────────────────────────────────────────────

def profile_to_yaml(partials, indent='      '):
    """Format PROFILE list, trimming trailing zeros."""
    while len(partials) > 1 and partials[-1] == 0:
        partials = partials[:-1]
    lines = [f'{indent}PROFILE:']
    for v in partials:
        lines.append(f'{indent}  - V: {v}')
    return '\n'.join(lines)

def write_spli(bins, path):
    lines = [
        'name: Piano',
        'source: >',
        '    Analyzed from University of Iowa Musical Instrument Samples.',
        '    Steinway & Sons model B, performed by Evan Mazunik, recorded 2001.',
        '    https://theremin.music.uiowa.edu/MISpiano.html',
        '    Analysis: FFT partial extraction + RMS envelope fitting.',
        '    This is a first-pass approximation; manual refinement is expected.',
        '',
        'character:',
        '  - ATTR: pitch',
        '    O: sine',
        '    R: "0.2:100;1,0"',
        '',
    ]

    for label, samples in sorted(bins.items()):
        rep   = pick_representative(samples)
        avg_p = average_profile(samples)
        note_list = ', '.join(s['note'] for s in sorted(samples, key=lambda s: s['hz']))

        lines += [
            f'    {label}:',
            f'      # Register: {note_list}',
            f'      # Representative sample: {rep["note"]} ({rep["hz"]:.1f} Hz)',
            f'      A: "{rep["attack"]}"',
            f'      S: "{rep["decay"]}"',
            profile_to_yaml(avg_p),
            '',
        ]

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write('\n'.join(lines))
    print(f'Written: {path}')

# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    samples_paths = sorted(glob.glob(os.path.join(DATA_DIR, '*.aiff')))
    if not samples_paths:
        print(f'No samples found in {DATA_DIR}', file=sys.stderr)
        sys.exit(1)

    print(f'Analyzing {len(samples_paths)} mf samples...')
    results = []
    for path in samples_paths:
        note = os.path.basename(path).split('.')[2]
        sys.stdout.write(f'  {note:<5}')
        sys.stdout.flush()
        r = analyze_sample(path)
        if r:
            results.append(r)
            sys.stdout.write(f'  attack={r["attack_len"]*1000:.0f}ms  partials={r["partials"][:5]}\n')
        else:
            sys.stdout.write('  FAILED\n')

    # Group into register bins
    bins = {}
    for r in results:
        label = assign_bin(r['hz'])
        bins.setdefault(label, []).append(r)

    print(f'\nRegister bins: {sorted(bins.keys())}')
    for label, samples in sorted(bins.items()):
        print(f'  {label:5d} Hz: {len(samples):2d} notes — '
              + ', '.join(s["note"] for s in sorted(samples, key=lambda s: s["hz"])))

    write_spli(bins, OUT_FILE)

if __name__ == '__main__':
    main()
