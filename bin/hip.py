#!/usr/bin/env python
"""
Main read-eval-print loop for untranslated Hippy.
"""

import sys, os, pdb

if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hippy.sourceparser import parse
from hippy.astcompiler import compile_ast
from hippy.interpreter import Interpreter, Frame
from hippy.objspace import getspace


def repl(argv):
    if len(argv) > 1:
        print "XXX arguments ignored"
    space = getspace()
    interp = Interpreter(space)
    namespace = {}
    while True:
        print
        try:
            line = raw_input("Hippy > ")
        except EOFError:
            print
            break
        try:
            pc = parse(line)
            bc = compile_ast(pc, space, 0)
            assert bc.uses_dict
        except Exception, e:
            print >> sys.stderr, '%s: %s' % (e.__class__.__name__, e)
            continue
        try:
            frame = Frame(space, bc)
            frame.vars_dict.d.update(namespace)
            namespace = frame.vars_dict.d
            interp.interpret(space, frame, bc)
        except Exception, e:
            print e
            pdb.post_mortem(sys.exc_info()[2])

if __name__ == '__main__':
    repl(sys.argv)
