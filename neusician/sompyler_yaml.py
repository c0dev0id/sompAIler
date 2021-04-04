from io import StringIO

def make_yaml_code(
        tones, beats, subdivisions, cut, beats_per_minute,
        upper_stress_bound, lower_stress_bound
    ):

    ticks_per_measure = len(beats) * len(subdivisions)
    ticks_per_minute = beats_per_minute * len(subdivisions)
    cut %= ticks_per_measure

    measure_tones = {}

    yaml = StringIO()
    yaml.write(
f"""
# This is Sompyler/YAML script, a human- as well as machine-readable
# music notation resoluble down to the level of exact sounding.
# It can be converted to "draft music" (i.e. an audience would expect
# better quality, but sound engineers are probably used to this kind of raw
# material) by your local installation of Sompyler.
#      Sompyler is available at <https://gitlab.com/flowdy/sompyler>.
#      (Limited support to Python programmers via Gitlab issues only)
#
# Coming soon: https://demo.neusik.de/sompyle, an online test instance for
#   users with a password. It will not be quite public, as the service is
#   poor of resources and therefore asks for patience and resilience against
#   being denied when no worker processess are available.
#
# Or, even better, make a sheet of it to play on your own instrument.
#

# Every measure contains all voices with notes in that measure. Notes
# are indicated by following scheme:
#     N: P L (N = offset from last bar, in ticks; P pitch; length, in ticks)
#
# A "tick" is the subdivision of the number of beats indicated in the
# stress pattern. "cut" adds to the offset of the first note. There will not
# be more pause before the note, only the stress of the note is adjusted
# accordingly.

stage:
  p: 1|1 0 dev/piano # Well, this "piano" is pretty unsatisfactory in sound.
                     # One may omit it alltogether, so Sompyler expects
                     # a ...

# ... free-style sound defined:
instrument p: {{}} # So simple, it is only a single sine.

# But, alas, this is not on sound, just on inspiration for composition.

---
_meta:
  stress_pattern: {",".join(str(x) for x in beats)};{",".join(str(x) for x in subdivisions)}
  ticks_per_minute: {ticks_per_minute}
  upper_stress_bound: {upper_stress_bound}
  lower_stress_bound: {lower_stress_bound}
  cut: {cut}

"""
    )

    following_measure = False

    def skipper(skipped_measures):
        nonlocal following_measure

        if following_measure:
            print("---", file=yaml)
        else:
            following_measure = True

        if measure_tones: print("p: {", ", ".join(
            ": ".join(str(x) for x in i) for i in measure_tones.items()
        ), "}\n", file=yaml)

        skipped_measures -= 1
        measure_tones.clear()

        for _ in range(skipped_measures):
            print("---\n{} # let last tone sound\n", file=yaml)

    for offset, pitch, length in tones:

        offset += cut
        skipped_measures, offset = divmod(offset, ticks_per_measure)

        if skipped_measures: skipper(skipped_measures)

        measure_tones[offset] = "{} {}".format(pitch, length)
        cut = offset + length

    skipper(int(cut % ticks_per_measure > 0) + cut // ticks_per_measure)

    return yaml
