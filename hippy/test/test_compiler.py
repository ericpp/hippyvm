
import py
from hippy.objects.intobject import W_IntObject
from hippy.sourceparser import parse
from hippy.astcompiler import compile_ast, bc_preprocess, CompilerContext
from hippy.objspace import ObjSpace
from hippy.objects import reference, floatobject
from hippy import consts

def test_preprocess_string():
    def prepr(s):
        no, has_vars = ctx.preprocess_str(s)
        if not has_vars:
            return ctx.names[no]
        else:
            return ctx.consts[no]

    ctx = CompilerContext('fname', [], 0, None)
    assert prepr('\\\\') == '\\'
    assert prepr('\\n') == '\n'
    assert prepr('\\\'') == '\''
    c = prepr('$x')
    assert c.strings == ['', '']
    assert c.var_nums == [0]
    c = prepr('a $x $y b $z ')
    assert c.strings == ['a ', ' ', ' b ', ' ']
    assert c.var_nums == [0, 1, 2]

class TestCompiler(object):
    def check_compile(self, source, expected=None, **kwds):
        self.space = ObjSpace()
        bc = compile_ast('<input>', source, parse(source), self.space, **kwds)
        if expected is not None:
            self.compare(bc, expected)
        return bc

    def compare(self, bc, expected):
        expected = bc_preprocess(expected)
        bcdump = bc.dump()
        bcdump = bcdump.splitlines()
        expected = expected.splitlines()
        maxlen = max(len(expected), len(bcdump))
        expected += ['' * (maxlen - len(expected))]
        bcdump += ['' * (maxlen - len(bcdump))]
        print "Got:" + " "*26 + "Expected:"
        for bcline, expline in zip(bcdump, expected):
            print "%s%s %s" % (bcline, " " * (30 - len(bcline)),
                                expline)
            bcline = bcline.split()
            expline = expline.split()
            # we fail if the line we got is different than the expected line,
            # possibly after removing the first word (the index number)
            if bcline != expline and bcline[1:] != expline:
                assert False

    def test_assign(self):
        bc = self.check_compile("$x = 3;", """
        LOAD_CONST 0
        LOAD_REF 0
        STORE 1
        DISCARD_TOP
        LOAD_NULL
        RETURN
        """)
        c = bc.consts[0]
        assert isinstance(c, W_IntObject)
        assert c.intval == 3
        assert bc.stackdepth == 2

    def test_assign_nonconst(self):
        bc = self.check_compile("$x = $y;", """
        LOAD_DEREF 0
        LOAD_REF 1
        STORE 1
        DISCARD_TOP
        LOAD_NULL
        RETURN
        """)
        assert bc.stackdepth == 2

    def test_addition(self):
        self.check_compile("3 + $x;", """
        LOAD_CONST 0
        LOAD_REF 0
        BINARY_ADD
        DISCARD_TOP
        LOAD_NULL
        RETURN
        """)

    def test_substraction(self):
        self.check_compile("3 - $x;", """
        LOAD_CONST 0
        LOAD_REF 0
        BINARY_SUB
        DISCARD_TOP
        LOAD_NULL
        RETURN
        """)

    def test_mul(self):
        self.check_compile("3 - $x * 3;", """
        LOAD_CONST 0
        LOAD_REF 0
        LOAD_CONST 0
        BINARY_MUL
        BINARY_SUB
        DISCARD_TOP
        LOAD_NULL
        RETURN
        """)

    def test_echo(self):
        bc = self.check_compile("echo 3;", """
        LOAD_CONST 0
        ECHO 1
        LOAD_NULL
        RETURN
        """)
        assert bc.stackdepth == 1

    def test_float_const(self):
        bc = self.check_compile("echo 3.5;", """
        LOAD_CONST 0
        ECHO 1
        LOAD_NULL
        RETURN""")
        assert bc.consts[0].floatval == 3.5

    def test_echo_2(self):
        bc = self.check_compile("echo $x, $y;", """
        LOAD_DEREF 0
        LOAD_DEREF 1
        ECHO 2
        LOAD_NULL
        RETURN
        """)
        assert bc.stackdepth == 2

    def test_unary_minus(self):
        self.check_compile("-$x;+$y;", """
        LOAD_REF 0
        UNARY_MINUS
        DISCARD_TOP
        LOAD_REF 1
        UNARY_PLUS
        DISCARD_TOP
        LOAD_NULL
        RETURN
        """)

    def test_float_const_cache(self):
        bc = self.check_compile("echo 3.5 + 3.5;", """
        LOAD_CONST 0
        LOAD_CONST 0
        BINARY_ADD
        DEREF           # XXX remove?
        ECHO 1
        LOAD_NULL
        RETURN""")
        assert bc.consts[0].floatval == 3.5

    def test_if(self):
        bc = self.check_compile("""
        if (1) {
          $x = 1;
        }
        echo $x;
        """, """
        LOAD_CONST 0
        JUMP_IF_FALSE 16
        LOAD_CONST 0
        LOAD_REF 0
        STORE 1
        DISCARD_TOP
     16 LOAD_DEREF 0
        ECHO 1
        LOAD_NULL
        RETURN
        """)
        assert bc.stackdepth == 2

    def test_ifelse(self):
        bc = self.check_compile("""
        if (1) {
          $x = 1;
        } else {
          $x = 1 + 3;
        }
        echo $x;
        """, """
        LOAD_CONST 0
        JUMP_IF_FALSE 19
        LOAD_CONST 0
        LOAD_REF 0
        STORE 1
        DISCARD_TOP
        JUMP_FORWARD 34
     19 LOAD_CONST 0
        LOAD_CONST 1
        BINARY_ADD
        DEREF           # XXX remove?
        LOAD_REF 0
        STORE 1
        DISCARD_TOP
     34 LOAD_DEREF 0
        ECHO 1
        LOAD_NULL
        RETURN
        """)
        assert bc.stackdepth == 2

    def test_ifelseif(self):
        self.check_compile("""
        if (1) {
          $x = 1;
        } elseif (2) {
          $x = 2;
        }
        echo $x;
        """, """
        LOAD_CONST 0
        JUMP_IF_FALSE 19
        LOAD_CONST 0
        LOAD_REF 0
        STORE 1
        DISCARD_TOP
        JUMP_FORWARD 35
     19 LOAD_CONST 1
        JUMP_IF_FALSE 35
        LOAD_CONST 1
        LOAD_REF 0
        STORE 1
        DISCARD_TOP
     35 LOAD_DEREF 0
        ECHO 1
        LOAD_NULL
        RETURN
        """)

    def test_ifelseif_else(self):
        self.check_compile("""
        if (1) {
          $x = 1;
        } elseif (2) {
          $x = 2;
        } else {
          $x = 3;
        }
        echo $x;
        """, """
        LOAD_CONST 0
        JUMP_IF_FALSE 19
        LOAD_CONST 0
        LOAD_REF 0
        STORE 1
        DISCARD_TOP
        JUMP_FORWARD 48
     19 LOAD_CONST 1
        JUMP_IF_FALSE 38
        LOAD_CONST 1
        LOAD_REF 0
        STORE 1
        DISCARD_TOP
        JUMP_FORWARD 48
     38 LOAD_CONST 2
        LOAD_REF 0
        STORE 1
        DISCARD_TOP
     48 LOAD_DEREF 0
        ECHO 1
        LOAD_NULL
        RETURN
        """)

    def test_while(self):
        self.check_compile("""
        $i = 0;
        while ($i < 3)
          $i++;
        """, """
        LOAD_CONST 0
        LOAD_REF 0
        STORE 1
        DISCARD_TOP
     10 LOAD_REF 0
        LOAD_CONST 1
        BINARY_LT
        JUMP_IF_FALSE 28
        LOAD_REF 0
        SUFFIX_PLUSPLUS
        DISCARD_TOP
        JUMP_BACKWARD 10
     28 LOAD_NULL
        RETURN
        """)

    def test_function_call(self):
        bc = self.check_compile("""
        cos($i, $j, $k);
        """, """
        LOAD_NAME 0
        GETFUNC
        LOAD_REF 0
        ARG 0
        LOAD_REF 1
        ARG 1
        LOAD_REF 2
        ARG 2
        CALL 3
        DISCARD_TOP
        LOAD_NULL
        RETURN
        """)
        assert bc.stackdepth == 4

    def test_function_call_nonref_arg(self):
        bc = self.check_compile("""
        f($i+2, $j);
        """, """
        LOAD_NAME 0
        GETFUNC
        LOAD_REF 0
        LOAD_CONST 0
        BINARY_ADD
        ARG 0
        LOAD_REF 1
        ARG 1
        CALL 2
        DISCARD_TOP
        LOAD_NULL
        RETURN
        """)
        assert bc.stackdepth == 3

    def test_function_call_mayberef_arg(self):
        self.check_compile("""
        f($a[5]);
        """, """
        LOAD_NAME 0
        GETFUNC
        ARG_IS_BYREF 0
        JUMP_IF_FALSE 32
        LOAD_CONST 0    # this is the case where f() takes a reference argument
        LOAD_NONE
        LOAD_REF 0
        FETCHITEM 2
        MAKE_REF 2
        STOREITEM_REF 2
        STORE 2
        JUMP_FORWARD 39
     32 LOAD_REF 0      # this is the case where f() does not take a ref arg
        LOAD_CONST 0
        GETITEM
     39 ARG 0
        CALL 1
        DISCARD_TOP
        LOAD_NULL
        RETURN
        """)

    def test_for(self):
        self.check_compile("""
        for ($i = 0; $i < 10; $i++) {$k++;}
        """, """
        LOAD_CONST 0
        LOAD_REF 0
        STORE 1
        DISCARD_TOP
     10 LOAD_REF 0
        LOAD_CONST 1
        BINARY_LT
        JUMP_IF_FALSE 33
        LOAD_REF 1
        SUFFIX_PLUSPLUS
        DISCARD_TOP
        LOAD_REF 0
        SUFFIX_PLUSPLUS
        DISCARD_TOP
        JUMP_BACKWARD 10
     33 LOAD_NULL
        RETURN
        """)

    def test_long_for(self):
        source = ["for ($i = 0; $i < 3; $i++) {"]
        for i in range(100):
            source.append("$j = 1;")
        source.append("}")
        source = "".join(source)
        compile_ast('<input>', source, parse(source), None)
        # assert did not crash

    def test_constant_str(self):
        self.check_compile('$x = "abc"; echo $x . $x;', """
        LOAD_NAME 0
        LOAD_REF 0
        STORE 1
        DISCARD_TOP
        LOAD_REF 0
        LOAD_REF 0
        BINARY_CONCAT
        DEREF           # XXX remove?
        ECHO 1
        LOAD_NULL
        RETURN
        """)

    def test_str_consts_preprocessed(self):
        bc = self.check_compile('$x = "\\n"; $y = "$x";', """
        LOAD_NAME 0
        LOAD_REF 0
        STORE 1
        DISCARD_TOP
        LOAD_CONST_INTERPOLATE 0
        LOAD_REF 1
        STORE 1
        DISCARD_TOP
        LOAD_NULL
        RETURN
        """)
        assert bc.names[0] == '\n';

    def test_getitem_setitem(self):
        self.check_compile("$x[3]; $x[3] = 1;", """
        LOAD_REF 0
        LOAD_CONST 0
        GETITEM
        DISCARD_TOP
        LOAD_CONST 0
        LOAD_CONST 1
        LOAD_REF 0
        FETCHITEM 2
        STOREITEM 2
        STORE 2
        DISCARD_TOP
        LOAD_NULL
        RETURN
        """)

    def test_setitem_2(self):
        self.check_compile("$x[$y-1][$z+5] = 1;", """
        LOAD_REF 0
        LOAD_CONST 0
        BINARY_SUB     # $y-1
        LOAD_REF 1
        LOAD_CONST 1
        BINARY_ADD     # $z+5
        LOAD_CONST 0   # 1
        LOAD_REF 2     # $x
        FETCHITEM 3
        FETCHITEM 3
        STOREITEM 3
        STOREITEM 3
        STORE 3
        DISCARD_TOP
        LOAD_NULL
        RETURN
        """)

    def test_array_constructor(self):
        self.check_compile("$x = array(1, 2, $y);", """
        LOAD_CONST 0
        LOAD_CONST 1
        LOAD_DEREF 0
        MAKE_ARRAY 3
        DEREF
        LOAD_REF 1
        STORE 1
        DISCARD_TOP
        LOAD_NULL
        RETURN
        """)

    def test_getitem_2_reference(self):
        self.check_compile("$a = & $b[0][0];", """
        LOAD_CONST 0
        LOAD_CONST 0
        LOAD_NONE
        LOAD_REF 0
        FETCHITEM 3
        FETCHITEM 3
        MAKE_REF 3
        STOREITEM_REF 3
        STOREITEM 3
        STORE 3
        STORE_FAST_REF 1
        DISCARD_TOP
        LOAD_NULL
        RETURN
        """)

    def test_function_decl(self):
        bc = self.check_compile("""\
        echo 5;
        function f($a, &$b, $c) { return $a + $b + $c; }""", """
        LOAD_CONST 0
        ECHO 1
        DECLARE_FUNC 0
        LOAD_NULL
        RETURN
        """)
        assert bc.user_functions[0].tp == [consts.ARG_ARGUMENT,
                                           consts.ARG_REFERENCE,
                                           consts.ARG_ARGUMENT]
        assert bc.user_functions[0].names == ['a', 'b', 'c']
        assert bc.startlineno == 1
        self.compare(bc.user_functions[0].bytecode, """
        LOAD_REF 0
        LOAD_REF 1
        BINARY_ADD
        LOAD_REF 2
        BINARY_ADD
        RETURN
        LOAD_NULL   # unreachable
        RETURN
        """)
        assert bc.user_functions[0].bytecode.startlineno == 2
        assert bc.user_functions[0].bytecode.name == 'f'

    def test_function_decl_2(self):
        bc = self.check_compile("""
        function f() { return; }""", """
        DECLARE_FUNC 0
        LOAD_NULL
        RETURN
        """)
        assert bc.user_functions[0].tp == []
        self.compare(bc.user_functions[0].bytecode, """
        LOAD_NULL
        RETURN
        LOAD_NULL   # unreachable
        RETURN
        """)

    def test_append(self):
        self.check_compile("""
        $a[] = $b;
        """, """
        LOAD_NONE
        LOAD_DEREF 0
        LOAD_REF 1
        APPEND_INDEX 2
        FETCHITEM 2
        STOREITEM 2
        STORE 2
        DISCARD_TOP
        LOAD_NULL
        RETURN
        """)

    def test_append_reference(self):
        self.check_compile("""
        $a = &$b[];
        """, """
        LOAD_NONE            # NULL
        LOAD_NONE            # NULL, NULL
        LOAD_REF 0          # NULL, NULL, Ref$b
        APPEND_INDEX 2       # idx, NULL, Ref$b
        FETCHITEM 2          # idx, NULL, Ref$b, Array$b[idx]
        MAKE_REF 2           # idx, NewRef, Ref$b, Array$b[idx]
        STOREITEM_REF 2      # NewArray, NewRef, Ref$b, Array$b[idx]
        STORE 2              # NewRef
        STORE_FAST_REF 1
        DISCARD_TOP
        LOAD_NULL
        RETURN
        """)

    def test_reference_append(self):
        self.check_compile("""
        $a[] = &$b;
        """, """
        LOAD_NONE            # NULL
        LOAD_REF 0          # NULL, Ref$b
        LOAD_REF 1          # NULL, Ref$b, Ref$a
        APPEND_INDEX 2       # idx, Ref$b, Ref$a
        STOREITEM_REF 2      # NewArray, Ref$b, Ref$a ]
        STORE 2              # Ref$b
        DISCARD_TOP
        LOAD_NULL
        RETURN
        """)

    def test_and(self):
        self.check_compile("""
        $a && $b;
        """, """
        LOAD_REF 0
        IS_TRUE
        JUMP_IF_FALSE_NO_POP 12
        DISCARD_TOP
        LOAD_REF 1
        IS_TRUE
     12 DISCARD_TOP
        LOAD_NULL
        RETURN
        """)

    def test_and_or_forced_parenthesis(self):
        self.check_compile("""
        $a && ($b || $c);
        """, """
        LOAD_REF 0
        IS_TRUE
        JUMP_IF_FALSE_NO_POP 21
        DISCARD_TOP
        LOAD_REF 1
        IS_TRUE
        JUMP_IF_TRUE_NO_POP 20
        DISCARD_TOP
        LOAD_REF 2
        IS_TRUE
     20 IS_TRUE
     21 DISCARD_TOP
        LOAD_NULL
        RETURN
        """)

    def test_and_or_default_precedence(self):
        self.check_compile("""
        $a && $b || $c;
        """, """
        LOAD_REF 0
        IS_TRUE
        JUMP_IF_FALSE_NO_POP 12
        DISCARD_TOP
        LOAD_REF 1
        IS_TRUE
     12 IS_TRUE
        JUMP_IF_TRUE_NO_POP 21
        DISCARD_TOP
        LOAD_REF 2
        IS_TRUE
     21 DISCARD_TOP
        LOAD_NULL
        RETURN
        """)

    def test_inplace_add(self):
        self.check_compile("""
        $a += 2;
        """, """
        LOAD_CONST 0
        LOAD_REF 0
        DUP_TOP_AND_NTH 1
        BINARY_ADD
        POP_AND_POKE_NTH 1
        STORE 1
        DISCARD_TOP
        LOAD_NULL
        RETURN
        """)

    def test_global(self):
        self.check_compile("""
        global $a, $b, $c;
        """, """
        DECLARE_GLOBAL 0
        DECLARE_GLOBAL 1
        DECLARE_GLOBAL 2
        LOAD_NULL
        RETURN
        """)

    def test_constant(self):
        self.check_compile("""
        $x = c;
        """, """
        LOAD_NAMED_CONSTANT 0
        DEREF
        LOAD_REF 0
        STORE 1
        DISCARD_TOP
        LOAD_NULL
        RETURN
        """)

    def test_dowhile(self):
        self.check_compile("""
        do { 1; } while (2);
        """, """
      0 LOAD_CONST 0
        DISCARD_TOP
        LOAD_CONST 1
        JUMP_BACK_IF_TRUE 0
        LOAD_NULL
        RETURN
        """)

    def test_reference_simple(self):
        self.check_compile("""
        $b; $a = &$b;
        """, """
        LOAD_REF 0
        DISCARD_TOP
        LOAD_REF 0
        STORE_FAST_REF 1
        DISCARD_TOP
        LOAD_NULL
        RETURN
        """)

    def test_reference_left_array(self):
        self.check_compile("""
        $b; $a[5][6][7] =& $b;
        """, """
        LOAD_REF 0
        DISCARD_TOP
        LOAD_CONST 0
        LOAD_CONST 1
        LOAD_CONST 2
        LOAD_REF 0
        LOAD_REF 1
        FETCHITEM 4
        FETCHITEM 4
        STOREITEM_REF 4
        STOREITEM 4
        STOREITEM 4
        STORE 4
        DISCARD_TOP
        LOAD_NULL
        RETURN
        """)

    def test_reference_right_array(self):
        self.check_compile("""
        $b; $a =& $b[7][8];
        """, """
        LOAD_REF 0
        DISCARD_TOP
        LOAD_CONST 0
        LOAD_CONST 1
        LOAD_NONE
        LOAD_REF 0
        FETCHITEM 3
        FETCHITEM 3
        MAKE_REF 3
        STOREITEM_REF 3
        STOREITEM 3
        STORE 3
        STORE_FAST_REF 1
        DISCARD_TOP
        LOAD_NULL
        RETURN
        """)

    def test_reference_both_left_right_array(self):
        self.check_compile("""
        $b+0; $a[0] =& $b[1];
        """, """
        LOAD_REF 0
        LOAD_CONST 0
        BINARY_ADD
        DISCARD_TOP
        LOAD_CONST 0
        LOAD_CONST 1
        LOAD_NONE
        LOAD_REF 0
        FETCHITEM 2
        MAKE_REF 2
        STOREITEM_REF 2
        STORE 2
        LOAD_REF 1
        STOREITEM_REF 2
        STORE 2
        DISCARD_TOP
        LOAD_NULL
        RETURN
        """)

    def test_break(self):
        self.check_compile("""
        while (1) {
           break;
        }
        """, """
      0 LOAD_CONST 0
        JUMP_IF_FALSE 12
        JUMP_FORWARD 12
        JUMP_BACKWARD 0
     12 LOAD_NULL
        RETURN
        """)

    def test_continue(self):
        self.check_compile("""
        while (1) {
           continue;
        }
        """, """
      0 LOAD_CONST 0
        JUMP_IF_FALSE 12
        JUMP_BACKWARD 0
        JUMP_BACKWARD 0
     12 LOAD_NULL
        RETURN
        """)

    def test_break_for(self):
        self.check_compile("""
        for(1;1;1) {
           break;
        }
        """, """
        LOAD_CONST 0
        DISCARD_TOP
      4 LOAD_CONST 0
        JUMP_IF_FALSE 20
        JUMP_FORWARD 20
        LOAD_CONST 0
        DISCARD_TOP
        JUMP_BACKWARD 4
     20 LOAD_NULL
        RETURN
        """)

    def test_break_do_while(self):
        self.check_compile("""
        do {
           break;
        } while(1);
        """, """
      0 JUMP_FORWARD 9
        LOAD_CONST 0
        JUMP_BACK_IF_TRUE 0
      9 LOAD_NULL
        RETURN
        """)

    def test_if_expr(self):
        self.check_compile("""
        $a = 0 ? 5 : 10;
        """, """
        LOAD_CONST 0
        JUMP_IF_FALSE 12
        LOAD_CONST 1
        JUMP_FORWARD 15
     12 LOAD_CONST 2
     15 DEREF
        LOAD_REF 0
        STORE 1
        DISCARD_TOP
        LOAD_NULL
        RETURN
        """)

    def test_iterator_1(self):
        bc = self.check_compile("""
        foreach ($a as $b) {$b+1;}
        """, """
        LOAD_REF 0
        CREATE_ITER
      4 NEXT_VALUE_ITER 25
        LOAD_REF 1
        STORE 1
        DISCARD_TOP
        LOAD_REF 1         # start of the code within the { }
        LOAD_CONST 0
        BINARY_ADD
        DISCARD_TOP
        JUMP_BACKWARD 4
     25 LOAD_NULL
        RETURN
        """)
        assert bc.stackdepth == 3

    def test_iterator_2(self):
        bc = self.check_compile("""
        foreach ($a as $b => $c) {$b;}
        """, """
        LOAD_REF 0
        CREATE_ITER
      4 NEXT_ITEM_ITER 28
        LOAD_REF 1          # store first $c
        STORE 1
        DISCARD_TOP
        LOAD_REF 2          # then store $b
        STORE 1
        DISCARD_TOP
        LOAD_REF 2          # start of the code within the { }
        DISCARD_TOP
        JUMP_BACKWARD 4
     28 LOAD_NULL
        RETURN
        """)
        assert bc.stackdepth == 4

    def test_iterator_3(self):
        bc = self.check_compile("""
        foreach ($a as $b[0][1]) {$b+1;}
        """, """
        LOAD_REF 0
        CREATE_ITER
      4 NEXT_VALUE_ITER 46
        LOAD_CONST 0
        LOAD_CONST 1
        ROT 2
        LOAD_REF 1       # $b
        FETCHITEM 3
        FETCHITEM 3
        STOREITEM 3
        STOREITEM 3
        STORE 3
        DISCARD_TOP
        LOAD_REF 1         # start of the code within the { }
        LOAD_CONST 1
        BINARY_ADD
        DISCARD_TOP
        JUMP_BACKWARD 4
     46 LOAD_NULL
        RETURN
        """)
        assert bc.stackdepth == 7

    def test_iterator_ref_1(self):
        bc = self.check_compile("""
        foreach ($a as &$b) {$b+=1;}
        """, """
        LOAD_REF 0
        CREATE_ITER_REF
      4 NEXT_VALUE_ITER 31
        STORE_FAST_REF 1
        DISCARD_TOP
        LOAD_CONST 0       # start of the code within the { }
        LOAD_REF 1
        DUP_TOP_AND_NTH 1
        BINARY_ADD
        POP_AND_POKE_NTH 1
        STORE 1
        DISCARD_TOP
        JUMP_BACKWARD 4
     31 LOAD_NULL
        RETURN
        """)
        assert bc.stackdepth == 5

    def test_iterator_ref_2(self):
        bc = self.check_compile("""
        foreach ($a as $k=>&$b[5][5]) {$b;}
        """, """
        LOAD_REF 0
        CREATE_ITER_REF
      4 NEXT_ITEM_ITER 46
        LOAD_CONST 0        # store the value as reference into $b[5]
        LOAD_CONST 0
        ROT 2
        LOAD_REF 1
        FETCHITEM 3
        STOREITEM_REF 3
        STOREITEM 3
        STORE 3
        DISCARD_TOP
        LOAD_REF 2          # then store the key into $k
        STORE 1
        DISCARD_TOP
        LOAD_REF 1          # start of the code within the { }
        DISCARD_TOP
        JUMP_BACKWARD 4
     46 LOAD_NULL
        RETURN
        """)
        assert bc.stackdepth == 7

    def test_array_cast(self):
        self.check_compile("""
        (array)3;
        """, """
        LOAD_CONST 0
        CAST_ARRAY
        DISCARD_TOP
        LOAD_NULL
        RETURN
        """)

    def test_dynamic_call(self):
        self.check_compile("""
        $a = 'func';
        $a(3, 4);
        """, """
        LOAD_NAME 0
        LOAD_REF 0
        STORE 1
        DISCARD_TOP
        LOAD_REF 0
        GETFUNC
        LOAD_CONST 0
        ARG 0
        LOAD_CONST 1
        ARG 1
        CALL 2
        DISCARD_TOP
        LOAD_NULL
        RETURN
        """)

    def test_lineno_mapping(self):
        bc = self.check_compile("""\
        1;
        2;
        3;
        """)
        assert bc.bc_mapping[0] == 1
        assert bc.bc_mapping[4] == 2
        assert bc.bc_mapping[8] == 3

    def test_make_hash(self):
        bc = self.check_compile("""
        array(1=>$a);
        """, """
        LOAD_CONST 0
        LOAD_DEREF 0
        MAKE_HASH 1
        DISCARD_TOP
        LOAD_NULL
        RETURN
        """)
        assert bc.stackdepth == 2

    def test_make_hash_const(self):
        bc = self.check_compile("""
        array(1=>2, 5=>null, 6=>true, 4=>3.5, 'abc'=>'def',
              'h'=>false);
        """, """
        LOAD_CONST 0
        DISCARD_TOP
        LOAD_NULL
        RETURN
        """)
        assert bc.stackdepth == 1
        arr = bc.consts[0]
        space = self.space
        assert arr.tp == space.tp_array
        assert space.str_w(space.getitem(arr, space.newstrconst('abc'))) == "def"

    def test_make_array_ref(self):
        bc = self.check_compile("""
        array(&$a);
        """, """
        LOAD_REF 0
        MAKE_ARRAY 1
        DISCARD_TOP
        LOAD_NULL
        RETURN
        """)

    def test_make_hash_ref(self):
        bc = self.check_compile("""
        array(5=>&$a);
        """, """
        LOAD_CONST 0
        LOAD_REF 0
        MAKE_HASH 1
        DISCARD_TOP
        LOAD_NULL
        RETURN
        """)

    def test_extra_offset(self):
        bc = self.check_compile("""\
        1;
        2;
        """, """
        LOAD_CONST 0
        DISCARD_TOP
        LOAD_CONST 1
        DISCARD_TOP
        LOAD_NULL
        RETURN
        """)
        assert bc.bc_mapping == [1, 1, 1, 1, 2, 2, 2, 2, 2, 2]

    def test_declare_static(self):
        self.check_compile("""
        static $a;
        """, """
        LOAD_CONST 0      # loads a reference
        STORE_FAST_REF 0  # store it into $a
        DISCARD_TOP
        LOAD_NULL
        RETURN
        """)

    def test_initialized_static(self):
        bc = self.check_compile("""
        static $a = 17.5;
        """, """
        LOAD_CONST 0      # loads a reference
        STORE_FAST_REF 0  # store it into $a
        DISCARD_TOP
        LOAD_NULL
        RETURN
        """)
        assert isinstance(bc.consts[0], reference.W_Reference)
        assert isinstance(bc.consts[0].w_value, floatobject.W_FloatObject)

    def test_print_exprs(self):
        bc = self.check_compile("$x = 3;", """
        LOAD_CONST 0
        LOAD_REF 0
        STORE 1
        DEREF
        LOAD_NAME 0
        ECHO 2
        LOAD_NULL
        RETURN
        """, print_exprs=True)
        c = bc.consts[0]
        assert isinstance(c, W_IntObject)
        assert c.intval == 3
        assert bc.stackdepth == 2

    def test_mixed_case(self):
        self.check_compile("array(nUll);", """
        LOAD_CONST 0
        DISCARD_TOP
        LOAD_NULL
        RETURN
        """)

    def test_call_unset_stmt(self):
        self.check_compile("unset($a, $c);", """
        LOAD_NAME 0
        GETFUNC
        LOAD_REF 0
        ARG 0
        LOAD_REF 1
        ARG 1
        CALL 2
        DISCARD_TOP
        LOAD_NULL
        RETURN
        """)
