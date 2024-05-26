#!/usr/bin/env python3

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
            if t <= max_number: yield (t,)
            return

        while m*2 <= t:
            for x in _recursor(i-1, t-m, m):
                yield (m,) + x
            m += 1

    yield from _recursor()



if __name__ == '__main__':
    import sys
    from itertools import permutations
    for x in share(*[int(x) for x in sys.argv[1:5]]):
        seen = set()
        for p in permutations(x):
            seen.add(p)
        for p in seen:
            print(" ".join(str(i) for i in p))

