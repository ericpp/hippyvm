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
from hippy.logger import Logger
from hippy.objspace import getspace


def repl(argv):
    if len(argv) > 1:
        print "XXX arguments ignored"
    space = getspace()
    interp = Interpreter(space, Logger())
    namespace = {}
    print
    print '-=- Hippy -=-'
    print
    while True:
        try:
            line = raw_input("<? ")
        except EOFError:
            print
            break
        if not line.lstrip() or line.lstrip().startswith('//'):
            continue
        try:
            pc = parse(line)
            bc = compile_ast("<input>", line, pc, space, 0, print_exprs=True)
        except Exception, e:
            print >> sys.stderr, '%s: %s' % (e.__class__.__name__, e)
            continue
        try:
            interp.run_main(space, bc)
        except Exception, e:
            print e
            pdb.post_mortem(sys.exc_info()[2])

if __name__ == '__main__':
    repl(sys.argv)
