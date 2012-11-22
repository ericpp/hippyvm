
from hippy.test.directrunner import source_replace, run_source
from hippy.objspace import ObjSpace

def test_source_replace():
    res = source_replace('''
    echo 1;
    echo "echo";
    123;
    ''')
    assert res == '''<?


var_dump(1);
var_dump("echo");
123;


?>
'''

def test_source_run():
    space = ObjSpace()
    output = run_source(space, '''
    echo 1;
    ''')
    assert len(output) == 1
    assert space.int_w(output[0]) == 1

def test_parse_array_output():
    pass
