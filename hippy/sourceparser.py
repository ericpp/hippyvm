import sys
from rply import ParserGenerator
from hippy.lexer import RULES
from hippy.lexer import PRECEDENCES
from hippy.lexer import Lexer
from pypy.tool.pairtype import extendabletype


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
    def __init__(self, stmts, lineno=0):
        self.stmts = stmts
        self.lineno = lineno

    def repr(self):
        return "Block(" + ", ".join([i.repr() for i in self.stmts]) + ", %d)" % self.lineno

class Stmt(Node):
    def __init__(self, expr, lineno=0):
        self.expr = expr
        self.lineno = lineno

    def repr(self):
        return "Stmt(%s)" % self.expr.repr()


class Assignment(Node):
    """ Simple assignment to statically named variable
    """
    def __init__(self, var, expr, lineno=0):
        self.var = var
        self.expr = expr
        self.lineno = lineno

    def repr(self):
        return "Assign(%s, %s, %d)" % (self.var.repr(),
                                       self.expr.repr(),
                                       self.lineno)


class InplaceOp(Node):
    def __init__(self, op, var, expr, lineno=0):
        self.op = op
        self.var = var
        self.expr = expr
        self.lineno = 0

    def repr(self):
        return "InplaceOp(%s, %s, %s)" % (self.op, self.var.repr(),
                                          self.expr.repr())


class Const(Node):
    def is_constant(self):
        return True


class ConstantInt(Const):
    def __init__(self, intval, lineno=0):
        self.intval = intval
        self.lineno = lineno

    def repr(self):
        return "ConstantInt(%d, %d)" % (self.intval, self.lineno)


class ConstantStr(Const):
    def __init__(self, strval, lineno=0):
        self.strval = strval
        self.lineno = lineno

    def repr(self):
        return "ConstantStr(%s, %d)" % (self.strval, self.lineno)


class ConstantFloat(Const):
    def __init__(self, floatval, lineno=0):
        self.floatval = floatval
        self.lineno = lineno

    def repr(self):
        return str(self.floatval)


class ConstantAppend(Const):

    def repr(self):
        return 'fake_index'


class BinOp(Node):
    def __init__(self, op, left, right, lineno=0):
        self.op = op
        self.left = left
        self.right = right
        self.lineno = 0

    def repr(self):
        return "BinOp(%s %s %s)" % (self.left.repr(), self.op, self.right.repr())


class PrefixOp(Node):
    def __init__(self, op, val, lineno=0):
        self.op = op
        self.val = val
        self.lineno = lineno

    def repr(self):
        return "%s%s" % (self.op, self.val.repr())


class SuffixOp(Node):
    def __init__(self, op, val, lineno=0):
        self.op = op
        self.val = val
        self.lineno = lineno

    def repr(self):
        return "%s%s" % (self.val.repr(), self.op)


class Variable(Node):
    def __init__(self, node, lineno=0):
        self.node = node
        self.lineno = lineno

    def repr(self):
        return "Variable(%s, %d)" % (self.node.repr(), self.lineno)


class UninitializedVariable(Node):
    def __init__(self, name, lineno=0):
        self.name = name
        self.lineno = lineno

    def repr(self):
        return "$" + self.name


class InitializedVariable(Node):
    def __init__(self, name, expr, lineno=0):
        self.name = name
        self.expr = expr
        self.lineno = lineno

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
        self.cond = cond
        self.step = step
        self.body = body
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
            elseif = ", [" + ", ".join(
                [i.repr() for i in self.elseiflist]) + "]"
        else:
            elseif = ""
        if self.elseclause is not None:
            elseclause = ", " + self.elseclause.repr()
        else:
            elseclause = ""
        return "If(%s, %s%s%s, %d)" % (self.cond.repr(), self.body.repr(),
                                       elseif, elseclause, self.lineno)


class SimpleCall(Node):
    def __init__(self, name, args, lineno=0):
        self.name = name
        self.args = args
        self.lineno = lineno

    def repr(self):
        argrepr = ", ".join([i.repr() for i in self.args])
        return "SimpleCall(%s, %s, %d)" % (self.name, argrepr, self.lineno)


class DynamicCall(Node):
    def __init__(self, node, args, lineno=0):
        self.node = node
        self.args = args
        self.lineno = lineno

    def repr(self):
        argrepr = ", ".join([i.repr() for i in self.args])
        return "DynamicCall(%s, %s, %d)" % (self.node.repr(), argrepr, self.lineno)


class FunctionDecl(Node):
    def __init__(self, name, argdecls, body, lineno):
        self.name = name
        self.argdecls = argdecls
        self.body = body
        self.lineno = lineno

    def repr(self):
        argsrepr = "[" + ", ".join([i.repr() for i in self.argdecls]) + "]"
        return "FunctionDecl(%s, %s, %s, %d)" % (self.name, argsrepr,
                                                 self.body.repr(),
                                                 self.lineno)

class Argument(Node):
    def __init__(self, name, lineno=0):
        self.name = name
        self.lineno = lineno

    def repr(self):
        return self.name


class ReferenceArgument(Node):
    def __init__(self, name, lineno=0):
        self.name = name
        self.lineno = lineno


    def repr(self):
        return "&" + self.name


class DefaultArgument(Node):
    def __init__(self, name, value, lineno=0):
        self.name = name
        self.value = value
        self.lineno = lineno


    def repr(self):
        return "%s = %s" % (self.name, self.value.repr())


class GetItem(Node):
    def __init__(self, node, item, lineno=0):
        self.node = node
        self.item = item
        self.lineno = lineno


    def repr(self):
        return 'GetItem(%s, %s)' % (self.node.repr(), self.item.repr())


class GetItemReference(GetItem):
    pass


class SetItem(Node):
    def __init__(self, node, item, value, lineno=0):
        self.node = node
        self.item = item
        self.value = value
        self.lineno = lineno


    def repr(self):
        return 'SetItem(%s, %s, %s)' % (self.node.repr(), self.item.repr(),
                                        self.value.repr())


class InplaceSetItem(Node):
    def __init__(self, op, node, item, value, lineno=0):
        self.op = op
        self.node = node
        self.item = item
        self.value = value
        self.lineno = lineno

    def repr(self):
        return 'InplaceSetItem(%s, %s, %s, %s)' % (self.op, self.node.repr(),
                                                   self.item.repr(),
                                                   self.value.repr())


class Array(Node):
    def __init__(self, initializers, lineno=0):
        self.initializers = initializers
        self.lineno = lineno

    def repr(self):
        return 'Array([%s])' % ', '.join([i.repr() for i in self.initializers])


class Hash(Node):
    def __init__(self, initializers, lineno=0):
        self.initializers = initializers
        self.lineno = lineno


    def repr(self):
        return 'Hash([%s])' % ', '.join([
                "(%s => %s)" %
                (k.repr(), v.repr()) for k, v in self.initializers])


class Append(Node):
    def __init__(self, node, expr, lineno=0):
        self.node = node
        self.expr = expr
        self.lineno = lineno


    def repr(self):
        return 'Append(%s, %s)' % (self.node.repr(), self.expr.repr())


class And(Node):
    def __init__(self, left, right, lineno=0):
        self.left = left
        self.right = right
        self.lineno = lineno


    def repr(self):
        return 'And(%s, %s)' % (self.left.repr(), self.right.repr())


class Or(Node):
    def __init__(self, left, right, lineno=0):
        self.left = left
        self.right = right
        self.lineno = lineno


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
    def __init__(self, name, lineno=0):
        self.name = name
        self.lineno = lineno

    def is_constant(self):
        # only prebuilt ones
        if self.name.lower() in ['true', 'false', 'null']:
            return True
        return False

    def repr(self):
        return 'NamedConstant(%s)' % self.name


class Reference(Node):
    def __init__(self, item, lineno=0):
        self.item = item
        self.lineno = lineno

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
    def __init__(self, cond, left, right, lineno=0):
        self.cond = cond
        self.left = left
        self.right = right
        self.lineno = lineno


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
    def __init__(self, to, expr, lineno=0):
        self.to = to
        self.expr = expr
        self.lineno = lineno


    def repr(self):
        return 'Cast(%s, %s)' % (self.to, self.expr.repr())


class LexerWrapper(object):
    def __init__(self, lexer):
        self.lexer = lexer

    def next(self):
        try:
            return self.lexer.next()
        except StopIteration:
            return None


class Parser(object):

    def __init__(self, lexer):
        self.lexer = lexer

    def parse(self):
        l = LexerWrapper(self.lexer)
        return self.parser.parse(l, state=self)

    pg = ParserGenerator([d for (r, d) in RULES],
                         precedence=PRECEDENCES,
                         cache_id="hippy")

    @pg.production("main : top_statement_list")
    def main_top_statement_list(self, p):
        print "Block(%s)" % p
        return Block(p[0])

    @pg.production("top_statement_list : top_statement_list top_statement")
    def top_statement_list_top_statement(self, p):
        if isinstance(p[0], list):
            if p[1]:
                p[0].append(p[1])
                return p[0]
            return p[0]
        return [p[0], p[1]]

    @pg.production("top_statement_list : top_statement")
    def top_statatement_list(self, p):
        return [p[0]]

    @pg.production("top_statement : statement")
    def top_statement(self, p):
        return p[0]

    @pg.production("top_statement : function_declaration_statement")
    def top_statement_function_declaration_statement(self, p):
        return p[0]

    @pg.production("inner_statement_list : "
                   "inner_statement_list inner_statement")
    def inner_statement_list_inner_statement_list_inner_statement(self, p):
        if isinstance(p[0], list):
            if p[1]:
                if p[0] is None:
                    return p[1]
                p[0].append(p[1])
                return p[0]
            return p[0]
        if p[0] is None:
            return p[1]
        return [p[0], p[1]]

    @pg.production("inner_statement_list : empty")
    def inner_statement_list_empty(self, p):
        return p[0]

    @pg.production("inner_statement : statement")
    def inner_statement_statement(self, p):
        return p[0]

    @pg.production("statement : unticked_statement")
    def statement(self, p):
        return p[0]

    @pg.production("unticked_statement : expr ;")
    def unticked_statement_expr(self, p):
        return Stmt(p[0], lineno=p[0].lineno)

    @pg.production("unticked_statement : { inner_statement_list }")
    def unticked_statement_inner_statement_list(self, p):
        if p[1] is None:
            return Block([], lineno=p[0].getsourcepos())
        return Block([p[1]], lineno=p[0].getsourcepos())

    @pg.production("unticked_statement : ;")
    def unticked_statement_empty_statement(self, p):
        return None

    @pg.production("expr : r_variable")
    def expr_expr_r_variable(self, p):
        return p[0]

    @pg.production("expr : expr_without_variable")
    def expr_expr_without_variable(self, p):
        return p[0]

    @pg.production("expr_without_variable : scalar")
    def expr_expr_without_variable_scalar(self, p):
        return p[0]

    @pg.production("expr_without_variable : variable = expr")
    def expr_without_variable_variable_eq_expr(self, p):
        return Assignment(p[0], p[2], lineno=p[0].lineno)

    @pg.production("expr_without_variable : rw_variable T_INC")
    @pg.production("expr_without_variable : rw_variable T_DEC")
    def expr_without_variable_variable_rw_var_t_inc_dec(self, p):
        return SuffixOp(p[1].getstr(), p[0], lineno=p[1].getsourcepos())

    @pg.production("expr_without_variable : T_INC rw_variable")
    @pg.production("expr_without_variable : T_DEC rw_variable")
    def expr_without_variable_variable_t_inc_dec_rw_var(self, p):
        return PrefixOp(p[0].getstr(), p[1], lineno=p[0].getsourcepos())

    @pg.production("expr_without_variable : expr + expr")
    @pg.production("expr_without_variable : expr - expr")
    @pg.production("expr_without_variable : expr * expr")
    @pg.production("expr_without_variable : expr / expr")
    @pg.production("expr_without_variable : expr > expr")
    @pg.production("expr_without_variable : expr < expr")
    def expr_oper_expr(self, p):
        return BinOp(p[1].getstr(), p[0], p[2], lineno=p[1].getsourcepos())

    @pg.production("expr_without_variable : expr T_BOOLEAN_OR expr")
    def expr_or_expr(self, p):
        return Or(p[0], p[2], lineno=p[1].getsourcepos())

    @pg.production("expr_without_variable : expr T_BOOLEAN_AND expr")
    def expr_and_expr(self, p):
        return And(p[0], p[2], lineno=p[1].getsourcepos())

    @pg.production("expr_without_variable : variable T_PLUS_EQUAL expr")
    def expr_variable_inplaceop_expr(self, p):
        return InplaceOp(p[1].getstr(), p[0], p[2])

    @pg.production("expr : - expr", precedence="T_DEC")
    @pg.production("expr : + expr", precedence="T_INC")
    def expr_h_minus_expr(self, p):
        return PrefixOp(p[0].getstr(), p[1], lineno=p[0].getsourcepos())

    @pg.production("expr : ( expr )")
    def expr_bracket_expr_bracket(self, p):
        return p[1]

    @pg.production("expr : scalar")
    def expr_scalar(self, p):
        raise NotImplementedError(p)

    @pg.production("expr : T_PRINT expr")
    def expr_t_print_expr(self, p):
        return Echo(p[1], lineno=p[0].getsourcepos())

    @pg.production("scalar : T_STRING_VARNAME")
    def scalar_t_string_varname(self, p):
        raise NotImplementedError(p)

    @pg.production("scalar : namespace_name")
    def scalar_namespace_name(self, p):
        return NamedConstant(p[0].getstr(), p[0].getsourcepos())

    @pg.production("scalar : common_scalar")
    def scalar_common_scalar(self, p):
        return p[0]

    @pg.production("common_scalar : T_LNUMBER")
    @pg.production("common_scalar : T_DNUMBER")
    @pg.production("common_scalar : T_CONSTANT_ENCAPSED_STRING")
    @pg.production("common_scalar : T_LINE")
    @pg.production("common_scalar : T_FILE")
    @pg.production("common_scalar : T_DIR")
    @pg.production("common_scalar : T_TRAIT_C")
    @pg.production("common_scalar : T_METHOD_C")
    @pg.production("common_scalar : T_FUNC_C")
    @pg.production("common_scalar : T_NS_C")
    def common_scalar_lnumber(self, p):
        lineno = p[0].getsourcepos()
        if p[0].gettokentype() == 'T_LNUMBER':
            return ConstantInt(int(p[0].getstr()), lineno=lineno)
        if p[0].gettokentype() == 'T_DNUMBER':
            return ConstantFloat(float(p[0].getstr()), lineno=lineno)
        if p[0].gettokentype() == 'T_CONSTANT_ENCAPSED_STRING':
            return ConstantStr(p[0].getstr().strip("\""), lineno=lineno)
        raise Exception("Not implemented yet!")


    @pg.production("static_scalar : common_scalar")
    def static_scalar_common_scalar(self, p):
        return p[0]

    @pg.production("static_scalar : namespace_name")
    def static_scalar_namespace_name(self, p):
        return p[0]

    @pg.production("variable : base_variable_with_function_calls")
    def variable_base_variable_with_function_calls(self, p):
        return p[0]

    @pg.production("base_variable_with_function_calls : base_variable")
    def base_variable_with_function_calls_base_variable(self, p):
        return p[0]


    @pg.production("base_variable_with_function_calls : function_call")
    def base_variable_with_function_calls_function_call(self, p):
        return p[0]

    @pg.production("base_variable : reference_variable")
    def base_variable_reference_variable(self, p):
        return p[0]

    @pg.production("base_variable : simple_indirect_reference reference_variable")
    def base_variable_reference_variable(self, p):
        return Variable(p[1], lineno=p[1].lineno)

    @pg.production("reference_variable : compound_variable")
    def reference_variable_compound_variable(self, p):
        return p[0]

    @pg.production("reference_variable : "
                   "reference_variable [ dim_offset ]")
    def reference_variable_reference_variable_offset(self, p):
        if p[2] is None:
            raise NotImplementedError(p)
        return GetItem(p[0], p[2], lineno=p[1].getsourcepos())

    @pg.production("dim_offset : empty")
    def dim_offset_empty(self, p):
        return p[0]

    @pg.production("dim_offset : expr")
    def dim_offset_expr(self, p):
        return p[0]

    @pg.production("compound_variable : T_VARIABLE")
    def compound_variable_t_variable(self, p):
        lineno = p[0].getsourcepos()
        return Variable(ConstantStr(p[0].getstr()[1:], lineno=lineno), lineno=lineno)

    @pg.production("compound_variable : $ { expr }")
    def compound_variable_expr(self, p):
        return Variable(p[2], lineno=p[0].getsourcepos())

    @pg.production("r_variable : variable")
    def variable_r_variable(self, p):
        return p[0]

    @pg.production("rw_variable : variable")
    def variable_rw_variable(self, p):
        return p[0]

    @pg.production("w_variable : variable")
    def variable_rw_variable(self, p):
        return p[0]

    @pg.production("unticked_statement : T_ECHO echo_expr_list ;")
    def unticked_statement_t_echo_expr_list(self, p):
        return Echo(p[1], lineno=p[0].getsourcepos())

    @pg.production("unticked_statement : T_DO statement "
                   "T_WHILE ( expr ) ;")
    def unticked_statement_t_do(self, p):
        return DoWhile(p[1], p[4], lineno=p[0].getsourcepos())

    @pg.production("echo_expr_list : echo_expr_list , expr")
    def echo_expr_list_echo_expr_list_expr(self, p):
        if isinstance(p[0], list):
            if p[2]:
                if p[0] is None:
                    return p[2]
                p[0].append(p[2])
                return p[0]
            return p[0]
        if p[0] is None:
            return p[2]
        return [p[0], p[2]]

    @pg.production("echo_expr_list : expr")
    def echo_expr_list_expr(self, p):
        return [p[0]]

    @pg.production("unticked_statement : T_RETURN ;")
    def unticked_statement_t_return(self, p):
        return Return(None, lineno=p[0].getsourcepos())

    @pg.production("unticked_statement : T_RETURN expr_without_variable ;")
    def unticked_statement_t_return_expr_wo_variable(self, p):
        return Return(p[1], lineno=p[0].getsourcepos())

    @pg.production("unticked_statement : T_RETURN variable ;")
    def unticked_statement_t_return_variable(self, p):
        return Return(p[1], lineno=p[0].getsourcepos())

    @pg.production("unticked_statement : T_GLOBAL global_var_list ;")
    def unticked_statement_t_global_global_var_list(self, p):
        return Global(p[1], lineno=p[0].getsourcepos())

    @pg.production("global_var_list : global_var_list , global_var")
    def global_var_list_global_var_list_global_var(self, p):
        print p
        if isinstance(p[0], list):
            p[0].append(p[2])
            return p[0]
        return p[2]

    @pg.production("global_var_list : global_var")
    def global_var_list_global_var(self, p):
        return [p[0]]

    @pg.production("global_var : T_VARIABLE")
    def global_var_t_variable(self, p):
        return p[0].getstr()[1:]

    @pg.production("global_var : $ r_variable")
    def global_var_dollar_r_variable(self, p):
        raise NotImplementedError(p)

    @pg.production("global_var : $ { expr }")
    def global_var_expr(self, p):
        raise NotImplementedError(p)

    @pg.production("unticked_statement : T_IF ( expr ) "
                   "statement elseif_list else_single")
    def unticked_statement_if_statement_elseif_else_single(self, p):
        return If(p[2],
                  p[4],
                  elseiflist=p[5],
                  elseclause=p[6],
                  lineno=p[0].getsourcepos())

    @pg.production("unticked_statement : T_IF ( expr ) : "
                   "inner_statement_list new_elseif_list "
                   "new_else_single T_ENDIF ;")
    def unticked_statement_if_inner_statement_elseif_else_single(self, p):
        raise NotImplementedError(p)

    @pg.production("elseif_list : empty")
    def elseif_list_empty(self, p):
        return p[0]

    @pg.production("elseif_list : elseif_list T_ELSEIF ( expr ) statement")
    def elseif_list_elseif_list(self, p):
        if isinstance(p[0], list):
            _if = If(p[3], p[5], lineno=p[1].getsourcepos())
            p[0].append(_if)
            return p[0]
        if p[0] is None:
            return [If(p[3], p[5], lineno=p[1].getsourcepos())]

    @pg.production("new_elseif_list : new_elseif_list "
                   "T_ELSEIF ( expr ) : inner_statement_list")
    def new_elseif_list_new_elseif_list(self, p):
        raise NotImplementedError(p)

    @pg.production("new_elseif_list : empty")
    def new_elseif_list_empty(self, p):
        raise NotImplementedError(p)

    @pg.production("else_single : T_ELSE statement")
    def else_single_t_else_statement(self, p):
        return p[1]

    @pg.production("else_single : empty")
    def else_single_empty(self, p):
        return p[0]

    @pg.production("new_else_single : T_ELSE : inner_statement_list")
    def new_else_single_t_else(self, p):
        raise NotImplementedError(p)

    @pg.production("new_else_single : empty")
    def new_else_single_empty(self, p):
        return p[0]


    @pg.production("unticked_statement : T_WHILE "
                   "( expr ) while_statement")
    def unticked_statement_t_while(self, p):
        return While(p[2], p[4], lineno=p[0].getsourcepos())

    @pg.production("while_statement : statement")
    def while_stmt_stmt(self, p):
        return p[0]

    @pg.production("while_statement : "
                   ": inner_statement_list T_ENDWHILE ;")
    def while_stmt_inner_stmt_list(self, p):
        raise NotImplementedError(p)

    @pg.production("unticked_statement : T_FOR "
                   "( for_expr ; "
                   "for_expr ; for_expr ) for_statement")
    def unticked_statement_t_for(self, p):
        return For(p[2], p[4], p[6], p[8], lineno=p[0].getsourcepos())

    @pg.production("for_expr : non_empty_for_expr")
    def for_expr_non_empty_for_expr(self, p):
        return p[0]

    @pg.production("for_expr : empty")
    def for_expr_empty(self, p):
        raise NotImplementedError(p)

    @pg.production("non_empty_for_expr : non_empty_for_expr , expr")
    def non_empty_for_expr_non_empty_for_expr_expr(self, p):
        raise NotImplementedError(p)

    @pg.production("non_empty_for_expr : expr")
    def non_empty_for_expr_expr(self, p):
        return p[0]

    @pg.production("for_statement : statement")
    def for_stmt_stmt(self, p):
        return p[0]

    @pg.production("for_statement : "
                   ": inner_statement_list T_ENDFOR ;")
    def for_stmt_inner_stmt_list(self, p):
        raise NotImplementedError(p)


    @pg.production("simple_indirect_reference : $")
    def simple_indirect_reference(self, p):
        return p[0]

    @pg.production("simple_indirect_reference : "
                   "simple_indirect_reference $")
    def simple_indirect_reference_simple_indirect_reference(self, p):
        raise NotImplementedError(p)


    @pg.production("function_call : "
                   "namespace_name "
                   "( function_call_parameter_list )")
    def function_call_cn_t_paamayim_variable_wo_f_call_p_list(self, p):
        return SimpleCall(p[0].getstr(), p[2], lineno=p[0].getsourcepos())

    @pg.production("function_call : "
                   "variable_without_objects "
                   "( function_call_parameter_list )")
    def function_call_cn_t_paamayim_variable_wo_f_call_p_list(self, p):
        return DynamicCall(p[0], p[2], lineno=p[1].getsourcepos())

    @pg.production("variable_without_objects : reference_variable")
    def variable_without_objects_reference_variable(self, p):
        return p[0]

    @pg.production("variable_without_objects : "
                   "simple_indirect_reference reference_variable")
    def variable_without_objects_simple_i_ref_reference_variable(self, p):
        raise NotImplementedError(p)

    @pg.production("namespace_name : T_STRING")
    def namespace_name_t_string(self, p):
        return p[0]

    @pg.production("namespace_name :  namespace_name T_NS_SEPARATOR T_STRING")
    def namespace_name_namespace_name_t_ns_sep_t_string(self, p):
        raise NotImplementedError(p)

    @pg.production("function_call_parameter_list : "
                   "non_empty_function_call_parameter_list")
    def function_call_parameter_list_non_empty_function(self, p):
        return p[0]

    @pg.production("function_call_parameter_list : empty")
    def function_call_parameter_list_empty(self, p):
        return []

    @pg.production("non_empty_function_call_parameter_list : "
                   "expr_without_variable")
    def non_empty_function_call_parameter_list_expr_wo_variable(self, p):
        return [p[0]]

    @pg.production("non_empty_function_call_parameter_list : "
                   "variable")
    def non_empty_function_call_parameter_list_variable(self, p):
        raise NotImplementedError(p)

    @pg.production("non_empty_function_call_parameter_list : "
                   "& w_variable")
    def non_empty_function_call_parameter_list_reference_variable(self, p):
        raise NotImplementedError(p)

    @pg.production("non_empty_function_call_parameter_list : "
                   "non_empty_function_call_parameter_list , "
                   "expr_without_variable")
    def non_empty_function_call_parameter_list_list_expr_wo_variable(self, p):
        if p[0] is not None:
            if isinstance(p[0], list):
                p[0].append(p[2])
                return p[0]
            return [p[0], p[2]]

    @pg.production("non_empty_function_call_parameter_list : "
                   "non_empty_function_call_parameter_list , variable")
    def non_empty_function_call_parameter_list_list_variable(self, p):
        raise NotImplementedError(p)

    @pg.production("non_empty_function_call_parameter_list : "
                   "non_empty_function_call_parameter_list , "
                   "& w_variable")
    def non_empty_function_call_parameter_list_list_ref_variable(self, p):
        raise NotImplementedError(p)

    @pg.production("function : T_FUNCTION")
    def function_t_function(self, p):
        return p[0]

    @pg.production("function_declaration_statement : "
                   "unticked_function_declaration_statement")
    def function_declaration_statement_unticked_f_decl_stmt(self, p):
        return p[0]

    @pg.production("unticked_function_declaration_statement : "
               "function is_reference T_STRING ( parameter_list ) "
                " { inner_statement_list }")
    def unticked_func_decl_stmt_f_is_ref_param_list_inner_stmt_lst(self, p):
        ist = p[7]
        if ist is None:
            ist = Block([], lineno=p[6].getsourcepos())
        else:
            ist = Block(p[7], lineno=p[6].getsourcepos())
        return FunctionDecl(p[2].getstr(), p[4], ist, lineno=p[0].getsourcepos())

    @pg.production("is_reference : &")
    def is_reference_reference(self, p):
        raise NotImplementedError(p)

    @pg.production("is_reference : empty")
    def is_reference_empty(self, p):
        return p[0]


    @pg.production("parameter_list : non_empty_parameter_list")
    def parameter_list_non_empty_parameter_list(self, p):
        return p[0]

    @pg.production("parameter_list : empty")
    def parameter_list_empty(self, p):
        return []

    @pg.production("non_empty_parameter_list : "
                   "optional_class_type T_VARIABLE")
    def nepl_optional_class_type_t_var(self, p):
        if p[0] is None:
            lineno = p[1].getsourcepos()
            return [Argument(p[1].getstr()[1:], lineno=lineno)]
        raise NotImplementedError(p)

    @pg.production("non_empty_parameter_list : "
                   "non_empty_parameter_list , optional_class_type T_VARIABLE")
    def nepl_nepl_optional_class_type_t_var(self, p):
        print p
        lineno = p[3].getsourcepos()
        tvar = Argument(p[3].getstr()[1:], lineno=lineno)

        if p[2] is not None:
            raise NotImplementedError(p)
        if p[0] is not None:
            if isinstance(p[0], list):
                p[0].append(tvar)
                return p[0]
            return [p[0], tvar]
        raise NotImplementedError(p)

    @pg.production("non_empty_parameter_list : "
                   "optional_class_type & T_VARIABLE")
    def nepl_optional_class_type_h_ref_t_var(self, p):
        if p[0] is None:
            lineno = p[2].getsourcepos()
            return [ReferenceArgument(p[2].getstr()[1:], lineno=lineno)]
        raise NotImplementedError(p)

    @pg.production("non_empty_parameter_list : "
                   "non_empty_parameter_list , "
                   "optional_class_type & T_VARIABLE")
    def nepl_nepl_optional_class_type_h_ref_t_var(self, p):
        raise NotImplementedError(p)

    @pg.production("non_empty_parameter_list : "
                   "optional_class_type T_VARIABLE = static_scalar")
    def nepl_optional_class_type_t_var_static_scalar(self, p):
        raise NotImplementedError(p)

    @pg.production("non_empty_parameter_list : "
                   "non_empty_parameter_list , optional_class_type"
                   " T_VARIABLE = static_scalar")
    def nepl_nepl_optional_class_type_t_var_static_scalar(self, p):
        raise NotImplementedError(p)

    @pg.production("non_empty_parameter_list : "
                   "optional_class_type "
                   "& T_VARIABLE = static_scalar")
    def nepl_optional_class_type_h_ref_t_var_static_scalar(self, p):
        raise NotImplementedError(p)

    @pg.production("optional_class_type : fully_qualified_class_name")
    def optional_class_type_fqcn(self, p):
        raise NotImplementedError(p)

    @pg.production("optional_class_type : T_ARRAY")
    def optional_class_type_t_array(self, p):
        raise NotImplementedError(p)

    @pg.production("optional_class_type : empty")
    def optional_class_type_empty(self, p):
        return p[0]

    @pg.production("fully_qualified_class_name : namespace_name")
    def fqcn_namespace_name(self, p):
        raise NotImplementedError(p)

    @pg.production("fully_qualified_class_name : "
                   "T_NAMESPACE T_NS_SEPARATOR namespace_name")
    def fqcn_t_namespace_t_ns_sep_namespace_name(self, p):
        raise NotImplementedError(p)

    @pg.production("fully_qualified_class_name : "
                   "T_NS_SEPARATOR namespace_name")
    def fqcn_t_ns_sep_namespace_name(self, p):
        raise NotImplementedError(p)

    @pg.production("expr_without_variable : combined_scalar")
    def expr_expr_without_variable_array(self, p):
        return p[0]

    @pg.production("combined_scalar : T_ARRAY ( array_pair_list )")
    def combined_scalar_t_array_array_pair_list(self, p):
        return Array(p[2], p[0].getsourcepos())

    @pg.production("combined_scalar : [ array_pair_list ]")
    def combined_scalar_square_bracket_array_pair_list(self, p):
        return Array(p[1], p[0].getsourcepos())

    @pg.production("array_pair_list : "
                   "non_empty_array_pair_list possible_comma")
    def array_pair_list_non_empty(self, p):
        return p[0]

    @pg.production("array_pair_list : empty")
    def array_pair_list_empty(self, p):
        return []

    @pg.production("non_empty_array_pair_list : "
                   "non_empty_array_pair_list , expr T_DOUBLE_ARROW expr")
    def non_empty_array_pair_list_list_expr_da_expr(self, p):
        raise NotImplementedError(p)

    @pg.production("non_empty_array_pair_list : "
                   "expr T_DOUBLE_ARROW expr")
    def non_empty_array_pair_list_expr_da_expr(self, p):
        raise NotImplementedError(p)

    @pg.production("non_empty_array_pair_list : "
                   "non_empty_array_pair_list , expr")
    def non_empty_array_pair_list_list_expr(self, p):
        if p[0] is not None:
            p[0].append(p[2])
            return p[0]
        raise NotImplementedError(p)

    @pg.production("non_empty_array_pair_list : expr")
    def non_empty_array_pair_list_expr(self, p):
        return [p[0]]

    @pg.production("non_empty_array_pair_list : "
                   "non_empty_array_pair_list , "
                   "static_scalar T_DOUBLE_ARROW static_scalar")
    def non_empty_array_pair_list_list_scalar_assign_scalar(self, p):
        raise NotImplementedError(p)


    @pg.production("possible_comma : empty")
    def possible_comma_empty(self, p):
        return p[0]

    @pg.production("possible_comma : ,")
    def possible_comma(self, p):
        raise NotImplementedError(p)


    @pg.production("empty :")
    def empty(self, p):
        return None

    @pg.error
    def error_handler(self, token):
        raise ValueError("syntax error, unexpected \'%s\' line(%s)" %
                         (token.gettokentype(),
                          token.getsourcepos())
                         )

    parser = pg.build()


def parse(_source):
    lx = Lexer(RULES, skip_whitespace=False)
    lx.input(_source)
    parser = Parser(lx.tokens())
    return parser.parse()
