
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
        echo is_array(0), is_array(array());
        ''')
        assert [i.boolval for i in output] == [False, True]

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

    # def test_array_reverse(self):
    #     output = self.run('''
    #     $a = array("php", 4.0, array ("green", "red"));
    #     $a = array_reverse($a);
    #     echo $a[2];
    #     ''')
    #     assert self.space.str_w(output[0]) == "php"

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
        $a = array("php", 4.0, "key"=>"test");
        $a = array_values($a);
        echo $a[0];
        echo $a[1];
        echo $a[2];

        ''')
        assert self.space.str_w(output[0]) == "php"
        assert self.space.str_w(output[1]) == "4.0"
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
