
from hippy.test.test_interpreter import BaseTestInterpreter


class TestFloatObject(BaseTestInterpreter):

    def test_repr(self):
        assert self.echo('3.0') == '3'
        assert self.echo('gettype(3.0)') == 'double'

    def test_modulo(self):
        # floats are just truncated to ints first
        assert self.echo('5.9 % 2') == '1'
        assert self.echo('5.9 % 2.9') == '1'
        assert self.echo('6.0 % 2.9') == '0'
        assert self.echo('6 % 2.9') == '0'
        assert self.echo('(-5.9) % 2.9') == '-1'
        assert self.echo('5.9 % (-2.9)') == '1'
        assert self.echo('gettype((-5.9) % 2.9)') == 'integer'
