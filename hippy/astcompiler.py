
from hippy.sourceparser import Block, Assignment, Stmt, ConstantInt, BinOp,\
     Variable, ConstantStr, Echo, ConstantFloat, If, SuffixOp, PrefixOp,\
     While, SimpleCall, For, GetItem, FunctionDecl, Argument,\
     Return, Append, And, Or, InplaceOp, Global, NamedConstant, DoWhile,\
     Reference, ReferenceArgument, Break, Hash, IfExpr,\
     ForEach, ForEachKey, Cast, Continue, DynamicCall, StaticDecl,\
     UninitializedVariable, InitializedVariable, DefaultArgument, Node,\
     LiteralBlock, Unset
from hippy.objects.intobject import W_IntObject
from hippy.objects.floatobject import W_FloatObject
from hippy.objects.interpolate import W_StrInterpolation
from hippy.objects.reference import W_Reference
from hippy import consts
from hippy.error import InterpreterError
from hippy.bytecode import ByteCode
from hippy.function import Function
from pypy.rlib.rsre.rsre_re import compile

def compile_ast(filename, source, mainnode, space, print_exprs=False):
    c = CompilerContext(filename, source.split("\n"), 1, space,
                        print_exprs=print_exprs)
    mainnode.compile(c)
    c.emit(consts.LOAD_NULL)
    c.emit(consts.RETURN)
    return c.create_bytecode()

class CompilerError(InterpreterError):
    pass

def intern(name, cache={}):
    try:
        return cache[name]
    except KeyError:
        cache[name] = name
        return name

VAR_REGEX = compile("[a-zA-Z_][a-zA-Z0-9_]*")
SUPERGLOBALS = ['GLOBALS']

class CompilerContext(object):
    """ Context for compiling a piece of bytecode. It'll store the necessary
    """
    def __init__(self, filename, sourcelines, startlineno, space, name='<main>',
                 print_exprs=False):
        self.space = space
        self.filename = filename
        self.sourcelines = sourcelines
        self.data = []
        self.consts = []
        self.names = []
        self.names_to_nums = {}
        self.varnames = []
        self.varnames_to_nums = {}
        self.int_cache = {}
        self.float_cache = {}
        self.string_cache = {}
        self.functions = []
        self.labels = [] # stack of labels
        self.jumps_to_patch = {} # label -> list of jumps to patch
        self.startlineno = startlineno
        self.cur_lineno = startlineno
        self.lineno_map = []
        self.name = name
        self.print_exprs = print_exprs
        self.static_vars = {}
        self.globals_var_num = -1

    def register_superglobal(self, name, index):
        assert name == 'GLOBALS' # not supporting anything else for now
        self.globals_var_num = index

    def set_lineno(self, lineno):
        self.cur_lineno = lineno

    def emit(self, bc, arg=-1, arg2=-1):
        self.lineno_map.append(self.cur_lineno)
        assert arg < 1<<16
        assert arg2 < 1<<16
        self.data.append(chr(bc))
        if arg != -1:
            self.data.append(chr(arg & 0xff))
            self.data.append(chr(arg >> 8))
            self.lineno_map.append(self.cur_lineno)
            self.lineno_map.append(self.cur_lineno)
        if arg2 != -1:
            self.data.append(chr(arg2 & 0xff))
            self.data.append(chr(arg2 >> 8))
            self.lineno_map.append(self.cur_lineno)
            self.lineno_map.append(self.cur_lineno)

    def get_pos(self):
        return len(self.data) - 2

    def register_label(self):
        self.labels.append(len(self.data))
        self.jumps_to_patch[len(self.labels) - 1] = []
        return len(self.labels) - 1

    def get_last_label_pos(self):
        return self.labels[-1]

    def register_jump_to_patch(self, label):
        self.jumps_to_patch[label].append(self.get_pos())

    def pop_label(self, label):
        for jmp_pos in self.jumps_to_patch[label]:
            self.patch_pos(jmp_pos)
        del self.jumps_to_patch[label]
        self.labels.pop()

    def get_pos_for_jump(self):
        return len(self.data)

    def patch_pos(self, pos):
        v = len(self.data)
        self.data[pos] = chr(v & 0xff)
        self.data[pos + 1] = chr(v >> 8)

    def create_interpolation_const(self, strings, var_nums):
        self.consts.append(W_StrInterpolation(strings[:], var_nums))
        return len(self.consts) - 1

    def create_int_const(self, v):
        try:
            return self.int_cache[v]
        except KeyError:
            a = len(self.consts)
            self.consts.append(W_IntObject(v))
            self.int_cache[v] = a
            return a

    def create_other_const(self, w_v):
        # xxx no caching for now, which should not really be a problem
        a = len(self.consts)
        self.consts.append(w_v)
        return a

    def create_float_const(self, v):
        try:
            return self.float_cache[v]
        except KeyError:
            a = len(self.consts)
            self.consts.append(W_FloatObject(v))
            self.float_cache[v] = a
            return a

    def create_name(self, name):
        name = intern(name)
        try:
            return self.names_to_nums[name]
        except KeyError:
            r = len(self.names)
            self.names_to_nums[name] = r
            self.names.append(name)
            return r

    def create_var_name(self, name):
        name = intern(name)
        try:
            return self.varnames_to_nums[name]
        except KeyError:
            r = len(self.varnames)
            self.varnames_to_nums[name] = r
            self.varnames.append(name)
            if name in SUPERGLOBALS:
                self.register_superglobal(name, r)
            return r

    def force_var_name(self, name, i):
        name = intern(name)
        assert i == len(self.varnames)
        self.varnames_to_nums[name] = i
        self.varnames.append(name)

    def register_function(self, args, bytecode):
        i = len(self.functions)
        self.functions.append(Function(args, bytecode))
        return i

    def create_bytecode(self):
        return ByteCode("".join(self.data), self.consts[:], self.names[:],
                        self.varnames[:], self.functions,
                        self.filename, self.sourcelines,
                        self.startlineno,
                        self.lineno_map, self.name, self.globals_var_num)

    def preprocess_str(self, s):
        i = 0
        has_vars = False
        r = []
        strings = []
        var_nums = []
        while i < len(s):
            c = s[i]
            if c == '\\':
                if i == len(s) - 1:
                    raise Exception("Strange string")
                next = s[i + 1]
                if next == 'n':
                    r.append('\n')
                elif next == 't':
                    r.append('\t')
                else:
                    r.append(next)
                i += 2
            elif c == '$':
                m = VAR_REGEX.match(s, i + 1)
                if m is None:
                    r.append(c)
                    i += 1
                else:
                    has_vars = True
                    strings.append(''.join(r))
                    v = m.group(0)
                    var_nums.append(self.create_var_name(v))
                    i += 1 + len(v)
                    r = []
            else:
                r.append(c)
                i += 1
        if not has_vars:
            return self.create_name(''.join(r)), False
        else:
            strings.append(''.join(r))
            return self.create_interpolation_const(strings, var_nums), True

    def compile_call(self, args):
        self.emit(consts.GETFUNC)
        for i, arg in enumerate(args):
            if (arg.can_be_passed_by_reference()
                    and not isinstance(arg, Variable)):
                self.emit(consts.ARG_IS_BYREF, i)
                self.emit(consts.JUMP_IF_FALSE, 0)
                pos = self.get_pos()
                arg.compile_reference(self)
                self.emit(consts.JUMP_FORWARD, 0)
                self.patch_pos(pos)
                pos = self.get_pos()
                arg.compile(self)
                self.patch_pos(pos)
            else:
                arg.compile(self)
            # ARG: [function, argument]
            #   => [fixed_argument, function]
            # so the function object remains on top of all arguments, which
            # accumulate below
            self.emit(consts.ARG, i)
        self.emit(consts.CALL, len(args))


class __extend__(Node):
    def can_be_passed_by_reference(self):
        return False

    def compile_deref(self, ctx):
        self.compile(ctx)
        if not self.is_constant():   # otherwise, not useful
            ctx.emit(consts.DEREF)

class __extend__(Block):
    def compile(self, ctx):
        for stmt in self.stmts:
            stmt.compile(ctx)

class __extend__(LiteralBlock):
    def compile(self, ctx):
        ctx.emit(consts.LOAD_NAME, ctx.create_name(self.literal_text))
        ctx.emit(consts.ECHO, 1)

class __extend__(Stmt):
    def compile(self, ctx):
        ctx.set_lineno(self.lineno)
        self.expr.compile(ctx)
        if ctx.print_exprs:
            # special mode used for interactive usage: print all expressions
            # (with a final \n) instead of discarding them.
            ctx.emit(consts.DEREF)
            ctx.emit(consts.LOAD_NAME, ctx.create_name("\n"))
            ctx.emit(consts.ECHO, 2)
        else:
            ctx.emit(consts.DISCARD_TOP)

class __extend__(Return):
    def compile(self, ctx):
        if self.expr is None:
            ctx.emit(consts.LOAD_NULL)
        else:
            self.expr.compile(ctx)
        ctx.emit(consts.RETURN)

class __extend__(Echo):
    def compile(self, ctx):
        ctx.set_lineno(self.lineno)
        for expr in self.exprlist:
            expr.compile_deref(ctx)
        ctx.emit(consts.ECHO, len(self.exprlist))

class __extend__(Assignment):
    def compile(self, ctx):
        expr = self.expr
        if isinstance(expr, Reference):
            self._compile_assign_reference(ctx, expr.item)
        else:
            self._compile_assign_regular(ctx)

    # A simple assignment like "$a = $b" becomes this:
    #                 stack:
    # LOAD_DEREF $b      [ Value$b ]
    # LOAD_REF $a        [ Value$b, Ref$a ]
    # STORE 1            [ Value$b ]
    #
    # The 'STORE 1' pops the reference Ref$a, and store into it the
    # next value from the stack.  The argument to the STORE is always 1
    # in simple assignments, but see below.
    #
    # An expression like "$a[5][6] = $b" becomes this:
    #                 stack:
    # LOAD_CONST 5       [ 5 ]
    # LOAD_CONST 6       [ 5, 6 ]
    # LOAD_DEREF $b      [ 5, 6, Value$b ]
    # LOAD_REF $a        [ 5, 6, Value$b, Ref$a ]
    # FETCHITEM 3        [ 5, 6, Value$b, Ref$a, Array$a[5] ]
    # FETCHITEM 3        [ 5, 6, Value$b, Ref$a, Array$a[5], OldValue$a[5][6] ]
    # STOREITEM 3        [ 5, NewArray1, Value$b, Ref$a, Array$a[5] ]
    # STOREITEM 3        [ NewArray2, NewArray1, Value$b, Ref$a ]
    # STORE 3            [ Value$b ]
    #
    # In more details, 'FETCHITEM N' fetches from the array at position 0
    # the item at position N, and pushes the result without popping any
    # argument.
    #
    # 'STOREITEM N' depends on four stack arguments, at position 0, 1, N
    # and N+1.  In the first case above:
    #
    #  - OldValue$a[5][6] is checked for being a reference.
    #
    #  - If it is not, then its value is ignored, and we compute
    #    NewArray1 = Array$a[5] with the 6th item replaced with Value$b.
    #
    #  - If it is, then Value$b is stored into this existing reference
    #    and NewArray1 is just Array$a[5].
    #
    #  - NewArray1 is put back in the stack at position N+1, and
    #    finally the stack item 0 is popped.
    #
    # 'STORE N' has also strange stack effects: it stores the item at
    # position N into the reference at position 0, then kill the item
    # at position 0 and all items at positions 2 to N inclusive.
    # Above, it leaves Value$b untouched, which (although not used by STORE)
    # is the result of the whole expression.
    #
    # Append: "$a[5][] = 42" becomes this:
    #                 stack:
    # LOAD_CONST 5       [ 5 ]
    # LOAD_NONE          [ 5, None ]
    # LOAD_CONST 42      [ 5, None, 42 ]
    # (DEREF -- not actually needed after a LOAD_CONST)
    # LOAD_REF $a        [ 5, None, 42, Ref$a ]
    # FETCHITEM 3        [ 5, None, 42, Ref$a, Array$a[5] ]
    # APPEND_INDEX 3     [ 5, idx, 42, Ref$a, Array$a[5] ]
    # FETCHITEM 3        [ 5, idx, 42, Ref$a, Array$a[5], OldValue$a[5][idx] ]
    # STOREITEM 3        [ 5, NewArray1, 42, Ref$a, Array$a[5] ]
    # STOREITEM 3        [ NewArray2, NewArray1, 42, Ref$a ]
    # STORE 3            [ 42 ]
    #
    def _compile_assign_regular(self, ctx):
        depth = self.var.compile_assignment_prepare(ctx)
        self.expr.compile_deref(ctx)
        self.var.compile_assignment_fetch(ctx, depth)
        self.var.compile_assignment_store(ctx, depth)

    # A simple assignment like '$a =& $b' becomes this:
    #                 stack:
    # LOAD_REF $b        [ Ref$b ]
    # STORE_FAST_REF $a  [ Ref$b ]
    #
    # If the expression on the left is more complex, like '$a[5][6][7] =& $b':
    #                 stack:
    # LOAD_CONST 5       [ 5 ]
    # LOAD_CONST 6       [ 5, 6 ]
    # LOAD_CONST 7       [ 5, 6, 7 ]
    # LOAD_REF $b        [ 5, 6, 7, Ref$b ]
    # LOAD_REF $a        [ 5, 6, 7, Ref$b, Ref$a ]
    # FETCHITEM 4        [ 5, 6, 7, Ref$b, Ref$a, Array$a[5] ]
    # FETCHITEM 4        [ 5, 6, 7, Ref$b, Ref$a, Array$a[5], Array$a[5][6] ]
    # STOREITEM_REF 4    [ 5, 6, NA1, Ref$b, Ref$a, Array$a[5], Array$a[5][6] ]
    # STOREITEM 4        [ 5, NA2, NA1, Ref$b, Ref$a, Array$a[5] ]
    # STOREITEM 4        [ NA3, NA2, NA1, Ref$b, Ref$a ]
    # STORE 4            [ Ref$b ]         # "NA" = "NewArray"
    #
    # If the expression on the right is more complex than just '$b',
    # say '... =& $b[7][8]', then we use compile_reference() to get code
    # like that to load it:
    #
    # LOAD_CONST 7       [ 7 ]
    # LOAD_CONST 8       [ 7, 8 ]
    # LOAD_NONE          [ 7, 8, None ]
    # LOAD_REF $b        [ 7, 8, None, Ref$b ]
    # FETCHITEM 3        [ 7, 8, None, Ref$b, Array$b[7] ]
    # FETCHITEM 3        [ 7, 8, None, Ref$b, Array$b[7], Array$b[7][8] ]
    # MAKE_REF 3         [ 7, 8, NewRef, Ref$b, Array$b[7] ]
    # STOREITEM_REF 3    [ 7, NewArray1, NewRef, Ref$b, Array$b[7] ]
    # STOREITEM 3        [ NewArray2, NewArray1, NewRef, Ref$b ]
    # STORE 3            [ NewRef ]
    #
    # The case of '... =& $b;' is done just with a LOAD_REF, but following
    # the recipe above we would get the following equivalent code:
    #
    # LOAD_NONE          [ None ]
    # LOAD_REF $b        [ None, Ref$b ]
    # MAKE_REF 1         [ Ref$b, Ref$b ]     # already a ref
    # STORE 1            [ Ref$b ]            # stores $b in $b, no-op
    #
    def _compile_assign_reference(self, ctx, source):
        depth = self.var.compile_assignment_prepare(ctx)
        source.compile_reference(ctx)
        self.var.compile_assignment_fetch_ref(ctx, depth)
        self.var.compile_assignment_store_ref(ctx, depth)

class __extend__(InplaceOp):
    # In-place operators: "$a += 42" becomes this:
    #                 stack:
    # LOAD_CONST 42      [ 42 ]
    # LOAD_REF $a        [ 42, Ref$a ]
    # DUP_TOP_AND_NTH 1  [ 42, Ref$a, Ref$a, 42 ]
    # BINARY_ADD         [ 42, Ref$a, $a+42 ]
    # POP_AND_POKE_NTH 1 [ $a+42, Ref$a ]
    # STORE 1            [ $a+42 ]
    #
    # "$a[5] += 42" becomes this:
    #                 stack:
    # LOAD_CONST 5       [ 5 ]
    # LOAD_CONST 42      [ 5, 42 ]
    # LOAD_REF $a        [ 5, 42, Ref$a ]
    # FETCHITEM 2        [ 5, 42, Ref$a, OldValue$a[5] ]
    # DUP_TOP_AND_NTH 2  [ 5, 42, Ref$a, OldValue$a[5], OldValue$a[5], 42 ]
    # BINARY_ADD         [ 5, 42, Ref$a, OldValue$a[5], old+42 ]
    # POP_AND_POKE_NTH 2 [ 5, old+42, Ref$a, OldValue$a[5] ]
    # STOREITEM 2        [ NewArray1, old+42, Ref$a ]
    # STORE 2            [ old+42 ]
    #
    def compile(self, ctx):
        assert self.op.endswith('=')
        op = self.op[:-1]
        depth = self.var.compile_assignment_prepare(ctx)
        self.expr.compile(ctx)
        self.var.compile_assignment_fetch(ctx, depth)
        ctx.emit(consts.DUP_TOP_AND_NTH, depth + 1)
        ctx.emit(consts.BIN_OP_TO_BC[op])
        ctx.emit(consts.POP_AND_POKE_NTH, depth + 1)
        self.var.compile_assignment_store(ctx, depth)

class __extend__(Unset):
    def compile(self, ctx):
        for node in self.nodes:
            node.compile_unset(ctx)

class __extend__(Reference):
    def compile_generic_assignment(self, ctx):
        self.item.compile_generic_assignment_ref(ctx)

class __extend__(ConstantInt):
    def compile(self, ctx):
        ctx.emit(consts.LOAD_CONST, ctx.create_int_const(self.intval))

    def wrap(self, space):
        return space.wrap(self.intval)

class __extend__(ConstantFloat):
    def compile(self, ctx):
        ctx.emit(consts.LOAD_CONST, ctx.create_float_const(self.floatval))

    def wrap(self, space):
        return space.wrap(self.floatval)

class __extend__(ConstantStr):
    def compile(self, ctx):
        no, is_interpolated = ctx.preprocess_str(self.strval)
        if is_interpolated:
            ctx.emit(consts.LOAD_CONST_INTERPOLATE, no)
        else:
            ctx.emit(consts.LOAD_NAME, no)

    def wrap(self, space):
        return space.newstrconst(self.strval)

class __extend__(BinOp):
    def compile(self, ctx):
        self.left.compile(ctx)
        self.right.compile(ctx)
        ctx.emit(consts.BIN_OP_TO_BC[self.op])

class __extend__(Variable):
    def can_be_passed_by_reference(self):
        return True

    def compile(self, ctx):
        # note that in the fast case (a variable) we could precache the name
        # lookup. It does not matter for the JIT, but it does matter for the
        # interpreter
        node = self.node
        if isinstance(node, ConstantStr):
            ctx.emit(consts.LOAD_REF, ctx.create_var_name(node.strval))
            return # fast path
        else:
            self.node.compile(ctx)
        ctx.emit(consts.LOAD_VAR)

    def compile_deref(self, ctx):
        node = self.node
        if isinstance(node, ConstantStr):
            ctx.emit(consts.LOAD_DEREF, ctx.create_var_name(node.strval))
            return # fast path
        return Node.compile_deref(self, ctx)

    def compile_generic_assignment(self, ctx):
        self.compile_assignment_fetch(ctx, 0)
        self.compile_assignment_store(ctx, 0)

    def compile_reference(self, ctx):
        self.compile(ctx)

    def compile_generic_assignment_ref(self, ctx):
        self.compile_assignment_fetch_ref(ctx, 0)
        self.compile_assignment_store_ref(ctx, 0)

    def compile_assignment_prepare(self, ctx):
        return 0

    def compile_assignment_fetch(self, ctx, depth):
        self.compile(ctx)

    def compile_assignment_store(self, ctx, depth):
        ctx.emit(consts.STORE, depth + 1)

    def compile_assignment_fetch_ref(self, ctx, depth):
        pass

    def compile_assignment_store_ref(self, ctx, depth):
        node = self.node
        if isinstance(node, ConstantStr):
            ctx.emit(consts.STORE_FAST_REF, ctx.create_var_name(node.strval))
            return # fast path
        raise NotImplementedError

    def compile_unset(self, ctx):
        node = self.node
        if isinstance(node, ConstantStr):
            ctx.emit(consts.UNSET, ctx.create_var_name(node.strval))
            return # fast path
        raise NotImplementedError

class __extend__(SuffixOp):
    def compile(self, ctx):
        self.val.compile(ctx)
        ctx.emit(consts.SUFFIX_OP_TO_BC[self.op])

class __extend__(PrefixOp):
    def compile(self, ctx):
        self.val.compile(ctx)
        ctx.emit(consts.PREFIX_OP_TO_BC[self.op])

class __extend__(If):
    def compile(self, ctx):
        ctx.set_lineno(self.lineno)
        self.cond.compile(ctx)
        ctx.emit(consts.JUMP_IF_FALSE, 0)
        pos = ctx.get_pos()
        self.body.compile(ctx)
        jump_after_list = []

        if self.elseiflist:
            for elem in self.elseiflist:
                ctx.emit(consts.JUMP_FORWARD, 0)
                jump_after_list.append(ctx.get_pos())
                ctx.patch_pos(pos)
                elem.cond.compile(ctx)
                ctx.emit(consts.JUMP_IF_FALSE, 0)
                pos = ctx.get_pos()
                elem.body.compile(ctx)

        if self.elseclause is not None:
            ctx.emit(consts.JUMP_FORWARD, 0)
            jump_after_list.append(ctx.get_pos())
        ctx.patch_pos(pos)
        if self.elseclause is not None:
            self.elseclause.compile(ctx)
        for pos in jump_after_list:
            ctx.patch_pos(pos)

class __extend__(While):
    def compile(self, ctx):
        ctx.set_lineno(self.lineno)
        pos = ctx.get_pos_for_jump()
        label = ctx.register_label()
        self.expr.compile(ctx)
        ctx.emit(consts.JUMP_IF_FALSE, 0)
        ctx.register_jump_to_patch(label)
        self.body.compile(ctx)
        ctx.emit(consts.JUMP_BACKWARD, pos)
        ctx.pop_label(label)

class __extend__(SimpleCall):
    def compile(self, ctx):
        ctx.emit(consts.LOAD_NAME, ctx.create_name(self.name))
        ctx.compile_call(self.args)

class __extend__(DynamicCall):
    def compile(self, ctx):
        self.node.compile(ctx)
        ctx.compile_call(self.args)

class __extend__(For):
    def compile(self, ctx):
        ctx.set_lineno(self.lineno)
        self.start.compile(ctx)
        ctx.emit(consts.DISCARD_TOP)
        pos = ctx.get_pos_for_jump()
        lbl = ctx.register_label()
        self.cond.compile(ctx)
        ctx.emit(consts.JUMP_IF_FALSE, 0)
        ctx.register_jump_to_patch(lbl)
        self.body.compile(ctx)
        self.step.compile(ctx)
        ctx.emit(consts.DISCARD_TOP)
        ctx.emit(consts.JUMP_BACKWARD, pos)
        ctx.pop_label(lbl)

class __extend__(GetItem):
    def can_be_passed_by_reference(self):
        return self.node.can_be_passed_by_reference()

    def compile(self, ctx):
        self.node.compile(ctx)
        self.item.compile(ctx)
        ctx.emit(consts.GETITEM)

    def compile_generic_assignment(self, ctx):
        depth = self.compile_assignment_prepare(ctx)
        ctx.emit(consts.ROT, depth)
        self.compile_assignment_fetch(ctx, depth)
        self.compile_assignment_store(ctx, depth)

    def compile_generic_assignment_ref(self, ctx):
        depth = self.compile_assignment_prepare(ctx)
        ctx.emit(consts.ROT, depth)
        self.compile_assignment_fetch_ref(ctx, depth)
        self.compile_assignment_store_ref(ctx, depth)

    def compile_assignment_prepare(self, ctx):
        depth = self.node.compile_assignment_prepare(ctx)
        self.item.compile(ctx)
        return depth + 1

    def compile_assignment_fetch(self, ctx, depth):
        self.node.compile_assignment_fetch(ctx, depth)
        ctx.emit(consts.FETCHITEM, depth + 1)

    def compile_assignment_store(self, ctx, depth):
        ctx.emit(consts.STOREITEM, depth + 1)
        self.node.compile_assignment_store(ctx, depth)

    def compile_assignment_fetch_ref(self, ctx, depth):
        self.node.compile_assignment_fetch(ctx, depth)   # and not '.._ref'

    def compile_assignment_store_ref(self, ctx, depth):
        ctx.emit(consts.STOREITEM_REF, depth + 1)
        self.node.compile_assignment_store(ctx, depth)   # and not '.._ref'

    def compile_reference(self, ctx):
        depth = self.compile_assignment_prepare(ctx)
        ctx.emit(consts.LOAD_NONE)
        self.compile_assignment_fetch(ctx, depth)
        ctx.emit(consts.MAKE_REF, depth + 1)
        self.compile_assignment_store_ref(ctx, depth)

    def compile_unset(self, ctx):
        depth = self.compile_assignment_prepare(ctx)
        ctx.emit(consts.LOAD_NONE)
        self.node.compile_assignment_fetch(ctx, depth)
        ctx.emit(consts.UNSETITEM, depth + 1)
        self.node.compile_assignment_store(ctx, depth)
        ctx.emit(consts.DISCARD_TOP)

class __extend__(Append):
    # note: this is a subclass of GetItem, so inherits all methods not
    # explicitly overridden.
    def compile(self, ctx):
        raise CompilerError("cannot use '[]' when reading items")

    def compile_assignment_prepare(self, ctx):
        depth = self.node.compile_assignment_prepare(ctx)
        ctx.emit(consts.LOAD_NONE)
        return depth + 1

    def compile_assignment_fetch(self, ctx, depth):
        self.node.compile_assignment_fetch(ctx, depth)
        ctx.emit(consts.APPEND_INDEX, depth + 1)
        ctx.emit(consts.FETCHITEM, depth + 1)

    def compile_assignment_fetch_ref(self, ctx, depth):
        self.node.compile_assignment_fetch(ctx, depth)
        ctx.emit(consts.APPEND_INDEX, depth + 1)

class __extend__(FunctionDecl):
    def compile(self, ctx):
        name = self.name.lower()
        new_context = CompilerContext(ctx.filename, ctx.sourcelines,
                                      self.lineno, ctx.space, name)
        args = []
        for i, arg in enumerate(self.argdecls):
            if isinstance(arg, Argument):
                name = arg.name
                args.append((consts.ARG_ARGUMENT, name, None))
            elif isinstance(arg, ReferenceArgument):
                name = arg.name
                args.append((consts.ARG_REFERENCE, name, None))
            elif isinstance(arg, DefaultArgument):
                name = arg.name
                args.append((consts.ARG_ARGUMENT, name,
                             arg.value.wrap(ctx.space)))
            else:
                assert False
            new_context.force_var_name(name, i)
        self.body.compile(new_context)
        new_context.emit(consts.LOAD_NULL)
        new_context.emit(consts.RETURN)
        num = ctx.register_function(args, new_context.create_bytecode())
        ctx.emit(consts.DECLARE_FUNC, num)

class __extend__(And):
    def compile(self, ctx):
        self.left.compile(ctx)
        ctx.emit(consts.IS_TRUE)
        ctx.emit(consts.JUMP_IF_FALSE_NO_POP, 0)
        jmp_pos = ctx.get_pos()
        ctx.emit(consts.DISCARD_TOP)
        self.right.compile(ctx)
        ctx.emit(consts.IS_TRUE)
        ctx.patch_pos(jmp_pos)

class __extend__(Or):
    def compile(self, ctx):
        self.left.compile(ctx)
        ctx.emit(consts.IS_TRUE)
        ctx.emit(consts.JUMP_IF_TRUE_NO_POP, 0)
        jmp_pos = ctx.get_pos()
        ctx.emit(consts.DISCARD_TOP)
        self.right.compile(ctx)
        ctx.emit(consts.IS_TRUE)
        ctx.patch_pos(jmp_pos)

class __extend__(Global):
    def compile(self, ctx):
        ctx.set_lineno(self.lineno)
        for name in self.names:
            ctx.emit(consts.DECLARE_GLOBAL, ctx.create_var_name(name))

class __extend__(StaticDecl):
    def compile(self, ctx):
        ctx.set_lineno(self.lineno)
        for var in self.vars:
            if isinstance(var, UninitializedVariable):
                name = var.name
                w_initial_value = ctx.space.w_Null
            else:
                assert isinstance(var, InitializedVariable)
                name = var.name
                w_initial_value = var.expr.wrap(ctx.space)
            if name in ctx.static_vars:
                # XXX here, generate a warning --- it's nonsense code
                w_ref = ctx.static_vars[name]
                w_ref.w_value = w_initial_value
            else:
                w_ref = W_Reference(w_initial_value)
                ctx.static_vars[name] = w_ref
            ctx.emit(consts.LOAD_CONST, ctx.create_other_const(w_ref))
            ctx.emit(consts.STORE_FAST_REF, ctx.create_var_name(name))
            ctx.emit(consts.DISCARD_TOP)

class __extend__(NamedConstant):
    def compile(self, ctx):
        ctx.emit(consts.LOAD_NAMED_CONSTANT, ctx.create_name(self.name))

    def wrap(self, space):
        name = self.name.lower()
        if name == 'null':
            return space.w_Null
        elif name == 'true':
            return space.w_True
        elif name == 'false':
            return space.w_False
        else:
            assert False

class __extend__(DoWhile):
    def compile(self, ctx):
        ctx.set_lineno(self.lineno)
        jmp_pos = ctx.get_pos_for_jump()
        lbl = ctx.register_label()
        self.body.compile(ctx)
        self.expr.compile(ctx)
        ctx.emit(consts.JUMP_BACK_IF_TRUE, jmp_pos)
        ctx.pop_label(lbl)

class __extend__(Break):
    def compile(self, ctx):
        ctx.set_lineno(self.lineno)
        ctx.emit(consts.JUMP_FORWARD, 0)
        ctx.register_jump_to_patch(len(ctx.labels) - 1)

class __extend__(Continue):
    def compile(self, ctx):
        ctx.set_lineno(self.lineno)
        ctx.emit(consts.JUMP_BACKWARD, ctx.get_last_label_pos())

class __extend__(Hash):
    def compile(self, ctx):
        # Can be compiled in several ways:
        # If no key is specified, it becomes an array
        for key, value in self.initializers:
            if key is not None:
                break
        else:
            self._compile_array(ctx)
            return
        # Otherwise, it becomes a hash
        self._compile_hash(ctx)

    def _generate_code(self, ctx, value):
        if value is None:
            ctx.emit(consts.LOAD_NONE)
        elif isinstance(value, Reference):
            value.item.compile(ctx)
        else:
            value.compile_deref(ctx)

    def _compile_array(self, ctx):
        # If all values are constants, then it's a constant array
        for key, value in self.initializers:
            if not value.is_constant():
                break
        else:
            values = [value.wrap(ctx.space)
                      for key, value in self.initializers]
            w_array = ctx.space.new_array_from_list(values)
            ctx.emit(consts.LOAD_CONST, ctx.create_other_const(w_array))
            return
        # Else, generate for "array($a, &$b, $c)":
        #        ...load $a...
        #        DEREF
        #        ...load $b...
        #        (no DEREF here)
        #        ...load $c...
        #        DEREF
        #        MAKE_ARRAY 3
        for key, value in self.initializers:
            self._generate_code(ctx, value)
        ctx.emit(consts.MAKE_ARRAY, len(self.initializers))

    def _compile_hash(self, ctx):
        # If all keys and values are constants, then it's a constant hash
        for key, value in self.initializers:
            if key is not None and not key.is_constant():
                break
            if not value.is_constant():
                break
        else:
            pairs_ww = []
            for key, value in self.initializers:
                if key is not None:
                    w_key = key.wrap(ctx.space)
                else:
                    w_key = None
                w_value = value.wrap(ctx.space)
                pairs_ww.append((w_key, w_value))
            w_array = ctx.space.new_array_from_pairs(pairs_ww)
            ctx.emit(consts.LOAD_CONST, ctx.create_other_const(w_array))
            return
        # Else, for every item:
        #     load the key...
        #     DEREF
        #     load the value...
        #     maybe DEREF
        for key, value in self.initializers:
            self._generate_code(ctx, key)
            self._generate_code(ctx, value)
        ctx.emit(consts.MAKE_HASH, len(self.initializers))

class __extend__(IfExpr):
    def compile(self, ctx):
        self.cond.compile(ctx)
        ctx.emit(consts.JUMP_IF_FALSE, 0)
        jmp_if_false_pos = ctx.get_pos()
        self.left.compile(ctx)
        ctx.emit(consts.JUMP_FORWARD, 0)
        jmp_forward_pos = ctx.get_pos()
        ctx.patch_pos(jmp_if_false_pos)
        self.right.compile(ctx)
        ctx.patch_pos(jmp_forward_pos)

class __extend__(Argument):
    def compile(self, ctx):
        ctx.emit(consts.LOAD_VAR_NAME, ctx.create_var_name(self.name))
        ctx.emit(consts.LOAD_VAR)

class __extend__(ReferenceArgument):
    def compile(self, ctx):
        ctx.emit(consts.LOAD_VAR_NAME, ctx.create_var_name(self.name))
        ctx.emit(consts.LOAD_VAR)
        ctx.emit(consts.REFERENCE)

class __extend__(ForEach):
    def compile(self, ctx):
        ctx.set_lineno(self.lineno)
        self.expr.compile(ctx)
        if not isinstance(self.valuevar, Reference):
            ctx.emit(consts.CREATE_ITER)
        else:
            ctx.emit(consts.CREATE_ITER_REF)
        lbl = ctx.register_label()
        jmp_back_pos = ctx.get_pos_for_jump()
        ctx.emit(consts.NEXT_VALUE_ITER, 0)
        ctx.register_jump_to_patch(lbl)
        self.valuevar.compile_generic_assignment(ctx)
        ctx.emit(consts.DISCARD_TOP)
        self.body.compile(ctx)
        ctx.emit(consts.JUMP_BACKWARD, jmp_back_pos)
        ctx.pop_label(lbl)

class __extend__(ForEachKey):
    def compile(self, ctx):
        ctx.set_lineno(self.lineno)
        self.expr.compile(ctx)
        if not isinstance(self.valuevar, Reference):
            ctx.emit(consts.CREATE_ITER)
        else:
            ctx.emit(consts.CREATE_ITER_REF)
        lbl = ctx.register_label()
        jmp_back_pos = ctx.get_pos_for_jump()
        ctx.emit(consts.NEXT_ITEM_ITER, 0)
        ctx.register_jump_to_patch(lbl)
        self.valuevar.compile_generic_assignment(ctx)
        ctx.emit(consts.DISCARD_TOP)
        self.keyvar.compile_generic_assignment(ctx)
        ctx.emit(consts.DISCARD_TOP)
        self.body.compile(ctx)
        ctx.emit(consts.JUMP_BACKWARD, jmp_back_pos)
        ctx.pop_label(lbl)

class __extend__(Cast):
    def compile(self, ctx):
        self.expr.compile(ctx)
        ctx.emit(consts.CAST_TO_BC[self.to])

def bc_preprocess(source):
    l = []
    for i in source.splitlines():
        if '#' in i:
            i = i[:i.find('#')]
        i = i.strip()
        if not i:
            continue
        l.append(i)
    return "\n".join(l)
