
import py
import os
from hippy.interpreter import Interpreter, Frame
from hippy.objspace import ObjSpace
from hippy.sourceparser import parse
from hippy.astcompiler import compile_ast
from hippy.error import InterpreterError
from hippy.conftest import option
from hippy.test.directrunner import run_source

TEST_DIR = os.path.dirname(__file__)
PHPT_DIR = os.path.join(TEST_DIR, 'phpts')


def parse_phpt(fname):
    src = []
    exp = []
    tname = None
    st = None  # -1, testname ,0 src, 1 exp
    with open(fname) as f:
        lines = f.readlines()
    for l in lines:
        if l.startswith("--TEST--"):
            st = -1
            continue
        if l.startswith("--FILE--"):
            st = 0
            continue
        if l.startswith("--EXPECTF--"):
            st = 1
            continue

        if st == -1:
            tname = l.strip()
        if st == 0:
            if l.startswith('<?'): continue
            if l.startswith('?>'): continue
            src.append(l)
        if st == 1:
            exp.append(l)
    return (tname, " ".join(src), exp)


class MockInterpreter(Interpreter):
    """ Like the interpreter, but captures stdout
    """
    def __init__(self, space):
        Interpreter.__init__(self, space)
        self.output = []

    def echo(self, space, v):
        self.output.append(v.deref().copy(space))


class BaseTestInterpreter(object):

    def run(self, source):
        self.space = ObjSpace()
        if option.runappdirect:
            return run_source(self.space, source)
        interp = MockInterpreter(self.space)
        self.space.ec.writestr = interp.output.append
        bc = compile_ast(parse(source), self.space)
        interp.interpret(self.space, Frame(self.space, bc), bc)
        return interp.output

    def echo(self, source):
        output = self.run("echo %s;" % (source,))
        assert len(output) == 1
        return self.space.str_w(output[0])


class TestPHPTSuite(BaseTestInterpreter):

    def test_array_pad_phpt(self):
        fname = os.path.join(PHPT_DIR, 'standard/tests/array/array_pad.phpt')
        (tname, src, exp) = parse_phpt(fname)

        output = self.run(src)
        for i, line in enumerate(output):
            if not isinstance(line, str):
                line = self.space.str_w(line)
            #print i, exp[i].strip(), self.space.str_w(line).strip()
            assert line == exp[i]
