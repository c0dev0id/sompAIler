import re

def markov_sensible_tone_getter(model):

    mel_interv, *nets = re.split(r",(?![-\d])", model)
    mel_interv = [ int(i) for i in mel_interv.split(",") ]
    markov_probs_intervals = {}

    def flat(chain):
        for i in chain:
            if isinstance(i, tuple):
                yield from flat(i)
            else:
                yield i

    max_pathlen = 0

    for net in nets:
        paths, probs = re.split(r":(?=\d)", net, 1)
        probs = [ int(i) for i in probs.split(",") ]
        multipath = parse_model(paths)
        for markov_chain in markov_evolutions_iter_from(multipath):
            path = tuple(flat(markov_chain))
            max_pathlen = max(max_pathlen, len(path))
            markov_probs_intervals[path] = probs

    lenbased_probs_intervals = []
    for _ in range(max_pathlen):
        lenbased_probs_intervals.append({})

    for path, probs in markov_probs_intervals.items():
        lenbased_probs_intervals[len(path)-1][path] = probs

    singles = list(i[0] for i in lenbased_probs_intervals[0])
    lastpos = 0
    octave = 4
    tones = [singles[0]]

    def cursor(diff):
        nonlocal lastpos, octave
        curpos = (lastpos + diff) % len(singles)
        if (lastpos + diff) < 0:
            octave -= 1
        elif (lastpos + diff) // len(singles):
            octave += 1
        tones.append(singles[curpos])
        lastpos = curpos
        return singles[curpos] + str(octave)

    def advancer():

        big_number = yield

        while True:
            for l in range(max_pathlen):
                try:
                    tail = tuple(tones[l-max_pathlen:])
                except IndexError:
                    continue

                try:
                    probs = lenbased_probs_intervals[-l-1][tail]
                except KeyError:
                    continue
                else:
                    big_number, remainder = divmod(big_number, sum(probs))
                    pos = -1
                    while remainder > 0:
                        pos += 1
                        remainder -= probs[pos]
                    big_number = yield big_number, cursor(mel_interv[pos])
                    break

    return lenbased_probs_intervals, advancer()


def parse_model(paths):

    def parse_clause(clause):
        stack = []
        for variant in clause.split(":"):
            if '-' in variant:
                adjnotes = []
                for note in variant.split("-"):
                    adjnotes.append(note)
                stack.append(adjnotes)
            else:
                stack.append(variant)
        return stack
    
    lstack = []
    stack = [lstack]
    after_close = False
    
    def wrap_in_tail(last, merge):
    
        lstack = stack[-1]
        last2 = lstack[-1]
        if len(last) and not(merge or isinstance(last, list)):
            last = [last]
    
        if last2 == '':
            if len(last):
                lstack[-1] = [last]
            else:
                lstack[-1] = []
            return lstack[-1]
        elif len(last) and not isinstance(last2, list):
            lstack[-1] = [last2]
    
        if len(last):
            if merge:
                lstack[-1].extend(last)
            else:
                lstack[-1].append(last)
    
        return lstack
    
    while paths:
        if '[' in paths or ']' in paths:
            phrase_before, sqbr, paths = re.split(r"([\[\]])", paths, 1)
    
            clause = parse_clause(phrase_before)
    
            if after_close:
                last, *clause = clause
                lstack = wrap_in_tail(last, True)
    
            lstack.extend(clause)
    
            if sqbr == '[':
                stack.append([])
                after_close = False
    
            else:
                lstack = wrap_in_tail(stack.pop(-1), False)
                after_close = True
        else:
            clause = parse_clause(paths)
            paths = ''
            if after_close:
                last, *clause = clause
                lstack = wrap_in_tail(last, True)
                after_close = False
            lstack.extend(clause)
    
        lstack = stack[-1]

    return lstack


def markov_chain(markov_list):

    iterators = []

    def my_iter(iterable):
        while True:
            it = iter(iterable)
            yield from it
            yield None

    for item in markov_list:
        if isinstance(item, list):
            iterators.append(
                my_iter(list(markov_evolutions_iter_from(item)))
            )
        else:
            iterators.append(my_iter([item]))

    ret = []
 
    while True:
        try:
            r = next(iterators[ len(ret) ])
            if r is None:
                ret.pop(-1)
                continue
            else:
                ret.append(r)
        except IndexError:
            if ret:
                yield tuple(ret)
                ret.pop(-1)
            else:
                break


def markov_evolutions_iter_from(markov_list):
    "Permute over every item and sub-item in markov_list"
    if not len(markov_list):
        return

    for i in markov_list:
        if isinstance(i, list):
            it = markov_chain(i)
            yield from it
        else:
            yield i


if __name__ == '__main__':
    # exit(main(
    #     "-7,-6,-5,-4,-3,-2,-1,0,1,2,3,4,5,6,7,"
    #     "C:83,23,56,76,92,96,88,76,79,85,86,72,48,33,65,D:100,77,52,30,35,42,95,123,90,82,75,62,78,82,98,"
    #     "E:45,16,23,15,29,44,59,76,67,53,49,37,25,56,62,F:13,12,17,15,14,19,30,21,25,15,19,17,16,23,26,"
    #     "G:55,42,33,24,32,39,46,55,51,45,37,31,39,42,36,39,A:83,7,20,12,15,23,19,92,19,12,14,17,23,29,97,"
    #     "H:1,0,0,0,0,0,0,0,15,0,0,0,0,0,1,"
    #     "C-E:D-F:C[D:E-F:G]A:A-E:[D-A:G]E-F-D:A[G:E[D:C-E]:F]:G-H-D:56,48,36,22,26,29,33,27,21,73,55,42,11,19,33"
    # ))
    exit(0)

