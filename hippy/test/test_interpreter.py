
import py
from hippy.interpreter import Interpreter, Frame
from hippy.objspace import ObjSpace
from hippy.objects.base import W_Root
from hippy.objects import strobject
from hippy.sourceparser import parse
from hippy.astcompiler import compile_ast
from hippy.error import InterpreterError
from hippy.conftest import option
from hippy.test.directrunner import run_source

class MockInterpreter(Interpreter):
    """ Like the interpreter, but captures stdout
    """
    def __init__(self, space):
        Interpreter.__init__(self, space)
        self.output = []
    
    def echo(self, space, w):
        assert isinstance(w, W_Root)
        self.output.append(w)

class BaseTestInterpreter(object):
    def run(self, source):
        if option.runappdirect:
            return run_source(self.space, source)
        interp = MockInterpreter(self.space)
        self.space.ec.writestr = interp.output.append
        bc = compile_ast(parse(source), self.space)
        old = strobject._new_mutable_string
        try:
            self.new_mutable_strings = []
            strobject._new_mutable_string = self._new_mutable_string
            interp.interpret(self.space, Frame(self.space, bc), bc)
        finally:
            strobject._new_mutable_string = old
        return interp.output

    @property
    def space(self):
        try:
            return self._space
        except AttributeError:
            self._space = ObjSpace()
            return self._space

    def _new_mutable_string(self, chars, flag):
        self.new_mutable_strings.append((''.join(chars), flag))

    def echo(self, source):
        output = self.run("echo %s;" % (source,))
        assert len(output) == 1
        return self.space.str_w(output[0])

    def is_array(self, w_obj, lst_w):
        assert w_obj.tp == self.space.tp_array
        assert self.space.arraylen(w_obj) == len(lst_w)
        for i in range(len(lst_w)):
            w_item = self.space.getitem(w_obj, self.space.newint(i))
            w_expected = lst_w[i]
            assert self.space.is_w(w_item, w_expected)
        return True

class TestInterpreter(BaseTestInterpreter):

    def test_simple(self):
        output = self.run("$x = 3; echo $x;")
        assert self.space.int_w(output[0]) == 3

    def test_add(self):
        output = self.run("$x = 3; echo $x + 10;")
        assert self.space.int_w(output[0]) == 13

    def test_sub(self):
        output = self.run("$x = 3; echo $x - 10;")
        assert self.space.int_w(output[0]) == -7

    def test_mul(self):
        output = self.run("$x = 3; echo $x * 10;")
        assert self.space.int_w(output[0]) == 30

    def test_float(self):
        output = self.run("echo 3.5;")
        assert self.space.float_w(output[0]) == 3.5

    def test_float_add(self):
        output = self.run("$x = .2; echo 3.5 + $x;")
        assert self.space.float_w(output[0]) == 3.7

    def test_floats_ints(self):
        output = self.run("$x = 2; echo 2.3 + $x;")
        assert self.space.float_w(output[0]) == 4.3
        output = self.run("$x = 2; echo $x + 2.3;")
        assert self.space.float_w(output[0]) == 4.3
        output = self.run("$x = 2; echo $x/3;")
        assert self.space.float_w(output[0]) == float(2)/3

    def test_plusplus(self):
        output = self.run("$x = 1; echo $x++; echo ++$x;")
        assert self.space.int_w(output[0]) == 1;
        assert self.space.int_w(output[1]) == 3;

    def test_minusminus(self):
        output = self.run("$x = 1; echo $x--; echo --$x;")
        assert self.space.int_w(output[0]) == 1;
        assert self.space.int_w(output[1]) == -1;

    def test_plusplus_2(self):
        output = self.run("$x = 9; echo $x * (++$x);")
        assert self.space.int_w(output[0]) == 100
        output = self.run("$x = 9; echo ($x + 0) * (++$x);")
        assert self.space.int_w(output[0]) == 90
        output = self.run("$x = 9; echo (++$x) * $x;")
        assert self.space.int_w(output[0]) == 100
        output = self.run("$x = 9; echo (++$x) * ($x + 0);")
        assert self.space.int_w(output[0]) == 100
        output = self.run("$x = 9; echo $x * ($x++);")
        assert self.space.int_w(output[0]) == 90
        output = self.run("$x = 9; echo ($x + 0) * ($x++);")
        assert self.space.int_w(output[0]) == 81
        output = self.run("$x = 9; echo ($x++) * $x;")
        assert self.space.int_w(output[0]) == 90
        output = self.run("$x = 9; echo ($x++) * ($x + 0);")
        assert self.space.int_w(output[0]) == 90
        output = self.run("$x = 9; echo (++$x) * (++$x);")
        assert self.space.int_w(output[0]) == 110
        output = self.run("$x = 9; echo (++$x) * ($x++);")
        assert self.space.int_w(output[0]) == 100
        output = self.run("$x = 9; echo ($x++) * (++$x);")
        assert self.space.int_w(output[0]) == 99
        output = self.run("$x = 9; echo ($x++) * ($x++);")
        assert self.space.int_w(output[0]) == 90

    def test_comparison(self):
        output = self.run("""$x = 3; echo $x > 1; echo $x < 1; echo $x == 3;
        echo $x >= 3; echo $x <= 3; echo $x != 8; echo $x == 8; echo $x != 3;
        """)
        assert [i.boolval for i in output] == [True, False, True, True, True,
                                               True, False, False]

    def test_unary(self):
        output = self.run("$x = 3; echo +$x; echo -$x;")
        assert [i.intval for i in output] == [3, -3]
        output = self.run("$x = 3.5; echo +$x; echo -$x;")
        assert [i.floatval for i in output] == [3.5, -3.5]

    def test_if(self):
        output = self.run("""
        $x = 3;
        if ($x)
           $x = 18;
        else
           $x = 13;
        echo $x;
        """)
        assert self.space.int_w(output[0]) == int(18)

    def test_while(self):
        output = self.run("""
        $i = 0;
        while ($i < 3)
          $i++;
        echo $i;
        """)
        assert self.space.int_w(output[0]) == 3

    def test_shifts(self):
        output = self.run("""
        echo 1 << 31, 15 >> 1;
        """)
        assert [self.space.int_w(i) for i in output] == [1<<31, 15>>1]

    def test_assign_inplace(self):
        output = self.run("""
        $x = 15;
        echo $x += 3;
        echo $x -= 17;
        echo $x *= 2;
        echo $x /= 3;
        echo $x;
        """)
        assert [self.space.int_w(i) for i in output[:-2]] == [18, 1, 2]
        assert [self.space.float_w(i) for i in output[-2:]] == [2./3, 2./3]

    def test_simple_assignment(self):
        output = self.run("""
        $y = 3;
        $x = 0;
        echo $x; echo $y;
        """)
        assert [self.space.int_w(i) for i in output] == [0, 3]

    def test_for(self):
        output = self.run("""
        $y = 3;
        for ($x = 0; $x < 10; $x++) { $y++; }
        echo $x; echo $y;
        """)
        assert [self.space.int_w(i) for i in output] == [10, 13]

    def test_aliasing(self):
        output = self.run("""
        $x = 3;
        $y = $x;
        $y++;
        echo $x; echo $y;
        """)
        assert [self.space.int_w(i) for i in output] == [3, 4]

    def test_echo_multielement(self):
        output = self.run("""
        echo 1, 2, 3;
        """)
        assert [self.space.int_w(i) for i in output] == [1, 2, 3]

    def test_string_ops_basic(self):
        output = self.run('''
        $a = "abc";
        echo $a;
        ''')
        assert self.space.str_w(output[0]) == 'abc'

    def test_string_ops(self):
        output = self.run('''
        $a = "abc";
        echo $a[0];
        $b = $a;
        $c = "abc";
        $a[1] = "d";
        echo $a, $b, $c;
        ''')
        assert [self.space.str_w(i) for i in output] == [
            'a', 'adc', 'abc', 'abc']

    def test_string_setitem_result(self):
        output = self.run('''
        $a = "abc";
        $b = $a[1] = "X";
        echo $a, $b;
        ''')
        assert [self.space.str_w(i) for i in output] == [
            'aXc', 'X']

    def test_string_coerce(self):
        output = self.run('''
        $a = "10 abc";
        echo $a + 1, $a + 1.5, "1.5" + 1, "1.5" + 1.2;
        ''')
        assert self.space.int_w(output[0]) == 11
        assert self.space.float_w(output[1]) == 11.5
        assert self.space.float_w(output[2]) == 2.5
        assert self.space.float_w(output[3]) == 2.7

    def test_mixed_string_ops(self):
        output = self.run('''
        $a = "abc";
        $a[0] = 12;
        echo $a;
        $a++;
        echo $a;
        ''')
        assert [self.space.str_w(i) for i in output] == ["1bc", "1bd"];

    def test_string_copies(self):
        output = self.run('''
        $a = "abc";
        $b = $a;
        $c = $b;
        $c[0] = 1;
        $a[0] = 5;
        echo $b[0], $a, $b, $c;
        ''')
        assert [self.space.str_w(i) for i in output] == [
            'a', '5bc', 'abc', '1bc']
        assert self.new_mutable_strings == [("abc", 1), ("abc", 1)]

    def test_string_copies2(self):
        output = self.run('''
        $a = "abc";
        $a[0] = "3";
        $b = $a;
        echo $b[0];
        ''')
        assert [self.space.str_w(i) for i in output] == [
            '3']
        assert self.new_mutable_strings == [("abc", 1)]

    def test_string_copies3(self):
        output = self.run('''
        $a = "abc";
        $a[0] = "3";
        $b = $a;
        $a[0] = "4";
        echo $a, $b;
        ''')
        assert [self.space.str_w(i) for i in output] == [
            '4bc', '3bc']
        assert self.new_mutable_strings == [("abc", 1), ("3bc", 2)]

    def test_string_empty(self):
        output = self.run('''
        $b = "";
        $a = "abc";
        $a[0] = $b;
        echo $a;
        ''')
        assert self.space.str_w(output[0]) == '\x00bc'

    def test_string_concat(self):
        output = self.run('''
        $a = "abc";
        echo $a . "def";
        $a[0] = "1";
        $b = $a;
        echo $a . "def", $a . $b . $a;
        ''')
        assert [self.space.str_w(i) for i in output] == [
            "abcdef", "1bcdef", "1bc1bc1bc"]

    def test_strlen(self):
        output = self.run('''
        $a = "abc" . "def";
        echo strlen($a), strlen(12);
        ''')
        assert [self.space.int_w(i) for i in output] == [6, 2]

    def test_plusplus_comp(self):
        output = self.run('''
        $n = 3;
        while ($n-- > 0) {
           echo $n;
        }
        ''')
        assert [self.space.int_w(i) for i in output] == [2, 1, 0]

    def test_declare_function_call(self):
        py.test.skip("XXX REDO")
        output = self.run('''
        function f($a, $b) {
           return $a + $b;
        }
        echo f(1, 2);
        ''')
        assert self.space.int_w(output[0]) == 3

    def test_declare_function_call_2(self):
        py.test.skip("XXX REDO")
        output = self.run('''
        function f($a) {
           return $a + 1;
        }
        echo f(1);
        ''')
        assert self.space.int_w(output[0]) == 2

    def test_declare_inside(self):
        py.test.skip("XXX REDO")
        py.test.raises(InterpreterError, self.run, '''
        function f() {
           function g() {
              return 1;
           }
        }
        echo g();
        ''')
        output = self.run('''
                function f() {
           function g() {
              return 1;
           }
        }
        f();
        echo g();
        ''')
        assert self.space.int_w(output[0]) == 1

    def test_recursion(self):
        py.test.skip("XXX REDO")
        output = self.run('''
        function f($n) {
           if ($n == 0)
              return 0;
           return $n + f($n - 1);
        }
        echo f(5);
        ''')
        assert self.space.int_w(output[0]) == 5 + 4 + 3 + 2 + 1

    def test_and_or(self):
        py.test.skip("XXX REDO")
        output = self.run('''
        echo 1 && 0 || 3;
        echo 1 && 2;
        echo 0 && 1;
        echo 1 && 0;
        echo 1 && 0 || "";
        ''')
        for i, expected in enumerate([True, True, False, False, False]):
            if expected:
                assert self.space.is_true(output[i])
            else:
                assert not self.space.is_true(output[i])

    def test_negation(self):
        output = self.run('''
        echo !15,!!15;
        ''')
        assert [i.boolval for i in output] == [False, True]

    def test_references(self):
        output = self.run('''
        $a = 3;      // [Int(3), None]
        $b = &$a;    // [r, r]  with r == Ref(Int(3),c=2)
        $b = 5;      //                       Int(5)
        echo $b, $a;
        ''')
        assert [self.space.int_w(i) for i in output] == [5, 5]

    def test_references_plusplus_1(self):
        output = self.run("$x = 1; $y =& $x; echo ++$x; echo ++$x; echo $y;")
        assert self.space.int_w(output[0]) == 2;
        assert self.space.int_w(output[1]) == 3;
        assert self.space.int_w(output[2]) == 3;

    def test_references_plusplus_2(self):
        output = self.run("$x = 1; $y =& $x; echo $x++; echo $x++; echo $y;")
        assert self.space.int_w(output[0]) == 1;
        assert self.space.int_w(output[1]) == 2;
        assert self.space.int_w(output[2]) == 3;

    def test_references_assign(self):
        output = self.run("""
        $x = 15;
        $y =& $x;
        echo $x = $x + 3;
        echo $y;
        """)
        assert self.space.int_w(output[0]) == 18
        assert self.space.int_w(output[1]) == 18

    def test_references_assign_inplace(self):
        output = self.run("""
        $x = 15;
        $y =& $x;
        echo $x += 3;
        echo $y;
        """)
        assert self.space.int_w(output[0]) == 18
        assert self.space.int_w(output[1]) == 18

    def test_references_2(self):
        py.test.skip("XXX FIXME")
        output = self.run('''
        function f() {
        $a = 3;
        $b = &$a;
        $b = 5;
        echo $b, $a;
        }
        f();
        ''')
        assert [self.space.int_w(i) for i in output] == [5, 5]

    def test_references_3(self):
        py.test.skip("XXX FIXME")
        output = self.run('''
        $a = 5;         // [Int(5), None]
        $x = array();   // [Int(5), Array([],c=1)]
        $x[] = &$a;     // [r, Array([r],c=1)],  r == Ref(Int(5),c=2)
        $x[0] = 3;
        echo $a;
        ''')
        assert [self.space.int_w(i) for i in output] == [3]

    def test_references_4(self):
        output = self.run('''
        $a = 5;
        $x = array(0);
        $x[0] = &$a;
        $x[0] = 3;
        echo $a;
        ''')
        assert [self.space.int_w(i) for i in output] == [3]

    def test_references_5(self):
        py.test.skip("XXX FIXME")
        output = self.run('''
        function f($x) {
           $x = 3;
        }
        $a = 5;
        f(&$a);
        echo $a;
        ''')
        assert [self.space.int_w(i) for i in output] == [3]

    def test_references_6(self):
        py.test.skip("XXX FIXME")
        output = self.run('''
        function f() {
           global $x;
           $x = 3;
        }
        $a = 5;
        $x = &$a;
        f();
        echo $a;
        ''')
        assert [self.space.int_w(i) for i in output] == [3]

    def test_references_7(self):
        py.test.skip("XXX FIXME")
        output = self.run('''
        function foo1(&$a) {
            $a[1] = & $a[0];
            return 5;
        }
        $a = array(-5, 0);
        $a[0] = foo1($a);
        echo $a[1];
        ''')
        assert [self.space.int_w(i) for i in output] == [5]

    def test_references_function(self):
        py.test.skip("XXX FIXME")
        output = self.run('''
        function f(&$a) {
           $a = 3;
        }
        $a = 5;
        f($a);
        echo $a;
        ''')
        assert [self.space.int_w(i) for i in output] == [3]

    def test_references_function_2(self):
        py.test.skip("XXX FIXME")
        output = self.run('''
        function f(&$a, $b) {
           $a[0] = 3;
           $b[0] = 4;
        }
        $a = array(15);
        $b = array(20);
        f($a, $b);
        echo $a[0], $b[0];
        ''')
        assert [self.space.int_w(i) for i in output] == [3, 20]

    def test_references_function_3(self):
        py.test.skip("XXX FIXME")
        output = self.run('''
        function foo(&$x) { global $a; $c=42; $a[10]=&$c; $y=$x; return $y; }
        $a = array(1,2,3,4,5,6,7,8,9,10,11);
        echo foo($a[10]);
        echo $a[10];
        ''')
        assert self.space.int_w(output[0]) == 11
        assert self.space.int_w(output[1]) == 42

    def test_dense_array_not_from_0(self):
        py.test.skip("XXX REDO")
        output = self.run('''
        $a = array();
        $a[10] = 5;
        echo $a[10];
        ''')
        assert self.space.int_w(output[0]) == 5

    def test_plusplus_on_array(self):
        py.test.skip("XXX REDO")
        output = self.run('''
        $a = array(10, 20, 30);
        echo $a[1]++;
        echo ++$a[2];
        echo $a[0];
        echo $a[1];
        echo $a[2];
        ''')
        assert [self.space.int_w(o) for o in output] == [20, 31, 10, 21, 31]

    def test_array_append(self):
        output = self.run('''
        $a = array();
        $b = $a[] = 42;
        echo $a, $b;
        ''')
        assert self.is_array(output[0], [self.space.newint(42)])
        assert self.space.is_w(output[1], self.space.newint(42))

    def test_array_obscure1(self):
        output = self.run('''
        $a = array(10);
        echo $a[0] * ($a[0]=5);
        ''')
        assert self.space.is_w(output[0], self.space.newint(50))

    def test_array_obscure1_2(self):
        output = self.run('''
        $a = array(10);
        $b = 5;
        echo $a[0] * ($a[0]=&$b);
        ''')
        assert self.space.is_w(output[0], self.space.newint(50))

    def test_evaluation_order_int(self):
        # same test as above, but using $v instead of $a[0], gives
        # different results
        output = self.run('''
        $v = 10;
        echo $v * ($v=5);
        ''')
        assert self.space.is_w(output[0], self.space.newint(25))

    def test_reference_array_obscure0(self):
        output = self.run('''
        $a = array(10);
        $b = 10;
        $a[0] = &$b;
        echo $a[0] * ($a[0]=5);
        ''')
        assert self.space.is_w(output[0], self.space.newint(25))

    def test_reference_array_obscure1(self):
        py.test.skip("XXX fix me")
        # just like test_array_obscure1, but because $a[0] is a reference,
        # the assignment $a[0]=5 really changes it in-place and then the
        # load of the value of the left-hand side of the '*' returns the
        # new value
        output = self.run('''
        $a = array(10);
        $a[0] = &$a[0];
        echo $a[0] * ($a[0]=5);
        ''')
        assert self.space.is_w(output[0], self.space.newint(25))

    def test_reference_array_obscure2(self):
        py.test.skip("XXX fix me")
        output = self.run('''
        $v = 10;
        $a = array(&$v);
        echo $a[0] * ($a[0] = 5);
        ''')
        assert self.space.is_w(output[0], self.space.newint(25))
        output = self.run('''
        $v = 10;
        $a = array(&$v);
        $v = &$a;        // reference goes away
        echo $a[0] * ($a[0] = 5);
        ''')
        assert self.space.is_w(output[0], self.space.newint(50))

    def test_reference_array_obscure3(self):
        py.test.skip("XXX fix me")
        # no no, this test really makes "sense" in the PHP world,
        # with enough levels of quotes around "sense"
        output = self.run('''
        $v = 10;
        $a = array(&$v);
        $v = &$a;
        echo $a[0] * ($a[0] = 5);   // 50
        $v = 10;
        $a = array(&$v);
        $v = &$a;
        echo $a[0] * ($a[0] = 5);   // 25
        echo $a;                    // 5
        ''')
        assert self.space.is_w(output[0], self.space.newint(50))
        assert self.space.is_w(output[1], self.space.newint(25))
        assert self.space.is_w(output[2], self.space.newint(5))

    def test_array_of_array(self):
        output = self.run('''
        $a = array();
        $b = array($a);
        $b[0][] = 3;
        echo !$a, $b[0][0];
        ''')
        assert self.space.is_w(output[0], self.space.newbool(True))
        assert self.space.is_w(output[1], self.space.newint(3))

    def test_inplace_concat(self):
        py.test.skip("XXX REDO")
        output = self.run('''
        $a = "x";
        $a .= "y";
        echo $a;
        ''')
        assert self.space.str_w(output[0]) == "xy"

    def test_function_var_unused(self):
        py.test.skip("XXX REDO")
        self.run('''
        function f($a) {}
        f(3);
        ''')
        # this used to explode

    def test_inplace_str_concat(self):
        py.test.skip("XXX REDO")
        output = self.run('''
        $a = "abc";
        $b = $a;
        $b[0] = "x";
        $c = $a . $a;
        $d = $a;
        $e = $c;
        $e .= "0";
        $d .= "0";
        $c .= "0";
        $b .= "0";
        $a .= "0";
        echo $a, $b, $c, $d, $e;
        ''')
        assert [self.space.str_w(i) for i in output] == ["abc0", "xbc0",
                                                         "abcabc0", "abc0",
                                                         "abcabc0"]

    def test_if_expr(self):
        output = self.run('''
        $a = 1 ? 3 : 0;
        $b = 0 ? 5 : 7;
        echo $a, $b;
        ''')
        assert [self.space.int_w(i) for i in output] == [3, 7]


    def test_globals_locals(self):
        py.test.skip("XXX REDO")
        output = self.run('''
        function f() {
            $x = 3;
            echo $x;
            global $x;
            echo $x;
            $x = 5;
        }
        $x = 4;
        echo $x;
        f();
        echo $x;
        ''')
        assert [self.space.int_w(i) for i in output] == [4, 3, 4, 5]

    def test_const(self):
        py.test.skip("XXX REDO")
        output = self.run("""
        define('x', 13);
        echo x;
        """)
        assert self.space.int_w(output[0]) == 13

    def test_const_2(self):
        py.test.skip("XXX REDO")
        output = self.run("""
        function f() {
            define('x', 13);
        }
        f();
        echo x;
        """)
        assert self.space.int_w(output[0]) == 13

    def test_mod(self):
        output = self.run('''
        echo 15 % 2, 14 % 2;
        ''') # XXX negative values
        assert [self.space.int_w(i) for i in output] == [1, 0]

    def test_string_interpolation_newline_var(self):
        py.test.skip("XXX REDO")
        output = self.run('''
        $s = "\\n";
        echo $s;
        echo "$s \$s";
        echo "\\t";
        ''')
        assert self.space.str_w(output[0]) == '\n'
        assert self.space.str_w(output[1]) == '\n $s'
        assert self.space.str_w(output[2]) == '\t'

    def test_prebuilt_consts(self):
        py.test.skip("XXX REDO")
        output = self.run('''
        echo TRUE, FALSE, NULL;
        ''')
        assert [self.space.is_true(i) for i in output] == [True, False, False]

    def test_do_while(self):
        py.test.skip("XXX REDO")
        output = self.run('''
        $x = 0;
        do { $x++; } while ($x < 10);
        echo $x;
        ''')
        assert self.space.int_w(output[0]) == 10

    def test_inplace_shift(self):
        output = self.run('''
        $x = 1;
        $x <<= 2;
        echo $x;
        $x >>= 1;
        echo $x;
        ''')
        assert [self.space.int_w(i) for i in output] == [1<<2, 1<<1]

    def test_mixed_eq(self):
        py.test.skip("XXX REDO")
        output = self.run('''
        echo "abc" == "abc", "abc" != "abc";
        echo "abc" == "abcc", "abc" != "abcc";
        echo 1 == "1bc", "1bc" == 1;
        echo 1.2 == 1, 1 == 1.2, 1 == 1.0, 1.0 == 1;
        echo NULL == NULL, NULL == 0, 1 == NULL;
        ''')
        assert [self.space.is_true(i) for i in output] == [
            True, False, False, True, True, True, False, False, True, True,
            True, True, False]

    def test_mixed_str_eq(self):
        py.test.skip("XXX REDO")
        output = self.run('''
        $a = "abc";
        $b = $a;
        $b[0] = "a";
        $c = $a + "";
        $d = $a;
        echo $a == $a, $b == $b, $c == $c, $d == $d;
        ''')
        assert [self.space.is_true(i) for i in output] == [
            True, True, True, True]

    def test_global_in_global(self):
        py.test.skip("XXX REDO")
        self.run('''
        global $x;
        ''')
        # assert did not crash

    def test_invariant_global_namespace(self):
        py.test.skip("XXX REDO")
        output = self.run('''
        echo TruE;
        ''')
        assert self.space.is_true(output[0])

    def test_triple_eq(self):
        py.test.skip("XXX REDO")
        output = self.run('''
        echo 1.0 === 1;
        echo 1 === 1;
        echo 1 === true;
        ''')
        assert not self.space.is_true(output[0])
        assert self.space.is_true(output[1])
        assert not self.space.is_true(output[2])

    def test_triple_ne(self):
        py.test.skip("XXX REDO")
        output = self.run('''
        echo 1.0 !== 1;
        echo 1 !== 1;
        echo 1 !== true;
        ''')
        assert self.space.is_true(output[0])
        assert not self.space.is_true(output[1])
        assert self.space.is_true(output[2])

    def test_dynamic_call(self):
        py.test.skip("XXX REDO")
        output = self.run('''
        function f($a, $b) {
           return $a + $b;
        }
        $c = "f";
        echo $c(1, 2);
        ''')
        assert self.space.int_w(output[0]) == 3

    def test_assignment_in_and(self):
        py.test.skip("XXX REDO")
        output = self.run('''
        $a = 3;
        $a && $b = "x";
        echo $b;
        ''')
        assert self.space.str_w(output[0]) == 'x'

    def test_global_no_local(self):
        py.test.skip("XXX REDO")
        output = self.run('''
        function f() {
           global $aa;
           $aa = 3;
           return $aa;
        }
        echo f();
        ''')
        assert self.space.int_w(output[0]) == 3

    def test_global_store(self):
        py.test.skip("XXX REDO")
        output = self.run('''
        function f() {
           global $a;
           $b = $a;
           echo $b;
        }
        $a = 3;
        f();
        ''')
        assert self.space.int_w(output[0]) == 3

    def test_superglobals(self):
        py.test.skip("XXX REDO")
        output = self.run('''
        function f() {
           return $GLOBALS["a"];
        }
        $a = 3;
        echo f();
        ''')
        assert self.space.int_w(output[0]) == 3

    def test_globals_indirectly(self):
        py.test.skip("XXX REDO")
        # Note that this works in PHP 5.3.5 but according to the docs it
        # should not work either.
        output = self.run('''
        function f() {
           $a = "GLO";
           return ${$a . "BALS"};
        }
        $a = 3;
        $g = f();
        echo $g["a"];
        ''')
        assert self.space.int_w(output[0]) == 3

    def test_null_eq(self):
        py.test.skip("XXX REDO")
        output = self.run('''
        $a = "x";
        echo $a == null, null == $a, null == null;
        echo $a != null, null != $a, null != null;
        ''')
        assert [i.boolval for i in output] == [False, False, True,
                                               True, True, False]

    def test_hash_of_a_copy_of_concat(self):
        py.test.skip("XXX REDO")
        output = self.run('''
        $a = "x";
        $b = $a . $a;
        $c = $b;
        $x = array();
        $x[$c] = 3;
        echo $x["xx"];
        ''')
        assert self.space.int_w(output[0]) == 3

    def test_reference_to_a_reference(self):
        py.test.skip("XXX fix me")
        output = self.run('''
        function f(&$x) {
            $x = 3;
        }
        function g() {
            $x = 2;
            f($x);
            return $x;
        }
        echo g();
        ''')
        assert self.space.int_w(output[0]) == 3

    def test_function_returns_reference_1(self):
        py.test.skip("XXX fix me")
        output = self.run('''
        function &f(&$x) {
            $y = &$x[0];
            return $y;
        }
        $a = array(array(5));
        $b = &f($a);
        $b[0] = 6;
        echo $a[0][0];
        ''')
        assert self.space.int_w(output[0]) == 6

    def test_function_returns_reference_2(self):
        py.test.skip("XXX fix me")
        output = self.run('''
        function &f(&$x) {
            $y = &$x[0];
            return $y;
        }
        $a = array(array(5));
        $b = f($a);
        $b[0] = 6;
        echo $a[0][0];
        ''')               # missing '&' in front of the call to f()
        assert self.space.int_w(output[0]) == 5

    def test_function_returns_reference_3(self):
        py.test.skip("XXX FIXME")

        output = self.run('''
        function f(&$x) {
            $y = &$x[0];
            return $y;
        }
        $a = array(array(5));
        $b = &f($a);
        $b[0] = 6;
        echo $a[0][0];
        ''')               # missing '&' in front of the function declaration
        assert self.space.int_w(output[0]) == 5

    def test_function_returns_reference_4(self):
        py.test.skip("XXX fix me")
        output = self.run('''
        function &f(&$x) {
            $y = &$x[0];
            return $y;
        }
        function g(&$x) {
            $x[0] = 6;
        }
        $a = array(array(5));
        g(f($a));
        echo $a[0][0];
        ''')               # passing a reference directly to another call
        assert self.space.int_w(output[0]) == 6

    def test_function_returns_reference_5(self):
        py.test.skip("XXX fix me")
        output = self.run('''
        function &f(&$x) {
            $y = &$x[0];
            return $y;
        }
        function g($x) {
            $x[0] = 6;
        }
        $a = array(array(5));
        g(f($a));
        echo $a[0][0];
        ''')               # missing '&' in the argument in g()
        assert self.space.int_w(output[0]) == 5

    def test_function_returns_reference_5bis(self):
        py.test.skip("XXX fix me")
        output = self.run('''
        function f(&$x) {
            $y = &$x[0];
            return $y;
        }
        function g(&$x) {
            $x[0] = 6;
        }
        $a = array(array(5));
        g(f($a));
        echo $a[0][0];
        ''')               # missing '&' in the return from f()
        assert self.space.int_w(output[0]) == 5

    def test_function_returns_reference_6(self):
        py.test.skip("XXX fix me")
        output = self.run('''
        function &f(&$x) {
            $y = &$x[0];
            return $y;
        }
        $a = array(array(5));
        $b = array(f($a));
        $b[0] = "foo";
        echo $a[0][0];
        ''')
        assert self.space.int_w(output[0]) == 5

    def test_function_returns_reference_7(self):
        py.test.skip("XXX fix me")
        output = self.run('''
        function &f(&$x) {
            $y = &$x[0];
            return $y;
        }
        function makearray(&$a) {
            return array(&$a);
        }
        $a = array(array(5));
        $b = makearray(f($a));
        $b[0][0] = 6;
        echo $a[0][0];
        ''')
        assert self.space.int_w(output[0]) == 6

    def test_function_mixed_case(self):
        py.test.skip("XXX REDO")
        output = self.run('''
        function F(){
            return 3;
        }
        echo f();
        ''')
        assert self.space.int_w(output[0]) == 3

    def test_global_2(self):
        py.test.skip("XXX REDO")
        output = self.run('''
        function f() {
          global $x;
          $x = 3;
        }
        function g() {
          global $x;
          echo $x;
        }
        g(); f(); g();
        ''')
        assert self.space.w_Null is output[0]
        assert self.space.int_w(output[1]) == 3

    def test_static_var(self):
        py.test.skip("XXX REDO")
        output = self.run('''
        function f() {
           $a = 15;
           static $a = 0;
           $a++;
           echo $a;
        }
        f(); f(); f(); f();
        ''')
        assert [self.space.int_w(i) for i in output] == [1, 2, 3, 4]

    def test_default_args(self):
        py.test.skip("XXX REDO")
        output = self.run('''
        function f($n = 10) {
           echo $n;
        }
        f();
        f(5);
        ''')
        assert [self.space.int_w(i) for i in output] == [10, 5]

    def test_bit_or(self):
        output = self.run('''
        echo 1 | 2;
        ''')
        assert self.space.int_w(output[0]) == 3

    def test_evaluation_order_str(self):
        output = self.run('''
        $A = "xx"; $a = 0;
        $A[$a] = ++$a;        // changes $A[1]
        echo $A;
        ''')
        assert self.space.str_w(output[0]) == "x1"

        output = self.run('''
        $B = "xx"; $b = 0;
        $B[++$b] = ++$b;      // changes $B[1]
        echo $B;
        ''')
        assert self.space.str_w(output[0]) == "x2"

        output = self.run('''
        $C = "xx"; $c = 0;
        $C[$c+=0] = ++$c;     // changes $C[0]
        echo $C;
        ''')
        assert self.space.str_w(output[0]) == "1x"

        output = self.run('''
        $D = "xxx"; $d = 0;
        $D[$d+=1] = ++$d;     // changes $D[1]
        echo $D;
        ''')
        assert self.space.str_w(output[0]) == "x2x"

        output = self.run('''
        $E = "xxx"; $e = 0;
        $E[$e=1] = ++$e;      // changes $E[1]
        echo $E;
        ''')
        assert self.space.str_w(output[0]) == "x2x"

        output = self.run('''
        $F = "xxx"; $f = 0; $s = "x";
        $F[$s[0]=$f] = ++$f;      // changes $F[0]
        echo $F;
        ''')
        assert self.space.str_w(output[0]) == "1xx"

    def test_evaluation_order_array(self):
        output = self.run('''
        $A = array(9, 9); $a = 0;
        $A[$a] = ++$a;        // changes $A[1]
        echo $A[0], $A[1];
        ''')
        assert self.space.int_w(output[0]) == 9
        assert self.space.int_w(output[1]) == 1

        output = self.run('''
        $B = array(9, 9); $b = 0;
        $B[++$b] = ++$b;      // changes $B[1]
        echo $B[0], $B[1];
        ''')
        assert self.space.int_w(output[0]) == 9
        assert self.space.int_w(output[1]) == 2

        output = self.run('''
        $C = array(9, 9); $c = 0;
        $C[$c+=0] = ++$c;     // changes $C[0]
        echo $C[0], $C[1];
        ''')
        assert self.space.int_w(output[0]) == 1
        assert self.space.int_w(output[1]) == 9

    def test_store_character(self):
        py.test.skip("XXX FIXME")
        output = self.run('$a="x"; echo gettype($a[0]=5);')
        assert self.space.str_w(output[0]) == "string"
