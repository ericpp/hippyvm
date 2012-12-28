from hippy.objects.base import W_Root
from pypy.rlib import jit


class W_StrInterpolation(W_Root):
    _immutable_fields_ = ['strings[*]', 'var_nums[*]']
    
    def __init__(self, strings, var_nums):
        self.strings = strings
        self.var_nums = var_nums
        assert len(var_nums) == len(strings) - 1

    @jit.unroll_safe
    def interpolate(self, space, frame, bytecode):
        # XXX mutable string support, can be made faster, by using write_into
        #     instead of casting to immutable string
        r = [self.strings[0]]
        for i in range(len(self.var_nums)):
            r.append(space.str_w(space.as_string(
                frame.load_fast(self.var_nums[i]))))
            r.append(self.strings[i + 1])
        return space.newstrconst(''.join(r))
