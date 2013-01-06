
import py, sys
from hippy.interpreter import Interpreter
from hippy.objspace import ObjSpace
from hippy.objects.base import W_Root
from hippy.sourceparser import parse
from hippy.astcompiler import compile_ast
from hippy.conftest import option
from hippy.logger import Logger, FatalError
from hippy.test.directrunner import run_source

class MockLogger(Logger):
    """ Like the logger, but instead of printing, records stuff
    """
    def __init__(self):
        Logger.__init__(self)
        self.msgs = []
        self.tb = []

    def _log_traceback(self, filename, funcname, line, source):
        self.tb.append((filename, funcname, line, source))
    
    def _log(self, level, msg):
        self.msgs.append((level, msg))

class MockInterpreter(Interpreter):
    """ Like the interpreter, but captures stdout
    """
    def __init__(self, space):
        logger = MockLogger()
        Interpreter.__init__(self, space, logger)
        self.output = []
    
    def echo(self, space, w):
        assert isinstance(w, W_Root)
        self.output.append(w.deref())

class BaseTestInterpreter(object):
    interpreter = MockInterpreter
    
    def run(self, source):
        # preparse the source a bit so traceback starts with the
        # correct number of whitespaces
        lines = source.splitlines(True)
        prefix = sys.maxint
        for line in lines:
            stripped = line.lstrip()
            if stripped:
                prefix = min(len(line) - len(stripped), prefix)
        for i, line in enumerate(lines):
            lines[i] = lines[i][prefix:]
        source = "".join(lines)
        if option.runappdirect:
            return self.run_direct(source)
        interp = self.interpreter(self.space)
        self.space.ec.writestr = interp.output.append
        bc = self.compile(source)
        self.interp = interp
        #old = strobject._new_mutable_string
        try:
            #self.new_mutable_strings = []
            #strobject._new_mutable_string = self._new_mutable_string
            interp.run_main(self.space, bc)
        finally:
            pass #strobject._new_mutable_string = old
        return interp.output

    def compile(self, source):
        return compile_ast('<input>', source, parse(source), self.space)

    def run_direct(self, source):
        return run_source(self.space, source)

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
        assert isinstance(source, str)
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
        py.test.skip("XXX redo")
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
        py.test.skip("XXX redo")
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
        py.test.skip("XXX redo")
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
        output = self.run('''
        function f($a, $b) {
           echo $a;
           echo $b;
           return $a + $b;
        }
        echo f(10, 20);
        ''')
        assert self.space.int_w(output[0]) == 10
        assert self.space.int_w(output[1]) == 20
        assert self.space.int_w(output[2]) == 30

    def test_declare_function_call_2(self):
        output = self.run('''
        function f($a) {
           return $a + 1;
        }
        echo f(1);
        ''')
        assert self.space.int_w(output[0]) == 2

    def test_declare_function_call_3(self):
        output = self.run('''
        function f($a) {
           $b = 2;
           return $a + $b;
        }
        $b = 5;
        echo f(10);
        echo $b;
        ''')
        assert [self.space.int_w(i) for i in output] == [12, 5]

    def test_declare_function_call_4(self):
        output = self.run('''
        function f($a, $a, $b) {    // ugh! supported
           echo $a, $b;
        }
        f(10, 20, 30);
        ''')
        assert [self.space.int_w(i) for i in output] == [20, 30]

    def test_declare_inside(self):
        py.test.raises(FatalError, self.run, '''
        function f() {
           function g() {
              return 1;
           }
        }
        echo g();
        ''')
        assert self.interp.logger.msgs == [
            ('FATAL', 'undefined function: g()')]
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

    def test_undeclared_traceback(self):
        py.test.raises(FatalError, self.run, '''\
        function f() {
           g();
        }
        f();
        ''')
        assert self.interp.logger.msgs == [
            ('FATAL', 'undefined function: g()')]
        assert self.interp.logger.tb == [('<input>', '<main>', 4, 'f();'),
                                         ('<input>', 'f', 2, '   g();')]

    def test_recursion(self):
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

    def test_references_left_array_1(self):
        output = self.run('''
        $a = 3;
        $b = array(0);
        $b[0] = & $a;
        $a = 5;
        echo $b[0];
        $b[0] = 7;
        echo $a;
        ''')
        assert [self.space.int_w(i) for i in output] == [5, 7]

    def test_references_left_array_2(self):
        output = self.run('''
        $a = 3;
        $b = array(array(0));
        $b[0][0] = & $a;
        $a = 5;
        echo $b[0][0];
        $b[0][0] = 7;
        echo $a;
        ''')
        assert [self.space.int_w(i) for i in output] == [5, 7]

    def test_references_right_array_1(self):
        output = self.run('''
        $b = array(0);
        $a = & $b[0];
        $a = 15;
        echo $b[0];
        $b[0] = 17;
        echo $a;
        ''')
        assert [self.space.int_w(i) for i in output] == [15, 17]

    def test_references_right_array_2(self):
        output = self.run('''
        $b = array(array(0));
        $a = & $b[0][0];
        $a = 12;
        echo $b[0][0];
        $b[0][0] = 13;
        echo $a;
        ''')
        assert [self.space.int_w(i) for i in output] == [12, 13]

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
        py.test.skip("Removed in PHP 5.4")
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

    def test_store_order_1(self):
        output = self.run('''
        $a = 5;
        $v = 6;
        $a = ($a =& $v);  // we must not read the reference to the leftmost $a
        echo $a;          // before we evaluate the expression ($a =& $v)
        $a = 7;
        echo $v;
        ''')
        assert self.space.int_w(output[0]) == 6
        assert self.space.int_w(output[1]) == 7

    def test_array_store_simple_1(self):
        output = self.run('''
        $v = 5;
        $a = array(&$v);
        $a[0] = 40 + 2;
        echo $v;
        ''')
        assert self.space.int_w(output[0]) == 42

    def test_array_store_simple_2(self):
        output = self.run('''
        $v = 5;
        $a = array(array(&$v));
        $a[0][0] = 40 + 2;
        echo $v;
        ''')
        assert self.space.int_w(output[0]) == 42

    def test_array_store_simple_3(self):
        output = self.run('''
        $c = array(5);
        $a = array(&$c);
        $a[0][0] = 40 + 2;
        echo $c[0];
        ''')
        assert self.space.int_w(output[0]) == 42

    def test_array_store_order_0(self):
        output = self.run('''
        $a = array(10, 11, 12, 13, array(20, 21, 22, 23));
        $n = 2;
        $a[$n *= 2][$n -= 1] = $n += 100;
        echo $a[4][3], $n;
        ''')
        assert self.space.int_w(output[0]) == 103
        assert self.space.int_w(output[1]) == 103

    def test_array_store_order_1(self):
        output = self.run('''
        $a = array(5);
        $a[0] = 3+!($a=array(6, 7));
        echo $a[0], $a[1];
        ''')
        assert self.space.int_w(output[0]) == 3
        assert self.space.int_w(output[1]) == 7

    def test_array_store_order_2(self):
        output = self.run('''
        $a = array(5);
        $v = 5;
        $a[0] = 3+!($a=array(&$v, 7));
        echo $a[0], $a[1], $v;
        ''')
        assert self.space.int_w(output[0]) == 3
        assert self.space.int_w(output[1]) == 7
        assert self.space.int_w(output[2]) == 3

    def test_array_store_order_3(self):
        output = self.run('''
        $v = 5;
        $a = array(&$v);
        $b = $a[0] = count($a=array(6, 7, 8));
        echo $a[0], $b;
        echo $v;
        ''')
        assert self.space.int_w(output[0]) == 3
        assert self.space.int_w(output[1]) == 3
        assert self.space.int_w(output[2]) == 5

    def test_dense_array_not_from_0(self):
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
        py.test.skip("XXX REFCOUNTING NEEDED")
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
        py.test.skip("XXX REFCOUNTING NEEDED")
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

    def test_array_of_array_2(self):
        output = self.run('''
        $a = array(array(42));
        $b = $a;
        $a[0][0] = 50;
        echo $b[0][0];
        ''')
        assert self.space.is_w(output[0], self.space.newint(42))

    def test_inplace_concat(self):
        output = self.run('''
        $a = "x";
        $a .= "y";
        echo $a;
        ''')
        assert self.space.str_w(output[0]) == "xy"

    def test_function_var_unused(self):
        self.run('''
        function f($a) {}
        f(3);
        ''')
        # this used to explode

    def test_inplace_str_concat(self):
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
        output = self.run("""
        define('x', 13);
        echo x;
        """)
        assert self.space.int_w(output[0]) == 13

    def test_const_2(self):
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
        output = self.run('''
        $s = "\\n";
        echo $s;
        echo "$s :-) \$s";
        echo "\\t";
        ''')
        assert self.space.str_w(output[0]) == '\n'
        assert self.space.str_w(output[1]) == '\n :-) $s'
        assert self.space.str_w(output[2]) == '\t'

    def test_prebuilt_consts(self):
        output = self.run('''
        echo TRUE, FALSE, NULL;
        ''')
        assert [self.space.is_true(i) for i in output] == [True, False, False]

    def test_do_while(self):
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
        self.run('''
        global $x;
        ''')
        # assert did not crash

    def test_invariant_global_namespace(self):
        output = self.run('''
        echo TruE;
        ''')
        assert self.space.is_true(output[0])

    def test_triple_eq(self):
        output = self.run('''
        echo 1.0 === 1;
        echo 1 === 1;
        echo 1 === true;
        ''')
        assert not self.space.is_true(output[0])
        assert self.space.is_true(output[1])
        assert not self.space.is_true(output[2])

    def test_triple_ne(self):
        output = self.run('''
        echo 1.0 !== 1;
        echo 1 !== 1;
        echo 1 !== true;
        ''')
        assert self.space.is_true(output[0])
        assert not self.space.is_true(output[1])
        assert self.space.is_true(output[2])

    def test_dynamic_call(self):
        output = self.run('''
        function f($a, $b) {
           return $a + $b;
        }
        $c = "f";
        echo $c(1, 2);
        ''')
        assert self.space.int_w(output[0]) == 3

    def test_assignment_in_and(self):
        output = self.run('''
        $a = 3;
        $a && $b = "x";
        echo $b;
        ''')
        assert self.space.str_w(output[0]) == 'x'

    def test_global_no_local(self):
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
        output = self.run('''
        function f() {
           return $GLOBALS["a"];
        }
        $a = 3;
        echo f();
        ''')
        assert self.space.int_w(output[0]) == 3

    def test_superglobals_assign(self):
        output = self.run('''
        function f() {
            global $b;
            $GLOBALS['b'] = 43;
            echo $b;
        }
        function g() {
            global $b;
            echo $b;
        }
        f();
        echo $b;
        g();
        ''')
        assert [self.space.int_w(i) for i in output] == [43, 43, 43]

    def test_superglobals_write(self):
        output = self.run('''
        $GLOBALS["c"] = 42;
        echo $c;
        ''')
        assert self.space.int_w(output[0]) == 42

    def test_superglobals_ref(self):
        output = self.run('''
        $a = 43;
        $b = &$a;
        echo $GLOBALS["a"], $GLOBALS["b"];
        $GLOBALS["c"] = &$a;
        echo $c;
        $GLOBALS["d"] = $a;
        echo $d;
        $a = 44;
        echo $a, $b, $c, $d;
        echo $GLOBALS["a"], $GLOBALS["b"], $GLOBALS["c"], $GLOBALS["d"];
        ''')
        assert [self.space.int_w(i) for i in output] == [43, 43, 43, 43,
                                                         44, 44, 44, 43,
                                                         44, 44, 44, 43]

    def test_null_eq(self):
        output = self.run('''
        $a = "x";
        echo $a == null, null == $a, null == null;
        echo $a != null, null != $a, null != null;
        ''')
        assert [i.boolval for i in output] == [False, False, True,
                                               True, True, False]

    def test_hash_of_a_copy_of_concat(self):
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
        output = self.run('''
        function F(){
            return 3;
        }
        echo f();
        ''')
        assert self.space.int_w(output[0]) == 3

    def test_global_2(self):
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

    def test_double_static_declarations(self):
        output = self.run('''
        function f() {
           static $a = 10;
           echo $a;
           static $a = 20;
           echo $a;
        }
        f();
        ''')
        assert [self.space.int_w(i) for i in output] == [20, 20]

    def test_double_static_declarations_uninit(self):
        output = self.run('''
        function f() {
           static $a = 10;
           echo $a;
           static $a;    // equivalent to: static $a = NULL;
           echo $a;
        }
        f();
        ''')
        assert [self.space.str_w(i) for i in output] == ['', '']  # NULL, NULL

    def test_default_args(self):
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
        echo $F . $s;
        ''')
        assert self.space.str_w(output[0]) == "1xx0"

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
        output = self.run('$a="x";\necho gettype($a[0]=5);')
        assert self.space.str_w(output[0]) == "string"

    def test_array_collisions(self):
        output = self.run('$a = array(0=>5, 0=>6);\necho $a[0];')
        assert self.space.int_w(output[0]) == 6
        output = self.run('''
        $b = 5;
        $a = array(0=>&$a, 0=>6);
        echo $b;
        ''')
        assert self.space.int_w(output[0]) == 5
        output = self.run('''
        $b = 5;
        $a = array($b, $b=7);
        echo $a[0];
        ''')
        assert self.space.int_w(output[0]) == 5
        output = self.run('''
        $key = "key";
        $a = array($key=>5, $key="bar");
        echo $a["key"];
        ''')
        assert self.space.int_w(output[0]) == 5
        output = self.run('''
        $key = "key";
        $a = array($key="bar", $key=>5);
        echo $a["bar"];
        ''')
        assert self.space.int_w(output[0]) == 5

    def test_getitem_does_not_create(self):
        output = self.run('''
        $a = array();
        $b = $a[0];   // NULL, but not stored in $a
        echo count($a);
        $a[] = 5;
        echo $a[0];
        ''')
        assert [self.space.int_w(i) for i in output] == [0, 5]

    def test_function_call_difference_based_on_actual_parameter(self):
        output = self.run('''
        function f1($a, $i) { g1($a[$i]); return $a; } //does not create $a[$i]
        function f2($a, $i) { g2($a[$i]); return $a; } //this creates $a[$i]
        function g1($x) { }
        function g2(&$x) { }
        echo count(f1(array(), 0));
        echo count(f2(array(), 0));
        echo count(f1(array(), "foo"));
        echo count(f2(array(), "foo"));
        ''')
        assert [self.space.int_w(i) for i in output] == [0, 1, 0, 1]

    def test_function_call_difference_based_on_actual_parameter_lazy(self):
        source = '''
        function f1($a, $j) { h1($j); g1($a[0]); return $a; }
        function h1($j) {
            if ($j == 5) {
                function g1($x) { }
            } else {
                function g1(&$x) { }
            }
        }
        '''
        output1 = self.run(source + 'echo count(f1(array(), 5));')
        output2 = self.run(source + 'echo count(f1(array(), 3));')
        assert self.space.int_w(output1[0]) == 0
        assert self.space.int_w(output2[0]) == 1

    def test_function_call_difference_based_on_actual_parameter_dyn(self):
        output = self.run('''
        function f1($name, $a) { $x = $name(count($a), $a[0], count($a));
                                 return $x + 100 * count($a); }
        function g1($m, $x, $n) { return 10+$n+1000*$m; }
        function g2($m, &$x, $n) { return 20+$n+1000*$m; }
        echo f1("g1", array());
        echo f1("g2", array());
        ''')
        assert [self.space.int_w(i) for i in output] == [10, 121]

    def test_function_call_argument_eval_order_1(self):
        output = self.run('''
        function f($a, $b) {
           echo $a, $b;
        }
        $x = 10;
        f($x, $x=12);
        ''')
        assert [self.space.int_w(i) for i in output] == [10, 12]

    def test_function_call_argument_eval_order_2(self):
        output = self.run('''
        function f(&$a, $b) {    // <-- difference with the previous test
           echo $a, $b;
        }
        $x = 10;
        f($x, $x=12);
        ''')
        assert [self.space.int_w(i) for i in output] == [12, 12]

    def test_builtin_function_call_argument_eval_order(self):
        output = self.run('''
        $x = 2;
        echo pow($x, $x=3);
        $y = 3;
        echo max($y, $y=1, $y);
        ''')
        assert self.space.float_w(output[0]) == 8.0
        assert self.space.int_w(output[1]) == 3

    def test_foreach_1(self):
        output = self.run('''
        $a = array(10, 20, 30, 40);
        foreach($a as $n) {
            echo $n;
        }
        ''')
        assert [self.space.int_w(i) for i in output] == [10, 20, 30, 40]

    def test_foreach_2(self):
        output = self.run('''
        $a = array(10, 20, 30, 40);
        foreach($a as $k => $n) {
            echo gettype($k);
            echo $k;
            echo $n;
        }
        ''')
        assert [self.space.str_w(i) for i in output] == [
            'integer', '0', '10',
            'integer', '1', '20',
            'integer', '2', '30',
            'integer', '3', '40']

    def test_foreach_3(self):
        output = self.run('''
        $a = array("0"=>10, "1"=>20, "2"=>30, "3"=>40);
        foreach($a as $k => $n) {
            echo gettype($k);
            echo $k;
            echo $n;
        }
        ''')
        assert [self.space.str_w(i) for i in output] == [
            'integer', '0', '10',
            'integer', '1', '20',
            'integer', '2', '30',
            'integer', '3', '40']

    def test_foreach_4(self):
        output = self.run('''
        $a = array(10, 20, 30, 40);
        $c = 0;
        $b = array(1=>&$c);
        foreach($a as $k => $b[1]) {
            echo $c;
        }
        ''')
        assert [self.space.int_w(i) for i in output] == [10, 20, 30, 40]

    def test_foreach_ref_1(self):
        output = self.run('''
        $a = array(10, 20, 30, 40);
        foreach($a as &$n) {
            $n *= 10;
        }
        echo $a[0];
        echo $a[3];
        ''')
        assert [self.space.int_w(i) for i in output] == [100, 400]

    def test_foreach_ref_2(self):
        output = self.run('''
        $a = array(10, 20, 30, 40);
        foreach($a as $k => &$n) {
            echo gettype($k);
            echo $k;
            echo $n++;
        }
        echo $a[0];
        echo $a[3];
        ''')
        assert [self.space.str_w(i) for i in output] == [
            'integer', '0', '10',
            'integer', '1', '20',
            'integer', '2', '30',
            'integer', '3', '40',
            '11', '41']

    def test_foreach_ref_3(self):
        output = self.run('''
        $a = array(10, 20, 30, 40);
        $c = 0;
        $b = array(1=>&$c);
        foreach($a as $k => &$b[1]) {
            echo $b[1];
            echo $c;
        }
        ''')
        assert [self.space.int_w(i) for i in output] == [
            10, 0, 20, 0, 30, 0, 40, 0]

    def test_foreach_ref_cornercase_1(self):
        output = self.run('''
        $a = array(10);
        foreach($a as &$v) {
            echo $v;
            $a[] = 42;
        }
        ''')
        assert [self.space.int_w(i) for i in output] == [10]

    def test_foreach_ref_cornercase_2(self):
        py.test.skip("XXX later")
        output = self.run('''
        $a = array(10, 20);
        $n = 8;
        foreach($a as &$v) {
            if (!--$n) break;
            echo $v;
            $a[] = 42;
        }
        ''')
        assert [self.space.int_w(i) for i in output] == [
            10, 20, 42, 42, 42, 42, 42]

    def test_unset_1(self):
        output = self.run('''
        $x1 = 42;
        $x2 = &$x1;
        unset($x1);
        echo gettype($x1);
        echo gettype($x2);
        foreach($GLOBALS as $key=>$value) {
            echo $key;
        }
        ''')
        assert self.space.str_w(output[0]) == 'NULL'
        assert self.space.str_w(output[1]) == 'integer'
        assert 'x1' not in [self.space.str_w(i) for i in output]
        assert 'x2' in [self.space.str_w(i) for i in output]

    def test_unset_2(self):
        output = self.run('''
        function destroy_bar() {
            global $bar;
            unset($bar);
        }
        $bar = "baz";
        destroy_bar();
        echo $bar;
        ''')
        assert self.space.str_w(output[0]) == 'baz'

    def test_unset_3(self):
        output = self.run('''
        function destroy_bar() {
            unset($GLOBALS['bar']);
        }
        $bar = "baz";
        $baz = &$bar;
        destroy_bar();
        echo gettype($bar);
        echo gettype($baz);
        ''')
        assert self.space.str_w(output[0]) == 'NULL'
        assert self.space.str_w(output[1]) == 'string'

    def test_unset_4(self):
        output = self.run('''
        function foo(&$bar) {
            unset($bar);
            echo gettype($bar);
            $bar = "othervalue";
            echo $bar;
        }
        $bar = "baz";
        foo($bar);
        echo $bar;
        ''')
        assert self.space.str_w(output[0]) == 'NULL'
        assert self.space.str_w(output[1]) == 'othervalue'
        assert self.space.str_w(output[2]) == 'baz'

    def test_unset_5(self):
        output = self.run('''
        function foo() {
            static $bar;
            $bar++;
            echo $bar;
            unset($bar);
            $bar = 23;
            echo $bar;
        }
        foo();
        foo();
        foo();
        ''')
        assert [self.space.int_w(i) for i in output] == [
            1, 23, 2, 23, 3, 23]

    def test_unset_6(self):
        output = self.run('''
        $v = 42;
        $a = array(&$v);
        unset($a[0]);
        echo $v;
        ''')
        assert self.space.int_w(output[0]) == 42
        output = self.run('''
        $v = 42;
        $a = array(&$v);
        $a[0] = NULL;
        echo gettype($v);
        ''')
        assert self.space.str_w(output[0]) == 'NULL'

    def test_float_constants(self):
        output = self.run('''
        echo INF;
        echo -INF;
        echo NAN;
        echo INF-INF;
        ''')
        assert [self.space.str_w(i) for i in output] == ['inf', '-inf',
                                                         'nan', 'nan']
