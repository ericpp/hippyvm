import sys
from hippy.test.test_interpreter import BaseTestInterpreter


class TestIntObject(BaseTestInterpreter):

    def test_cast_to_int(self):
        assert self.echo('(int)42') == '42'
        assert self.echo('(int)FaLsE') == '0'
        assert self.echo('(int)TrUe') == '1'
        assert self.echo('(int)12.34') == '12'
        assert self.echo('(int)-12.34') == '-12'
        assert self.echo('(int)"  42  "') == '42'

    def test_cast_to_integer(self):
        assert self.echo('(integer)-42') == '-42'
        assert self.echo('(integer)FaLsE') == '0'
        assert self.echo('(integer)TrUe') == '1'
        assert self.echo('(integer)-1E3') == '-1000'
        assert self.echo('(integer)"  12.34  "') == '12'
        assert self.echo('(integer)NULL') == '0'

    def test_division(self):
        assert self.echo('5 / 2') == '2.5'
        assert self.echo('6 / 2') == '3'
        assert self.echo('gettype(5 / 2)') == 'double'
        assert self.echo('gettype(6 / 2)') == 'integer'

    def test_modulo(self):
        assert self.echo('50 % 20') == '10'
        assert self.echo('50 % -20') == '10'
        assert self.echo('(-50) % 20') == '-10'
        assert self.echo('(-50) % -20') == '-10'

    def test_uplusplus(self):
        output = self.run('$a = -189;\necho ++$a;')
        assert self.space.is_w(output[0], self.space.newint(-188))
        output = self.run('$a = %d;\necho ++$a;' % sys.maxint)
        assert self.space.is_w(output[0], self.space.newfloat(sys.maxint+1))
        output = self.run('$a = NULL;\necho ++$a;')
        assert self.space.is_w(output[0], self.space.newint(1))
