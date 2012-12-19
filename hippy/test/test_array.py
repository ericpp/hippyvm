
import py
from hippy.test.test_interpreter import BaseTestInterpreter
from hippy.objspace import ObjSpace

class TestArrayDirect(object):
    def create_array_strats(self, space):
        # int, float, mix, empty, hash, copy
        int_arr = space.new_array_from_list([space.wrap(1), space.wrap(2)])
        return (int_arr,
                space.new_array_from_list([space.wrap(1.2), space.wrap(2.2)]),
                space.new_array_from_list([space.wrap(1.2),
                                           space.newstrconst("x")]),
                space.new_array_from_list([]),
                space.new_array_from_pairs([
                    (space.newstrconst("xyz"), space.wrap(1)),
                    (space.newstrconst("a"), space.wrap(2)),
                    (space.newstrconst("b"), space.wrap(3)),
                    (space.newstrconst("c"), space.wrap(4))]),
                int_arr.copy(space))

    def test_value_iterators(self):
        space = ObjSpace()
        int_arr, float_arr, mix_arr, empty, hash, cp_arr = \
                 self.create_array_strats(space)
        w_iter = int_arr.create_iter(space)
        assert space.int_w(w_iter.next(space)) == 1
        assert space.int_w(w_iter.next(space)) == 2
        assert w_iter.done()
        w_iter = float_arr.create_iter(space)
        assert space.float_w(w_iter.next(space)) == 1.2
        assert space.float_w(w_iter.next(space)) == 2.2
        assert w_iter.done()
        w_iter = mix_arr.create_iter(space)
        assert space.float_w(w_iter.next(space)) == 1.2
        assert space.str_w(w_iter.next(space)) == "x"
        assert w_iter.done()
        assert empty.create_iter(space).done()
        w_iter = hash.create_iter(space)
        assert space.int_w(w_iter.next(space)) == 1
        assert space.int_w(w_iter.next(space)) == 2
        assert space.int_w(w_iter.next(space)) == 3
        assert space.int_w(w_iter.next(space)) == 4
        assert w_iter.done()
        w_iter = cp_arr.create_iter(space)
        assert space.int_w(w_iter.next(space)) == 1
        assert space.int_w(w_iter.next(space)) == 2
        assert w_iter.done()

    def test_item_iterators(self):
        def unpack((w_1, w_2)):
            l = []
            for w_obj in w_1, w_2:
                if w_obj.tp == space.tp_str:
                    l.append(space.str_w(w_obj))
                elif w_obj.tp == space.tp_float:
                    l.append(space.float_w(w_obj))
                elif w_obj.tp == space.tp_int:
                    l.append(space.int_w(w_obj))
                else:
                    raise NotImplementedError
            return l

        space = ObjSpace()
        int_arr, float_arr, mix_arr, empty, hash, cp_arr = \
                 self.create_array_strats(space)
        w_iter = int_arr.create_iter(space)
        assert unpack(w_iter.next_item(space)) == [0, 1]
        assert unpack(w_iter.next_item(space)) == [1, 2]
        assert w_iter.done()
        w_iter = float_arr.create_iter(space)
        assert unpack(w_iter.next_item(space)) == [0, 1.2]
        assert unpack(w_iter.next_item(space)) == [1, 2.2]
        assert w_iter.done()
        w_iter = mix_arr.create_iter(space)
        assert unpack(w_iter.next_item(space)) == [0, 1.2]
        assert unpack(w_iter.next_item(space)) == [1, "x"]
        assert w_iter.done()
        assert empty.create_iter(space).done()
        w_iter = hash.create_iter(space)
        assert unpack(w_iter.next_item(space)) == ['xyz', 1]
        assert unpack(w_iter.next_item(space)) == ['a', 2]
        assert unpack(w_iter.next_item(space)) == ['b', 3]
        assert unpack(w_iter.next_item(space)) == ['c', 4]
        assert w_iter.done()
        w_iter = cp_arr.create_iter(space)
        assert unpack(w_iter.next_item(space)) == [0, 1]
        assert unpack(w_iter.next_item(space)) == [1, 2]
        assert w_iter.done()

    def test_isset_index(self):
        space = ObjSpace()
        int_arr, float_arr, mix_arr, empty, hash, cp_arr = \
                 self.create_array_strats(space)
        assert int_arr.isset_index(space, space.wrap(0))
        assert not int_arr.isset_index(space, space.wrap(13))
        assert float_arr.isset_index(space, space.wrap(0))
        assert not float_arr.isset_index(space, space.wrap(13))
        assert mix_arr.isset_index(space, space.wrap(0))
        assert not mix_arr.isset_index(space, space.wrap(13))
        assert not empty.isset_index(space, space.wrap(0))
        assert hash.isset_index(space, space.newstrconst("a"))
        assert hash.isset_index(space, space.newstrconst("xyz"))
        assert not hash.isset_index(space, space.wrap(3))
        assert cp_arr.isset_index(space, space.wrap(0))
        assert not cp_arr.isset_index(space, space.wrap(13))

    def test_hashes(self):
        space = ObjSpace()
        assert space.wrap(1).hash() == space.newstrconst("1").hash()
        assert space.wrap(123).hash() == space.newstrconst("123").hash()

    def test_map(self):
        space = ObjSpace()
        w_a = space.newstrconst("a")
        w_b = space.newstrconst("b")
        w_arr = space.new_map_from_pairs([(w_a, space.wrap(0)),
                                         (w_b , space.wrap(12))])
        assert space.int_w(space.getitem(w_arr, w_a)) == 0
        space.setitem(w_arr, w_b, space.wrap(3))
        assert space.int_w(space.getitem(w_arr, w_b)) == 3
        assert w_arr.arraylen(space) == 2
        assert w_arr.isset_index(space, w_b)
        assert not w_arr.isset_index(space, space.wrap(0))
        assert not w_arr.isset_index(space, space.newstrconst("c"))
        w_arr2 = w_arr.copy(space)
        space.setitem(w_arr2, space.wrap(0), space.wrap(15))
        assert w_arr2.strategy.name == 'hash'
        assert space.int_w(space.getitem(w_arr, w_a)) == 0
        assert space.int_w(space.getitem(w_arr, w_b)) == 3
        assert space.int_w(space.getitem(w_arr2, space.wrap(0))) == 15
        space.setitem(w_arr, space.newstrconst("c"), space.wrap(38))
        assert w_arr.strategy.name == 'hash'

    def test_map_iter(self):
        def unpack((w_1, w_2)):
            l = []
            for w_obj in w_1, w_2:
                if w_obj.tp == space.tp_str:
                    l.append(space.str_w(w_obj))
                elif w_obj.tp == space.tp_float:
                    l.append(space.float_w(w_obj))
                elif w_obj.tp == space.tp_int:
                    l.append(space.int_w(w_obj))
                else:
                    raise NotImplementedError
            return l

        space = ObjSpace()
        w_a = space.newstrconst("a")
        w_b = space.newstrconst("b")
        w_arr = space.new_map_from_pairs([(w_a, space.wrap(0)),
                                         (w_b , space.wrap(12))])
        w_iter = w_arr.create_iter(space)
        assert space.int_w(w_iter.next(space)) == 0
        assert space.int_w(w_iter.next(space)) == 12
        assert w_iter.done()
        w_iter = w_arr.create_iter(space)
        assert unpack(w_iter.next_item(space)) == ["a", 0]
        assert unpack(w_iter.next_item(space)) == ["b", 12]
        assert w_iter.done()

class TestArray(BaseTestInterpreter):
    def test_array_constructor(self):
        output = self.run('''
        $a = array(1, 2, 3);
        echo $a;
        ''')
        space = self.space
        assert space.int_w(space.getitem(output[0], space.wrap(0))) == 1
        assert space.int_w(space.getitem(output[0], space.wrap(1))) == 2

    def test_array_constructor_mix(self):
        output = self.run('''
        $a = array(1, "2", 3);
        echo $a;
        ''')
        space = self.space
        assert space.int_w(space.getitem(output[0], space.wrap(0))) == 1
        assert space.str_w(space.getitem(output[0], space.wrap(1))) == "2"

    def test_array_constructor_to_hash(self):
        output = self.run('''
        $a = array(1, "a" => 5, 3, "a" => 99);
        echo $a;
        echo $a["a"];
        ''')
        space = self.space
        assert space.int_w(space.getitem(output[0], space.wrap(0))) == 1
        assert space.str_w(space.getitem(output[0], space.wrap(1))) == "3"
        assert self.space.int_w(output[1]) == 99

    def test_array_empty_strat_append(self):
        output = self.run('''
        $a = array();
        echo $a[] = 3;
        $a[] = 15;
        $a[] = "xyz";
        $a[] = 5;
        echo $a[0];
        echo $a[1];
        echo $a[2];
        echo $a[3];
        ''')
        assert self.space.int_w(output[0]) == 3
        assert self.space.int_w(output[1]) == 3
        assert self.space.int_w(output[2]) == 15
        assert self.space.str_w(output[3]) == "xyz"
        assert self.space.int_w(output[4]) == 5

    def test_array_setitem(self):
        output = self.run('''
        $a = array(1, 2, 3);
        echo $a[1] = 15;
        echo $a[1];
        $a[0] = "xyz";
        echo $a[0];
        echo $a[1];
        ''')
        assert [self.space.int_w(output[i]) for i in [0, 1, 3]] == [15, 15, 15]
        assert self.space.str_w(output[2]) == "xyz"

    def test_array_setitem_inplace(self):
        output = self.run('''
        $a = array(1);
        $a[0] += 3;
        echo $a[0];
        ''')
        assert self.space.int_w(output[0]) == 4

    def test_copy_on_write(self):
        output = self.run('''
        $a = array(1, 2, 3);
        $b = $a;
        $a[1] = 15;
        echo $b[1];
        ''')
        assert self.space.int_w(output[0]) == 2

    def test_float_strategy(self):
        output = self.run('''
        $a = array();
        $a[] = 3.0;
        $b = array(1.2, 3.2);
        echo $a, $b;
        $a[1] = 1.2;
        $b[0] = 1;
        echo $a, $b;
        ''')
        [i.force_write() for i in output]
        assert [i.strategy.name for i in output] == [
            'lfloat', 'lfloat', 'lfloat', 'lobject']
        assert output[0].strategy.unerase(output[0].storage) == [3.0]
        assert output[1].strategy.unerase(output[1].storage) == [1.2, 3.2]
        assert output[2].strategy.unerase(output[2].storage) == [3.0, 1.2]
        assert self.space.int_w(
            output[3].strategy.unerase(output[3].storage)[0]) == 1

    def test_append_empty(self):
        output = self.run('''
        $a = array();
        $a[0] = "abc";
        echo $a[0];
        ''')
        assert self.space.str_w(output[0]) == 'abc'

    def test_hash_constructor(self):
        output = self.run('''
        $z = "xy";
        $z[0] = "a";
        $a = array("x" => "y", "z" => 3, $z => 5);
        echo $a["x"], $a["z"], $a["ay"];
        ''')
        assert self.space.str_w(output[0]) == "y"
        assert self.space.int_w(output[1]) == 3
        assert self.space.int_w(output[2]) == 5

    def test_int_iterator(self):
        output = self.run('''
        $a = array(1, 2, 3, 4);
        foreach($a as $x) {
           echo $x;
        }
        ''')
        assert [self.space.int_w(i) for i in output] == [1, 2, 3, 4]

    def test_modifying_while_iterating(self):
        output = self.run('''
        $a = array(1, 2);
        foreach ($a as $x) {
          $a[1] = 13;
          echo $x;
        }
        ''')
        assert [self.space.int_w(i) for i in output] == [1, 2]

    def test_modifying_while_iterating_2(self):
        output = self.run('''
        $a = array("a" => 1, "b" => 2);
        foreach ($a as $x => $y) {
          $a[1] = 13;
          echo $x;
        }
        ''')
        assert [self.space.str_w(i) for i in output] == ["a", "b"]

    def test_reference_to_arrayitem(self):
        py.test.skip("XXX FIXME")

        output = self.run('''
        function f(&$a) {
          $a = 3;
        }
        $a = array(1, 2);
        f($a[1]);
        echo $a[1];
        ''')
        assert self.space.int_w(output[0]) == 3

    def test_key_value_iterator(self):
        output = self.run('''
        $a = array("a" => 3, "b" => 4);
        foreach ($a as $x => $y) {
           echo $x, $y;
        }
        ''')
        assert self.space.str_w(output[0]) == "a"
        assert self.space.int_w(output[1]) == 3
        assert self.space.str_w(output[2]) == "b"
        assert self.space.int_w(output[3]) == 4

    def test_cast(self):
        output = self.run('''
        $a = (array)3;
        $b = (array)$a;
        echo $a[0], $b[0];
        ''')
        assert [self.space.int_w(i) for i in output] == [3, 3]

    def test_promotion_to_hash(self):
        output = self.run('''
        $a = array(1);
        $a["xyz"] = 3;
        echo $a["xyz"], $a[0];
        ''')
        assert [self.space.int_w(i) for i in output] == [3, 1]

    def test_copy_of_a_copy(self):
        output = self.run('''
        $a = array(1, 2, 3);
        $b = $a;
        $c = $b;
        $c[0] = 3;
        echo $c[0], $a[0], $b[0];
        ''')
        assert [self.space.int_w(i) for i in output] == [3, 1, 1]

    def test_copy_of_a_copy_2(self):
        output = self.run('''
        $a = array(1, 2, 3);
        $b = $a;
        $c = $b;
        $b[0] = 3;
        echo $c[0], $a[0], $b[0];
        ''')
        assert [self.space.int_w(i) for i in output] == [1, 1, 3]

    def test_hash_copy(self):
        output = self.run('''
        $a = array(1 => 2, 3 => 4);
        $a["x"] = 3;
        echo $a["x"];
        ''')
        assert self.space.int_w(output[0]) == 3

    def test_store_makes_copy(self):
        output = self.run('''
        $a = "x";
        $b = array();
        $b["y"] = $a;
        $b["y"][0] = "c";
        echo $a;
        ''')
        assert self.space.str_w(output[0]) == "x"

    def test_array_cast_null(self):
        output = self.run('''
        $a = (array)NULL;
        echo count($a);
        ''')
        assert self.space.int_w(output[0]) == 0

    def test_hashes_equal(self):
        output = self.run('''
        $a = array(123 => "xyz");
        echo $a["123"];
        ''')
        assert self.space.str_w(output[0]) == "xyz"

    def test_hashes_creation(self):
        output = self.run('''
        $a = array(123 => "xyz", "marry", 199=> "abc", "had");
        echo $a["123"];
        echo $a["124"];
        echo $a["200"];

        ''')
        assert self.space.str_w(output[0]) == "xyz"
        assert self.space.str_w(output[1]) == "marry"
        assert self.space.str_w(output[2]) == "had"

    def test_iterator_cleans(self):
        output = self.run('''
        $a = array(1, 2, 3);
        foreach ($a as $x) {
           $x;
        }
        echo $a;
        ''')
        w_arr = output[0]
        cp = w_arr.strategy.unerase(w_arr.storage)
        assert cp.next_link is None

    def test_array_elem(self):
        py.test.skip("XXX FIXME")

        output = self.run('''
        $x = 3;
        $y = &$x;
        $a = array();
        $a[0] = $y;
        echo $a[0];
        $x = 8;
        echo $a[0];
        ''')
        assert [self.space.int_w(i) for i in output] == [3, 3]
