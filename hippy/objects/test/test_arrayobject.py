
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

    def test_getitem_hash(self):
        space = self.space
        w_array = space.new_array_from_dict({"foo": space.newint(42),
                                             "-84": space.newint(43)})
        w_item = space.getitem(w_array, space.newstr("foo"))
        assert space.is_w(w_item, space.newint(42))
        w_item = space.getitem(w_array, space.newint(-84))
        assert space.is_w(w_item, space.newint(43))
