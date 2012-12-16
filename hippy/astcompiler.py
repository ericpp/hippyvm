
from hippy.sourceparser import Block, Assignment, Stmt, ConstantInt, BinOp,\
     Variable, ConstantStr, Echo, ConstantFloat, If, SuffixOp, PrefixOp,\
     While, SimpleCall, For, GetItem, Array, FunctionDecl, Argument,\
     Return, Append, And, Or, InplaceOp, Global, NamedConstant, DoWhile,\
     Reference, ReferenceArgument, Break, Hash, IfExpr,\
     ForEach, ForEachKey, Cast, Continue, DynamicCall, StaticDecl,\
     UninitializedVariable, InitializedVariable, DefaultArgument,\
     ConstantAppend
from hippy.objects.intobject import W_IntObject
from hippy.objects.floatobject import W_FloatObject
#from hippy.objects.strobject import W_StrInterpolation
#from hippy.objects.arrayobject import W_FakeIndex
from hippy.objects.reference import W_Cell
from hippy import consts
from hippy.error import InterpreterError
from hippy.bytecode import ByteCode
from hippy.function import Function
from pypy.rlib.rsre.rsre_re import compile

def compile_ast(mainnode, space, extra_offset=0, print_exprs=False):
    c = CompilerContext(0, space, extra_offset=extra_offset,
                        print_exprs=print_exprs)
    mainnode.compile(c)
    c.emit(consts.RETURN_NULL)
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
    def __init__(self, startlineno, space, name='<main>',
                 extra_offset=0, print_exprs=False):
        self.space = space
        self.data = []
        self.consts = []
        self.names = []
        self.names_to_nums = {}
        self.varnames = []
        self.varnames_to_nums = {}
        self.int_cache = {}
        self.float_cache = {}
        self.string_cache = {}
        self.other_cache = {}
        self.functions = {}
        self.labels = [] # stack of labels
        self.jumps_to_patch = {} # label -> list of jumps to patch
        self.startlineno = startlineno
        self.cur_lineno = startlineno
        self.lineno_map = []
        self.name = name
        self.extra_offset = extra_offset
        self.print_exprs = print_exprs
        self.static_vars = {}

    def register_superglobal(self, name):
        assert name == 'GLOBALS' # not supporting anything else for now

    def set_lineno(self, lineno):
        self.cur_lineno = lineno

    def register_static_declr(self, name, w_val):
        self.static_vars[name] = W_Cell(w_val)

    def emit(self, bc, arg=-1, arg2=-1):
        self.lineno_map.append(self.cur_lineno + self.extra_offset)
        assert arg < 1<<16
        assert arg2 < 1<<16
        self.data.append(chr(bc))
        if arg != -1:
            self.data.append(chr(arg & 0xff))
            self.data.append(chr(arg >> 8))
            self.lineno_map.append(self.cur_lineno + self.extra_offset)
            self.lineno_map.append(self.cur_lineno + self.extra_offset)
        if arg2 != -1:
            self.data.append(chr(arg2 & 0xff))
            self.data.append(chr(arg2 >> 8))
            self.lineno_map.append(self.cur_lineno + self.extra_offset)
            self.lineno_map.append(self.cur_lineno + self.extra_offset)

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

    def create_interpolation_const(self, strings, vars):
        self.consts.append(W_StrInterpolation(strings[:], vars[:]))
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
        try:
            return self.other_cache[w_v]
        except KeyError:
            a = len(self.consts)
            self.consts.append(w_v)
            self.other_cache[w_v] = a
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
        if name in SUPERGLOBALS:
            self.register_superglobal(name)
        try:
            return self.varnames_to_nums[name]
        except KeyError:
            r = len(self.varnames)
            self.varnames_to_nums[name] = r
            self.varnames.append(name)
            return r

    def register_function(self, name, args, bytecode):
        name = name.lower()
        if name in self.functions:
            raise CompilerError("function %s already declared" % name)
        self.functions[name] = Function(args[:], bytecode)

    def create_bytecode(self):
        return ByteCode("".join(self.data), self.consts[:], self.names[:],
                        self.varnames[:], self.functions, self.static_vars,
                        self.startlineno,
                        self.lineno_map, self.name)

    def preprocess_str(self, s):
        i = 0
        has_vars = False
        r = []
        strings = []
        vars = []
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
                    vars.append(v)
                    i += 1 + len(v)
                    r = []
            else:
                r.append(c)
                i += 1
        if not has_vars:
            return self.create_name(''.join(r)), False
        else:
            strings.append(''.join(r))
            return self.create_interpolation_const(strings, vars), True

class __extend__(Block):
    def compile(self, ctx):
        for stmt in self.stmts:
            stmt.compile(ctx)

class __extend__(Stmt):
    def compile(self, ctx):
        ctx.set_lineno(self.lineno)
        self.expr.compile(ctx)
        if ctx.print_exprs:
            # special mode used for interactive usage: print all expressions
            # (with a final \n) instead of discarding them.
            ctx.emit(consts.LOAD_NAME, ctx.create_name("\n"))
            ctx.emit(consts.ECHO, 2)
        else:
            ctx.emit(consts.DISCARD_TOP)

class __extend__(Return):
    def compile(self, ctx):
        if self.expr is None:
            ctx.emit(consts.RETURN_NULL)
        else:
            self.expr.compile(ctx)
            ctx.emit(consts.RETURN)

class __extend__(Echo):
    def compile(self, ctx):
        ctx.set_lineno(self.lineno)
        for expr in self.exprlist:
            expr.compile(ctx)
        ctx.emit(consts.ECHO, len(self.exprlist))

class __extend__(Assignment):
    def compile(self, ctx):
        # An expression like "$a[5][6] = 42" becomes this:
        #                 stack:
        # LOAD_CONST 5       [ 5 ]
        # LOAD_CONST 6       [ 5, 6 ]
        # LOAD_CONST 42      [ 5, 6, 42 ]
        # LOAD_FAST $a       [ 5, 6, 42, Ref$a ]
        # FETCHITEM 3        [ 5, 6, 42, Ref$a, Array$a[5] ]
        # FETCHITEM 3        [ 5, 6, 42, Ref$a, Array$a[5], OldValue$a[5][6] ]
        # STOREITEM 3        [ 5, NewArray1, 42, Ref$a, Array$a[5] ]
        # STOREITEM 3        [ NewArray2, NewArray1, 42, Ref$a ]
        # STORE 3            [ 42 ]
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
        #    NewArray1 = Array$a[5] with the 6th item replaced with 42.
        #
        #  - If it is, then 42 is stored into this existing reference
        #    and NewArray1 is just Array$a[5].
        #
        #  - NewArray1 is put back in the stack at position N+1, and
        #    finally the stack item 0 is popped.
        #
        # 'STORE N' has also strange stack effects: it stores the item at
        # position N into the reference at position 0, then kill the item
        # at position 0 and all items at positions 2 to N inclusive.
        #
        depth = self.var.compile_assignment_prepare(ctx)
        self.expr.compile(ctx)
        self.var.compile_assignment_fetch(ctx, depth)
        self.var.compile_assignment_store(ctx, depth)

class __extend__(ConstantInt):
    def compile(self, ctx):
        ctx.emit(consts.LOAD_CONST, ctx.create_int_const(self.intval))

    def wrap(self, space):
        return space.wrap(self.intval)

class __extend__(ConstantAppend):

    def wrap(self, space):
        return W_FakeIndex()

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

class __extend__(InplaceOp):
    def compile(self, ctx):
        self.var.compile(ctx)
        self.expr.compile(ctx)
        ctx.emit(consts.INPLACE_OP_TO_BC[self.op])

class __extend__(Variable):
    def compile(self, ctx):
        # note that in the fast case (a variable) we could precache the name
        # lookup. It does not matter for the JIT, but it does matter for the
        # interpreter
        node = self.node
        if isinstance(node, ConstantStr):
            ctx.emit(consts.LOAD_FAST, ctx.create_var_name(node.strval))
            return # fast path
        else:
            self.node.compile(ctx)
        ctx.emit(consts.LOAD_VAR)

    def compile_assignment_prepare(self, ctx):
        return 0

    def compile_assignment_fetch(self, ctx, depth):
        self.compile(ctx)

    def compile_assignment_store(self, ctx, depth):
        ctx.emit(consts.STORE, depth + 1)

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

        if self.elseiflist:
            for elem in self.elseiflist:
                ctx.patch_pos(pos)
                elem.cond.compile(ctx)
                ctx.emit(consts.JUMP_IF_FALSE, 0)
                pos = ctx.get_pos()
                elem.body.compile(ctx)

        if self.elseclause is not None:
            ctx.emit(consts.JUMP_FORWARD, 0)
            elsepos = ctx.get_pos()
        else:
            elsepos = -1 # help the annotator
        ctx.patch_pos(pos)
        if self.elseclause is not None:
            self.elseclause.compile(ctx)
            ctx.patch_pos(elsepos)

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
        for i in range(len(self.args) - 1, -1, -1):
            self.args[i].compile(ctx)
        ctx.emit(consts.LOAD_NAME, ctx.create_name(self.name))
        ctx.emit(consts.CALL, len(self.args))

class __extend__(DynamicCall):
    def compile(self, ctx):
        for i in range(len(self.args) - 1, -1, -1):
            self.args[i].compile(ctx)
        self.node.compile(ctx)
        ctx.emit(consts.CALL, len(self.args))

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
    def compile(self, ctx):
        self.node.compile(ctx)
        self.item.compile(ctx)
        ctx.emit(consts.GETITEM)

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

class __extend__(Array):
    def compile(self, ctx):
        for item in self.initializers:
            item.compile(ctx) # XXX order?
        ctx.emit(consts.ARRAY, len(self.initializers))

class __extend__(FunctionDecl):
    def compile(self, ctx):
        new_context = CompilerContext(self.lineno, ctx.space, self.name,
                                      extra_offset=ctx.extra_offset)
        self.body.compile(new_context)
        new_context.emit(consts.RETURN_NULL) # optimization! or lack of
        args = []
        for arg in self.argdecls:
            if isinstance(arg, Argument):
                name = arg.name
                args.append((consts.ARG_ARGUMENT, name, None))
            elif isinstance(arg, ReferenceArgument):
                name = arg.name
                args.append((consts.ARG_REFERENCE, name, None))
            elif isinstance(arg, DefaultArgument):
                name = arg.name
                args.append((consts.ARG_DEFAULT, name,
                             arg.value.wrap(ctx.space)))
            else:
                assert False
            new_context.create_var_name(name) # make sure those are in vars
        ctx.register_function(self.name, args, new_context.create_bytecode())

class __extend__(Append):
    def compile(self, ctx):
        self.node.compile(ctx)
        self.expr.compile(ctx)
        ctx.emit(consts.APPEND)

class __extend__(And):
    def compile(self, ctx):
        self.left.compile(ctx)
        ctx.emit(consts.IS_TRUE)
        ctx.emit(consts.JUMP_IF_FALSE_NO_POP, 0)
        jmp_pos = ctx.get_pos()
        self.right.compile(ctx)
        ctx.emit(consts.IS_TRUE)
        ctx.emit(consts.ROT_AND_DISCARD)
        ctx.patch_pos(jmp_pos)

class __extend__(Or):
    def compile(self, ctx):
        self.left.compile(ctx)
        ctx.emit(consts.IS_TRUE)
        ctx.emit(consts.JUMP_IF_TRUE_NO_POP, 0)
        jmp_pos = ctx.get_pos()
        self.right.compile(ctx)
        ctx.emit(consts.IS_TRUE)
        ctx.emit(consts.ROT_AND_DISCARD)
        ctx.patch_pos(jmp_pos)

class __extend__(Global):
    def compile(self, ctx):
        ctx.set_lineno(self.lineno)
        for name in self.names:
            ctx.emit(consts.LOAD_VAR_NAME, ctx.create_var_name(name))
        ctx.emit(consts.DECLARE_GLOBAL, len(self.names))

class __extend__(StaticDecl):
    def compile(self, ctx):
        ctx.set_lineno(self.lineno)
        for var in self.vars:
            if isinstance(var, UninitializedVariable):
                ctx.emit(consts.LOAD_VAR_NAME, ctx.create_var_name(var.name))
                ctx.register_static_declr(var.name, ctx.space.w_Null)
            else:
                assert isinstance(var, InitializedVariable)
                w_obj = var.expr.wrap(ctx.space)
                ctx.register_static_declr(var.name, w_obj)
                ctx.emit(consts.LOAD_VAR_NAME, ctx.create_var_name(var.name))
        ctx.emit(consts.DECLARE_STATIC, len(self.vars))

class __extend__(NamedConstant):
    def compile(self, ctx):
        ctx.emit(consts.LOAD_NAMED_CONSTANT, ctx.create_name(self.name))

    def wrap(self, space):
        if self.name == 'null':
            return space.w_Null
        elif self.name == 'true':
            return space.w_True
        elif self.name == 'false':
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

class __extend__(Reference):
    def compile(self, ctx):
        self.item.compile(ctx)
        ctx.emit(consts.REFERENCE)

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
        if True:
            for key, value in self.initializers:
                if not key.is_constant():
                    break
                if not value.is_constant():
                    break
            else:
                # just precompile it
                pairs = []
                for key, value in self.initializers:
                    pairs.append((key.wrap(ctx.space), value.wrap(ctx.space)))
                w_arr = ctx.space.new_map_from_pairs(pairs)
                ctx.emit(consts.LOAD_MUTABLE_CONST, ctx.create_other_const(w_arr))
                return
        for key, v in self.initializers:
            key.compile(ctx)
            v.compile(ctx)
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
        ctx.emit(consts.CREATE_ITER)
        lbl = ctx.register_label()
        jmp_back_pos = ctx.get_pos_for_jump()
        self.varname.compile(ctx)
        ctx.emit(consts.NEXT_VALUE_ITER, 0)
        ctx.register_jump_to_patch(lbl)
        self.body.compile(ctx)
        ctx.emit(consts.JUMP_BACK_IF_NOT_DONE, jmp_back_pos)
        ctx.pop_label(lbl)

class __extend__(ForEachKey):
    def compile(self, ctx):
        ctx.set_lineno(self.lineno)
        self.expr.compile(ctx)
        ctx.emit(consts.CREATE_ITER)
        lbl = ctx.register_label()
        jmp_back_pos = ctx.get_pos_for_jump()
        self.keyname.compile(ctx)
        self.valname.compile(ctx)
        ctx.emit(consts.NEXT_ITEM_ITER, 0)
        ctx.register_jump_to_patch(lbl)
        self.body.compile(ctx)
        ctx.emit(consts.JUMP_BACK_IF_NOT_DONE, jmp_back_pos)
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
