import sys
from pypy.rlib import jit
from pypy.rlib.rarithmetic import ovfcheck
from hippy.objects.base import W_Root
from hippy.objects.support import _new_binop
from hippy.consts import BINOP_LIST, BINOP_COMPARISON_LIST

SYS_MAXINT_PLUS_1  = float(sys.maxint+1)
SYS_MININT_MINUS_1 = float(-sys.maxint-2)

@jit.elidable
def hash_int(v, l=[0]*20):
    """The algorithm behind compute_hash() for a string or a unicode."""
    from pypy.rlib.rarithmetic import intmask
    i = 0
    while v:
        l[i] = (v % 10) + ord('0')
        v /= 10
        i += 1
    x = l[i - 1] << 7
    for k in range(i - 1, -1, -1):
        x = intmask((1000003*x) ^ l[k])
    x ^= i
    return intmask(x)

class W_IntObject(W_Root):
    _immutable_fields_ = ['intval']

    def __init__(self, intval):
        self.intval = intval

    def int_w(self, space):
        return self.intval

    def as_number(self, space):
        return self

    def as_string(self, space):
        return space.newstr(str(self.intval))

    def coerce(self, space, tp):
        if tp == space.tp_int:
            return self
        elif tp == space.tp_float:
            return space.newfloat(float(self.intval))
        raise NotImplementedError

    def div(self, space, w_other):
        assert isinstance(w_other, W_IntObject)
        x = self.intval
        y = w_other.intval
        try:
            z = ovfcheck(x % y)
        except OverflowError:
            z = 1
        if z == 0:
            return space.newint(x / y)
        else:
            return space.newfloat(float(x) / float(y))

    def mod(self, space, w_other):
        assert isinstance(w_other, W_IntObject)
        x = self.intval
        y = w_other.intval
        if y < 0:
            y = -y
        z = x % y
        if x < 0:
            z = -z
        return space.newint(z)

    def is_true(self, space):
        return self.intval != 0

    def uplus(self, space):
        return self

    def uminus(self, space):
        return space.newint(-self.intval)

    def uplusplus(self, space):
        try:
            v = ovfcheck(self.intval + 1)
        except OverflowError:
            return space.newfloat(SYS_MAXINT_PLUS_1)
        return space.newint(v)

    def uminusminus(self, space):
        try:
            v = ovfcheck(self.intval - 1)
        except OverflowError:
            return space.newfloat(SYS_MININT_MINUS_1)
        return space.newint(v)

    def eq_w(self, space, w_other):
        assert isinstance(w_other, W_IntObject)
        return self.intval == w_other.intval

    def hash(self, space):
        return hash_int(self.intval)

    def __repr__(self):
        return 'W_IntObject(%s)' % self.intval

    def var_dump(self, space, indent, recursion):
        space.ec.writestr('%sint(%d)\n' % (indent, self.intval))

    def abs(self, space):
        return abs(self.intval)

for _name in BINOP_LIST:
    if hasattr(W_IntObject, _name):
        continue
    setattr(W_IntObject, _name, _new_binop(W_IntObject, _name,
                                           'intval',
                                           _name in BINOP_COMPARISON_LIST))
