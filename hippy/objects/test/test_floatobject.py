
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

    def test_lshift(self):
        # truncated to ints
        assert self.echo('5.9 << 1') == '10'
        assert self.echo('5.9 << 1.9') == '10'
        assert self.echo('gettype(5.9 << 1)') == 'integer'

    def test_rshift(self):
        # truncated to ints
        assert self.echo('32.9 >> 1') == '16'
        assert self.echo('32.9 >> 2.9') == '8'
        assert self.echo('gettype(32.9 >> 1)') == 'integer'

    def test_or(self):
        # truncated to ints
        assert self.echo('6.9 | 1') == '7'
        assert self.echo('6.9 | 1.9') == '7'
        assert self.echo('gettype(6.9 | 1.9)') == 'integer'

    def test_and(self):
        # truncated to ints
        assert self.echo('6.9 & 5.9') == '4'
        assert self.echo('gettype(6.9 & 5.9)') == 'integer'
