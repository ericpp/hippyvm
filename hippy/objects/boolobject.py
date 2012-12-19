
from hippy.objects.base import W_Root

class W_BoolObject(W_Root):
    _immutable_fields_ = ['boolval']

    def __init__(self, boolval):
        self.boolval = boolval

    def is_true(self, space):
        return self.boolval

    def as_string(self, space):
        if self.boolval:
            return space.newstrconst('1')
        return space.newstrconst('')

    def as_number(self, space):
        return space.newint(int(self.boolval))

    def eq_w(self, space, w_other):
        assert isinstance(w_other, W_BoolObject)
        return self is w_other

    def __repr__(self):
        return 'W_BoolObject(%s)' % self.boolval

    def tostring(self):
        # XXX quick hack, should go via coerce, but we don't have actual strings
        return str(int(self.boolval))

    def var_dump(self, space, indent, recursion):
        if self.boolval:
            s = '%sbool(true)\n' % indent
        else:
            s = '%sbool(false)\n' % indent
        space.ec.writestr(s)

    def eq_w(self, space, w_other):
        assert isinstance(w_other, W_BoolObject)
        return self.boolval == w_other.boolval

    def as_number(self, space):
        return space.newint(0)

    def abs(self, space):
        return abs(self.boolval)
