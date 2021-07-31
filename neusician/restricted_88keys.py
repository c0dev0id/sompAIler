import re

pitches = {
    'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11, # 'H': 11
}

def parse_pitch(key):
    pitch, octave = re.sub(r"(?<![-\d])(?=[-\d])", "|", key).split("|")
    pitchnum = pitches[pitch[0]]
    if pitch[-1] == "#":
        pitchnum += 1
    elif pitch[-1] == "b":
        pitchnum -= 1
    # breakpoint()
    pitchnum += 12 * (int(octave) + shift) - 9

    return pitchnum

def boundguard(start=0, stop=88):

    shift = 0

    def _inner(key, start=start, stop=stop):
        nonlocal shift
        pitchnum = parse_pitch(key)
        
        while pitchnum < start:
            shift += 1
            pitchnum += 12

        while pitchnum >= stop:
            shift -= 1
            pitchnum -= 12

        return re.sub(r"-?\d+$", lambda m: str(int(m.group(0)) + shift), key)

    return _inner
