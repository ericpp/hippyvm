
import py
import os
import fnmatch
from hippy.interpreter import Interpreter
from hippy.test.test_interpreter import BaseTestInterpreter, MockLogger

py.test.skip("in progress")

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
            if l.startswith('<?'):
                continue
            if l.startswith('?>'):
                continue
            if l.startswith('==='):
                continue
            src.append(l)
        if st == 1:
            exp.append(l)
    return (tname, " ".join(src), [l for l in exp if l.strip()])


class MockInterpreter(Interpreter):
    """ Like the interpreter, but captures stdout
    """
    def __init__(self, space):
        logger = MockLogger()
        Interpreter.__init__(self, space, logger)
        self.output = []

    def echo(self, space, v):
        self.output.append(space.str_w(v.deref()))


def pytest_generate_tests(metafunc):
    argvalues = []
    for phpt in metafunc.cls.phpt_files:
        argvalues.append(phpt)
    metafunc.parametrize("file_name", argvalues)

TEST_DIR = os.path.dirname(__file__)
PHPT_DIR = os.path.join(TEST_DIR, 'phpts-5.4.9')
PHPT_FILES = []
for root, dirs, files in os.walk(PHPT_DIR):
    PHPT_FILES += [os.path.join(root, f) for f in files
                   if fnmatch.fnmatch(f, '*.phpt')]
PHPT_FILES.sort()


class TestPHPTSuite(BaseTestInterpreter):
    phpt_files = PHPT_FILES
    interpreter = MockInterpreter

    def test_phpt(self, file_name):
        (tname, src, exp) = parse_phpt(file_name)

        output = self.run(src)
        for i, line in enumerate(output):
            if not isinstance(line, str):
                line = self.space.str_w(line)
                assert line.strip() == exp[i].strip()
