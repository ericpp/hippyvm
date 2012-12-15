
from hippy.test.test_interpreter import BaseTestInterpreter


class TestArrayObject(BaseTestInterpreter):

    def test_bool_w(self):
        space = self.space
        w_array = space.new_array_from_list([])
        assert space.bool_w(w_array) is False
        w_array = space.new_array_from_list([space.newint(0)])
        assert space.bool_w(w_array) is True

    def test_getitem(self):
        space = self.space
        w_array = space.new_array_from_list([space.newint(42)])
        w_item = space.getitem(w_array, space.newint(0))
        assert space.is_w(w_item, space.newint(42))
