
from hippy.builtin import AbstractFunction, ArgumentError
from hippy.interpreter import Frame
from hippy import consts
from hippy.objects.reference import W_Reference, W_Cell
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
        args_to_invalidate = [None] * len(self.args)
        for i in range(len(self.args)):
            tp, name, def_arg = self.args[i]
            if i >= len(args_w) and tp != consts.ARG_DEFAULT:
                raise ArgumentError
            if tp == consts.ARG_ARGUMENT:
                w_arg = frame.store_var_by_name(space, bc, name,
                                                args_w[i].deref_for_store())
                args_to_invalidate[i] = w_arg
            elif tp == consts.ARG_REFERENCE:
                w_arg = parent_frame.upgrade_to_cell(args_w[i])
                frame.vars_w[bc.lookup_var_pos(name)] = W_Cell(W_Reference(
                    w_arg))
            elif tp == consts.ARG_DEFAULT:
                if i >= len(args_w):
                    arg_to_store = def_arg.copy(space)
                else:
                    arg_to_store = args_w[i].deref_for_store()
                w_arg = frame.store_var_by_name(space, bc, name, arg_to_store)
                args_to_invalidate[i] = w_arg
            else:
                raise Exception("wrong argument spec")
        try:
            return space.ec.interpreter.interpret(space, frame, self.bytecode)
        finally:
            for w_arg in args_to_invalidate:
                if w_arg is not None:
                    w_arg.mark_invalid()
