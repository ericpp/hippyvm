from hippy.rply import ParserGenerator
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


class GetItemReference(GetItem):
    pass


class SetItem(Node):
    def __init__(self, node, item, value):
        self.node = node
        self.item = item
        self.value = value

    def repr(self):
        return 'SetItem(%s, %s, %s)' % (self.node.repr(), self.item.repr(),
                                        self.value.repr())


class InplaceSetItem(Node):
    def __init__(self, op, node, item, value):
        self.op = op
        self.node = node
        self.item = item
        self.value = value

    def repr(self):
        return 'InplaceSetItem(%s, %s, %s, %s)' % (self.op, self.node.repr(),
                                                   self.item.repr(),
                                                   self.value.repr())


class Array(Node):
    def __init__(self, initializers):
        self.initializers = initializers

    def repr(self):
        return 'Array([%s])' % ', '.join([i.repr() for i in self.initializers])


class Hash(Node):
    def __init__(self, initializers):
        self.initializers = initializers

    def repr(self):
        return 'Hash([%s])' % ', '.join([
                "(%s => %s)" %
                (k.repr(), v.repr()) for k, v in self.initializers])


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
        print p[0]
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
        raise NotImplementedError(p)

    @pg.production("top_statement : class_declaration_statement")
    def top_statement_class_declaration_statement(self, p):
        raise NotImplementedError(p)

    @pg.production("top_statement : T_HALT_COMPILER H_LB H_RB H_END_STMT")
    def top_statement_t_halt_compiler(self, p):
        raise NotImplementedError(p)

    @pg.production("top_statement : T_NAMESPACE namespace_name H_END_STMT")
    def top_statement_t_namespace_namespace_name(self, p):
        raise NotImplementedError(p)

    @pg.production("top_statement : T_NAMESPACE namespace_name "
                   "H_L_CB top_statement_list H_R_CB")
    def top_statement_t_namespace_namespace_name_top_stmt_list(self, p):
        raise NotImplementedError(p)

    @pg.production("top_statement : T_USE use_declarations H_END_STMT")
    def top_statement_t_use_use_declarations(self, p):
        raise NotImplementedError(p)

    @pg.production("top_statement : constant_declaration H_END_STMT")
    def top_statement_constant_declaration(self, p):
        raise NotImplementedError(p)

    @pg.production("constant_declaration : constant_declaration"
                   " , T_STRING H_EQUAL static_scalar")
    def constant_declaration_constant_decl_scalar(self, p):
        raise NotImplementedError(p)

    @pg.production("constant_declaration : T_CONST"
                   " T_STRING H_EQUAL static_scalar")
    def constant_declaration_t_const_scalar(self, p):
        raise NotImplementedError(p)

    @pg.production("use_declarations : use_declarations , use_declaration")
    def use_declarations_use_declarations_use_declaration(self, p):
        raise NotImplementedError(p)

    @pg.production("use_declarations : use_declaration")
    def use_declarations_use_declaration(self, p):
        raise NotImplementedError(p)

    @pg.production("function_declaration_statement : "
                   "unticked_function_declaration_statement")
    def function_declaration_statement_unticked_f_decl_stmt(self, p):
        raise NotImplementedError(p)

    @pg.production("unticked_function_declaration_statement : "
               "function is_reference T_STRING H_LB parameter_list H_RB "
                " H_L_CB inner_statement_list H_R_CB")
    def unticked_func_decl_stmt_f_is_ref_param_list_inner_stmt_lst(self, p):
        raise NotImplementedError(p)

    @pg.production("inner_statement_list : "
                   "inner_statement_list inner_statement")
    def inner_statement_list_inner_statement_list_inner_statement(self, p):
        raise NotImplementedError(p)

    @pg.production("function : T_FUNCTION")
    def function_t_function(self, p):
        raise NotImplementedError(p)

    @pg.production("class_declaration_statement : "
                   "unticked_class_declaration_statement")
    def class_declaration_statement_unticked_class_decl_stmt(self, p):
        raise NotImplementedError(p)

    @pg.production("inner_statement : statement")
    def inner_statement_statement(self, p):
        raise NotImplementedError(p)

    @pg.production("inner_statement : function_declaration_statement")
    def inner_statement_function_declaration_statement(self, p):
        raise NotImplementedError(p)

    @pg.production("inner_statement : class_declaration_statement")
    def inner_statement_class_declaration_statement(self, p):
        raise NotImplementedError(p)

    @pg.production("inner_statement : T_HALT_COMPILER H_LB H_RB H_END_STMT")
    def inner_statement_halt(self, p):
        raise NotImplementedError(p)

    @pg.production("is_reference : H_REFERENCE")
    def is_reference_reference(self, p):
        raise NotImplementedError(p)

    @pg.production("is_reference : empty")
    def is_reference_empty(self, p):
        raise NotImplementedError(p)

    @pg.production("unticked_class_declaration_statement : "
                   "class_entry_type T_STRING extends_from implements_list "
                   "H_L_CB class_statement_list H_R_CB")
    def unticked_class_declaration_statemet_class_entry_type(self, p):
        raise NotImplementedError(p)

    @pg.production("unticked_class_declaration_statement : "
                   "interface_entry T_STRING interface_extends_list "
                   "H_L_CB class_statement_list H_R_CB")
    def unticked_class_declaration_statemet_interface_entry(self, p):
        raise NotImplementedError(p)

    @pg.production("class_entry_type : T_CLASS")
    def class_entry_type_t_class(self, p):
        raise NotImplementedError(p)

    @pg.production("class_entry_type : T_ABSTRACT T_CLASS")
    def class_entry_type_t_abstract_t_class(self, p):
        raise NotImplementedError(p)

    @pg.production("class_entry_type : T_FINAL T_CLASS")
    def class_entry_type_t_final_t_class(self, p):
        raise NotImplementedError(p)

    @pg.production("extends_from : T_EXTENDS fully_qualified_class_name")
    def extends_from_t_extends_fully_qual_class_name(self, p):
        raise NotImplementedError(p)

    @pg.production("class_statement_list : "
                   "class_statement_list class_statement")
    def class_statement_list_class_statement_list_class_statement(self, p):
        raise NotImplementedError(p)

    @pg.production("class_statement_list : empty")
    def class_statement_list_empty(self, p):
        raise NotImplementedError(p)

    @pg.production("class_statement : variable_modifiers "
                   "class_variable_declaration H_END_STMT")
    def class_statement_variable_modifiers_class_var_declaration(self, p):
        raise NotImplementedError(p)

    @pg.production("class_statement : class_constant_declaration H_END_STMT")
    def class_statement_class_const_declaration(self, p):
        raise NotImplementedError(p)

    @pg.production("class_statement : method_modifiers function"
                   " is_reference T_STRING H_LB "
                   "parameter_list H_RB method_body")
    def class_statement_method_modifiers_function(self, p):
        raise NotImplementedError(p)

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

    @pg.production("implements_list : T_IMPLEMENTS interface_list")
    def implements_list_t_implements_interface_list(self, p):
        raise NotImplementedError(p)

    @pg.production("implements_list : empty")
    def implements_list_empty(self, p):
        raise NotImplementedError(p)

    @pg.production("interface_list : interface_list"
                   " , fully_qualified_class_name")
    def interface_list_interface_list_fqcn(self, p):
        raise NotImplementedError(p)

    @pg.production("interface_list : fully_qualified_class_name")
    def interface_list_fqcn(self, p):
        raise NotImplementedError(p)

    @pg.production("class_constant_declaration : "
                   "class_constant_declaration , "
                   "T_STRING H_EQUAL static_scalar")
    def class_constant_decl_class_constant_decl_t_string(self, p):
        raise NotImplementedError(p)

    @pg.production("class_constant_declaration : "
                   "T_CONST T_STRING H_EQUAL static_scalar")
    def class_constant_decl_class_constant_decl_t_const_t_string(self, p):
        raise NotImplementedError(p)

    @pg.production("method_body : H_END_STMT")
    def method_body_end_stmt(self, p):
        raise NotImplementedError(p)

    @pg.production("method_body : H_L_CB inner_statement_list H_R_CB")
    def method_body_inner_stmt_list(self, p):
        raise NotImplementedError(p)

    @pg.production("variable_modifiers : non_empty_member_modifiers")
    def variable_modifiers_non_empty_member_modifiers(self, p):
        raise NotImplementedError(p)

    @pg.production("variable_modifiers : T_VAR")
    def variable_modifiers_t_var(self, p):
        raise NotImplementedError(p)

    @pg.production("non_empty_member_modifiers : "
                   "non_empty_member_modifiers member_modifier")
    def non_empty_member_modifiers_non_empty_member_modifiers(self, p):
        raise NotImplementedError(p)

    @pg.production("member_modifier : T_PUBLIC")
    @pg.production("member_modifier : T_PROTECTED")
    @pg.production("member_modifier : T_PRIVATE")
    @pg.production("member_modifier : T_STATIC")
    @pg.production("member_modifier : T_ABSTRACT")
    @pg.production("member_modifier : T_FINAL")
    def member_modifier(self, p):
        raise NotImplementedError(p)

    @pg.production("non_empty_member_modifiers : "
                   "member_modifier")
    def non_empty_member_modifiers_member_modifier(self, p):
        raise NotImplementedError(p)

    @pg.production("interface_extends_list : T_EXTENDS interface_list")
    def interface_extends_list_t_extends(self, p):
        raise NotImplementedError(p)

    @pg.production("interface_extends_list : empty")
    def interface_extends_list_empty(self, p):
        raise NotImplementedError(p)

    @pg.production("method_modifiers : non_empty_member_modifiers")
    def method_modifiers_non_empty_member_modifiers(self, p):
        raise NotImplementedError(p)

    @pg.production("method_modifiers : empty")
    def method_modifiers_empty(self, p):
        raise NotImplementedError(p)

    @pg.production("non_empty_member_modifiers : "
                   "non_empty_member_modifiers member_modifier")
    def ne_member_modifiers_ne_member_modifiers_member_modifier(self, p):
        raise NotImplementedError(p)

    @pg.production("non_empty_member_modifiers : "
                   "member_modifier")
    def ne_member_modifiers_member_modifier(self, p):
        raise NotImplementedError(p)

    @pg.production("optional_class_type : fully_qualified_class_name")
    def optional_class_type_fqcn(self, p):
        raise NotImplementedError(p)

    @pg.production("optional_class_type : T_ARRAY")
    def optional_class_type_t_array(self, p):
        raise NotImplementedError(p)

    @pg.production("optional_class_type : empty")
    def optional_class_type_empty(self, p):
        raise NotImplementedError(p)

    @pg.production("class_variable_declaration : "
                   "class_variable_declaration , T_VARIABLE")
    def class_vdecl_class_vdecl_t_var(self, p):
        raise NotImplementedError(p)

    @pg.production("class_variable_declaration : "
                   "class_variable_declaration , "
                   "T_VARIABLE H_EQUAL static_scalar")
    def class_vdecl_class_vdecl_t_var_static_scalar(self, p):
        raise NotImplementedError(p)

    @pg.production("class_variable_declaration : T_VARIABLE")
    def class_vdecl_t_var(self, p):
        raise NotImplementedError(p)

    @pg.production("class_variable_declaration : "
                   "T_VARIABLE H_EQUAL static_scalar")
    def class_vdecl_t_var_static_scalar(self, p):
        raise NotImplementedError(p)

    @pg.production("interface_entry : T_INTERFACE")
    def interface_entry_t_interface(self, p):
        raise NotImplementedError(p)

    @pg.production("parameter_list : non_empty_parameter_list")
    def parameter_list_non_empty_parameter_list(self, p):
        raise NotImplementedError(p)

    @pg.production("parameter_list : empty")
    def parameter_list_empty(self, p):
        raise NotImplementedError(p)

    @pg.production("non_empty_parameter_list : "
                   "optional_class_type T_VARIABLE")
    def nepl_optional_class_type_t_var(self, p):
        raise NotImplementedError(p)

    @pg.production("non_empty_parameter_list : "
                   "non_empty_parameter_list , optional_class_type T_VARIABLE")
    def nepl_nepl_optional_class_type_t_var(self, p):
        raise NotImplementedError(p)

    @pg.production("non_empty_parameter_list : "
                   "optional_class_type H_REFERENCE T_VARIABLE")
    def nepl_optional_class_type_h_ref_t_var(self, p):
        raise NotImplementedError(p)

    @pg.production("non_empty_parameter_list : "
                   "non_empty_parameter_list , "
                   "optional_class_type H_REFERENCE T_VARIABLE")
    def nepl_nepl_optional_class_type_h_ref_t_var(self, p):
        raise NotImplementedError(p)

    @pg.production("non_empty_parameter_list : "
                   "optional_class_type T_VARIABLE H_EQUAL static_scalar")
    def nepl_optional_class_type_t_var_static_scalar(self, p):
        raise NotImplementedError(p)

    @pg.production("non_empty_parameter_list : "
                   "non_empty_parameter_list , optional_class_type"
                   " T_VARIABLE H_EQUAL static_scalar")
    def nepl_nepl_optional_class_type_t_var_static_scalar(self, p):
        raise NotImplementedError(p)

    @pg.production("non_empty_parameter_list : "
                   "optional_class_type "
                   "H_REFERENCE T_VARIABLE H_EQUAL static_scalar")
    def nepl_optional_class_type_h_ref_t_var_static_scalar(self, p):
        raise NotImplementedError(p)

    @pg.production("inner_statement_list : empty")
    def inner_statement_list_empty(self, p):
        raise NotImplementedError(p)

    @pg.production("use_declaration : namespace_name")
    def use_declaration_namespace_name(self, p):
        raise NotImplementedError(p)

    @pg.production("use_declaration : namespace_name T_AS T_STRING")
    def use_declaration_namespace_name_as_string(self, p):
        raise NotImplementedError(p)

    @pg.production("use_declaration : T_NS_SEPARATOR namespace_name")
    def use_declaration_t_ns_namespace_namespace_name(self, p):
        raise NotImplementedError(p)

    @pg.production("use_declaration : T_NS_SEPARATOR "
                   "namespace_name T_AS T_STRING")
    def use_declaration_t_ns_namespace_namespace_name_as_string(self, p):
        raise NotImplementedError(p)

    @pg.production("statement : unticked_statement")
    def statement(self, p):
        return p[0]

    @pg.production("unticked_statement : expr H_END_STMT")
    def unticked_statement_expr(self, p):
        return Stmt(p[0])

    @pg.production("unticked_statement : H_L_CB inner_statement_list H_R_CB")
    def unticked_statement_inner_statement_list(self, p):
        raise NotImplementedError(p)

    @pg.production("unticked_statement : T_IF H_LB expr H_RB "
                   "statement elseif_list else_single")
    def unticked_statement_if_statement_elseif_else_single(self, p):
        raise NotImplementedError(p)

    @pg.production("unticked_statement : T_IF H_LB expr H_RB H_COLON "
                   "inner_statement_list new_elseif_list "
                   "new_else_single T_ENDIF H_END_STMT")
    def unticked_statement_if_inner_statement_elseif_else_single(self, p):
        raise NotImplementedError(p)

    @pg.production("unticked_statement : T_WHILE "
                   "H_LB expr H_RB while_statement")
    def unticked_statement_t_while(self, p):
        raise NotImplementedError(p)

    @pg.production("unticked_statement : T_DO statement "
                   "T_WHILE H_LB expr H_RB H_END_STMT")
    def unticked_statement_t_do(self, p):
        raise NotImplementedError(p)

    @pg.production("unticked_statement : T_FOR "
                   "H_LB for_expr H_END_STMT "
                   "for_expr H_END_STMT for_expr H_RB for_statement")
    def unticked_statement_t_for(self, p):
        raise NotImplementedError(p)

    @pg.production("unticked_statement : "
                   "T_SWITCH H_LB expr H_RB switch_case_list")
    def unticked_statement_t_switch(self, p):
        raise NotImplementedError(p)

    @pg.production("unticked_statement : T_BREAK H_END_STMT")
    def unticked_statement_t_break(self, p):
        raise NotImplementedError(p)

    @pg.production("unticked_statement : T_BREAK expr H_END_STMT")
    def unticked_statement_t_break_expr(self, p):
        raise NotImplementedError(p)

    @pg.production("unticked_statement : T_CONTINUE H_END_STMT")
    def unticked_statement_t_continue(self, p):
        raise NotImplementedError(p)

    @pg.production("unticked_statement : T_CONTINUE expr H_END_STMT")
    def unticked_statement_t_continue_expr(self, p):
        raise NotImplementedError(p)

    @pg.production("unticked_statement : T_RETURN H_END_STMT")
    def unticked_statement_t_return(self, p):
        raise NotImplementedError(p)

    @pg.production("unticked_statement : T_RETURN "
                   "expr_without_variable H_END_STMT")
    def unticked_statement_t_return_expr_wo_variable(self, p):
        raise NotImplementedError(p)

    @pg.production("unticked_statement : T_RETURN variable H_END_STMT")
    def unticked_statement_t_return_variable(self, p):
        raise NotImplementedError(p)

    @pg.production("unticked_statement : T_GLOBAL global_var_list H_END_STMT")
    def unticked_statement_t_global_global_var_list(self, p):
        raise NotImplementedError(p)

    @pg.production("unticked_statement : T_STATIC static_var_list H_END_STMT")
    def unticked_statement_t_static_static_var_list(self, p):
        raise NotImplementedError(p)

    @pg.production("unticked_statement : T_ECHO echo_expr_list H_END_STMT")
    def unticked_statement_t_echo_expr_list(self, p):
        raise NotImplementedError(p)

    #@pg.production("unticked_statement : T_INLINE_HTML")

    @pg.production("unticked_statement : T_UNSET "
                   "H_LB unset_variables H_RB H_END_STMT")
    def unticked_statement_t_unset_variables(self, p):
        raise NotImplementedError(p)

    @pg.production("unticked_statement : T_FOREACH "
                   "H_LB variable T_AS foreach_variable "
                   "foreach_optional_arg H_RB foreach_statement")
    def unticked_statement_t_for_each_variable(self, p):
        raise NotImplementedError(p)

    @pg.production("unticked_statement : T_FOREACH "
                   "H_LB expr_without_variable T_AS "
                   "variable foreach_optional_arg H_RB foreach_statement")
    def unticked_statement_t_for_each_expr_wo_variable(self, p):
        raise NotImplementedError(p)

    @pg.production("unticked_statement : T_DECLARE "
                   "H_LB declare_list H_RB declare_statement")
    def unticked_statement_t_declare_declare_list(self, p):
        raise NotImplementedError(p)

    @pg.production("unticked_statement : T_TRY "
                   "H_L_CB inner_statement_list H_R_CB "
                   "T_CATCH H_LB fully_qualified_class_name "
                   "T_VARIABLE H_RB H_L_CB "
                   "inner_statement_list H_R_CB additional_catches")
    def unticked_statement_t_try(self, p):
        raise NotImplementedError(p)

    @pg.production("unticked_statement : T_THROW expr H_END_STMT")
    def unticked_statement_t_throw_expr(self, p):
        raise NotImplementedError(p)

    @pg.production("unticked_statement : T_GOTO T_STRING H_END_STMT")
    def unticked_statement_t_goto_string(self, p):
        raise NotImplementedError(p)

    @pg.production("expr : r_variable")
    def expr_expr_r_variable(self, p):
        return p[0]

    @pg.production("expr : expr_without_variable")
    def expr_expr_without_variable(self, p):
        return p[0]

    @pg.production("expr_without_variable : scalar")
    def expr_expr_without_variable_scalar(self, p):
        return p[0]

    @pg.production("expr_without_variable : T_ARRAY H_LB "
                   "array_pair_list H_RB")
    def expr_expr_without_variable_array(self, p):
        raise NotImplementedError(p)

    @pg.production("expr_without_variable : variable H_EQUAL expr")
    def expr_without_variable_variable_eq_expr(self, p):
        return Assignment(p[0], p[2])

    @pg.production("expr_without_variable : variable "
                   "H_EQUAL H_REFERENCE variable")
    def expr_without_variable_variable_eq_ref_var(self, p):
        raise NotImplementedError(p)

    @pg.production("expr_without_variable : variable "
                   "H_EQUAL H_REFERENCE T_NEW "
                   "class_name_reference ctor_arguments")
    def expr_without_variable_variable_eq_var_t_new_class(self, p):
        raise NotImplementedError(p)

    @pg.production("expr_without_variable : T_NEW "
                   "class_name_reference ctor_arguments")
    def expr_without_variable_variable_t_new_class(self, p):
        raise NotImplementedError(p)

    @pg.production("expr_without_variable : T_CLONE expr")
    def expr_without_variable_variable_t_clone(self, p):
        raise NotImplementedError(p)

    @pg.production("expr_without_variable : variable T_PLUS_EQUAL expr")
    @pg.production("expr_without_variable : variable T_MINUS_EQUAL expr")
    @pg.production("expr_without_variable : variable T_MUL_EQUAL expr")
    @pg.production("expr_without_variable : variable T_DIV_EQUAL expr")
    @pg.production("expr_without_variable : variable T_CONCAT_EQUAL expr")
    @pg.production("expr_without_variable : variable T_MOD_EQUAL expr")
    @pg.production("expr_without_variable : variable T_AND_EQUAL expr")
    @pg.production("expr_without_variable : variable T_OR_EQUAL expr")
    @pg.production("expr_without_variable : variable T_XOR_EQUAL expr")
    @pg.production("expr_without_variable : variable T_SL_EQUAL expr")
    @pg.production("expr_without_variable : variable T_SR_EQUAL expr")
    def expr_without_variable_variable_var_t_sth_eq_expr(self, p):
        raise NotImplementedError(p)

    @pg.production("expr_without_variable : rw_variable T_INC")
    @pg.production("expr_without_variable : rw_variable T_DEC")
    def expr_without_variable_variable_rw_var_t_inc_dec(self, p):
        return SuffixOp(p[1].getstr(), p[0])

    @pg.production("expr_without_variable : T_INC rw_variable")
    @pg.production("expr_without_variable : T_DEC rw_variable")
    def expr_without_variable_variable_t_inc_dec_rw_var(self, p):
        return PrefixOp(p[0].getstr(), p[1])

    @pg.production("expr : expr T_BOOLEAN_OR expr")
    @pg.production("expr : expr T_BOOLEAN_AND expr")
    @pg.production("expr : expr T_LOGICAL_OR expr")
    @pg.production("expr : expr T_LOGICAL_XOR expr")
    @pg.production("expr : expr T_LOGICAL_AND expr")
    @pg.production("expr : expr H_PIPE expr")
    @pg.production("expr : expr H_REFERENCE expr")
    @pg.production("expr : expr H_DASH expr")
    @pg.production("expr : expr H_DOT expr")
    @pg.production("expr : expr H_PLUS expr")
    @pg.production("expr : expr H_MINUS expr")
    @pg.production("expr : expr H_STAR expr")
    @pg.production("expr : expr H_SLASH expr")
    @pg.production("expr : expr H_PERCENT expr")
    @pg.production("expr : expr T_SL expr")
    @pg.production("expr : expr T_SR expr")
    @pg.production("expr : expr T_IS_IDENTICAL expr")
    @pg.production("expr : expr T_IS_NOT_IDENTICAL expr")
    @pg.production("expr : expr T_IS_EQUAL expr")
    @pg.production("expr : expr T_IS_NOT_EQUAL expr")
    @pg.production("expr : expr H_LT expr")
    @pg.production("expr : expr T_IS_SMALLER_OR_EQUAL expr")
    @pg.production("expr : expr H_GT expr")
    @pg.production("expr : expr T_IS_GREATER_OR_EQUAL expr")
    def expr_oper_expr(self, p):
        return BinOp(p[1].getstr(), p[0], p[2])

    @pg.production("expr : H_MINUS expr", precedence="T_DEC")
    @pg.production("expr : H_PLUS expr", precedence="T_INC")
    def expr_h_minus_expr(self, p):
        return PrefixOp(p[0].getstr(), p[1])
    # |'+' expr %prec T_INC
    # |'-' expr %prec T_INC
    # |'!' expr
    # |'~' expr

    @pg.production("expr : expr T_INSTANCEOF class_name_reference")
    def expr_expr_is_instance(self, p):
        raise NotImplementedError(p)

    @pg.production("expr : H_LB expr H_RB")
    def expr_bracket_expr_bracket(self, p):
        return p[1]

    @pg.production("expr : expr H_QUESTION expr H_COLON expr")
    def expr_expr_if_expr_else_expr(self, p):
        raise NotImplementedError(p)

    @pg.production("expr : expr H_QUESTION H_COLON expr")
    def expr_expr_else_expr(self, p):
        raise NotImplementedError(p)

    # internal_functions_in_yacc
    @pg.production("expr : T_INT_CAST expr")
    @pg.production("expr : T_DOUBLE_CAST expr")
    @pg.production("expr : T_STRING_CAST expr")
    @pg.production("expr : T_UNICODE_CAST expr")
    @pg.production("expr : T_BINARY_CAST expr")
    @pg.production("expr : T_ARRAY_CAST expr")
    @pg.production("expr : T_OBJECT_CAST expr")
    @pg.production("expr : T_BOOL_CAST expr")
    @pg.production("expr : T_UNSET_CAST expr")
    def expr_cast_expr(self, p):
        raise NotImplementedError(p)

    @pg.production("expr : T_EXIT exit_expr")
    def expr_t_exit_exit_expr(self, p):
        raise NotImplementedError(p)

    @pg.production("expr : H_AT expr")
    def expr_at_expr(self, p):
        raise NotImplementedError(p)

    @pg.production("expr : scalar")
    def expr_scalar(self, p):
        raise NotImplementedError(p)

    # '`' backticks_expr '`'
    @pg.production("expr : T_PRINT expr")
    def expr_t_print_expr(self, p):
        raise NotImplementedError(p)

    @pg.production("expr : function is_reference "
                   "H_LB parameter_list H_RB "
                   "lexical_vars H_L_CB inner_statement_list H_R_CB")
    def expr_function_is_reference(self, p):
        raise NotImplementedError(p)

    @pg.production("expr : T_STATIC function is_reference "
                   "H_LB parameter_list H_RB "
                   "lexical_vars H_L_CB inner_statement_list H_R_CB")
    def expr_t_static_function_is_reference(self, p):
        raise NotImplementedError(p)

    @pg.production("exit_expr : H_LB H_RB")
    def expr_empty_brackets(self, p):
        raise NotImplementedError(p)

    @pg.production("exit_expr : H_LB expr H_RB")
    def expr_expr_in_brackets(self, p):
        raise NotImplementedError(p)

    @pg.production("exit_expr : empty")
    def expr_empty(self, p):
        raise NotImplementedError(p)

    @pg.production("ctor_arguments : H_LB function_call_parameter_list H_RB")
    def ctor_arguments_function_call_parameter_list(self, p):
        raise NotImplementedError(p)

    @pg.production("ctor_arguments : empty")
    def ctor_empty(self, p):
        raise NotImplementedError(p)

    @pg.production("class_name_reference : class_name")
    def class_name_reference_class_name(self, p):
        raise NotImplementedError(p)

    @pg.production("class_name_reference : dynamic_class_name_reference")
    def class_name_reference_dynamic_class_name_reference(self, p):
        raise NotImplementedError(p)

    @pg.production("dynamic_class_name_reference : base_variable "
                   "T_OBJECT_OPERATOR object_property "
                   "dynamic_class_name_variable_properties")
    def dynamic_class_name_reference_base_variable_t_object_operator(self, p):
        raise NotImplementedError(p)

    @pg.production("dynamic_class_name_reference : base_variable")
    def dynamic_class_name_reference_base_variable(self, p):
        raise NotImplementedError(p)

    @pg.production("dynamic_class_name_variable_properties : "
                   "dynamic_class_name_variable_properties "
                   "dynamic_class_name_variable_property")
    def dynamic_class_name_variable_dcnvps_dcnvp(self, p):
        raise NotImplementedError(p)

    @pg.production("dynamic_class_name_variable_properties : empty")
    def dynamic_class_name_variable_empty(self, p):
        raise NotImplementedError(p)

    @pg.production("dynamic_class_name_variable_property : "
                   "T_OBJECT_OPERATOR object_property")
    def dynamic_class_name_variable_property(self, p):
        raise NotImplementedError(p)

    @pg.production("lexical_vars : T_USE H_LB lexical_var_list H_RB")
    def lexical_vars_t_use_lexical_var_list(self, p):
        raise NotImplementedError(p)

    @pg.production("lexical_vars : empty")
    def lexical_vars_empty(self, p):
        raise NotImplementedError(p)

    @pg.production("lexical_var_list : lexical_var_list , T_VARIABLE")
    def lexical_var_list_lexical_var_list_t_variable(self, p):
        raise NotImplementedError(p)

    @pg.production("lexical_var_list : lexical_var_list , "
                   "H_REFERENCE T_VARIABLE")
    def lexical_var_list_lexical_var_list_ref_t_variable(self, p):
        raise NotImplementedError(p)

    @pg.production("lexical_var_list : T_VARIABLE")
    def lexical_var_list_t_variable(self, p):
        raise NotImplementedError(p)

    @pg.production("lexical_var_list : H_REFERENCE T_VARIABLE")
    def lexical_var_list_ref_t_variable(self, p):
        raise NotImplementedError(p)

    @pg.production("scalar : T_STRING_VARNAME")
    def scalar_t_string_varname(self, p):
        raise NotImplementedError(p)

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
        if p[0].gettokentype() == 'T_LNUMBER':
            return ConstantInt(int(p[0].getstr()))
        if p[0].gettokentype() == 'T_DNUMBER':
            return ConstantFloat(float(p[0].getstr()))
        raise Exception("Not implemented yet!")

    @pg.production("static_scalar : common_scalar")
    def static_scalar(self, p):
        return p[0]

    @pg.production("static_array_pair_list : "
                   "non_empty_static_array_pair_list possible_comma")
    def static_array_pair_list_non_empty(self, p):
        raise NotImplementedError(p)

    @pg.production("static_array_pair_list : empty")
    def static_array_pair_list_empty(self, p):
        raise NotImplementedError(p)

    @pg.production("array_pair_list : "
                   "non_empty_static_array_pair_list possible_comma")
    def array_pair_list_non_empty(self, p):
        raise NotImplementedError(p)

    @pg.production("array_pair_list : empty")
    def array_pair_list_empty(self, p):
        raise NotImplementedError(p)

    @pg.production("non_empty_static_array_pair_list : "
                   "non_empty_static_array_pair_list , static_scalar")
    def non_empty_static_array_pair_list_list(self, p):
        raise NotImplementedError(p)

    @pg.production("non_empty_static_array_pair_list : "
                   "non_empty_static_array_pair_list , "
                   "static_scalar T_DOUBLE_ARROW static_scalar")
    def non_empty_static_array_pair_list_list_scalar_assign_scalar(self, p):
        raise NotImplementedError(p)

    @pg.production("non_empty_static_array_pair_list : "
                   "static_scalar T_DOUBLE_ARROW static_scalar")
    def non_empty_static_array_pair_list_scalar_assign_scalar(self, p):
        raise NotImplementedError(p)

    @pg.production("non_empty_static_array_pair_list : static_scalar")
    def non_empty_static_array_pair_list_scalar(self, p):
        raise NotImplementedError(p)

    @pg.production("assignment_list : "
                   "assignment_list , assignment_list_element")
    def assignment_list_assignment_list_assignment_list_element(self, p):
        raise NotImplementedError(p)

    @pg.production("assignment_list : assignment_list_element")
    def assignment_list_assignment_list_element(self, p):
        raise NotImplementedError(p)

    @pg.production("assignment_list_element : variable")
    def assignment_list_element_variable(self, p):
        raise NotImplementedError(p)

    @pg.production("assignment_list_element : "
                   "T_LIST H_LB assignment_list H_RB")
    def assignment_list_element_t_list(self, p):
        raise NotImplementedError(p)

    @pg.production("assignment_list_element : empty")
    def assignment_list_element_empty(self, p):
        raise NotImplementedError(p)

    @pg.production("variable : base_variable_with_function_calls"
                   " T_OBJECT_OPERATOR object_property method_or_not"
                   " variable_properties ")
    def variable_base_variable_with_function_calls_t_object_operator(self, p):
        raise NotImplementedError(p)

    @pg.production("variable : base_variable_with_function_calls")
    def variable_base_variable_with_function_calls(self, p):
        return p[0]

    @pg.production("base_variable_with_function_calls : base_variable")
    def base_variable_with_function_calls_base_variable(self, p):
        return p[0]

    @pg.production("base_variable_with_function_calls : function_call")
    def base_variable_with_function_calls_function_call(self, p):
        raise NotImplementedError(p)

    @pg.production("base_variable : reference_variable")
    def base_variable_reference_variable(self, p):
        return p[0]

    @pg.production("base_variable : simple_indirect_reference "
                   "reference_variable")
    def base_variable_simple_indirect_ref_ref_variable(self, p):
        raise NotImplementedError(p)

    @pg.production("base_variable : static_member")
    def base_variable_static_member(self, p):
        raise NotImplementedError(p)

    @pg.production("reference_variable : "
                   "reference_variable H_L_SB dim_offset H_R_SB")
    def reference_variable_reference_variable_offset(self, p):
        raise NotImplementedError(p)

    @pg.production("reference_variable : "
                   "reference_variable H_L_CB expr H_R_CB")
    def reference_variable_reference_variable_expr(self, p):
        raise NotImplementedError(p)

    @pg.production("reference_variable : compound_variable")
    def reference_variable_compound_variable(self, p):
        return p[0]

    @pg.production("compound_variable : T_VARIABLE")
    def compound_variable_t_variable(self, p):
        return Variable(ConstantStr(p[0].getstr()[1:]))

    @pg.production("compound_variable : H_DOLLAR H_L_CB expr H_R_CB")
    def compound_variable_expr(self, p):
        raise NotImplementedError(p)

    @pg.production("r_variable : variable")
    def variable_r_variable(self, p):
        return p[0]

    @pg.production("rw_variable : variable")
    def variable_rw_variable(self, p):
        return p[0]

    @pg.production("w_variable : variable")
    def variable_w_variable(self, p):
        raise NotImplementedError(p)

    @pg.production("variable_properties : "
                   "variable_properties variable_property")
    def variable_properties_variable_properties_variable_property(self, p):
        raise NotImplementedError(p)

    @pg.production("variable_properties : "
                   "empty")
    def variable_properties_empty(self, p):
        raise NotImplementedError(p)

    @pg.production("variable_property : T_OBJECT_OPERATOR "
                   "object_property method_or_not")
    def variable_property_t_object_operator(self, p):
        raise NotImplementedError(p)

    @pg.production("foreach_variable : variable")
    def foreach_variable_variable(self, p):
        raise NotImplementedError(p)

    @pg.production("foreach_variable : H_REFERENCE variable")
    def foreach_variable_ref_variable(self, p):
        raise NotImplementedError(p)

    @pg.production("while_statement : statement")
    def while_stmt_stmt(self, p):
        raise NotImplementedError(p)

    @pg.production("while_statement : "
                   "H_COLON inner_statement_list T_ENDWHILE H_END_STMT")
    def while_stmt_inner_stmt_list(self, p):
        raise NotImplementedError(p)

    @pg.production("for_statement : statement")
    def for_stmt_stmt(self, p):
        raise NotImplementedError(p)

    @pg.production("for_statement : "
                   "H_COLON inner_statement_list T_ENDFOR H_END_STMT")
    def for_stmt_inner_stmt_list(self, p):
        raise NotImplementedError(p)

    @pg.production("declare_statement : statement")
    def declare_stmt_stmt(self, p):
        raise NotImplementedError(p)

    @pg.production("declare_statement : "
                   "H_COLON inner_statement_list T_ENDDECLARE H_END_STMT")
    def declare_stmt_inner_stmt_list(self, p):
        raise NotImplementedError(p)

    @pg.production("else_single : T_ELSE statement")
    def else_single_t_else_statement(self, p):
        raise NotImplementedError(p)

    @pg.production("else_single : empty")
    def else_single_empty(self, p):
        raise NotImplementedError(p)

    @pg.production("switch_case_list : H_L_CB case_list H_R_CB")
    def switch_case_list_case_list(self, p):
        raise NotImplementedError(p)

    @pg.production("switch_case_list : H_L_CB H_END_STMT case_list H_R_CB")
    def switch_case_list_h_end_stmt_case_list(self, p):
        raise NotImplementedError(p)

    @pg.production("switch_case_list : H_COLON "
                   "case_list T_ENDSWITCH H_END_STMT")
    def switch_case_list_h_colon_case_list(self, p):
        raise NotImplementedError(p)

    @pg.production("switch_case_list : H_COLON "
                   "H_END_STMT case_list T_ENDSWITCH H_END_STMT")
    def switch_case_list_h_colon_h_end_stmt_case_list(self, p):
        raise NotImplementedError(p)

    @pg.production("case_list : case_list "
                   "T_CASE expr case_separator inner_statement_list")
    def case_list_case_list_t_case_expr_case_sep_inner_stmt_list(self, p):
        raise NotImplementedError(p)

    @pg.production("case_list : case_list "
                   "T_DEFAULT expr case_separator inner_statement_list")
    def case_list_case_list_t_default_expr_case_sep_inner_stmt_list(self, p):
        raise NotImplementedError(p)

    @pg.production("static_var_list : static_var_list , T_VARIABLE")
    def static_var_list_static_var_list_t_variable(self, p):
        raise NotImplementedError(p)

    @pg.production("static_var_list : static_var_list"
                   " , T_VARIABLE H_EQUAL static_scalar")
    def static_var_list_static_var_list_t_variable_t_eq_static_scalar(self, p):
        raise NotImplementedError(p)

    @pg.production("static_var_list : T_VARIABLE")
    def static_var_list_t_variable(self, p):
        raise NotImplementedError(p)

    @pg.production("static_var_list : T_VARIABLE H_EQUAL static_scalar")
    def static_var_list_t_variable_t_eq_static_scalar(self, p):
        raise NotImplementedError(p)

    @pg.production("elseif_list : elseif_list "
                   "T_ELSEIF H_LB expr H_RB statement")
    def elseif_list_elseif_list(self, p):
        raise NotImplementedError(p)

    @pg.production("elseif_list : empty")
    def elseif_list_empty(self, p):
        raise NotImplementedError(p)

    @pg.production("new_else_single : T_ELSE H_COLON inner_statement_list")
    def new_else_single_t_else(self, p):
        raise NotImplementedError(p)

    @pg.production("new_else_single : empty")
    def new_else_single_empty(self, p):
        raise NotImplementedError(p)

    @pg.production("echo_expr_list : echo_expr_list , expr")
    def echo_expr_list_echo_expr_list_expr(self, p):
        raise NotImplementedError(p)

    @pg.production("echo_expr_list : expr")
    def echo_expr_list_expr(self, p):
        raise NotImplementedError(p)

    @pg.production("global_var_list : global_var_list , global_var")
    def global_var_list_global_var_list_global_var(self, p):
        raise NotImplementedError(p)

    @pg.production("global_var_list : global_var")
    def global_var_list_global_var(self, p):
        return p[0]

    @pg.production("new_elseif_list : new_elseif_list "
                   "T_ELSEIF H_LB expr H_RB H_COLON inner_statement_list")
    def new_elseif_list_new_elseif_list(self, p):
        raise NotImplementedError(p)

    @pg.production("new_elseif_list : empty")
    def new_elseif_list_empty(self, p):
        raise NotImplementedError(p)

    @pg.production("foreach_statement : statement")
    def foreach_statement_statement(self, p):
        raise NotImplementedError(p)

    @pg.production("foreach_statement : "
                   "H_COLON inner_statement_list T_ENDFOREACH H_END_STMT")
    def foreach_statement_inner_statement_list(self, p):
        raise NotImplementedError(p)

    @pg.production("foreach_optional_arg : T_DOUBLE_ARROW foreach_variable")
    def foreach_opt_arg_t_d_arrow_foreach_var(self, p):
        raise NotImplementedError(p)

    @pg.production("foreach_optional_arg : empty")
    def foreach_opt_arg_empty(self, p):
        raise NotImplementedError(p)

    @pg.production("additional_catches : non_empty_additional_catches")
    def additional_catches_non_empty(self, p):
        raise NotImplementedError(p)

    @pg.production("additional_catches : empty")
    def additional_empty(self, p):
        raise NotImplementedError(p)

    @pg.production("non_empty_additional_catches : "
                   "non_empty_additional_catches additional_catch")
    def non_empty_additional_catches_nead_additional_catch(self, p):
        raise NotImplementedError(p)

    @pg.production("non_empty_additional_catches : additional_catch")
    def non_empty_additional_catches_additional_catch(self, p):
        raise NotImplementedError(p)

    @pg.production("additional_catch : T_CATCH "
                   "H_LB fully_qualified_class_name "
                   "T_VARIABLE H_RB H_L_CB inner_statement_list H_R_CB")
    def additional_catch(self, p):
        raise NotImplementedError(p)

    @pg.production("case_separator : H_COLON")
    @pg.production("case_separator : H_END_STMT")
    def case_separator(self, p):
        raise NotImplementedError(p)

    @pg.production("declare_list : declare_list , "
                   "T_STRING H_EQUAL static_scalar")
    def declare_list_declare_list_t_string_eq_static_scalar(self, p):
        raise NotImplementedError(p)

    @pg.production("declare_list : T_STRING H_EQUAL static_scalar")
    def declare_list_t_string_eq_static_scalar(self, p):
        raise NotImplementedError(p)

    @pg.production("for_expr : non_empty_for_expr")
    def for_expr_non_empty_for_expr(self, p):
        raise NotImplementedError(p)

    @pg.production("for_expr : empty")
    def for_expr_empty(self, p):
        raise NotImplementedError(p)

    @pg.production("non_empty_for_expr : non_empty_for_expr , expr")
    def non_empty_for_expr_non_empty_for_expr_expr(self, p):
        raise NotImplementedError(p)

    @pg.production("non_empty_for_expr : expr")
    def non_empty_for_expr_expr(self, p):
        raise NotImplementedError(p)

    @pg.production("unset_variables : unset_variables , unset_variable")
    def unset_vars_unset_vars_unset_var(self, p):
        raise NotImplementedError(p)

    @pg.production("unset_variables : unset_variable")
    def unset_vars_unset_var(self, p):
        raise NotImplementedError(p)

    @pg.production("unset_variable : variable")
    def unset_var_var(self, p):
        raise NotImplementedError(p)

    @pg.production("method_or_not : H_LB function_call_parameter_list H_RB")
    def method_or_not_function_call_paramter_list(self, p):
        raise NotImplementedError(p)

    @pg.production("method_or_not : empty")
    def method_or_not_empty(self, p):
        raise NotImplementedError(p)

    @pg.production("function_call_parameter_list : "
                   "non_empty_function_call_parameter_list")
    def function_call_parameter_list_non_empty_function(self, p):
        raise NotImplementedError(p)

    @pg.production("non_empty_function_call_parameter_list : "
                   "expr_without_variable")
    def non_empty_function_call_parameter_list_expr_wo_variable(self, p):
        raise NotImplementedError(p)

    @pg.production("non_empty_function_call_parameter_list : "
                   "variable")
    def non_empty_function_call_parameter_list_variable(self, p):
        raise NotImplementedError(p)

    @pg.production("non_empty_function_call_parameter_list : "
                   "H_REFERENCE w_variable")
    def non_empty_function_call_parameter_list_reference_variable(self, p):
        raise NotImplementedError(p)

    @pg.production("non_empty_function_call_parameter_list : "
                   "non_empty_function_call_parameter_list , "
                   "expr_without_variable")
    def non_empty_function_call_parameter_list_list_expr_wo_variable(self, p):
        raise NotImplementedError(p)

    @pg.production("non_empty_function_call_parameter_list : "
                   "non_empty_function_call_parameter_list , variable")
    def non_empty_function_call_parameter_list_list_variable(self, p):
        raise NotImplementedError(p)

    @pg.production("non_empty_function_call_parameter_list : "
                   "non_empty_function_call_parameter_list , "
                   "H_REFERENCE w_variable")
    def non_empty_function_call_parameter_list_list_ref_variable(self, p):
        raise NotImplementedError(p)

    @pg.production("function_call : namespace_name "
                   "H_LB function_call_parameter_list H_RB")
    def function_call_namespace_name_function_call_parameter_list(self, p):
        raise NotImplementedError(p)

    @pg.production("function_call : T_NAMESPACE T_NS_SEPARATOR namespace_name "
                   "H_LB function_call_parameter_list H_RB")
    def function_call_ns_sep_ns_name_function_call_parameter_list(self, p):
        raise NotImplementedError(p)

    @pg.production("function_call : class_name T_PAAMAYIM_NEKUDOTAYIM "
                   "T_STRING H_LB function_call_parameter_list H_RB")
    def function_call_cn_t_paamayim_string_f_call_p_list(self, p):
        raise NotImplementedError(p)

    @pg.production("function_call : variable_class_name "
                   "T_PAAMAYIM_NEKUDOTAYIM "
                   "T_STRING H_LB function_call_parameter_list H_RB")
    def function_call_vcn_t_paamayim_string_f_call_p_list(self, p):
        raise NotImplementedError(p)

    @pg.production("function_call : variable_class_name "
                   "T_PAAMAYIM_NEKUDOTAYIM "
                   "variable_without_objects "
                   "H_LB function_call_parameter_list H_RB")
    def function_call_vcn_t_paamayim_variable_wo_f_call_p_list(self, p):
        raise NotImplementedError(p)

    @pg.production("function_call : "
                   "T_PAAMAYIM_NEKUDOTAYIM "
                   "variable_without_objects "
                   "H_LB function_call_parameter_list H_RB")
    def function_call_t_paamayim_variable_wo_f_call_p_list(self, p):
        raise NotImplementedError(p)

    @pg.production("function_call : class_name "
                   "variable_without_objects "
                   "H_LB function_call_parameter_list H_RB")
    def function_call_cn_t_paamayim_variable_wo_f_call_p_list(self, p):
        raise NotImplementedError(p)

    @pg.production("class_name : T_STATIC")
    def class_name_t_static(self, p):
        raise NotImplementedError(p)

    @pg.production("class_name : namespace_name")
    def class_name_namespace_name(self, p):
        raise NotImplementedError(p)

    @pg.production("class_name : T_NAMESPACE T_NS_SEPARATOR namespace_name")
    def class_name_t_namespace_t_ns_separator_namespace_name(self, p):
        raise NotImplementedError(p)

    @pg.production("class_name : T_NS_SEPARATOR namespace_name")
    def class_name_t_ns_separator_namespace_name(self, p):
        raise NotImplementedError(p)

    @pg.production("simple_indirect_reference : H_DOLLAR")
    def simple_indirect_reference(self, p):
        raise NotImplementedError(p)

    @pg.production("simple_indirect_reference : "
                   "simple_indirect_reference H_DOLLAR")
    def simple_indirect_reference_simple_indirect_reference(self, p):
        raise NotImplementedError(p)

    @pg.production("variable_without_objects : reference_variable")
    def variable_without_objects_reference_variable(self, p):
        raise NotImplementedError(p)

    @pg.production("variable_without_objects : "
                   "simple_indirect_reference reference_variable")
    def variable_without_objects_simple_i_ref_reference_variable(self, p):
        raise NotImplementedError(p)

    @pg.production("static_member : class_name "
                   "T_PAAMAYIM_NEKUDOTAYIM variable_without_objects")
    def static_member_class_name_T_PAAMAYIM_variable_without_objects(self, p):
        raise NotImplementedError(p)

    @pg.production("static_member : variable_class_name "
                   "T_PAAMAYIM_NEKUDOTAYIM variable_without_objects")
    def static_member_var_class_name_T_PAAMAYIM_variable_ww(self, p):
        raise NotImplementedError(p)

    @pg.production("dim_offset : empty")
    def dim_offset_empty(self, p):
        raise NotImplementedError(p)

    @pg.production("dim_offset : expr")
    def dim_offset_expr(self, p):
        raise NotImplementedError(p)

    @pg.production("object_property : object_dim_list")
    def object_property_object_dim_list(self, p):
        raise NotImplementedError(p)

    @pg.production("object_property : variable_without_objects")
    def object_property_variable_without_objects(self, p):
        raise NotImplementedError(p)

    @pg.production("object_dim_list : object_dim_list "
                   "H_L_SB dim_offset H_R_SB")
    def object_dim_list_object_dim_list_dim_offset(self, p):
        raise NotImplementedError(p)

    @pg.production("object_dim_list : object_dim_list H_L_CB expr H_R_CB")
    def object_dim_list_object_dim_list_expr(self, p):
        raise NotImplementedError(p)

    @pg.production("object_dim_list : variable_name")
    def object_dim_list_variable_name(self, p):
        raise NotImplementedError(p)

    @pg.production("variable_name : T_STRING")
    def variable_name_t_string(self, p):
        raise NotImplementedError(p)

    @pg.production("variable_name : H_L_CB expr H_R_CB")
    def variable_name_expr(self, p):
        raise NotImplementedError(p)

    @pg.production("variable_class_name : reference_variable")
    def variable_class_name_reference_variable(self, p):
        raise NotImplementedError(p)

    @pg.production("global_var : T_VARIABLE")
    def global_var_t_variable(self, p):
        raise NotImplementedError(p)

    @pg.production("global_var : H_DOLLAR r_variable")
    def global_var_dollar_r_variable(self, p):
        raise NotImplementedError(p)

    @pg.production("global_var : H_DOLLAR H_L_CB expr H_R_CB")
    def global_var_expr(self, p):
        raise NotImplementedError(p)

    @pg.production("namespace_name : T_STRING")
    def namespace_name_t_string(self, p):
        raise NotImplementedError(p)

    @pg.production("namespace_name :  namespace_name T_NS_SEPARATOR T_STRING")
    def namespace_name_namespace_name_t_ns_sep_t_string(self, p):
        raise NotImplementedError(p)

    @pg.production("possible_comma : empty")
    def possible_comma_empty(self, p):
        raise NotImplementedError(p)

    @pg.production("possible_comma : ,")
    def possible_comma(self, p):
        raise NotImplementedError(p)

    @pg.production("empty :")
    def empty(self, p):
        return None

    @pg.error
    def error_handler(self, token):
        raise ValueError("Ran into a %s where it "
                     "wasn't expected at line(%s)" %
                         (token.gettokentype(),
                          token.getsourcepos())
                         )

    parser = pg.build()


def parse(_source):
    lx = Lexer(RULES, skip_whitespace=False)
    lx.input(_source)
    # for r in lx.tokens():
    #     print r
    parser = Parser(lx.tokens())
    return parser.parse()
