
""" Hippy VM. Execute by typing

hippy <file.php> [--gcdump gcdumpfile]

and enjoy
"""

import sys, os, pdb

if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hippy.sourceparser import parse
from hippy.astcompiler import compile_ast
from hippy.interpreter import Interpreter, Frame
from hippy.logger import Logger
from hippy.objspace import getspace
from pypy.rlib.streamio import open_file_as_stream
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.rgc import dump_rpy_heap
from pypy.rlib import jit

class Error(Exception):
    pass

def entry_point(argv):
    jit.set_param(None, 'trace_limit', 20000)
    if len(argv) < 2:
        print __doc__
        return 1
    f = open_file_as_stream(argv[1])
    data = f.readall()
    f.close()
    c = 0
    try:
        while True:
            assert c >= 0
            next_c = data.find("\n", c)
            if next_c < 0:
                raise Error
            line = data[c:next_c].strip(" ")
            if line:
                start = next_c + 1
                if line != '<?php' and line != '<?':
                    raise Error
                break
            c = next_c + 1
        c = len(data)
        while True:
            assert c >= 0
            prev_c = data.rfind('\n', 0, c)
            if prev_c < 0:
                raise Error
            line = data[prev_c + 1:c].strip(" ")
            if line:
                end = prev_c
                if line != '?>':
                    raise Error
                break
            c = prev_c
    except Error:
        print "not a php input file, can't find <?php ?> tags"
        return 1

    extra_offset = data[:start].count("\n") + 1
    data = data[start:end]
    space = getspace()
    bc = compile_ast(data, parse(data), space, extra_offset)
    interp = Interpreter(space, Logger())
    frame = Frame(space, bc)
    if not we_are_translated():
        try:
            interp.interpret(space, frame, bc)
        except Exception, e:
            print e
            pdb.post_mortem(sys.exc_info()[2])
    else:
        interp.interpret(space, frame, bc)
    if len(argv) >= 4 and argv[2] == '--gcdump':
        f = os.open(argv[3], os.O_CREAT | os.O_WRONLY, 0777)
        dump_rpy_heap(f)
        os.close(f)
    return 0

if __name__ == '__main__':
    entry_point(sys.argv)
