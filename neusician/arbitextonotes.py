import re
from .markov_util import markov_sensible_tone_getter
from .harmonisation import closest_harmonic_tone_getter
from .restricted_88keys import boundguard
from collections import defaultdict

BASE64URL_STR = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
BASE64URL_CHARS = { k: v for v, k in enumerate(BASE64URL_STR) }

class CreativeStringError(RuntimeError):
    pass

def seedphrase_to_bigint(seed_phrase):
    base = 0
    def incr():
        nonlocal base
        base += 1
        return base - 1
    
    characters = defaultdict(incr)
    
    remainders = []
    for c in seed_phrase:
        remainders.append(characters[c])

    big_number = 0
    for i, r in enumerate(reversed(remainders)):
        big_number += r * base ** i
    
    return big_number


def tones(
        seed_phrase, model, melody_pause_ratio=(1,1),
        creativity=None, compositionalavi=None,
        restrict_88keys=False
    ):
    """ Tones from a seed phrase (any unicode string) based
        on a markov net model.
    """

    melody_level, pause_level = melody_pause_ratio
    melody_level += pause_level

    big_number = seedphrase_to_bigint(seed_phrase)

    markov_scheme, tone_it = markov_sensible_tone_getter(
        re.sub(r"\s", "", model)
    )

    bg = boundguard() if restrict_88keys else lambda x: x

    tone, melody, pause_offset = (None, 0, 0)
    def it_and_reset():
        nonlocal tone, melody, pause_offset
        ret = (tone[0], bg(tone[1]), tone[2][0])
        tone, melody, pause_offset = (None, 0, 0)
        return ret

    def my_iter():
        nonlocal big_number, tone, melody, pause_offset
        next(tone_it)
        while big_number:
            big_number, remainder = divmod(big_number, melody_level + pause_level)
            if remainder < pause_level:
                pause_offset += 1
                if tone: yield it_and_reset()
            elif melody > remainder:
                tone[2][0] += 1
            else:
                if tone: yield it_and_reset()
                melody = remainder
                big_number, tone = tone_it.send(big_number)
                tone = (pause_offset, tone, [1])

        if tone: yield it_and_reset()

    tones = list(my_iter())

    if creativity is None:
        return tones
    elif isinstance(creativity, str):
        creativity = creativity_from_b64string(creativity)

    if len(tones) < len(creativity):
        raise CreativeStringError(
            "Creativity demands more tones than available"
        )
    elif len(tones) > len(creativity):
        raise CreativeStringError(
            "There are more tones than changed by creativity"
        )

    quite_final_tones = []
    tone_getter = closest_harmonic_tone_getter()
    harmony_offset = 0
    next_harmony_offset = 0
    current_offset = 0
    for tone, change in zip(tones, creativity):
        orig_offset = tone[0] + current_offset
        if change["harmony"] == "f":
            new_offset = orig_offset
        elif change["harmony"] == "r":
            new_offset = tone[0] + harmony_offset
        else:
            new_offset = tone[0] + next_harmony_offset
        current_offset = tone[0] + tone[2] - orig_offset
        next_harmony_offset = max(next_harmony_offset, current_offset)
        new_offset += change.get("offset", 0)
        quite_final_tones.append({ "new": [ new_offset, tone_getter(
                change["harmony"], tone[1], change["steps"], change["octaves"]
            ), tone[2] + change.get("length", 0) ], "old": tone, **change
        })

    if compositionalavi is None:
        return quite_final_tones

    else:
        return compositor(quite_final_tones, compositionalavi)


def creativity_from_b64string(changes):
    # harmony flag: f r n -5 -4 -3 -2 -1 0 +1 +2 +3 +4 +5 +6
    #               ^ follow note
    #                 ^ offset relative to last harmony hook
    #                   ^ no harmony, step means chromatic step
    #                     ^----- set new harmony here -----^
    #                     = relative step back- or forward in the circle
    #                       of fifth.
    #                     - |step|>2 means step of the diatonic scale,
    #                       any mode. step +/-1 is an augmented/diminished
    #                       prime. 2 steps is a second (hence may yield the
    #                       same note as 1), 3 steps is a third, and so forth
    #                     - little or big steps, depends on scale chosen mode.

    variance, changes = changes.split("-", 1)
    octaves, steps, length, offset = (2*int(i)+1 for i in variance)
    big_number = 0
    for i, char in enumerate(reversed(changes)):
        big_number += BASE64URL_CHARS[char] * len(BASE64URL_STR) ** i
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
        rem, o = divmod(rem, offset)
        props["offset"] = o - int(variance[3])
        rem, l = divmod(rem, length)
        props["length"] = l - int(variance[2])
        rem, s = divmod(rem, steps)
        props["steps"] = s - int(variance[1])
        rem, o = divmod(rem, octaves)
        o -= int(variance[0])
        cum_octave += o
        props["octave"] = cum_octave
        changes.append(props)

    return changes


def creativity_to_b64string(changes):

    PROPS = ("offset", "length", "steps", "octave")
    # uncalculate accumulation:
    octaves = [0] * (len(changes)-1)
    for i, change in enumerate(reversed(changes[1:])):
        octaves[-1-i] = change["octave"] - changes[-2-i]["octave"]
    for i, o in enumerate(octaves):
        changes[i+1]["octave"] = o

    maxabs = {}
    for prop in PROPS:
        maxabs[prop] = max(abs(i[prop]) for i in changes)

    note_change_codes = []
    for change in changes:
        num = 0
        factor = 1
        for prop in PROPS:
            num += (change[prop] + maxabs[prop]) * factor
            factor *= 2 * maxabs[prop] + 1
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
        note_change_codes.append(num)

    big_number = 0
    base = 15
    for v in maxabs.values():
        base *= 2*v + 1

    for i, code in enumerate(reversed(note_change_codes)):
        big_number += code * base ** i

    base64 = []
    while big_number:
        big_number, remainder = divmod(big_number, len(BASE64URL_CHARS))
        base64.append(BASE64URL_STR[remainder])

    return ("".join(str(maxabs[i]) for i in reversed(PROPS))
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

