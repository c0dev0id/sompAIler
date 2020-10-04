import re
from collections import namedtuple

# Prototypical code, will be imported as module later.

CHARS = { str(letter): i for i, letter in enumerate((
    '_', 'a', 'b', 0, 'c', 'd', 'e', 1, 'f', 'g', 'h', 2, 'i', 'j', 'k', 3,
    'l', 'm', 'n', 4, 'o', 'p', 'q', 5, 'r', 's', 't', 6, 'u', 'v', 'w', 7,
    'x', 'y', 'z', 8, 'ä', 'ö', 'ü', 9, 'ß'))
}

def get_probability_model(string):

    def cycler(mylist):
        pos = 0
        length = len(mylist)
        def ret(num):
            pos = (pos + num) % length
            return mylist[pos]
        return ret

    class Model:

        def __init__(self, singles, multis=[]):
            singles = list(x for x in singles)
            self.notes = []
            self.cycler = cycler(tuple(x[0] for x in singles))
            self.positions = { pitch: pos for pos, pitch in enumerate(singles) }
            layers = [{ head: items for head, items in singles }]
            for head, items in sorted(multis, key=lambda k: len(k[0])):
                lendiff = len(head) - len(layers)
                for _ in range(lendiff):
                    layers.append({})
                d = layers[-1]
                for h in head[:-1]:
                    d = d.setdefault(h, {})
                d[ head[-1] ] = items
            self.markov_layers = layers

        def __call__(self, pos_number):
            base = min(len(self.notes), len(self.markov_layers))
            while base:
                tail = [ i.rstrip("-0123456789") for i in self.notes[-base:] ]
                ml = self.markov_layers[base-1]
                try:
                    for t in tail:
                        ml = ml[t]
                except KeyError:
                    base -= 1
                else:
                    break
            else:
                raise RuntimeError("Tail procession failed")

            pos_number, remainder = divmod(pos_number, sum(ml))
            i = 0
            while True:
                remainder -= ml[i]
                if remainder > 0:
                    i += 1
                else:
                    break
            octave = int(self.notes[-1].replace(tail[-1], ""))
            octave = octave + (octave + self.diffs[i]) // len(self.layers[0])
            pitch = (self.positions[tail[-1]] + self.diffs[i]) % len(self.layers[0])

            note = pitch + str(octave)

            self.notes.append(note)

            return pos_number, note

    # TODO rework from ground up:
    # ---------------------------
    # Support
    #   : separates variants
    #   / separates adjacent notes
    #   [...] circumfixes variant parts in /-separated parts
    #       A/B/C is equivalent to [A][B][C]
    # Examples: (for better overview, assume an octave of 26 tones A-Z)
    # A:B:C[D:E/F:G]H:I/J:[K/L:M]N/O/P:Q[R:S[T:U/V]:W]:X/Y/Z:56,48,36,...
    # yields following paths ...
    # - A           # A, B, and all these paths will be linked with same
    # - B           # probability scheme [56,48,36,...]:
    # - C/D/H       # Consequently reduced $SEED number is divmod()ed by
    # - C/E/F/H     # the sum of the values of that probability scheme.
    # - C/G/H       # If the remainder is, say, 65, then the scheme's
    # - I/J         # second item will be selected and mapped to
    # - K/L/N/O/P   # respective next melodic interval according
    # - M/N/O/P     # fingerprint preamble.
    # - Q/R
    # - Q/S/T
    # - Q/S/U/V
    # - Q/W
    # - X/Y/Z

    if '/' in string:
        singles, multis = re.split(r",(?=[^\s\d:]+/)", string, 1)
        print(multis)
    else:
        singles = string
        multis = None

    def parse(string):
        for items in re.split(r",(?!\d)", string):
            items = items.split(",", items)
            head, items[0] = split(":", items[0])
            yield head, [int(x) for x in items]

    def multiparse(string):
        for head, items in parse(string):
            head = tuple(split('/', head))
            yield head, items

    singles = parse(singles)
    multis = parse(multis)
    return Model(singles, multis)


if __name__ == '__main__':
    PROBABILITIES = get_probability_model(input("Probabilistic fingerprint: ").rstrip())
    phrase = re.sub(r"\W+", "_", input("Secret phrase (EN|DE): ").rstrip().lower())
    corrections = extract_corrections(int(
        input("Corrections to be applied use (integer):").rstrip() or 0
    ))

    phrasum = 0
    for exp, letter in enumerate(reversed(phrase)):
        phrasum += CHARS[letter] * len(CHARS) ** exp

    print(phrasum)

    notes = []
    while phrasum:
        ...
