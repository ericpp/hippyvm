
import os
from hippy.rpython.rdict import RDict
from hippy.consts import BYTECODE_NUM_ARGS, BYTECODE_NAMES, RETURN_NULL,\
     BINOP_LIST, RETURN, INPLACE_LIST
from hippy.builtin import setup_builtin_functions
from hippy.array_funcs import setup_array_functions
from hippy.error import InterpreterError
from hippy.objects.reference import W_Variable, W_Cell, W_Reference
from hippy.objects.base import W_Root
from hippy.objects.strobject import W_StrInterpolation
from hippy.objects.arrayiter import BaseArrayIterator
from hippy.objects.arrayobject import new_globals_wrapper
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib import jit
from pypy.rlib.unroll import unrolling_iterable

class FunctionNotFound(InterpreterError):
    pass

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
    """ Frame implementation. Note that vars_w store references, while
    stack stores values (also references)
    """
    _virtualizable2_ = ['vars_w[*]', 'stack[*]', 'stackpos']

    @jit.unroll_safe
    def __init__(self, space, code):
        self = jit.hint(self, fresh_virtualizable=True, access_directly=True)
        self.stack = [None] * code.stackdepth
        self.stackpos = 0
        self.bytecode = code # for the debugging
        if code.uses_dict:
            # we use dict in case of:
            # * dynamic var access
            # * global namespace
            self.vars_dict = RDict(W_Root)
            for v in code.varnames:
                self.vars_dict[v] = W_Cell(space.w_Null)
            # create a global dict on the interpreter
            if code.is_main:
                space.ec.interpreter.setup_globals(space, self.vars_dict)
            if code.uses_GLOBALS:
                self.vars_dict['GLOBALS'] = space.get_globals_wrapper()
            self.vars_w = []
        else:
            self.vars_w = [space.w_Null for v in code.varnames]
            if code.uses_GLOBALS:
                self.vars_w[code.lookup_var_pos('GLOBALS')] = space.get_globals_wrapper()

    def push(self, w_v):
        stackpos = jit.hint(self.stackpos, promote=True)
        self.stack[stackpos] = w_v
        self.stackpos = stackpos + 1

    def pop(self):
        stackpos = jit.hint(self.stackpos, promote=True) - 1
        assert stackpos >= 0
        res = self.stack[stackpos]
        if self.stack[stackpos] is not None:
            self.stack[stackpos].mark_invalid()
        self.stack[stackpos] = None # don't artificially keep alive stuff
        self.stackpos = stackpos
        return res

    @jit.unroll_safe
    def clean(self, bytecode):
        if not bytecode.uses_dict:
            for i in range(len(bytecode.varnames)):
                self.vars_w[i].mark_invalid()

    def peek(self):
        stackpos = jit.hint(self.stackpos, promote=True) - 1
        assert stackpos >= 0
        return self.stack[stackpos]

    def store_var_by_name(self, space, bc, name, w_value):
        if bc.uses_dict:
            self.vars_dict[name].store_var(space, w_value)
        else:
            pos = bc.lookup_var_pos(name)
            return self.simple_store_var(space, pos, w_value)

    def simple_store_var(self, space, pos, w_value):
        pos = jit.hint(pos, promote=True)
        if isinstance(w_value, W_Reference):
            self.vars_w[pos] = W_Cell(w_value)
        else:
            w_copy = w_value.deref_for_store().copy(space)
            self.vars_w[pos] = w_copy
            return w_copy

    def store_var(self, space, w_v, w_value):
        if isinstance(w_v, W_Variable):
            self.simple_store_var(space, w_v.pos, w_value)
        else:
            w_v.store_var(space, w_value)

    @jit.elidable
    def lookup_var_pos(self, name):
        return self.vars_dict[name]

    def load_var(self, space, bytecode, name):
        if bytecode.uses_dict:
            return self.lookup_var_pos(name)
        pos = jit.hint(bytecode.lookup_var_pos(name), promote=True)
        w_v = self.vars_w[pos]
        if w_v.tp == space.tp_cell:
            return w_v
        return W_Variable(self, pos)

    def load_fast(self, space, bytecode, no):
        w_v = self.vars_w[no]
        if w_v.tp == space.tp_cell:
            return w_v
        return W_Variable(self, no)

    def upgrade_to_cell(self, w_var):
        if self.bytecode.uses_dict:
            return w_var
        if isinstance(w_var, W_Reference):
            w_var = w_var.deref()
        elif isinstance(w_var, W_Cell):
            return w_var
        elif not isinstance(w_var, W_Variable):
            raise InterpreterError("Reference to something that's not a variable")
        assert isinstance(w_var, W_Variable)
        new_var = W_Cell(w_var.deref())
        pos = jit.hint(w_var.pos, promote=True)
        self.vars_w[pos] = new_var
        return new_var

class IllegalInstruction(InterpreterError):
    pass

class Interpreter(object):
    """ Interpreter keeps the state of the current run. There will be a new
    interpreter instance per run of script
    """
    def setup_constants(self, space):
        self.constants['true'] = space.w_True
        self.constants['false'] = space.w_False
        self.constants['null'] = space.w_Null

    def setup_globals(self, space, dct):
        self.globals = dct
        self.globals_wrapper = new_globals_wrapper(space, dct)

    def __init__(self, space):
        self.functions = {}
        self.constants = {}
        self.setup_constants(space)
        setup_builtin_functions(self, space)
        setup_array_functions(self, space)
        space.ec.interpreter = self # one interpreter at a time

    @jit.elidable
    def lookup_global(self, space, name):
        try:
            return self.globals[name]
        except KeyError:
            new_glob = W_Cell(space.w_Null)
            self.globals[name] = new_glob
            return new_glob

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
            raise InterpreterError("undefined function %s" % name)

    def interpret(self, space, frame, bytecode):
        bytecode.setup_functions(self, space)
        pc = 0
        try:
            while True:
                driver.jit_merge_point(bytecode=bytecode, frame=frame,
                                       pc=pc, self=self)
                code = bytecode.code
                next_instr = ord(code[pc])
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
                if next_instr == RETURN_NULL:
                    assert frame.stackpos == 0
                    frame.clean(bytecode)
                    return None
                elif next_instr == RETURN:
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
        except InterpreterError:
            print "Error occured in %s line %d" % (bytecode.name,
                                   bytecode.bc_mapping[pc])
            raise

    def echo(self, space, v):
        # XXX extra copy of the string if mutable
        os.write(1, space.conststr_w(space.as_string(v)))

    def ILLEGAL(self, bytecode, frame, space, arg, arg2, pc):
        raise IllegalInstruction()

    RETURN_NULL = ILLEGAL # handled separately
    RETURN = ILLEGAL      # handled separately

    def LOAD_CONST(self, bytecode, frame, space, arg, arg2, pc):
        frame.push(bytecode.consts[arg])
        return pc

    def LOAD_MUTABLE_CONST(self, bytecode, frame, space, arg, arg2, pc):
        frame.push(bytecode.consts[arg].copy(space))
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
        w_val = frame.pop()
        w_var = frame.pop()
        frame.store_var(space, w_var, w_val)
        frame.push(w_val)
        return pc

    def DISCARD_TOP(self, bytecode, frame, space, arg, arg2, pc):
        frame.pop()
        return pc

    def ROT_AND_DISCARD(self, bytecode, frame, space, arg, arg2, pc):
        w_v = frame.pop()
        frame.pop()
        frame.push(w_v)
        return pc

    def LOAD_NAME(self, bytecode, frame, space, arg, arg2, pc):
        frame.push(space.newstrconst(bytecode.names[arg]))
        return pc

    def LOAD_VAR_NAME(self, bytecode, frame, space, arg, arg2, pc):
        frame.push(space.newstrconst(bytecode.varnames[arg]))
        return pc

    def LOAD_VAR(self, bytecode, frame, space, arg, arg2, pc):
        name = space.conststr_w(frame.pop())
        frame.push(frame.load_var(space, bytecode, name))
        return pc

    def LOAD_FAST(self, bytecode, frame, space, arg, arg2, pc):
        frame.push(frame.load_fast(space, bytecode, arg))
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

    def JUMP_BACK_IF_NOT_DONE(self, bytecode, frame, space, arg, arg2, pc):
        w_iter = frame.peek()
        assert isinstance(w_iter, BaseArrayIterator)
        if w_iter.done():
            frame.pop().mark_invalid()
            return pc
        return arg

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
        frame.push(w_var.deref().copy(space))
        frame.store_var(space, w_var, space.uplusplus(w_var))
        return pc

    def SUFFIX_MINUSMINUS(self, bytecode, frame, space, arg, arg2, pc):
        w_var = frame.pop()
        frame.push(w_var.deref().copy(space))
        frame.store_var(space, w_var, space.uminusminus(w_var))
        return pc

    def PREFIX_PLUSPLUS(self, bytecode, frame, space, arg, arg2, pc):
        w_var = frame.pop()
        frame.store_var(space, w_var,
                        space.uplusplus(w_var.deref().copy(space)))
        frame.push(w_var.deref())
        return pc

    def PREFIX_MINUSMINUS(self, bytecode, frame, space, arg, arg2, pc):
        w_var = frame.pop()
        frame.store_var(space, w_var,
                        space.uminusminus(w_var.deref().copy(space)))
        frame.push(w_var.deref())
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

    @jit.unroll_safe
    def CALL(self, bytecode, frame, space, arg, arg2, pc):
        name = space.str_w(frame.pop())
        func = self.lookup_function(name)
        frame.push(func.call(space, frame, [frame.pop() for i in range(arg)]))
        return pc

    def GETITEM(self, bytecode, frame, space, arg, arg2, pc):
        w_item = frame.pop()
        w_obj = frame.pop()
        frame.push(space.getitem(w_obj, w_item))
        return pc

    def ITEMREFERENCE(self, bytecode, frame, space, arg, arg2, pc):
        w_item = frame.pop()
        w_obj = frame.pop()
        frame.push(space.itemreference(w_obj, w_item))
        return pc

    def SETITEM(self, bytecode, frame, space, arg, arg2, pc):
        w_value = frame.pop()
        w_item = frame.pop()
        w_obj = frame.pop()
        space.setitem(w_obj, w_item, w_value)
        frame.push(w_value)
        return pc

    def BINARY_CONCAT(self, bytecode, frame, space, arg, arg2, pc):
        w_right = frame.pop()
        w_left = frame.pop()
        frame.push(space.concat(w_left, w_right))
        return pc

    def BINARY_IS(self, bytecode, frame, space, arg, arg2, pc):
        w_right = frame.pop().deref()
        w_left = frame.pop().deref()
        if w_left.tp != w_right.tp:
            frame.push(space.w_False)
        else:
            frame.push(space.eq(w_left, w_right))
        return pc

    def BINARY_ISNOT(self, bytecode, frame, space, arg, arg2, pc):
        w_right = frame.pop().deref()
        w_left = frame.pop().deref()
        if w_left.tp != w_right.tp:
            frame.push(space.w_True)
        else:
            frame.push(space.ne(w_left, w_right))
        return pc

    def IS_TRUE(self, bytecode, frame, space, arg, arg2, pc):
        frame.push(space.newbool(space.is_true(frame.pop())))
        return pc

    @jit.unroll_safe
    def ARRAY(self, bytecode, frame, space, arg, arg2, pc):
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
            w_k = frame.pop()
            args_w[i] = (w_k, w_v)
        frame.push(space.new_array_from_pairs(args_w))
        return pc

    def APPEND(self, bytecode, frame, space, arg, arg2, pc):
        w_val = frame.pop()
        arr = frame.pop()
        frame.push(w_val)
        space.append(arr, w_val)
        return pc

    @jit.unroll_safe
    def DECLARE_GLOBAL(self, bytecode, frame, space, arg, arg2, pc):
        for i in range(arg):
            name = space.str_w(frame.pop())
            glob = self.lookup_global(space, name)
            if bytecode.uses_dict:
                # XXX check if it's there
                frame.vars_dict[name] = W_Cell(glob)
            else:
                pos = jit.hint(bytecode.lookup_var_pos(name), promote=True)
                frame.vars_w[pos] = glob
        return pc

    @jit.unroll_safe
    def DECLARE_STATIC(self, bytecode, frame, space, arg, arg2, pc):
        for i in range(arg):
            name = space.str_w(frame.pop())
            w_cell = bytecode.lookup_static(name)
            if bytecode.uses_dict:
                frame.vars_dict[name] = w_cell
            else:
                pos = jit.hint(bytecode.lookup_var_pos(name), promote=True)
                frame.vars_w[pos] = w_cell
        return pc

    def REFERENCE(self, bytecode, frame, space, arg, arg2, pc):
        w_var = frame.pop()
        w_var = frame.upgrade_to_cell(w_var)
        frame.push(W_Reference(w_var))
        return pc

    def INPLACE_CONCAT(self, bytecode, frame, space, arg, arg2, pc):
        w_value = frame.pop()
        w_var = frame.pop()
        frame.store_var(space, w_var,
                        space.inplace_concat(w_var, w_value))
        frame.push(w_var)
        return pc

    def CREATE_ITER(self, bytecode, frame, space, arg, arg2, pc):
        w_arr = frame.pop()
        frame.push(space.create_iter(space.as_array(w_arr)))
        return pc

    def NEXT_VALUE_ITER(self, bytecode, frame, space, arg, arg2, pc):
        w_var = frame.pop()
        w_iter = frame.peek()
        assert isinstance(w_iter, BaseArrayIterator)
        if w_iter.done():
            frame.pop().mark_invalid()
            return arg
        w_value = w_iter.next(space)
        frame.store_var(space, w_var, w_value)
        return pc

    def NEXT_ITEM_ITER(self, bytecode, frame, space, arg, arg2, pc):
        w_valvar = frame.pop()
        w_keyvar = frame.pop()
        w_iter = frame.peek()
        assert isinstance(w_iter, BaseArrayIterator)
        if w_iter.done():
            frame.pop().mark_invalid()
            return arg
        w_item, w_value = w_iter.next_item(space)
        frame.store_var(space, w_keyvar, w_item)
        frame.store_var(space, w_valvar, w_value)
        return pc

    def CAST_ARRAY(self, bytecode, frame, space, arg, arg2, pc):
        frame.push(space.as_array(frame.pop()))
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

def _new_inplace_op(name):
    def INPLACE(self, bytecode, frame, space, arg, arg2, pc):
        w_value = frame.pop()
        w_var = frame.pop()
        w_newval = getattr(space, name)(w_var, w_value)
        frame.store_var(space, w_var, w_newval)
        frame.push(w_newval)
        return pc
    new_name = 'INPLACE_' + name.upper()
    INPLACE.func_name = new_name
    return new_name, INPLACE

for _name in BINOP_LIST:
    setattr(Interpreter, *_new_binop(_name))

for _name in INPLACE_LIST:
    setattr(Interpreter, *_new_inplace_op(_name))

unrolling_bc = unrolling_iterable(enumerate(BYTECODE_NAMES))
