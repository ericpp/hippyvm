from hippy.objects.base import W_Root


class W_NullObject(W_Root):
    def is_true(self, space):
        return False

    def as_number(self, space):
        return space.wrap(0)

    def as_string(self, space):
        return space.newstrconst("")

    def eq_w(self, space, other):
        return True

    def var_dump(self, space, indent, recursion):
        space.ec.writestr("%sNULL\n" % indent)

    def abs(self, space):
        return 0
