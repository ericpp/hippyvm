
from hippy.consts import BYTECODE_STACK_EFFECTS, ARGVAL, BYTECODE_NUM_ARGS,\
     BYTECODE_NAMES, ARGVAL1, ARGVAL2
from hippy.error import InterpreterError
from pypy.rlib import jit

class ByteCode(object):
    """ A representation of a single code block
    """
    _immutable_fields_ = ['code', 'consts[*]', 'varnames[*]',
                          'functions[*]', 'names[*]', 'stackdepth',
                          'var_to_pos', 'names_to_pos', 'user_functions']
    
    def __init__(self, code, consts, names, varnames, user_functions,
                 static_vars,
                 startlineno=0, bc_mapping=None, name='<main>'):
        self.code = code
        self.consts = consts
        self.names = names
        self.varnames = varnames # named variables
        self.stackdepth = self.count_stack_depth()
        self.var_to_pos = {}
        self.names_to_pos = {}
        self.user_functions = user_functions
        self.startlineno = startlineno
        self.bc_mapping = bc_mapping
        self.name = name
        for i, v in enumerate(varnames):
            assert i >= 0
            self.var_to_pos[v] = i
        for i, v in enumerate(names):
            self.names_to_pos[v] = i
        self.static_vars = static_vars

    @jit.elidable
    def lookup_static(self, name):
        return self.static_vars[name]

    def lookup_var_pos(self, v):
        return self._lookup_pos(jit.hint(v, promote_string=True))

    @jit.elidable
    def lookup_pos(self, v):
        return self.names_to_pos[v]

    @jit.elidable
    def _lookup_pos(self, v):
        return self.var_to_pos[v]

    def setup_functions(self, interp, space):
        if self.user_functions is not None:
            self._setup_functions(interp, space)

    def _setup_functions(self, interp, space):
        for v in self.user_functions:
            if v in interp.functions:
                raise InterpreterError("Function %s alread declared")
            interp.functions[v] = self.user_functions[v]
        self.user_functions = None

    def count_stack_depth(self):
        i = 0
        counter = 0
        max_eff = 0
        while i < len(self.code):
            c = ord(self.code[i])
            i += 1
            stack_eff = BYTECODE_STACK_EFFECTS[c]
            if stack_eff == ARGVAL:
                stack_eff = -ord(self.code[i])
            elif stack_eff == ARGVAL1:
                stack_eff = -ord(self.code[i]) + 1
            elif stack_eff == ARGVAL2:
                stack_eff = -2*ord(self.code[i]) + 1
            i += BYTECODE_NUM_ARGS[c] * 2
            counter += stack_eff
            max_eff = max(counter, max_eff)
        return max_eff

    def dump(self):
        i = 0
        lines = []
        while i < len(self.code):
            if i == self._marker:   # not translated
                line = ' ===> '
            else:
                line = '%4d  ' % (i,)
            c = ord(self.code[i])
            line += BYTECODE_NAMES[c]
            i += 1
            for k in range(BYTECODE_NUM_ARGS[c]):
                line += " %s" % (ord(self.code[i]) +
                                 (ord(self.code[i + 1]) << 8))
                i += 2
            lines.append(line)
        return "\n".join(lines)

    def show(self):
        print self.dump()
