import re
from sys import stdin as textinp, stdout as textoutp, argv
from .arbitextonotes import seedphrase_to_bigint

def randomint_getter(big_number):

    reduced = 0
    base = yield

    while True:
        if reduced == 0: reduced = big_number
        reduced, remainder = divmod(reduced, base)
        base = yield remainder


getter = None

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


def expand_line(line):

    return re.sub(
            r'\((?=\d)[\w,=\s]+\)',
            lambda m: eval(f'voiceline{m.group(0)}'),
            line
        )

arbitext = []

def preprocess(infileobj=textinp):
    global getter

    slurp_mode = None

    for line in infileobj:
    
        if line.startswith('*** '):
            endmarker = line[4:]
            slurp_mode = True
            arbitext.clear()
            continue
    
        if slurp_mode:
            if line == f"END {endmarker}":
                slurp_mode = False
                getter = randomint_getter(seedphrase_to_bigint("".join(arbitext)))
                next(getter)
            else:
                arbitext.append(line)
        else:
            yield expand_line(line)


if __name__ == '__main__':
    if len(argv) > 1:
        textfile_in = argv[1]
        textinp = open(textfile_in, 'r')
    
    if len(argv) == 3:
        textfile_out = argv[2]
        textoutp = open(textfile_out, 'w')
    
    for line in preprocess():
        print(line, end='', file=textoutp)

    exit()
