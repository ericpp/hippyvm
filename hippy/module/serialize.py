
""" Stolen from phpserialize by Armin Ronacher, BSD license.
"""

from hippy.error import InterpreterError

class SerializerError(InterpreterError):
    pass

class StreamIO(object):
    def __init__(self, s):
        self.pos = 0
        self.s = s

    def read(self, n):
        prev_pos = self.pos
        assert prev_pos >= 0
        self.pos += n
        stop = self.pos
        assert stop >= 0 # XXX why???
        return self.s[prev_pos:stop]

    def expect(self, e):
        got = self.read(len(e))
        if got != e:
            raise SerializerError("Got %s expected %s" % (got, e))

    def read_until(self, delim):
        start = self.pos
        assert start >= 0
        newpos = self.s.find(delim, start)
        if newpos < 0:
            raise SerializerError("unexpected end of stream")
        res = self.s[start:newpos]
        self.pos = newpos + len(delim)
        return res

def load_array(space, fp):
    items = int(fp.read_until(':'))
    fp.expect('{')
    result = []
    for idx in xrange(items):
        w_item = _unserialize(space, fp)
        w_value = _unserialize(space, fp)
        result.append((w_item, w_value))
    fp.expect('}')
    return space.new_array_from_pairs(result)

def _unserialize(space, fp):
    type_ = fp.read(1).lower()
    if type_ == 'n':
        fp.expect(';')
        return space.w_Null
    if type_ in 'idb':
        fp.expect(':')
        data = fp.read_until(';')
        if type_ == 'i':
            return space.wrap(int(data))
        if type_ == 'd':
            return space.wrap(float(data))
        return space.wrap(int(data) != 0)
    if type_ == 's':
        fp.expect(':')
        length = int(fp.read_until(':'))
        fp.expect('"')
        data = fp.read(length)
        fp.expect('"')
        fp.expect(';')
        return space.newstr(data)
    if type_ == 'a':
        fp.expect(':')
        return load_array(space, fp)
    raise ValueError('unexpected opcode %s' % type_)

def unserialize(space, s):    
    """Read a string from the open file object `fp` and interpret it as a
    data stream of PHP-serialized objects, reconstructing and returning
    the original object hierarchy.

    """
    return _unserialize(space, StreamIO(s))
