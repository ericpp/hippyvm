
from hippy.rpython.rdict import RDict
from hippy.consts import BYTECODE_NUM_ARGS, BYTECODE_NAMES,\
     BINOP_LIST, RETURN
from hippy.builtin import setup_builtin_functions, AbstractFunction
from hippy.error import InterpreterError
from hippy.objects.reference import W_Reference
from hippy.objects.base import W_Root
from hippy.objects.interpolate import W_StrInterpolation
from hippy.objects.arrayiter import W_BaseArrayIterator
from hippy.objects.arrayobject import new_rdict
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib import jit
from pypy.rlib.unroll import unrolling_iterable

import hippy.array_funcs     # side-effect of registering functions

def get_printable_location(pc, bytecode, interp):
    lineno = bytecode.bc_mapping[pc]
    return (bytecode.name + " " + str(lineno)
            + " " + BYTECODE_NAMES[ord(bytecode.code[pc])])

driver = jit.JitDriver(reds = ['frame'],
                       greens = ['pc', 'bytecode', 'self'],
                       virtualizables = ['frame'],
                       get_printable_location = get_printable_location,
                       should_unroll_one_iteration = lambda *args: True)

class Frame(object):
    """ Frame implementation. Note that vars_w stores references, while
    stack stores values (also references)
    """
    _virtualizable2_ = ['vars_w[*]', 'stack[*]', 'stackpos', 'f_backref',
                        'next_instr']

    is_global_level = False

    @jit.unroll_safe
    def __init__(self, space, code):
        self = jit.hint(self, fresh_virtualizable=True, access_directly=True)
        self.stack = [None] * code.stackdepth
        self.stackpos = 0
        self.bytecode = code # for the debugging
        self.next_instr = 0
        self.vars_w = [W_Reference(space.w_Null) for v in code.varnames]
        i = code.globals_var_num
        if i >= 0:
            self.vars_w[i].w_value = space.ec.interpreter.w_globals

    def push(self, w_v):
        stackpos = jit.hint(self.stackpos, promote=True)
        assert isinstance(w_v, W_Root) or w_v is None
        self.stack[stackpos] = w_v
        self.stackpos = stackpos + 1

    def pop(self):
        stackpos = jit.hint(self.stackpos, promote=True) - 1
        assert stackpos >= 0
        res = self.stack[stackpos]
        #if self.stack[stackpos] is not None:
        #    self.stack[stackpos].mark_invalid()
        self.stack[stackpos] = None # don't artificially keep alive stuff
        self.stackpos = stackpos
        return res

    def pop_n(self, count):
        stackpos = jit.hint(self.stackpos, promote=True) - count
        assert stackpos >= 0
        for i in range(count):
            self.stack[stackpos + i] = None
        self.stackpos = stackpos

    @jit.unroll_safe
    def clean(self, bytecode):
        return # XXX
        if not bytecode.uses_dict:
            for i in range(len(bytecode.varnames)):
                self.vars_w[i].mark_invalid()

    def peek(self):
        stackpos = jit.hint(self.stackpos, promote=True) - 1
        assert stackpos >= 0
        return self.stack[stackpos]

    def peek_nth(self, n):
        # peek() == peek_nth(0)
        stackpos = jit.hint(self.stackpos, promote=True) + ~n
        assert stackpos >= 0
        return self.stack[stackpos]

    def poke_nth(self, n, w_obj):
        stackpos = jit.hint(self.stackpos, promote=True) + ~n
        assert stackpos >= 0
        assert isinstance(w_obj, W_Root) or w_obj is None
        self.stack[stackpos] = w_obj

    def store_var(self, space, w_v, w_value):
        if not isinstance(w_v, W_Reference):
            raise InterpreterError(
                "Reference to something that's not a variable")
        else:
            w_v.w_value = w_value.deref()

    @jit.elidable
    def lookup_var_pos(self, name):
        return self.vars_dict[name]

    def load_fast(self, no):
        return self.vars_w[no]

    def store_fast_ref(self, no, w_ref):
        assert isinstance(w_ref, W_Reference)
        self.vars_w[no] = w_ref


class IllegalInstruction(InterpreterError):
    pass

class Interpreter(object):
    """ Interpreter keeps the state of the current run. There will be a new
    interpreter instance per run of script
    """
    def __init__(self, space, logger):
        self.functions = {}
        self.constants = {}
        self.globals = new_rdict()
        self.w_globals = space.new_array_from_rdict(self.globals)
        self.logger = logger
        self.setup_constants(space)
        self.setup_globals(space)
        setup_builtin_functions(self, space)
        space.ec.interpreter = self # one interpreter at a time
        self.topframeref = jit.vref_None

    def setup_constants(self, space):
        self.constants['true'] = space.w_True
        self.constants['false'] = space.w_False
        self.constants['null'] = space.w_Null

    def setup_globals(self, space):
        self.globals['GLOBALS'] = W_Reference(self.w_globals)

    #@jit.elidable -- XXX redo
    def lookup_global(self, space, name):
        try:
            return self.globals[name]
        except KeyError:
            new_glob = W_Reference(space.w_Null)
            self.globals[name] = new_glob
            return new_glob

    def update_global(self, space, name, w_ref):
        self.globals[name] = w_ref

    def unset_global(self, space, name):
        try:
            del self.globals[name]
        except KeyError:
            pass

    @jit.elidable
    def lookup_constant(self, name):
        try:
            return self.constants[name.lower()]
        except KeyError:
            raise NotImplementedError("Constant %s not found" % name) # XXX store on constants a string version
        # blah blah blah

    @jit.elidable
    def lookup_function(self, name):
        try:
            return self.functions[name.lower()]
        except KeyError:
            self.logger.fatal(self, "undefined function: %s()" % name)

    def run_main(self, space, bytecode):
        frame = Frame(space, bytecode)
        # The global 'frame' needs to have its local variables be references
        # to the real global variables.
        for i, name in enumerate(bytecode.varnames):
            w_ref = self.lookup_global(space, name)
            frame.store_fast_ref(i, w_ref)
        frame.is_global_level = True
        #
        return self.interpret(space, frame, bytecode)

    def interpret(self, space, frame, bytecode):
        self.enter(frame)
        try:
            return self._interpret(space, frame, bytecode)
        finally:
            self.leave(frame)

    def _interpret(self, space, frame, bytecode):
        pc = 0
        while True:
            driver.jit_merge_point(bytecode=bytecode, frame=frame,
                                   pc=pc, self=self)
            code = bytecode.code
            if not we_are_translated():
                bytecode._marker = pc
            next_instr = ord(code[pc])
            frame.next_instr = pc
            # XXX change this to range check
            numargs = BYTECODE_NUM_ARGS[next_instr]
            pc += 1
            if numargs == 1:
                arg = ord(code[pc]) + (ord(code[pc + 1]) << 8)
                arg2 = 0
                pc += 2
            elif numargs == 2:
                arg = ord(code[pc]) + (ord(code[pc + 1]) << 8)
                arg2 = ord(code[pc + 2]) + (ord(code[pc + 3]) << 8)
                pc += 4
            else:
                arg = 0 # don't make it negative
                arg2 = 0
            assert arg >= 0
            assert arg2 >= 0
            if next_instr == RETURN:
                assert frame.stackpos == 1
                res = frame.stack[0].deref()
                frame.clean(bytecode)
                return res
            if we_are_translated():
                for i, name in unrolling_bc:
                    if i == next_instr:
                        pc = getattr(self, name)(bytecode, frame, space,
                                                 arg, arg2, pc)
                        break
                else:
                    assert False
            else:
                #print get_printable_location(pc, bytecode, self)
                pc = getattr(self, BYTECODE_NAMES[next_instr])(bytecode,
                             frame, space, arg, arg2, pc)

    def enter(self, frame):
        frame.f_backref = self.topframeref
        self.topframeref = jit.virtual_ref(frame)

    def gather_traceback(self, callback, arg):
        frame = self.topframeref()
        while frame is not None:
            callback(arg, frame)
            frame = frame.f_backref()

    def leave(self, frame):
        jit.virtual_ref_finish(self.topframeref, frame)
        self.topframeref = frame.f_backref

    def echo(self, space, v):
        space.ec.writestr(space.str_w(space.as_string(v)))

    def ILLEGAL(self, bytecode, frame, space, arg, arg2, pc):
        raise IllegalInstruction()

    RETURN = ILLEGAL      # handled separately

    def LOAD_NONE(self, bytecode, frame, space, arg, arg2, pc):
        frame.push(None)
        return pc

    def LOAD_NULL(self, bytecode, frame, space, arg, arg2, pc):
        frame.push(space.w_Null)
        return pc

    def LOAD_CONST(self, bytecode, frame, space, arg, arg2, pc):
        frame.push(bytecode.consts[arg])
        return pc

    def LOAD_CONST_INTERPOLATE(self, bytecode, frame, space, arg, arg2, pc):
        w_const = bytecode.consts[arg]
        assert isinstance(w_const, W_StrInterpolation)
        frame.push(w_const.interpolate(space, frame, bytecode))
        return pc

    def LOAD_NAMED_CONSTANT(self, bytecode, frame, space, arg, arg2, pc):
        frame.push(self.lookup_constant(bytecode.names[arg]))
        return pc

    def STORE(self, bytecode, frame, space, arg, arg2, pc):
        w_val = frame.peek_nth(arg)
        w_var = frame.pop()
        w_keep = frame.peek()
        frame.pop_n(arg)
        frame.store_var(space, w_var, w_val)
        frame.push(w_keep)
        return pc

    def DISCARD_TOP(self, bytecode, frame, space, arg, arg2, pc):
        frame.pop()
        return pc

    def DUP_TOP_AND_NTH(self, bytecode, frame, space, arg, arg2, pc):
        w_v = frame.peek_nth(arg)
        frame.push(frame.peek())
        frame.push(w_v)
        return pc

    def POP_AND_POKE_NTH(self, bytecode, frame, space, arg, arg2, pc):
        w_v = frame.pop()
        frame.poke_nth(arg, w_v)
        return pc

    @jit.unroll_safe
    def ROT(self, bytecode, frame, space, arg, arg2, pc):
        w_move_forward = frame.peek_nth(arg)
        arg -= 1
        while arg >= 0:
            frame.poke_nth(arg + 1, frame.peek_nth(arg))
            arg -= 1
        frame.poke_nth(0, w_move_forward)
        return pc

    def LOAD_NAME(self, bytecode, frame, space, arg, arg2, pc):
        frame.push(space.newstrconst(bytecode.names[arg]))
        return pc

    def LOAD_VAR_NAME(self, bytecode, frame, space, arg, arg2, pc):
        frame.push(space.newstrconst(bytecode.varnames[arg]))
        return pc

    def LOAD_REF(self, bytecode, frame, space, arg, arg2, pc):
        frame.push(frame.load_fast(arg))
        return pc

    def LOAD_DEREF(self, bytecode, frame, space, arg, arg2, pc):
        frame.push(frame.load_fast(arg).deref())
        return pc

    def STORE_FAST_REF(self, bytecode, frame, space, arg, arg2, pc):
        w_ref = frame.peek()
        frame.store_fast_ref(arg, w_ref)
        if frame.is_global_level:
            # we just changed the reference stored into a local variable,
            # but if we are the main level, it means we need to change
            # too the reference stored in self.globals
            self.update_global(space, bytecode.varnames[arg], w_ref)
        return pc

    def UNSET(self, bytecode, frame, space, arg, arg2, pc):
        frame.store_fast_ref(arg, W_Reference(space.w_Null))
        if frame.is_global_level:
            self.unset_global(space, bytecode.varnames[arg])
        return pc

    @jit.unroll_safe
    def ECHO(self, bytecode, frame, space, arg, arg2, pc):
        # reverse the args
        args_w = [frame.pop() for i in range(arg)]
        for i in range(len(args_w) - 1, -1, -1):
            self.echo(space, args_w[i])
        return pc

    def JUMP_IF_FALSE(self, bytecode, frame, space, arg, arg2, pc):
        if not space.is_true(frame.pop()):
            return arg
        return pc

    def JUMP_BACK_IF_TRUE(self, bytecode, frame, space, arg, arg2, pc):
        if space.is_true(frame.pop()):
            driver.can_enter_jit(pc=arg, bytecode=bytecode, frame=frame,
                             self=self)
            return arg
        return pc

    def JUMP_IF_FALSE_NO_POP(self, bytecode, frame, space, arg, arg2, pc):
        if not space.is_true(frame.peek()):
            return arg
        return pc

    def JUMP_IF_TRUE_NO_POP(self, bytecode, frame, space, arg, arg2, pc):
        if space.is_true(frame.peek()):
            return arg
        return pc

    def JUMP_FORWARD(self, bytecode, frame, space, arg, arg2, pc):
        return arg

    def JUMP_BACKWARD(self, bytecode, frame, space, arg, arg2, pc):
        driver.can_enter_jit(pc=arg, bytecode=bytecode, frame=frame,
                             self=self)
        return arg

    def SUFFIX_PLUSPLUS(self, bytecode, frame, space, arg, arg2, pc):
        w_var = frame.pop()
        frame.push(w_var.deref())
        frame.store_var(space, w_var, space.uplusplus(w_var))
        return pc

    def SUFFIX_MINUSMINUS(self, bytecode, frame, space, arg, arg2, pc):
        w_var = frame.pop()
        frame.push(w_var.deref())
        frame.store_var(space, w_var, space.uminusminus(w_var))
        return pc

    def PREFIX_PLUSPLUS(self, bytecode, frame, space, arg, arg2, pc):
        w_var = frame.pop()
        w_newval = space.uplusplus(w_var.deref())
        frame.store_var(space, w_var, w_newval)
        frame.push(w_newval)
        return pc

    def PREFIX_MINUSMINUS(self, bytecode, frame, space, arg, arg2, pc):
        w_var = frame.pop()
        w_newval = space.uminusminus(w_var.deref())
        frame.store_var(space, w_var, w_newval)
        frame.push(w_newval)
        return pc

    def UNARY_PLUS(self, bytecode, frame, space, arg, arg2, pc):
        w_v = frame.pop()
        frame.push(space.uplus(w_v))
        return pc

    def UNARY_MINUS(self, bytecode, frame, space, arg, arg2, pc):
        w_v = frame.pop()
        frame.push(space.uminus(w_v))
        return pc

    def UNARY_NOT(self, bytecode, frame, space, arg, arg2, pc):
        frame.push(space.newbool(not space.is_true(frame.pop())))
        return pc

    def GETFUNC(self, bytecode, frame, space, arg, arg2, pc):
        name = space.str_w(frame.pop())
        func = self.lookup_function(name)
        frame.push(func)
        return pc

    def ARG(self, bytecode, frame, space, arg, arg2, pc):
        w_argument = frame.pop()
        func = frame.pop()
        assert isinstance(func, AbstractFunction)
        w_argument = func.prepare_argument(space, arg, w_argument)
        frame.push(w_argument)
        frame.push(func)
        return pc

    def ARG_IS_BYREF(self, bytecode, frame, space, arg, arg2, pc):
        func = frame.peek()
        assert isinstance(func, AbstractFunction)
        frame.push(space.newbool(func.argument_is_byref(arg)))
        return pc

    def CALL(self, bytecode, frame, space, arg, arg2, pc):
        func = frame.pop()
        w_res = func.call(space, frame, arg)
        frame.pop_n(arg)
        frame.push(w_res)
        return pc

    def GETITEM(self, bytecode, frame, space, arg, arg2, pc):
        w_item = frame.pop()
        w_obj = frame.pop()
        frame.push(space.getitem(w_obj, w_item))
        return pc

    def FETCHITEM(self, bytecode, frame, space, arg, arg2, pc):
        # like GETITEM, but without destroying the input argument
        w_obj = frame.peek()
        w_item = frame.peek_nth(arg)
        frame.push(space.getitem(w_obj, w_item))
        return pc

    def STOREITEM(self, bytecode, frame, space, arg, arg2, pc):
        # strange stack effects, matching the usage of this opcode
        w_value = frame.peek_nth(arg)
        w_target = frame.pop()
        w_item = frame.peek_nth(arg)
        w_obj = frame.peek()
        if isinstance(w_target, W_Reference):
            w_target.w_value = w_value.deref()
            w_newobj = w_obj
        else:
            w_newobj, w_newvalue = space.setitem2(w_obj, w_item, w_value)
            frame.poke_nth(arg - 1, w_newvalue)
        frame.poke_nth(arg, w_newobj)
        return pc

    def STOREITEM_REF(self, bytecode, frame, space, arg, arg2, pc):
        w_ref = frame.peek_nth(arg - 1)
        assert isinstance(w_ref, W_Reference)
        w_item = frame.peek_nth(arg)
        w_obj = frame.peek()
        w_newobj = space.setitem_ref(w_obj, w_item, w_ref)
        frame.poke_nth(arg, w_newobj)
        return pc

    def UNSETITEM(self, bytecode, frame, space, arg, arg2, pc):
        w_item = frame.peek_nth(arg)
        w_obj = frame.peek()
        w_newobj = space.unsetitem(w_obj, w_item)
        frame.poke_nth(arg, w_newobj)
        return pc

    def APPEND_INDEX(self, bytecode, frame, space, arg, arg2, pc):
        w_obj = frame.peek()
        w_item = space.append_index(w_obj)
        frame.poke_nth(arg, w_item)
        return pc

    def MAKE_REF(self, bytecode, frame, space, arg, arg2, pc):
        w_obj = frame.pop()
        if not isinstance(w_obj, W_Reference):
            w_obj = W_Reference(w_obj)
        frame.poke_nth(arg - 1, w_obj)
        return pc

    def BINARY_IS(self, bytecode, frame, space, arg, arg2, pc):
        w_right = frame.pop()
        w_left = frame.pop()
        frame.push(space.newbool(space.is_w(w_left, w_right)))
        return pc

    def BINARY_ISNOT(self, bytecode, frame, space, arg, arg2, pc):
        w_right = frame.pop()
        w_left = frame.pop()
        frame.push(space.newbool(not space.is_w(w_left, w_right)))
        return pc

    def IS_TRUE(self, bytecode, frame, space, arg, arg2, pc):
        frame.push(space.newbool(space.is_true(frame.pop())))
        return pc

    def DEREF(self, bytecode, frame, space, arg, arg2, pc):
        w_x = frame.pop()
        frame.push(w_x.deref())
        return pc

    @jit.unroll_safe
    def MAKE_ARRAY(self, bytecode, frame, space, arg, arg2, pc):
        args_w = [None] * arg
        for i in range(arg - 1, -1, -1):
            args_w[i] = frame.pop()
        frame.push(space.new_array_from_list(args_w))
        return pc

    @jit.unroll_safe
    def MAKE_HASH(self, bytecode, frame, space, arg, arg2, pc):
        args_w = [(None, None)] * arg
        for i in range(arg -1, -1, -1):
            w_v = frame.pop()
            w_k = frame.pop()     # <= may be None
            args_w[i] = (w_k, w_v)
        frame.push(space.new_array_from_pairs(args_w))
        return pc

    def DECLARE_GLOBAL(self, bytecode, frame, space, arg, arg2, pc):
        name = bytecode.varnames[arg]
        w_ref = self.lookup_global(space, name)
        frame.store_fast_ref(arg, w_ref)
        return pc

    def DECLARE_FUNC(self, bytecode, frame, space, arg, arg2, pc):
        func = bytecode.user_functions[arg]
        name = func.get_name()
        if name in self.functions:
            raise InterpreterError("Function '%s' already declared" % name)
        self.functions[name] = func
        return pc

    def CREATE_ITER(self, bytecode, frame, space, arg, arg2, pc):
        w_arr = frame.pop()
        frame.push(space.create_iter(w_arr))
        return pc

    def CREATE_ITER_REF(self, bytecode, frame, space, arg, arg2, pc):
        w_arr_ref = frame.pop()
        frame.push(space.create_iter_ref(w_arr_ref))
        return pc

    def NEXT_VALUE_ITER(self, bytecode, frame, space, arg, arg2, pc):
        w_iter = frame.peek()
        assert isinstance(w_iter, W_BaseArrayIterator)
        try:
            w_value = w_iter.next(space)
        except StopIteration:
            frame.pop()
            return arg
        frame.push(w_value)
        return pc

    def NEXT_ITEM_ITER(self, bytecode, frame, space, arg, arg2, pc):
        w_iter = frame.peek()
        assert isinstance(w_iter, W_BaseArrayIterator)
        try:
            item_w = w_iter.next_item(space)
        except StopIteration:
            frame.pop()
            return arg
        w_key, w_value = item_w
        frame.push(w_key)
        frame.push(w_value)
        return pc

    def CAST_ARRAY(self, bytecode, frame, space, arg, arg2, pc):
        frame.push(space.as_array(frame.pop()))
        return pc

    def CAST_INT(self, bytecode, frame, space, arg, arg2, pc):
        frame.push(space.newint(space.int_w(frame.pop())))
        return pc

    def CAST_FLOAT(self, bytecode, frame, space, arg, arg2, pc):
        frame.push(space.newfloat(space.float_w(frame.pop())))
        return pc

def _new_binop(name):
    def BINARY(self, bytecode, frame, space, arg, arg2, pc):
        w_right = frame.pop()
        w_left = frame.pop()
        frame.push(getattr(space, name)(w_left, w_right))
        return pc
    new_name = 'BINARY_' + name.upper()
    BINARY.func_name = new_name
    return new_name, BINARY

for _name in BINOP_LIST + ['concat']:
    setattr(Interpreter, *_new_binop(_name))

unrolling_bc = unrolling_iterable(enumerate(BYTECODE_NAMES))
