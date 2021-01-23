from copy import copy

_diatonic = (
            [ 0,  0,  0,  0,  0,  0,  0],
            ( 2,  2,  1,  2,  2,  2,  1),
            ('C','D','E','F','G','A','B'),
            ( 1,  2,  2,  1,  2,  2,  2)
        )

_chromatic = (
            (0,) * 12,
            (1,) * 12,
            ('C','C#','D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'),
            (1,) * 12
        )

def get_scaler(scale):

    length = len(scale[0])
    pos = 0

    def scaler(diff):
        nonlocal pos
        pos += diff
        pos %= length
        return pos

    return tuple(copy(s) for s in scale), scaler


def closest_harmonic_tone_getter():

    diatonic_scale, diatonic_scaler = get_scaler(_diatonic)
    adiff = 0

    def get_tone(diff, otone, add_steps=0, add_octaves=0):
        nonlocal adiff
        adiff += diff or 0
        bfr, aftr = (3, 1) if diff == abs(diff) else (-1, -3)
        if diff is None:
            scale, scaler = get_scaler(_chromatic)
        elif diff:
            scale, scaler = diatonic_scale, diatonic_scaler
            sdiff = diff//(abs(diff) or 1)
            for _ in range(abs(diff)):
                n0 = scaler(bfr)
                scale[0][n0] += sdiff
                scaler(aftr)

        _, nscaler = get_scaler(scale)

        sdiff = adiff // (abs(adiff) or 1)
        tone = otone[0]
        octave = int(otone[1:])
        octave += add_octaves
        adj_octave, tone = divmod(
            scale[2].index(tone)
          + max(0, abs(add_steps)-1) * add_steps/(abs(add_steps) or 1),
            len(scale[0])
        )
        octave += int(adj_octave)
        tone = int(tone)
        n0 = nscaler(tone)
        cstep = scale[0][n0]
        if cstep:
            # probe back if another note matches requested one
            c2step = 0
            while abs(cstep) > abs(c2step):
                n = nscaler(-sdiff)
                c2step += scale[sdiff][n] * sdiff
                if scale[0][n] == c2step:
                    sdiff = 0
                    break
        else:
            sdiff = 0

        if add_steps == 1:
            if sdiff == 1:
                sdiff = 0
                tone = scaler(0)
            else:
                sdiff += 1 
        elif add_steps == -1:
            if sdiff == -1:
                sdiff = 0
                tone = scaler(2)
            else:
                sdiff -= 1

        return scale[2][tone] + ('', '#', 'b')[sdiff] + str(octave)

    return get_tone


if __name__ == '__main__':
    t = closest_harmonic_tone_getter()
    while True:
        i = input("Tone[,Diff]: ")
        s = 0
        if i == '':
            break
        elif ',d' in i:
            i, d = i.split(",d")
            d = None if d == "chr" else int(d)
        else:
            d = 0
        if 's' in i:
            i, s = i.split('s')
            s = int(s)
        else:
            s = 0

        print(t(d, i, s))
