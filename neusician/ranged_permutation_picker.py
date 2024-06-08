#!/usr/bin/env python3
from collections import Counter
from math import factorial

def share(items, total, min_number=0, max_number=None):
    """ Distribute numbers in min_number<=x<=max_number
        so that they sum up to total and are sorted in
        ascending order. Items indicates how many items
        are to be returned.
        Example:
        >>> it = share(5, 13, 1)
        >>> next(it) == (1, 1, 1, 1, 9)
        >>> next(it) == (1, 1, 1, 2, 8)
        >>> next(it) == (1, 1, 1, 3, 7)
        >>> next(it) == (1, 1, 1, 4, 6)
        >>> next(it) == (1, 1, 1, 5, 5)
        >>> next(it) == (1, 1, 2, 2, 7) 
        >>> next(it) == (1, 1, 2, 3, 6)
        >>> next(it) == (1, 1, 2, 4, 5)
        >>> next(it) == (1, 1, 3, 3, 5)
        >>> next(it) == (1, 1, 3, 4, 4)
        >>> next(it) == (1, 2, 2, 2, 6)
        >>> next(it) == (1, 2, 2, 3, 5)
        >>> next(it) == (1, 2, 2, 4, 4)
        >>> next(it) == (1, 2, 3, 3, 4)
        >>> next(it) == (2, 2, 3, 3, 3)
        >>> next(it) raises StopIteration
    """

    if min_number>0 and items > total//min_number:
        raise ValueError(
            f"Cannot distribute {total} on {items} positions "
            f"because each must be at least {min_number}."
        )

    if max_number is not None and items < total/max_number:
        raise ValueError(
            f"Cannot distribute {total} on {items} positions "
            f"because each may not exceed maximum {max_number}."
        )

    def _recursor(i=items, t=total, m=min_number):

        if i == 1:
            if t <= (max_number or t): yield (t,)
            return

        while m*2 <= t:
            for x in _recursor(i-1, t-m, m):
                yield (m,) + x
            m += 1

    yield from _recursor()


class RangedPermutationPicker:

    def __init__(self, items, total, minimum=0, maximum=None):
        self.items = items
        self.total = total
        self.minimum = minimum
        self.maximum = maximum
        self.sets = []
        permutations = 0
        for s in share(items, total, minimum, maximum):
            s = SequencePicker(s)
            permutations += s.permutations
            self.sets.append(s)
        self.permutations = permutations

    def sequence_at_index(self, index_position):
        index = index_position
        for s in self.sets:
            if index < s.permutations:
                break
            else:
                index -= s.permutations
        else:
            raise ValueError(
                    f"There is no permutated sequence #{index_position}, "
                    f"with the arguments passed only {self.permutations} "
                    "are available"
                )
        return s.sequence_at_index(index)


class SequencePicker():
    def __init__(self, orig_sequence):
        self.counter = Counter(orig_sequence)
        reps = 1
        for v in self.counter.values():
            reps *= factorial(v)
        self.permutations = factorial(self.counter.total()) // reps

    def sequence_at_index(self, index):
        counter = self.counter.copy()
        sequence = []
        while counter:
            minuend = 0
            for element, count in counter.items():
                if count == 0:
                    continue
                counter[element] -= 1
                reps = 1
                for v in counter.values():
                    reps *= factorial(v)
                permutations = factorial(counter.total()) // reps
                counter[element] += 1
                if index < permutations + minuend:
                    break
                else:
                    minuend += permutations
            index -= minuend
            counter[element] -= 1
            if counter[element] == 0:
                del counter[element]
            sequence.append(element)
        return tuple(sequence)


if __name__ == '__main__':
    import sys
    args = [int(x) for x in sys.argv[1:6]]
    rpp = RangedPermutationPicker(*args[0:4])
    print(
        f"At the index #{args[4]} you will find sequence: ",
        rpp.sequence_at_index(args[4])
    )
    from itertools import permutations
    i = 0
    for x in share(*args[0:4]):
        seen = set()
        counter = Counter((i for i in x))
        reps = 1
        for v in counter.values():
            reps *= factorial(v)
        print("#", " ".join(str(i) for i in x),
              "=", ", ".join(f"{n}*{i}" for i, n in counter.items()),
              "=>", str(factorial(counter.total()) // reps)
              ) 
        for p in permutations(x):
            seen.add(p)
        for p in sorted(seen):
            print(f"{i}.", " ".join(str(i) for i in p))
            i += 1
