
from pypy.rlib import jit
from hippy.objects.base import W_Root
from hippy.objects.support import _new_binop
from hippy.consts import BINOP_LIST, BINOP_COMPARISON_LIST

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

    def is_valid_number(self, space):
        return True

    def copy(self, space):
        return self # immutable object

    def as_number(self, space):
        return self

    def as_string(self, space):
        return space.newstrconst(str(self.intval))

    def coerce(self, space, tp):
        if tp == space.w_int:
            return self
        elif tp == space.w_float:
            return space.newfloat(float(self.intval))
        raise NotImplementedError

    def div(self, space, w_other):
        assert isinstance(w_other, W_IntObject)
        return space.newfloat(float(self.intval) / float(w_other.intval))

    def is_true(self, space):
        return self.intval != 0

    def float_w(self, space):
        return float(self.intval)

    def uplus(self, space):
        return self

    def uminus(self, space):
        return space.newint(-self.intval)

    def uplusplus(self, space):
        return space.newint(self.intval + 1)

    def uminusminus(self, space):
        return space.newint(self.intval - 1)

    def eq_w(self, space, w_other):
        assert isinstance(w_other, W_IntObject)
        return self.intval == w_other.intval

    def hash(self):
        return hash_int(self.intval)

    def __repr__(self):
        return 'W_IntObject(%s)' % self.intval

for _name in [i for i in BINOP_LIST if i != 'div']: # div returns floats
    setattr(W_IntObject, _name, _new_binop(W_IntObject, _name,
                                           'intval',
                                           _name in BINOP_COMPARISON_LIST))
