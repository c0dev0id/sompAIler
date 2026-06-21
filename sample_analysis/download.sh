#!/bin/sh
# Downloads University of Iowa MIS piano samples.
# Samples are stored in data/piano/{pp,mf,ff}/ and are gitignored.
# Re-run this script at any time to restore the sample library.
#
# Source: https://theremin.music.uiowa.edu/MISpiano.html
# Instrument: Steinway & Sons model B, recorded 2001
# Format: AIFF, 16-bit, 44.1 kHz, stereo

BASE="https://theremin.music.uiowa.edu/sound%20files/MIS/Piano_Other/piano"
DIR="$(dirname "$0")/data/piano"

fetch() {
    dynamic="$1"
    note="$2"
    dest="$DIR/$dynamic/Piano.$dynamic.$note.aiff"
    if [ -f "$dest" ]; then
        return 0
    fi
    url="$BASE/Piano.$dynamic.$note.aiff"
    printf "  %s %s ... " "$dynamic" "$note"
    if curl -sf -o "$dest" "$url"; then
        echo "ok"
    else
        echo "FAILED ($url)"
    fi
}

# All chromatic notes within an octave range, using Iowa's flat notation
notes_octave() {
    octave="$1"
    echo "C$octave Db$octave D$octave Eb$octave E$octave F$octave Gb$octave G$octave Ab$octave A$octave Bb$octave B$octave"
}

# ── pp (pianissimo): Bb0, B0, C1–B7, C8 ───────────────────────────────────
echo "Downloading pp samples..."
for note in Bb0 B0; do fetch pp "$note"; done
for oct in 1 2 3 4 5 6 7; do
    for note in $(notes_octave "$oct"); do fetch pp "$note"; done
done
fetch pp C8

# ── mf (mezzo-forte): B0, C1–B7, C8 (Gb7 is a broken link, skip) ──────────
echo "Downloading mf samples..."
fetch mf B0
for oct in 1 2 3 4 5 6; do
    for note in $(notes_octave "$oct"); do fetch mf "$note"; done
done
for note in C7 Db7 D7 Eb7 E7 F7 G7 Ab7 A7 Bb7 B7; do fetch mf "$note"; done
# Piano.mf.Gb7.aiff is a broken link on the source page — skipped
fetch mf C8

# ── ff (fortissimo): A0, Bb0, B0, C1–B7, C8 ──────────────────────────────
echo "Downloading ff samples..."
for note in A0 Bb0 B0; do fetch ff "$note"; done
for oct in 1 2 3 4 5 6 7; do
    for note in $(notes_octave "$oct"); do fetch ff "$note"; done
done
fetch ff C8

echo "Done."
