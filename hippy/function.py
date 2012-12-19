
from hippy.builtin import AbstractFunction, ArgumentError
from hippy.interpreter import Frame
from hippy import consts
from hippy.objects.reference import W_Reference
from pypy.rlib import jit

class Function(AbstractFunction):
    _immutable_fields_ = ['args[*]', 'bytecode']
    
    def __init__(self, args, bytecode):
        self.args = args
        self.bytecode = bytecode

    @jit.unroll_safe
    def call(self, space, parent_frame, args_w):
        bc = self.bytecode
        frame = Frame(space, bc)
        #args_to_invalidate = [None] * len(self.args)
        for i in range(len(self.args)):
            tp, name, w_def_arg = self.args[i]
            if i >= len(args_w):
                if tp != consts.ARG_DEFAULT:
                    raise ArgumentError
                w_arg = w_def_arg
            else:
                w_arg = args_w[i]
                if tp == consts.ARG_REFERENCE:
                    assert isinstance(w_arg, W_Reference)
                    frame.vars_w[i] = w_arg
                    continue
            w_ref = frame.vars_w[i]
            assert isinstance(w_ref, W_Reference)
            w_ref.w_value = w_arg.deref()
        #try:
        return space.ec.interpreter.interpret(space, frame, self.bytecode)
        #finally:
        #    for w_arg in args_to_invalidate:
        #        if w_arg is not None:
        #            w_arg.mark_invalid()
