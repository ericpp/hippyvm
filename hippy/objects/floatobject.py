
from hippy.objects.base import W_Root
from hippy.objects.support import _new_binop
from hippy.consts import BINOP_LIST, BINOP_COMPARISON_LIST

class W_FloatObject(W_Root):
    _immutable_fields_ = ['floatval']
    
    def __init__(self, floatval):
        self.floatval = floatval

    def copy(self, space):
        return self # immutable object

    def as_number(self, space):
        return self

    def as_string(self, space):
        s = str(self.floatval)
        if s.endswith('.0'):
            i = len(s) - 2
            assert i >= 0
            s = s[:i]
        return space.newstrconst(s)

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

    def __repr__(self):
        return 'W_FloatObject(%s)' % self.floatval

# floats have no shifts
for _name in [i for i in BINOP_LIST if i not in ['lshift', 'rshift', 'mod',
                                                 'or_']]:
    setattr(W_FloatObject, _name, _new_binop(W_FloatObject, _name,
                                             'floatval',
                                             _name in BINOP_COMPARISON_LIST))
