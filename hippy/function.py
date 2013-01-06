
from hippy.builtin import AbstractFunction
from hippy.interpreter import Frame
from hippy import consts
from hippy.objects.reference import W_Reference
from pypy.rlib import jit

class Function(AbstractFunction):
    _immutable_fields_ = ['tp[*]', 'names[*]',
                          'defaults_w[*]', 'bytecode']

    def __init__(self, args, bytecode):
        self.tp         = [tp    for tp, name, w_def in args]
        self.names      = [name  for tp, name, w_def in args]
        self.defaults_w = [w_def for tp, name, w_def in args]
        self.bytecode   = bytecode

    def get_name(self):
        return self.bytecode.name

    def argument_is_byref(self, i):
        assert i >= 0
        return i < len(self.tp) and self.tp[i] == consts.ARG_REFERENCE

    def prepare_argument(self, space, i, w_argument):
        if self.argument_is_byref(i):
            # must receive a reference
            if not isinstance(w_argument, W_Reference):
                raise space.ec.fatal("Argument %d for %d() must be a variable"
                                     % (i+1, self.get_name()))
        else:
            # dereference the argument
            w_argument = w_argument.deref()
        return w_argument

    @jit.unroll_safe
    def call(self, space, parent_frame, nb_args):
        newframe = Frame(space, self.bytecode)
        # XXX warn if too many arguments and this function does not call
        # func_get_arg() & friends
        for i in range(len(self.tp)):
            if i < nb_args:
                # this argument was provided; fetch it from parent_frame
                w_argument = parent_frame.peek_nth(nb_args - i - 1)
                if self.tp[i] == consts.ARG_REFERENCE:
                    newframe.store_fast_ref(i, w_argument)
                    continue
            else:
                # this argument is missing; pick the default
                w_argument = self.defaults_w[i]
                if w_argument is None:
                    space.ec.warn("Missing argument %d for %s()"
                                  % (i+1, self.get_name()))
                    w_argument = space.w_Null
            w_ref = newframe.load_fast(i)
            w_ref.w_value = w_argument
        return space.ec.interpreter.interpret(space, newframe, self.bytecode)

    @jit.unroll_safe
    def call_args(self, space, args_w):
        # XXX warn if too many arguments and this function does not call
        # func_get_arg() & friends
        newframe = Frame(space, self.bytecode)
        nb_args = len(args_w)
        for i in range(len(self.tp)):
            if i < nb_args:
                # this argument was provided; fetch it from parent_frame
                w_argument = args_w[i]
            else:
                # this argument is missing; pick the default
                w_argument = self.defaults_w[i]
                if w_argument is None:
                    space.ec.warn("Missing argument %d for %s()"
                                  % (i+1, self.get_name()))
                    w_argument = space.w_Null
            w_ref = newframe.load_fast(i)
            w_ref.w_value = w_argument
        return space.ec.interpreter.interpret(space, newframe, self.bytecode)
        
