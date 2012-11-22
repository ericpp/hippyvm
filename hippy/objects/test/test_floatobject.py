
from hippy.test.test_interpreter import BaseTestInterpreter


class TestFloatObject(BaseTestInterpreter):

    def test_repr(self):
        assert self.echo('3.0') == '3'
        assert self.echo('gettype(3.0)') == 'double'
