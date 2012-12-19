
from hippy.objects.convert import _whitespaces_in_front
from hippy.objects.convert import convert_string_to_number


def test_whitespaces_in_front():
    assert _whitespaces_in_front('') == 0
    assert _whitespaces_in_front('\t ') == 2
    assert _whitespaces_in_front('\tX\t') == 1
    assert _whitespaces_in_front('   .-.') == 3

class FakeSpace(object):
    def wrap(self, result):
        return '%s: %s' % (type(result).__name__, str(result))
    def newint(self, result):
        return 'int: %s' % (str(result),)
    def newfloat(self, result):
        return 'float: %s' % (str(result),)

def test_convert_string_to_number_int():
    space = FakeSpace()
    assert convert_string_to_number(space, '') == ('int: 0', False)
    assert convert_string_to_number(space, '    ') == ('int: 0', False)
    assert convert_string_to_number(space, '+') == ('int: 0', False)
    assert convert_string_to_number(space, '-') == ('int: 0', False)
    assert convert_string_to_number(space, '1') == ('int: 1', True)
    assert convert_string_to_number(space, '\t-101') == ('int: -101', True)
    assert convert_string_to_number(space, '020') == ('int: 20', True)
    assert convert_string_to_number(space, '50b') == ('int: 50', False)
    assert convert_string_to_number(space, '50x') == ('int: 50', False)
    assert convert_string_to_number(space, '5x0') == ('int: 5', False)
    assert convert_string_to_number(space, 'x50') == ('int: 0', False)
    assert convert_string_to_number(space, '0x50') == ('int: 80', True)
    assert convert_string_to_number(space, '0X50') == ('int: 80', True)
    assert convert_string_to_number(space, '0X50X') == ('int: 80', False)
    assert convert_string_to_number(space, '-0x50') == ('int: 0', False)
    assert convert_string_to_number(space, '+0x50') == ('int: 0', False)

def test_convert_string_to_number_overflow():
    space = FakeSpace()
    assert convert_string_to_number(space, '1' * 100) == (
        'float: 1.11111111111e+99', True)
    assert convert_string_to_number(space, '-' + '1' * 100) == (
        'float: -1.11111111111e+99', True)
    assert convert_string_to_number(space, '0x' + '1' * 100) == (
        'float: 1.72149991872e+119', True)
    assert convert_string_to_number(space, '-0x' + '1' * 100) == (
        'int: 0', False)

def test_convert_string_to_number_float():
    space = FakeSpace()
    assert convert_string_to_number(space, ' 5.') == ('float: 5.0', True)
    assert convert_string_to_number(space, ' -.5') == ('float: -0.5', True)
    assert convert_string_to_number(space, ' .') == ('int: 0', False)
    assert convert_string_to_number(space, ' 10.25') == ('float: 10.25', True)
    assert convert_string_to_number(space, ' 10.25X') == ('float: 10.25',False)
    #
    assert convert_string_to_number(space, 'E5') == ('int: 0', False)
    assert convert_string_to_number(space, '.E5') == ('int: 0', False)
    assert convert_string_to_number(space, '5E') == ('int: 5', False)
    assert convert_string_to_number(space, '5.E') == ('float: 5.0', False)
    assert convert_string_to_number(space, '5E-') == ('int: 5', False)
    assert convert_string_to_number(space, '5E+') == ('int: 5', False)
    assert convert_string_to_number(space, '5E0') == ('float: 5.0', True)
    assert convert_string_to_number(space, '5E+0') == ('float: 5.0', True)
    assert convert_string_to_number(space, '5E-0') == ('float: 5.0', True)
    assert convert_string_to_number(space, '5E2') == ('float: 500.0', True)
    assert convert_string_to_number(space, '5E-02') == ('float: 0.05', True)
    assert convert_string_to_number(space, '5E-02.9') == ('float: 0.05', False)
    assert convert_string_to_number(space, '5E-02E9') == ('float: 0.05', False)
    assert convert_string_to_number(space, '5e2') == ('float: 500.0', True)
