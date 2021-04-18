import re

pitches = {
    'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11, # 'H': 11
}

def boundguard():

    shift = 0

    def _inner(key):
        nonlocal shift
        pitch, octave = re.sub(r"(?=\d)", "|", key).split("|")
        pitchnum = pitches[pitch[0]]
        if pitch[-1] == "#":
            pitchnum += 1
        elif pitch[-1] == "b":
            pitchnum -= 1
        
        pitchnum += 12 * (int(octave) + shift) - 9

        while pitchnum < 0:
            shift += 1
            pitchnum += 12

        while pitchnum > 87:
            shift -= 1
            pitchnum -= 12

        return re.sub(r"\d+$", lambda m: str(int(m.group(0)) + shift), key)

    return _inner
