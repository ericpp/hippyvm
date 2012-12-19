from hippy.objects.base import W_Root
from pypy.rlib import jit


class W_StrInterpolation(W_Root):
    _immutable_fields_ = ['strings[*]', 'vars[*]']
    
    def __init__(self, strings, vars):
        self.strings = strings
        self.vars = vars
        assert len(vars) == len(strings) - 1

    @jit.unroll_safe
    def interpolate(self, space, frame, bytecode):
        # XXX mutable string support, can be made faster, by using write_into
        #     instead of casting to immutable string
        r = [self.strings[0]]
        for i in range(len(self.vars)):
            r.append(space.str_w(space.as_string(
                frame.load_var(space, bytecode, self.vars[i]))))
            r.append(self.strings[i + 1])
        return space.newstrconst(''.join(r))
