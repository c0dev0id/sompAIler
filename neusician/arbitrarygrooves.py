import re
from sys import stdin as textinp, stdout as textoutp, argv
from .input_error import last_lines, ScorePreprocessingError
from .arbitextonotes import seedphrase_to_bigint
from .markov_util import markov_sensible_tone_getter
from .ranged_permutation_picker import RangedPermutationPicker

def randomint_getter(big_number):

    reduced = 0
    base = yield

    while True:
        if reduced == 0: reduced = big_number
        reduced, remainder = divmod(reduced, base)
        base = yield remainder


getter = None
markov_adv = None

def voiceline(length, height, melody_share=1, pause_share=1, depth=0):

    each = melody_share + pause_share + 1
    last = 0
    last_t = 0

    ret = []
    for _ in range(length):
        t = getter.send(each)
        if t > (last_t or pause_share):
            last_t = t
            p = getter.send(height) - depth
            if p == 0 and last != 0:
                last = p
                ret.append('o=')
            else:
                rp = p - last
                last = p
                if rp > 0:
                    if rp > 2: rp = f'+{rp}'
                    else: rp = '+' * rp
                elif rp < 0:
                    if rp < -2: rp = str(rp)
                    else: rp = '-' * abs(rp)
                else:
                    rp = ''
                ret.append('o' + rp)
        elif t < pause_share or not last_t:
            ret.append('.')
            last_t = 0
        else:
            ret.append('_')
            
    return ''.join(ret)


def rhythmelcode_picker(spec):
    spec = re.sub(r"(?=[^\d()])|(?<=\d)", " ", spec).split()
    if '0' in spec:
        i = spec.index('0')
        rhythm, melody = spec[0:i], spec[i+1:]
    else:
        raise ValueError("No first zero to mark where melody starts")

    for r in rhythm:
        # -n: n Ticks Pause
        # n: 1 Ton der Länge n
        # m(nnn...) oder m(x:...):
        #    vier Töne der mglw. unterschiedlichen Längen n,
        #    Gesamtlänge x, verhältnismäßig skaliert auf Länge n, oder
        #    Gesamtlänge n, durch die die Summe der Teillängen teilbar
        #    ist, oder umgekehrt ist n teilbar durch die Summe der Teil-
        #    längen.
        ...

    sign = 1
    cons_melody = []
    for m in melody:
        if m[0] == '+':
            if sign == 1:
                cons_melody.append('R')
                continue
            else:
                sign = 1
            m = m[1:]
        elif m[0] == '-':
            if sign == -1:
                cons_melody.append('R')
                continue
            else:
                sign = -1
            m = m[1:]

        if m.isdecimal():
            cons_melody.append(sign * int(m))
        else:
            raise ValueError(f"{m} is not decimal")


def get_rhythm(*rpp_args):
    rpp = RangedPermutationPicker(*rpp_args)
    index = getter.send(rpp.permutations)
    return rpp.sequence_at_index(index)

def get_melody(length, shift_to_base_prob, upper_probs, lower_probs):

    tones = [ x for (x,) in markov_adv[0][0].keys() ]

    def number_of(tone):
        m = re.match(r"[^\d-]+", tone)
        if m:
            position = tones.index(m.group(0))
            octave = int(tone[m.end():])
        else:
            raise ValueError(f"Not a tone: {tone}")
        return octave * len(tones) + position
        
    TMP_HEIGHT = sum(upper_probs) + sum(lower_probs)
    TMP_SCALE = lower_probs + upper_probs
    melody = []
    while len(melody) < length:
        kind = getter.send(shift_to_base_prob+TMP_HEIGHT)
        if shift_to_base_prob > kind:
            melody.append("=")
            continue
        tone = next(markov_adv[1])
        tonum = number_of(tone)
        isneg, tonum = divmod(tonum % (2*TMP_HEIGHT), TMP_HEIGHT)
        if isneg:
            tonum = -tonum % TMP_HEIGHT
        findex = 0
        while tonum > 0:
            tonum -= TMP_SCALE[findex]
            findex += 1
        melody.append( findex-len(lower_probs) )

    return melody


def get_both(melody, rhythm, offset, span, articles='o', modifiers=None):

    if offset is None: offset = 0

    if span:
        until_excl = offset + span
    else:
        until_excl = offset + max(len(rhythm), len(melody))

    if not offset < len(rhythm):
        raise ValueError(f"offset {offset} too far off, rhythm does not contain it")
    if until_excl > (r0 := sum(rhythm)): # may adapt offset and until_excl for melody
        r = len(rhythm)
        new = []
        for ticks in (offset, until_excl):
            total = 0
            for i, length in enumerate(rhythm):
                if ticks < total + abs(length):
                    break
                total += length
            new.append((i, ticks-total))
        offset, until_excl = new
        rhythm = [ *rhythm[offset[0]:], *(rhythm[ i % r ] for i in range(until_excl[0] - r)) ]
        rhythm[0] -= offset[1]
        rhythm[-1] -= until_excl[1]
        offset = offset[0]
        until_excl = until_excl[0]

    if not offset < len(melody):
        raise ValueError(f"offset {offset} too far off, melody does not contain it")
    if until_excl > (m := len(melody)):
        melody = [ *melody[offset:], *(melody[ i % m ] for i in range(until_excl - m)) ]

    aggregation = []
    pause = 0
    for r, m in zip(rhythm, melody):
        if r < 0:
            pause -= r
            continue
        else:
            aggregation.append((pause, m, r))
            pause = 0

    def quantify(num, sign=None):
        if sign is None:
            if num == '=': return num
            elif abs(num) > 2:
                return f"{num:+d}"
            else:
                return ['',"+","-"][num//abs(num or 1)]*abs(num)
        elif num > 2:
            return f"{sign}{num}"
        else:
            return sign*num

    return "".join(
        quantify(pause, ".") + articles[ i % len(articles) ]
        + quantify(tone) + quantify(length-1, '_')
          for i, (pause, tone, length) in enumerate(aggregation)
    ) + quantify(pause, '.')
        


memory = (
        {'_last_melody': ([], [None, None, None, None]) },
        {'_last_rhythm': ([], [None, None, None]) }
)

def melody_cycler(
        items_or_reference,
        pause_prob=None, shift_to_base_prob=None,
        upper_probs=None, lower_probs=None, *,
        save=None, extend=False, offset=0, span=None,
        modifiers=None, articles='o', rotate=0
    ):

    if isinstance(items_or_reference, str) and items_or_reference.startswith('?'):
        try:
            mel_pattern_name = items_or_reference[1:]
            memory[0]['_last_melody'] = saved = memory[0][mel_pattern_name]
        except KeyError:
            del memory[0]['_last_melody']
            list_of_names = ", ".join(memory[0])
            raise ScorePreprocessingError(
                    f'Melody pattern of name {mel_pattern_name} not found in '
                    f'available {list_of_names}.'
                )
    else:
        length = int(items_or_reference)
        saved = memory[0]['_last_melody']

    if save is not None:
        save_target = memory[0][save] = ([], [None, None, None, None])
    else:
        save_target = saved

    if saved[0]:
        data = saved[1]
        overwrote_sth = False
        if pause_prob is None:
            pause_prob = data[0]
        else:
            save_target[0][0] = pause_prob
            overwrote_sth = True
        if shift_to_base_prob is None:
            shift_to_base_prob = data[1]
        else:
            save_target[0][1] = shift_to_base_prob
            overwrote_sth = True
        if upper_probs is None:
            upper_probs = data[2]
        else:
            save_target[0][2] = upper_probs
            overwrote_sth = True
        if lower_probs is None:
            lower_probs = data[3]
        else:
            save_target[0][3] = lower_probs
            overwrote_sth = True
    else:
        overwrote_sth = True

    if overwrote_sth:
        if lower_probs is False: lower_probs = reversed(upper_probs[1:])
        melody = get_melody(length, pause_prob, shift_to_base_prob, upper_probs, lower_probs)
        if extend is False: save_target[0].clear()
        save_target[0].extend(melody)
    else:
        melody = saved[0]

    if rotate: melody = [ *melody[rotate:], *melody[0:] ]

    return get_both(melody, memory[1]['_last_rhythm'][0], offset, span, articles, modifiers)


def rhythm_cycler(
        items_or_reference, total=None, minimum_length=None, maximum_length=None,
        save=None, extend=False, offset=0, span=None, rotate=0,
        modifiers=None, articles="o", defer=False
    ):

    if isinstance(items_or_reference, str) and items_or_reference.startswith('?'):
        try:
            rh_pattern_name = items_or_reference[1:]
            memory[0]['_last_rhythm'] = saved = memory[1][rh_pattern_name]
        except KeyError:
            del memory[1]['_last_rhythm']
            list_of_names = ", ".join(memory[1]) or "(none)"
            raise ScorePreprocessingError(
                    f'Rhythm pattern of name "{rh_pattern_name}" not found in '
                    f'available {list_of_names}.'
                )
    else:
        items = int(items_or_reference)
        saved = memory[1]['_last_rhythm']

    if save is not None:
        save_target = memory[1][save] = ([], [None, None, None])
    else:
        save_target = saved

    if saved[0]:
        data = saved[1]
        overwrote_sth = False
        if total is None:
            total = data[0]
        else:
            save_target[1][0] = total
            overwrote_sth = True
        if minimum_length is None:
            minimum_length = data[1]
        else:
            save_target[1][1] = minimum_length
            overwrote_sth = True
        if maximum_length is None:
            maximum_length = data[2]
        else:
            save_target[1][2] = maximum_length
            overwrote_sth = True
    else:
        overwrote_sth = True

    if overwrote_sth:
        rhythm = get_rhythm(items, total, minimum_length, maximum_length)
        if extend is False: save_target[0].clear()
        save_target[0].extend(rhythm)
    else:
        rhythm = saved[0]

    if rotate: rhythm = [ *rhythm[rotate:], *rhythm[0:rotate] ]

    return '' if defer else get_both(
            memory[0]['_last_melody'][0], rhythm, offset, span, articles, modifiers
        )
    

def number_picker(*weights, start=0, end=None):
    if weights and isinstance(weights[0], str):
        fmt = weights.pop(0)
    else:
        fmt = '{}'

    if not all(isinstance(w, int) for w in weights):
        raise ValueError("all weights must be integer")

    nt = 'd'
    if "." in str(start):
        nt = 'f'
        if end is None:
            raise ValueError(
                "key argument 'end' must be specified given 'start' of type float"
            )
    elif end is None:
        if weights:
            end = start + len(weights)
        else:
            raise ValueError(
                "key argument 'end' nor weights are specified"
            )

    fmt = fmt.replace(r'{}', '{:%s}' % nt)

    total = 0
    items = fmt.count('{')
    values = []
    while len(values) < items:
        p = getter.send(sum(weights))
        for j, w in enumerate(weights):
            if p < total + w:
                break
            total += w
        v = start + (j + (p - total) / w) / len(weights) * (end - start)
        if nt == 'd': v = int(v)
        values.append(v)

    return fmt.format(*values)


allowed = {
    'vl': voiceline,
    'mel': melody_cycler,
    'rh': rhythm_cycler,
    'rhm': rhythmelcode_picker,
    'n': number_picker,
    '__builtins__': {}
}
def expand_line(s):

    last_lines.unpacked_line(s)

    def _resolver(m):
        d = m.groupdict()
        if d['mel'] is not None:
            d['func'] = 'mel'
            d['args'] = d.pop('mel')
        elif d['rh'] is not None:
            d['func'] = 'rh'
            d['args'] = d.pop('rh')
        elif d['func'] is None:
            d['func'] = 'rhm' if d['args'].startswith("!") else 'vl'

        d['args'] = re.sub(r"^(?![\"']|-?\d+,)([^,]+)", r'"\1"', d['args'])
        d['args'] = re.sub(r">([a-z]\w*)", r', save="\1"', d['args'])
        d['args'] = re.sub(r"([+-]\d+)$",  r', rotate=\1', d['args'])
        if d['chained'] is None:
            d['chained'] = {}
        else:
            d['chained'] = {'defer': True}

        for x in ('modifiers', 'start', 'span'):
            val = d.pop(x, None)
            if val is not None:
                d['chained'][x] = val
        if d['chained']:
            d['chained'] = ", " + ", ".join(f'{key}={value!r}' for key, value in d['chained'].items())
        else:
            d['chained'] = ''

        if d['before'] == '<':
            d['before'] = ''

        try:
          return d['before'] + eval(
            '{func}({args}{chained})'.format(**d), allowed
          )
        except NameError as e:
            raise ScorePreprocessingError(f'No score snippet preprocessing filter {e.name}')
        except TypeError as e:
            raise ScorePreprocessingError(str(e))

    # re.sub(r"(?P<before>(?:[^\s#]\s*-|[^-,:{\[]) \s*)", _resolver, s, re.X)
    return re.sub(r"""
      (?P<before>(?: \s (?=\?\w) | [^\s#]\s*- | [^-,:{\[\s] )
                 (?: \B\s* | \s+ ) # space optional if non-word character preceeds
      )
      (?:
         (?: \?(?P<func>\w+))?
         \( (?(func)|(?=\d+,|['"?!])) (?P<args>[^;)]+) \)
       | \[          (?=\d+,|['"?])  (?P<mel>[^;\]]+) \]
       | \{          (?=\d+,|['"?])  (?P<rh>[^;}]+)   \}
      )
      (?<=[)}\]])
      (?: (?P<chained>(?<=\})> (?=<\[))
        | (?::(?P<modifiers>\D[^:]+))?
          (?::(?P<start>\d+))?
          (?:\+(?P<span>\d+))?
      )
      """, _resolver, s, flags=re.X)
      

def preprocess(infileobj=None):
    global getter, markov_adv

    arbitext = []

    if infileobj is None:
        infileobj = textinp

    slurp_mode = None
    markov_spec = []
    markov_tail = False

    for line in infileobj:
    
        if line.startswith('*** '):
            endmarker = line[4:]
            if ':' in endmarker:
                endmarker, markov_tail = endmarker.split(':')
            else:
                markov_spec = open("markov_default.txt").read()
            slurp_mode = True
            arbitext.clear()
            continue
    
        if slurp_mode:
            if line.rstrip() == f"END {endmarker}":
                slurp_mode = False
                getter = randomint_getter(seedphrase_to_bigint("".join(arbitext)))
                next(getter)
            else:
                arbitext.append(line)
        elif markov_tail:
            if line == f"END {markov_tail}":
                markov_tail = False
                markov_adv = markov_sensible_tone_getter(re.sub(r"\s+", "", "".join(markov_spec)), getter)
                markov_spec.clear()
            else:
                markov_spec.append(line)
        else:
            yield expand_line(line)


if __name__ == '__main__':
    if len(argv) > 1:
        textfile_in = argv[1]
        textinp = open(textfile_in, 'r')
    
    if len(argv) == 3:
        textfile_out = argv[2]
        textoutp = open(textfile_out, 'w')
    
    try:
        for line in preprocess():
            print(line, end='', file=textoutp)
    except ScorePreprocessingError as e:
        print(str(e), "– Last lines processed:\n", e.tail_log(), end="")

    exit()
