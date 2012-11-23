
import py
from hippy.test.test_interpreter import BaseTestInterpreter
from hippy.objects import arrayobject

class TestFile(BaseTestInterpreter):
    def setup_class(cls):
        tmpdir = py.path.local.make_numbered_dir('hippy')
        cls.tmpdir = tmpdir

    def test_get_file_contents(self):
        fname = self.tmpdir.join('get_file_contents')
        fname.write('xyyz')
        output = self.run('''
        echo file_get_contents("%s");
        ''' % fname)
        assert self.space.str_w(output[0]) == 'xyyz'

    def test_unserialize(self):
        output = self.run('''
        $a = unserialize('a:3:{i:0;i:1;i:1;i:2;i:2;s:3:"xyz";}');
        echo unserialize("b:1;"), unserialize("i:3;"),
             unserialize("d:15.2;"), unserialize('s:5:"acdef";'),
             $a[2], unserialize("N;");
        ''')
        assert self.space.is_true(output[0])
        assert self.space.int_w(output[1]) == 3
        assert self.space.float_w(output[2]) == 15.2
        assert self.space.str_w(output[3]) == "acdef"
        assert self.space.str_w(output[4]) == "xyz"
        assert output[5] is self.space.w_Null

class TestBuiltin(BaseTestInterpreter):
    def test_builtin_sin_cos(self):
        output = self.run("""
        $i = 1.5707963267948966;
        echo cos($i) + 2 * sin($i);
        """)
        assert self.space.float_w(output[0]) == 2.0

    def test_builtin_pow(self):
        output = self.run("""
        $i = pow(1.2, 2.4);
        echo $i;
        """)
        assert self.space.float_w(output[0]) == 1.2 ** 2.4

    def test_builtin_max(self):
        output = self.run("""
        echo max(1, 1.2), max(5, 4), max(1.1, 0.0), max(NULL, 3);
        """)
        assert self.space.float_w(output[0]) == 1.2
        assert self.space.int_w(output[1]) == 5
        assert self.space.float_w(output[2]) == 1.1
        assert self.space.int_w(output[3]) == 3

    def test_unset(self):
        output = self.run("""
        $a = 3;
        echo $a;
        $b = $a;
        $c = $a;
        unset($a, $c);
        echo $a, $b, $c;
        """)
        assert self.space.int_w(output[0]) == 3
        assert self.space.int_w(output[2]) == 3
        assert output[1] is self.space.w_Null
        assert output[3] is self.space.w_Null

    def test_unset_array_elems(self):
        output = self.run("""
        $a = array(1);
        unset($a[0], $a['xyz']);
        echo $a, $a[0];
        """)
        assert output[1] is self.space.w_Null
        w_array = output[0].strategy.unerase(output[0].storage).parent
        # int or null
        assert isinstance(w_array.strategy, arrayobject.ListArrayStrategy)

    def test_printf_1(self):
        output = self.run('''
        printf("a %d b\\n", 12);
        ''')
        assert self.space.str_w(output[0]) == 'a 12 b\n'

    def test_count(self):
        output = self.run('''
        $a = array(1, 2, 3);
        echo count($a), sizeof($a);
        ''')
        assert [self.space.int_w(i) for i in output] == [3, 3]

    def test_count_not_full(self):
        output = self.run('''
        $a = array(1, 2, 3);
        $a[15] = 3;
        echo count($a), $a[15];
        ''')
        assert self.space.int_w(output[0]) == 4
        assert self.space.int_w(output[1]) == 3

    def test_count_not_full_2(self):
        output = self.run('''
        $a = array();
        $a[15] = 3;
        echo count($a), $a[15];
        ''')
        assert self.space.int_w(output[0]) == 1
        assert self.space.int_w(output[1]) == 3

    def test_count_not_full_3(self):
        output = self.run('''
        $a = array("xyz");
        $a[15] = 3;
        echo count($a), $a[15];
        ''')
        assert self.space.int_w(output[0]) == 2
        assert self.space.int_w(output[1]) == 3

    def test_substr(self):
        output = self.run('''
        $a = "xyz";
        echo substr($a, 0, 3), substr($a, 1), substr($a, -1, 1),
             substr($a, 1, 1), substr($a, 1, -1), substr($a, 1, NULL);
        ''')
        assert [self.space.str_w(s) for s in output] == ["xyz", "yz", "z",
                                                         "y", "y", ""]

    def test_print(self):
        output = self.run('''
        print("xyz");
        ''')
        assert self.space.str_w(output[0]) == 'xyz'

    def test_empty(self):
        output = self.run('''
        echo empty(1), empty(array(1, 2)), empty(0), empty(array());
        ''')
        assert [i.boolval for i in output] == [False, False, True, True]

    def test_isset(self):
        output = self.run('''
        $a = array(1, null);
        $b = null;
        echo isset($a[3]), isset($a[1]), isset($a), isset($a[0]), isset($b);
        ''')
        assert [i.boolval for i in output] == [False, False, True, True, False]

    def test_array_fill_keys(self):
        output = self.run('''
        $a = array(1, 2, 3, 4);
        $b = array_fill_keys($a, "x");
        echo $b[3], $b[4];
        ''')
        assert [self.space.str_w(i) for i in output] == ["x", "x"]

    def test_array_fill(self):
        output = self.run('''
        $a = array_fill(0, 10, "x");
        echo $a[0];
        echo $a[8];
        ''')
        assert [self.space.str_w(i) for i in output] == ["x", "x"]

    def test_is_array(self):
        output = self.run('''
        echo is_array(0), is_array(0.0), is_array(NULL), is_array(array());
        echo is_array(FALSE), is_array(TRUE), is_array("foo");
        ''')
        assert [i.boolval for i in output] == [False, False, False, True,
                                               False, False, False]

    def test_is_bool(self):
        output = self.run('''
        echo is_bool(0), is_bool(0.0), is_bool(NULL), is_bool(array());
        echo is_bool(FALSE), is_bool(TRUE), is_bool("foo");
        ''')
        assert [i.boolval for i in output] == [False, False, False, False,
                                               True, True, False]

    def test_is_int(self):
        output = self.run('''
        echo is_int(0), is_int(0.0), is_int(NULL), is_int(array());
        echo is_int(FALSE), is_int(TRUE), is_int("foo");
        ''')
        assert [i.boolval for i in output] == [True, False, False, False,
                                               False, False, False]

    def test_is_integer(self):
        output = self.run('''
        echo is_integer(0), is_integer(0.0), is_integer(NULL), is_integer(array());
        echo is_integer(FALSE), is_integer(TRUE), is_integer("foo");
        ''')
        assert [i.boolval for i in output] == [True, False, False, False,
                                               False, False, False]

    def test_is_long(self):
        output = self.run('''
        echo is_long(0), is_long(0.0), is_long(NULL), is_long(array());
        echo is_long(FALSE), is_long(TRUE), is_long("foo");
        ''')
        assert [i.boolval for i in output] == [True, False, False, False,
                                               False, False, False]

    def test_is_float(self):
        output = self.run('''
        echo is_float(0), is_float(0.0), is_float(NULL), is_float(array());
        echo is_float(FALSE), is_float(TRUE), is_float("foo");
        ''')
        assert [i.boolval for i in output] == [False, True, False, False,
                                               False, False, False]

    def test_is_double(self):
        output = self.run('''
        echo is_double(0), is_double(0.0), is_double(NULL), is_double(array());
        echo is_double(FALSE), is_double(TRUE), is_double("foo");
        ''')
        assert [i.boolval for i in output] == [False, True, False, False,
                                               False, False, False]

    def test_is_real(self):
        output = self.run('''
        echo is_real(0), is_real(0.0), is_real(NULL), is_real(array());
        echo is_real(FALSE), is_real(TRUE), is_real("foo");
        ''')
        assert [i.boolval for i in output] == [False, True, False, False,
                                               False, False, False]

    def test_is_null(self):
        output = self.run('''
        echo is_null(0), is_null(0.0), is_null(NULL), is_null(array());
        echo is_null(FALSE), is_null(TRUE), is_null("foo");
        ''')
        assert [i.boolval for i in output] == [False, False, True, False,
                                               False, False, False]

    def test_is_scalar(self):
        output = self.run('''
        echo is_scalar(0), is_scalar(0.0), is_scalar(NULL), is_scalar(array());
        echo is_scalar(FALSE), is_scalar(TRUE), is_scalar("foo");
        ''')
        assert [i.boolval for i in output] == [True, True, False, False,
                                               True, True, True]

    def test_is_string(self):
        output = self.run('''
        echo is_string(0), is_string(0.0), is_string(NULL), is_string(array());
        echo is_string(FALSE), is_string(TRUE), is_string("foo");
        ''')
        assert [i.boolval for i in output] == [False, False, False, False,
                                               False, False, True]

    def test_array_merge(self):
        output = self.run('''
        $a = array("xyz" => 1);
        $b = array("a" => 2);
        $c = array_merge($a, $b);
        echo $c["a"], $c["xyz"];
        $a = array(1, 2, 3);
        $b = array(4, 5, 6);
        $c = array_merge($a, $b);
        echo $c[4];
        ''')
        assert [self.space.int_w(i) for i in output] == [2, 1, 5]

    def test_defined(self):
        output = self.run('''
        define("abc", 3);
        echo defined("abc"), defined("def");
        ''')
        assert [i.boolval for i in output] == [True, False]

    def test_array_diff_key(self):
        output = self.run('''
        $a = array_diff_key(array("a" => 1, 1 => 2, "c" =>3),
                            array("c"=>18), array(0, 1));
        echo count($a), $a[0];
        echo array_diff_key(NULL, array(1, 2, 3));
        ''')
        assert self.space.int_w(output[0]) == 1
        assert self.space.str_w(output[1]) == "a"

    def test_array_diff_assoc(self):
        output = self.run('''
        $array1 = array("a" => "green", "b" => "brown", "c" => "blue", "red");
        $array2 = array("a" => "green", "yellow", "red");
        $result = array_diff_assoc($array1, $array2);
        echo $result["b"];
        echo $result["c"];
        echo $result[0];
        ''')
        assert self.space.str_w(output[0]) == "brown"
        assert self.space.str_w(output[1]) == "blue"
        assert self.space.str_w(output[2]) == "red"

    def test_array_change_key_case(self):
        output = self.run('''
        $a = array("a" => 1, 1 => 2, "c" =>3);
        $a = array_change_key_case($a, 1);
        echo $a['A'];
        echo $a[1];
        $a = array("A" => 1, 1 => 2, "c" =>3);
        $a = array_change_key_case($a, 0);
        echo $a['a'];
        echo $a[1];
        echo $a['c'];

        ''')
        assert self.space.str_w(output[0]) == "1"
        assert self.space.str_w(output[1]) == '2'
        assert self.space.str_w(output[2]) == "1"
        assert self.space.str_w(output[3]) == '2'
        assert self.space.str_w(output[4]) == "3"

    def test_array_combine(self):
        output = self.run('''
        $a = array('god', 'save', 'the', 'queen');
        $b = array(1, 2, 3, 4);
        $c = array_combine($a, $b);
        echo $c['god'];
        echo $c['the'];
        $a = array(1, 2, 3, 4);
        $b = array('god', 'save', 'the', 'queen');
        $c = array_combine($a, $b);
        echo $c['1'];
        echo $c['4'];
        $a = array('a'=>1, 'b', 'c', 'd');
        $b = array('q', 'w', 'e', 'r'=>5);
        $c = array_combine($a, $b);
        echo $c['1'];
        echo $c['b'];
        echo $c['d'];

        ''')
        assert self.space.str_w(output[0]) == '1'
        assert self.space.str_w(output[1]) == "3"
        assert self.space.str_w(output[2]) == "god"
        assert self.space.str_w(output[3]) == "queen"
        assert self.space.str_w(output[4]) == "q"
        assert self.space.str_w(output[5]) == "w"
        assert self.space.str_w(output[6]) == "5"

    def test_array_slice(self):
        output = self.run('''
        $a = array(0, 1, 2, 3, 4, 5, 6, 7, 8, 9);
        $a = array_slice($a, 2);
        echo $a[0];
        $a = array(0, 1, 2, 3, 4, 5, 6, 7, 8, 9);
        $a = array_slice($a, 1, 3);
        echo $a[0];
        echo $a[1];
        $a = array(0, 1, 2, 3, 4, 5, 6, 7, 8, 9);
        $a = array_slice($a, 5, 6);
        echo $a[0];
        $a = array(0, 1, 2, 3, 4, 5, 6, 7, 8, 9);
        $a = array_slice($a, -2, 6);
        echo $a[0];
        $a = array(0, 1, 2, 3, 4, 5, 6, 7, 8, 9);
        $a = array_slice($a, -5, -2);
        echo $a[0];
        echo $a[1];
        echo $a[2];

        $a = array(0, 1, 2, 3, 4, 5, 6, 7, 8, 9);
        $a = array_slice($a, 2, true);
        echo $a[2];
        $a = array(0, 1, 2, 3, 4, 5, 6, 7, 8, 9);
        $a = array_slice($a, 1, 3, true);
        echo $a[1];
        echo $a[2];
        $a = array(0, 1, 2, 3, 4, 5, 6, 7, 8, 9);
        $a = array_slice($a, 5, 6, true);
        echo $a[5];
        $a = array(0, 1, 2, 3, 4, 5, 6, 7, 8, 9);
        $a = array_slice($a, -2, 6, true);
        echo $a[8];
        $a = array(0, 1, 2, 3, 4, 5, 6, 7, 8, 9);
        $a = array_slice($a, -5, -2, true);
        echo $a[5];
        echo $a[6];
        echo $a[7];


        ''')
        assert self.space.str_w(output[0]) == '2'

        assert self.space.str_w(output[1]) == '1'
        assert self.space.str_w(output[2]) == '2'

        assert self.space.str_w(output[3]) == '5'

        assert self.space.str_w(output[4]) == '8'

        assert self.space.str_w(output[5]) == '5'
        assert self.space.str_w(output[6]) == '6'
        assert self.space.str_w(output[7]) == '7'

        assert self.space.str_w(output[8]) == '2'

        assert self.space.str_w(output[9]) == '1'
        assert self.space.str_w(output[10]) == '2'

        assert self.space.str_w(output[11]) == '5'

        assert self.space.str_w(output[12]) == '8'

        assert self.space.str_w(output[13]) == '5'
        assert self.space.str_w(output[14]) == '6'
        assert self.space.str_w(output[15]) == '7'

    def test_array_chunk(self):
        output = self.run('''
        $a = array(0, 1, 2, 3, 4, 5, 6, 7, 8, 9);
        $a = array_chunk($a, 3);
        echo $a[0][0];
        echo $a[1][0];
        echo $a[2][0];
        echo count($a);
        echo $a[3][0];
        echo count($a[0]);
        echo count($a[3]);

        $a = array(0, 1, 2, 3, 4, 5, 6, 7, 8, 9);
        $a = array_chunk($a, 3, true);
        echo $a[0][0];
        echo $a[1][3];
        echo $a[2][6];
        echo count($a);
        echo $a[3][9];
        echo count($a[0]);
        echo count($a[3]);

        ''')
        assert self.space.str_w(output[0]) == "0"
        assert self.space.str_w(output[1]) == "3"
        assert self.space.str_w(output[2]) == "6"
        assert self.space.str_w(output[3]) == "4"
        assert self.space.str_w(output[4]) == "9"
        assert self.space.str_w(output[5]) == "3"
        assert self.space.str_w(output[6]) == "1"

        assert self.space.str_w(output[7]) == "0"
        assert self.space.str_w(output[8]) == "3"
        assert self.space.str_w(output[9]) == "6"
        assert self.space.str_w(output[10]) == "4"
        assert self.space.str_w(output[11]) == "9"
        assert self.space.str_w(output[12]) == "3"
        assert self.space.str_w(output[13]) == "1"

    def test_array_count_values(self):
        output = self.run('''
        $a = array(1, "hello", 1, "world", "hello");
        $a = array_count_values($a);
        echo $a[1];
        echo $a["hello"];
        echo $a["world"];
        ''')
        assert self.space.str_w(output[0]) == '2'
        assert self.space.str_w(output[1]) == '2'
        assert self.space.str_w(output[2]) == '1'

    def test_array_flip(self):
        output = self.run('''
        $a = array('a'=>0, 'b'=>2, 'c');
        $a = array_flip($a);
        echo $a[2];
        echo $a['c'];
        echo $a[0];
        $a =  array("a" => 1, "b" => 1, "c" => 2);
        $a = array_flip($a);
        echo $a[1];
        ''')
        assert self.space.str_w(output[0]) == "b"
        assert self.space.str_w(output[1]) == "0"
        assert self.space.str_w(output[2]) == "a"
        assert self.space.str_w(output[3]) == "b"

    def test_array_sum(self):
        output = self.run('''
        $a = array('a'=>0, 'b'=>2, 'c', 1, 2, 3, '5');
        $a = array_sum($a);
        echo $a;
        ''')
        assert self.space.str_w(output[0]) == "13"

    def test_array_pad(self):
        output = self.run('''
        $b = array(1229600459=>'large', 1229604787=>20, 1229609459=>'red');
        $b = array_pad($b, 5, 'foo');
        echo $b[0];
        echo $b[4];
        $a= array('a'=> 'a', 'b'=>4, '0'=>'0');
        $a = array_pad($a, -6, "x");
        echo $a[0];
        echo $a[3];
        ''')
        assert self.space.str_w(output[0]) == "large"
        assert self.space.str_w(output[1]) == "foo"
        assert self.space.str_w(output[2]) == "x"
        assert self.space.str_w(output[3]) == "0"

    def test_array_product(self):
        output = self.run('''
        echo array_product(array('a'=>1, 'b'=>2, 'c', 1, 2, 3, '5'));
        echo array_product(array('a'=>1, 'b'=>2, 1, 1, 2, 3, '5'));
        echo array_product(array(1=>1, 'b'=>2, 1, 1, 2, 3, 5));
        echo array_product(array());
        ''')
        assert self.space.str_w(output[0]) == "0"
        assert self.space.str_w(output[1]) == "60"
        assert self.space.str_w(output[2]) == "60"
        assert self.space.str_w(output[3]) == "0"

    def test_array_reverse(self):
        output = self.run('''
        $a = array("php", 4.0, array ("green", "red"));
        $a = array_reverse($a);
        echo $a[2];
        echo $a[1];
        $a = array(0=>1, 2=>4, '3'=>'6');
        $b = array_reverse($a, true);
        $c = array_reverse($a, false);
        echo $b[0];
        echo $c[0];
        $a = array(0=>1, 2=>4, '3'=>'6');
        $b = array_reverse($a, 'x');
        $c = array_reverse($a, '');
        echo $b[0];
        echo $c[0];
        $a = array(0=>1, 2=>4, '3'=>'6');
        $b = array_reverse($a, 0.001);
        $c = array_reverse($a, 0);
        echo $b[0];
        echo $c[0];

        ''')
        assert self.space.str_w(output[0]) == "php"
        assert self.space.str_w(output[1]) == "4.0"
        assert self.space.str_w(output[2]) == "1"
        assert self.space.str_w(output[3]) == "6"
        assert self.space.str_w(output[4]) == "1"
        assert self.space.str_w(output[5]) == "6"
        assert self.space.str_w(output[6]) == "1"
        assert self.space.str_w(output[7]) == "6"

    def test_array_keys(self):
        output = self.run('''
        $a = array("php", 4.0, "test"=>"test");
        $a = array_keys($a);
        echo $a[0];
        echo $a[1];
        echo $a[2];
        $a = array("php", 4.0, "test"=>"test", "php");
        $a = array_keys($a, "php");
        echo $a[0];
        echo $a[1];
        $a = array(1, 2, 3, 4, 5, 6, 7);
        $a = array_keys($a, '2');
        echo $a[0];
        $a = array(1, 2, 3, 4, 5, 6, 7);
        $a = array_keys($a, '2', true);
        echo sizeof($a);

        ''')
        assert self.space.str_w(output[0]) == "0"
        assert self.space.str_w(output[1]) == "1"
        assert self.space.str_w(output[2]) == "test"
        assert self.space.str_w(output[3]) == "0"
        assert self.space.str_w(output[4]) == "2"
        assert self.space.str_w(output[5]) == "1"
        assert self.space.str_w(output[6]) == "0"

    def test_array_values(self):
        output = self.run('''
        $a = array("php", 4.5, "key"=>"test");
        $a = array_values($a);
        echo $a[0];
        echo $a[1];
        echo $a[2];

        ''')
        assert self.space.str_w(output[0]) == "php"
        assert self.space.str_w(output[1]) == "4.5"
        assert self.space.str_w(output[2]) == "test"

    def test_array_combine_mix(self):
        output = self.run('''
        $a = array('a'=>1, 'b', 'c', 'd');
        $b = array('q', 'w', 'e', 'r'=>5);
        $c = array_combine($a, $b);
        echo $c[1];
        echo $c['b'];
        echo $c['c'];
        echo $c['d'];

        ''')
        assert self.space.str_w(output[0]) == "q"
        assert self.space.str_w(output[1]) == "w"
        assert self.space.str_w(output[2]) == "e"
        assert self.space.str_w(output[3]) == "5"

    def test_str_repeat(self):
        output = self.run('''
        $a = str_repeat("xyz", 2);
        echo $a;
        ''')
        assert self.space.str_w(output[0]) == 'xyzxyz'
        py.test.skip("XXX in-progress")
        assert self.echo("str_repeat('a', 5)") == "aaaaa"
        assert self.echo("str_repeat('a', 5.9)") == "aaaaa"
        assert self.echo("str_repeat('a', '5')") == "aaaaa"
        assert self.echo("str_repeat('a', '+5')") == "aaaaa"
        assert self.echo("str_repeat('a', '5.1')") == "aaaaa"
        assert self.echo("str_repeat('a', '5.1')") == "aaaaa"
        assert self.echo("str_repeat('a', TRUE)") == "a"
        assert self.echo("str_repeat('a', FALSE)") == ""
        assert self.echo("str_repeat('a', NULL)") == ""

    def test_gettype(self):
        output = self.run('''
        echo gettype(5 > 2);
        echo gettype(5);
        echo gettype(5.5);
        echo gettype("5");
        echo gettype(array());
        echo gettype(NULL);
        ''')
        assert self.space.str_w(output[0]) == 'boolean'
        assert self.space.str_w(output[1]) == 'integer'
        assert self.space.str_w(output[2]) == 'double'
        assert self.space.str_w(output[3]) == 'string'
        assert self.space.str_w(output[4]) == 'array'
        assert self.space.str_w(output[5]) == 'NULL'

    def test_function_exists(self):
        output = self.run('''
        function f42() { }
        echo function_exists("f42");
        echo function_exists("function_exists");
        echo function_exists("f43");
        ''')
        assert self.space.str_w(output[0]) == '1'
        assert self.space.str_w(output[1]) == '1'
        assert self.space.str_w(output[2]) == ''

    def test_var_dump(self):
        output = self.run('''
        var_dump(5);
        $a = 5.5; var_dump($a);
        var_dump(5.0);
        var_dump(TRUE);
        var_dump(FALSE);
        var_dump(NULL);
        var_dump(5, 6, 7);
        var_dump("foobar");
        $a = array(4, 5); var_dump($a);
        ''')
        assert ''.join(output) == '''\
int(5)
float(5.5)
float(5)
bool(true)
bool(false)
NULL
int(5)
int(6)
int(7)
string(6) "foobar"
array(2) {
  [0]=>
  int(4)
  [1]=>
  int(5)
}
'''

    def test_var_dump_2(self):
        py.test.skip("FIXME")
        output = self.run('''
        var_dump(array(TRUE, 5), array("xx"=>array(0), 7));
        ''')
        assert ''.join(output) == '''\
array(2) {
  [0]=>
  bool(true)
  [1]=>
  int(5)
}
array(2) {
  ["xx"]=>
  array(1) {
    [0]=>
    int(0)
  }
  [0]=>
  int(7)
}
'''

    def test_var_dump_recursion(self):
        output = self.run('var_dump($GLOBALS);')
        assert '*RECURSION*' in ''.join(output)

    def test_print_r_0(self):
        output = self.run('''
        print_r(25);
        $a = 25.5; print_r($a);
        print_r(25.0);
        print_r(TRUE);
        print_r(FALSE);
        print_r(NULL);
        print_r("foobar");
        $a = array(4, 5); print_r($a);
        ''')
        assert output == [
            '25',
            '25.5',
            '25',
            '1',
            '',
            '',
            'foobar',
            'Array\n(\n    [0] => 4\n    [1] => 5\n)\n']

    def test_print_r_recursion(self):
        output = self.run('''
        print_r($GLOBALS);
        ''')
        assert '*RECURSION*' in output[0]

    def test_print_r_1(self):
        output = self.run('''
        $a = print_r(array(25.5), 1);
        echo "the result is: ", $a;
        ''')
        assert self.space.str_w(output[0]) == 'the result is: '
        assert self.space.str_w(output[1]) == 'Array\n(\n    [0] => 25.5\n)\n'

    def test_intval(self):
        py.test.skip("XXX in-progress")
        assert self.echo("intval(42)") == "42"
        assert self.echo("intval(4.2)") == "4"
        assert self.echo("intval('42')") == "42"
        assert self.echo("intval('+42')") == "42"
        assert self.echo("intval('-42')") == "-42"
        assert self.echo("intval(042)") == "34"
        assert self.echo("intval('042')") == "42"
        assert self.echo("intval(1e10)") == "1410065408"
        assert self.echo("intval('1e10')") == "1"
        assert self.echo("intval(0x1A)") == "26"
        assert self.echo("intval(42000000)") == "42000000"
        assert self.echo("intval(420000000000000000000)") == "0"
        assert self.echo("intval('420000000000000000000')") == "2147483647"
        assert self.echo("intval(42, 8)") == "42"
        assert self.echo("intval('42', 8)") == "34"
        assert self.echo("intval(array())") == "0"
        assert self.echo("intval(array('foo', 'bar'))") == "1"
