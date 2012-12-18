
from hippy.rpython.rdict import RDict
from hippy.consts import BYTECODE_NUM_ARGS, BYTECODE_NAMES,\
     BINOP_LIST, RETURN
from hippy.builtin import setup_builtin_functions
from hippy import array_funcs     # site-effect of registering functions
from hippy.error import InterpreterError
from hippy.objects.reference import W_Reference
from hippy.objects.base import W_Root
from hippy.objects.interpolate import W_StrInterpolation
from hippy.objects.arrayiter import BaseArrayIterator
#from hippy.objects.arrayobject import new_globals_wrapper
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
        self.vars_w = [W_Reference(space.w_Null) for v in code.varnames]

    def push(self, w_v):
        stackpos = jit.hint(self.stackpos, promote=True)
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

    def store_fast(self, no, w_ref):
        assert isinstance(w_ref, W_Reference)
        self.vars_w[no] = w_ref


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
        #self.globals_wrapper = new_globals_wrapper(space, dct)

    def __init__(self, space):
        self.functions = {}
        self.constants = {}
        self.setup_constants(space)
        setup_builtin_functions(self, space)
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
                if not we_are_translated():
                    bytecode._marker = pc
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
        except InterpreterError:
            print "Error occured in %s line %d" % (bytecode.name,
                                   bytecode.bc_mapping[pc])
            raise

    def echo(self, space, v):
        space.ec.writestr(space.str_w(space.as_string(v)))

    def ILLEGAL(self, bytecode, frame, space, arg, arg2, pc):
        raise IllegalInstruction()

    RETURN = ILLEGAL      # handled separately

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
        w_keep = frame.peek().deref()
        frame.pop_n(arg)
        frame.store_var(space, w_var, w_val)
        frame.push(w_keep)
        return pc

    def DISCARD_TOP(self, bytecode, frame, space, arg, arg2, pc):
        frame.pop()
        return pc

    def ROT_AND_DISCARD(self, bytecode, frame, space, arg, arg2, pc):
        w_v = frame.pop()
        frame.pop()
        frame.push(w_v)
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

    def LOAD_NAME(self, bytecode, frame, space, arg, arg2, pc):
        frame.push(space.newstrconst(bytecode.names[arg]))
        return pc

    def LOAD_VAR_NAME(self, bytecode, frame, space, arg, arg2, pc):
        frame.push(space.newstrconst(bytecode.varnames[arg]))
        return pc

    def LOAD_VAR(self, bytecode, frame, space, arg, arg2, pc):
        name = space.str_w(frame.pop())
        frame.push(frame.load_var(space, bytecode, name))
        return pc

    def LOAD_FAST(self, bytecode, frame, space, arg, arg2, pc):
        frame.push(frame.load_fast(arg))
        return pc

    def STORE_FAST_REF(self, bytecode, frame, space, arg, arg2, pc):
        w_ref = frame.peek()
        frame.store_fast(arg, w_ref)
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

    def FETCHITEM(self, bytecode, frame, space, arg, arg2, pc):
        # like GETITEM, but without destroying the input argument
        w_obj = frame.peek()
        w_item = frame.peek_nth(arg)
        frame.push(space.getitem(w_obj, w_item))
        return pc

    def FETCHITEM_APPEND(self, bytecode, frame, space, arg, arg2, pc):
        w_obj = frame.peek()
        w_item = space.append_index(w_obj)
        frame.poke_nth(arg, w_item)
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
            w_newobj = space.setitem(w_obj, w_item, w_value)
        frame.poke_nth(arg, w_newobj)
        return pc

    def STOREITEM_REF(self, bytecode, frame, space, arg, arg2, pc):
        w_ref = frame.peek_nth(arg - 1)
        assert isinstance(w_ref, W_Reference)
        w_item = frame.peek_nth(arg)
        w_obj = frame.peek()
        w_newvalue = space.setitem_ref(w_obj, w_item, w_ref)
        frame.poke_nth(arg, w_newvalue)
        return pc

    def MAKE_REF(self, bytecode, frame, space, arg, arg2, pc):
        w_obj = frame.pop()
        if not isinstance(w_obj, W_Reference):
            w_obj = W_Reference(w_obj)
        frame.poke_nth(arg - 1, w_obj)
        return pc

    def BINARY_CONCAT(self, bytecode, frame, space, arg, arg2, pc):
        w_right = frame.pop()
        w_left = frame.pop()
        frame.push(space.concat(w_left, w_right))
        return pc

    def BINARY_IS(self, bytecode, frame, space, arg, arg2, pc):
        w_right = frame.pop().deref()
        w_left = frame.pop().deref()
        XXX - space.is_w(w_left, w_right)
        if w_t.tp != w_right.tp:
            frame.push(space.w_False)
        else:
            frame.push(space.eq(w_left, w_right))
        return pc

    def BINARY_ISNOT(self, bytecode, frame, space, arg, arg2, pc):
        w_right = frame.pop().deref()
        w_left = frame.pop().deref()
        XXX - space.is_w(w_left, w_right)
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

for _name in BINOP_LIST:
    setattr(Interpreter, *_new_binop(_name))

unrolling_bc = unrolling_iterable(enumerate(BYTECODE_NAMES))
