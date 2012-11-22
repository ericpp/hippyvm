
from hippy.test.test_interpreter import BaseTestInterpreter


class TestIntObject(BaseTestInterpreter):

    def test_division(self):
        assert self.echo('5 / 2') == '2.5'
        assert self.echo('6 / 2') == '3'
        assert self.echo('gettype(5 / 2)') == 'double'
        assert self.echo('gettype(6 / 2)') == 'integer'
