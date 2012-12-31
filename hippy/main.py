
""" Hippy VM. Execute by typing

hippy <file.php> [--gcdump gcdumpfile]

and enjoy
"""

import sys, os

if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hippy.phpcompiler import compile_php
from hippy.interpreter import Interpreter
from hippy.logger import Logger, InterpreterError
from hippy.objspace import getspace
from pypy.rlib.streamio import open_file_as_stream
from pypy.rlib.rgc import dump_rpy_heap
from pypy.rlib import jit

class Error(Exception):
    pass

def entry_point(argv):
    jit.set_param(None, 'trace_limit', 20000)
    if len(argv) < 2:
        print __doc__
        return 1
    filename = argv[1]
    f = open_file_as_stream(filename)
    data = f.readall()
    f.close()
    #
    space = getspace()
    bc = compile_php(filename, data, space)
    #
    interp = Interpreter(space, Logger())
    try:
        interp.run_main(space, bc)
    except InterpreterError:
        # the traceback should already have been printed,
        # including the error msg
        pass
    if len(argv) >= 4 and argv[2] == '--gcdump':
        f = os.open(argv[3], os.O_CREAT | os.O_WRONLY, 0777)
        dump_rpy_heap(f)
        os.close(f)
    return 0

if __name__ == '__main__':
    entry_point(sys.argv)
