import py, sys
from pypy.rlib.rfloat import INFINITY, NAN, isnan
from hippy.test.test_interpreter import BaseTestInterpreter


class TestArrayObject(BaseTestInterpreter):

    def test_is_true(self):
        space = self.space
        w_array = space.new_array_from_list([])
        assert space.is_true(w_array) is False
        w_array = space.new_array_from_list([space.newint(0)])
        assert space.is_true(w_array) is True

    def test_getitem(self):
        space = self.space
        w_array = space.new_array_from_list([space.newint(42)])
        w_item = space.getitem(w_array, space.newint(0))
        assert space.is_w(w_item, space.newint(42))
        assert w_array.as_dict() == {"0": w_item}

    def test_getitem_hash(self):
        space = self.space
        w_array = space.new_array_from_dict({"foo": space.newint(42),
                                             "-84": space.newint(43)})
        w_item = space.getitem(w_array, space.newstr("foo"))
        assert space.is_w(w_item, space.newint(42))
        w_item = space.getitem(w_array, space.newint(-84))
        assert space.is_w(w_item, space.newint(43))

    def test_setitem(self):
        space = self.space
        w_array = space.new_array_from_list([])
        w_item = space.newstr("bok")
        w_array = space.setitem(w_array, space.newint(0), w_item)
        assert w_array.as_dict() == {"0": w_item}
        w_item2 = space.newstr("bok2")
        w_array = space.setitem(w_array, space.newint(0), w_item2)
        assert w_array.as_dict() == {"0": w_item2}
        w_item3 = space.newstr("bok3")
        w_array = space.setitem(w_array, space.newint(1), w_item3)
        assert w_array.as_dict() == {"0": w_item2, "1": w_item3}

    def test_setitem_hash(self):
        space = self.space
        w_array = space.new_array_from_dict({})
        w_item = space.newstr("bok")
        w_array = space.setitem(w_array, space.newint(0), w_item)
        assert w_array.as_dict() == {"0": w_item}
        w_item2 = space.newstr("bok2")
        w_array = space.setitem(w_array, space.newstr("0"), w_item2)
        assert w_array.as_dict() == {"0": w_item2}
        w_item3 = space.newstr("bok3")
        w_array = space.setitem(w_array, space.newstr("aAa"), w_item3)
        assert w_array.as_dict() == {"0": w_item2, "aAa": w_item3}

    def test_getitem_str(self):
        space = self.space
        w_array = space.new_array_from_list([space.newint(42)])
        w_item = space.getitem(w_array, space.newstr("0"))
        assert space.is_w(w_item, space.newint(42))
        w_item = space.getitem(w_array, space.newstr(""))
        assert w_item is space.w_Null
        w_item = space.getitem(w_array, space.newstr("00"))
        assert w_item is space.w_Null
        w_item = space.getitem(w_array, space.newstr("foo"))
        assert w_item is space.w_Null
        w_item = space.getitem(w_array, space.newstr(str(1<<128)))
        assert w_item is space.w_Null

    def test_list2hash_out_of_bound(self):
        space = self.space
        w_x = space.newstr("x")
        w_y = space.newstr("y")
        w_array = space.new_array_from_list([w_x])
        w_array = space.setitem(w_array, space.newint(100), w_y)
        assert w_array.as_dict() == {"0": w_x, "100": w_y}

    def test_list2hash_str(self):
        space = self.space
        w_x = space.newstr("x")
        w_y = space.newstr("y")
        w_array = space.new_array_from_list([w_x])
        w_array = space.setitem(w_array, space.newstr("z"), w_y)
        assert w_array.as_dict() == {"0": w_x, "z": w_y}
        assert w_array._has_string_keys

    def test_setitem_numeric_str(self):
        space = self.space
        w_x = space.newstr("x")
        w_y = space.newstr("y")
        w_array = space.new_array_from_list([w_x])
        w_array = space.setitem(w_array, space.newstr("0"), w_y)
        assert w_array.as_dict() == {"0": w_y}
        assert not w_array._has_string_keys

    def test_unsetitem(self):
        space = self.space
        for w_0, w_2 in [(space.newint(0), space.newint(2)),
                         (space.newstr("0"), space.newstr("2"))]:
            w_x = space.newstr("x")
            w_y = space.newstr("y")
            w_z = space.newstr("z")
            w_array = space.new_array_from_list([w_x, w_y, w_z])
            w_array = space.unsetitem(w_array, w_2)
            assert w_array.as_dict() == {"0": w_x, "1": w_y}
            assert not w_array._has_string_keys
            w_array = space.unsetitem(w_array, w_2)
            assert w_array.as_dict() == {"0": w_x, "1": w_y}
            assert not w_array._has_string_keys
            w_array = space.unsetitem(w_array, w_0)
            assert w_array.as_dict() == {"1": w_y}
            assert w_array._has_string_keys   # for now

    def test_unsetitem_hash(self):
        space = self.space
        w_x = space.newstr("x")
        w_y = space.newstr("y")
        w_array = space.new_array_from_dict({"foo": w_x, "42": w_y})
        w_array = space.unsetitem(w_array, space.newint(42))
        assert w_array.as_dict() == {"foo": w_x}
        w_array = space.unsetitem(w_array, space.newstr("bar"))
        assert w_array.as_dict() == {"foo": w_x}
        w_array = space.unsetitem(w_array, space.newstr("foo"))
        assert w_array.as_dict() == {}

    def test_index_overflow(self):
        def check(inputfloat, outputint):
            if isnan(inputfloat):         inputfloat = 'NAN'
            elif inputfloat == INFINITY:  inputfloat = 'INF'
            elif inputfloat == -INFINITY: inputfloat = '-INF'
            else: inputfloat = repr(inputfloat)
            output = self.run("""
                $arr1 = array(%d=>4);
                echo $arr1[%s];
            """ % (outputint, inputfloat))
            assert self.space.is_w(output[0], self.space.newint(4))

        check(123.95, 123)
        check(-123.95, -123)
        check(2147483647.1, 2147483647)
        check(-1234567898765432123456789.0, 0)
        check(1234567898765432123456789.0, 0)
        check(INFINITY, 0)
        check(-INFINITY, 0)
        check(NAN, -sys.maxint-1)
        check(-9.223372036855e+18, 0)
        check(9.223372036855e+18, 0)
        if sys.maxint > 2**32:
            py.test.xfail("parsing of floats doesn't get a 1-1 exact result")
        check(9.223372036854767e+18, -9216)
        check(9.223372036854766e+18, -10240)
        check(9.223372036854786e+18, 0)
        check(9.214148664817921e+18, 1511828480)
