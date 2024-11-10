import re
from itertools import cycle

rhythm_pattern = '1(2:111)21'

class Pattern:

    def __init__(self, segments):
        pats = []
        cumlength = 0
        for pat in segments:
            if isinstance(pat, Pattern):
                pats.append(pat)
                cumlength += pat.cumlength
            else:
                subpats = re.sub(r"(?<=\d)", "|", pat).split("|")
                subpats[-1], _cumlen = subpats[-1].split(':')
                cumlength += int(_cumlen)
                subpats = map(int, subpats)
                self.orig_cumlength = sum(abs(x) for x in subpats)
        self.subpatterns = pats
        self.cumlength = cumlength

        
def deserialize(pattern):

    def partition(string):
        try:
            head, direction, tail = re.split("([\(\)])", 1)
            return head, direction, tail
        except ValueError:
            return head, '', ''
    
    stack = [[]]
    
    while pattern:
        head, direction, pattern = partition(pattern)
        stack[-1].append(head)
        if direction == '(':
            stack.append([])
        elif direction == ')':
            pat = Pattern(stack.pop(-1))
            stack[-1].append(pat)
    
        return stack[0]

def intdigester(intgr, div):
    x = intgr
    rems = []
    while x:
        x, remainder = divmod(x, div)
        rems.insert(0, remainder)
    return rems

def melody_from_nary(intgr, up, down=None, central_share=0, offset=0):
    if down is None:
        down = up
    rems = intdigester(intgr, down + up + central_share + 1)
    melodybits = []
    for r in rems:
        r -= central_share
        if r < 0:
            melodybits.append("=")
            continue
        r -= down
        melodybits.append(
            '' if r == 0 else r * '+' if r > 0 else abs(r) * '-'
        )
    return melodybits

def from_trinary(intgr, segmentlen=None, melody=None):
    rems = intdigester(intgr, 3)
    last = '3'
    offset = 0
    length = 0
    tones = []
    for r in rems:
        r = str(r)
        if last == '2':
            if r in'12':
                offset += 1
            elif r == '0':
                length = 0
        if r in '12' and last in '01':
            tones.append((offset, max(length, 1)))
            offset = 0
        if r == '2':
            offset += 1
            length = 0
            last = r
            continue
        elif r == '1':
            length = 1
        elif r == '0':
            length += 1
        last = r
    tones.append((offset, length))
    translated = []
    for pause, length in tones:
        pause = pause * '.'
        ext = length - 1
        if ext < 0:
            ext = ''
        else:
            ext = 'o' + ext * '_'
        translated.append(f"{pause}{ext}")
    string = "".join(translated)
    if segmentlen:
        segmentlen = int(segmentlen)
        lencounter = 0
        next_space = False
        def segment_sep(m):
            nonlocal lencounter, next_space
            lencounter += len(m.group(0))
            space = " " if next_space else ""
            if lencounter >= segmentlen:
                next_space = True
                lencounter %= segmentlen
            else:
                next_space = False
            return space + m.group(0)
        string = re.sub(r"\.|o_*", segment_sep, string)
        segmentlen -= lencounter
        if segmentlen > 0:
            string = string + " " + segmentlen * "."
    if melody:
        if ':' in melody:
            props, intgr = melody.split(':')
        else:
            props = melody
        if (m := re.match(r"(\d)(?:,(\d))?(?:-(\d))?(?:\+(\d))?", props)):
            up = m.group(1)
            if up is not None:
                up = int(up)
            down = m.group(2)
            if down is not None:
                down = int(down)
            central_share = int(m.group(3) or 0) 
            offset = int(m.group(4) or 0)
        c = cycle(melody_from_nary(
            int(intgr), up, down, central_share, offset)
        )
        for _ in range(offset): next(c)
        string = re.sub(r'(?<=o)', lambda m: next(c), string)
    return re.sub(r'([.+_-])\1{2,}',
        lambda m: m.group(1) + str(len(m.group(0))), string
    )

