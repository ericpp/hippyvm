import sys
from hippy.objects.base import W_Root
from hippy.objects.support import _new_binop
from hippy.consts import BINOP_LIST, BINOP_COMPARISON_LIST
from pypy.rlib.rarithmetic import intmask
from pypy.rlib.rfloat import isnan


class W_FloatObject(W_Root):
    _immutable_fields_ = ['floatval']

    def __init__(self, floatval):
        self.floatval = floatval

    def _truncate(self, space):
        return space.wrap(int(self.floatval))

    def as_number(self, space):
        return self

    def _as_str(self):
        s = str(self.floatval)
        if s.endswith('.0'):
            i = len(s) - 2
            assert i >= 0
            s = s[:i]
        return s

    def as_string(self, space):
        return space.newstr(self._as_str())

    def int_w(self, space):
        if isnan(self.floatval):
            result = -sys.maxint-1
            space.ec.hippy_warn("cast float to integer: NaN"
                                " is returned as %d" % result)
            return result
        try:
            result = intmask(int(self.floatval))
        except OverflowError:
            result = 0    # +/- infinity
        if result != self.floatval:
            space.ec.hippy_warn("cast float to integer: value %s overflows"
                                " and is returned as %d" % (self._as_str(),
                                                            result))
        return result

    def coerce(self, space, tp):
        if tp == space.tp_float:
            return self
        raise NotImplementedError

    def float_w(self, space):
        return self.floatval

    def is_true(self, space):
        return self.floatval != 0.0

    def uplus(self, space):
        return self

    def uminus(self, space):
        return space.newfloat(-self.floatval)

    def uplusplus(self, space):
        return space.newfloat(self.floatval + 1)

    def uminusminus(self, space):
        return space.newfloat(self.floatval - 1)

    def eq_w(self, space, w_other):
        assert isinstance(w_other, W_FloatObject)
        return self.floatval == w_other.floatval

    def mod(self, space, w_other):
        assert isinstance(w_other, W_FloatObject)
        return self._truncate(space).mod(space, w_other._truncate(space))

    def lshift(self, space, w_other):
        assert isinstance(w_other, W_FloatObject)
        return self._truncate(space).lshift(space, w_other._truncate(space))

    def rshift(self, space, w_other):
        assert isinstance(w_other, W_FloatObject)
        return self._truncate(space).rshift(space, w_other._truncate(space))

    def or_(self, space, w_other):
        assert isinstance(w_other, W_FloatObject)
        return self._truncate(space).or_(space, w_other._truncate(space))

    def and_(self, space, w_other):
        assert isinstance(w_other, W_FloatObject)
        return self._truncate(space).and_(space, w_other._truncate(space))

    def __repr__(self):
        return 'W_FloatObject(%r)' % self.floatval

    def var_dump(self, space, indent, recursion):
        space.ec.writestr('%sfloat(%s)\n' % (indent, self._as_str()))

    def abs(self, space):
        return abs(self.floatval)


for _name in BINOP_LIST:
    if hasattr(W_FloatObject, _name):
        continue
    setattr(W_FloatObject, _name, _new_binop(W_FloatObject, _name,
                                             'floatval',
                                             _name in BINOP_COMPARISON_LIST))
