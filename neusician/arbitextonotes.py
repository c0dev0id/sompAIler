import re
from markov_util import markov_sensible_tone_getter
from collections import defaultdict

BASE64URL_STR = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
BASE64URL_CHARS = { k: v for v, k in enumerate(BASE64URL_STR) }

def tones(seed_phrase, model, melody_pause_ratio=(1,1)):
    """ Tones from a seed phrase (any unicode string) based on a markov net model.

    Example for a model specification:
      model = "-7,-6,-5,-4,-3,-2,-1,0,1,2,3,4,5,6,7,"
        "C:83,23,56,76,92,96,88,76,79,85,86,72,48,33,65,D:100,77,52,30,35,42,95,123,90,82,75,62,78,82,98,"
        "E:45,16,23,15,29,44,59,76,67,53,49,37,25,56,62,F:13,12,17,15,14,19,30,21,25,15,19,17,16,23,26,"
        "G:55,42,33,24,32,39,46,55,51,45,37,31,39,42,36,39,A:83,7,20,12,15,23,19,92,19,12,14,17,23,29,97,"
        "H:1,0,0,0,0,0,0,0,15,0,0,0,0,0,1,"
        "C/E:D/F:C[D:E/F:G]A:A/E:[D/A:G]E/F/D:A[G:E[D:C/E]:F]:G/H/D:56,48,36,22,26,29,33,27,21,73,55,42,11,19,33"
    """

    melody_level, pause_level = melody_pause_ratio
    melody_level += pause_level
    
    base = 0
    def incr():
        global base
        base += 1
        return base - 1
    
    characters = defaultdict(incr)
    
    remainders = []
    for c in seed_phrase:
        remainders.append(characters[c])

    big_number = 0
    for i, r in enumerate(reversed(remainders)):
        big_number += r * base ** i
    
    markov_scheme, tone_it = markov_sensible_tone_getter(
        re.sub(r"\s", "", model)
    )

    tone, melody, pause_offset = (None, 0, 0)
    def get_tone():
        nonlocal tone, melody, pause_offset
        ret = (*tone[0:2], tone[2][0])
        tone, melody, pause_offset = (None, 0, 0)
        return ret

    def my_iter():
        next(tone_it)
        while big_number:
            big_number, remainder = divmod(big_number, melody_level + pause_level)
            if remainder < pause_level:
                pause_offset += 1
                if tone: yield get_tone()
            elif melody > remainder:
                tone[2][0] += 1
            else:
                if tone: yield get_tone()
                melody = remainder
                big_number, tone = tone_it.send(big_number)
                tone = (pause_offset, tone, [1])

        yield tone[0], tone[1], tone[2][0]

    return list(my_iter())


def creativity_from_b64string(changes):
    # harmony flag: f r n -5 -4 -3 -2 -1 0 +1 +2 +3 +4 +5 +6
    #               ^ follow note
    #                 ^ offset relative to last harmony hook
    #                   ^ no harmony, step means chromatic step
    #                     ^----- set new harmony here -----^
    #                     = relative step back- or forward in circle of fifth.
    #                     - step means step of the diatonic scale, any mode 
    #                     - i.e. a step is a second, 2 steps is a third.
    #                     - little or big steps, depends on scale / chosen mode.
    variance, changes = changes.split("-", 1)
    octaves, steps, length, offset = (2*int(i)+1 for i in variance)
    big_number = 0
    i = 0
    for char in reversed(changes):
        big_number += BASE64URL_CHARS[char] * len(BASE64URL_STR) ** i
        i += 1
    base = 15 * octaves * steps * length * offset
    remainders = []
    while big_number:
        big_number, remainder = divmod(big_number, base)
        remainders.append(remainder)
    changes = []
    cum_octave = 0
    for rem in reversed(remainders):
        rem, harmony = divmod(rem, 15)
        if harmony == 0:
            harmony = "f"
        elif harmony == 1:
            harmony = "r"
        elif harmony == 2:
            harmony = None
        else:
            harmony -= 8
        props = { "harmony": harmony }
        rem, o = divmod(rem, octaves)
        cum_octave += o
        props["octave"] = cum_octave
        rem, s = divmod(rem, steps)
        props["steps"] = s
        rem, l = divmod(rem, length)
        props["length"] = l
        rem, o = divmod(rem, offset)
        props["offset"] = o
        changes.append(props)

    return changes


def creativity_to_b64string(changes):

    note_change_codes = []
    PROBS = ("offset", "length", "steps", "octaves")
    # uncalculate accumulation:
    for i, change in enumerate(reversed(changes[1:])):
        change["octaves"] -= changes[-1-i]["octaves"]

    maxabs = {}
    minima = {}
    for prop in PROPS:
        maxabs[prop] = max(abs(i[prop]) in changes)

    for change in changes:
        num = 0
        for i, prop in enumerate(PROPS):
            num += (change[prop] + maxabs[prop]) * (2*maxabs[prop]+1)**i
        num *= 15
        harmony = change["harmony"]
        if harmony == "f":
            harmony = 0
        elif harmony == "r":
            harmony = 1
        elif harmony is None:
            harmony = 2
        else:
            harmony += 8
        num += harmony
        note_change_codes.append(harmony)

    big_number = 0
    base = 15
    for v in maxabs.values():
        base *= 2*i + 1

    for i, code in enumerate(reversed(note_change_codes)):
        big_number += code * base ** i

    base64 = []
    while big_number:
        big_number, remainder = divmod(big_number, len(BASE64URL_CHARS))
        base64.append(BASE64URL_STR[remainder])

    return ("".join(maxabs[i] for i in reversed(PROPS))
            + "-" + "".join(reversed(base64))
        )


def creativize_tones(tones, changes):

    if isinstance(changes, str):
        changes = extract_creativity_string(changes)

    harmony_cof_pos = 0
    harmony_offset  = 0
    lastnote_pos    = 0
    lastnote_next   = []

    for tone, change in zip(tones, changes):
        offset, tone, length = tone
        pitch, octave = re.fullmatch(r"(\D+)(\d)", tone).groups()
        octave = int(octave) + change["octave"]
        if change["harmony"] == "f":
            pass
        elif change["harmony"] == "r":
            lastnote_pos = harmony_cof_pos
        else:
            lastnote_pos = max(lastnote_next)
            lastnote_next = []

        offset += lastnote_pos

        lastnote_pos = offset + length
        lastnote_next.append(lastnote_pos)

