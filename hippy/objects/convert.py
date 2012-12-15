from pypy.rlib.rarithmetic import intmask


def _whitespaces_in_front(s):
    i = 0
    while i < len(s):
        if s[i].isspace():
            i += 1
        else:
            break
    return i

def nextchr(s, i):
    if i < len(s):
        return s[i]
    else:
        return '\0'

_OVERFLOWED = 1<<20

def _convert_hexadecimal(space, s, i):
    value_int = 0
    value_float = 0.0
    fully_processed = False
    while True:
        c = nextchr(s, i)
        if '0' <= c <= '9':
            digit = ord(c) - ord('0')
        elif 'A' <= c <= 'F':
            digit = ord(c) - ord('A') + 10
        elif 'a' <= c <= 'f':
            digit = ord(c) - ord('a') + 10
        else:
            break
        value_int = intmask((value_int * 16) + digit)
        value_float = (value_float * 16.0) + digit
        fully_processed = True
        i += 1
    fully_processed = fully_processed and i == len(s)
    if abs(value_int - value_float) < _OVERFLOWED:
        return space.newint(value_int), fully_processed
    else:    # overflowed at some point
        return space.newfloat(value_float), fully_processed

def convert_string_to_number(space, s):
    """Returns (wrapped number, flag: number-fully-processed)."""

    i = _whitespaces_in_front(s)
    forced_float = False
    negative_sign = False
    at_least_one_digit = False

    if nextchr(s, i) == '-':
        negative_sign = True
        i += 1
    elif nextchr(s, i) == '+':
        i += 1
    elif nextchr(s, i) == '0' and nextchr(s, i + 1) in 'xX':
        return _convert_hexadecimal(space, s, i + 2)

    value_int = 0
    value_float = 0.0
    while nextchr(s, i).isdigit():
        digit = ord(s[i]) - ord('0')
        value_int = intmask((value_int * 10) + digit)
        value_float = (value_float * 10.0) + digit
        at_least_one_digit = True
        i += 1

    if nextchr(s, i) == '.':
        i += 1
        fraction = 1.0
        while nextchr(s, i).isdigit():
            digit = ord(s[i]) - ord('0')
            fraction *= 0.1
            value_float += fraction * digit
            at_least_one_digit = True
            i += 1
        forced_float |= at_least_one_digit

    if nextchr(s, i) in 'Ee' and at_least_one_digit:
        at_least_one_digit = False
        negative_exponent = False
        i += 1
        if nextchr(s, i) == '-':
            negative_exponent = True
            i += 1
        elif nextchr(s, i) == '+':
            i += 1

        exponent = 0
        while nextchr(s, i).isdigit():
            digit = ord(s[i]) - ord('0')
            exponent = exponent * 10 + digit
            if exponent > 99999:
                exponent = 99999    # exponent is huge enough already
            at_least_one_digit = True
            i += 1

        if negative_exponent:
            exponent = -exponent
        value_float *= (10.0 ** exponent)
        forced_float |= at_least_one_digit

    if negative_sign:
        value_int = intmask(-value_int)
        value_float = -value_float

    fully_processed = at_least_one_digit and i == len(s)
    if forced_float or abs(value_int - value_float) > _OVERFLOWED:
        return space.newfloat(value_float), fully_processed
    else:
        return space.newint(value_int), fully_processed
