
import py
from hippy.objects.intobject import W_IntObject
from hippy.sourceparser import parse
from hippy.astcompiler import compile_ast, bc_preprocess, CompilerContext
from hippy.objspace import ObjSpace
from hippy import consts

def test_preprocess_string():
    def prepr(s):
        no, has_vars = ctx.preprocess_str(s)
        if not has_vars:
            return ctx.names[no]
        else:
            return ctx.consts[no]

    ctx = CompilerContext(0, None)
    assert prepr('\\\\') == '\\'
    assert prepr('\\n') == '\n'
    assert prepr('\\\'') == '\''
    c = prepr('$x')
    assert c.strings == ['', '']
    assert c.vars == ['x']
    c = prepr('a $x $y b $z ')
    assert c.strings == ['a ', ' ', ' b ', ' ']
    assert c.vars == ['x', 'y', 'z']

class TestCompiler(object):
    def check_compile(self, source, expected=None, **kwds):
        self.space = ObjSpace()
        bc = compile_ast(parse(source), self.space, **kwds)
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
        LOAD_FAST 0
        STORE 1
        DISCARD_TOP
        LOAD_NULL
        RETURN
        """)
        c = bc.consts[0]
        assert isinstance(c, W_IntObject)
        assert c.intval == 3
        assert bc.stackdepth == 2

    def test_addition(self):
        self.check_compile("3 + $x;", """
        LOAD_CONST 0
        LOAD_FAST 0
        BINARY_ADD
        DISCARD_TOP
        LOAD_NULL
        RETURN
        """)

    def test_substraction(self):
        self.check_compile("3 - $x;", """
        LOAD_CONST 0
        LOAD_FAST 0
        BINARY_SUB
        DISCARD_TOP
        LOAD_NULL
        RETURN
        """)

    def test_mul(self):
        self.check_compile("3 - $x * 3;", """
        LOAD_CONST 0
        LOAD_FAST 0
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

    def test_unary_minus(self):
        self.check_compile("-$x;+$y;", """
        LOAD_FAST 0
        UNARY_MINUS
        DISCARD_TOP
        LOAD_FAST 1
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
        LOAD_FAST 0
        STORE 1
        DISCARD_TOP
     16 LOAD_FAST 0
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
        LOAD_FAST 0
        STORE 1
        DISCARD_TOP
        JUMP_FORWARD 33
     19 LOAD_CONST 0
        LOAD_CONST 1
        BINARY_ADD
        LOAD_FAST 0
        STORE 1
        DISCARD_TOP
     33 LOAD_FAST 0
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
        LOAD_FAST 0
        STORE 1
        DISCARD_TOP
        JUMP_FORWARD 35
     19 LOAD_CONST 1
        JUMP_IF_FALSE 35
        LOAD_CONST 1
        LOAD_FAST 0
        STORE 1
        DISCARD_TOP
     35 LOAD_FAST 0
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
        LOAD_FAST 0
        STORE 1
        DISCARD_TOP
        JUMP_FORWARD 48
     19 LOAD_CONST 1
        JUMP_IF_FALSE 38
        LOAD_CONST 1
        LOAD_FAST 0
        STORE 1
        DISCARD_TOP
        JUMP_FORWARD 48
     38 LOAD_CONST 2
        LOAD_FAST 0
        STORE 1
        DISCARD_TOP
     48 LOAD_FAST 0
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
        LOAD_FAST 0
        STORE 1
        DISCARD_TOP
     10 LOAD_FAST 0
        LOAD_CONST 1
        BINARY_LT
        JUMP_IF_FALSE 28
        LOAD_FAST 0
        SUFFIX_PLUSPLUS
        DISCARD_TOP
        JUMP_BACKWARD 10
     28 LOAD_NULL
        RETURN
        """)

    def test_function_call(self):
        bc = self.check_compile("""
        cos($i);
        """, """
        LOAD_FAST 0
        LOAD_NAME 0
        CALL 1
        DISCARD_TOP
        LOAD_NULL
        RETURN
        """)
        assert bc.stackdepth == 2

    def test_for(self):
        self.check_compile("""
        for ($i = 0; $i < 10; $i++) {$k++;}
        """, """
        LOAD_CONST 0
        LOAD_FAST 0
        STORE 1
        DISCARD_TOP
     10 LOAD_FAST 0
        LOAD_CONST 1
        BINARY_LT
        JUMP_IF_FALSE 33
        LOAD_FAST 1
        SUFFIX_PLUSPLUS
        DISCARD_TOP
        LOAD_FAST 0
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
        compile_ast(parse("".join(source)), None)
        # assert did not crash

    def test_constant_str(self):
        self.check_compile('$x = "abc"; echo $x . $x;', """
        LOAD_NAME 0
        LOAD_FAST 0
        STORE 1
        DISCARD_TOP
        LOAD_FAST 0
        LOAD_FAST 0
        BINARY_CONCAT
        ECHO 1
        LOAD_NULL
        RETURN
        """)

    def test_str_consts_preprocessed(self):
        bc = self.check_compile('$x = "\\n"; $y = "$x";', """
        LOAD_NAME 0
        LOAD_FAST 0
        STORE 1
        DISCARD_TOP
        LOAD_CONST_INTERPOLATE 0
        LOAD_FAST 1
        STORE 1
        DISCARD_TOP
        LOAD_NULL
        RETURN
        """)
        assert bc.names[0] == '\n';

    def test_getitem_setitem(self):
        self.check_compile("$x[3]; $x[3] = 1;", """
        LOAD_FAST 0
        LOAD_CONST 0
        GETITEM
        DISCARD_TOP
        LOAD_CONST 0
        LOAD_CONST 1
        LOAD_FAST 0
        FETCHITEM 2
        STOREITEM 2
        STORE 2
        DISCARD_TOP
        LOAD_NULL
        RETURN
        """)

    def test_setitem_2(self):
        self.check_compile("$x[$y-1][$z+5] = 1;", """
        LOAD_FAST 0
        LOAD_CONST 0
        BINARY_SUB     # $y-1
        LOAD_FAST 1
        LOAD_CONST 1
        BINARY_ADD     # $z+5
        LOAD_CONST 0   # 1
        LOAD_FAST 2    # $x
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
        LOAD_FAST 0
        ARRAY 3
        LOAD_FAST 1
        STORE 1
        DISCARD_TOP
        LOAD_NULL
        RETURN
        """)

    def test_getitem_2_reference(self):
        self.check_compile("$a = & $b[0][0];", """
        LOAD_CONST 0
        LOAD_CONST 0
        LOAD_NULL
        LOAD_FAST 0
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
        py.test.skip("XXX FIXME")

        bc = self.check_compile("""
        function f($a, &$b, $c) { return $a + $b + $c; }""", """
        RETURN_NULL
        """)
        assert bc.user_functions.keys() == ['f']
        assert bc.user_functions['f'].args == [(consts.ARG_ARGUMENT, 'a', None),
                                              (consts.ARG_REFERENCE, 'b', None),
                                               (consts.ARG_ARGUMENT, 'c', None)]
        assert bc.startlineno == 0
        self.compare(bc.user_functions['f'].bytecode, """
        LOAD_FAST 0
        LOAD_FAST 1
        LOAD_FAST 2
        BINARY_ADD
        BINARY_ADD
        RETURN
        RETURN_NULL # unreachable
        """)
        assert bc.user_functions['f'].bytecode.startlineno == 1
        assert bc.user_functions['f'].bytecode.name == 'f'

    def test_function_decl_2(self):
        bc = self.check_compile("""
        function f() { return; }""", """
        LOAD_NULL
        RETURN
        """)
        assert bc.user_functions.keys() == ['f']
        assert bc.user_functions['f'].args == []
        self.compare(bc.user_functions['f'].bytecode, """
        LOAD_NULL
        RETURN
        LOAD_NULL   # unreachable
        RETURN
        """)

    def test_append(self):
        self.check_compile("""
        $a[] = 3;
        """, """
        LOAD_NULL
        LOAD_CONST 0
        LOAD_FAST 0
        FETCHITEM_APPEND 2
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
        LOAD_NULL            # NULL
        LOAD_NULL            # NULL, NULL
        LOAD_FAST 0          # NULL, NULL, Ref$b
        FETCHITEM_APPEND 2   # idx, NULL, Ref$b, Array$b[idx]
        MAKE_REF 2           # idx, NewRef, Ref$b, Array$b[idx]
        STOREITEM_REF 2      # NewArray, NewRef, Ref$b, Array$b[idx]
        STORE 2              # NewRef
        STORE_FAST_REF 1
        DISCARD_TOP
        LOAD_NULL
        RETURN
        """)

    def test_and(self):
        self.check_compile("""
        $a && $b;
        """, """
        LOAD_FAST 0
        IS_TRUE
        JUMP_IF_FALSE_NO_POP 12
        LOAD_FAST 1
        IS_TRUE
        ROT_AND_DISCARD
     12 DISCARD_TOP
        LOAD_NULL
        RETURN
        """)

    def test_and_or(self):
        self.check_compile("""
        $a && $b || $c;
        """, """
        LOAD_FAST 0
        IS_TRUE
        JUMP_IF_FALSE_NO_POP 21
        LOAD_FAST 1
        IS_TRUE
        JUMP_IF_TRUE_NO_POP 19
        LOAD_FAST 2
        IS_TRUE
        ROT_AND_DISCARD
     19 IS_TRUE
        ROT_AND_DISCARD
     21 DISCARD_TOP
        LOAD_NULL
        RETURN
        """)

    def test_inplace_add(self):
        self.check_compile("""
        $a += 2;
        """, """
        LOAD_CONST 0
        LOAD_FAST 0
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
        global $a;
        """, """
        LOAD_VAR_NAME 0
        DECLARE_GLOBAL 1
        RETURN_NULL
        """)

    def test_constant(self):
        self.check_compile("""
        $x = c;
        """, """
        LOAD_VAR_NAME 0
        LOAD_VAR
        LOAD_NAMED_CONSTANT 0
        STORE
        DISCARD_TOP
        RETURN_NULL
        """)

    def test_dowhile(self):
        self.check_compile("""
        do { 1; } while (2);
        """, """
        LOAD_CONST 0
        DISCARD_TOP
        LOAD_CONST 1
        JUMP_BACK_IF_TRUE 0
        RETURN_NULL
        """)

    def test_reference(self):
        self.check_compile("""
        &$a;
        """, """
        LOAD_VAR_NAME 0
        LOAD_VAR
        REFERENCE
        DISCARD_TOP
        RETURN_NULL
        """)
        XXX # more cases!

    def test_break(self):
        self.check_compile("""
        while (1) {
           break;
        }
        """, """
        LOAD_CONST 0
        JUMP_IF_FALSE 12
        JUMP_FORWARD 12
        JUMP_BACKWARD 0
        RETURN_NULL
        """)

    def test_continue(self):
        self.check_compile("""
        while (1) {
           continue;
        }
        """, """
        LOAD_CONST 0
        JUMP_IF_FALSE 12
        JUMP_BACKWARD 0
        JUMP_BACKWARD 0
        RETURN_NULL
        """)

    def test_break_for(self):
        self.check_compile("""
        for(1;1;1) {
           break;
        }
        """, """
        LOAD_CONST 0
        DISCARD_TOP
        LOAD_CONST 0
        JUMP_IF_FALSE 20
        JUMP_FORWARD 20
        LOAD_CONST 0
        DISCARD_TOP
        JUMP_BACKWARD 4
        RETURN_NULL
        """)

    def test_break_do_while(self):
        self.check_compile("""
        do {
           break;
        } while(1);
        """, """
        JUMP_FORWARD 9
        LOAD_CONST 0
        JUMP_BACK_IF_TRUE 0
        RETURN_NULL
        """)

    def test_if_expr(self):
        self.check_compile("""
        $a = 1 ? 0 : 1;
        """, """
        LOAD_VAR_NAME 0
        LOAD_VAR
        LOAD_CONST 0
        JUMP_IF_FALSE 16
        LOAD_CONST 1
        JUMP_FORWARD 19
        LOAD_CONST 0
        STORE
        DISCARD_TOP
        RETURN_NULL
        """)

    def test_iterator_1(self):
        self.check_compile("""
        foreach ($a as $b) {$b;}
        """, """
        LOAD_VAR_NAME 0
        LOAD_VAR
        CREATE_ITER
        LOAD_VAR_NAME 1
        LOAD_VAR
        NEXT_VALUE_ITER 20
        LOAD_VAR_NAME 1
        LOAD_VAR
        DISCARD_TOP
        JUMP_BACK_IF_NOT_DONE 5
        RETURN_NULL
        """)

    def test_iterator_2(self):
        self.check_compile("""
        foreach ($a as $b => $c) {$b;}
        """, """
        LOAD_VAR_NAME 0
        LOAD_VAR
        CREATE_ITER
        LOAD_VAR_NAME 1
        LOAD_VAR
        LOAD_VAR_NAME 2
        LOAD_VAR
        NEXT_ITEM_ITER 24
        LOAD_VAR_NAME 1
        LOAD_VAR
        DISCARD_TOP
        JUMP_BACK_IF_NOT_DONE 5
        RETURN_NULL
        """)

    def test_array_cast(self):
        self.check_compile("""
        (array)3;
        """, """
        LOAD_CONST 0
        CAST_ARRAY
        DISCARD_TOP
        RETURN_NULL
        """)

    def test_dynamic_call(self):
        self.check_compile("""
        $a = 'func';
        $a(3, 4);
        """, """
        LOAD_VAR_NAME 0
        LOAD_VAR
        LOAD_NAME 0
        STORE
        DISCARD_TOP
        LOAD_CONST 0
        LOAD_CONST 1
        LOAD_VAR_NAME 0
        LOAD_VAR
        CALL 2
        DISCARD_TOP
        RETURN_NULL
        """)

    def test_lineno_mapping(self):
        bc = self.check_compile("""
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
        LOAD_VAR_NAME 0
        LOAD_VAR
        MAKE_HASH 1
        DISCARD_TOP
        RETURN_NULL
        """)
        assert bc.stackdepth == 2

    def test_make_hash_const(self):
        bc = self.check_compile("""
        array(1=>2, 5=>null, 6=>true, 4=>3.5, 'abc'=>'def',
              'h'=>false);
        """, """
        LOAD_MUTABLE_CONST 0
        DISCARD_TOP
        RETURN_NULL
        """)
        assert bc.stackdepth == 1
        arr = bc.consts[0]
        space = self.space
        assert arr.tp == space.tp_array
        assert space.str_w(space.getitem(arr, space.newstrconst('abc'))) == "def"

    def test_extra_offset(self):
        bc = self.check_compile("""
        1;
        2;
        """, """
        LOAD_CONST 0
        DISCARD_TOP
        LOAD_CONST 1
        DISCARD_TOP
        RETURN_NULL
        """)
        assert bc.bc_mapping == [1, 1, 1, 1, 2, 2, 2, 2, 2]

    def test_declare_static(self):
        self.check_compile("""
        static $a;
        """, """
        LOAD_VAR_NAME 0
        DECLARE_STATIC 1
        RETURN_NULL
        """)

    def test_initialized_static(self):
        bc = self.check_compile("""
        static $a = 0;
        """, """
        LOAD_VAR_NAME 0
        DECLARE_STATIC 1
        RETURN_NULL
        """)
        assert bc.static_vars.keys() == ['a']

    def test_print_exprs(self):
        bc = self.check_compile("$x = 3;", """
        LOAD_VAR_NAME 0
        LOAD_VAR
        LOAD_CONST 0
        STORE
        LOAD_NAME 0
        ECHO 2
        RETURN_NULL
        """, print_exprs=True)
        c = bc.consts[0]
        assert isinstance(c, W_IntObject)
        assert c.intval == 3
        assert bc.stackdepth == 2
