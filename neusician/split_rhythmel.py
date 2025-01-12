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

def get_segment_separator(segmentlen, chainlen=0, measurelen=0, offset=0):

    lencounter = 0
    chainsegs = 0
    measuresegs = 0

    if chainlen == 0 and measurelen:
        chainlen = 1

    next_space = False

    def segment_sep(m=None):
        nonlocal lencounter, chainsegs, measuresegs, next_space
        if m is None:
            nonlocal segmentlen
            segmentlen -= lencounter
            if segmentlen > 0:
                return (" " if next_space else "") + segmentlen * "."
            else: return ""
        try:
            lencounter += len(match := m.group(0))
        except AttributeError:
            lencounter += m
            match = ""
        space = " " if next_space else ""
        if chainlen and chainsegs >= chainlen:
            times, chainsegs = divmod(chainsegs, chainlen)
            measuresegs += times
            if space: space = ", "
        if measurelen and measuresegs >= measurelen:
            measuresegs = 0
            if space: space = " | " + f".{segmentlen*chainlen}, " * chainsegs
        if segmentlen and lencounter >= segmentlen:
            if match: next_space = True
            times, lencounter = divmod(lencounter, segmentlen)
            chainsegs += times
        else:
            next_space = False
        return space + match

    if offset:
        if offset < 0:
            offset %= segmentlen * chainlen * measurelen
        segment_sep(offset)

    return segment_sep


def intdigester(intgr, div):
    x = intgr
    rems = []
    while x:
        x, remainder = divmod(x, div)
        rems.insert(0, remainder)
    return rems

def melody_from_nary(intgr, up, base=0, down=None, central_share=0):
    if down is None:
        down = up
    rems = intdigester(intgr, down + up + central_share + base)
    melodybits = []
    for r in rems:
        r -= central_share
        if r < 0:
            melodybits.append("=")
            continue
        r -= down
        melodybits.append(
                       '' if base >= r >= 0 else
           (r-base) * '+' if r > 0 else
             abs(r) * '-'
        )
    return melodybits

def from_trinary(
        intgr, segmentlen=None, melody=None, base=None, up=None, down=None,
        central=None, cycle_offset=0, tick_offset=0
    ):
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
    if segmentlen is not None:
        if isinstance(segmentlen, (tuple, list, str)):
            if len(segmentlen) > 2:
                segmentlen, chainlen, measurelen = (int(s) for s in segmentlen)
            elif len(segmentlen) == 2:
                segmentlen = int(segmentlen[0])
                chainlen = int(segmentlen[1])
                measurelen = 0
        else:
            segmentlen = int(segmentlen)
            chainlen = 0
            measurelen = 0
        if segmentlen > 0:
            segment_sep = get_segment_separator(segmentlen, chainlen, measurelen, tick_offset)
            string = re.sub(r"\.|o_*", segment_sep, string) + segment_sep()
    if melody or up or down:
        if isinstance(melody, str) and ':' in melody:
            props, intgr = melody.split(':')
        else:
            props = None
        if props and (
            m := re.match(r"(\d)(?:,(\d))?(?:-(\d))?(?:\+(\d))?", props)
        ):
            up = m.group(1)
            if up is not None:
                up = int(up)
            down = m.group(2)
            if down is not None:
                down = int(down)
            central = int(m.group(3) or 0) 
            cycle_offset = int(m.group(4) or 0)
        c = cycle(melody_from_nary(
            int(melody or intgr), up, base, down, central)
        )
        for _ in range(cycle_offset): next(c)
        melody_diff = 0
        def get_next(m):
            nonlocal melody_diff
            if m.group(0) != 'o': return f'{melody_diff:+d} '
            mel = next(c)
            if not len(mel): return mel
            if mel[0] == '=':
                melody_diff = 0
            elif mel[0] == '+':
                melody_diff += mel.count('+')
            elif mel[0] == '-':
                melody_diff -= mel.count('-')
            else:
                raise RuntimeError("note diff not in =, + or -")
            return mel
        string = re.sub(r'o|[\|,] ', lambda m: m.group(0) + get_next(m), string)
    return re.sub(r'([.+_-])\1{2,}',
        lambda m: m.group(1) + str(len(m.group(0))), string
    )

