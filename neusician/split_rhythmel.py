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

def rhythm_from_trinary(intgr):
    x = intgr
    rems = []
    while x:
        x, remainder = divmod(x, 3)
        rems.insert(0, str(remainder))
    print(*rems)
    last = '3'
    offset = 0
    length = 0
    tones = []
    for r in rems:
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
    return "".join(translated)

