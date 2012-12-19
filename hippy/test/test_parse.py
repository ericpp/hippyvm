import py
from py.test import raises
from hippy.sourceparser import parse, Block, Stmt, Assignment, ConstantInt,\
     Variable, Echo, Return, If, PrefixOp, SuffixOp, While, For, ConstantStr,\
     SimpleCall, DynamicCall, FunctionDecl, Argument, BinOp, ConstantFloat,\
     GetItem, SetItem, Array, Append, And, Or, InplaceOp, Global,\
     NamedConstant, DoWhile, Reference, ReferenceArgument, Hash, ForEach,\
     ForEachKey, Cast, DefaultArgument, StaticDecl, InitializedVariable,\
     UninitializedVariable, ConstantAppend, Break, Continue
from rply import ParsingError

class TestParser(object):

    def test_top_statement(self):
        r = parse("1;")
        assert r == Block([Stmt(ConstantInt(1))])
        r = parse("{1;}")
        assert r == Block([Block([Stmt(ConstantInt(1))])])


    def test_assign(self):
        r = parse("$x = 3;")
        assert r == Block([Stmt(Assignment(Variable(ConstantStr('x')),
                                           ConstantInt(3)))])

    def test_assign_error(self):
        raises(ValueError, lambda : parse("$x$ = 3;"))

    def test_add(self):
        r = parse("3 + 1;")
        assert r == Block([Stmt(BinOp("+", ConstantInt(3), ConstantInt(1)))])

    def test_add2(self):
        r = parse("3 + 1 + 5;")
        assert r == Block([Stmt(
                    BinOp("+", BinOp("+", ConstantInt(3), ConstantInt(1)), ConstantInt(5)))])

    def test_minus2(self):
        r = parse("1 - 2 - 3;")
        assert r == Block([Stmt(
                    BinOp("-", BinOp("-", ConstantInt(1), ConstantInt(2)), ConstantInt(3)))])

    def test_add_minus(self):
        r = parse("3 - 1 + 5;")
        assert r == Block([Stmt(
                    BinOp("+", BinOp("-", ConstantInt(3), ConstantInt(1)), ConstantInt(5)))])


    def test_operation_precedence(self):
        r = parse("5 + 1 * 3;")
        assert r == Block([Stmt(
                    BinOp("+", ConstantInt(5), BinOp("*", ConstantInt(1), ConstantInt(3))))])
        r = parse("5 - 1 * 3;")
        assert r == Block([Stmt(
                    BinOp("-", ConstantInt(5), BinOp("*", ConstantInt(1), ConstantInt(3))))])
        r = parse("5 + 1 / 3;")
        assert r == Block([Stmt(
                    BinOp("+", ConstantInt(5), BinOp("/", ConstantInt(1), ConstantInt(3))))])
        r = parse("5 - 1 / 3;")
        assert r == Block([Stmt(
                    BinOp("-", ConstantInt(5), BinOp("/", ConstantInt(1), ConstantInt(3))))])
        r = parse("(5 + 1) * 3;")
        assert r == Block([Stmt(
                    BinOp("*", BinOp("+", ConstantInt(5), ConstantInt(1)), ConstantInt(3)))])
        r = parse("(5 + 1) / 3;")
        assert r == Block([Stmt(
                    BinOp("/", BinOp("+", ConstantInt(5), ConstantInt(1)), ConstantInt(3)))])
        r = parse("5 * (1 + 3);")
        assert r == Block([Stmt(
                    BinOp("*", ConstantInt(5), BinOp("+", ConstantInt(1), ConstantInt(3))))])
        r = parse("5 / (1 + 3);")
        assert r == Block([Stmt(
                    BinOp("/", ConstantInt(5), BinOp("+", ConstantInt(1), ConstantInt(3))))])
        r = parse("5 * 1 + 3;")
        assert r == Block([Stmt(
                    BinOp("+", BinOp("*", ConstantInt(5), ConstantInt(1)), ConstantInt(3)))])
        r = parse("5 / 1 + 3;")
        assert r == Block([Stmt(
                    BinOp("+", BinOp("/", ConstantInt(5), ConstantInt(1)), ConstantInt(3)))])
        r = parse("5 + 1 / 3;")
        assert r == Block([Stmt(
                    BinOp("+", ConstantInt(5), BinOp("/", ConstantInt(1), ConstantInt(3))))])
        r = parse("5 + 1 * 3;")
        assert r == Block([Stmt(
                    BinOp("+", ConstantInt(5), BinOp("*", ConstantInt(1), ConstantInt(3))))])
        r = parse("5 || 1 && 3;")
        assert r == Block([Stmt(
                    Or(ConstantInt(5), And(ConstantInt(1), ConstantInt(3))))])


    def test_multi(self):
        r = parse("1 * 2 - $x;")
        assert r == Block([Stmt(BinOp("-",
                                     BinOp("*", ConstantInt(1), ConstantInt(2)),
                                     Variable(ConstantStr("x"))))])

    def test_float_const(self):
        r = parse("$x = 3.5 + .2 + 2.;");
        assert r == Block([Stmt(Assignment(Variable(ConstantStr("x")),
                               BinOp("+", BinOp("+", ConstantFloat(3.5), ConstantFloat(.2)),
                                     ConstantFloat(2.))))])

    def test_paren_multi(self):
        r = parse("($x - 3) * 2;")
        assert r == Block([Stmt(BinOp("*",
                          BinOp("-", Variable(ConstantStr("x")),
                                ConstantInt(3)),
                          ConstantInt(2)))])

    def test_plusplus(self):
        r = parse("++$x;")
        assert r == Block([Stmt(PrefixOp("++", Variable(ConstantStr("x"))))])
        r = parse("$x--;")
        assert r == Block([Stmt(SuffixOp("--", Variable(ConstantStr("x"))))])

    def test_unary_minus(self):
        r = parse("-$x;")
        assert r == Block([Stmt(PrefixOp("-", Variable(ConstantStr("x"))))])

    def test_multiple_stmts(self):
        r = parse("""
        $x = 3;
        $y = 4;
        $z;
        """)
        assert r == Block([
                Stmt(
                    Assignment(
                        Variable(
                            ConstantStr("x", 1),
                            1),
                        ConstantInt(3, 1),
                        1),
                    1),
                Stmt(
                    Assignment(
                        Variable(
                            ConstantStr("y", 2),
                            2),
                        ConstantInt(4, 2),
                        2),
                    2),
                Stmt(
                    Variable(
                        ConstantStr("z", 3), 3
                        ),
                    3)
                ])

    def test_echo(self):
        r = parse("echo $x;")
        assert r == Block([Echo([Variable(ConstantStr("x"))])])

    def test_echo_list(self):
        r = parse("echo $x, 2, 3, 4;")
        assert r == Block([Echo([
                        Variable(ConstantStr("x")),
                        ConstantInt(2),
                        ConstantInt(3),
                        ConstantInt(4),
                        ])])

    def test_return(self):
        r = parse("return $y;")
        assert r == Block([Return(Variable(ConstantStr("y")))])

    def test_if(self):
        r = parse("""
        if ($x)
           return $y;
        """)
        assert r == Block([
                If(
                    Variable(
                        ConstantStr("x", 1),
                        1),
                    Return(
                        Variable(
                            ConstantStr("y", 2),
                            2),
                        2),
                    lineno=1)])

    def test_if_brackets(self):
        r = parse("if ($x) { return $y; }")
        assert r == Block([If(Variable(ConstantStr("x")),
                              Block([Return(Variable(ConstantStr("y")))]))])

    def test_if_else(self):
        r = parse("if ($x) $y; else $z;")
        expected = Block([If(Variable(ConstantStr("x")),
                             Stmt(Variable(ConstantStr("y"))),
                             elseclause=Stmt(Variable(ConstantStr("z"))))])

        assert r == expected

    def test_if_else_if_oneline(self):
        r = parse("""if ($x) $y; elseif ($z) 3; else 4;""")
        expected = Block([If(Variable(ConstantStr("x")),
                             Stmt(Variable(ConstantStr("y"))),
                             [If(Variable(ConstantStr("z")),
                                 Stmt(ConstantInt(3)))],
                             Stmt(ConstantInt(4)))])

        assert r == expected

    def test_if_else_if(self):
        r = parse("""
        if ($x)
          $y;
        elseif ($z)
          3;
        else
          4;
        """)
        expected = Block([
                If(
                    Variable(ConstantStr("x", 1), 1),
                    Stmt(
                        Variable(
                            ConstantStr("y", 2), 2), 2),
                             [
                        If(
                            Variable(
                                ConstantStr("z", 3), 3),
                            Stmt(
                                ConstantInt(3, 4), 4),
                            lineno=3)],
                    Stmt(ConstantInt(4, 6), 6),
                    lineno=1)])

        assert r == expected

    def test_if_else_if_2(self):
        r = parse("""
        if ($x)
          $y;
        elseif ($z)
          3;
        elseif($y)
          7;
        else
          8;
        """)
        assert r == Block([
                If(Variable(ConstantStr("x", 1), 1),
                              Stmt(Variable(ConstantStr("y", 2), 2), 2),
                          [If(Variable(ConstantStr("z", 3), 3),
                              Stmt(ConstantInt(3, 4), 4),
                              lineno=3),
                           If(Variable(ConstantStr("y", 5), 5),
                              Stmt(ConstantInt(7, 6), 6),
                              lineno=5)],
                              Stmt(ConstantInt(8, 8), 8),
                              lineno=1)])

    def test_if_else_if_3(self):
        r = parse("""
        if ($x)
          $y;
        elseif ($z)
          3;
        elseif($y)
          7;
        """)
        assert r == Block([If(Variable(ConstantStr("x", 1), 1),
                              Stmt(Variable(ConstantStr("y", 2), 2), 2),
                          [If(Variable(ConstantStr("z", 3), 3),
                              Stmt(ConstantInt(3, 4), 4),
                              lineno=3),
                           If(Variable(ConstantStr("y", 5), 5),
                              Stmt(ConstantInt(7, 6), 6),
                              lineno=5)],
                              lineno=1)])

    def test_while(self):
        r = parse("while ($x) $x--;")
        assert r == Block([While(Variable(ConstantStr("x")),
                                 Stmt(SuffixOp("--",
                                               Variable(ConstantStr("x")))))])

    def test_for(self):
        r = parse("for ($i = 0; $i < 10; $i++) {}")
        expected = Block([For(Assignment(Variable(ConstantStr("i")),
                                         ConstantInt(0)),
                              BinOp("<", Variable(ConstantStr("i")),
                                    ConstantInt(10)),
                              SuffixOp("++", Variable(ConstantStr("i"))),
                              Block([]))])

        assert r == expected

    def test_dynamic_var(self):
        r = parse("$$x;")
        assert r == Block([Stmt(Variable(Variable(ConstantStr("x"))))])
        r = parse('${"x" + 3};')
        assert r == Block([Stmt(Variable(BinOp("+", ConstantStr("x"),
                                               ConstantInt(3))))])

    def test_function_call(self):
        r = parse("3 + printf();")
        assert r == Block([Stmt(BinOp("+", ConstantInt(3),
                          SimpleCall("printf", [])))])
        r = parse("printf(1, 2, 3);")
        assert r == Block([Stmt(SimpleCall("printf", [ConstantInt(1),
                                                      ConstantInt(2),
                                                      ConstantInt(3)]))])
        r = parse("printf(1);")
        assert r == Block([Stmt(SimpleCall("printf", [ConstantInt(1)]))])

    def test_dynamic_funccall(self):
        r = parse("3 + $x(3, 4);")
        assert r == Block([Stmt(BinOp("+", ConstantInt(3),
                    DynamicCall(Variable(ConstantStr("x")),
                                [ConstantInt(3), ConstantInt(4)])))])

    def test_function_declr(self):
        r = parse("""
        function f() {}
        f();
        """)
        assert r == Block([
            FunctionDecl("f", [], Block([], 1), 1),
            Stmt(SimpleCall("f", [], 2), 2)])
        r = parse("function f($a, $b, $c) { 3; 4; }")
        assert r == Block([
            FunctionDecl("f", [Argument("a"), Argument("b"), Argument("c")],
                         Block([Stmt(ConstantInt(3)),
                                Stmt(ConstantInt(4))]), 0)])

        r = parse("function f($a) { 3; 4; }")
        assert r == Block([
            FunctionDecl("f", [Argument("a")],
                         Block([Stmt(ConstantInt(3)),
                                Stmt(ConstantInt(4))]), 0)])
        r = parse("function f(&$a) {}")
        assert r == Block([
            FunctionDecl("f", [ReferenceArgument("a")], Block([]), 0)])

    def test_multielem_echo(self):
        r = parse('''
        echo 1, 2, 3;
        ''')
        assert r == Block([Echo([ConstantInt(1, 1), ConstantInt(2, 1),
                                 ConstantInt(3, 1)], 1)])
        # print gramma is >T_PRING expr<, so we should see parse exception
        raises(ValueError, lambda : parse('''
        print 1, 2, 3;
        '''))

    def test_string_literal(self):
        r = parse('''
        $x = "\\n";
        ''')
        expected = Block([Stmt(Assignment(Variable(ConstantStr("x", 1), 1),
                                                   ConstantStr("\\n", 1), 1), 1)])
        assert r == expected

    def test_getitem(self):
        r = parse("$x[1];")
        assert r == Block([Stmt(GetItem(Variable(ConstantStr("x")),
                                        ConstantInt(1)))])

    def test_setitem(self):
        py.test.skip("XXX FIXME")
        r = parse("$x[1] = 3;")
        assert r == Block([Stmt(SetItem(Variable(ConstantStr("x")),
                                        ConstantInt(1), ConstantInt(3)))])

    def test_array(self):
        r = parse("array();")
        assert r == Block([Stmt(Array([]))])
        r = parse("array(1);")
        assert r == Block([Stmt(Array([ConstantInt(1)]))])
        r = parse("array(1, 2, 3 + 4);")
        assert r == Block([Stmt(Array([ConstantInt(1), ConstantInt(2),
                                       BinOp("+", ConstantInt(3),
                                             ConstantInt(4))]))])

    def test_array_append(self):
        py.test.skip("XXX FIXME")
        r = parse("$a[] = 3;")
        expected = Block([Stmt(Append(Variable(ConstantStr("a")),
                                       ConstantInt(3)))])
        assert r == expected

    def test_and_or(self):
        r = parse("1 && 2 || 3;")
        assert r == Block([Stmt(Or(And(ConstantInt(1), ConstantInt(2)), ConstantInt(3)))])

    def test_and_or2(self):
        r = parse("2 || 3 && 1;")
        assert r == Block([Stmt(Or(ConstantInt(2), And(ConstantInt(3), ConstantInt(1))))])

    def test_inplace_oper(self):
        r = parse("$x += 2;")
        assert r == Block([Stmt(InplaceOp("+=", Variable(ConstantStr("x")),
                                          ConstantInt(2)))])

    def test_inplace_2(self):
        r = parse("($i = $j);")
        assert r == Block([Stmt(Assignment(Variable(ConstantStr("i")),
                                           Variable(ConstantStr("j"))))])

    def test_global(self):
        r = parse("global $a, $b, $c;")
        assert r == Block([Global(["a", "b", "c"])])
        r = parse("global $a;")
        assert r == Block([Global(["a"])])

    def test_constant(self):
        r = parse("$x = c;")
        assert r == Block([Stmt(Assignment(Variable(ConstantStr("x")),
                                           NamedConstant("c")))])

    def test_do_while(self):
        r = parse("do { 1; } while (TRUE);")
        assert r == Block([DoWhile(Block([Stmt(ConstantInt(1))]),
                                   NamedConstant('TRUE'))])

    def test_assign_array_element_2(self):
        py.test.skip("XXX FIXME")
        r = parse("$x[0][0];")
        assert r == Block([Stmt(GetItem(GetItem(Variable(ConstantStr("x")),
                                                ConstantInt(0)),
                                        ConstantInt(0)))])
        r = parse("$x[0][0] = 1;")
        assert r == Block([Stmt(SetItem(GetItem(Variable(ConstantStr("x")),
                                                ConstantInt(0)),
                                        ConstantInt(0), ConstantInt(1)))])
        r = parse("$x[0][] = 1;")
        assert r == Block([Stmt(Append(GetItem(Variable(ConstantStr("x")),
                                                ConstantInt(0)),
                                        ConstantInt(1)))])

    def test_hash_creation(self):
        r = parse('array("x" => "y", "b" => "a", "z" => 3);')
        assert r == Block([Stmt(Hash([(ConstantStr("x"), ConstantStr("y")),
                                      (ConstantStr("b"), ConstantStr("a")),
                                      (ConstantStr("z"), ConstantInt(3))]))])

    def test_array_mix_creation(self):
        r = parse("array(1, 'a'=>2, 3, 'b'=>'c');")
        expected = Block([Stmt(Hash([(ConstantAppend(), ConstantInt(1)),
                                      (ConstantStr("a"), ConstantInt(2)),
                                      (ConstantAppend(), ConstantInt(3)),
                                      (ConstantStr('b'), ConstantStr('c'))
                                      ]))])

        r = parse("array(14 => 'xcx', 'a'=>2, 3);")
        assert r == Block([Stmt(Hash([(ConstantInt(14), ConstantStr("xcx")),
                                      (ConstantStr("a"), ConstantInt(2)),
                                      (ConstantAppend(), ConstantInt(3))
                                      ]))])

        r = parse("array(1, 2, 3, 4 => 5);")
        assert r == Block([Stmt(Hash([(ConstantAppend(), ConstantInt(1)),
                                      (ConstantAppend(), ConstantInt(2)),
                                      (ConstantAppend(), ConstantInt(3)),
                                      (ConstantInt(4), ConstantInt(5))
                                      ]))])


    def test_iterator(self):
        r = parse("foreach ($x as $y) {}")
        assert r == Block([ForEach(Variable(ConstantStr("x")),
                                   Argument("y"), Block([]))])

    def test_iterator_with_reference(self):
        py.test.skip("XXX: fix me")
        r = parse("foreach ($x as $y => &$z) {}")
        assert r == Block([ForEachKey(Variable(ConstantStr("x")),
                                      Argument("y"),
                                      ReferenceArgument("z"), Block([]))])

    def test_array_cast(self):
        py.test.skip("XXX: fix me")
        r = parse('(array)3;')
        assert r == Block([Stmt(Cast("array", ConstantInt(3)))])

    def test_array_trailing_coma(self):
        r = parse("array(1,);")
        assert r == Block([Stmt(Array([ConstantInt(1)]))])

    def test_array_single_elem(self):
        r = parse("array(1 => 2);")
        assert r == Block([Stmt(Hash([(ConstantInt(1), ConstantInt(2))]))])

    def test_comments(self):
        r = parse('''1; // comment
        2;''')
        assert r == Block([Stmt(ConstantInt(1)), Stmt(ConstantInt(2, 1), 1)])
        r = parse('''
        1;
        1 /* abc * / */ + /* abc */ 2;
        ''')
        expected = Block([Stmt(ConstantInt(1, 1), 1),
                          Stmt(BinOp("+",
                                     ConstantInt(1, 2),
                                     ConstantInt(2, 2),
                                     2)
                               , 2)], 0)
        assert r == expected

    def test_comments_2(self):
        r = parse('''
        1;
        # some other comment
        2;
        ''')
        assert r == Block([Stmt(ConstantInt(1, 1), 1),
                           Stmt(ConstantInt(2, 3), 3)])

    def test_print(self):
        py.test.xfail("unsuporrted gramma")
        r = parse('''
        print 1;
        ''')
        assert r == Block([Echo([ConstantInt(1)], 1)])

    def test_print_new(self):
        r = parse('''
        print 1;
        ''')
        assert r == Block([
                Stmt(Echo([ConstantInt(1, 1)], 1), 1)
                ])

    def test_default_args(self):
        r = parse('''
        function f($a = 3)
        {
        }
        ''')
        assert r == Block([FunctionDecl(
                    "f",
                    [
                        DefaultArgument("a",
                                        ConstantInt(3, 1), 1)],
                    Block([], 2), 1)])

    def test_static(self):
        r = parse('''
        static $a = 0, $x;
        ''')
        assert r == Block([StaticDecl([InitializedVariable('a',
                                        ConstantInt(0, 1), 1),
                                       UninitializedVariable("x", 1)], 1)])
        r = parse('''
        static $a, $x = 0, $y, $z = 0;
        ''')
        assert r == Block([StaticDecl([UninitializedVariable("a", 1),
                                       InitializedVariable('x',
                                        ConstantInt(0, 1), 1),
                                       UninitializedVariable("y", 1),
                                       InitializedVariable('z',
                                       ConstantInt(0, 1), 1)], 1)])
        r = parse('''
        static $x = 0;
        ''')
        assert r == Block([StaticDecl([InitializedVariable('x',
                                           ConstantInt(0, 1), 1)], 1)])
        r = parse('''
        static $x;
        ''')
        assert r == Block([StaticDecl([UninitializedVariable('x', 1)], 1)])
        r = parse('''
        static $x = 3;
        ''')
        assert r == Block([StaticDecl([InitializedVariable('x',
                                                        ConstantInt(3, 1), 1)], 1)])

    def test_octal(self):
        r = parse('''
        027;
        ''')
        assert r == Block([Stmt(ConstantInt(23, 1), 1)])

    # def test_octal_overflow(self):
    #     r = parse('''
    #     0277777777777777777777;
    #     ''')
    #     assert r == Block([Stmt(ConstantFloat(3.4587645138205E+18, 1), 1)])

    def test_ill_octal(self):
        r = parse('''
        02792;
        ''')
        assert r == Block([Stmt(ConstantInt(23, 1), 1)])

    def test_more_ill_octal(self):
        r = parse('''
        -07182;
        ''')
        assert r == Block([Stmt(PrefixOp('-', ConstantInt(57, 1), 1), 1)])

    def test_hex(self):
        r = parse('''
        0xff;
        ''')
        assert r == Block([Stmt(ConstantInt(255, 1), 1)])

    def test_hex2(self):
        py.test.xfail("now we have overflow")
        r = parse('''
        0xff33ff33f23f;
        ''')
        assert r == Block([Stmt(ConstantInt(int('0xff33ff33f23f', 16)), 1)])

    def test_hex_overflow(self):
        r = parse('''
        0xff33ff33f23f;
        ''')
        assert r == Block([Stmt(ConstantFloat(280598790009407.0, 1), 1)])

    def test_exponent(self):
        r = parse('''
        10e1;
        ''')
        expected = Block([Stmt(ConstantFloat(float(100.0), 1), 1)])
        assert r == expected

    def test_exponent_float(self):
        r = parse('''
        10.3e1;
        ''')
        expected = Block([Stmt(ConstantFloat(float(103.0), 1), 1)])
        assert r == expected

    def test_exponent_float_plus(self):
        r = parse('''
        10.3e+1;
        ''')
        assert r == Block([Stmt(ConstantFloat(float('10.3e+1'), 1), 1)])

    def test_exponent_float_minus(self):
        r = parse('''
        10.3e-1;
        ''')
        assert r == Block([Stmt(ConstantFloat(float('10.3e-1'), 1), 1)])

    def test_exponent_simple(self):
        r = parse('''
        2.345e1;
        ''')
        assert r == Block([Stmt(ConstantFloat(23.45, 1), 1)])

    def test_exponent_simple_minus(self):
        r = parse('''
        -2.345e1;
        ''')
        assert r == Block([Stmt(PrefixOp('-', ConstantFloat(23.45, 1), 1), 1)])

    def test_minus_octal(self):
        r = parse('''
        -027;
        ''')
        assert r == Block([Stmt(PrefixOp('-', ConstantInt(23, 1), 1), 1)])

    def test_bug_1(self):
        r = parse('$i < $iter and $Tr;')
        expected =  Block([Stmt(And(BinOp("<", Variable(ConstantStr("i")),
                                          Variable(ConstantStr("iter"))),
                                    Variable(ConstantStr("Tr"))))])
        assert r == expected

    def test_break_with_expr(self):
        raises(ParsingError, lambda : parse("break 1+1;"))
        raises(ParsingError, lambda : parse("break 1+$x;"))
        raises(ParsingError, lambda : parse("break $x;"))
        raises(ParsingError, lambda : parse("break -1;"))
        r = parse('''
        break 1;
        ''')
        assert r == Block([Break(levels=ConstantInt(1, 1), lineno=1)])

    def test_continue_with_expr(self):
        raises(ParsingError, lambda : parse("continue 1+1;"))
        raises(ParsingError, lambda : parse("continue 1+$x;"))
        raises(ParsingError, lambda : parse("continue $x;"))
        raises(ParsingError, lambda : parse("continue -1;"))
        r = parse('''
        continue 1;
        ''')
        assert r == Block([Continue(levels=ConstantInt(1, 1), lineno=1)])
