
from hippy.objects.base import W_Root

class W_BoolObject(W_Root):
    _immutable_fields_ = ['boolval']

    def __init__(self, boolval):
        self.boolval = boolval

    def copy(self, space):
        return self # immutable object

    def is_true(self, space):
        return self.boolval

    def as_string(self, space):
        if self.boolval:
            return space.newstrconst('1')
        return space.newstrconst('')

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
