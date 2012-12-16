
import py
from hippy import hippydir
from pypy.rlib.parsing.ebnfparse import parse_ebnf, make_parse_function
from pypy.tool.pairtype import extendabletype

grammar = py.path.local(hippydir).join('grammar.txt').read("rt")
regexs, rules, ToAST = parse_ebnf(grammar)
_parse = make_parse_function(regexs, rules, eof=True)

class ParserError(Exception):
    pass

class Node(object):
    __metaclass__ = extendabletype

    lineno = 0

    _attrs_ = ()

    # those classes are extended with compile() methods in compiler.py

    def __eq__(self, other):
        return (self.__class__ == other.__class__ and
                self.__dict__ == other.__dict__)

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        return self.repr()

    def is_constant(self):
        return False

    def repr(self):
        raise NotImplementedError("abstract base class")

    def compile(self, ctx):
        raise NotImplementedError("abstract base class")

class Block(Node):
    def __init__(self, stmts):
        self.stmts = stmts

    def repr(self):
        return "Block(" + ", ".join([i.repr() for i in self.stmts]) + ")"

class Stmt(Node):
    def __init__(self, expr, lineno=0):
        self.expr = expr
        self.lineno = lineno

    def repr(self):
        return "Stmt(%s)" % self.expr.repr()

class Assignment(Node):
    """ Simple assignment to statically named variable
    """
    def __init__(self, var, expr):
        self.var = var
        self.expr = expr

    def repr(self):
        return "Assign(%s, %s)" % (self.var.repr(), self.expr.repr())

class InplaceOp(Node):
    def __init__(self, op, var, expr):
        self.op = op
        self.var = var
        self.expr = expr

    def repr(self):
        return "InplaceOp(%s, %s, %s)" % (self.op, self.var.repr(),
                                          self.expr.repr())

class Const(Node):
    def is_constant(self):
        return True

class ConstantInt(Const):
    def __init__(self, intval):
        self.intval = intval

    def repr(self):
        return str(self.intval)

class ConstantStr(Const):
    def __init__(self, strval):
        self.strval = strval

    def repr(self):
        return '"' + self.strval + '"'

class ConstantFloat(Const):
    def __init__(self, floatval):
        self.floatval = floatval

    def repr(self):
        return str(self.floatval)

class ConstantAppend(Const):

    def repr(self):
        return 'fake_index'

class BinOp(Node):
    def __init__(self, op, left, right):
        self.op = op
        self.left = left
        self.right = right

    def repr(self):
        return "%s %s %s" % (self.left.repr(), self.op, self.right.repr())

class PrefixOp(Node):
    def __init__(self, op, val):
        self.op = op
        self.val = val

    def repr(self):
        return "%s%s" % (self.op, self.val.repr())

class SuffixOp(Node):
    def __init__(self, op, val):
        self.op = op
        self.val = val

    def repr(self):
        return "%s%s" % (self.val.repr(), self.op)

class Variable(Node):
    def __init__(self, node):
        self.node = node

    def repr(self):
        return "$" + self.node.repr()

class UninitializedVariable(Node):
    def __init__(self, name):
        self.name = name

    def repr(self):
        return "$" + self.name

class InitializedVariable(Node):
    def __init__(self, name, expr):
        self.name = name
        self.expr = expr

    def repr(self):
        return "$" + self.name + " = " + self.expr.repr()

class Echo(Node):
    def __init__(self, exprlist, lineno=0):
        self.exprlist = exprlist
        self.lineno = lineno

    def repr(self):
        return "Echo(%s)" % ", ".join([i.repr() for i in self.exprlist])

class Return(Stmt):
    def repr(self):
        if self.expr is None:
            return "return;"
        return "return " + self.expr.repr() + ";"

class While(Node):
    def __init__(self, expr, body, lineno=0):
        self.expr = expr
        self.body = body
        self.lineno = lineno

    def repr(self):
        return "While(%s, %s)" % (self.expr.repr(), self.body.repr())

class DoWhile(Node):
    def __init__(self, body, expr, lineno=0):
        self.expr = expr
        self.body = body
        self.lineno = lineno

    def repr(self):
        return "DoWhile(%s, %s)" % (self.body.repr(), self.expr.repr())

class For(Node):
    def __init__(self, start, cond, step, body, lineno=0):
        self.start = start
        self.cond  = cond
        self.step  = step
        self.body  = body
        self.lineno = lineno

    def repr(self):
        return "For(%s, %s, %s, %s)" % (self.start.repr(), self.cond.repr(),
                                        self.step.repr(), self.body.repr())

class If(Node):
    def __init__(self, cond, body, elseiflist=None, elseclause=None,
                 lineno=0):
        self.cond = cond
        self.body = body
        self.elseiflist = elseiflist
        self.elseclause = elseclause
        self.lineno = lineno

    def repr(self):
        if self.elseiflist is not None:
            elseif = ", [" + ", ".join([i.repr() for i in self.elseiflist]) + "]"
        else:
            elseif = ""
        if self.elseclause is not None:
            elseclause = ", " + self.elseclause.repr()
        else:
            elseclause = ""
        return "If(%s, %s%s%s)" % (self.cond.repr(), self.body.repr(),
                                       elseif, elseclause)

class SimpleCall(Node):
    def __init__(self, name, args):
        self.name = name
        self.args = args

    def repr(self):
        argrepr = ", ".join([i.repr() for i in self.args])
        return "SimpleCall(%s, %s)" % (self.name, argrepr)

class DynamicCall(Node):
    def __init__(self, node, args):
        self.node = node
        self.args = args

    def repr(self):
        argrepr = ", ".join([i.repr() for i in self.args])
        return "DynamicCall(%s, %s)" % (self.node.repr(), argrepr)

class FunctionDecl(Node):
    def __init__(self, name, argdecls, body, lineno):
        self.name = name
        self.argdecls = argdecls
        self.body = body
        self.lineno = lineno

    def repr(self):
        argsrepr = "[" + ", ".join([i.repr() for i in self.argdecls]) + "]"
        return "FunctionDecl(%s, %s, %s)" % (self.name, argsrepr,
                                             self.body.repr())

class Argument(Node):
    def __init__(self, name):
        self.name = name

    def repr(self):
        return self.name

class ReferenceArgument(Node):
    def __init__(self, name):
        self.name = name

    def repr(self):
        return "&" + self.name

class DefaultArgument(Node):
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def repr(self):
        return "%s = %s" % (self.name, self.value.repr())

class GetItem(Node):
    def __init__(self, node, item):
        self.node = node
        self.item = item

    def repr(self):
        return 'GetItem(%s, %s)' % (self.node.repr(), self.item.repr())

class Array(Node):
    def __init__(self, initializers):
        self.initializers = initializers

    def repr(self):
        return 'Array([%s])' % ', '.join([i.repr() for i in self.initializers])

class Hash(Node):
    def __init__(self, initializers):
        self.initializers = initializers

    def repr(self):
        return 'Hash([%s])' % ', '.join(["(%s => %s)" % (k.repr(), v.repr()) for k, v in self.initializers])

class Append(Node):
    def __init__(self, node, expr):
        self.node = node
        self.expr = expr

    def repr(self):
        return 'Append(%s, %s)' % (self.node.repr(), self.expr.repr())

class And(Node):
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def repr(self):
        return 'And(%s, %s)' % (self.left.repr(), self.right.repr())

class Or(Node):
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def repr(self):
        return 'Or(%s, %s)' % (self.left.repr(), self.right.repr())

class Global(Node):
    def __init__(self, names, lineno=0):
        self.names = names
        self.lineno = lineno

    def repr(self):
        return 'Global(%s)' % ', '.join(self.names)

class StaticDecl(Node):
    def __init__(self, vars, lineno=0):
        self.vars = vars
        self.lineno = lineno

    def repr(self):
        return 'StaticDecl([%s])' % ', '.join([v.repr() for v in self.vars])

class NamedConstant(Node):
    def __init__(self, name):
        self.name = name

    def is_constant(self):
        # only prebuilt ones
        if self.name.lower() in ['true', 'false', 'null']:
            return True
        return False

    def repr(self):
        return 'NamedConstant(%s)' % self.name

class Reference(Node):
    def __init__(self, item):
        self.item = item

    def repr(self):
        return 'Reference(%s)' % self.item.repr()

class Break(Node):
    def __init__(self, lineno=0):
        self.lineno = lineno

    def repr(self):
        return "Break"

class Continue(Node):
    def __init__(self, lineno=0):
        self.lineno = lineno

    def repr(self):
        return "Continue"

class IfExpr(Node):
    def __init__(self, cond, left, right):
        self.cond = cond
        self.left = left
        self.right = right

    def repr(self):
        return "IfExpr(%s, %s, %s)" % (self.cond.repr(), self.left.repr(),
                                       self.right.repr())

class ForEach(Node):
    def __init__(self, expr, varname, body, lineno=0):
        self.expr = expr
        self.varname = varname
        self.body = body
        self.lineno = lineno

    def repr(self):
        return 'ForEach(%s, %s, %s)' % (self.expr.repr(), self.varname.repr(),
                                        self.body.repr())

class ForEachKey(Node):
    def __init__(self, expr, keyname, valname, body, lineno=0):
        self.expr = expr
        self.keyname = keyname
        self.valname = valname
        self.body = body
        self.lineno = lineno

    def repr(self):
        return 'ForEachKey(%s, %s, %s, %s)' % (self.expr.repr(),
                                               self.keyname.repr(),
                                               self.valname.repr(),
                                               self.body.repr())

class Cast(Node):
    def __init__(self, to, expr):
        self.to = to
        self.expr = expr

    def repr(self):
        return 'Cast(%s, %s)' % (self.to, self.expr.repr())

class Transformer(object):
    def visit_main(self, node):
        return self.visit_block(node.children[0])

    def visit_block(self, nextnode):
        stmts = []
        while True:
            stmts.append(self.visit_stmt(nextnode.children[0]))
            if len(nextnode.children) == 1:
                break
            nextnode = nextnode.children[1]
        return Block(stmts)

    def visit_stmt(self, node):
        lineno = node.getsourcepos().lineno
        if node.children[0].symbol == 'expr':
            return Stmt(self.visit_expr(node.children[0]), lineno)
        elif node.children[0].symbol == 'function_decl':
            return self.visit_function_decl(node.children[0])
        info = node.children[0].additional_info
        if node.children[0].symbol == 'ECHO':
            args = [self.visit_expr(node.children[1])]
            if len(node.children) == 4:
                argnode = node.children[2]
                while len(argnode.children) == 3:
                    args.append(self.visit_expr(argnode.children[1]))
                    argnode = argnode.children[2]
                args.append(self.visit_expr(argnode.children[1]))
            return Echo(args, lineno)
        elif info == 'return':
            if len(node.children) == 2:
                return Return(None, lineno)
            return Return(self.visit_expr(node.children[1]), lineno)
        elif info == 'if':
            return self.visit_if(node)
        elif info == "{":
            if len(node.children) == 2:
                return Block([])
            return self.visit_block(node.children[1])
        elif info == "while":
            return self.visit_while(node, lineno)
        elif info == "do":
            return self.visit_do_while(node, lineno)
        elif info == "for":
            return self.visit_for(node, lineno)
        elif info == "global":
            return self.visit_global(node, lineno)
        elif info == "static":
            return self.visit_static(node, lineno)
        elif info == "break":
            return Break(lineno)
        elif info == "continue":
            return Continue(lineno)
        elif info == "foreach":
            return self.visit_foreach(node)
        raise NotImplementedError

    def visit_static_var(self, node):
        varname = node.children[2].additional_info
        if len(node.children) == 5:
            rest = node.children[4]
            expr = self.visit_expr(node.children[3].children[1])
            return InitializedVariable(varname, expr), rest
        return (UninitializedVariable(varname),
                node.children[3])

    def visit_static(self, node, lineno):
        vars = []
        while True:
            var, node = self.visit_static_var(node)
            vars.append(var)
            if ';' not in node.symbol and node.children:
                node = node.children[0]
            else:
                break
        return StaticDecl(vars, lineno)

    def visit_var_assign(self, node):
        if len(node.children) == 3:
            if node.children[0].symbol == 'REFERENCE':
                return ReferenceArgument(node.children[2].additional_info)
            if node.children[2].children[0].additional_info != '=':
                raise ParserError("Wrong assignemnt symbol")
            expr = self.visit_expr(node.children[2].children[1])
            assert expr.is_constant()
            return DefaultArgument(node.children[1].additional_info,
                                   expr)
        return Argument(node.children[1].additional_info)

    def visit_foreach(self, node):
        lineno = node.getsourcepos().lineno
        if len(node.children) == 7:
            return ForEach(self.visit_expr(node.children[2]),
                           self.visit_var_assign(node.children[4]),
                           self.visit_stmt(node.children[6]),
                           lineno)
        return ForEachKey(self.visit_expr(node.children[2]),
                          self.visit_var_assign(node.children[4]),
                          self.visit_var_assign(node.children[6]),
                          self.visit_stmt(node.children[8]),
                          lineno)

    def visit_global(self, node, lineno):
        names = [node.children[2].additional_info]
        if len(node.children) == 5:
            nextnode = node.children[3]
            while len(nextnode.children) == 4:
                names.append(nextnode.children[2].additional_info)
                nextnode = nextnode.children[3]
            names.append(nextnode.children[2].additional_info)
        return Global(names, lineno)

    def visit_if(self, node):
        cond = self.visit_expr(node.children[2])
        body = self.visit_stmt(node.children[4])
        lineno = node.getsourcepos().lineno
        if not node.children[5].children:
            # simple if
            return If(cond, body, lineno=lineno)

        if 'star' in node.children[5].symbol:
            if len(node.children) == 7 and node.children[6].children:
                elseclause = self.visit_stmt(node.children[6].children[0].children[1])
            else:
                elseclause = None
            item = node.children[5]
            elseiflist = []
            while 'star' in item.symbol:
                expr = self.visit_expr(item.children[2])
                subbody = self.visit_stmt(item.children[4])
                curlineno = item.getsourcepos().lineno
                elseiflist.append(If(expr, subbody, lineno=curlineno))
                item = item.children[-1]
        else:
            elseiflist = None
            elseclause = self.visit_stmt(node.children[5].children[0].children[1])
        return If(cond, body, elseiflist, elseclause, lineno=lineno)

    def visit_while(self, node, lineno):
        return While(self.visit_expr(node.children[2]),
                     self.visit_stmt(node.children[4]),
                     lineno)

    def visit_do_while(self, node, lineno):
        return DoWhile(self.visit_block(node.children[2]),
                       self.visit_expr(node.children[6]),
                       lineno)

    def visit_for(self, node, lineno):
        return For(self.visit_expr(node.children[2]),
                   self.visit_expr(node.children[4]),
                   self.visit_expr(node.children[6]),
                   self.visit_stmt(node.children[8]),
                   lineno)

    def visit_expr(self, node, is_func_arg=False):
        if node.symbol == 'expr':
            if len(node.children) == 1:
                node = node.children[0]
            elif len(node.children) == 5:
                return IfExpr(self.visit_expr(node.children[0]),
                              self.visit_expr(node.children[2]),
                              self.visit_expr(node.children[4]))
            else:
                raise NotImplementedError
        symname = node.symbol
        if symname == 'assignment':
            return self.visit_assignment(node)
        elif symname == 'and':
            if len(node.children) == 1:
                return self.visit_expr(node.children[0],
                                       is_func_arg=is_func_arg)
            return And(self.visit_expr(node.children[0]),
                       self.visit_expr(node.children[2]))
        elif symname == 'or':
            if len(node.children) == 1:
                return self.visit_expr(node.children[0],
                                       is_func_arg=is_func_arg)
            return Or(self.visit_expr(node.children[0]),
                       self.visit_expr(node.children[2]))
        elif symname in ['additive', 'multitive', 'comparison']:
            return self.visit_subexpr(node, is_func_arg=is_func_arg)
        elif symname == 'primary':
            return self.visit_primary(node, is_func_arg=is_func_arg)
        raise NotImplementedError

    def visit_funccall(self, node):
        if node.children[0].children[0].symbol == 'NAME':
            # a simple call
            return SimpleCall(node.children[0].children[0].additional_info,
                              self.parse_args(node))
        return DynamicCall(self.visit_atom(node.children[0]),
                           self.parse_args(node))

    def parse_args(self, node):
        if len(node.children) == 3:
            # no args
            return []
        arglist = node.children[2]
        args = []
        while len(arglist.children) == 3:
            args.append(self.visit_expr(arglist.children[0], is_func_arg=True))
            arglist = arglist.children[2]
        args.append(self.visit_expr(arglist.children[0], is_func_arg=True))
        return args

    def visit_array_pair(self, node, arr_args, params):
        if node.symbol == 'array_pair':
            if len(node.children) == 2:
                arr_args.append((
                        self.visit_expr(node.children[0]),
                        self.visit_expr(node.children[1].children[1])
                        ))
                params['is_hash'] = True
            if len(node.children) == 1:
                arr_args.append((
                        ConstantAppend(),
                        self.visit_expr(node.children[0])
                        ))
                params['p_iter'] += 1

    def visit_nonempty_array(self, node):
        array_pairs = []
        params = {'p_iter': 0,
                  'is_hash': False}
        if len(node.children) == 1:
            self.visit_array_pair(
                node.children[0],
                array_pairs, params)
        else:
            first_pair = node.children[0]
            self.visit_array_pair(
                first_pair,
                array_pairs, params)
            rest = node.children[1]
            while len(rest.children) == 3:
                pair = rest.children[1]
                self.visit_array_pair(pair, array_pairs,
                                      params)
                rest = rest.children[2]
            self.visit_array_pair(rest.children[1], array_pairs,
                                  params)
        if params['is_hash']:
            return Hash(array_pairs)
        return Array([val for _, val in array_pairs])

    def visit_primary(self, node, is_func_arg=False):
        if node.children[0].symbol == 'function_call':
            return self.visit_funccall(node.children[0])
        elif node.children[0].symbol == 'ARRAY':
            if len(node.children) == 3:
                return Array([])
            else:
                return self.visit_nonempty_array(node.children[2])
        elif len(node.children) == 1:
            if node.children[0].symbol == 'NAME':
                return NamedConstant(node.children[0].additional_info)
            return self.visit_atom(node.children[0])
        elif node.children[0].symbol == 'INOP':
            return PrefixOp(node.children[0].additional_info,
                            self.visit_atom(node.children[1]))
        elif node.children[1].symbol == 'INOP':
            return SuffixOp(node.children[1].additional_info,
                            self.visit_atom(node.children[0]))
        elif node.children[0].symbol == 'atom':
            # getitem
            atom = self.visit_atom(node.children[0])
            return self.parse_getitem(atom, node.children[1],
                                      is_func_arg=is_func_arg)
        elif node.children[0].additional_info == '(':
            if len(node.children) == 4:
                return Cast(node.children[1].additional_info,
                            self.visit_expr(node.children[3]))
            return self.visit_paren(node)
        elif node.children[0].symbol in ('PLUSMINUS', 'UNARYONLY'):
            return PrefixOp(node.children[0].additional_info,
                            self.visit_primary(node.children[1]))
        raise NotImplementedError

    def parse_getitem(self, atom, rest, is_func_arg=False):
        #if is_func_arg:
        #    cls = GetItemReference
        #else:
        cls = GetItem
        if len(rest.children) == 3:
            return cls(atom, self.visit_expr(rest.children[1]))
        atom = cls(atom, self.visit_expr(rest.children[1]))
        return self.parse_getitem(atom, rest.children[3], is_func_arg=is_func_arg)

    def visit_atom(self, node):
        symname = node.children[0].symbol
        if symname == 'DECIMAL':
            return ConstantInt(int(node.children[0].additional_info))
        if symname == 'STR':
            info = node.children[0].additional_info
            end = len(info) - 1
            assert end >= 0
            return ConstantStr(info[1:end])
        if symname == 'FLOAT':
            return ConstantFloat(float(node.children[0].additional_info))
        elif symname == 'NAME':
            return ConstantStr(node.children[0].additional_info)
        elif '$' in symname:
            if len(node.children) == 2:
                return Variable(self.visit_atom(node.children[1]))
            return Variable(self.visit_expr(node.children[2]))
        elif symname == 'REFERENCE':
            return Reference(self.visit_atom(node.children[1]))
        raise NotImplementedError

    def visit_subexpr(self, node, is_func_arg=False):
        if len(node.children) == 1:
            return self.visit_expr(node.children[0], is_func_arg=is_func_arg)
        return BinOp(node.children[1].additional_info,
                     self.visit_expr(node.children[0]),
                     self.visit_expr(node.children[2]))

    def visit_assignment(self, node):
        if len(node.children) == 5:
            oper = node.children[3].additional_info
            atom = Variable(self.visit_atom(node.children[1]))
            getitem = self.parse_getitem(atom, node.children[2])
            if oper != '=':
                return InplaceOp(oper, getitem,
                                 self.visit_expr(node.children[4]))
            return Assignment(getitem,
                              self.visit_expr(node.children[4]))
        elif len(node.children) == 6:
            XXX   # ??
            if node.children[4].additional_info != '=':
                raise ParserError
            return Append(Variable(self.visit_atom(node.children[1])),
                          self.visit_expr(node.children[5]))
        elif len(node.children) == 7:
            atom = Variable(self.visit_atom(node.children[1]))
            getitem = self.parse_getitem(atom, node.children[2])
            if node.children[5].additional_info != '=':
                raise ParserError
            return Append(getitem, self.visit_expr(node.children[6]))
        if node.children[2].additional_info == '=':
            return Assignment(Variable(self.visit_atom(node.children[1])),
                              self.visit_expr(node.children[3]))
        return InplaceOp(node.children[2].additional_info,
                         Variable(self.visit_atom(node.children[1])),
                         self.visit_expr(node.children[3]))

    def visit_paren(self, node):
        return self.visit_expr(node.children[1])

    def visit_function_decl(self, node):
        funcname = node.children[1].additional_info
        args = self.parse_argdecls(node.children[2])
        if len(node.children) == 5:
            body = Block([])
        else:
            stmts = []
            stmt = node.children[4]
            while len(stmt.children) == 2:
                stmts.append(self.visit_stmt(stmt.children[0]))
                stmt = stmt.children[1]
            stmts.append(self.visit_stmt(stmt.children[0]))
            body = Block(stmts)
        lineno = node.getsourcepos().lineno
        return FunctionDecl(funcname, args, body, lineno)

    def parse_argdecls(self, node):
        if len(node.children) == 2:
            return []
        argdecls = node.children[1]
        args = []
        while len(argdecls.children) > 1:
            args.append(self.visit_var_assign(argdecls.children[0]))
            argdecls = argdecls.children[2]
        args.append(self.visit_var_assign(argdecls.children[0]))
        return args

transformer = Transformer()

def parse(source):
    return transformer.visit_main(_parse(source))
